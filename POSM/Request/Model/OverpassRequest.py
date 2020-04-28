from Shared.Model.OverpassSet import OverpassSet
from Shared.Utils.OverpassUtils import getIdFromLocationName
from Shared.constants import OsmType, Surround
from Tag.Model.OverpassFilter import OverpassFilter


class OverpassRequest(OverpassSet):

    def __init__(self, requestType, surrounding, name, aroundRadius=100):
        super().__init__(name)
        self.__type = requestType
        self.__filters = []
        self.__surrounding = surrounding
        self.__aroundRadius = aroundRadius
        self.__polygon = []
        self.__locationId = None
        self.__locationName = ""

    @property
    def type(self):
        return self.type

    @property
    def filters(self):
        return self.filters

    @property
    def surrounding(self):
        return self.surrounding

    @property
    def aroundRadius(self):
        return self.aroundRadius

    @property
    def polygon(self):
        return self.polygon

    @property
    def locationId(self):
        return self.locationId

    @property
    def locationName(self):
        return self.__locationName

    def setLocationName(self, locationName):
        self.__locationName = locationName
        self.__locationId = getIdFromLocationName(locationName)

    def addFilterByValues(self, key, value, exactValue, negated):
        self.filters.append(OverpassFilter(key, value, exactValue, negated))

    def addFilter(self, filter):
        self.filters.append(filter)

    def addPolygon(self, coords):
        self.__polygon = coords

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
        return ql + "->." + self.setName + ";\n"

    def getDict(self):
        return {"type": self.type.value,
                "filters": [singleFilter.getDict() for singleFilter in self.filters],
                "surrounding": self.surrounding.value,
                "aroundRadius": self.aroundRadius,
                "polygon": self.polygon,
                "location": self.locationId}

    @staticmethod
    def getRequestFromDict(requestDict):
        request = OverpassRequest(OsmType(requestDict["type"]),
                                  Surround(requestDict["surrounding"]),
                                  requestDict["aroundRadius"])
        request.addPolygon(requestDict["polygon"])
        request.setLocationName("location")
        for singleFilter in requestDict["filters"]:
            request.addFilter(OverpassFilter.getFilterFromDict(singleFilter))
        return request
