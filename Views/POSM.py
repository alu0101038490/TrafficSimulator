import logging
import os
import sys
import traceback
from os.path import expanduser

import osmnx as ox
import qtmodern.styles
import qtmodern.windows
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QUrl, QLocale
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QFileDialog, QSplitter, QHBoxLayout, QMessageBox, QLabel, QVBoxLayout, QSizePolicy, QWIDGETSIZE_MAX

from Exceptions.OverpassExceptions import OverpassRequestException, OsmnxException
from Utils.OverpassUtils import OverpassQLHighlighter
from Utils.SumoUtils import buildNet, openNetedit, buildHTMLWithQuery, defaultTileMap, buildHTMLWithNetworkx, tempDir
from Views.Console import InformationalConsole
from Views.NumberedTextEdit import CodeEditor
from Views.QueryUI import QueryUI
from constants import APP_STYLESHEET, HTML_SCRIPTS


class POSM(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setLocale(QLocale(QLocale.English))
        self.htmlSettings = []
        self.initUI()
        self.setAttribute(Qt.WA_AlwaysShowToolTips)
        sizegrip = QtWidgets.QSizeGrip(self)
        self.layout.addWidget(sizegrip, 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight)

    def initUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.console = InformationalConsole()

        self.horSplitter = QSplitter(Qt.Horizontal)
        self.horSplitter.setChildrenCollapsible(False)
        self.editionSplitter = QSplitter(Qt.Vertical)
        self.editionSplitter.setChildrenCollapsible(False)

        self.queryUI = QueryUI()
        self.queryUI.onClearPolygon(self.cleanCurrentPolygon)
        self.queryUI.onPolygonEnabled(self.enablePolygon, self.disablePolygon)
        self.queryUI.setOnTabChanged(self.changeCurrentPolygon)
        self.editionSplitter.addWidget(self.queryUI)

        self.queryWidget = QWidget()
        self.queryWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.queryWidget.setLayout(QVBoxLayout())
        self.queryWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.queryWidget.layout().setSpacing(0)

        self.queryHeader = QLabel("Query")
        self.queryHeader.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.queryHeader.setFixedHeight(self.queryHeader.sizeHint().height() + 10)
        self.queryHeader.setContentsMargins(5, 5, 0, 5)
        self.queryWidget.layout().addWidget(self.queryHeader)

        self.queryText = CodeEditor()
        self.qlHighlighter = OverpassQLHighlighter(self.queryText.document())
        self.queryText.setReadOnly(True)
        self.queryWidget.layout().addWidget(self.queryText)

        self.editionSplitter.addWidget(self.queryWidget)

        self.horSplitter.addWidget(self.editionSplitter)

        self.emptyMapUrl = QUrl.fromLocalFile(defaultTileMap)
        self.lastMapUrl = None

        self.mapRenderer = QWebEngineView()
        self.mapRenderer.setMinimumWidth(500)
        self.mapRenderer.load(self.emptyMapUrl)
        self.mapRenderer.loadFinished.connect(
            lambda: self.mapRenderer.page().runJavaScript("document.body.children[0].id;", self.modifyHtml))

        self.addRequest()

        self.consoleSplitter = QSplitter(Qt.Vertical)
        self.consoleSplitter.setChildrenCollapsible(False)
        self.consoleSplitter.addWidget(self.mapRenderer)

        self.consoleWidget = QWidget()
        self.consoleWidget.setLayout(QVBoxLayout())
        self.consoleWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.consoleWidget.layout().setSpacing(0)

        self.consoleHeader = QLabel("Console")
        self.consoleHeader.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.consoleHeader.setContentsMargins(5, 5, 0, 5)
        self.consoleWidget.layout().addWidget(self.consoleHeader)
        self.consoleWidget.layout().addWidget(self.console)

        self.consoleSplitter.addWidget(self.consoleWidget)

        self.horSplitter.addWidget(self.consoleSplitter)

        self.layout.addWidget(self.horSplitter)

        self.initMenuBar()

        centralWidget = QWidget(self)
        centralWidget.setLayout(self.layout)
        self.setCentralWidget(centralWidget)

        self.setWindowTitle('Python Open Street Map')

    def initMenuBar(self):
        menubar = self.menuBar()

        fileMenu = menubar.addMenu('File')

        openAct = QAction('Open netedit', self)
        openAct.triggered.connect(self.openNet)
        fileMenu.addAction(openAct)

        saveAct = QAction('Save output', self)
        saveAct.triggered.connect(self.saveNet)
        saveAct.setShortcut('Ctrl+S')
        fileMenu.addAction(saveAct)

        saveQuery = QAction('Save query', self)
        saveQuery.triggered.connect(self.saveQuery)
        saveQuery.setShortcut('Ctrl+Shift+S')
        fileMenu.addAction(saveQuery)

        openQuery = QAction('Open query', self)
        openQuery.triggered.connect(self.openQuery)
        openQuery.setShortcut('Ctrl+O')
        fileMenu.addAction(openQuery)

        runMenu = menubar.addMenu('Run')

        playAct = QAction('Play', self)
        playAct.triggered.connect(self.playQuery)
        playAct.setShortcut('Ctrl+P')
        runMenu.addAction(playAct)

        showSelectionAct = QAction('Run selected row of the disambiguation table', self)
        showSelectionAct.triggered.connect(self.showTableSelection)
        showSelectionAct.setShortcut('Ctrl+N')
        runMenu.addAction(showSelectionAct)

        self.requestMenu = menubar.addMenu('Request')

        addRequestAct = QAction('Add request', self)
        addRequestAct.triggered.connect(lambda b: self.addRequest())
        addRequestAct.setShortcut('Ctrl+A')
        self.requestMenu.addAction(addRequestAct)

        templatesMenu = self.requestMenu.addMenu("Add template")

        addRoadAct = QAction('Roads', self)
        addRoadAct.triggered.connect(lambda: self.addTemplate([("highway", "", True, False),
                                                               ("name", "", True, False),
                                                               ("ref", "", True, False),
                                                               ("maxspeed", "^1([01]\d|20)|\d\d?$", False, False),
                                                               ("lanes", "", True, False),
                                                               ("oneway", "", True, False)]))
        templatesMenu.addAction(addRoadAct)

        addMainRoadAct = QAction('Main roads', self)
        mainHighways = "^(motorway|trunk|primary|secondary|residential)(_link)?$"
        everythinButYes = "^(y(e([^s]|$|s.)|[^e]|$)|[^y]|$).*"
        addMainRoadAct.triggered.connect(lambda: self.addTemplate([("highway", mainHighways, False, False),
                                                                   ("construction", "", False, True),
                                                                   ("noexit", "yes", True, True),
                                                                   ("access", everythinButYes, False, True)]))
        templatesMenu.addAction(addMainRoadAct)

        addParkingAct = QAction('Parking', self)
        addParkingAct.triggered.connect(lambda: self.addTemplate([("service", "parking", False, False),
                                                                  ("highway", "", False, False)]))
        templatesMenu.addAction(addParkingAct)

        addPedestriansAct = QAction('Pedestrians', self)
        pedestrianHighway = "^(pedestrian|footway|path|cycleway|bridleway|steps|crossing)$"
        addPedestriansAct.triggered.connect(lambda: self.addTemplate([("highway", pedestrianHighway, False, False)]))
        templatesMenu.addAction(addPedestriansAct)

        removeRequestAct = QAction('Remove current request', self)
        removeRequestAct.triggered.connect(self.removeRequest)
        removeRequestAct.setShortcut('Ctrl+R')
        self.requestMenu.addAction(removeRequestAct)

        addFilterAct = QAction('Add filter', self)
        addFilterAct.triggered.connect(lambda b: self.addFilter())
        addFilterAct.setShortcut('Ctrl+T')
        self.requestMenu.addAction(addFilterAct)

        self.manualModeAct = QAction('Switch between interactive and manual mode', self)
        self.manualModeAct.triggered.connect(self.switchManualMode)
        self.requestMenu.addAction(self.manualModeAct)

        self.manualModeMenu = menubar.addMenu('Manual mode')
        self.manualModeMenu.setEnabled(False)

        manualModeCleanPolygonAct = QAction('Clean polygon', self)
        manualModeCleanPolygonAct.triggered.connect(self.cleanCurrentPolygon)
        self.manualModeMenu.addAction(manualModeCleanPolygonAct)

        manualModeGetPolygonAct = QAction('Polygon coordinates', self)
        manualModeGetPolygonAct.triggered.connect(
            lambda: self.mapRenderer.page().runJavaScript("getManualPolygon();", self.logManualModePolygonCoords))
        self.manualModeMenu.addAction(manualModeGetPolygonAct)

        windowsMenu = menubar.addMenu('Windows')

        templatesMenu = windowsMenu.addMenu("Map")

        showEmptyMapAct = QAction('Empty', self)
        showEmptyMapAct.triggered.connect(self.changeToEmptyMap)
        templatesMenu.addAction(showEmptyMapAct)

        showLastMapAct = QAction('Last response', self)
        showLastMapAct.triggered.connect(self.changeToLastMap)
        templatesMenu.addAction(showLastMapAct)

        self.showHideInteractiveModeAct = QAction('Interactive mode', self)
        self.showHideInteractiveModeAct.triggered.connect(self.showHideInteractiveMode)
        windowsMenu.addAction(self.showHideInteractiveModeAct)

        showHideConsole = QAction('Console', self)
        showHideConsole.triggered.connect(self.showHideConsole)
        windowsMenu.addAction(showHideConsole)

        showHideQuery = QAction('Query', self)
        showHideQuery.triggered.connect(self.showHideQuery)
        windowsMenu.addAction(showHideQuery)

    def changeToEmptyMap(self):
        if self.mapRenderer.url() != self.emptyMapUrl:
            self.getPolygons(lambda polygons: self.changeMap(polygons, self.emptyMapUrl))
            logging.info("Changing to empty map.")
        else:
            logging.warning("The empty map is currently showing.")
        logging.debug("LINE")

    def changeToLastMap(self):
        if self.lastMapUrl is None:
            logging.warning("No request have been made yet.")
        elif self.mapRenderer.url() != self.emptyMapUrl:
            logging.warning("The last request map is currently showing.")
        else:
            self.getPolygons(lambda polygons: self.changeMap(polygons, self.lastMapUrl))
            logging.info("Changing to last request map.")
        logging.debug("LINE")

    def changeMap(self, settings, url):
        self.htmlSettings = settings
        self.mapRenderer.load(url)

    def logManualModePolygonCoords(self, coords):
        logging.info("Polygon coordinates:\"{}\"".format(" ".join([str(c) for point in coords for c in point])))
        logging.debug("LINE")

    def showHideInteractiveMode(self):
        if self.queryUI.isHidden():
            self.queryUI.show()
            logging.info("Showing 'Interactive mode' window.")
        else:
            self.queryUI.hide()
            logging.info("Hiding 'Interactive mode' window.")
        logging.debug("LINE")

    def showHideConsole(self):
        if self.console.isHidden():
            self.console.show()
            logging.info("Showing 'Console' window.")
            self.consoleWidget.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self.console.hide()
            self.consoleWidget.setMaximumHeight(self.queryHeader.sizeHint().height())
            logging.info("Hiding 'Console' window.")
        logging.debug("LINE")

    def showHideQuery(self):
        if self.queryText.isHidden():
            self.queryText.show()
            logging.info("Showing 'Query' window.")
            self.queryWidget.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self.queryText.hide()
            self.queryWidget.setMaximumHeight(self.queryHeader.sizeHint().height())
            logging.info("Hiding 'Query' window.")
        logging.debug("LINE")

    def switchManualMode(self):
        if self.queryText.isReadOnly():
            reply = QMessageBox.question(self, "Manual mode",
                                         "Are you sure?\nThe interactive mode will remain as it is now.")

            if reply == QMessageBox.Yes:
                self.queryText.setReadOnly(False)

                self.queryUI.hide()
                for action in self.requestMenu.actions():
                    action.setEnabled(False)
                self.manualModeAct.setEnabled(True)
                self.manualModeMenu.setEnabled(True)
                self.showHideInteractiveModeAct.setEnabled(False)

                logging.info("Switching to manual mode.")
            else:
                logging.info("'Switch between interactive and manual mode' cancelled.")
        else:
            reply = QMessageBox.question(self, "Interactive mode", "Are you sure?\nThe current query will be removed.")

            if reply == QMessageBox.Yes:
                try:
                    self.queryText.setPlainText(self.queryUI.getQuery().getQL())
                except RuntimeError:
                    logging.warning("Failed to write query.")
                    self.queryText.setPlainText("")

                self.queryText.setReadOnly(True)

                self.queryUI.show()
                for action in self.requestMenu.actions():
                    action.setEnabled(True)
                self.manualModeMenu.setEnabled(False)
                self.showHideInteractiveModeAct.setEnabled(True)

                logging.info("Switching to interactive mode.")
            else:
                logging.info("'Switch between interactive and manual mode' cancelled.")

        logging.info("Showing 'manual mode' polygon.")
        self.mapRenderer.page().runJavaScript("switchInteractiveManualMode();",
                                              lambda x: logging.debug("LINE"))

    def loadMap(self):
        try:
            self.lastMapUrl = buildHTMLWithQuery(self.queryText.toPlainText())
            self.mapRenderer.load(self.lastMapUrl)
            logging.info("Query drawn.")
            logging.debug("LINE")
        except (OverpassRequestException, OsmnxException) as e:
            logging.error(str(e))
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given query.")
        except OSError:
            logging.error("There was a problem creating the file with the request response.")
        except Exception:
            logging.error(traceback.format_exc())

    def addFilter(self, key="", value="", accuracy=False, negate=False):
        if len(key) == 0 and len(value) == 0:
            self.queryUI.addFilter()
            logging.info("Empty filter added.")
        else:
            self.queryUI.addFilter(key, value, accuracy, negate)
            logging.info("'{}' filter added.".format(key))
        logging.debug("LINE")

    def addRequest(self, filters=None):
        self.mapRenderer.page().runJavaScript("addPolygon();")
        self.queryUI.addRequest(filters)
        logging.info("Request added.")
        logging.debug("LINE")

    def addTemplate(self, filters):
        if self.queryUI.requestsCount() > 0:
            for key, value, accuracy, negate in filters:
                self.queryUI.addFilter(key, value, accuracy, negate)
                if len(key) == 0 and len(value) == 0:
                    logging.info("Empty filter added.")
                else:
                    logging.info("'{}' filter added.".format(key))
            logging.info("Template applied.")
            logging.debug("LINE")
        else:
            logging.warning("There is no requests. Adding a new one.")
            logging.info("Template applied.")
            self.queryUI.addRequest(filters)

    def removeRequest(self):
        reply = QMessageBox.question(self, "Remove current request",
                                     "Are you sure? This option is not undoable.")

        if reply == QMessageBox.Yes:
            self.mapRenderer.page().runJavaScript("removeCurrentPolygon();")
            self.queryUI.removeRequest()
            logging.info("'Remove request' successfully executed.")
        else:
            logging.info("'Remove request' cancelled.")
        logging.debug("LINE")

    def modifyHtml(self, id):
        code = HTML_SCRIPTS % (id, id, id, id, id, id, id, id, id, id)
        self.mapRenderer.page().runJavaScript(code, lambda x: self.setPolygons())

    def getPolygons(self, f=None):
        if f is None:
            f = self.setHtmlSettings
        self.mapRenderer.page().runJavaScript("getPolygons();", f)

    def setHtmlSettings(self, settings):
        self.htmlSettings = settings

    def playQuery(self):
        self.mapRenderer.page().runJavaScript("getPolygons();", self.setHtmlSettingsAndLoad)

    def setHtmlSettingsAndLoad(self, settings):
        self.htmlSettings = settings
        if self.queryText.isReadOnly():
            query = self.queryUI.getQuery()
            for i in range(len(self.htmlSettings[1])):
                query.addPolygon(i, self.htmlSettings[1][i])

            try:
                self.queryText.setPlainText(query.getQL())
            except RuntimeError as e:
                logging.error(str(e))
                return
        self.loadMap()

    def setPolygons(self):
        if len(self.htmlSettings) > 0:
            self.mapRenderer.page().runJavaScript(
                "setPolygons(%s, %s, %s, %s, %s);" % (self.htmlSettings[0],
                                                      str(self.htmlSettings[1]),
                                                      self.htmlSettings[2],
                                                      str(self.htmlSettings[3]),
                                                      self.htmlSettings[4]))

    def disablePolygon(self):
        self.mapRenderer.page().runJavaScript("disablePolygon();")

    def enablePolygon(self):
        self.mapRenderer.page().runJavaScript("enablePolygon();")

    def cleanCurrentPolygon(self):
        logging.info("Cleaning polygon.")
        self.mapRenderer.page().runJavaScript("cleanPolygon();", logging.debug("LINE"))

    def changeCurrentPolygon(self, i):
        self.mapRenderer.page().runJavaScript("changeCurrentPolygon(%i);" % i)

    def saveQuery(self):
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save query', expanduser("~/filename.txt"),
                                                               "Text files (*.txt)")

        if filename != "":
            if self.queryText.isReadOnly():
                try:
                    query = self.queryUI.getQuery().getQL()
                    f = open(filename, "w+")
                    f.seek(0)
                    f.truncate()
                    f.write(query)
                    f.close()

                    logging.info("Query saved successfully.")
                except RuntimeError as e:
                    logging.error(str(e))
                except OSError:
                    logging.error("There was a problem creating the file with the query.")
            else:
                try:
                    f = open(filename, "w+")
                    f.seek(0)
                    f.truncate()
                    f.write(self.queryText.toPlainText())
                    f.close()

                    logging.info("Query saved successfully.")
                except OSError:
                    logging.error("There was a problem creating the file with the query.")
        else:
            logging.info("\"Save query\" canceled.")

        logging.debug("LINE")

    def openQuery(self):
        filename, selectedFilter = QFileDialog.getOpenFileName(self, 'Open query', expanduser("~/filename.txt"),
                                                               "Text files (*.txt)")

        if filename != "":
            try:
                f = open(filename, "w+")
                self.queryText.setPlainText(f.read())
                f.close()
                logging.info("File read successfully.")
                if self.queryText.isReadOnly():
                    self.switchManualMode()
            except OSError:
                logging.error("There was a problem opening the query file.")
        else:
            logging.info("\"Open query\" canceled.")

        logging.debug("LINE")

    def saveNet(self):
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save File',
                                                               expanduser("~/filenameWithoutExtension"))
        if filename != "":
            buildNet(filename)
        else:
            logging.info("\"Save File\" canceled.")
        logging.debug("LINE")
        return filename

    def openNet(self):
        try:
            filename = self.saveNet()
            if filename == "":
                logging.error("Can't open NETEDIT without a file.")
            else:
                openNetedit(filename + ".net.xml")
                logging.info("Opening NETEDIT.")
                logging.warning("If NETEDIT is not open in ten seconds, there was an unhandled problem.")
                logging.debug("LINE")
        except OSError:
            logging.error("Can't find NETEDIT.")
        except Exception:
            logging.error(traceback.format_exc())

    def showTableSelection(self):
        try:
            self.mapRenderer.load(buildHTMLWithNetworkx(self.queryUI.getSelectedRowNetworkx()))
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

    def closeEvent(self, event):
        for f in os.listdir(tempDir):
            os.remove(os.path.join(tempDir, f))
        QMainWindow.closeEvent(self, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = POSM()

    qtmodern.styles.dark(app)
    app.setStyleSheet(APP_STYLESHEET)

    mw = qtmodern.windows.ModernWindow(ex)

    mw.show()
    sys.exit(app.exec_())
