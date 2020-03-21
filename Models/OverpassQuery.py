import logging
from abc import ABC, abstractmethod
from enum import Enum

from Utils.GenericUtils import nextString


class Surround(Enum):
    AROUND = 1
    ADJACENT = 2
    NONE = 3


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

    def __init__(self, surrounding, aroundRadius=100):
        super().__init__()
        self.filters = {}
        self.surrounding = surrounding
        self.aroundRadius = aroundRadius
        self.polygon = []

    def addFilter(self, key, value, exactValue):
        self.filters[key] = (value, exactValue)

    def addPolygon(self, coords):
        self.polygon = coords

    def getQL(self):
        if len(self.filters) == 0:
            raise RuntimeError("Request without filters.")
        ql = "(way" if self.surrounding != Surround.NONE else "way"
        if len(self.polygon) > 0:
            coords = ""
            for point in self.polygon:
                for c in point:
                    coords += " {}".format(c)
            ql += "(poly:\"%s\")" % coords
        for key, (value, exact) in self.filters.items():
            ql += '["{}"{}"{}"]'.format(key, '=' if exact else '~', value)
        if self.surrounding == Surround.AROUND:
            ql += ";way(around:" + str(self.aroundRadius) + ");)"
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
        for name, request in self.requests.items():
            statement += request.getQL() + "->." + name + ";\n"

        for name, op in self.ops.items():
            statement += op.getQL() + "->." + name + ";\n"

        return "%s(.%s;>;);\nout meta;" % (statement, self.outputSet)
