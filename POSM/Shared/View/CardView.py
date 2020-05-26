from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect


class CardView(QFrame):

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowFlags())
        self.setAutoFillBackground(True)
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        effect.setColor(QColor(0, 0, 0, 160))
        effect.setOffset(0.0)
        self.setGraphicsEffect(effect)
