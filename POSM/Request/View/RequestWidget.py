import logging
import os
import traceback

import bs4
import osmnx as ox
from PyQt5.QtCore import Qt, pyqtSlot, QJsonValue
from PyQt5.QtGui import QIcon, QDoubleValidator, QIntValidator
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtWidgets import QWidget, QFormLayout, QVBoxLayout, QCheckBox, QLineEdit, QSizePolicy, QHBoxLayout, \
    QGroupBox, QRadioButton, QTableView, QHeaderView

from Query.Model.OverpassQuery import OverpassQuery
from Request.Model.OverpassRequest import OverpassRequest
from Shared.Exceptions.OverpassExceptions import OverpassRequestException, OsmnxException
from Shared.Utils.SumoUtils import buildHTMLWithNetworkx, writeXMLResponse
from Shared.View.CollapsibleList import CheckableComboBox
from Shared.View.DisambiguationTable import DisconnectedWaysTable, SimilarWaysTable
from Shared.View.HorizontalLine import HorizontalLine
from Shared.View.IconButton import IconButton
from Shared.constants import picturesDir, Surround, tableDir, JS_SCRIPT, OsmType
from Tag.View.FilterWidget import FilterWidget


class RequestWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.polygonSettings = []
        self.webChannel = QWebChannel()
        self.webChannel.registerObject('request', self)
        self.polygonPage = QWebEnginePage()
        self.polygonPage.setWebChannel(self.webChannel)
        self.initUI()

    def __onAreaSelected(self):
        self.nodesCB.setChecked(False)
        self.waysCB.setChecked(False)
        self.relCB.setChecked(False)

    def initUI(self):
        self.layout = QFormLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

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

        self.layout.addRow("ELEMENTS TYPE", elementsTypeGB)
        self.layout.addRow(HorizontalLine(self))

        self.locationNameWidget = QLineEdit()
        self.locationNameWidget.setPlaceholderText("Areas: 'New York', 'Italy'...")
        self.locationNameWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.layout.addRow("LOCATION", self.locationNameWidget)
        self.layout.addRow(HorizontalLine(self))

        filtersButtons = QWidget()
        filtersButtonsLayout = QHBoxLayout()
        filtersButtons.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        filtersButtonsLayout.setAlignment(Qt.AlignRight)
        filtersButtonsLayout.setSpacing(0)
        filtersButtonsLayout.setContentsMargins(0, 0, 0, 0)
        filtersButtons.setLayout(filtersButtonsLayout)

        self.addFilterButton = IconButton(QIcon(os.path.join(picturesDir, "add.png")),
                                          filtersButtons.windowHandle(),
                                          filtersButtons.height())
        self.addFilterButton.setToolTip("Add filter")
        self.addFilterButton.setFlat(True)
        self.addFilterButton.clicked.connect(lambda b: self.addFilter())

        filtersButtonsLayout.addWidget(self.addFilterButton)

        self.layout.addRow("FILTERS", filtersButtons)

        self.filtersWidget = QWidget(self)
        self.filtersLayout = QVBoxLayout()
        self.filtersLayout.setContentsMargins(10, 10, 10, 10)
        self.filtersWidget.setLayout(self.filtersLayout)
        self.layout.addRow(self.filtersWidget)
        self.layout.addRow(HorizontalLine(self))

        polygonButtons = QWidget()
        polygonButtonsLayout = QHBoxLayout()
        polygonButtons.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        polygonButtonsLayout.setAlignment(Qt.AlignRight)
        polygonButtonsLayout.setSpacing(0)
        polygonButtonsLayout.setContentsMargins(0, 0, 0, 0)
        polygonButtons.setLayout(polygonButtonsLayout)

        self.drawPolButton = IconButton(QIcon(os.path.join(picturesDir, "polygon.png")), polygonButtons.windowHandle(),
                                        polygonButtons.height())
        self.drawPolButton.setToolTip("Draw polygon")
        self.drawPolButton.setFlat(True)
        self.drawPolButton.setCheckable(True)
        self.drawPolButton.toggled.connect(self.enableDisablePolygon)

        polygonButtonsLayout.addWidget(self.drawPolButton)

        self.buttonClearPol = IconButton(QIcon(os.path.join(picturesDir, "reset.png")), polygonButtons.windowHandle(),
                                         polygonButtons.height())
        self.buttonClearPol.setToolTip("Remove polygon")
        self.buttonClearPol.setFlat(True)
        self.buttonClearPol.clicked.connect(self.clearPolygon)

        polygonButtonsLayout.addWidget(self.buttonClearPol)

        self.layout.addRow("POLYGON", polygonButtons)
        self.layout.addRow(HorizontalLine(self))

        self.surroundGB = QGroupBox()
        self.surroundGB.setFlat(True)
        surroundLayout = QVBoxLayout()
        surroundLayout.setContentsMargins(0, 0, 0, 0)

        noneRB = QRadioButton(self.tr("&None"))
        noneRB.setObjectName("None")
        noneRB.setChecked(True)
        surroundLayout.addWidget(noneRB)

        adjacentRB = QRadioButton(self.tr("&Adjacent streets"))
        adjacentRB.setObjectName("Adjacent")
        surroundLayout.addWidget(adjacentRB)

        aroundRB = QRadioButton(self.tr("&Streets around"))
        aroundRB.setObjectName("Around")
        surroundLayout.addWidget(aroundRB)

        self.aroundRadiusEdit = QLineEdit("")
        self.aroundRadiusEdit.hide()
        self.aroundRadiusEdit.setPlaceholderText("Radius in meters")
        self.aroundRadiusEdit.setValidator(QIntValidator(0, 10000000, self.surroundGB))
        aroundRB.toggled.connect(lambda b: self.aroundRadiusEdit.show() if b else self.aroundRadiusEdit.hide())
        surroundLayout.addWidget(self.aroundRadiusEdit)

        self.surroundGB.setLayout(surroundLayout)

        self.layout.addRow("SURROUNDINGS", self.surroundGB)
        self.layout.addRow(HorizontalLine(self))

        self.onlyDisconnectedCB = QCheckBox()
        self.onlyDisconnectedCB.setText("Only disconnected ways")

        self.columnSelectionWidget = QWidget()
        self.columnSelectionLayout = QHBoxLayout()
        self.columnSelectionLayout.setContentsMargins(0, 0, 0, 0)
        self.columnSelectionWidget.setLayout(self.columnSelectionLayout)
        self.columnSelection = CheckableComboBox("Keys")
        self.columnSelection.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.columnSelectionLayout.addWidget(self.columnSelection)
        buttonTable = IconButton(QIcon(os.path.join(picturesDir, "reset.png")),
                                 self.columnSelectionWidget.windowHandle(),
                                 self.columnSelectionWidget.height())
        buttonTable.setToolTip("Show table")
        buttonTable.setFlat(True)
        buttonTable.clicked.connect(self.showTable)

        self.columnSelectionLayout.addWidget(buttonTable)

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
        tableButtonsLayout.setAlignment(Qt.AlignRight)
        tableButtons.setLayout(tableButtonsLayout)
        tableButtonsLayout.setSpacing(0)
        tableButtonsLayout.setContentsMargins(0, 0, 0, 0)

        buttonMore = IconButton(QIcon(os.path.join(picturesDir, "showMore.png")), tableButtons.windowHandle(),
                                tableButtons.height())
        buttonMore.setToolTip("Show more")
        buttonMore.setFlat(True)
        buttonMore.clicked.connect(self.showMore)

        tableButtonsLayout.addWidget(buttonMore)

        buttonLess = IconButton(QIcon(os.path.join(picturesDir, "showLess.png")), tableButtons.windowHandle(),
                                tableButtons.height())
        buttonLess.setToolTip("Show less")
        buttonLess.setFlat(True)
        buttonLess.clicked.connect(self.showLess)

        tableButtonsLayout.addWidget(buttonLess)

        self.layout.addRow("DISAMBIGUATION", self.columnSelectionWidget)
        self.layout.addRow("", self.onlyDisconnectedCB)
        self.layout.addRow(self.tableView)
        self.layout.addRow(tableButtons)

        self.setLayout(self.layout)

    def __getLocationId__(self):
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

    def __getType__(self):
        return OsmType.getType(self.nodesCB.isChecked(), self.waysCB.isChecked(),
                               self.relCB.isChecked(), self.areasCB.isChecked())

    def __getSelectedSurrounding__(self):
        switcher = {
            "Adjacent": Surround.ADJACENT,
            "Around": Surround.AROUND,
            "None": Surround.NONE
        }
        selectedSurrounding = [b for b in self.surroundGB.findChildren(QRadioButton) if b.isChecked()][0]
        return switcher.get(selectedSurrounding.objectName())

    @pyqtSlot(QJsonValue)
    def __setPolygons__(self, val):
        self.polygonSettings = []
        for point in val.toArray():
            self.polygonSettings.append([point["lat"].toDouble(), point["lng"].toDouble()])

    def __getPolygon__(self):
        return self.polygonSettings

    def changePage(self, html):
        soup = bs4.BeautifulSoup(html, features="html.parser")
        js = soup.new_tag("script")
        js.string = (JS_SCRIPT % (str(self.polygonSettings), str(self.drawPolButton.isChecked()).lower()))
        soup.append(js)
        soup.head.append(soup.new_tag("script", src="qrc:///qtwebchannel/qwebchannel.js"))

        self.polygonPage.setHtml(str(soup))

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

    def getRequest(self):
        surroundType = self.__getSelectedSurrounding__()
        aroundRadius = 100
        if surroundType == Surround.AROUND and len(self.aroundRadiusEdit.text()) > 0:
            aroundRadius = int(self.aroundRadiusEdit.text())

        request = OverpassRequest(self.__getType__(), surroundType, aroundRadius)
        request.setLocationId(self.__getLocationId__())
        request.addPolygon(self.__getPolygon__())
        for filterWidget in self.filtersWidget.findChildren(FilterWidget):
            request.addFilter(filterWidget.getFilter())
        return request

    def getMap(self):
        return self.polygonPage

    def clearPolygon(self):
        self.polygonPage.runJavaScript("cleanPolygon();", lambda x: logging.debug("LINE"))

    def enableDisablePolygon(self):
        if self.drawPolButton.isChecked():
            self.polygonPage.runJavaScript("enablePolygon();")
        else:
            self.polygonPage.runJavaScript("disablePolygon();")

    def showTable(self):
        query = OverpassQuery(self.objectName())

        switcher = {
            "Adjacent": Surround.ADJACENT,
            "Around": Surround.AROUND,
            "None": Surround.NONE
        }

        selectedSurrounding = [b for b in self.findChildren(QRadioButton) if b.isChecked()][0]
        request = OverpassRequest(self.getType(), switcher.get(selectedSurrounding.objectName()))
        for filterWidget in self.findChildren(FilterWidget):
            request.addFilter(filterWidget.getKey(), filterWidget.getValue(), filterWidget.isExactValueSelected(),
                              filterWidget.isNegateSelected())

        query.addRequest(self.objectName(), request)

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
        if key != "" and key in currentKeys.keys():
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