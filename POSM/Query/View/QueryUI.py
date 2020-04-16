import logging
import os
import pathlib

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QTabWidget, QToolBox, QAbstractButton
from requests import RequestException

from Operation.View.RequestsOperations import RequestsOperations
from Query.Model.OverpassQuery import OverpassQuery
from Query.View.GlobalOverpassSettingUI import GlobalOverpassSettingUI
from Request.View.RequestWidget import RequestWidget
from Shared.Utils.TaginfoUtils import getOfficialKeys
from Shared.constants import EMPTY_HTML, picturesDir


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

        self.headers = self.requestAreaWidget.findChildren(QAbstractButton, "qt_toolbox_toolboxbutton")
        self.requestAreaWidget.currentChanged.connect(self.__onToolTabChanged__)
        self.headers[0].setIcon(QIcon(os.path.join(picturesDir, "arrowUp.png")))
        for i in range(1, len(self.headers)):
            self.headers[i].setIcon(QIcon(os.path.join(picturesDir, "arrowDown.png")))

        self.layout.addWidget(self.requestAreaWidget)

        self.setLayout(self.layout)

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

        self.requestTabs.widget(index).setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.requestTabs.widget(index).resize(self.requestTabs.widget(index).minimumSizeHint())
        self.requestTabs.widget(index).adjustSize()

    def setOnRequestChanged(self, f):
        self.requestTabs.currentChanged.connect(f)

    def addRequest(self, filters=None):
        requestWidget = RequestWidget(self, self.keyValues)
        setName = OverpassQuery.getUniqueSetName()
        requestWidget.setObjectName(setName)
        requestWidget.changePage(self.currentHtml)
        self.requestTabs.addTab(requestWidget, setName)
        self.requestOps.addRequest(setName)

        if filters is not None:
            for key, value, accuracy, negate in filters:
                requestWidget.addFilter(key, value, accuracy, negate)
        else:
            requestWidget.addFilter()

    def removeRequest(self):
        self.requestOps.removeSetAndDependencies(self.requestTabs.currentWidget().objectName())
        self.requestTabs.currentWidget().deleteLater()

    def requestsCount(self):
        return self.requestTabs.count()

    def getQuery(self):
        query = OverpassQuery(self.requestOps.outputSet())
        query.addDate(self.generalConfig.getDate())

        for requestWidget in self.findChildren(RequestWidget):
            query.addRequest(requestWidget.objectName(), requestWidget.getRequest())

        for name, op in self.requestOps.ops.items():
            query.addSetsOp(name, op)

        return query

    def updateMaps(self, html):
        self.currentHtml = html
        for requestWidget in self.findChildren(RequestWidget):
            requestWidget.changePage(html)

        return self.getCurrentMap()

    def getCurrentMap(self):
        return self.requestTabs.currentWidget().getMap()