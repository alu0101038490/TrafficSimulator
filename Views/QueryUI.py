import os

import osmnx as ox
from PyQt5.QtCore import Qt, QVariant, QModelIndex, QAbstractTableModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, \
    QSizePolicy, QComboBox, QCheckBox, QGroupBox, QRadioButton, QFrame, QTabWidget, QLabel, QTableView, QHeaderView, \
    QPushButton, QListView, QListWidget, QMessageBox

from Models.OverpassQuery import OverpassQuery, Surround, OverpassRequest, OverpassUnion, OverpassIntersection, \
    OverpassDiff
from Utils.SumoUtils import tempDir, writeXMLResponse
from Utils.TaginfoUtils import getOfficialKeys
from Views.CollapsibleList import CheckableComboBox
from Views.DisambiguationTable import SimilarWaysTable, DisconnectedWaysTable

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

    def getNameByIndex(self, i):
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
        self.ops = {}

    def initUI(self):
        self.layout = QVBoxLayout()

        self.layout.addWidget(QLabel("Sets"))

        horizontalSets = QWidget()
        horizontalSets.setLayout(QHBoxLayout())
        horizontalSets.layout().setSpacing(0)

        self.requestList = QListView()
        self.model = QStandardItemModel()
        self.requestList.setModel(self.model)

        self.requestList2 = QListView()
        self.model2 = QStandardItemModel()
        self.requestList2.setModel(self.model2)

        horizontalSets.layout().addWidget(self.requestList)
        horizontalSets.layout().addWidget(self.requestList2)

        self.layout.addWidget(horizontalSets)

        self.layout.addWidget(QLabel("Operation"))

        self.operationSelection = QGroupBox()
        self.operationSelection.setLayout(QHBoxLayout())

        self.buttonIntersection = QRadioButton("Intersection")
        self.operationSelection.layout().addWidget(self.buttonIntersection)
        self.buttonIntersection.clicked.connect(self.__setsIntersection)
        self.buttonIntersection.click()

        self.buttonUnion = QRadioButton("Union")
        self.operationSelection.layout().addWidget(self.buttonUnion)
        self.buttonUnion.clicked.connect(self.__setsUnion)

        self.buttonDiff = QRadioButton("Difference")
        self.operationSelection.layout().addWidget(self.buttonDiff)
        self.buttonDiff.clicked.connect(self.__setsDiff)

        self.layout.addWidget(self.operationSelection)

        self.buttonApply = QPushButton("Apply")
        self.buttonApply.clicked.connect(self.__applyOp)
        self.operationSelection.layout().addWidget(self.buttonApply)
        self.layout.addWidget(self.buttonApply)

        self.layout.addWidget(QLabel("Resulting sets"))

        self.resultingSets = QTableView()
        self.resultingSets.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resultingSets.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.resultingSets.setModel(OperationsTableModel())
        self.layout.addWidget(self.resultingSets)

        self.layout.addWidget(QLabel("Output set"))

        self.outputSetSelection = QComboBox()
        self.layout.addWidget(self.outputSetSelection)

        self.setLayout(self.layout)

    def getOps(self):
        return self.ops

    def __applyOp(self):
        sets = [self.model.item(i).text() for i in range(self.model.rowCount()) if
                self.model.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]
        if self.buttonUnion.isChecked():
            if len(sets) > 1:
                setName = OverpassQuery.getSetName()
                self.ops[setName] = OverpassUnion()
                self.ops[setName].addSets(sets)
                self.resultingSets.model().addOp(setName, self.ops[setName])
                self.addRequest(setName)
                self.cleanRequestList()
        elif self.buttonIntersection.isChecked():
            if len(sets) > 1:
                setName = OverpassQuery.getSetName()
                self.ops[setName] = OverpassIntersection()
                self.ops[setName].addSets(sets)
                self.resultingSets.model().addOp(setName, self.ops[setName])
                self.addRequest(setName)
                self.cleanRequestList()
        elif self.buttonDiff.isChecked():
            sets2 = [self.model2.item(i).text() for i in range(self.model2.rowCount()) if
                     self.model2.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]
            if len(sets) == 1 and len(sets2) > 0:
                setName = OverpassQuery.getSetName()
                self.ops[setName] = OverpassDiff(sets[0])
                self.ops[setName].addSets(sets)
                self.resultingSets.model().addOp(setName, self.ops[setName])
                self.addRequest(setName)
                self.cleanRequestList()

    def __setsDiff(self):
        self.requestList2.setEnabled(True)

    def __setsUnion(self):
        self.requestList2.setEnabled(False)

    def __setsIntersection(self):
        self.requestList2.setEnabled(False)

    def addRequest(self, name):
        self.model.beginInsertRows(QModelIndex(), self.model.rowCount(), self.model.rowCount())
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
        self.model.appendRow(item)
        self.model.endInsertRows()

        self.model2.beginInsertRows(QModelIndex(), self.model2.rowCount(), self.model2.rowCount())
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
        self.model2.appendRow(item)
        self.model2.endInsertRows()

        self.outputSetSelection.addItem(name)

    def removeRequest(self, i):
        self.model.beginRemoveRows(QModelIndex(), i, i)
        self.model.removeRow(i)
        self.model.endInsertRows()

        self.model2.beginRemoveRows(QModelIndex(), i, i)
        self.model2.removeRow(i)
        self.model2.endInsertRows()

        self.outputSetSelection.removeItem(i)

    def removeByName(self, setName):
        removeList = [setName]

        for set in removeList:
            removeList.extend([i for i in self.removeRecursively(set) if i not in removeList])

    def removeRecursively(self, setName):
        result = []
        for opName in self.ops.keys():
            self.ops[opName].removeSet(setName)
            if not self.ops[opName].isValid():
                result.append(opName)

        for i in range(self.model.rowCount()):
            if self.model.item(i).text() == setName:
                self.removeRequest(i)
                break

        if setName in self.ops.keys():
            self.resultingSets.model().removeOp(setName)
            del self.ops[setName]

        return result

    def cleanRequestList(self):
        for i in range(self.model.rowCount()):
            self.model.item(i).setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
            self.model2.item(i).setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace and self.resultingSets.hasFocus():

            reply = QMessageBox.question(self, "Remove request operation",
                                         "Are you sure?\nAll sets containing this one will be deleted if they are no longer valid")
            if reply == QMessageBox.Yes:
                select = self.resultingSets.selectionModel()
                while len(select.selectedRows()) > 0:
                    self.removeByName(self.resultingSets.model().getNameByIndex(select.selectedRows()[0].row()))

        event.accept()


class FilterWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        topWidget = QWidget()
        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        topWidget.setLayout(topLayout)

        keyLabel = QLabel("Key:")
        keyLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        topLayout.addWidget(keyLabel)

        self.removeCB = QCheckBox()
        topLayout.addWidget(self.removeCB)

        self.layout.addWidget(topWidget)

        self.keyInput = QComboBox()
        self.keyInput.setEditable(True)

        self.keyInput.addItems(self.keyValues)

        self.layout.addWidget(self.keyInput)

        valueEdition = QWidget()
        valueEdition.setLayout(QHBoxLayout())
        valueEdition.layout().setContentsMargins(0, 0, 0, 0)

        self.valueInput = QComboBox()
        self.valueInput.setEditable(True)
        valueEdition.layout().addWidget(self.valueInput)

        self.checkboxAccuracy = QCheckBox()
        self.checkboxAccuracy.setText("Exact Value")
        valueEdition.layout().addWidget(self.checkboxAccuracy)

        self.layout.addWidget(QLabel("Value:"))
        self.layout.addWidget(valueEdition)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.setLayout(self.layout)

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

    def isSelectedToDelete(self):
        return self.removeCB.isChecked()


class RequestWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(QLabel("Filters:"))

        self.filtersWidget = QWidget(self)
        self.filtersLayout = QVBoxLayout()
        self.filtersWidget.setLayout(self.filtersLayout)
        self.layout.addWidget(self.filtersWidget)

        self.addFilter()

        self.layout.addWidget(QLabel("Surroundings:"))

        surroundGB = QGroupBox()
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

        self.layout.addWidget(surroundGB)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.tableOptions = QWidget()
        self.tableOptions.setVisible(False)
        tableOptionsLayout = QHBoxLayout()
        self.tableOptions.setLayout(tableOptionsLayout)
        self.layout.addWidget(self.tableOptions)

        self.onlyDisconnectedCB = QCheckBox()
        self.onlyDisconnectedCB.setText("Only disconnected ways")
        tableOptionsLayout.addWidget(self.onlyDisconnectedCB)

        self.layout.addWidget(QLabel("Disambiguation table:"))

        self.columnSelection = CheckableComboBox("Keys")
        self.columnSelection.setVisible(False)
        tableOptionsLayout.addWidget(self.columnSelection)

        self.tableView = QTableView()
        self.tableView.doubleClicked.connect(self.addFilterFromCell)

        self.horizontalHeader = self.tableView.horizontalHeader()
        self.horizontalHeader.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader.setStretchLastSection(True)

        self.verticalHeader = self.tableView.verticalHeader()
        self.verticalHeader.sectionDoubleClicked.connect(self.addFiltersFromRow)

        self.tableView.setVisible(False)
        self.tableView.setMinimumHeight(300)
        self.layout.addWidget(self.tableView)

        tableButtons = QWidget()
        tableButtonsLayout = QHBoxLayout()
        tableButtons.setLayout(tableButtonsLayout)

        buttonTable = QPushButton()
        buttonTable.setText("Update table")
        buttonTable.clicked.connect(self.showTable)

        tableButtonsLayout.addWidget(buttonTable)

        buttonMore = QPushButton()
        buttonMore.setText("Show more")
        buttonMore.clicked.connect(self.showMore)

        tableButtonsLayout.addWidget(buttonMore)

        buttonLess = QPushButton()
        buttonLess.setText("Show less")
        buttonLess.clicked.connect(self.showLess)

        tableButtonsLayout.addWidget(buttonLess)

        self.layout.addWidget(tableButtons)

        self.setLayout(self.layout)

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
            request.addFilter(filterWidget.getKey(), filterWidget.getValue(), filterWidget.isExactValueSelected())

        query.addRequest(self.objectName(), request)

        tableDir = os.path.join(tempDir, "table.osm.xml")
        writeXMLResponse(query.getQL(), tableDir)

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

    def addFilter(self, key="", value="", accuracy=False):
        filter = FilterWidget(self.filtersWidget, self.keyValues)
        filter.setKey(key)
        filter.setValue(value)
        filter.setExactValue(accuracy)
        self.filtersLayout.addWidget(filter)

    def addFilterFromCell(self, signal):
        key = self.tableView.model().headerData(signal.column(), Qt.Horizontal, Qt.DisplayRole)
        value = self.tableView.model().itemData(signal).get(0)
        self.addFilter(key, value, True)

    def addFiltersFromRow(self, index):
        row = self.tableView.model().getDictData(index)
        currentKeys = {filter.getKey(): filter for filter in self.findChildren(FilterWidget)}
        for k, v in row.items():
            if k in currentKeys.keys():
                currentKeys[k].setValue(v)
            else:
                self.addFilter(k, v, True)

    def removeFilters(self):
        for widget in self.filtersWidget.findChildren(FilterWidget):
            if (widget.isSelectedToDelete()):
                widget.deleteLater()

    def getSelectedRowNetworkx(self):
        indexes = self.tableView.selectionModel().selectedRows()
        return self.tableView.model().getRowJson(indexes)


