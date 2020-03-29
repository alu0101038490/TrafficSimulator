from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCalendarWidget


class DelimitedCalendar(QCalendarWidget):

    def paintCell(self, painter, rect, date):
        if not self.minimumDate() <= date <= self.maximumDate():
            painter.setPen(QtGui.QPen(Qt.lightGray))
            painter.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, str(date.day()))
        else:
            super().paintCell(painter, rect, date)