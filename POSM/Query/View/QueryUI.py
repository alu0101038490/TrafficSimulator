import logging
import os
from datetime import datetime

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QTabWidget, QToolBox, QAbstractButton
from requests import RequestException

from Operation.Model.OverpassOperations import OverpassDiff
from Operation.View.RequestsOperations import RequestsOperations
from Query.Model.OverpassQuery import OverpassQuery
from Query.View.GlobalOverpassSettingUI import GlobalOverpassSettingUI
from Request.Model.OverpassRequest import OverpassRequest
from Request.View.RequestWidget import RequestWidget
from Shared.Utils.SetNameGenerator import SetNameManagement
from Shared.Utils.TaginfoUtils import getOfficialKeys
from Shared.View.DisambiguationTableWidget import DisambiguationWidget
from Shared.constants import EMPTY_HTML, picturesDir, OsmType, Surround


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
        self.currentHtml = EMPTY_HTML
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.requestAreaWidget = QToolBox()
        self.requestAreaWidget.layout().setSpacing(1)

        self.requestTabs = QTabWidget()
        self.requestTabs.setUsesScrollButtons(True)
        self.requestTabs.currentChanged.connect(self.__updateTabSizes__)
        self.requestAreaWidget.addItem(self.requestTabs, "Requests")

        self.requestOps = RequestsOperations(self)
        self.requestAreaWidget.addItem(self.requestOps, "Operations")

        self.generalConfig = GlobalOverpassSettingUI(self)
        self.requestAreaWidget.addItem(self.generalConfig, "General")

        self.disambiguationWidget = DisambiguationWidget(self.__getRequestByName__, self.__applyTableRow__, self)
        self.requestAreaWidget.addItem(self.disambiguationWidget, "Disambiguation")

        self.headers = self.requestAreaWidget.findChildren(QAbstractButton, "qt_toolbox_toolboxbutton")
        self.requestAreaWidget.currentChanged.connect(self.__onToolTabChanged__)
        self.headers[0].setIcon(QIcon(os.path.join(picturesDir, "arrowUp.png")))
        for i in range(1, len(self.headers)):
            self.headers[i].setIcon(QIcon(os.path.join(picturesDir, "arrowDown.png")))

        self.layout.addWidget(self.requestAreaWidget)

        self.setLayout(self.layout)

    def __getRequestByName__(self, requestName):
        for requestWidget in self.findChildren(RequestWidget):
            if requestWidget.getName() == requestName:
                return requestWidget.getRequest()
        return None

    def __applyTableRow__(self, name, data):
        filters, ids = data
        for requestWidget in self.findChildren(RequestWidget):
            if requestWidget.getName() == name:
                for newFilter in filters:
                    requestWidget.addFilter(newFilter)
                break

        if len(ids) > 0:
            idsRequestName = SetNameManagement.getUniqueSetName()
            request = OverpassRequest(OsmType.WAYS, Surround.NONE, idsRequestName)
            request.setIds(ids)
            self.addRequest(request)

            differenceOpName = SetNameManagement.getUniqueSetName()
            self.requestOps.addOp(OverpassDiff(name, differenceOpName), [idsRequestName])
            self.requestOps.setOutputSet(differenceOpName)

        logging.info("Configuration from the table row has been applied.")

    def __onToolTabChanged__(self, i):
        for h in range(len(self.headers)):
            if h == i:
                self.headers[h].setIcon(QIcon(os.path.join(picturesDir, "arrowUp.png")))
            else:
                self.headers[h].setIcon(QIcon(os.path.join(picturesDir, "arrowDown.png")))

    def __updateTabSizes__(self, index):
        for i in range(self.requestTabs.count()):
            if i != index:
                self.requestTabs.widget(i).setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        if index >= 0:
            self.requestTabs.widget(index).setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.requestTabs.widget(index).resize(self.requestTabs.widget(index).minimumSizeHint())
            self.requestTabs.widget(index).adjustSize()

    def setOnRequestChanged(self, f):
        self.requestTabs.currentChanged.connect(f)

    def addRequestByFilters(self, filters=None):
        requestWidget = RequestWidget(self, self.keyValues)
        setName = requestWidget.requestName
        requestWidget.changePage(self.currentHtml)
        self.requestTabs.addTab(requestWidget, setName)
        self.requestOps.addRequest(setName)
        self.disambiguationWidget.addSet(setName)

        if filters is not None:
            for filter in filters:
                requestWidget.addFilter(filter)

    def addRequest(self, request):
        if not SetNameManagement.isAvailable(request.name):
            raise ValueError("There is another request with the same name.")
        else:
            SetNameManagement.assign(request.name)

        requestWidget = RequestWidget(self, self.keyValues, request)
        requestWidget.changePage(self.currentHtml)
        self.requestTabs.addTab(requestWidget, request.name)
        self.requestOps.addRequest(request.name)
        self.disambiguationWidget.addSet(request.name)

    def removeRequest(self):
        requestName = self.requestTabs.currentWidget().getName()
        self.requestOps.removeSetAndDependencies(requestName)
        self.disambiguationWidget.removeSet(requestName)
        currentRequestWidget = self.requestTabs.currentWidget()
        SetNameManagement.releaseName(currentRequestWidget.requestName)
        self.requestTabs.removeTab(self.requestTabs.currentIndex())
        currentRequestWidget.deleteLater()

    def requestsCount(self):
        return self.requestTabs.count()

    def getQuery(self):
        query = OverpassQuery(self.requestOps.outputSet())
        query.addDate(self.generalConfig.getDate())

        for i in range(self.requestTabs.count()):
            query.addRequest(self.requestTabs.widget(i).getRequest())

        for op in self.requestOps.ops:
            query.addSetsOp(op)

        return query

    def setQuery(self, query):
        self.reset()
        for request in query.requests:
            self.addRequest(request)
        for op in query.ops:
            self.requestOps.addOp(op)
        if query.config.get("date") is not None:
            self.generalConfig.setDate(datetime.strptime(query.config["date"], "%Y-%m-%dT00:00:00Z"))
        else:
            self.generalConfig.setDate()
        self.requestOps.setOutputSet(query.outputSet)

    def reset(self):
        while self.requestTabs.count() > 0:
            self.removeRequest()
        self.generalConfig.setDate()

    def updateMaps(self, html):
        self.currentHtml = html
        for requestWidget in self.findChildren(RequestWidget):
            requestWidget.changePage(html)

        return self.getCurrentMap()

    def updateMapFromRow(self):
        currentRequest = self.requestTabs.currentWidget()
        return self.updateMaps(currentRequest.getHtmlFromSelectedRow())

    def getCurrentMap(self):
        if self.requestTabs.currentWidget() is None:
            return None
        else:
            return self.requestTabs.currentWidget().getMap()
