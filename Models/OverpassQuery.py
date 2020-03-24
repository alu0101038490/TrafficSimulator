import logging
from abc import ABC, abstractmethod
from enum import Enum

from Utils.GenericUtils import nextString


class Surround(Enum):
    AROUND = 1
    ADJACENT = 2
    NONE = 3

class OsmType(Enum):
    NODES = "node"
    WAYS = "way"
    RELATIONS = "rel"
    AREA = "area"
    NW = "nw"
    NR = "nr"
    WR = "wr"
    NWR = "nwr"

    @classmethod
    def getType(self, node, way, rel, area):
        type = (1 * node) | (2 * way) | (4 * rel)

        switchCase = [0, OsmType.NODES, OsmType.WAYS, OsmType.NW, OsmType.RELATIONS, OsmType.NR, OsmType.WR, OsmType.NWR]

        if area:
            return OsmType.AREA
        elif type == 0:
            raise RuntimeError("No type selected.")
        else:
            return switchCase[type]

class OverpassSetOp(ABC):

    def __init__(self):
        super().__init__()
        self.__sets = []

    @property
    def sets(self):
        return self.__sets

    def addSet(self, set):
        self.sets.append(set)

    def addSets(self, sets):
        self.sets.extend(sets)

    def removeSet(self, set):
        if set in self.sets:
            self.sets.remove(set)

    @abstractmethod
    def getType(self):
        pass

    @abstractmethod
    def getQL(self):
        pass

    @abstractmethod
    def isValid(self):
        pass


class OverpassUnion(OverpassSetOp):

    def __init__(self):
        super().__init__()

    def getType(self):
        return "Union"

    def getQL(self):
        if len(self.sets) == 0:
            raise RuntimeError("Union without sets")
        if len(self.sets) == 1:
            logging.warning("Getting query with invalid union.")
        return "(.%s;)" % ";.".join(self.sets)

    def isValid(self):
        return len(self.sets) > 1


class OverpassIntersection(OverpassSetOp):

    def __init__(self):
        super().__init__()

    def getType(self):
        return "Intersection"

    def getQL(self):
        if len(self.sets) == 0:
            raise RuntimeError("Intersection without sets")
        if len(self.sets) == 1:
            logging.warning("Getting query with invalid intersection.")
        return "way.%s" % ".".join(self.sets)

    def isValid(self):
        return len(self.sets) > 1


class OverpassDiff(OverpassSetOp):

    def __init__(self, includedSet):
        super().__init__()
        self.__includedSet = includedSet

    @property
    def includedSet(self):
        return self.__includedSet

    def getType(self):
        return "Difference"

    def changeIncludedSet(self, set):
        self.__includedSet = set

    def removeSet(self, set):
        if set == self.includedSet:
            self.__includedSet = ""
        else:
            super().removeSet(set)

    def getQL(self):
        if not self.isValid():
            raise RuntimeError("Difference without excluded sets nor included set.")
        return "(.%s;- .%s;)" % (self.includedSet, ";- .".join(self.sets))

    def isValid(self):
        return len(self.sets) > 0 and self.includedSet != ""


class OverpassRequest(object):

    def __init__(self, type, surrounding, aroundRadius=100):
        super().__init__()
        self.type = type
        self.filters = {}
        self.surrounding = surrounding
        self.aroundRadius = aroundRadius
        self.polygon = []
        self.locationId = None

    def setLocationId(self, id):
        self.locationId = id

    def addFilter(self, key, value, exactValue, negated):
        self.filters[key] = (value, '=' if exactValue else '~', "!" if negated else '')

    def addPolygon(self, coords):
        self.polygon = coords

    def getQL(self):
        if len(self.filters) == 0 and len(self.polygon) == 0 and self.locationId is None:
            raise RuntimeError("Empty request.")
        if not isinstance(self.type, OsmType):
            raise RuntimeError("Invalid osm type.")

        ql = "({}".format(self.type.value) if self.surrounding != Surround.NONE else self.type.value

        if self.locationId is not None:
            ql += "(area:{})".format(self.locationId)

        if len(self.polygon) > 0:
            ql += "(poly:\"%s\")" % " ".join([str(c) for point in self.polygon for c in point])

        for key, (value, exact, negated) in self.filters.items():
            if value:
                ql += '["{}"{}{}"{}"]'.format(key, negated, exact, value)
            else:
                ql += '[{}"{}"]'.format(negated, key)

        if self.surrounding == Surround.AROUND:
            ql += ";{}(around:{});)".format(self.type.value, str(self.aroundRadius))
        elif self.surrounding == Surround.ADJACENT:
            ql += ";>;way(bn);>;)"
        return ql


class OverpassQuery(object):
    setName = "a"

    def __init__(self, outputSet):
        super().__init__()
        self.requests = {}
        self.outputSet = outputSet
        self.ops = {}
        self.config = {}

    def addDate(self, date):
        self.config["date"] = date.strftime("%Y-%m-%dT00:00:00Z")

    @classmethod
    def getUniqueSetName(self):
        lastSetName = self.setName
        self.setName = nextString(lastSetName)
        return lastSetName

    def addRequest(self, name, request):
        self.requests[name] = request

    def changeOutputSet(self, name):
        self.outputSet = name

    def addSetsOp(self, name, op):
        self.ops[name] = op

    def addPolygon(self, i, polygon):
        self.requests[list(self.requests.keys())[i]].addPolygon(polygon)

    def getQL(self):
        if len(self.requests) == 0:
            raise RuntimeError("Query without requests.")

        statement = ""

        if len(self.config) > 0:
            for key, value in self.config.items():
                statement += "[{}:\"{}\"]".format(key, value)
            statement += ";\n"

        for name, request in self.requests.items():
            statement += request.getQL() + "->." + name + ";\n"

        for name, op in self.ops.items():
            statement += op.getQL() + "->." + name + ";\n"

        return "%s(.%s;>;);\nout meta;" % (statement, self.outputSet)
