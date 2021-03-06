import datetime
import json
import logging
import os
import sys
import traceback
from os.path import expanduser

import bs4
import osmnx as ox
import pyperclip
import qtmodern.styles
import qtmodern.windows
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QFileDialog, QSplitter, QHBoxLayout, QMessageBox, QLabel, QVBoxLayout, QSizePolicy, QWIDGETSIZE_MAX

from Query.Model.OverpassQuery import OverpassQuery
from Query.View.QueryUI import QueryUI
from Shared.Exceptions.OverpassExceptions import OverpassRequestException, OsmnxException
from Shared.Utils.OverpassUtils import OverpassQLHighlighter
from Shared.Utils.SumoUtils import buildNet, openNetedit, buildHTMLWithQuery
from Shared.View.Console import InformationalConsole
from Shared.View.NumberedTextEdit import CodeEditor
from Shared.constants import tempDir, APP_STYLESHEET, EMPTY_HTML, TagComparison, MANUAL_MODE_JS_SCRIPT
from Tag.Exception.BadFilterAttributes import BadFilterAttributes
from Tag.Model.OverpassFilter import OverpassFilter


class POSM(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setLocale(QLocale(QLocale.English))
        self.initUI()
        self.setAttribute(Qt.WA_AlwaysShowToolTips)
        sizegrip = QtWidgets.QSizeGrip(self)
        self.layout.addWidget(sizegrip, 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight)

        self.record = [None]
        recordAction = QAction(datetime.datetime.now().strftime('%H:%M:%S'), self)
        recordAction.triggered.connect(lambda: self.changeMap(0))
        self.recordMenu.addAction(recordAction)

    def initUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.console = InformationalConsole(app)

        self.horSplitter = QSplitter(Qt.Horizontal)
        self.horSplitter.setChildrenCollapsible(False)
        self.editionSplitter = QSplitter(Qt.Vertical)
        self.editionSplitter.setChildrenCollapsible(False)

        self.queryUI = QueryUI()
        self.queryUI.setOnRequestChanged(self.changeCurrentMap)
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

        self.emptyMapPage = QWebEnginePage()
        self.emptyMapPage.setHtml(EMPTY_HTML)

        self.manualModePage = QWebEnginePage()
        soup = bs4.BeautifulSoup(EMPTY_HTML, features="html.parser")
        js = soup.new_tag("script")
        js.string = (MANUAL_MODE_JS_SCRIPT % (str([])))
        soup.append(js)

        self.manualModePage.setHtml(str(soup))

        self.mapRenderer = QWebEngineView()
        self.mapRenderer.setMinimumWidth(500)
        self.mapRenderer.setPage(self.emptyMapPage)

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

        saveMenu = fileMenu.addMenu("Save")

        saveOutputAct = QAction('output', self)
        saveOutputAct.triggered.connect(self.saveNet)
        saveOutputAct.setShortcut('Ctrl+S')
        saveMenu.addAction(saveOutputAct)

        saveQueryAct = QAction('query', self)
        saveQueryAct.triggered.connect(self.saveQuery)
        saveQueryAct.setShortcut('Ctrl+Shift+S')
        saveMenu.addAction(saveQueryAct)

        saveInteractiveModeAct = QAction('interactive mode', self)
        saveInteractiveModeAct.triggered.connect(self.saveInteractiveQuery)
        saveMenu.addAction(saveInteractiveModeAct)

        openMenu = fileMenu.addMenu("Open")

        openQuery = QAction('query', self)
        openQuery.triggered.connect(self.openQuery)
        openQuery.setShortcut('Ctrl+O')
        openMenu.addAction(openQuery)

        openInteractiveMode = QAction('interactive mode', self)
        openInteractiveMode.triggered.connect(self.openInteractiveQuery)
        openMenu.addAction(openInteractiveMode)

        self.recordMenu = openMenu.addMenu("record")

        runMenu = menubar.addMenu('Run')

        playAct = QAction('Play', self)
        playAct.triggered.connect(self.playQuery)
        playAct.setShortcut('Ctrl+P')
        runMenu.addAction(playAct)

        playTableRowAct = QAction('Play row selection', self)
        playTableRowAct.triggered.connect(self.playTableRow)
        playTableRowAct.setShortcut('Ctrl+T')
        runMenu.addAction(playTableRowAct)

        self.requestMenu = menubar.addMenu('Request')

        addRequestAct = QAction('Add request', self)
        addRequestAct.triggered.connect(lambda b: self.addRequest())
        addRequestAct.setShortcut('Ctrl+A')
        self.requestMenu.addAction(addRequestAct)

        templatesMenu = self.requestMenu.addMenu("Add template")

        addRoadAct = QAction('Roads', self)
        addRoadAct.triggered.connect(lambda: self.addTemplate([
            OverpassFilter("highway", TagComparison.EQUAL, "", False, True),
            OverpassFilter("name", TagComparison.EQUAL, "", False, True),
            OverpassFilter("ref", TagComparison.EQUAL, "", False, True),
            OverpassFilter("maxspeed", TagComparison.AT_MOST, "120", False, False),
            OverpassFilter("lanes", TagComparison.EQUAL, "", False, True),
            OverpassFilter("oneway", TagComparison.EQUAL, "", False, True)]))
        templatesMenu.addAction(addRoadAct)

        addMainRoadAct = QAction('Main roads', self)
        mainHighways = "^(motorway|trunk|primary|secondary|residential)(_link)?$"
        everythingButYes = "^(y(e([^s]|$|s.)|[^e]|$)|[^y]|$).*"
        addMainRoadAct.triggered.connect(lambda: self.addTemplate([
            OverpassFilter("highway", TagComparison.EQUAL, mainHighways, False, False),
            OverpassFilter("construction", TagComparison.HAS_NOT_KEY, "", False, False),
            OverpassFilter("noexit", TagComparison.EQUAL, "yes", True, True),
            OverpassFilter("access", TagComparison.EQUAL, everythingButYes, True, False)]))
        templatesMenu.addAction(addMainRoadAct)

        addParkingAct = QAction('Parking', self)
        addParkingAct.triggered.connect(lambda: self.addTemplate([
            OverpassFilter("service", TagComparison.EQUAL, "parking", False, False),
            OverpassFilter("highway", TagComparison.HAS_KEY, "", False, True)]))
        templatesMenu.addAction(addParkingAct)

        addPedestriansAct = QAction('Pedestrians', self)
        pedestrianHighway = ["pedestrian", "footway", "path", "cycleway", "bridleway", "steps", "crossing"]
        addPedestriansAct.triggered.connect(lambda: self.addTemplate([
            OverpassFilter("highway", TagComparison.IS_ONE_OF, pedestrianHighway, False, True)]))
        templatesMenu.addAction(addPedestriansAct)

        removeRequestAct = QAction('Remove current request', self)
        removeRequestAct.triggered.connect(self.removeRequest)
        removeRequestAct.setShortcut('Ctrl+R')
        self.requestMenu.addAction(removeRequestAct)

        self.manualModeAct = QAction('Switch between interactive and manual mode', self)
        self.manualModeAct.triggered.connect(self.switchManualMode)
        self.requestMenu.addAction(self.manualModeAct)

        self.manualModeMenu = menubar.addMenu('Manual mode')
        self.manualModeMenu.setEnabled(False)

        manualModeCleanPolygonAct = QAction('Clean polygon', self)
        manualModeCleanPolygonAct.triggered.connect(self.cleanManualModePolygon)
        self.manualModeMenu.addAction(manualModeCleanPolygonAct)

        manualModeGetPolygonAct = QAction('Polygon coordinates', self)
        manualModeGetPolygonAct.triggered.connect(
            lambda: self.manualModePage.runJavaScript("getPolygons();", self.logManualModePolygonCoords))
        self.manualModeMenu.addAction(manualModeGetPolygonAct)

        windowsMenu = menubar.addMenu('Windows')

        cleanMapAct = QAction('Clean map', self)
        cleanMapAct.triggered.connect(self.cleanMap)
        windowsMenu.addAction(cleanMapAct)

        self.showHideInteractiveModeAct = QAction('Interactive mode', self)
        self.showHideInteractiveModeAct.triggered.connect(self.showHideInteractiveMode)
        windowsMenu.addAction(self.showHideInteractiveModeAct)

        showHideConsole = QAction('Console', self)
        showHideConsole.triggered.connect(self.showHideConsole)
        windowsMenu.addAction(showHideConsole)

        showHideQuery = QAction('Query', self)
        showHideQuery.triggered.connect(self.showHideQuery)
        windowsMenu.addAction(showHideQuery)

    # ACTIONS
    def cleanMap(self):
        if self.queryText.isReadOnly():
            if self.queryUI.getCurrentMap() is not None:
                self.mapRenderer.setPage(self.queryUI.updateMaps(EMPTY_HTML))
        else:
            soup = bs4.BeautifulSoup(EMPTY_HTML, features="html.parser")
            js = soup.new_tag("script")
            js.string = (MANUAL_MODE_JS_SCRIPT % (str([])))
            soup.append(js)
            self.manualModePage.setHtml(str(soup))

        logging.info("Cleaning map")

    def changeMap(self, i):
        if i == 0:
            if not self.queryText.isReadOnly():
                self.switchManualMode()
            if self.queryText.isReadOnly():
                self.queryUI.reset()
                self.queryText.clear()
                self.mapRenderer.setPage(self.emptyMapPage)
                self.queryUI.updateMaps(EMPTY_HTML)
        elif self.record[i]["interactiveMode"]:
            if not self.queryText.isReadOnly():
                self.switchManualMode()
            if self.queryText.isReadOnly():
                self.queryUI.setQuery(self.record[i]["query"])
                self.queryText.setPlainText(self.record[i]["query"].getQL())
                self.mapRenderer.setPage(self.queryUI.updateMaps(self.record[i]["html"]))
        else:
            if self.queryText.isReadOnly():
                self.switchManualMode()
            if not self.queryText.isReadOnly():
                self.queryUI.reset()
                self.queryText.setPlainText(self.record[i]["query"])
                self.manualModePage.setHtml(self.record[i]["html"])
                self.mapRenderer.setPage(self.manualModePage)

    def logManualModePolygonCoords(self, coords):
        coordsString = " ".join([str(c) for point in coords for c in point])
        logging.info("Polygon coordinates:\"{}\"".format(coordsString))
        pyperclip.copy(coordsString)
        logging.debug("LINE")

    def cleanManualModePolygon(self):
        logging.info("Cleaning polygon.")
        self.manualModePage.runJavaScript("cleanPolygon();", lambda returnValue: logging.debug("LINE"))

    def showHideInteractiveMode(self):
        if self.queryUI.isHidden():
            if self.editionSplitter.isHidden():
                self.editionSplitter.show()
                self.queryText.hide()
            self.queryUI.show()
            logging.info("Showing 'Interactive mode' window.")
        else:
            if self.queryText.isHidden():
                self.editionSplitter.hide()
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
            if self.editionSplitter.isHidden():
                self.editionSplitter.show()
                self.queryUI.hide()
            self.queryText.show()
            logging.info("Showing 'Query' window.")
            self.queryWidget.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            if self.queryUI.isHidden():
                self.editionSplitter.hide()
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
                self.mapRenderer.setPage(self.manualModePage)

                logging.info("Switching to manual mode.")
            else:
                logging.info("'Switch between interactive and manual mode' cancelled.")
        else:
            reply = QMessageBox.question(self, "Interactive mode", "Are you sure?\nThe current query will be removed.")

            if reply == QMessageBox.Yes:
                try:
                    self.queryText.clear()
                    self.queryText.setPlainText(self.queryUI.getQuery().getQL())
                except BadFilterAttributes as e:
                    logging.error(str(e))
                except RuntimeError:
                    logging.warning("Failed to write query.")
                    self.queryText.clear()
                    self.queryText.setPlainText("")

                self.queryText.setReadOnly(True)

                self.queryUI.show()
                for action in self.requestMenu.actions():
                    action.setEnabled(True)
                self.manualModeMenu.setEnabled(False)
                self.showHideInteractiveModeAct.setEnabled(True)
                self.changeCurrentMap(0)

                logging.info("Switching to interactive mode.")
            else:
                logging.info("'Switch between interactive and manual mode' cancelled.")

        logging.info("Showing 'manual mode' polygon.")

    def addRequest(self, filters=None):
        self.queryUI.addRequestByFilters(filters)
        logging.info("Request added.")
        logging.debug("LINE")

    def addTemplate(self, filters):
        logging.info("Template applied.")
        self.queryUI.addRequestByFilters(filters)

    def removeRequest(self):
        reply = QMessageBox.question(self, "Remove current request",
                                     "Are you sure? This option is not undoable.")

        if reply == QMessageBox.Yes:
            self.queryUI.removeRequest()
            logging.info("'Remove request' successfully executed.")
        else:
            logging.info("'Remove request' cancelled.")
        logging.debug("LINE")

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
                except (RuntimeError, BadFilterAttributes) as e:
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
        filename, selectedFilter = QFileDialog.getOpenFileName(self, 'Open query', expanduser("~/filename.txt"))

        if filename != "":
            try:
                if self.queryText.isReadOnly():
                    self.switchManualMode()

                f = open(filename, "r")
                self.queryText.clear()
                self.queryText.setPlainText(f.read())
                f.close()

                logging.info("File read successfully.")
            except UnicodeDecodeError:
                logging.error("The given file is not readable as text.")
            except OSError:
                logging.error("There was a problem opening the query file.")
        else:
            logging.info("\"Open query\" canceled.")

        logging.debug("LINE")

    def saveInteractiveQuery(self):
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save query', expanduser("~/filename.json"),
                                                               "JSON files (*.json)")

        if filename != "":
            try:
                query = self.queryUI.getQuery()
                query.saveToFile(filename)
                logging.info("Query saved successfully.")
            except (RuntimeError, BadFilterAttributes) as e:
                logging.error(str(e))
            except OSError:
                logging.error("There was a problem creating the file with the query.")
        else:
            logging.info("\"Save query\" canceled.")

        logging.debug("LINE")

    def openInteractiveQuery(self):
        filename, selectedFilter = QFileDialog.getOpenFileName(self, 'Open query', expanduser("~/filename.json"))

        if filename != "":
            try:
                self.queryUI.setQuery(OverpassQuery.getFromFile(filename))

                if not self.queryText.isReadOnly():
                    self.switchManualMode()
            except json.decoder.JSONDecodeError:
                logging.error("The given file has not the right format (json). The file could not be opened.")
            except UnicodeDecodeError:
                logging.error("The given file is not readable as text. The file could not be opened.")
            except (TypeError, KeyError):
                logging.error("Fields are missing from the file or there are fields with the wrong data type. "
                              "The file could not be opened.")
            except OSError:
                logging.error("There was a problem opening the query file. The file could not be opened.")
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

    # POLYGONS
    def changeCurrentMap(self, i):
        if self.queryUI.getCurrentMap() is None:
            self.mapRenderer.setPage(self.emptyMapPage)
        else:
            self.mapRenderer.setPage(self.queryUI.getCurrentMap())

    def playQuery(self):
        newRecord = {"interactiveMode": self.queryText.isReadOnly(), "query": self.queryText.toPlainText(), "html": ""}

        if self.queryText.isReadOnly():
            try:
                query = self.queryUI.getQuery()
                newRecord["query"] = query
                self.queryText.setPlainText(query.getQL())
            except (RuntimeError, BadFilterAttributes) as e:
                logging.error(str(e))
                return
        try:
            html = buildHTMLWithQuery(self.queryText.toPlainText())
            if self.queryText.isReadOnly():
                self.mapRenderer.setPage(self.queryUI.updateMaps(html))
                newRecord["html"] = html
            else:
                soup = bs4.BeautifulSoup(html, features="html.parser")
                js = soup.new_tag("script")
                js.string = (MANUAL_MODE_JS_SCRIPT % (str([])))
                soup.append(js)

                self.manualModePage.setHtml(str(soup))
                newRecord["html"] = str(soup)
                self.mapRenderer.setPage(self.manualModePage)
            logging.info("Query drawn.")
            logging.debug("LINE")
            self.addRecord(newRecord)
        except (OverpassRequestException, OsmnxException) as e:
            logging.error(str(e))
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given query.")
        except OSError:
            logging.error("There was a problem creating the file with the request response.")
        except Exception:
            logging.error(traceback.format_exc())

    def addRecord(self, newRecord):
        self.record.append(newRecord)
        index = len(self.record) - 1

        recordAction = QAction(datetime.datetime.now().strftime('%H:%M:%S'), self)
        recordAction.triggered.connect(lambda: self.changeMap(index))
        self.recordMenu.addAction(recordAction)

    def playTableRow(self):
        try:
            self.mapRenderer.setPage(self.queryUI.updateMapFromRow())
        except (OverpassRequestException, OsmnxException) as e:
            logging.error(str(e))
            logging.warning("Before open NETEDIT you must run a query with the row filters applied.")
        except ox.EmptyOverpassResponse:
            logging.error("There are no elements with the given row.")
        except OSError:
            logging.error("There was a problem creating the file with the row selection.")
        except RuntimeError as e:
            logging.error(str(e))
        except Exception:
            logging.error(traceback.format_exc())
        logging.debug("LINE")

    # EVENTS
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
