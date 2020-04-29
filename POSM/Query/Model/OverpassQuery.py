import json
from datetime import datetime

from Operation.Model.OverpassOperations import OverpassUnion, OverpassIntersection, OverpassDiff
from Request.Model.OverpassRequest import OverpassRequest
from Shared.constants import tempDir


class OverpassQuery(object):

    def __init__(self, outputSet):
        super().__init__()
        self.__requests = []
        self.__outputSet = outputSet
        self.__ops = []
        self.__config = {}

    @property
    def requests(self):
        return self.__requests

    @property
    def outputSet(self):
        return self.__outputSet

    @property
    def ops(self):
        return self.__ops

    @property
    def config(self):
        return self.__config

    def addDate(self, date):
        if date != datetime.today().date():
            self.__config["date"] = date.strftime("%Y-%m-%dT00:00:00Z")

    def addRequest(self, request):
        self.__requests.append(request)

    def changeOutputSet(self, name):
        self.__outputSet = name

    def addSetsOp(self, op):
        self.__ops.append(op)

    def getQL(self):
        if len(self.__requests) == 0:
            raise RuntimeError("Query without requests.")

        statement = ""

        if len(self.__config) > 0:
            for key, value in self.__config.items():
                statement += "[{}:\"{}\"]".format(key, value)
            statement += ";\n"

        for request in self.__requests:
            statement += request.getQL()

        for op in self.__ops:
            statement += op.getQL()

        return "%s(.%s;>;);\nout meta;" % (statement, self.__outputSet)

    def getDict(self):
        return {"requests": [request.getDict() for request in self.__requests],
                "outputSet": self.__outputSet,
                "operations": [op.getDict() for op in self.__ops],
                "configuration": self.__config}

    def saveToFile(self):
        with open(tempDir.join(["query.json"]), "w+") as f:
            json.dump(self.getDict(), f, indent=3)

    @staticmethod
    def getFromFile():
        with open(tempDir.join(["query.json"]), "r") as f:
            dictQuery = json.load(f)

        query = OverpassQuery(dictQuery["outputSet"])
        query.__config = dictQuery["configuration"]
        for request in dictQuery["requests"]:
            query.addRequest(OverpassRequest.getRequestFromDict(request))
        for op in dictQuery["operations"]:
            if op["type"] == "Union":
                query.addSetsOp(OverpassUnion.getOpFromDict(op))
            elif op["type"] == "Intersection":
                query.addSetsOp(OverpassIntersection.getOpFromDict(op))
            elif op["type"] == "Difference":
                query.addSetsOp(OverpassDiff.getOpFromDict(op))
        return query
