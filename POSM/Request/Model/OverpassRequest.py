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
        self.__ids = []
        self.__locationId = None
        self.__locationName = ""

    # REQUEST GETTERS

    @property
    def type(self):
        return self.__type

    @property
    def filters(self):
        return self.__filters

    @property
    def surrounding(self):
        return self.__surrounding

    @property
    def aroundRadius(self):
        return self.__aroundRadius

    @property
    def polygon(self):
        return self.__polygon

    @property
    def ids(self):
        return self.__ids

    @property
    def locationId(self):
        return self.__locationId

    @property
    def locationName(self):
        return self.__locationName

    def getQL(self):
        if len(self.filters) == 0 and len(self.polygon) == 0 and self.locationId is None and len(self.ids) == 0:
            raise RuntimeError("Empty request.")
        if not isinstance(self.type, OsmType):
            raise RuntimeError("Invalid osm type.")

        ql = "({}".format(self.type.value) if self.surrounding != Surround.NONE else self.type.value

        if self.locationId is not None:
            ql += "(area:{})".format(self.locationId)

        if len(self.ids) > 0:
            ql += "(id:{})".format(", ".join(self.ids))

        if len(self.polygon) > 0:
            ql += "(poly:\"%s\")" % " ".join([str(c) for point in self.polygon for c in point])

        ql += "".join([f.getQL() for f in self.filters])

        if self.surrounding == Surround.AROUND:
            ql += ";{}(around:{});)".format(self.type.value, str(self.aroundRadius))
        elif self.surrounding == Surround.ADJACENT:
            ql += ";>;way(bn);>;)"
        return ql + "->." + self.name + ";\n"

    # REQUEST SETTERS

    def setLocationName(self, locationName):
        self.__locationName = locationName
        self.__locationId = getIdFromLocationName(locationName)

    def addFilter(self, newFilter):
        self.filters.append(newFilter)

    def addPolygon(self, coords):
        self.__polygon = coords

    def setIds(self, ids):
        self.__ids = ids

    # EQUIVALENT JSON

    def getDict(self):
        return {"name": self.name,
                "type": self.type.value,
                "filters": [singleFilter.getDict() for singleFilter in self.filters],
                "surrounding": self.surrounding.value,
                "aroundRadius": self.aroundRadius,
                "polygon": self.polygon,
                "ids": self.ids,
                "location": self.locationName}

    @staticmethod
    def getRequestFromDict(requestDict):
        request = OverpassRequest(OsmType(requestDict["type"]),
                                  Surround(requestDict["surrounding"]),
                                  requestDict["name"],
                                  requestDict["aroundRadius"])
        request.addPolygon(requestDict["polygon"])
        request.setIds(requestDict["ids"])
        request.setLocationName(requestDict["location"])
        for singleFilter in requestDict["filters"]:
            request.addFilter(OverpassFilter.getFilterFromDict(singleFilter))
        return request
