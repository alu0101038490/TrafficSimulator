import os
import subprocess
import sys

import osmnx as ox
import requests
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, \
    QTextEdit, QFileDialog, QSplitter, QHBoxLayout, QPushButton

from Views import osmBuild, sumolib
from Views.EditionWidget import EditionWidget


class POSM(QMainWindow):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QHBoxLayout()

        self.horSplitter = QSplitter(Qt.Horizontal)
        self.editionSplitter = QSplitter(Qt.Vertical)
        self.editionWidget = EditionWidget()
        self.editionSplitter.addWidget(self.editionWidget)
        self.query = QTextEdit()
        self.query.setText("out meta;")
        self.editionSplitter.addWidget(self.query)
        self.horSplitter.addWidget(self.editionSplitter)
        self.mplCanvas = QWebEngineView()
        self.mplCanvas.setMinimumWidth(500)
        self.horSplitter.addWidget(self.mplCanvas)
        self.layout.addWidget(self.horSplitter)

        self.initMenuBar()

        centralWidget = QWidget()
        centralWidget.setLayout(self.layout)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle('Python Open Street Map')

    def initMenuBar(self):
        menubar = self.menuBar()

        fileMenu = menubar.addMenu('File')

        openAct = QAction('Open netedit', self)
        openAct.triggered.connect(lambda: fileSaveAndOpen(self))
        openAct.setShortcut('Ctrl+O')
        fileMenu.addAction(openAct)

        saveAct = QAction('Save output', self)
        saveAct.triggered.connect(lambda: fileSave(self))
        saveAct.setShortcut('Ctrl+S')
        fileMenu.addAction(saveAct)

        runMenu = menubar.addMenu('Run')

        playAct = QAction('Play', self)
        playAct.triggered.connect(self.playQuery)
        playAct.setShortcut('Ctrl+P')
        runMenu.addAction(playAct)

        tagsMenu = menubar.addMenu('Tags')

        addAct = QAction('Add tag', self)
        addAct.triggered.connect(self.editionWidget.addFitler)
        addAct.setShortcut('Ctrl+A')
        tagsMenu.addAction(addAct)

        removeAct = QAction('Remove current tag', self)
        removeAct.triggered.connect(self.editionWidget.removeFilter)
        removeAct.setShortcut('Ctrl+R')
        tagsMenu.addAction(removeAct)

        addKeyValue = QAction('Add key/value', self)
        addKeyValue.triggered.connect(self.editionWidget.addKeyValue)
        addKeyValue.setShortcut('Ctrl+K')
        tagsMenu.addAction(addKeyValue)

        removeKeyValue = QAction('Remove selected key/value', self)
        removeKeyValue.triggered.connect(self.editionWidget.removeKeyValue)
        removeKeyValue.setShortcut('Ctrl+D')
        tagsMenu.addAction(removeKeyValue)

    def playQuery(self):
        self.query.setText(str(self.editionWidget.getQuery()))
        self.mplCanvas.load(callOverpass(self.query.toPlainText()))

def fileSave(parent):
    name, selectedFilter = QFileDialog.getSaveFileName(parent, 'Save File')
    build(name)


def fileSaveAndOpen(parent):
    name, selectedFilter = QFileDialog.getSaveFileName(parent, 'Save File')
    build(name)
    openNetedit(name + ".net.xml")


def build(name):
    typemapdir = os.path.join(os.getcwd(), "typemap")
    typemaps = {
        "net": os.path.join(typemapdir, "osmNetconvert.typ.xml"),
        "poly": os.path.join(typemapdir, "osmPolyconvert.typ.xml"),
        "urban": os.path.join(typemapdir, "osmNetconvertUrbanDe.typ.xml"),
        "pedestrians": os.path.join(typemapdir, "osmNetconvertPedestrians.typ.xml"),
        "ships": os.path.join(typemapdir, "osmNetconvertShips.typ.xml"),
        "bicycles": os.path.join(typemapdir, "osmNetconvertBicycle.typ.xml"),
    }

    options = ["-f", os.path.join(os.getcwd(), "map.osm.xml")]
    options += ["-p", name]

    typefiles = [typemaps["net"]]
    netconvertOptions = osmBuild.DEFAULT_NETCONVERT_OPTS
    netconvertOptions += ",--tls.default-type,actuated"

    options += ["--netconvert-typemap", ','.join(typefiles)]
    options += ["--netconvert-options", netconvertOptions]

    osmBuild.build(options)


def openNetedit(name):
    netedit = sumolib.checkBinary("netedit")
    subprocess.Popen([netedit, name])


def callOverpass(query):
    print("Sending request")
    overpass_url = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpass_url, params={'data': query})
    print("Got response")
    f = open(os.path.join(os.getcwd(), "map.osm.xml"), "w+")
    f.seek(0)
    f.truncate()
    f.write(response.text)
    f.close()
    print("File written")

    G = ox.graph_from_file(os.path.join(os.getcwd(), "map.osm.xml"))
    graph_map = ox.plot_graph_folium(G, popup_attribute='name', edge_width=2)
    graph_map.save(os.path.join(os.getcwd(), "graph.html"))

    return QUrl.fromLocalFile(os.path.join(os.getcwd(), "graph.html"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = POSM()
    ex.show()
    sys.exit(app.exec_())