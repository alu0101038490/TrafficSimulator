from enum import Enum
from abc import ABC, abstractmethod

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

    @abstractmethod
    def getQL(self):
        pass

class OverpassUnion(OverpassSetOp):

    def __init__(self):
        super().__init__()

    def getQL(self):
        return "(.%s;)" % ";.".join(self.sets)

class OverpassIntersection(OverpassSetOp):

    def __init__(self):
        super().__init__()

    def getQL(self):
        return "way.%s" % ".".join(self.sets)

class OverpassDiff(OverpassSetOp):

    def __init__(self, includedSet):
        super().__init__()
        self.includedSet = includedSet

    def changeIncludedSet(self, set):
        self.includedSet = set

    def getQL(self):
        return "(%s;-.%s;)" % (self.includedSet, ";-.".join(self.sets))

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

    def __init__(self, outputSet):
        super().__init__()
        self.requests = {}
        self.outputSet = outputSet
        self.ops = {}

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

        return "%s(%s;>;);\nout meta;" %(statement, self.outputSet)
