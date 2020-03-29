from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QPushButton


class IconButton(QPushButton):

    def __init__(self, icon, window, side):
        super().__init__(icon, "")
        self.setFixedHeight(icon.actualSize(window, QSize(side, side)).height())
        self.setFixedWidth(icon.actualSize(window, QSize(side, side)).height())