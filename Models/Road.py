from enum import Enum
from math import hypot, atan2, degrees, radians, cos, sin, sqrt


class Road(object):

    def __init__(self, speedLimit):
        self.__speedLimit = speedLimit
        self.__connections = {}

    @property
    def speedLimit(self):
        return self.__speedLimit

    @speedLimit.setter
    def speedLimit(self, speedLimit):
        self.__speedLimit = speedLimit

    def addConnection(self, x, y, connectedRoad):
        self.__connections[(x, y)] = connectedRoad

    def removeConnection(self, point):
        del self.__connections[point]


class NonIntersection(Road):

    def __init__(self, speedLimit, overtakingPossibility, origin, end):
        super().__init__(speedLimit)
        self.__overtakingPossibility = overtakingPossibility
        self.__origin = origin
        self.__end = end
        self.__lanes = []

    @property
    def lanes(self):
        return self.__lanes

    @property
    def overtakingPossibility(self):
        return self.__overtakingPossibility

    @overtakingPossibility.setter
    def overtakingPossibility(self, overtakingPossibility):
        self.__overtakingPossibility = overtakingPossibility

    @property
    def origin(self):
        return self.__origin

    @origin.setter
    def origin(self, origin):
        self.__origin = origin

    @property
    def end(self):
        return self.__end

    @end.setter
    def end(self, end):
        self.__end = end

    def addLane(self, length, bounds, direction):
        self.__lanes.append(Lane(length, bounds, 90 - degrees(self.angle(bounds)), direction))

    def removeLane(self, index):
        self.__connections.pop(index)

    def totalWidth(self, bounds):
        return sum([lane.length(bounds) for lane in self.__lanes])

    def length(self, bounds):
        return hypot(self.end[0] * bounds[0] - self.origin[0] * bounds[0],
                     self.end[1] * bounds[1] - self.origin[1] * bounds[1])

    def angle(self, bounds):
        return atan2(self.end[1] * bounds[1] - self.origin[1] * bounds[1],
                     self.end[0] * bounds[0] - self.origin[0] * bounds[0])


class Straight(NonIntersection):

    def __init__(self, speedLimit, overtakingPossibility, origin, end):
        super().__init__(speedLimit, overtakingPossibility, origin, end)


class Curve(NonIntersection):

    def __init__(self, speedLimit, overtakingPossibility, origin, end, middle):
        super().__init__(speedLimit, overtakingPossibility, origin, end)
        self.__middle = middle

    @property
    def middle(self):
        return self.__middle

    @middle.setter
    def middle(self, middle):
        self.__middle = middle


class Lane(object):
    
    def __init__(self, length, bounds, angle, direction):
        self.__width = (length * cos(radians(angle))) / bounds[0]
        self.__height = (length * sin(radians(angle))) / bounds[1]
        self.__direction = direction

    def length(self, bounds):
        return sqrt((self.__width * bounds[0])**2 + (self.__height * bounds[1])**2)

    @property
    def direction(self):
        return self.__direction

    @direction.setter
    def direction(self, direction):
        self.__direction = direction

Direction = Enum('Direction', 'FORWARD INVERSE')

'''
class Intersection(Road):

class Crossroad(Intersection):

class Roundabout(Intersection):
'''
