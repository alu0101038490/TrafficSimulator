import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtWidgets import QTextEdit

from Views.POSM import app


class InformationalConsole(QTextEdit):

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

        logging.basicConfig(stream=self, level=logging.DEBUG, format='%(levelname)s%(asctime)s - %(message)s',
                            datefmt="%H:%M:%S")

        self.insertPlainText("\nWelcome!")

    def write(self, text):
        if text[0] == "W":
            self.writeWarning(text[7:])
        elif text[0] == "I":
            self.writeInfo(text[4:])
        elif text[0] == "E":
            self.writeError(text[5:])
        elif text[0] == "C":
            self.writeError(text[8:])
        elif text[0] == "D" and text[-5:-1] == "LINE":
            self.addProcessEnd()
        app.processEvents()

    def flush(self):
        pass

    def addProcessEnd(self):
        self.moveCursor(QTextCursor.End)
        self.insertHtml("<hr />")

    def writeMessage(self, message, color):
        self.moveCursor(QTextCursor.End)
        self.insertHtml("<br /><p><font color=\"#ffffff\">{}</font><font color=\"{}\">{}</font></p>\n".format(message[:10],
                                                                                                      color,
                                                                                                      message[10:]))

    def writeWarning(self, warning):
        self.writeMessage(warning, QColor(Qt.darkYellow).name(QColor.HexRgb))

    def writeInfo(self, info):
        self.writeMessage(info, QColor(Qt.white).name(QColor.HexRgb))

    def writeError(self, error):
        self.writeMessage(error, QColor(Qt.darkRed).name(QColor.HexRgb))

    def writeSuccess(self, success):
        self.writeMessage(success, QColor(Qt.darkGreen).name(QColor.HexRgb))