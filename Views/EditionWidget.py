import requests
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QScrollArea, QHBoxLayout, \
    QSizePolicy, QComboBox, QCheckBox, QFormLayout, QGroupBox, QRadioButton, QFrame, QToolBox

from Models.OverpassQuery import Query, Surrounding


class TagWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        self.nameLabel = QComboBox()
        overpass_url = "https://taginfo.openstreetmap.org/api/4/keys/all?filter=in_wiki"
        response = requests.get(overpass_url)
        self.nameLabel.addItems([item["key"] for item in response.json()['data']])
        self.nameLabel.setEditable(True)
        layout.addRow(self.tr("&Key:"), self.nameLabel)

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

        layout.addRow(self.tr("&Value:"), valueEdition)

        groupBox = QGroupBox()
        radio1 = QRadioButton(self.tr("&Streets around"))
        radio1.setObjectName("Around")
        radio2 = QRadioButton(self.tr("&Adjacent streets"))
        radio2.setObjectName("Adjacent")
        radio3 = QRadioButton(self.tr("&None"))
        radio3.setObjectName("None")
        radio3.setChecked(True)

        groupBoxLayout = QHBoxLayout()
        groupBoxLayout.setContentsMargins(0,0,0,0)
        groupBoxLayout.addWidget(radio1)
        groupBoxLayout.addWidget(radio2)
        groupBoxLayout.addWidget(radio3)
        groupBox.setLayout(groupBoxLayout)

        layout.addRow(self.tr("&Surroundings:"), groupBox)

        #self.nameLabel.currentIndexChanged.connect(self.getValuesByKey)
        deleteButton = QPushButton()
        deleteButton.setIcon(QtGui.QIcon('../Resources/Pictures/remove.png'))
        deleteButton.clicked.connect(lambda: self.deleteLater())
        layout.addRow(self.tr(""), deleteButton)

        self.setLayout(layout)

    def getValuesByKey(self, i):
        overpass_url = "https://taginfo.openstreetmap.org/api/4/key/values?key=" + self.nameLabel.itemText(i)
        response = requests.get(overpass_url)
        self.nameInput.addItems([item["value"] for item in response.json()['data'] if item["in_wiki"] == True])

class EditionWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        buttonAdd = QPushButton()
        buttonAdd.setText("+")
        self.layout.addWidget(buttonAdd)

        tags = QScrollArea()
        self.scrollableWidget = QToolBox()
        tags.setWidget(self.scrollableWidget)
        tags.setWidgetResizable(True)
        self.layout.addWidget(tags)


        buttonAdd.clicked.connect(self.addFitler)

        self.setLayout(self.layout)

    def addFitler(self):
        new = TagWidget(self)
        self.scrollableWidget.addItem(new, "Tag")

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