import logging
import os
import subprocess
import xml.etree.ElementTree as ET

import osmnx as ox
import requests

import osmBuild
import sumolib
from Shared.Exceptions.OverpassExceptions import UnknownException, TooManyRequestsException, TimeoutException, \
    OsmnxException, RequestSyntaxException
from Shared.constants import responsePath, tilePath, typemapPath


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
    overpassServers = ["http://overpass-api.de/api/interpreter",
                       "https://lz4.overpass-api.de/api/interpreter",
                       "https://z.overpass-api.de/api/interpreter"]
    serverUsed = 0
    response = requests.get(overpassServers[serverUsed], params={'data': query})
    retry = True
    kill = False
    while retry:
        if retry:
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                remarks = root.findall("./remark")
                if len(remarks) > 0:
                    raise UnknownException("Error messages: \n\t" + "\n\t".join(["".join(r.itertext()) for r in remarks]))
                else:
                    logging.info("Selected elements received.")
                    retry = False
            elif response.status_code == 400:
                root = ET.fromstring(response.text)
                errorList = "\n\t".join(["".join(root[1][i].itertext()) for i in range(1, len(root[1]))])
                raise RequestSyntaxException("Syntax errors: \n\t{}".format(errorList))
            elif response.status_code == 429:
                if serverUsed + 1 < len(overpassServers):
                    serverUsed += 1
                elif not kill:
                    kill = True
                    serverUsed = 0
                    for server in overpassServers:
                        requests.get(server.replace("interpreter", "kill_my_queries"))
                else:
                    raise TooManyRequestsException("You have done too many requests. Try later.")
                logging.warning("Too many requests. Trying another server.")
                response = requests.get(overpassServers[serverUsed], params={'data': query})
            elif response.status_code == 504:
                raise TimeoutException("Timeout. You should try a smaller 'timeout' and/or 'maxsize'.")
            else:
                response.raise_for_status()

    f = open(outputFilename, "w+")
    f.seek(0)
    f.truncate()
    f.write(response.text)
    f.close()

    logging.info("Selected elements written to file.")


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

    if len(intersections) > 0:
        logging.info("Intersections found.")
    else:
        logging.warning("No intersections found.")

    return intersections


def buildHTMLWithNetworkx(G):
    try:
        graphMap = ox.plot_graph_folium(G, popup_attribute='name', edge_width=2)
    except (ValueError, KeyError):
        raise OsmnxException("Probably there are elements without all its nodes. It is not possible to show the "
                             "results but you can use the option 'Open netedit'.")
    graphMap.save(tilePath)

    logging.info("Html built.")

    return graphMap.get_root().render()


def buildHTMLWithQuery(query):
    writeXMLResponse(query)
    try:
        if os.stat(responsePath).st_size >= 2097152:
            logging.warning("Response is too big. Maybe the map will not work properly but you can use the option "
                            "'Open netedit'.")
        G = ox.graph_from_file(responsePath, retain_all=True)
    except (ValueError, KeyError):
        raise OsmnxException("Probably there are elements without all its nodes. It is not possible to show the "
                             "results but you can use the option 'Open netedit'.")
    logging.info("Network built.")

    return buildHTMLWithNetworkx(G)
