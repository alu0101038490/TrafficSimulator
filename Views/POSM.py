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
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QTextEdit, QFileDialog, QSplitter, QHBoxLayout, QMessageBox, QLabel, QVBoxLayout, QSizePolicy, QWIDGETSIZE_MAX

from Exceptions.OverpassExceptions import OverpassRequestException, OsmnxException
from Utils.OverpassUtils import OverpassQLHighlighter
from Utils.SumoUtils import buildNet, openNetedit, buildHTMLWithQuery, defaultTileMap, buildHTMLWithNetworkx, tempDir
from Views.NumberedTextEdit import CodeEditor
from Views.QueryUI import QueryUI


class InformationalConsole(QTextEdit):

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

        logging.basicConfig(stream=self, level=logging.INFO, format='%(levelname)s%(asctime)s - %(message)s',
                            datefmt="%H:%M:%S")

    def write(self, text):
        if text[0] == "W":
            self.writeWarning(text[7:])
        elif text[0] == "I":
            self.writeInfo(text[4:])
        elif text[0] == "E":
            self.writeError(text[5:])
        elif text[0] == "C":
            self.writeError(text[8:])
        app.processEvents()

    def flush(self):
        pass

    def writeMessage(self, message, color):
        self.moveCursor(QTextCursor.End)
        self.setTextColor(Qt.white)
        self.insertPlainText(message[:10])
        self.setTextColor(color)
        self.insertPlainText(message[10:] + "\n")
        self.moveCursor(QTextCursor.End)

    def writeWarning(self, warning):
        self.writeMessage(warning, Qt.darkYellow)

    def writeInfo(self, info):
        self.writeMessage(info, Qt.white)

    def writeError(self, error):
        self.writeMessage(error, Qt.darkRed)

    def writeSuccess(self, success):
        self.writeMessage(success, Qt.darkGreen)


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
        self.console = InformationalConsole()
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
        addFilterAct.triggered.connect(lambda b: self.queryUI.addFilter())
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

        self.showHideInteractiveMode = QAction('Interactive mode', self)
        self.showHideInteractiveMode.triggered.connect(
            lambda: self.queryUI.show() if self.queryUI.isHidden() else self.queryUI.hide())
        windowsMenu.addAction(self.showHideInteractiveMode)

        showHideConsole = QAction('Console', self)
        showHideConsole.triggered.connect(self.showHideConsole)
        windowsMenu.addAction(showHideConsole)

        showHideQuery = QAction('Query', self)
        showHideQuery.triggered.connect(self.showHideQuery)
        windowsMenu.addAction(showHideQuery)

    def changeToEmptyMap(self):
        if self.mapRenderer.url() != self.emptyMapUrl:
            self.getPolygons(lambda polygons: self.changeMap(polygons, self.emptyMapUrl))

    def changeToLastMap(self):
        if self.mapRenderer.url() == self.emptyMapUrl and self.lastMapUrl is not None:
            self.getPolygons(lambda polygons: self.changeMap(polygons, self.lastMapUrl))

    def changeMap(self, settings, url):
        self.htmlSettings = settings
        self.mapRenderer.load(url)

    def logManualModePolygonCoords(self, coords):
        logging.info("Polygon coordinates:\"{}\"".format(" ".join([str(c) for point in coords for c in point])))

    def showHideConsole(self):
        if self.console.isHidden():
            self.console.show()
            self.consoleWidget.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self.console.hide()
            self.consoleWidget.setMaximumHeight(self.queryHeader.sizeHint().height())

    def showHideQuery(self):
        if self.queryText.isHidden():
            self.queryText.show()
            self.queryWidget.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self.queryText.hide()
            self.queryWidget.setMaximumHeight(self.queryHeader.sizeHint().height())

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
                self.showHideInteractiveMode.setEnabled(False)

                logging.info("Switching to manual mode.")
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
                self.showHideInteractiveMode.setEnabled(True)

                logging.info("Switching to interactive mode.")

        self.mapRenderer.page().runJavaScript("switchInteractiveManualMode();")

    def loadMap(self):
        try:
            self.lastMapUrl = buildHTMLWithQuery(self.queryText.toPlainText())
            self.mapRenderer.load(self.lastMapUrl)
            logging.info("Query drawn.")
        except (OverpassRequestException, OsmnxException) as e:
            logging.error(str(e))
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given query.")
        except OSError:
            logging.error("There was a problem creating the file with the request response.")
        except Exception:
            logging.error(traceback.format_exc())

    def addRequest(self, filters=None):
        self.mapRenderer.page().runJavaScript("addPolygon();")
        self.queryUI.addRequest(filters)

    def addTemplate(self, filters):
        if self.queryUI.requestsCount() > 0:
            for key, value, accuracy, negate in filters:
                self.queryUI.addFilter(key, value, accuracy, negate)
        else:
            self.queryUI.addRequest(filters)

    def removeRequest(self):
        self.mapRenderer.page().runJavaScript("removeCurrentPolygon();")
        self.queryUI.removeRequest()

    def modifyHtml(self, id):
        code = """
            var currentPolygon = 0;
            var interactiveMode = true
            var isClickActivated = [false];
            var polygon = [null];
            var latlngs = [[]];
            
            var manualModePolygon = null
            var manualModeLatlngs = []

            function draw() {
                if(interactiveMode) {
                    if(polygon[currentPolygon] != null) {
                        polygon[currentPolygon].removeFrom(%s);  
                    }
                    polygon[currentPolygon] = L.polygon(latlngs[currentPolygon], {color: 'red'}).addTo(%s);  
                } else {
                    if(manualModePolygon != null) {
                        manualModePolygon.removeFrom(%s);  
                    }
                    manualModePolygon = L.polygon(manualModeLatlngs, {color: 'red'}).addTo(%s);
                }
            }

            %s.on('click', function(e) { 
                if(!interactiveMode) {
                    manualModeLatlngs.push(e.latlng);
                    draw();
                } else if(isClickActivated[currentPolygon] && currentPolygon >= 0) {
                    latlngs[currentPolygon].push(e.latlng);
                    draw();
                }
            });

            function addPolygon() {
                latlngs.push([]);
                isClickActivated.push(false)
                polygon.push(null);
            }

            function cleanPolygon() {
                if(interactiveMode) {
                    if(polygon[currentPolygon] != null)
                        polygon[currentPolygon].removeFrom(%s);
                    latlngs[currentPolygon] = [];
                } else {
                    if(manualModePolygon != null)
                        manualModePolygon.removeFrom(%s);
                    manualModeLatlngs = [];
                }
            }

            function disablePolygon() {
                isClickActivated[currentPolygon] = false;
            }

            function enablePolygon() {
                isClickActivated[currentPolygon] = true;
            }

            function changeCurrentPolygon(i) {
                if(polygon[currentPolygon] != null)
                    polygon[currentPolygon].removeFrom(%s);
                currentPolygon = i;
                draw();
            }
            
            function switchInteractiveManualMode() {
                if(interactiveMode) {
                    if (polygon[currentPolygon] != null)
                        polygon[currentPolygon].removeFrom(%s);
                } else {
                    if (manualModePolygon)
                        manualModePolygon.removeFrom(%s);
                }
                interactiveMode = !interactiveMode;
                draw();
            }
            
            function getManualPolygon() {
                result = []
                for (i in manualModeLatlngs) {
                    result.push([manualModeLatlngs[i].lat, manualModeLatlngs[i].lng])
                }
                return result;
            }

            function removeCurrentPolygon() {
                cleanPolygon();
                isClickActivated.splice(currentPolygon, 1);
                latlngs.splice(currentPolygon, 1);
                polygon.splice(currentPolygon, 1);
                if(currentPolygon == polygon.length) {
                    currentPolygon = currentPolygon - 1;
                }
            }

            function getPolygons() {
                result = []
                for(i in latlngs){
                    aux = []
                    for (j in latlngs[i]) {
                        aux.push([latlngs[i][j].lat, latlngs[i][j].lng])
                    }
                    result.push(aux)
                }
                return [currentPolygon, result, "[" + isClickActivated.toString() + "]"];
            }

            function setPolygons(current, coors, clicksActivated) {
                latlngs = [];
                polygons = [];
                isClickActivated = clicksActivated;
                for (i in coors){
                    latlngs.push([]);
                    for (j in coors[i]) { 
                        latlngs[i].push(L.latLng(coors[i][j][0], coors[i][j][1]));
                    }
                    polygons.push(null);
                }
                currentPolygon = i;
                draw();
            }

            function KeyPress(e) {
                var evtobj = window.event? event : e
                if (evtobj.keyCode == 90 && (event.ctrlKey || event.metaKey)) {
                    if(interactiveMode) {
                        latlngs[currentPolygon].pop();
                    } else {
                        manualModeLatlngs.pop()
                    }
                    draw();
                }
            }

            document.onkeydown = KeyPress;
            """ % (id, id, id, id, id, id, id, id, id, id)
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
                "setPolygons(%s, %s, %s);" % (self.htmlSettings[0], str(self.htmlSettings[1]), self.htmlSettings[2]))

    def disablePolygon(self):
        self.mapRenderer.page().runJavaScript("disablePolygon();")

    def enablePolygon(self):
        self.mapRenderer.page().runJavaScript("enablePolygon();")

    def cleanCurrentPolygon(self):
        self.mapRenderer.page().runJavaScript("cleanPolygon();")

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

    def openQuery(self):
        filename, selectedFilter = QFileDialog.getOpenFileName(self, 'Open query', expanduser("~/filename.txt"),
                                                               "Text files (*.txt)")

        if filename != "":
            try:
                f = open(filename, "w+")
                self.queryText.setPlainText(f.read())
                f.close()
                if self.queryText.isReadOnly():
                    self.switchManualMode()
            except OSError:
                logging.error("There was a problem opening the query file.")
        else:
            logging.info("\"Open query\" canceled.")

    def saveNet(self):
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save File',
                                                               expanduser("~/filenameWithoutExtension"))
        if filename != "":
            buildNet(filename)
        else:
            logging.info("\"Save File\" canceled.")
        return filename

    def openNet(self):
        try:
            filename = self.saveNet()
            if filename == "":
                logging.error("Can't open NETEDIT without a file.")
            else:
                openNetedit(filename + ".net.xml")
                logging.info("Opening NETEDIT.")
        except OSError:
            logging.error("Can't find NETEDIT.")
        except Exception:
            logging.error(traceback.format_exc())

    def showTableSelection(self):
        self.mapRenderer.load(buildHTMLWithNetworkx(self.queryUI.getSelectedRowNetworkx()))

    def closeEvent(self, event):
        for f in os.listdir(tempDir):
            os.remove(os.path.join(tempDir, f))
        QMainWindow.closeEvent(self, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = POSM()

    qtmodern.styles.dark(app)
    app.setStyleSheet("""

        QGroupBox:flat {
            border: none;
        }

        QToolBox::tab {
            background: #454545;
        }

        QToolButton {
            background-color: #f6f7fa;
        }

        QToolButton:pressed {
            background-color: #dadbde;
        }

        QToolTip {
            border: 2px solid darkkhaki;
            padding: 5px;
            border-radius: 3px;
            opacity: 200;
        }   

        FilterWidget {
            background: #353535;
            border: 0px solid green;
            border-radius: 7px;
        }

        QCalendarWidget QToolButton {
            background-color: #2A2A2A;
        }

        QCalendarWidget QToolButton::menu-indicator{image: none;}

        QCalendarWidget QWidget#qt_calendar_navigationbar
        { 
            background-color: #2A2A2A; 
        }

    """)

    mw = qtmodern.windows.ModernWindow(ex)

    mw.show()
    sys.exit(app.exec_())
