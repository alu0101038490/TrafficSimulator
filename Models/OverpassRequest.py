from constants import Surround, OsmType


class OverpassRequest(object):

    def __init__(self, requestType, surrounding, aroundRadius=100):
        super().__init__()
        self.type = requestType
        self.filters = {}
        self.surrounding = surrounding
        self.aroundRadius = aroundRadius
        self.polygon = []
        self.locationId = None

    def setLocationId(self, locationID):
        self.locationId = locationID

    def addFilter(self, key, value, exactValue, negated):
        self.filters[key] = (value, '=' if exactValue else '~', "!" if negated else '')

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

        for key, (value, exact, negated) in self.filters.items():
            if value:
                ql += '["{}"{}{}"{}"]'.format(key, negated, exact, value)
            else:
                ql += '[{}"{}"]'.format(negated, key)

        if self.surrounding == Surround.AROUND:
            ql += ";{}(around:{});)".format(self.type.value, str(self.aroundRadius))
        elif self.surrounding == Surround.ADJACENT:
            ql += ";>;way(bn);>;)"
        return ql
