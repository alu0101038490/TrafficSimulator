import logging
import sys

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QTextEdit, QFileDialog, QSplitter, QHBoxLayout, QMessageBox

from Utils.SumoUtils import buildNet, openNetedit, buildHTML, defaultTileMap
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

        self.queryText = QTextEdit()
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
        openAct.setShortcut('Ctrl+O')
        fileMenu.addAction(openAct)

        saveAct = QAction('Save output', self)
        saveAct.triggered.connect(self.saveNet)
        saveAct.setShortcut('Ctrl+S')
        fileMenu.addAction(saveAct)

        runMenu = menubar.addMenu('Run')

        playAct = QAction('Play', self)
        playAct.triggered.connect(self.playQuery)
        playAct.setShortcut('Ctrl+P')
        runMenu.addAction(playAct)

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

        removeFilterAct = QAction('Remove selected filters', self)
        removeFilterAct.triggered.connect(self.queryUI.removeFilter)
        removeFilterAct.setShortcut('Ctrl+D')
        self.requestMenu.addAction(removeFilterAct)

        manualModeAct = QAction('Manual editing of the query', self)
        manualModeAct.triggered.connect(self.setManualMode)
        self.requestMenu.addAction(manualModeAct)

    def setManualMode(self):
        reply = QMessageBox.question(self, "Manual mode", "Are you sure?\nYou will not be able to return to "
                                                          "interactive mode")
        if reply == QMessageBox.Yes:
            self.queryText.setReadOnly(False)
            self.queryUI.hide()
            self.requestMenu.setEnabled(False)

    def loadMap(self):
        self.mapRenderer.load(buildHTML(self.queryText.toPlainText()))
        self.mapRenderer.loadFinished.connect(
            lambda: self.mapRenderer.page().runJavaScript("document.body.children[0].id;", self.modifyHtml))

    def addRequest(self):
        self.mapRenderer.page().runJavaScript("addPolygon();")
        self.queryUI.addRequest()

    def removeRequest(self):
        self.mapRenderer.page().runJavaScript("removeCurrentPolygon();")
        self.queryUI.removeRequest()

    def modifyHtml(self, id):
        code = """
            var currentPolygon = 0;
            var isClickActivated = [false];
            var polygon = [null];
            var latlngs = [[]];
            
            function draw() {
                if(polygon[currentPolygon] != null) {
                    polygon[currentPolygon].removeFrom(%s);  
                }
                polygon[currentPolygon] = L.polygon(latlngs[currentPolygon], {color: 'red'}).addTo(%s);
            }

            %s.on('click', function(e) { 
                if(isClickActivated[currentPolygon] && currentPolygon >= 0) {
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
				polygon[currentPolygon].removeFrom(%s);
                latlngs[currentPolygon] = [];
			}
			
			function disablePolygon() {
			    cleanPolygon();
			    isClickActivated[currentPolygon] = false;
			}
			
			function enablePolygon() {
			    isClickActivated[currentPolygon] = true;
			}
			
			function changeCurrentPolygon(i) {
			    polygon[currentPolygon].removeFrom(%s);
			    currentPolygon = i;
			    draw();
			}
			
			function getPolygon() {
			    return latlngs;
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
                    latlngs[currentPolygon].pop();
                    draw();
                }
            }
            
            document.onkeydown = KeyPress;
            """ % (id, id, id, id, id)
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
            self.queryText.setText(query.getQL())
        self.loadMap()

    def setPolygons(self):
        if len(self.htmlSettings) > 0:
            self.mapRenderer.page().runJavaScript("setPolygons(%s, %s, %s);" % (self.htmlSettings[0], str(self.htmlSettings[1]), self.htmlSettings[2]))

    def disablePolygon(self):
        self.mapRenderer.page().runJavaScript("disablePolygon();")

    def enablePolygon(self):
        self.mapRenderer.page().runJavaScript("enablePolygon();")

    def cleanCurrentPolygon(self):
        self.mapRenderer.page().runJavaScript("cleanPolygon();")

    def changeCurrentPolygon(self, i):
        self.mapRenderer.page().runJavaScript("changeCurrentPolygon(%i);" % i)

    def getPolygon(self):
        self.mapRenderer.page().runJavaScript("getPolygons();")

    def saveNet(self):
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save File')
        buildNet(filename)
        return filename

    def openNet(self):
        openNetedit(self.saveNet() + ".net.xml")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = POSM()
    ex.show()
    sys.exit(app.exec_())
