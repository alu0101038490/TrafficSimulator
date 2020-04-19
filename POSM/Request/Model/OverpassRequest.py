from Shared.constants import OsmType, Surround
from Tag.Model.OverpassFilter import OverpassFilter


class OverpassRequest(object):

    def __init__(self, requestType, surrounding, aroundRadius=100):
        super().__init__()
        self.type = requestType
        self.filters = []
        self.surrounding = surrounding
        self.aroundRadius = aroundRadius
        self.polygon = []
        self.locationId = None

    def setLocationId(self, locationID):
        self.locationId = locationID

    def addFilterByValues(self, key, value, exactValue, negated):
        self.filters.append(OverpassFilter(key, value, exactValue, negated))

    def addFilter(self, filter):
        self.filters.append(filter)

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

        for filter in self.filters:
            ql += filter.getQL()

        if self.surrounding == Surround.AROUND:
            ql += ";{}(around:{});)".format(self.type.value, str(self.aroundRadius))
        elif self.surrounding == Surround.ADJACENT:
            ql += ";>;way(bn);>;)"
        return ql

    def getDict(self):
        return {"type": self.type.value,
                "filters": [singleFilter.getDict() for singleFilter in self.filters],
                "surrounding": self.surrounding.value,
                "aroundRadius": self.aroundRadius,
                "polygon": self.polygon,
                "location": self.locationId}

    @staticmethod
    def getRequestFromDict(dict):
        request = OverpassRequest(OsmType(dict["type"]),
                                  Surround(dict["surrounding"]),
                                  dict["aroundRadius"])
        request.addPolygon(dict["polygon"])
        request.setLocationId("location")
        for singleFilter in dict["filters"]:
            request.addFilter(OverpassFilter.getFilterFromDict(singleFilter))
        return request