class QueryUI(QWidget):

    def __init__(self):
        super().__init__()
        self.keyValues = getOfficialKeys()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        self.requestsArea = QScrollArea()
        self.requestsArea.setWidgetResizable(True)

        self.requestAreaWidget = QWidget()
        self.requestAreaWidget.setLayout(QVBoxLayout())

        self.requestTabs = QTabWidget()
        self.requestAreaWidget.layout().addWidget(self.requestTabs)

        self.requestOps = RequestsOperations(self)
        self.requestOps.hide()
        self.requestAreaWidget.layout().addWidget(self.requestOps)

        self.addRequest()

        self.requestsArea.setWidget(self.requestAreaWidget)
        self.layout.addWidget(self.requestsArea)

        self.setLayout(self.layout)

    def addRequest(self):
        requestWidget = RequestWidget(self, self.keyValues)
        setName = OverpassQuery.getSetName()
        requestWidget.setObjectName(setName)
        self.requestTabs.addTab(requestWidget, setName)
        self.requestOps.addRequest(setName)

    def showHideRequestOperation(self):
        if self.requestOps.isHidden():
            self.requestOps.show()
        else:
            self.requestOps.hide()

    def showHideRequests(self):
        if self.requestTabs.isHidden():
            self.requestTabs.show()
        else:
            self.requestTabs.hide()

    def removeRequest(self):
        reply = QMessageBox.question(self, "Remove request",
                                     "Are you sure?\nAll sets containing this one will be deleted if they are no longer valid")
        if reply == QMessageBox.Yes:
            self.requestOps.removeByName(self.requestTabs.currentWidget().objectName())
            self.requestTabs.currentWidget().deleteLater()

    def addFilter(self):
        self.requestTabs.currentWidget().addFilter()

    def removeFilter(self):
        self.requestTabs.currentWidget().removeFilters()

    def getQuery(self):
        query = OverpassQuery()

        switcher = {
            "Adjacent": Surround.ADJACENT,
            "Around": Surround.AROUND,
            "None": Surround.NONE
        }

        for requestWidget in self.findChildren(RequestWidget):
            selectedSurrounding = [b for b in requestWidget.findChildren(QRadioButton) if b.isChecked()][0]
            request = OverpassRequest(switcher.get(selectedSurrounding.objectName()))
            for filterWidget in requestWidget.findChildren(FilterWidget):
                request.addFilter(filterWidget.getKey(), filterWidget.getValue(), filterWidget.isExactValueSelected())

            query.addRequest(requestWidget.objectName(), request)

        for name, op in self.requestOps.getOps():
            query.addSetsOp(name, op)

        return query

    def getSelectedRowNetworkx(self):
        return self.requestTabs.currentWidget().getSelectedRowNetworkx()
