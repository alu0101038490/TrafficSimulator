from math import degrees, sqrt

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QPixmap, QBrush
from PyQt5.QtWidgets import QWidget

from Models import Road
from Models.Road import Direction


class SimulationWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.straight = Road.Straight(80, False, [0.58, 0.80], [0.608, 0.90])
        self.straight.addLane(10, [self.rect().width(), self.rect().height()], Direction.FORWARD)
        self.straight.addLane(10, [self.rect().width(), self.rect().height()], Direction.FORWARD)
        self.straight.addLane(10, [self.rect().width(), self.rect().height()], Direction.FORWARD)

        self.curve = Road.Curve(80, False, [0.58, 0.80], [0.65, 0.6], [0.7, 0.7])
        self.curve.addLane(15, [self.rect().width(), self.rect().height()], Direction.FORWARD)
        self.curve.addLane(15, [self.rect().width(), self.rect().height()], Direction.FORWARD)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)

        pic = QPixmap("Resources/Pictures/ejemplo-rotonda.jpg")
        painter.drawPixmap(self.rect(), pic)

        painter.setRenderHint(QPainter.Antialiasing)

        '''
        painter.setPen(QPen(Qt.gray, 24))
        painter.translate(0.58 * self.rect().width(), 0.80 * self.rect().height())
        painter.rotate(-90 + degrees(self.straight.angle([self.rect().width(), self.rect().height()])))
        painter.drawArc(-30, -30, 30, 30, 0, 180 * 16)

        SimulationWindow.PaintStraightRoad(painter, self.straight, [self.rect().width(), self.rect().height()])
        SimulationWindow.PaintCurvedRoad(painter, self.curve, [self.rect().width(), self.rect().height()])
        '''
        painter.end()

    @staticmethod
    def PaintStraightRoad(painter, straight, conversion):
        painter.resetTransform()
        painter.translate(straight.origin[0] * conversion[0], straight.origin[1] * conversion[1])
        painter.rotate(degrees(straight.angle(conversion)))
        halfWidth = straight.totalWidth(conversion) / 2

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Qt.gray, Qt.SolidPattern))
        painter.drawRect(0, -halfWidth, straight.length(conversion), 2 * halfWidth)

        roadLinesWidth = 0.06 * max([lane.length(conversion) for lane in straight.lanes])

        painter.setPen(QPen(Qt.white, roadLinesWidth, Qt.DashLine))
        accumulatedWidth = -halfWidth
        for lane in straight.lanes[:-1]:
            accumulatedWidth += lane.length(conversion)
            painter.drawLine(0, accumulatedWidth, straight.length(conversion), accumulatedWidth)

        painter.setPen(QPen(Qt.yellow, roadLinesWidth))
        painter.drawLine(0, -halfWidth + roadLinesWidth, straight.length(conversion), -halfWidth + roadLinesWidth)
        painter.drawLine(0, halfWidth - roadLinesWidth, straight.length(conversion), halfWidth - roadLinesWidth)

    @staticmethod
    def PaintCurvedRoad(painter, curve, conversion):
        painter.resetTransform()
        painter.translate(curve.middle[0] * conversion[0], curve.middle[1] * conversion[1])
        painter.rotate(90 - degrees(curve.angle(conversion)))
        halfWidth = curve.totalWidth(conversion) / 2
        edgesDistance = sqrt((curve.end[0] * conversion[0] - curve.origin[0] * conversion[0]) ** 2 + (curve.end[1] * conversion[1] - curve.origin[1] * conversion[1]) ** 2)
        midpoint = [(curve.origin[0] * conversion[0] + curve.end[0] * conversion[0]) / 2, (curve.origin[1] * conversion[1] + curve.end[1] * conversion[1]) / 2]
        radius = sqrt((curve.middle[0] * conversion[0] - midpoint[0]) ** 2 + (curve.middle[1] * conversion[1] - midpoint[1]) ** 2)

        painter.setPen(QPen(Qt.gray, curve.totalWidth(conversion)))
        #TODO: ANGLES ARE NOT RIGHT
        painter.drawArc(0, - edgesDistance / 2, radius * 2, edgesDistance, 270 * 16, 90 * 16)

    '''
        roadLinesWidth = 0.06 * max([lane.length(conversion) for lane in curve.lanes])

        painter.setPen(QPen(Qt.white, roadLinesWidth, Qt.DashLine))
        accumulatedWidth = -halfWidth
        for lane in curve.lanes[:-1]:
            accumulatedWidth += lane.length(conversion)
            painter.drawArc(,, , , , )

            painter.setPen(QPen(Qt.yellow, roadLinesWidth))
            painter.drawArc(,, , , , )
            painter.drawArc(,, , , , )

        painter.translate(-curve.middle[0], -curve.middle[1])
        painter.rotate(-degrees(curve.angle(conversion)))

    @staticmethod
    def PaintRoundabout(painter, roundabout):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Qt.gray, Qt.SolidPattern))
        painter.drawEllipse(250, 250, 50, 50)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOut)
        painter.setBrush(QBrush(Qt.transparent, Qt.SolidPattern))
        painter.drawEllipse(250, 250, 25, 25)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.white, 4, Qt.DashLine))
        painter.drawArc(100, 70, 300, 300, 0 * 16, 90 * 16)

        painter.setPen(QPen(Qt.yellow, 4))
        painter.drawArc(100, 70, 300, 300, 0 * 16, 90 * 16)
        painter.drawArc(100, 70, 300, 300, 0 * 16, 90 * 16)
    '''
