import logging
import os
import pathlib
import traceback

import osmnx as ox
import requests
from PyQt5.QtCore import Qt, QVariant, QModelIndex, QAbstractTableModel, QDate
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QIcon, QPalette
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, \
    QSizePolicy, QComboBox, QCheckBox, QGroupBox, QRadioButton, QFrame, QTabWidget, QLabel, QTableView, QHeaderView, \
    QPushButton, QListView, QMessageBox, QToolBox, QCalendarWidget, QLineEdit, QToolButton, QScrollArea, QFormLayout, \
    QLayout, QAbstractScrollArea
from requests import RequestException

from Exceptions.OverpassExceptions import OverpassRequestException
from Models.OverpassQuery import OverpassQuery, Surround, OverpassRequest, OverpassUnion, OverpassIntersection, \
    OverpassDiff, OsmType
from Utils.SumoUtils import tempDir, writeXMLResponse
from Utils.TaginfoUtils import getOfficialKeys, getKeyDescription, getValuesByKey
from Views.CollapsibleList import CheckableComboBox
from Views.DisambiguationTable import SimilarWaysTable, DisconnectedWaysTable

resDir = pathlib.Path(__file__).parent.parent.absolute().joinpath("Resources")
picturesDir = os.path.join(resDir, "pictures")


