import logging
import os
import sys
import traceback
from os.path import expanduser

import osmnx as ox
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QTextEdit, QFileDialog, QSplitter, QHBoxLayout, QMessageBox
from requests import RequestException

from Exceptions.OverpassExceptions import OverpassRequestException
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

    def flush(self):
        pass

    def writeMessage(self, message, color):
        self.moveCursor(QTextCursor.End)
        self.setTextColor(Qt.black)
        self.insertPlainText(message[:10])
        self.setTextColor(color)
        self.insertPlainText(message[10:] + "\n")
        self.moveCursor(QTextCursor.End)

    def writeWarning(self, warning):
        self.writeMessage(warning, Qt.darkYellow)

    def writeInfo(self, warning):
        self.writeMessage(warning, Qt.black)

    def writeError(self, warning):
        self.writeMessage(warning, Qt.darkRed)

    def writeSuccess(self, warning):
        self.writeMessage(warning, Qt.darkGreen)


class POSM(QMainWindow):

    def __init__(self):
        super().__init__()
        self.htmlSettings = []
        self.initUI()

    def initUI(self):
        self.layout = QHBoxLayout()

        self.horSplitter = QSplitter(Qt.Horizontal)
        self.editionSplitter = QSplitter(Qt.Vertical)

        self.queryUI = QueryUI()
        self.queryUI.onClearPolygon(self.cleanCurrentPolygon)
        self.queryUI.onPolygonEnabled(self.enablePolygon, self.disablePolygon)
        self.queryUI.onTabChanged(self.changeCurrentPolygon)
        self.editionSplitter.addWidget(self.queryUI)

        self.queryText = CodeEditor()
        self.qlHighlighter = OverpassQLHighlighter(self.queryText.document())
        self.queryText.setReadOnly(True)
        self.editionSplitter.addWidget(self.queryText)

        self.horSplitter.addWidget(self.editionSplitter)

        self.mapRenderer = QWebEngineView()
        self.mapRenderer.setMinimumWidth(500)
        self.mapRenderer.load(QUrl.fromLocalFile(defaultTileMap))
        self.mapRenderer.loadFinished.connect(
            lambda: self.mapRenderer.page().runJavaScript("document.body.children[0].id;", self.modifyHtml))

        self.addRequest()

        self.consoleSplitter = QSplitter(Qt.Vertical)
        self.consoleSplitter.addWidget(self.mapRenderer)

        self.console = InformationalConsole()
        self.consoleSplitter.addWidget(self.console)

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
        addRequestAct.triggered.connect(self.addRequest)
        addRequestAct.setShortcut('Ctrl+A')
        self.requestMenu.addAction(addRequestAct)

        removeRequestAct = QAction('Remove current request', self)
        removeRequestAct.triggered.connect(self.removeRequest)
        removeRequestAct.setShortcut('Ctrl+R')
        self.requestMenu.addAction(removeRequestAct)

        addFilterAct = QAction('Add filter', self)
        addFilterAct.triggered.connect(self.queryUI.addFilter)
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
        manualModeGetPolygonAct.triggered.connect(lambda: self.mapRenderer.page().runJavaScript("getManualPolygon();", self.logManualModePolygonCoords))
        self.manualModeMenu.addAction(manualModeGetPolygonAct)

        windowsMenu = menubar.addMenu('Windows')

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

    def logManualModePolygonCoords(self, coords):
        logging.info("Polygon coordinates:\"{}\"".format(" ".join([str(c) for point in coords for c in point])))

    def showHideConsole(self):
        if self.console.isHidden():
            self.console.show()
        else:
            self.console.hide()

    def showHideQuery(self):
        if self.queryText.isHidden():
            self.queryText.show()
        else:
            self.queryText.hide()

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
            self.mapRenderer.load(buildHTMLWithQuery(self.queryText.toPlainText()))
            logging.info("Query drawn.")
            self.mapRenderer.loadFinished.connect(
                lambda: self.mapRenderer.page().runJavaScript("document.body.children[0].id;", self.modifyHtml))
        except OverpassRequestException as e:
            logging.error(str(e))
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given query.")
        except RequestException:
            logging.error(traceback.format_exc())
        except OSError:
            logging.error("There was a problem creating the file with the request response.")

    def addRequest(self):
        self.mapRenderer.page().runJavaScript("addPolygon();")
        self.queryUI.addRequest()

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

    def getPolygons(self):
        self.mapRenderer.page().runJavaScript("getPolygons();", self.setHtmlSettings)

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
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save File', expanduser("~/filename.net.xml"),
                                                               "NET files (*.net.xml)")
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

    def showTableSelection(self):
        self.mapRenderer.load(buildHTMLWithNetworkx(self.queryUI.getSelectedRowNetworkx()))

    def closeEvent(self, event):
        for f in os.listdir(tempDir):
            os.remove(os.path.join(tempDir, f))
        QMainWindow.closeEvent(self, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = POSM()
    ex.show()
    sys.exit(app.exec_())
