import logging
import os

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect, QFormLayout, QWidget, QHBoxLayout, QComboBox, \
    QSizePolicy, QMenu, QAction, QCheckBox
from requests import RequestException

from Shared.Utils.TaginfoUtils import getKeyDescription, getValuesByKey
from Shared.View.IconButton import IconButton
from Shared.constants import picturesDir, TagComparison
from Tag.Model.OverpassFilter import OverpassFilter


class FilterWidget(QFrame):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

        self.setAutoFillBackground(True)
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        effect.setColor(QColor(0, 0, 0, 160))
        effect.setOffset(0.0)
        self.setGraphicsEffect(effect)

    def initUI(self):
        self.layout = QFormLayout()
        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setVerticalSpacing(5)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        topWidget = QWidget()
        topLayout = QHBoxLayout()
        topLayout.setSpacing(0)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topWidget.setLayout(topLayout)

        self.keyInput = QComboBox()
        self.keyInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.keyInput.setEditable(True)
        self.keyInput.lineEdit().setPlaceholderText("'highway', 'name'...")
        self.keyInput.addItems(self.keyValues)
        topLayout.addWidget(self.keyInput)

        self.filterOptionsButton = IconButton(QIcon(os.path.join(picturesDir, "options.png")),
                                              topWidget.windowHandle(),
                                              self.keyInput.height())
        self.filterOptionsButton.setStyleSheet("""QPushButton::menu-indicator{image: none;}""")

        self.filterOptionsMenu = QMenu()

        removeAct = QAction('Remove filter', self)
        removeAct.triggered.connect(self.deleteLater)
        self.filterOptionsMenu.addAction(removeAct)

        helpAct = QAction('Help', self)
        helpAct.triggered.connect(self.getInfo)
        self.filterOptionsMenu.addAction(helpAct)

        self.filterOptionsButton.setMenu(self.filterOptionsMenu)
        self.filterOptionsButton.setFlat(True)
        topLayout.addWidget(self.filterOptionsButton)

        self.layout.addRow("Key:", topWidget)

        self.comparisonInput = QComboBox()
        self.comparisonInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.comparisonSwtich = [TagComparison.EQUAL,
                                 TagComparison.CONTAIN_ALL,
                                 TagComparison.IS_ONE_OF,
                                 TagComparison.AT_MOST,
                                 TagComparison.AT_LEAST,
                                 TagComparison.HAS_KEY,
                                 TagComparison.HAS_ONE_KEY]
        self.comparisonInput.addItems(["is equal to",
                                       "contains",
                                       "contains one of",
                                       "is at most",
                                       "is at least",
                                       "is included",
                                       "at least one is included"])
        self.comparisonInput.currentIndexChanged.connect(self.__onComparisonSelected__)
        self.layout.addRow("", self.comparisonInput)

        valueEdition = QWidget()
        valueEdition.setLayout(QHBoxLayout())
        valueEdition.layout().setSpacing(0)
        valueEdition.layout().setContentsMargins(0, 0, 0, 0)

        self.valueInput = QComboBox()
        self.valueInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.valueInput.setEditable(True)
        self.valueInput.lineEdit().setPlaceholderText("'service', 'motorway'...")
        valueEdition.layout().addWidget(self.valueInput)

        self.layout.addRow("Value:", valueEdition)

        self.keyInput.currentTextChanged.connect(self.valueInput.clear)

        flagsWidget = QWidget()
        flagsWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        flagsWidgetLayout = QHBoxLayout()
        flagsWidgetLayout.setContentsMargins(0, 0, 0, 0)
        flagsWidget.setLayout(flagsWidgetLayout)

        self.checkboxAccuracy = QCheckBox()
        self.checkboxAccuracy.setText("Exact Value")
        flagsWidgetLayout.addWidget(self.checkboxAccuracy)

        self.checkboxNegate = QCheckBox()
        self.checkboxNegate.setText("Negate")
        flagsWidgetLayout.addWidget(self.checkboxNegate)

        self.layout.addRow("Flags:", flagsWidget)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.setLayout(self.layout)

    def __onComparisonSelected__(self, i):
        if i == 6:
            self.checkboxNegate.hide()
        else:
            self.checkboxNegate.show()

        if i > 4:
            self.valueInput.setEnabled(False)
            self.valueInput.lineEdit().setPlaceholderText("Not required")
        else:
            self.valueInput.setEnabled(True)
            self.valueInput.lineEdit().setPlaceholderText("'service', 'motorway'...")

        if 2 < i <= 4:
            self.checkboxAccuracy.hide()
        else:
            self.checkboxAccuracy.show()

    def getFilter(self):
        return OverpassFilter(self.getKey(),
                              self.getComparison(),
                              self.getValue(),
                              self.isNegateSelected(),
                              self.isExactValueSelected())

    def getInfo(self):
        keyName = self.keyInput.currentText()
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

    def getKey(self):
        return self.keyInput.currentText()

    def getComparison(self):
        return self.comparisonSwtich[self.comparisonInput.currentIndex()]

    def getValue(self):
        return self.valueInput.currentText()

    def setKey(self, key):
        self.keyInput.setEditText(key)

    def setValue(self, value):
        self.valueInput.setEditText(value)

    def isExactValueSelected(self):
        return self.checkboxAccuracy.isChecked()

    def setExactValue(self, bool):
        self.checkboxAccuracy.setChecked(bool)

    def isNegateSelected(self):
        return self.checkboxNegate.isChecked()

    def setNegate(self, bool):
        self.checkboxNegate.setChecked(bool)

    def isSelectedToDelete(self):
        return self.removeCB.isChecked()
