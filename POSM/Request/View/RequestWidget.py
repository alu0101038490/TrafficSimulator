import logging
import os
import traceback

import bs4
import osmnx as ox
from PyQt5.QtCore import Qt, pyqtSlot, QJsonValue, QUrl
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtWidgets import QWidget, QFormLayout, QVBoxLayout, QCheckBox, QLineEdit, QSizePolicy, QHBoxLayout, \
    QGroupBox, QRadioButton, QTableView, QHeaderView

from Query.Model.OverpassQuery import OverpassQuery
from Request.Model.OverpassRequest import OverpassRequest
from Shared.Exceptions.OverpassExceptions import OverpassRequestException, OsmnxException
from Shared.Utils.SetNameGenerator import SetNameManagement
from Shared.Utils.SumoUtils import buildHTMLWithNetworkx, writeXMLResponse
from Shared.View.CollapsibleList import CheckableComboBox
from Shared.View.DisambiguationTable import DisconnectedWaysTable, SimilarWaysTable
from Shared.View.HorizontalLine import HorizontalLine
from Shared.View.IconButton import IconButton
from Shared.constants import picturesDir, Surround, tableDir, JS_SCRIPT, OsmType, TagComparison, resDir, tempDir
from Tag.View.FilterWidget import FilterWidget


