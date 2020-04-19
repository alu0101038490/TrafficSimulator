import json
from datetime import datetime

from Operation.Model.OverpassOperations import OverpassUnion, OverpassIntersection, OverpassDiff
from Request.Model.OverpassRequest import OverpassRequest
from Shared.Utils.GenericUtils import nextString
from Shared.constants import tempDir


class OverpassQuery(object):
    setName = "a"

    def __init__(self, outputSet):
        super().__init__()
        self.requests = {}
        self.outputSet = outputSet
        self.ops = {}
        self.config = {}

    def addDate(self, date):
        if date != datetime.today().date():
            self.config["date"] = date.strftime("%Y-%m-%dT00:00:00Z")

    @classmethod
    def getUniqueSetName(cls):
        lastSetName = cls.setName
        cls.setName = nextString(lastSetName)
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

    def getDict(self):
        return {"requests": {key: value.getDict() for key, value in self.requests.items()},
                "outputSet": self.outputSet,
                "operations": {key: value.getDict() for key, value in self.ops.items()},
                "configuration": self.config}

    def saveToFile(self):
        with open(tempDir.join(["query.json"]), "w+") as f:
            json.dump(self.getDict(), f, indent=3)

    @staticmethod
    def getFromFile():
        with open(tempDir.join(["query.json"]), "r") as f:
            dictQuery = json.load(f)

        query = OverpassQuery(dictQuery["outputSet"])
        query.config = dictQuery["configuration"]
        for name, request in dictQuery["request"]:
            query.addRequest(name, OverpassRequest.getRequestFromDict(request))
        for name, op in dictQuery["operations"]:
            if op["type"] == "Union":
                query.addSetsOp(name, OverpassUnion.getOpFromDict(op))
            elif op["type"] == "Intersection":
                query.addSetsOp(name, OverpassIntersection.getOpFromDict(op))
            elif op["type"] == "Difference":
                query.addSetsOp(name, OverpassDiff.getOpFromDict(op))
        return query
