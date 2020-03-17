import os
import pathlib
import subprocess
import xml.etree.ElementTree as ET

import osmnx as ox
import requests
from PyQt5.QtCore import QUrl

from Views import osmBuild, sumolib

resDir = pathlib.Path(__file__).parent.parent.absolute().joinpath("Resources")
tempDir = os.path.join(resDir, "temp")
responsePath = os.path.join(resDir, "temp", "response.osm.xml")
defaultTileMap = os.path.join(resDir, "html", "tile.html")
tilePath = os.path.join(resDir, "temp", "tile.html")
typemapPath = os.path.join(resDir, "typemap")


def buildNet(outputName, inputFileName=responsePath):
    typemaps = {
        "net": os.path.join(typemapPath, "osmNetconvert.typ.xml"),
        "poly": os.path.join(typemapPath, "osmPolyconvert.typ.xml"),
        "urban": os.path.join(typemapPath, "osmNetconvertUrbanDe.typ.xml"),
        "pedestrians": os.path.join(typemapPath, "osmNetconvertPedestrians.typ.xml"),
        "ships": os.path.join(typemapPath, "osmNetconvertShips.typ.xml"),
        "bicycles": os.path.join(typemapPath, "osmNetconvertBicycle.typ.xml"),
    }

    options = ["-f", inputFileName]
    options += ["-p", outputName]

    typefiles = [typemaps["net"]]
    netconvertOptions = osmBuild.DEFAULT_NETCONVERT_OPTS
    netconvertOptions += ",--tls.default-type,actuated"

    options += ["--netconvert-typemap", ','.join(typefiles)]
    options += ["--netconvert-options", netconvertOptions]

    osmBuild.build(options)


def openNetedit(inputName):
    netedit = sumolib.checkBinary("netedit")
    subprocess.Popen([netedit, inputName])


def writeXMLResponse(query, outputFilename=responsePath):
    overpassUrl = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpassUrl, params={'data': query})

    f = open(outputFilename, "w+")
    f.seek(0)
    f.truncate()
    f.write(response.text)
    f.close()


def getXML():
    return ET.parse(responsePath).getroot()


def getIntersections():
    root = getXML()
    nodes = [child for child in root if child.tag == "node"]
    ways = [child for child in root if child.tag == "way"]

    intersections = []
    for n in nodes:
        id = n.attrib["id"]
        appearances = []
        for w in ways:
            if id in [child.attrib["ref"] for child in list(w) if child.tag == "nd"]:
                appearances.append(w)

        if len(appearances) > 2:
            intersections.append(id)
        elif len(appearances) > 1:
            way1firstNode = appearances[0].find("./nd[1]").attrib["ref"]
            way2firstNode = appearances[1].find("./nd[1]").attrib["ref"]
            way1lastNode = appearances[0].find("./nd[last()]").attrib["ref"]
            way2lastNode = appearances[1].find("./nd[last()]").attrib["ref"]
            if len({way1firstNode, way2firstNode, way1lastNode, way2lastNode}) == 4:
                intersections.append(id)

    return intersections


def buildHTMLWithNetworkx(G):
    graphMap = ox.plot_graph_folium(G, popup_attribute='name', edge_width=2)
    graphMap.save(tilePath)

    return QUrl.fromLocalFile(tilePath)


def buildHTMLWithQuery(query):
    writeXMLResponse(query)
    G = ox.graph_from_file(responsePath, retain_all=True)

    return buildHTMLWithNetworkx(G)