class RequestWidget(QWidget):

    def __init__(self, parent, keyList, request=None):
        super().__init__(parent)

        self.keyList = keyList

        # INITIALIZE POLYGON MANAGEMENT

        self.polygonSettings = []
        self.html = ""
        self.webChannel = QWebChannel()
        self.webChannel.registerObject('request', self)
        self.polygonPage = QWebEnginePage()
        self.polygonPage.setWebChannel(self.webChannel)

        # INITIALIZE UI

        self.layout = self.__generateLayout__()
        self.setLayout(self.layout)

        elementsTypeGB, self.nodesCB, self.waysCB, self.relCB, self.areasCB = self.__generateTypeWidget__()
        self.layout.addRow("ELEMENTS TYPE", elementsTypeGB)
        self.layout.addRow(HorizontalLine(self))

        self.locationNameWidget = self.__generateLocationWidget__()
        self.layout.addRow("LOCATION", self.locationNameWidget)
        self.layout.addRow(HorizontalLine(self))

        filtersButtons, self.filtersWidget, self.filtersLayout = self.__generateFiltersWidget__()
        self.layout.addRow("FILTERS", filtersButtons)
        self.layout.addRow(self.filtersWidget)
        self.layout.addRow(HorizontalLine(self))

        polygonButtons, self.drawPolButton, self.buttonClearPol = self.__generatePolygonWidget__()
        self.layout.addRow("POLYGON", polygonButtons)
        self.layout.addRow(HorizontalLine(self))

        self.surroundGB, self.aroundRadiusEdit = self.__generateSurroundingWidget__()
        self.layout.addRow("SURROUNDINGS", self.surroundGB)
        self.layout.addRow(HorizontalLine(self))

        columnSelectionWidget, self.onlyDisconnectedCB, self.tableView, tableButtons = self.__generateDisambiguationTable__()
        self.layout.addRow("DISAMBIGUATION", columnSelectionWidget)
        self.layout.addRow("", self.onlyDisconnectedCB)
        self.layout.addRow(self.tableView)
        self.layout.addRow(tableButtons)

        # SETTING DATA

        if request is None:
            self.requestName = SetNameManagement.getUniqueSetName()
        else:
            self.__setRequest__(request)

    # UI COMPONENTS

    def __generateLayout__(self):
        layout = QFormLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        layout.setLabelAlignment(Qt.AlignLeft)
        layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        return layout

    def __generateLocationWidget__(self):
        locationNameWidget = QLineEdit()
        locationNameWidget.setPlaceholderText("Areas: 'New York', 'Italy'...")
        locationNameWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return locationNameWidget

    def __generatePolygonWidget__(self):
        polygonButtons = QWidget()
        polygonButtonsLayout = QHBoxLayout()
        polygonButtons.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        polygonButtonsLayout.setAlignment(Qt.AlignRight)
        polygonButtonsLayout.setSpacing(0)
        polygonButtonsLayout.setContentsMargins(0, 0, 0, 0)
        polygonButtons.setLayout(polygonButtonsLayout)

        drawPolButton = IconButton(QIcon(os.path.join(picturesDir, "polygon.png")), polygonButtons.windowHandle(),
                                   polygonButtons.height())
        drawPolButton.setToolTip("Draw polygon")
        drawPolButton.setFlat(True)
        drawPolButton.setCheckable(True)
        drawPolButton.toggled.connect(self.enableDisablePolygon)

        polygonButtonsLayout.addWidget(drawPolButton)

        buttonClearPol = IconButton(QIcon(os.path.join(picturesDir, "reset.png")), polygonButtons.windowHandle(),
                                    polygonButtons.height())
        buttonClearPol.setToolTip("Remove polygon")
        buttonClearPol.setFlat(True)
        buttonClearPol.clicked.connect(self.clearPolygon)

        polygonButtonsLayout.addWidget(buttonClearPol)

        return polygonButtons, drawPolButton, buttonClearPol

    def __generateTypeWidget__(self):
        elementsTypeGB = QWidget()
        elementsTypeLayout = QVBoxLayout()
        elementsTypeGB.setLayout(elementsTypeLayout)
        elementsTypeLayout.setContentsMargins(10, 0, 0, 0)
        elementsTypeLayout.setSpacing(0)

        nodesCB = QCheckBox(self.tr("&Nodes"))
        elementsTypeLayout.addWidget(nodesCB)

        waysCB = QCheckBox(self.tr("&Ways"))
        waysCB.setChecked(True)
        elementsTypeLayout.addWidget(waysCB)

        relCB = QCheckBox(self.tr("&Relations"))
        elementsTypeLayout.addWidget(relCB)

        areasCB = QCheckBox(self.tr("&Areas"))
        areasCB.stateChanged.connect(self.__onAreaSelected__)
        elementsTypeLayout.addWidget(areasCB)

        nodesCB.stateChanged.connect(lambda b: self.areasCB.setChecked(False) if b else None)
        waysCB.stateChanged.connect(lambda b: self.areasCB.setChecked(False) if b else None)
        relCB.stateChanged.connect(lambda b: self.areasCB.setChecked(False) if b else None)

        return elementsTypeGB, nodesCB, waysCB, relCB, areasCB

    def __generateSurroundingWidget__(self):
        surroundGB = QGroupBox()
        surroundGB.setFlat(True)
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

        aroundRadiusEdit = QLineEdit("")
        aroundRadiusEdit.hide()
        aroundRadiusEdit.setPlaceholderText("Radius in meters")
        aroundRadiusEdit.setValidator(QIntValidator(0, 10000000, surroundGB))
        aroundRB.toggled.connect(lambda b: aroundRadiusEdit.show() if b else aroundRadiusEdit.hide())
        surroundLayout.addWidget(aroundRadiusEdit)

        surroundGB.setLayout(surroundLayout)

        return surroundGB, aroundRadiusEdit

    def __generateFiltersWidget__(self):
        filtersButtons = QWidget()
        filtersButtonsLayout = QHBoxLayout()
        filtersButtons.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        filtersButtonsLayout.setAlignment(Qt.AlignRight)
        filtersButtonsLayout.setSpacing(0)
        filtersButtonsLayout.setContentsMargins(0, 0, 0, 0)
        filtersButtons.setLayout(filtersButtonsLayout)

        addFilterButton = IconButton(QIcon(os.path.join(picturesDir, "add.png")),
                                     filtersButtons.windowHandle(),
                                     filtersButtons.height())
        addFilterButton.setToolTip("Add filter")
        addFilterButton.setFlat(True)
        addFilterButton.clicked.connect(lambda b: self.addFilter())

        filtersButtonsLayout.addWidget(addFilterButton)

        filtersWidget = QWidget(self)
        filtersLayout = QVBoxLayout()
        filtersLayout.setContentsMargins(10, 10, 10, 10)
        filtersWidget.setLayout(filtersLayout)

        return filtersButtons, filtersWidget, filtersLayout

    def __generateDisambiguationTable__(self):
        onlyDisconnectedCB = QCheckBox()
        onlyDisconnectedCB.setText("Only disconnected ways")

        columnSelectionWidget = QWidget()
        columnSelectionLayout = QHBoxLayout()
        columnSelectionLayout.setContentsMargins(0, 0, 0, 0)
        columnSelectionWidget.setLayout(columnSelectionLayout)
        columnSelection = CheckableComboBox("Keys")
        columnSelection.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        columnSelectionLayout.addWidget(self.columnSelection)
        buttonTable = IconButton(QIcon(os.path.join(picturesDir, "reset.png")),
                                 columnSelectionWidget.windowHandle(),
                                 columnSelectionWidget.height())
        buttonTable.setToolTip("Show table")
        buttonTable.setFlat(True)
        buttonTable.clicked.connect(self.showTable)

        columnSelectionLayout.addWidget(buttonTable)

        tableView = QTableView()
        tableView.doubleClicked.connect(self.addFilterFromCell)

        horizontalHeader = tableView.horizontalHeader()
        horizontalHeader.setSectionResizeMode(QHeaderView.ResizeToContents)
        horizontalHeader.setStretchLastSection(True)

        verticalHeader = tableView.verticalHeader()
        verticalHeader.sectionDoubleClicked.connect(self.addFiltersFromRow)

        tableView.setMinimumHeight(300)

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

        return columnSelectionWidget, onlyDisconnectedCB, tableView, tableButtons

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

    # ============= DISAMBIGUATION TABLE =============

    def showTable(self):
        query = OverpassQuery(self.getName())
        query.addRequest(self.getRequest())

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

    def getHtmlFromSelectedRow(self):
        selectedRows = self.getSelectedRowNetworkx()
        if selectedRows:
            return buildHTMLWithNetworkx(selectedRows)
        else:
            raise RuntimeError("No row is selected")

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

    def addFilterByValues(self, key="", value="", accuracy=False, negate=False, comparison=TagComparison.EQUAL):
        currentKeys = {filter.getKey(): filter for filter in self.findChildren(FilterWidget)}
        if key != "" and key in currentKeys.keys():
            filter = currentKeys[key]
            logging.warning("Some filters have been modified.")
        else:
            filter = FilterWidget(self.filtersWidget, self.keyList)
            self.filtersLayout.addWidget(filter)
        filter.setKey(key)
        filter.setComparison(comparison)
        filter.setValue(value)
        filter.setExactValue(accuracy)
        filter.setNegate(negate)

    def addFilter(self, filter=None):
        if filter is None:
            self.addFilterByValues()
        else:
            self.addFilterByValues(filter.key, filter.value, filter.isExactValue, filter.isNegated, filter.comparison)

    def addFilterFromCell(self, signal):
        key = self.tableView.model().headerData(signal.column(), Qt.Horizontal, Qt.DisplayRole)
        value = self.tableView.model().itemData(signal).get(0)
        self.addFilterByValues(key, value, True)

    def addFiltersFromRow(self, index):
        row = self.tableView.model().getDictData(index)
        for k, v in row.items():
            self.addFilterByValues(k, v, True)

    def getSelectedRowNetworkx(self):
        indexes = self.tableView.selectionModel().selectedRows()
        return self.tableView.model().getRowJson(indexes)

    def __del__(self):
        SetNameManagement.releaseName(self.requestName)

    # REQUEST GETTERS

    def __getLocationName__(self):
        return self.locationNameWidget.text()

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

    def getAroundRadius(self):
        return int(self.aroundRadiusEdit.text()) if len(self.aroundRadiusEdit.text()) > 0 else 100

    def getRequest(self):
        request = OverpassRequest(self.__getType__(),
                                  self.__getSelectedSurrounding__(),
                                  self.requestName,
                                  self.getAroundRadius())
        request.setLocationName(self.__getLocationName__())
        request.addPolygon(self.__getPolygon__())
        for filterWidget in self.filtersWidget.findChildren(FilterWidget):
            request.addFilter(filterWidget.getFilter())
        return request

    def getName(self):
        return self.requestName

    def getMap(self):
        return self.polygonPage

    # REQUEST SETTERS

    def __setLocationName__(self, locationName):
        self.locationNameWidget.setText(locationName)

    def __setType__(self, requestType):
        typeConfig = OsmType.getConfig(requestType)
        self.waysCB.setChecked(typeConfig["way"])
        self.nodesCB.setChecked(typeConfig["node"])
        self.relCB.setChecked(typeConfig["rel"])
        self.areasCB.setChecked(typeConfig["area"])

    def __setSelectedSurrounding__(self, surroundValue):
        if surroundValue == Surround.ADJACENT:
            self.surroundGB.findChild(QRadioButton, "Adjacent").setChecked(True)
        elif surroundValue == Surround.AROUND:
            self.surroundGB.findChild(QRadioButton, "Around").setChecked(True)
        elif surroundValue == Surround.NONE:
            self.surroundGB.findChild(QRadioButton, "None").setChecked(True)

    def changePolygon(self, coors):
        self.polygonSettings = coors
        if self.html != "":
            self.changePage(self.html)

    def setAroundRadius(self, radius):
        return self.aroundRadiusEdit.setText(str(radius))

    def __setRequest__(self, request):
        self.requestName = request.name
        self.__setType__(request.type)
        self.setAroundRadius(request.aroundRadius)
        self.__setSelectedSurrounding__(request.surrounding)
        for filterWidget in self.filtersWidget.findChildren(FilterWidget):
            filterWidget.deleteLater()
        for filter in request.filters:
            self.addFilter(filter)
        self.__setLocationName__(request.locationName)
        self.changePolygon(request.polygon)

    def changePage(self, html):
        self.html = html
        soup = bs4.BeautifulSoup(html, features="html.parser")
        js = soup.new_tag("script")
        js.string = (JS_SCRIPT % (str(self.polygonSettings), str(self.drawPolButton.isChecked()).lower()))
        soup.append(js)
        soup.head.append(soup.new_tag("script", src="qrc:///qtwebchannel/qwebchannel.js"))
        htmlFileName = os.path.join(tempDir, "{}.html".format(self.requestName))
        with open(htmlFileName, "w+") as f:
            f.write(str(soup))

        self.polygonPage.load(QUrl.fromLocalFile(htmlFileName))

    # SIGNALS

    def __onAreaSelected__(self):
        self.nodesCB.setChecked(False)
        self.waysCB.setChecked(False)
        self.relCB.setChecked(False)

    def clearPolygon(self):
        self.polygonPage.runJavaScript("cleanPolygon();", lambda x: logging.debug("LINE"))

    def enableDisablePolygon(self):
        if self.drawPolButton.isChecked():
            self.polygonPage.runJavaScript("enablePolygon();")
        else:
            self.polygonPage.runJavaScript("disablePolygon();")
