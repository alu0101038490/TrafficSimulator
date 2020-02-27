import requests
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QScrollArea, QHBoxLayout, \
    QSizePolicy, QComboBox, QCheckBox, QFormLayout, QGroupBox, QRadioButton, QFrame, QToolBox, QTabWidget, QLabel

from Models.OverpassQuery import Query, Surrounding

class KeyValueWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        self.nameLabel = QComboBox()
        overpass_url = "https://taginfo.openstreetmap.org/api/4/keys/all?filter=in_wiki"
        response = requests.get(overpass_url)
        self.nameLabel.addItems([item["key"] for item in response.json()['data']])
        self.nameLabel.setEditable(True)
        top = QWidget()
        removeLayout = QHBoxLayout()
        removeLayout.setContentsMargins(0, 0, 0, 0)
        keyLabel = QLabel("Key:")
        keyLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        removeLayout.addWidget(keyLabel)
        self.removeCB = QCheckBox()
        removeLayout.addWidget(self.removeCB)
        top.setLayout(removeLayout)
        self.layout.addWidget(top)
        self.layout.addWidget(self.nameLabel)

        valueEdition = QWidget()
        valueEdition.setLayout(QHBoxLayout())
        valueEdition.layout().setContentsMargins(0,0,0,0)

        self.nameInput = QComboBox()
        self.nameInput.setMaximumHeight(30)
        self.nameInput.setEditable(True)
        valueEdition.layout().addWidget(self.nameInput)

        self.checkboxAccuracy = QCheckBox()
        self.checkboxAccuracy.setText("Exact Value")
        valueEdition.layout().addWidget(self.checkboxAccuracy)

        self.layout.addWidget(QLabel("Value:"))
        self.layout.addWidget(valueEdition)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.setLayout(self.layout)

    def isSelected(self):
        return self.removeCB.isChecked()

class TagWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        self.listWidget = QWidget()
        self.listLayout = QVBoxLayout()
        self.listWidget.setLayout(self.listLayout)
        self.layout.addWidget(self.listWidget)

        self.addKeyValue()

        groupBox = QGroupBox()
        radio1 = QRadioButton(self.tr("&Streets around"))
        radio1.setObjectName("Around")
        radio2 = QRadioButton(self.tr("&Adjacent streets"))
        radio2.setObjectName("Adjacent")
        radio3 = QRadioButton(self.tr("&None"))
        radio3.setObjectName("None")
        radio3.setChecked(True)

        groupBoxLayout = QVBoxLayout()
        groupBoxLayout.setContentsMargins(0,0,0,0)
        groupBoxLayout.addWidget(radio1)
        groupBoxLayout.addWidget(radio2)
        groupBoxLayout.addWidget(radio3)
        groupBox.setLayout(groupBoxLayout)

        self.layout.addWidget(QLabel("Surroundings:"))
        self.layout.addWidget(groupBox)

        #self.nameLabel.currentIndexChanged.connect(self.getValuesByKey)

        self.setLayout(self.layout)

    def getValuesByKey(self, i):
        overpass_url = "https://taginfo.openstreetmap.org/api/4/key/values?key=" + self.nameLabel.itemText(i)
        response = requests.get(overpass_url)
        self.nameInput.addItems([item["value"] for item in response.json()['data'] if item["in_wiki"] == True])

    def addKeyValue(self):
        self.listLayout.addWidget(KeyValueWidget(self.listWidget))

    def removeSelected(self):
        for widget in self.listWidget.findChildren(KeyValueWidget):
            if(widget.isSelected()):
                widget.deleteLater()



class EditionWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        tags = QScrollArea()
        self.tabWidget = QTabWidget()
        tags.setWidget(self.tabWidget)
        tags.setWidgetResizable(True)
        self.layout.addWidget(tags)

        self.setLayout(self.layout)

    def addFitler(self):
        new = TagWidget(self)
        self.tabWidget.addTab(new, "Tag " + str(len(self.findChildren(TagWidget))))

    def removeFilter(self):
        self.tabWidget.currentWidget().deleteLater()

    def removeKeyValue(self):
        self.tabWidget.currentWidget().removeSelected()

    def addKeyValue(self):
        self.tabWidget.currentWidget().addKeyValue()

    def getQuery(self):
        query = Query()
        for widget in self.findChildren(TagWidget):
            selectedRadioButton = [b for b in widget.findChildren(QRadioButton) if b.isChecked() == True][0]
            switcher = {
                "Adjacent": Surrounding.ADJACENT,
                "Around": Surrounding.AROUND,
                "None": Surrounding.NONE
            }
            query.addTag(widget.nameLabel.currentText(),
                         widget.nameInput.currentText(),
                         widget.checkboxAccuracy.isChecked(),
                         switcher.get(selectedRadioButton.objectName()))
        return query