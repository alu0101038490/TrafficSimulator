from datetime import datetime

from Utils.GenericUtils import nextString


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
