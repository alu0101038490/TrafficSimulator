import os

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QFormLayout, QCalendarWidget, QSizePolicy, QToolButton

from Shared.View.DelimitedCalendar import DelimitedCalendar
from Shared.constants import picturesDir


class GlobalOverpassSettingUI(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout()
        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setLayout(self.layout)

        self.layout.addRow("DATE", None)

        self.dateEdit = DelimitedCalendar()
        self.dateEdit.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.dateEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dateEdit.setMinimumDate(QDate(2012, 9, 13))
        self.dateEdit.setMaximumDate(QDate.currentDate())

        prevIcon = self.dateEdit.findChild(QToolButton, "qt_calendar_prevmonth")
        nextIcon = self.dateEdit.findChild(QToolButton, "qt_calendar_nextmonth")
        prevIcon.setIcon(QIcon(os.path.join(picturesDir, "arrowLeft.png")))
        nextIcon.setIcon(QIcon(os.path.join(picturesDir, "arrowRight.png")))
        self.dateEdit.findChild(QToolButton, "qt_calendar_monthbutton").setEnabled(False)

        format = self.dateEdit.weekdayTextFormat(Qt.Monday)
        self.dateEdit.setWeekdayTextFormat(Qt.Saturday, format)
        self.dateEdit.setWeekdayTextFormat(Qt.Sunday, format)

        self.layout.addRow(self.dateEdit)

    def getDate(self):
        return self.dateEdit.selectedDate().toPyDate()

    def setDate(self, date):
        return self.dateEdit.setSelectedDate(date)