class HorizontalLine(QFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class OperationsTableModel(QAbstractTableModel):

    def __init__(self):
        QAbstractTableModel.__init__(self)

        self.headerItems = ["Name", "Type", "Components"]
        self.ops = []

    def addOp(self, name, op):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self.ops.append((name, op))
        self.endInsertRows()

    def removeOp(self, opToRemove):
        for i in range(len(self.ops)):
            if self.ops[i][0] == opToRemove:
                self.beginRemoveRows(QModelIndex(), i, i)
                self.ops.pop(i)
                self.endRemoveRows()
                break

    def getOpByIndex(self, i):
        return self.ops[i][0]

    def rowCount(self, parent=QModelIndex(), **kwargs):
        return len(self.ops)

    def columnCount(self, parent=QModelIndex(), **kwargs):
        return len(self.headerItems)

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headerItems[section]
        else:
            return "{}".format(section)

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            if column == 0:
                return self.ops[row][0]
            elif column == 1:
                return self.ops[row][1].getType()
            elif column == 2:
                if self.ops[row][1].getType() == "Difference":
                    return "%s - %s" % (self.ops[row][1].includedSet, ",".join(self.ops[row][1].sets))
                else:
                    return ",".join(self.ops[row][1].sets)
        elif role == Qt.BackgroundRole:
            return QColor(Qt.white)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight

        return None


class RequestsOperations(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.initUI()
        self.__ops = {}

    def initUI(self):
        self.layout = QFormLayout()
        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        twoListsOfSets = QWidget()
        twoListsOfSets.setLayout(QHBoxLayout())
        twoListsOfSets.layout().setContentsMargins(0,10,0,0)
        twoListsOfSets.layout().setSpacing(0)

        self.requestList = QListView()
        self.requestList.setFlow(QListView.LeftToRight)
        self.requestList.setWrapping(True)
        self.requestList.setResizeMode(QListView.Adjust)
        self.requestList.setUniformItemSizes(True)
        self.requestList.setFrameStyle(QFrame.NoFrame)
        self.requestList.viewport().setAutoFillBackground(False)
        self.requestsModel = QStandardItemModel()
        self.requestList.setModel(self.requestsModel)

        self.requestList2 = QListView()
        self.requestList2.setFlow(QListView.LeftToRight)
        self.requestList2.setWrapping(True)
        self.requestList2.setResizeMode(QListView.Adjust)
        self.requestList2.setUniformItemSizes(True)
        self.requestList2.setFrameStyle(QFrame.NoFrame)
        self.requestList2.viewport().setAutoFillBackground(False)
        self.requestsModel2 = QStandardItemModel()
        self.requestList2.setModel(self.requestsModel2)

        twoListsOfSets.layout().addWidget(self.requestList)
        twoListsOfSets.layout().addWidget(self.requestList2)

        self.layout.addRow("Sets", twoListsOfSets)

        self.operationSelection = QGroupBox()
        self.operationSelection.setFlat(True)
        self.operationSelection.setLayout(QVBoxLayout())

        self.buttonIntersection = QRadioButton("Intersection")
        self.operationSelection.layout().addWidget(self.buttonIntersection)
        self.buttonIntersection.clicked.connect(self.__disableSecondRequestList)
        self.buttonIntersection.click()

        self.buttonUnion = QRadioButton("Union")
        self.operationSelection.layout().addWidget(self.buttonUnion)
        self.buttonUnion.clicked.connect(self.__disableSecondRequestList)

        self.buttonDiff = QRadioButton("Difference")
        self.operationSelection.layout().addWidget(self.buttonDiff)
        self.buttonDiff.clicked.connect(self.__enableSecondRequestList)

        self.layout.addRow("Operation", self.operationSelection)

        self.buttonApply = QPushButton("Apply")
        self.buttonApply.clicked.connect(self.__applyOp)
        self.operationSelection.layout().addWidget(self.buttonApply)
        self.layout.addRow("", self.buttonApply)

        self.layout.addRow("Resulting sets", None)

        self.resultingSets = QTableView()
        self.resultingSets.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resultingSets.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.resultingSets.setModel(OperationsTableModel())
        self.layout.addRow(self.resultingSets)

        self.outputSetSelection = QComboBox()
        self.outputSetSelection.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.layout.addRow("Output set", self.outputSetSelection)

        self.setLayout(self.layout)

    def outputSet(self):
        return self.outputSetSelection.currentText()

    @property
    def ops(self):
        return self.__ops

    def __applyOp(self):
        includedSets = [self.requestsModel.item(i).text() for i in range(self.requestsModel.rowCount()) if
                        self.requestsModel.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]

        if self.buttonUnion.isChecked():
            if len(includedSets) > 1:
                self.__addOp(OverpassUnion(), includedSets)
        elif self.buttonIntersection.isChecked():
            if len(includedSets) > 1:
                self.__addOp(OverpassIntersection(), includedSets)
        elif self.buttonDiff.isChecked():
            excludedSets = [self.requestsModel2.item(i).text() for i in range(self.requestsModel2.rowCount()) if
                            self.requestsModel2.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]

            if len(includedSets) == 1 and len(excludedSets) > 0:
                self.__addOp(OverpassDiff(includedSets[0]), excludedSets)

    def __addOp(self, op, sets):
        setName = OverpassQuery.getUniqueSetName()
        self.__ops[setName] = op
        self.__ops[setName].addSets(sets)
        self.resultingSets.model().addOp(setName, self.__ops[setName])
        self.addRequest(setName)
        self.cleanRequestList()

    def __enableSecondRequestList(self):
        self.requestList2.show()

    def __disableSecondRequestList(self):
        self.requestList2.hide()

    def addRequest(self, name):
        self.requestsModel.beginInsertRows(QModelIndex(), self.requestsModel.rowCount(), self.requestsModel.rowCount())
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
        self.requestsModel.appendRow(item)
        self.requestsModel.endInsertRows()

        self.requestsModel2.beginInsertRows(QModelIndex(), self.requestsModel2.rowCount(),
                                            self.requestsModel2.rowCount())
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
        self.requestsModel2.appendRow(item)
        self.requestsModel2.endInsertRows()

        self.outputSetSelection.addItem(name)

    def removeSetAndDependencies(self, setName):
        removeList = [setName]

        for set in removeList:
            removeList.extend([i for i in self.__removeSet(set) if i not in removeList])

    def __removeSet(self, setName):
        dependencies = []
        for opName in self.__ops.keys():
            self.__ops[opName].removeSet(setName)
            if not self.__ops[opName].isValid():
                dependencies.append(opName)

        for i in range(self.requestsModel.rowCount()):
            if self.requestsModel.item(i).text() == setName:
                self.requestsModel.beginRemoveRows(QModelIndex(), i, i)
                self.requestsModel.removeRow(i)
                self.requestsModel.endInsertRows()

                self.requestsModel2.beginRemoveRows(QModelIndex(), i, i)
                self.requestsModel2.removeRow(i)
                self.requestsModel2.endInsertRows()

                self.outputSetSelection.removeItem(i)
                break

        if setName in self.__ops.keys():
            self.resultingSets.model().removeOp(setName)
            del self.__ops[setName]

        return dependencies

    def cleanRequestList(self):
        for i in range(self.requestsModel.rowCount()):
            self.requestsModel.item(i).setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
            self.requestsModel2.item(i).setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace and self.resultingSets.hasFocus():

            advice = "Are you sure?\nAll sets containing this one will be deleted if they are no longer valid"
            reply = QMessageBox.question(self, "Remove request operation", advice)

            if reply == QMessageBox.Yes:
                select = self.resultingSets.selectionModel()
                while len(select.selectedRows()) > 0:
                    self.removeSetAndDependencies(
                        self.resultingSets.model().getOpByIndex(select.selectedRows()[0].row()))

        event.accept()


class FilterWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

    def initUI(self):
        self.layout = QFormLayout()
        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setVerticalSpacing(0)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        topWidget = QWidget()
        topLayout = QHBoxLayout()
        topLayout.setSpacing(0)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topWidget.setLayout(topLayout)

        self.keyInput = QComboBox()
        self.keyInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.keyInput.setEditable(True)
        self.keyInput.addItems(self.keyValues)
        topLayout.addWidget(self.keyInput)

        self.deleteButton = QPushButton(QIcon(os.path.join(picturesDir, "remove.png")), "")
        self.deleteButton.setFlat(True)
        self.deleteButton.clicked.connect(self.deleteLater)
        topLayout.addWidget(self.deleteButton)

        self.keyInfoButton = QPushButton(QIcon(os.path.join(picturesDir, "info.png")), "")
        self.keyInfoButton.setFlat(True)
        self.keyInfoButton.clicked.connect(self.getInfo)

        self.layout.addRow("Key:", topWidget)

        valueEdition = QWidget()
        valueEdition.setLayout(QHBoxLayout())
        valueEdition.layout().setSpacing(0)
        valueEdition.layout().setContentsMargins(0, 0, 0, 0)

        self.valueInput = QComboBox()
        self.valueInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.valueInput.setEditable(True)
        valueEdition.layout().addWidget(self.valueInput)
        valueEdition.layout().addWidget(self.keyInfoButton)


        self.layout.addRow("Value:", valueEdition)

        self.keyInput.currentTextChanged.connect(self.valueInput.clear)

        flagsWidgetLayout = QHBoxLayout()

        self.checkboxAccuracy = QCheckBox()
        self.checkboxAccuracy.setText("Exact Value")
        flagsWidgetLayout.addWidget(self.checkboxAccuracy)

        self.checkboxNegate = QCheckBox()
        self.checkboxNegate.setText("Negate")
        flagsWidgetLayout.addWidget(self.checkboxNegate)

        self.layout.addRow("Flags:", flagsWidgetLayout)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.setLayout(self.layout)

    def getInfo(self):
        keyName = self.keyInput.currentText()
        try:
            descriptions = getKeyDescription(keyName)
            if len(descriptions) == 0:
                logging.warning("'{}' is an unofficial or unused key. No available description.".format(keyName))
            else:
                englishDescription = next((d["description"] for d in descriptions if d["language_en"] == "English"),
                                          "English description not available.")
                logging.info(keyName + ": " + englishDescription)
        except RequestException:
            logging.error("There was a problem with the internet connection. Can't get the key description.")
            return

        self.valueInput.clear()

        try:
            self.valueInput.addItems(getValuesByKey(keyName))
        except requests.exceptions.Timeout:
            logging.warning("Too many available values for the given key.")
        except RequestException:
            logging.error("There was a problem with the internet connection. Can't get the possible values for the "
                          "given key.")

    def getKey(self):
        return self.keyInput.currentText()

    def getValue(self):
        return self.valueInput.currentText()

    def setKey(self, key):
        self.keyInput.setEditText(key)

    def setValue(self, value):
        self.valueInput.setEditText(value)

    def isExactValueSelected(self):
        return self.checkboxAccuracy.isChecked()

    def setExactValue(self, bool):
        self.checkboxAccuracy.setChecked(bool)

    def isNegateSelected(self):
        return self.checkboxNegate.isChecked()

    def setNegate(self, bool):
        self.checkboxNegate.setChecked(bool)

    def isSelectedToDelete(self):
        return self.removeCB.isChecked()


class RequestWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

    def __onAreaSelected(self):
        self.nodesCB.setChecked(False)
        self.waysCB.setChecked(False)
        self.relCB.setChecked(False)

    def initUI(self):
        self.layout = QFormLayout()
        self.layout.setContentsMargins(10,10,10,10)

        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        elementsTypeGB = QWidget()
        elementsTypeLayout = QVBoxLayout()
        elementsTypeGB.setLayout(elementsTypeLayout)
        elementsTypeLayout.setContentsMargins(10, 0, 0, 0)
        elementsTypeLayout.setSpacing(0)

        self.nodesCB = QCheckBox(self.tr("&Nodes"))
        elementsTypeLayout.addWidget(self.nodesCB)

        self.waysCB = QCheckBox(self.tr("&Ways"))
        self.waysCB.setChecked(True)
        elementsTypeLayout.addWidget(self.waysCB)

        self.relCB = QCheckBox(self.tr("&Relations"))
        elementsTypeLayout.addWidget(self.relCB)

        self.areasCB = QCheckBox(self.tr("&Areas"))
        self.areasCB.stateChanged.connect(self.__onAreaSelected)
        elementsTypeLayout.addWidget(self.areasCB)

        self.nodesCB.stateChanged.connect(lambda b: self.areasCB.setChecked(False) if b else None)
        self.waysCB.stateChanged.connect(lambda b: self.areasCB.setChecked(False) if b else None)
        self.relCB.stateChanged.connect(lambda b: self.areasCB.setChecked(False) if b else None)

        self.layout.addRow("Elements type:", elementsTypeGB)

        self.locationNameWidget = QLineEdit()
        self.locationNameWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.layout.addRow("Location:", self.locationNameWidget)

        self.filtersWidget = QWidget(self)
        self.filtersLayout = QVBoxLayout()
        self.filtersLayout.setContentsMargins(10,10,0,10)
        self.filtersWidget.setLayout(self.filtersLayout)
        self.layout.addRow("Filters:", None)
        self.layout.addRow(self.filtersWidget)

        polygonButtons = QWidget()
        polygonButtonsLayout = QHBoxLayout()
        polygonButtonsLayout.setSpacing(0)
        polygonButtonsLayout.setContentsMargins(0, 0, 0, 0)
        polygonButtons.setLayout(polygonButtonsLayout)

        self.drawPolButton = QPushButton(QIcon(os.path.join(picturesDir, "polygon.png")), "")
        self.drawPolButton.setFlat(True)
        self.drawPolButton.setCheckable(True)

        polygonButtonsLayout.addWidget(self.drawPolButton)

        self.buttonClearPol = QPushButton(QIcon(os.path.join(picturesDir, "reset.png")), "")
        self.buttonClearPol.setFlat(True)

        polygonButtonsLayout.addWidget(self.buttonClearPol)

        self.layout.addRow("Polygon:", polygonButtons)

        surroundGB = QGroupBox()
        surroundGB.setFlat(True)
        surroundLayout = QVBoxLayout()
        surroundLayout.setContentsMargins(0, 0, 0, 0)

        aroundRB = QRadioButton(self.tr("&Streets around"))
        aroundRB.setObjectName("Around")
        surroundLayout.addWidget(aroundRB)

        adjacentRB = QRadioButton(self.tr("&Adjacent streets"))
        adjacentRB.setObjectName("Adjacent")
        surroundLayout.addWidget(adjacentRB)

        noneRB = QRadioButton(self.tr("&None"))
        noneRB.setObjectName("None")
        noneRB.setChecked(True)
        surroundLayout.addWidget(noneRB)

        surroundGB.setLayout(surroundLayout)

        self.layout.addRow("Surroundings:", surroundGB)

        self.onlyDisconnectedCB = QCheckBox()
        self.onlyDisconnectedCB.setText("Only disconnected ways")

        self.columnSelection = CheckableComboBox("Keys")
        self.columnSelection.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.tableView = QTableView()
        self.tableView.doubleClicked.connect(self.addFilterFromCell)

        self.horizontalHeader = self.tableView.horizontalHeader()
        self.horizontalHeader.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader.setStretchLastSection(True)

        self.verticalHeader = self.tableView.verticalHeader()
        self.verticalHeader.sectionDoubleClicked.connect(self.addFiltersFromRow)

        self.tableView.setMinimumHeight(300)

        tableButtons = QWidget()
        tableButtonsLayout = QHBoxLayout()
        tableButtons.setLayout(tableButtonsLayout)
        tableButtonsLayout.setSpacing(0)
        tableButtonsLayout.setContentsMargins(0,0,0,0)

        buttonTable = QPushButton(QIcon(os.path.join(picturesDir, "reset.png")), "")
        buttonTable.setFlat(True)
        buttonTable.clicked.connect(self.showTable)

        tableButtonsLayout.addWidget(buttonTable)

        buttonMore = QPushButton(QIcon(os.path.join(picturesDir, "showMore.png")), "")
        buttonMore.setFlat(True)
        buttonMore.clicked.connect(self.showMore)

        tableButtonsLayout.addWidget(buttonMore)

        buttonLess = QPushButton(QIcon(os.path.join(picturesDir, "showLess.png")), "")
        buttonLess.setFlat(True)
        buttonLess.clicked.connect(self.showLess)

        tableButtonsLayout.addWidget(buttonLess)

        self.layout.addRow("Disambiguation:", tableButtons)
        self.layout.addRow("", self.onlyDisconnectedCB)
        self.layout.addRow("", self.columnSelection)
        self.layout.addRow(self.tableView)

        self.setLayout(self.layout)

    def getLocationId(self):
        if self.locationNameWidget.text() == "":
            return None
        item = next((x for x in ox.nominatim_request({"q": self.locationNameWidget.text(), 'format': 'json'})
                     if x['osm_type'] != 'node'), None)
        if item is None:
            return item
        id = item['osm_id']
        if item['osm_type'] == 'relation':
            id += 3600000000
        elif item['osm_type'] == 'node':
            id += 2400000000
        return id

    def getType(self):
        return OsmType.getType(self.nodesCB.isChecked(), self.waysCB.isChecked(),
                               self.relCB.isChecked(), self.areasCB.isChecked())

    def onClearPolygon(self, f):
        self.buttonClearPol.clicked.connect(f)

    def onPolygonEnabled(self, fTrue, fFalse):
        self.drawPolButton.toggled.connect(lambda: fTrue() if self.drawPolButton.isChecked() else fFalse())

    def showTable(self):
        query = OverpassQuery()

        switcher = {
            "Adjacent": Surround.ADJACENT,
            "Around": Surround.AROUND,
            "None": Surround.NONE
        }

        selectedSurrounding = [b for b in self.findChildren(QRadioButton) if b.isChecked()][0]
        request = OverpassRequest(switcher.get(selectedSurrounding.objectName()))
        for filterWidget in self.findChildren(FilterWidget):
            request.addFilter(filterWidget.getKey(), filterWidget.getValue(), filterWidget.isExactValueSelected(),
                              filterWidget.isNegateSelected())

        query.addRequest(self.objectName(), request)

        tableDir = os.path.join(tempDir, "table.osm.xml")
        try:
            writeXMLResponse(query.getQL(), tableDir)
        except OverpassRequestException as e:
            logging.error(str(e))
        except OSError:
            logging.error("There was a problem creating the file with the request response.")
        except Exception:
            logging.error(traceback.format_exc())

        jsonResponse = ox.overpass_json_from_file(tableDir)

        self.disconnectedWaysTable = DisconnectedWaysTable(jsonResponse)
        self.similarWaysTable = SimilarWaysTable(jsonResponse)
        self.tableView.setModel(self.similarWaysTable)
        self.tableView.setVisible(True)
        self.tableOptions.setVisible(True)

        for key in self.tableView.model().getAllColumns():
            self.columnSelection.addItem(key, key in self.tableView.model().getSelectedColumns())

        self.columnSelection.setDropdownMenuSignal(
            lambda: self.tableView.model().updateColumns(self.columnSelection.getSelectedItems()))

        self.onlyDisconnectedCB.stateChanged.connect(self.showHideOnlyDisconnected)

    def showHideOnlyDisconnected(self):
        if self.onlyDisconnectedCB.isChecked():
            self.tableView.setModel(self.disconnectedWaysTable)
            self.columnSelection.setEnabled(False)
        else:
            self.tableView.setModel(self.similarWaysTable)
            self.columnSelection.setEnabled(True)

    def showMore(self):
        self.tableView.model().showMore()

    def showLess(self):
        self.tableView.model().showLess()

    def addFilter(self, key="", value="", accuracy=False, negate=False):
        currentKeys = {filter.getKey(): filter for filter in self.findChildren(FilterWidget)}
        if key in currentKeys.keys():
            filter = currentKeys[key]
            logging.warning("Some filters have been modified.")
        else:
            filter = FilterWidget(self.filtersWidget, self.keyValues)
            self.filtersLayout.addWidget(filter)
        filter.setKey(key)
        filter.setValue(value)
        filter.setExactValue(accuracy)
        filter.setNegate(negate)

    def addFilterFromCell(self, signal):
        key = self.tableView.model().headerData(signal.column(), Qt.Horizontal, Qt.DisplayRole)
        value = self.tableView.model().itemData(signal).get(0)
        self.addFilter(key, value, True)

    def addFiltersFromRow(self, index):
        row = self.tableView.model().getDictData(index)
        for k, v in row.items():
            self.addFilter(k, v, True)

    def getSelectedRowNetworkx(self):
        indexes = self.tableView.selectionModel().selectedRows()
        return self.tableView.model().getRowJson(indexes)


class GlobalOverpassSettingUI(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Date:"))

        self.dateEdit = QCalendarWidget()
        self.dateEdit.setMinimumDate(QDate(2012, 9, 13))
        self.dateEdit.setMaximumDate(QDate.currentDate())

        prevIcon = self.dateEdit.findChild(QToolButton, "qt_calendar_prevmonth")
        nextIcon = self.dateEdit.findChild(QToolButton, "qt_calendar_nextmonth")
        prevIcon.setIcon(QIcon(os.path.join(picturesDir, "arrowLeft.png")))
        nextIcon.setIcon(QIcon(os.path.join(picturesDir, "arrowRight.png")))

        self.layout.addWidget(self.dateEdit)

    def getDate(self):
        return self.dateEdit.selectedDate().toPyDate()


class QueryUI(QWidget):

    def __init__(self):
        super().__init__()
        try:
            self.keyValues = getOfficialKeys()
        except RequestException:
            logging.warning(
                "There was a problem with the internet connection. You will not be able to see the existing keys.")
        self.onClearPolygonF = lambda: None
        self.onPolygonEnabledF = lambda: None
        self.onPolygonDisabledF = lambda: None
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.requestAreaWidget = QToolBox()
        self.requestAreaWidget.layout().setSpacing(1)

        self.requestTabs = QTabWidget()
        self.requestTabs.setUsesScrollButtons(True)
        self.requestAreaWidget.addItem(self.requestTabs, "Requests")

        self.requestOps = RequestsOperations(self)
        self.requestAreaWidget.addItem(self.requestOps, "Operations")

        self.generalConfig = GlobalOverpassSettingUI(self)
        self.requestAreaWidget.addItem(self.generalConfig, "General")

        self.layout.addWidget(self.requestAreaWidget)

        self.setLayout(self.layout)

    def currentRequest(self):
        return self.requestTabs.currentIndex()

    def onTabChanged(self, f):
        self.requestTabs.currentChanged.connect(f)

    def onClearPolygon(self, f):
        self.onClearPolygonF = f
        for tab in self.requestTabs.findChildren(RequestWidget):
            tab.onClearPolygon(f)

    def onPolygonEnabled(self, fTrue, fFalse):
        self.onPolygonEnabledF = fTrue
        self.onPolygonDisabledF = fFalse
        for tab in self.requestTabs.findChildren(RequestWidget):
            tab.onPolygonEnabled(fTrue, fFalse)

    def addRequest(self, filters=None):
        requestWidget = RequestWidget(self, self.keyValues)
        setName = OverpassQuery.getUniqueSetName()
        requestWidget.setObjectName(setName)
        requestWidget.onPolygonEnabled(self.onPolygonEnabledF, self.onPolygonDisabledF)
        requestWidget.onClearPolygon(self.onClearPolygonF)
        self.requestTabs.addTab(requestWidget, setName)
        self.requestOps.addRequest(setName)

        if filters is not None:
            for key, value, accuracy, negate in filters:
                requestWidget.addFilter(key, value, accuracy, negate)
        else:
            requestWidget.addFilter()

    def removeRequest(self):
        reply = QMessageBox.question(self, "Remove request",
                                     "Are you sure?\nAll sets containing this one will be deleted if they are no longer valid")
        if reply == QMessageBox.Yes:
            self.requestOps.removeSetAndDependencies(self.requestTabs.currentWidget().objectName())
            self.requestTabs.currentWidget().deleteLater()

    def addFilter(self, key="", value="", accuracy=False, negate=False):
        self.requestTabs.currentWidget().addFilter(key, value, accuracy, negate)

    def requestsCount(self):
        return self.requestTabs.count()

    def getQuery(self):
        query = OverpassQuery(self.requestOps.outputSet())

        query.addDate(self.generalConfig.getDate())

        switcher = {
            "Adjacent": Surround.ADJACENT,
            "Around": Surround.AROUND,
            "None": Surround.NONE
        }

        for requestWidget in self.findChildren(RequestWidget):
            selectedSurrounding = [b for b in requestWidget.findChildren(QRadioButton) if b.isChecked()][0]
            request = OverpassRequest(requestWidget.getType(), switcher.get(selectedSurrounding.objectName()))
            request.setLocationId(requestWidget.getLocationId())
            for filterWidget in requestWidget.findChildren(FilterWidget):
                request.addFilter(filterWidget.getKey(), filterWidget.getValue(), filterWidget.isExactValueSelected(),
                                  filterWidget.isNegateSelected())

            query.addRequest(requestWidget.objectName(), request)

        for name, op in self.requestOps.ops.items():
            query.addSetsOp(name, op)

        return query

    def getSelectedRowNetworkx(self):
        return self.requestTabs.currentWidget().getSelectedRowNetworkx()
