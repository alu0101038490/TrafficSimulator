import os
import pathlib
import subprocess
import osmnx as ox

import requests
from PyQt5.QtCore import QUrl

from Views import osmBuild, sumolib

resDir = pathlib.Path(__file__).parent.parent.absolute().joinpath("Resources")
responsePath = os.path.join(resDir, "temp", "response.osm.xml")
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


def buildHTML(query):
    overpassUrl = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpassUrl, params={'data': query})

    f = open(responsePath, "w+")
    f.seek(0)
    f.truncate()
    f.write(response.text)
    f.close()

    G = ox.graph_from_file(responsePath)
    graphMap = ox.plot_graph_folium(G, popup_attribute='name', edge_width=2)
    graphMap.save(tilePath)

    return QUrl.fromLocalFile(tilePath)
