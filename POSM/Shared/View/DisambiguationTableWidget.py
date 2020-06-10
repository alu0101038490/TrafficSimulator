import logging
import os
import traceback

import osmnx as ox
from PyQt5.QtCore import Qt, QModelIndex, QVariant
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QSizePolicy, QHBoxLayout, QTableView, \
    QCheckBox, QHeaderView, QFormLayout, QComboBox, QPushButton, QListView, QFrame

from Query.Model.OverpassQuery import OverpassQuery
from Shared.Exceptions.OverpassExceptions import OverpassRequestException, OsmnxException
from Shared.Utils.SumoUtils import writeXMLResponse, buildHTMLWithNetworkx
from Shared.View.DisambiguationTable import DisconnectedWaysTable, SimilarWaysTable
from Shared.View.IconButton import IconButton
from Shared.constants import picturesDir, tableDir


class DisambiguationWidget(QWidget):

    def __init__(self, getRequestFunction, setFiltersFunction, parent=None):
        super().__init__(parent)

        self.getRequestFunction = getRequestFunction
        self.setFiltersFunction = setFiltersFunction

        # LAYOUT

        self.layout = QFormLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        # TYPE

        self.onlyDisconnectedCB = QCheckBox()
        self.onlyDisconnectedCB.setText("Only disconnected ways")

        self.columnSelection = QListView()
        self.columnSelection.setSpacing(3)
        self.columnSelection.setAutoFillBackground(True)
        self.columnSelection.setFrameStyle(QFrame.NoFrame)
        self.columnSelection.viewport().setAutoFillBackground(False)
        self.columnSelection.setFlow(QListView.LeftToRight)
        self.columnSelection.setWrapping(True)
        self.columnSelection.setResizeMode(QListView.Adjust)
        self.columnSelectionModel = QStandardItemModel()
        self.columnSelection.setModel(self.columnSelectionModel)

        self.applyButton = QPushButton("Apply")
        self.applyButton.clicked.connect(self.showTable)

        self.tableView = QTableView()
        self.tableView.doubleClicked.connect(self.addFilterFromCell)

        horizontalHeader = self.tableView.horizontalHeader()
        horizontalHeader.setSectionResizeMode(QHeaderView.ResizeToContents)
        horizontalHeader.setStretchLastSection(True)

        verticalHeader = self.tableView.verticalHeader()
        verticalHeader.sectionDoubleClicked.connect(
            lambda i: self.setFiltersFunction(self.setSelection.currentText(), self.tableView.model().getDictData(i)))

        self.tableView.setMinimumHeight(300)

        self.tableButtons = QWidget()
        tableButtonsLayout = QHBoxLayout()
        tableButtonsLayout.setAlignment(Qt.AlignRight)
        self.tableButtons.setLayout(tableButtonsLayout)
        tableButtonsLayout.setSpacing(0)
        tableButtonsLayout.setContentsMargins(0, 0, 0, 0)

        buttonMore = IconButton(QIcon(os.path.join(picturesDir, "showMore.png")), self.tableButtons.windowHandle(),
                                self.tableButtons.height())
        buttonMore.setToolTip("Show more")
        buttonMore.setFlat(True)
        buttonMore.clicked.connect(self.showMore)

        tableButtonsLayout.addWidget(buttonMore)

        buttonLess = IconButton(QIcon(os.path.join(picturesDir, "showLess.png")), self.tableButtons.windowHandle(),
                                self.tableButtons.height())
        buttonLess.setToolTip("Show less")
        buttonLess.setFlat(True)
        buttonLess.clicked.connect(self.showLess)

        tableButtonsLayout.addWidget(buttonLess)

        self.setSelection = QComboBox()
        self.setSelection.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.layout.addRow("SET", self.setSelection)
        self.layout.addRow("TYPE", self.onlyDisconnectedCB)
        self.layout.addRow("KEYS", self.columnSelection)
        self.layout.addRow(self.applyButton)
        self.layout.addRow(self.tableView)
        self.layout.addRow(self.tableButtons)

        self.setLayout(self.layout)

    def showMore(self):
        self.tableView.model().showMore()

    def showLess(self):
        self.tableView.model().showLess()

    def addFilterFromCell(self, signal):
        key = self.tableView.model().headerData(signal.column(), Qt.Horizontal, Qt.DisplayRole)
        value = self.tableView.model().itemData(signal).get(0)
        self.addFilterByValues(key, value, True)

    def showTable(self):
        request = self.getRequestFunction(self.setSelection.currentText())
        if request is not None:
            query = OverpassQuery(request.name)
            query.addRequest(request)

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
            self.showHideOnlyDisconnected()

            for key in self.similarWaysTable.getAllColumns():
                self.columnSelectionModel.beginInsertRows(QModelIndex(), self.columnSelectionModel.rowCount(),
                                                          self.columnSelectionModel.rowCount())
                item = QStandardItem(key)
                self.columnSelectionModel.itemChanged.connect(self.updateColumns)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setData(QVariant(Qt.Checked if key in self.similarWaysTable.getSelectedColumns() else Qt.Unchecked), Qt.CheckStateRole)
                self.columnSelectionModel.appendRow(item)
                self.columnSelectionModel.endInsertRows()

            self.onlyDisconnectedCB.stateChanged.connect(self.showHideOnlyDisconnected)
        else:
            logging.warning("There is no requests. It is not possible to show the table.")

    def updateColumns(self):
        self.disconnectedWaysTable.updateColumns(self.getSelectedKeys())
        self.similarWaysTable.updateColumns(self.getSelectedKeys())

    def getSelectedKeys(self):
        return [self.columnSelectionModel.item(i).text()
                for i in range(self.columnSelectionModel.rowCount())
                if self.columnSelectionModel.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]

    def getSelectedRowNetworkx(self):
        indexes = self.tableView.selectionModel().selectedRows()
        return self.tableView.model().getRowJson(indexes)

    def getHtmlFromSelectedRow(self):
        selectedRows = self.getSelectedRowNetworkx()
        if selectedRows:
            return buildHTMLWithNetworkx(selectedRows)
        else:
            raise RuntimeError("No row is selected")

    def showHideOnlyDisconnected(self):
        if self.onlyDisconnectedCB.isChecked():
            self.tableView.setModel(self.disconnectedWaysTable)
        else:
            self.tableView.setModel(self.similarWaysTable)

    def showTableSelection(self):
        try:
            self.changePage(buildHTMLWithNetworkx(self.getSelectedRowNetworkx()))
        except (OverpassRequestException, OsmnxException) as e:
            logging.error(str(e))
            logging.warning("Before open NETEDIT you must run a query with the row filters applied.")
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given row.")
        except OSError:
            logging.error("There was a problem creating the file with the row selection.")
        except Exception:
            logging.error(traceback.format_exc())
        logging.debug("LINE")

    def addSet(self, setName):
        self.applyButton.setEnabled(True)
        self.setSelection.addItem(setName)

    def removeSet(self, setName):
        for i in range(self.setSelection.count()):
            if self.setSelection.itemText(i) == setName:
                self.setSelection.removeItem(i)
                break
