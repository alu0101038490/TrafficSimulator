import os

import osmnx as ox
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, \
    QSizePolicy, QComboBox, QCheckBox, QGroupBox, QRadioButton, QFrame, QTabWidget, QLabel, QTableView, QHeaderView, \
    QPushButton

from Models.OverpassQuery import OverpassQuery, Surround, OverpassRequest
from Utils.GenericUtils import nextString
from Utils.SumoUtils import tempDir, writeXMLResponse
from Utils.TaginfoUtils import getOfficialKeys
from Views.CollapsibleList import CheckableComboBox


class DisambiguationTable(QAbstractTableModel):

    def __init__(self, data):
        QAbstractTableModel.__init__(self)

        self.data = data
        self.allKeys = frozenset([])
        for i in data:
            self.allKeys |= frozenset(i["tags"].keys())

        self.headerItems = list(frozenset(["highway", "name", "maxspeed", "ref", "lanes", "oneway"]) & self.allKeys)

        self.updateAlt()
        self.rowCount = min(5, len(self.alt)) if self.alt else 0

    def updateAlt(self):
        self.alt = []
        for i in self.data:
            reducedData = {k:i["tags"].get(k) for k in self.headerItems}
            coincidence = [i for i in range(len(self.alt)) if self.alt[i][0] == reducedData]
            if len(coincidence) != 0:
                self.alt[coincidence[0]] = (self.alt[coincidence[0]][0], self.alt[coincidence[0]][1] + 1)
            else:
                self.alt.append((reducedData, 1))

        self.alt = sorted(self.alt, key=lambda x: x[1], reverse=True)

    def updateColumns(self, keys):
        keySet = frozenset(keys)
        if keySet != frozenset(self.headerItems):
            self.beginResetModel()
            self.headerItems = list(keySet)
            self.updateAlt()
            self.rowCount = max(self.rowCount, len(self.alt)) if self.alt else 0
            self.endResetModel()

    '''
    def addColumn(self, keys):
        acceptedKeys = [k for k in keys if k in self.allKeys and k not in self.headerItems]
        if len(acceptedKeys) > 0:
            self.beginInsertColumns(QModelIndex(), len(self.headerItems), len(self.headerItems) + len(acceptedKeys) - 1)
            self.headerItems += acceptedKeys
            self.updateAlt()
            self.endRemoveColumns()

    def removeColumnByKey(self, key):
        if key in self.headerItems:
            self.removeColumn(self.headerItems.index(key))
            self.updateAlt()
    '''

    def getAllColumns(self):
        return self.allKeys

    def getSelectedColumns(self):
        return self.headerItems

    def getDictData(self, index):
        return {k: self.alt[index][0].get(k) for k in self.headerItems}

    def showMore(self):
        newRowCount = min(self.rowCount + 5, len(self.alt)) if self.alt else 0
        if newRowCount != self.rowCount:
            self.beginInsertRows(QModelIndex(), self.rowCount, newRowCount - 1)
            self.rowCount = newRowCount
            self.endInsertRows()

    def showLess(self):
        newRowCount = max(self.rowCount - 5, 2) if self.alt else 0
        if newRowCount != self.rowCount:
            self.beginRemoveRows(QModelIndex(), newRowCount, self.rowCount - 1)
            self.rowCount = newRowCount
            self.endRemoveRows()

    def rowCount(self, parent=QModelIndex(), **kwargs):
        return self.rowCount

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
            return self.alt[row][0].get(self.headerItems[column])
        elif role == Qt.BackgroundRole:
            return QColor(Qt.white)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight

        return None


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
        self.layout.setContentsMargins(0,0,0,0)

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

        self.layout.addWidget(QLabel("Disambiguation table:"))

        self.columnSelection = CheckableComboBox("Keys")
        self.columnSelection.setVisible(False)
        self.layout.addWidget(self.columnSelection)

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

        tableData = [i for i in jsonResponse["elements"] if i["type"] == "way"]
        self.tableView.setModel(DisambiguationTable(tableData))
        self.tableView.setVisible(True)
        self.columnSelection.setVisible(True)

        for key in self.tableView.model().getAllColumns():
            self.columnSelection.addItem(key, key in self.tableView.model().getSelectedColumns())

        self.columnSelection.setDropdownMenuSignal(lambda: self.tableView.model().updateColumns(self.columnSelection.getSelectedItems()))

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


class QueryUI(QWidget):

    def __init__(self):
        super().__init__()
        self.keyValues = getOfficialKeys()
        self.lastRequestName = "a"
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        requestsArea = QScrollArea()
        requestsArea.setWidgetResizable(True)

        self.requestTabs = QTabWidget()
        self.addRequest()
        requestsArea.setWidget(self.requestTabs)

        requestsArea.setMinimumWidth(self.requestTabs.minimumWidth())
        self.layout.addWidget(requestsArea)

        self.setLayout(self.layout)

    def addRequest(self):
        requestWidget = RequestWidget(self, self.keyValues)
        requestWidget.setObjectName(self.lastRequestName)
        self.requestTabs.addTab(requestWidget, self.lastRequestName)
        self.lastRequestName = nextString(self.lastRequestName)

    def removeRequest(self):
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

        return query
