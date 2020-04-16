from PyQt5.QtWidgets import QFrame


class HorizontalLine(QFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setContentsMargins(0, 0, 0, 0)