import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLineEdit, QSizePolicy

from Shared.View.IconButton import IconButton
from Shared.constants import picturesDir


class VariableInputListItem(QWidget):

    def __init__(self, defaultValue="", placeHolder="", validator=None):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        itemInput = QLineEdit()
        itemInput.setText(str(defaultValue))
        itemInput.setPlaceholderText(placeHolder)
        if validator is not None:
            itemInput.setValidator(validator)
        itemInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(itemInput)

        removeItemButton = IconButton(QIcon(os.path.join(picturesDir, "remove.png")),
                                      self.windowHandle(),
                                      self.height())
        removeItemButton.setToolTip("Remove item")
        removeItemButton.setFlat(True)
        removeItemButton.clicked.connect(self.deleteLater)
        layout.addWidget(removeItemButton)


class VariableInputList(QWidget):

    def __init__(self, defaultValue="", placeHolder="", validator=None):
        super().__init__()

        self.defaultValue = defaultValue
        self.placeHolder = placeHolder
        self.validator = validator

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        self.layout.addWidget(scrollArea)

        self.listContainer = QWidget()
        scrollArea.setWidget(self.listContainer)

        self.listContainerLayout = QVBoxLayout()
        self.listContainerLayout.setSpacing(0)
        self.listContainerLayout.setContentsMargins(0, 0, 0, 0)
        self.listContainer.setLayout(self.listContainerLayout)

        self.buttons = QWidget()
        self.layout.addWidget(self.buttons)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.setAlignment(Qt.AlignRight)
        self.buttons.setLayout(buttonsLayout)
        buttonsLayout.setSpacing(0)
        buttonsLayout.setContentsMargins(0, 0, 0, 0)

        buttonAdd = IconButton(QIcon(os.path.join(picturesDir, "add.png")), self.buttons.windowHandle(),
                               self.buttons.height())
        buttonAdd.setToolTip("Add item")
        buttonAdd.setFlat(True)
        buttonAdd.clicked.connect(lambda b: self.addItem(self.defaultValue))

        buttonsLayout.addWidget(buttonAdd)

    def getItems(self):
        return [lineEdit.text() for lineEdit in self.listContainer.findChildren(QLineEdit)]

    def setItems(self, items=None):
        if items is None:
            items = []
        self.deleteAll()
        for newItem in items:
            self.addItem(newItem)

    def deleteAll(self):
        for lineEdit in self.listContainer.findChildren(QLineEdit):
            lineEdit.deleteLater()

    def addItem(self, itemValue=""):
        self.listContainerLayout.addWidget(VariableInputListItem(itemValue, self.placeHolder, self.validator))
