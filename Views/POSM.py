import logging
import os
import sys

import osmnx as ox
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QTextEdit, QFileDialog, QSplitter, QHBoxLayout, QMessageBox
from requests import RequestException

from Utils.SumoUtils import buildNet, openNetedit, buildHTMLWithQuery, defaultTileMap, buildHTMLWithNetworkx, tempDir
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
        self.initUI()

    def initUI(self):
        self.layout = QHBoxLayout()

        self.horSplitter = QSplitter(Qt.Horizontal)
        self.editionSplitter = QSplitter(Qt.Vertical)

        self.queryUI = QueryUI()
        self.editionSplitter.addWidget(self.queryUI)

        self.queryText = QTextEdit()
        self.queryText.setReadOnly(True)
        self.editionSplitter.addWidget(self.queryText)

        self.horSplitter.addWidget(self.editionSplitter)

        self.mapRenderer = QWebEngineView()
        self.mapRenderer.setMinimumWidth(500)
        self.mapRenderer.load(QUrl.fromLocalFile(defaultTileMap))

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
        addRequestAct.triggered.connect(self.queryUI.addRequest)
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

        self.manualModeAct = QAction('Switch between interactive and manual mode', self)
        self.manualModeAct.triggered.connect(self.setManualMode)
        self.requestMenu.addAction(self.manualModeAct)

        disambiguationMenu = menubar.addMenu('Disambiguation')

        showSelectionAct = QAction('Show selected option', self)
        showSelectionAct.triggered.connect(self.showTableSelection)
        showSelectionAct.setShortcut('Ctrl+N')
        disambiguationMenu.addAction(showSelectionAct)

        windowsMenu = menubar.addMenu('Windows')

        self.showHideRequests = QAction('Requests', self)
        self.showHideRequests.triggered.connect(self.queryUI.showHideRequests)
        windowsMenu.addAction(self.showHideRequests)

        self.showHideRequestOperation = QAction('Operations', self)
        self.showHideRequestOperation.triggered.connect(self.queryUI.showHideRequestOperation)
        windowsMenu.addAction(self.showHideRequestOperation)

        showHideConsole = QAction('Console', self)
        showHideConsole.triggered.connect(self.showHideConsole)
        windowsMenu.addAction(showHideConsole)

        showHideQuery = QAction('Query', self)
        showHideQuery.triggered.connect(self.showHideQuery)
        windowsMenu.addAction(showHideQuery)

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

    def setManualMode(self):
        if self.queryText.isReadOnly():
            reply = QMessageBox.question(self, "Manual mode", "Are you sure?\nThe interactive mode will remain as it is now.")

            if reply == QMessageBox.Yes:
                self.queryText.setReadOnly(False)

                if self.queryUI.isHidden():
                    self.queryUI.showHideRequests()
                self.queryUI.hide()
                for action in self.requestMenu.actions():
                    action.setEnabled(False)
                self.manualModeAct.setEnabled(True)
                self.showHideRequests.setEnabled(False)
                self.showHideRequestOperation.setEnabled(False)

                logging.info("Switching to manual mode.")
        else:
            reply = QMessageBox.question(self, "Interactive mode", "Are you sure?\nThe current query will be removed.")

            if reply == QMessageBox.Yes:
                try:
                    self.queryText.setText(self.queryUI.getQuery().getQL())
                except RuntimeError:
                    logging.warning("Failed to write query.")
                    self.queryText.setText("")

                self.queryText.setReadOnly(True)

                self.queryUI.show()
                for action in self.requestMenu.actions():
                    action.setEnabled(True)
                self.showHideRequests.setEnabled(True)
                self.showHideRequestOperation.setEnabled(True)

                logging.info("Switching to interactive mode.")

    def playQuery(self):
        if self.queryText.isReadOnly():
            try:
                self.queryText.setText(self.queryUI.getQuery().getQL())
            except RuntimeError as e:
                logging.error(str(e))
                return

        try:
            self.mapRenderer.load(buildHTMLWithQuery(self.queryText.toPlainText()))
            logging.info("Query drawn.")
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given query.")
        except RequestException:
            logging.error("There was a problem with the internet connection.")
        except OSError:
            logging.error("There was a problem creating the file with the request response.")

    def saveNet(self):
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save File')
        buildNet(filename)
        return filename

    def openNet(self):
        try:
            openNetedit(self.saveNet() + ".net.xml")
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
