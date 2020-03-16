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
        self.sets = []

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
        return "(.%s;)" % ";.".join(self.sets)

    def isValid(self):
        return len(self.sets) > 1


class OverpassIntersection(OverpassSetOp):

    def __init__(self):
        super().__init__()

    def getType(self):
        return "Intersection"

    def getQL(self):
        return "way.%s" % ".".join(self.sets)

    def isValid(self):
        return len(self.sets) > 1


class OverpassDiff(OverpassSetOp):

    def __init__(self, includedSet):
        super().__init__()
        self.includedSet = includedSet

    def getType(self):
        return "Difference"

    def changeIncludedSet(self, set):
        self.includedSet = set

    def removeSet(self, set):
        if set == self.includedSet:
            self.includedSet = ""
        else:
            super().removeSet(set)

    def getQL(self):
        return "(%s;-.%s;)" % (self.includedSet, ";-.".join(self.sets))

    def isValid(self):
        return len(self.sets) > 0 and self.includedSet != ""


class OverpassRequest(object):

    def __init__(self, surrounding, aroundRadius=100):
        super().__init__()
        self.filters = {}
        self.surrounding = surrounding
        self.aroundRadius = aroundRadius

    def addFilter(self, key, value, exactValue):
        self.filters[key] = (value, exactValue)

    def getQL(self):
        ql = "(way" if self.surrounding == Surround.AROUND else "way"
        for key, (value, exact) in self.filters.items():
            ql += '["' + key + '"'
            ql += '=' if exact else '~'
            ql += '"' + value + '"]'
        if self.surrounding == Surround.AROUND:
            ql += ";way(around:" + str(self.aroundRadius) + ");)"
        return ql


class OverpassQuery(object):
    setName = "a"

    def __init__(self, outputSet):
        super().__init__()
        self.requests = {}
        self.outputSet = outputSet
        self.ops = {}

    @classmethod
    def getSetName(self):
        lastSetName = self.setName
        self.setName = nextString(lastSetName)
        return lastSetName

    def addRequest(self, name, request):
        self.requests[name] = request

    def changeOutputSet(self, name):
        self.outputSet = name

    def addSetsOp(self, name, op):
        self.ops[name] = op

    def getQL(self):
        statement = ""
        for name, request in self.requests.items():
            statement += request.getQL() + "->." + name + ";\n"

        for name, op in self.ops.items():
            statement += op.getQL() + "->." + name + ";\n"

        return "%s(%s;>;);\nout meta;" % (statement, self.outputSet)
