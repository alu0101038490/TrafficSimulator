from enum import Enum


class Surround(Enum):
    AROUND = 1
    ADJACENT = 2
    NONE = 3


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

    def __init__(self):
        super().__init__()
        self.requests = {}

    def addRequest(self, name, request):
        self.requests[name] = request

    def getQL(self):
        statement = ""
        combination = "(\n"
        for name, request in self.requests.items():
            statement += request.getQL() + "->." + name + ";\n"
            combination += "\t." + name + ";\n"

        return statement + combination + "\t>;\n);\nout meta;"
