import logging
import os

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect, QFormLayout, QWidget, QHBoxLayout, QComboBox, \
    QSizePolicy, QMenu, QAction, QCheckBox, QScrollArea, QVBoxLayout, QLabel, QLineEdit
from requests import RequestException

from Shared.Utils.TaginfoUtils import getKeyDescription, getValuesByKey
from Shared.View.CardView import CardView
from Shared.View.IconButton import IconButton
from Shared.View.VariableInputList import VariableInputList
from Shared.constants import picturesDir, TagComparison
from Tag.Model.OverpassFilter import OverpassFilter


class FilterWidget(CardView):

    attributesByComparison = {
        TagComparison.AT_LEAST: {
            "multipleKeys": False,
            "comparisonMessage": "is at least",
            "multipleValues": False,
            "exactValue": False,
            "negate": True
        }, TagComparison.AT_MOST: {
            "multipleKeys": False,
            "comparisonMessage": "is at most",
            "multipleValues": False,
            "exactValue": False,
            "negate": True
        }, TagComparison.CONTAIN_ALL: {
            "multipleKeys": False,
            "comparisonMessage": "contain the words",
            "multipleValues": True,
            "exactValue": True,
            "negate": True
        }, TagComparison.EQUAL: {
            "multipleKeys": False,
            "comparisonMessage": "is equal to",
            "multipleValues": False,
            "exactValue": True,
            "negate": True
        }, TagComparison.HAS_KEY: {
            "multipleKeys": False,
            "comparisonMessage": "exists",
            "multipleValues": None,
            "exactValue": True,
            "negate": False
        }, TagComparison.HAS_NOT_KEY: {
            "multipleKeys": False,
            "comparisonMessage": "does not exists",
            "multipleValues": None,
            "exactValue": False,
            "negate": False
        }, TagComparison.HAS_ONE_KEY: {
            "multipleKeys": True,
            "comparisonMessage": "at least one exists",
            "multipleValues": None,
            "exactValue": True,
            "negate": False
        }, TagComparison.IS_ONE_OF: {
            "multipleKeys": False,
            "comparisonMessage": "is one of",
            "multipleValues": True,
            "exactValue": True,
            "negate": True
        }
    }

    def __init__(self, parent, comparison, keyList=None):
        super().__init__(parent)
        self.comparison = comparison
        if keyList is None:
            keyList = []
        self.keyList = keyList

        self.layout = self.__generateLayout__()
        self.setLayout(self.layout)
        if FilterWidget.attributesByComparison[comparison]["multipleKeys"]:
            self.__generateMultiKeyWidget__()
        else:
            topWidget, self.keyInput = self.__generateKeyWidget__()
            self.layout.addRow("Keys:", topWidget)
            self.layout.addRow("", self.__generateComparisonLabel__(FilterWidget.attributesByComparison[comparison]["comparisonMessage"]))
        if FilterWidget.attributesByComparison[comparison]["multipleValues"]:
            self.__generateMultiValueWidget__()
        elif FilterWidget.attributesByComparison[comparison]["multipleValues"] == False:
            self.__generateValueWidget__()
        if FilterWidget.attributesByComparison[comparison]["exactValue"]:
            self.__generateFlagsWidget__()
            self.__addExactFlag__()
            if  FilterWidget.attributesByComparison[comparison]["negate"]:
                self.__addNegateFlag__()
        elif FilterWidget.attributesByComparison[comparison]["negate"]:
            self.__generateFlagsWidget__()
            self.__addNegateFlag__()

    # UI COMPONENTS

    def __generateLayout__(self):
        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setVerticalSpacing(5)
        layout.setLabelAlignment(Qt.AlignLeft)
        layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        return layout

    def __generateKeyWidget__(self):
        topWidget = QWidget()
        topLayout = QHBoxLayout()
        topLayout.setSpacing(0)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topWidget.setLayout(topLayout)

        keyInput = QComboBox()
        keyInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        keyInput.setEditable(True)
        keyInput.lineEdit().setPlaceholderText("'highway', 'name'...")
        keyInput.addItems(self.keyList)
        topLayout.addWidget(keyInput)

        filterOptionsButton = IconButton(QIcon(os.path.join(picturesDir, "options.png")),
                                         topWidget.windowHandle(),
                                         keyInput.height())
        filterOptionsButton.setStyleSheet("""QPushButton::menu-indicator{image: none;}""")

        filterOptionsMenu = QMenu()

        removeAct = QAction('Remove filter', self)
        removeAct.triggered.connect(self.deleteLater)
        filterOptionsMenu.addAction(removeAct)

        helpAct = QAction('Help', self)
        helpAct.triggered.connect(self.getInfo)
        filterOptionsMenu.addAction(helpAct)

        filterOptionsButton.setMenu(filterOptionsMenu)
        filterOptionsButton.setFlat(True)
        topLayout.addWidget(filterOptionsButton)

        return topWidget, keyInput

    def __generateMultiKeyWidget__(self):
        topWidget = QWidget()
        topLayout = QHBoxLayout()
        topLayout.setSpacing(0)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topWidget.setLayout(topLayout)

        filterOptionsButton = IconButton(QIcon(os.path.join(picturesDir, "options.png")),
                                         topWidget.windowHandle(),
                                         topWidget.height())
        filterOptionsButton.setStyleSheet("""QPushButton::menu-indicator{image: none;}""")

        filterOptionsMenu = QMenu()

        removeAct = QAction('Remove filter', self)
        removeAct.triggered.connect(self.deleteLater)
        filterOptionsMenu.addAction(removeAct)

        helpAct = QAction('Help', self)
        helpAct.triggered.connect(self.getInfo)
        filterOptionsMenu.addAction(helpAct)

        filterOptionsButton.setMenu(filterOptionsMenu)
        filterOptionsButton.setFlat(True)
        topLayout.addWidget(filterOptionsButton)

        self.layout.addRow("Keys:", topWidget)

        keysArea = QScrollArea()
        keysArea.setWidgetResizable(True)
        self.keysWidget = QWidget()
        keysArea.setWidget(self.keysWidget)
        keysWidgetLayout = QVBoxLayout()
        keysWidgetLayout.setSpacing(0)
        keysWidgetLayout.setContentsMargins(0, 0, 0, 0)
        self.keysWidget.setLayout(keysWidgetLayout)

        self.layout.addWidget(keysArea)

        keysButtons = QWidget()
        keysButtonsLayout = QHBoxLayout()
        keysButtonsLayout.setAlignment(Qt.AlignRight)
        keysButtons.setLayout(keysButtonsLayout)
        keysButtonsLayout.setSpacing(0)
        keysButtonsLayout.setContentsMargins(0, 0, 0, 0)

        buttonAdd = IconButton(QIcon(os.path.join(picturesDir, "add.png")), keysButtons.windowHandle(),
                               keysButtons.height())
        buttonAdd.setToolTip("Add key")
        buttonAdd.setFlat(True)
        buttonAdd.clicked.connect(self.addKey)

        keysButtonsLayout.addWidget(buttonAdd)

        self.layout.addWidget(keysButtons)

    def __generateComparisonLabel__(self, comparisonMessage):
        self.comparisonLabel = QLabel(comparisonMessage)
        return self.comparisonLabel

    def __generateValueWidget__(self):
        valueEdition = QWidget()
        valueEdition.setLayout(QHBoxLayout())
        valueEdition.layout().setSpacing(0)
        valueEdition.layout().setContentsMargins(0, 0, 0, 0)

        self.valueInput = QComboBox()
        self.valueInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.valueInput.setEditable(True)
        self.valueInput.lineEdit().setPlaceholderText("'service', 'motorway'...")
        valueEdition.layout().addWidget(self.valueInput)
        self.keyInput.currentTextChanged.connect(self.valueInput.clear)

        self.layout.addRow("Value:", valueEdition)

    def __generateMultiValueWidget__(self):
        self.valuesWidget = VariableInputList(placeHolder="Value")
        self.layout.addRow("Values:", self.valuesWidget)

    def __generateFlagsWidget__(self):
        flagsWidget = QWidget()
        flagsWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.flagsWidgetLayout = QHBoxLayout()
        self.flagsWidgetLayout.setContentsMargins(0, 0, 0, 0)
        flagsWidget.setLayout(self.flagsWidgetLayout)

        self.layout.addRow("Flags:", flagsWidget)

    def __addNegateFlag__(self):
        self.checkboxNegate = QCheckBox()
        self.checkboxNegate.setText("Negate")
        self.flagsWidgetLayout.addWidget(self.checkboxNegate)

    def __addExactFlag__(self):
        self.checkboxAccuracy = QCheckBox()
        self.checkboxAccuracy.setText("Exact")
        self.flagsWidgetLayout.addWidget(self.checkboxAccuracy)

    # TAG GETTERS

    def getFilter(self):
        return OverpassFilter(self.getMultipleKeys() if FilterWidget.attributesByComparison[self.comparison]["multipleKeys"] else self.getKey(),
                              self.getComparison(),
                              self.getMultipleValues() if FilterWidget.attributesByComparison[self.comparison]["multipleValues"] else self.getValue(),
                              self.isNegateSelected(),
                              self.isExactValueSelected())

    def getKey(self):
        try:
            return self.keyInput.currentText()
        except AttributeError:
            return None

    def getMultipleKeys(self):
        return [lineEdit.text() for lineEdit in self.keysWidget.findChildren(QLineEdit)]

    def getComparison(self):
        return self.comparison

    def getValue(self):
        try:
            return self.valueInput.currentText()
        except AttributeError:
            return None

    def getMultipleValues(self):
        return [lineEdit.text() for lineEdit in self.valuesWidget.findChildren(QLineEdit)]

    def isExactValueSelected(self):
        try:
            return self.checkboxAccuracy.isChecked()
        except AttributeError:
            return None

    def isNegateSelected(self):
        try:
            return self.checkboxNegate.isChecked()
        except AttributeError:
            return None

    # TAG SETTERS

    def setFilter(self, newFilter):
        if FilterWidget.attributesByComparison[self.comparison]["multipleKeys"]:
            self.setMultipleKeys(newFilter.key)
        else:
            self.setKey(newFilter.key)
        if FilterWidget.attributesByComparison[self.comparison]["multipleValues"]:
            self.setMultipleValues(newFilter.value)
        elif FilterWidget.attributesByComparison[self.comparison]["multipleValues"] == False:
            self.setValue(newFilter.value)
        if FilterWidget.attributesByComparison[self.comparison]["exactValue"]:
            self.setExactValue(newFilter.isExactValue)
        if FilterWidget.attributesByComparison[self.comparison]["negate"]:
            self.setNegate(newFilter.isNegated)

    def setKey(self, key):
        try:
            self.keyInput.setEditText(key)
        except AttributeError:
            pass

    def setMultipleKeys(self, keys=None):
        if keys is None:
            keys = []
        for lineEdit in self.keysWidget.findChildren(QLineEdit):
            lineEdit.deleteLater()
        for newKey in keys:
            self.addKey(newKey)

    def addKey(self, newKey=0):
        keyWidget = QWidget()
        keyWidgetLayout = QHBoxLayout()
        keyWidgetLayout.setContentsMargins(0, 0, 0, 0)
        keyWidget.setLayout(keyWidgetLayout)
        keyInput = QLineEdit()
        if newKey != 0:
            keyInput.setText(str(newKey))
        keyInput.setPlaceholderText("Key")
        keyInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        keyWidgetLayout.addWidget(keyInput)
        removeIdButton = IconButton(QIcon(os.path.join(picturesDir, "remove.png")),
                                 keyWidget.windowHandle(),
                                 keyWidget.height())
        removeIdButton.setToolTip("Show table")
        removeIdButton.setFlat(True)
        removeIdButton.clicked.connect(keyWidget.deleteLater)

        keyWidgetLayout.addWidget(removeIdButton)

        self.keysWidget.layout().addWidget(keyWidget)

    def setValue(self, value):
        try:
            self.valueInput.setEditText(value)
        except AttributeError:
            pass

    def setMultipleValues(self, values=None):
        self.valuesWidget.setItems(values)

    def addValue(self, newValue=""):
        self.valuesWidget.addItem(newValue)

    def setExactValue(self, checked):
        try:
            self.checkboxAccuracy.setChecked(checked)
        except AttributeError:
            pass

    def setNegate(self, checked):
        try:
            self.checkboxNegate.setChecked(checked)
        except AttributeError:
            pass

    # SIGNALS

    def __onComparisonSelected__(self, i):
        if i > 4:
            self.valueInput.setEnabled(False)
            self.valueInput.lineEdit().setPlaceholderText("Not required")
            self.checkboxNegate.hide()
        else:
            self.valueInput.setEnabled(True)
            self.valueInput.lineEdit().setPlaceholderText("'service', 'motorway'...")
            self.checkboxNegate.show()

        if 2 < i <= 5:
            self.checkboxAccuracy.hide()
        else:
            self.checkboxAccuracy.show()

    def getInfo(self):
        keyName = self.getKey()
        try:
            descriptions = getKeyDescription(keyName)
            if len(descriptions) == 0:
                logging.warning("'{}' is an unofficial or unused key. No available description.".format(keyName))
            else:
                englishDescription = next((d["description"] for d in descriptions if d["language_en"] == "English"),
                                          "English description not available.")
                logging.info(keyName + ": " + englishDescription)
        except RequestException:
            logging.error("There was a problem with the internet connection. Can't get the key description.")
            return

        self.valueInput.clear()

        try:
            self.valueInput.addItems(getValuesByKey(keyName))
        except requests.exceptions.Timeout:
            logging.warning("Too many available values for the given key.")
        except RequestException:
            logging.error("There was a problem with the internet connection. Can't get the possible values for the "
                          "given key.")
