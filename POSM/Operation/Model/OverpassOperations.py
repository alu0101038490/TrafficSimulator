import logging
from abc import ABC, abstractmethod

from Shared.Model.OverpassSet import OverpassSet


class OverpassSetOp(ABC, OverpassSet):

    def __init__(self, name):
        super().__init__(name)
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

    def getDict(self):
        return {"type": self.getType(), "sets": self.sets, "name": self.name}

    @staticmethod
    @abstractmethod
    def getOpFromDict(opDict):
        pass

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

    def __init__(self, name):
        super().__init__(name)

    @staticmethod
    def getOpFromDict(opDict):
        op = OverpassUnion(opDict["name"])
        op.addSets(opDict["sets"])
        return op

    def getType(self):
        return "Union"

    def getQL(self):
        if len(self.sets) == 0:
            raise RuntimeError("Union without sets")
        if len(self.sets) == 1:
            logging.warning("Getting query with invalid union.")
        return "(.%s;)->.%s;\n" % (";.".join(self.sets), self.setName)

    def isValid(self):
        return len(self.sets) > 1


class OverpassIntersection(OverpassSetOp):

    def __init__(self, name):
        super().__init__(name)

    @staticmethod
    def getOpFromDict(opDict):
        op = OverpassIntersection(opDict["name"])
        op.addSets(opDict["sets"])
        return op

    def getType(self):
        return "Intersection"

    def getQL(self):
        if len(self.sets) == 0:
            raise RuntimeError("Intersection without sets")
        if len(self.sets) == 1:
            logging.warning("Getting query with invalid intersection.")
        return "way.%s->.%s;\n" % (".".join(self.sets), self.setName)

    def isValid(self):
        return len(self.sets) > 1


class OverpassDiff(OverpassSetOp):

    def __init__(self, includedSet, name):
        super().__init__(name)
        self.__includedSet = includedSet

    @property
    def includedSet(self):
        return self.__includedSet

    def getDict(self):
        baseDict = super().getDict()
        baseDict["includedSet"] = self.includedSet
        return baseDict

    @staticmethod
    def getOpFromDict(opDict):
        op = OverpassDiff(opDict["includedSet"], opDict["name"])
        op.addSets(opDict["sets"])
        return op

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
        return "(.%s;- .%s;)->.%s;\n" % (self.includedSet, ";- .".join(self.sets), self.setName)

    def isValid(self):
        return len(self.sets) > 0 and self.includedSet != ""
