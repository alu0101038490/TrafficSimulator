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
        self.initUI()

    def initUI(self):
        self.layout = QHBoxLayout()

        self.horSplitter = QSplitter(Qt.Horizontal)
        self.editionSplitter = QSplitter(Qt.Vertical)

        self.queryUI = QueryUI()
        self.queryUI.onClearPolygon(self.clearCurrentPolygon)
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
        removeRequestAct.triggered.connect(self.queryUI.removeRequest)
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

    def playQuery(self):
        if self.queryText.isReadOnly():
            self.queryText.setText(self.queryUI.getQuery().getQL())
        self.mapRenderer.load(buildHTML(self.queryText.toPlainText()))
        self.mapRenderer.loadFinished.connect(
            lambda: self.mapRenderer.page().runJavaScript("document.body.children[0].id;", self.modifyHtml))

    def addRequest(self):
        self.mapRenderer.page().runJavaScript("polygon.push([]);")
        self.queryUI.addRequest()

    def removeRequest(self):
        index = self.queryUI.currentRequest()
        self.mapRenderer.page().runJavaScript("polygon.splice(%i, 1);" %index)
        self.queryUI.removeRequest()

    def modifyHtml(self, id):
        code = """
            var isClickActivated = false;
            var currentPolygon = 0;
            var polygon = [];
            var latlngs = [];

            %s.on('click', function(e) { 
                if(isClickActivated && currentPolygon >= 0) {
                    if(latlngs[currentPolygon].length > 0) {
                        polygon[currentPolygon].removeFrom(%s);  
                    }
                    latlngs[currentPolygon].push(e.latlng);
                    polygon[currentPolygon] = L.polygon(latlngs[currentPolygon], {color: 'red'}).addTo(%s);
                }
            });
            """ % (id, id, id)
        self.mapRenderer.page().runJavaScript(code)

    def disablePolygon(self):
        self.mapRenderer.page().runJavaScript("document.body.children[0].id;",
                                              lambda id: self.mapRenderer.page().runJavaScript(
                                                  "polygon.removeFrom(%s);polygon = [];isClickActivated = false;" % id))

    def enablePolygon(self):
        self.mapRenderer.page().runJavaScript("isClickActivated = true;")

    def clearCurrentPolygon(self):
        self.mapRenderer.page().runJavaScript("document.body.children[0].id;",
                                              lambda id: self.mapRenderer.page().runJavaScript(
                                                  """
                                                  polygon[currentPolygon].removeFrom(%s);
                                                  polygon = [];""" % id))

    def changeCurrentPolygon(self, i):
        self.mapRenderer.page().runJavaScript("document.body.children[0].id;",
                                              lambda id: self.mapRenderer.page().runJavaScript(
                                                            """currentPolygon = %i;
                                                            polygon[currentPolygon].removeFrom(%s);
                                                            polygon[currentPolygon] = L.polygon(latlngs[currentPolygon], {color: 'red'}).addTo(%s);""" % (i,id,id)))

    def getPolygon(self):
        self.mapRenderer.page().runJavaScript("latlngs;")

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
