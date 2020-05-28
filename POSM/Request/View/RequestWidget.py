import logging
import os

import bs4
from PyQt5.QtCore import Qt, pyqtSlot, QJsonValue, QUrl, QRegularExpression
from PyQt5.QtGui import QIcon, QIntValidator, QRegularExpressionValidator
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtWidgets import QWidget, QFormLayout, QVBoxLayout, QCheckBox, QLineEdit, QSizePolicy, QHBoxLayout, \
    QGroupBox, QRadioButton, QMenu, QAction

from Request.Model.OverpassRequest import OverpassRequest
from Shared.Utils.SetNameGenerator import SetNameManagement
from Shared.View.HorizontalLine import HorizontalLine
from Shared.View.IconButton import IconButton
from Shared.View.VariableInputList import VariableInputList
from Shared.View.WidgetsFactory import WidgetFactory
from Shared.constants import picturesDir, Surround, JS_SCRIPT, OsmType, TagComparison, tempDir
from Tag.View.FilterWidget import FilterWidget


class RequestWidget(QWidget):

    def __init__(self, parent, keyList, request=None):
        super().__init__(parent)

        self.keyList = keyList

        # INITIALIZE POLYGON MANAGEMENT

        self.polygonSettings = []
        self.polygonActivated = False
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

        polygonButtons = self.__generatePolygonWidget__()
        self.layout.addRow("POLYGON", polygonButtons)
        self.layout.addRow(HorizontalLine(self))

        self.surroundGB, self.aroundRadiusEdit = self.__generateSurroundingWidget__()
        self.layout.addRow("SURROUNDINGS", self.surroundGB)
        self.layout.addRow(HorizontalLine(self))

        self.idsWidget = self.__generateIdsWidget__()
        self.layout.addRow("IDS", self.idsWidget)

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
        return WidgetFactory.buildIconButtonGroup([
            {"image": "polygon.png", "tooltip": "Draw polygon", "checkable": True, "action": self.enableDisablePolygon},
            {"image": "reset.png", "tooltip": "Remove polygon", "checkable": False, "action": self.clearPolygon}
        ])

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
        addFilterButton.setStyleSheet("""QPushButton::menu-indicator{image: none;}""")

        filtersMenu = QMenu()

        equalAct = QAction('Equal', self)
        equalAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.EQUAL))
        filtersMenu.addAction(equalAct)

        maxAct = QAction('Maximum', self)
        maxAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.AT_MOST))
        filtersMenu.addAction(maxAct)

        minAct = QAction('Minimum', self)
        minAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.AT_LEAST))
        filtersMenu.addAction(minAct)

        containAllAct = QAction('Contain all', self)
        containAllAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.CONTAIN_ALL))
        filtersMenu.addAction(containAllAct)

        oneOfAct = QAction('Is one of', self)
        oneOfAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.IS_ONE_OF))
        filtersMenu.addAction(oneOfAct)

        hasKeyAct = QAction('Has key', self)
        hasKeyAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.HAS_KEY))
        filtersMenu.addAction(hasKeyAct)

        hasOneKeyAct = QAction('Has one key', self)
        hasOneKeyAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.HAS_ONE_KEY))
        filtersMenu.addAction(hasOneKeyAct)

        hasNotKeyAct = QAction('Has not key', self)
        hasNotKeyAct.triggered.connect(lambda: self.addFilterByComparison(comparison=TagComparison.HAS_NOT_KEY))
        filtersMenu.addAction(hasNotKeyAct)

        addFilterButton.setMenu(filtersMenu)

        filtersButtonsLayout.addWidget(addFilterButton)

        filtersWidget = QWidget(self)
        filtersLayout = QVBoxLayout()
        filtersLayout.setContentsMargins(10, 10, 10, 10)
        filtersWidget.setLayout(filtersLayout)

        return filtersButtons, filtersWidget, filtersLayout

    def __generateIdsWidget__(self):
        return VariableInputList(0, "Numeric id", QRegularExpressionValidator(QRegularExpression("^[0-9]+$")))

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
        request.setIds(self.__getIds__())
        for filterWidget in self.filtersWidget.findChildren(FilterWidget):
            request.addFilter(filterWidget.getFilter())
        return request

    def getName(self):
        return self.requestName

    def getMap(self):
        return self.polygonPage

    def __getIds__(self):
        return self.idsWidget.getItems()

    # REQUEST SETTERS

    def addFilterByComparison(self, comparison):
        newFilterWidget = FilterWidget(self.filtersWidget, comparison, self.keyList)
        self.filtersLayout.addWidget(newFilterWidget)

    def addFilter(self, filter):
        currentKeys = {filter.getKey(): filter for filter in self.findChildren(FilterWidget)}
        if filter.key != "" and filter.key in currentKeys.keys():
            logging.warning("The key {} is used more than once in the set {}.".format(filter.key, self.getName()))
        newFilterWidget = FilterWidget(self.filtersWidget, filter.comparison, self.keyList)
        self.filtersLayout.addWidget(newFilterWidget)
        newFilterWidget.setFilter(filter)

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
        self.setIds(request.ids)
        self.changePolygon(request.polygon)

    def changePage(self, html):
        self.html = html
        soup = bs4.BeautifulSoup(html, features="html.parser")
        js = soup.new_tag("script")
        js.string = (JS_SCRIPT % (str(self.polygonSettings), str(self.polygonActivated).lower()))
        soup.append(js)
        soup.head.append(soup.new_tag("script", src="qrc:///qtwebchannel/qwebchannel.js"))
        htmlFileName = os.path.join(tempDir, "{}.html".format(self.requestName))
        with open(htmlFileName, "w+") as f:
            f.write(str(soup))

        self.polygonPage.load(QUrl.fromLocalFile(htmlFileName))

    def setIds(self, ids=None):
        self.idsWidget.setItems(ids)

    def addId(self, newId=0):
        self.idsWidget.addItem(newId)

    def __del__(self):
        SetNameManagement.releaseName(self.requestName)

    # SIGNALS

    def __onAreaSelected__(self):
        self.nodesCB.setChecked(False)
        self.waysCB.setChecked(False)
        self.relCB.setChecked(False)

    def clearPolygon(self):
        self.polygonPage.runJavaScript("cleanPolygon();", lambda x: logging.debug("LINE"))

    def enableDisablePolygon(self, checked):
        self.polygonActivated = checked
        self.polygonPage.runJavaScript("enablePolygon();" if checked else "disablePolygon();")
