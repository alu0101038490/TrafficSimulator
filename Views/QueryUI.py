from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, \
    QSizePolicy, QComboBox, QCheckBox, QGroupBox, QRadioButton, QFrame, QTabWidget, QLabel

from Models.OverpassQuery import OverpassQuery, Surround, OverpassRequest
from Utils.GenericUtils import nextString
from Utils.TaginfoUtils import getOfficialKeys


class FilterWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        topWidget = QWidget()
        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        topWidget.setLayout(topLayout)

        keyLabel = QLabel("Key:")
        keyLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        topLayout.addWidget(keyLabel)

        self.removeCB = QCheckBox()
        topLayout.addWidget(self.removeCB)

        self.layout.addWidget(topWidget)

        self.keyInput = QComboBox()
        self.keyInput.setEditable(True)

        self.keyInput.addItems(self.keyValues)

        self.layout.addWidget(self.keyInput)

        valueEdition = QWidget()
        valueEdition.setLayout(QHBoxLayout())
        valueEdition.layout().setContentsMargins(0, 0, 0, 0)

        self.valueInput = QComboBox()
        self.valueInput.setEditable(True)
        valueEdition.layout().addWidget(self.valueInput)

        self.checkboxAccuracy = QCheckBox()
        self.checkboxAccuracy.setText("Exact Value")
        valueEdition.layout().addWidget(self.checkboxAccuracy)

        self.layout.addWidget(QLabel("Value:"))
        self.layout.addWidget(valueEdition)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.setLayout(self.layout)

    def getKey(self):
        return self.keyInput.currentText()

    def getValue(self):
        return self.valueInput.currentText()

    def isExactValueSelected(self):
        return self.checkboxAccuracy.isChecked()

    def isSelectedToDelete(self):
        return self.removeCB.isChecked()


class RequestWidget(QWidget):

    def __init__(self, parent, keyValues):
        super().__init__(parent)
        self.keyValues = keyValues
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        self.filtersWidget = QWidget(self)
        self.filtersLayout = QVBoxLayout()
        self.filtersWidget.setLayout(self.filtersLayout)
        self.layout.addWidget(self.filtersWidget)

        self.addFilter()

        self.layout.addWidget(QLabel("Surroundings:"))

        surroundGB = QGroupBox()
        surroundLayout = QVBoxLayout()
        surroundLayout.setContentsMargins(0, 0, 0, 0)

        aroundRB = QRadioButton(self.tr("&Streets around"))
        aroundRB.setObjectName("Around")
        surroundLayout.addWidget(aroundRB)

        adjacentRB = QRadioButton(self.tr("&Adjacent streets"))
        adjacentRB.setObjectName("Adjacent")
        surroundLayout.addWidget(adjacentRB)

        noneRB = QRadioButton(self.tr("&None"))
        noneRB.setObjectName("None")
        noneRB.setChecked(True)
        surroundLayout.addWidget(noneRB)

        surroundGB.setLayout(surroundLayout)

        self.layout.addWidget(surroundGB)

        self.setLayout(self.layout)

    def addFilter(self):
        self.filtersLayout.addWidget(FilterWidget(self.filtersWidget, self.keyValues))

    def removeFilters(self):
        for widget in self.filtersWidget.findChildren(FilterWidget):
            if (widget.isSelectedToDelete()):
                widget.deleteLater()


class QueryUI(QWidget):

    def __init__(self):
        super().__init__()
        self.keyValues = getOfficialKeys()
        self.lastRequestName = "a"
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        requestsArea = QScrollArea()
        requestsArea.setWidgetResizable(True)

        self.requestTabs = QTabWidget()
        self.addRequest()
        requestsArea.setWidget(self.requestTabs)

        self.layout.addWidget(requestsArea)

        self.setLayout(self.layout)

    def addRequest(self):
        requestWidget = RequestWidget(self, self.keyValues)
        requestWidget.setObjectName(self.lastRequestName)
        self.requestTabs.addTab(requestWidget, self.lastRequestName)
        self.lastRequestName = nextString(self.lastRequestName)

    def removeRequest(self):
        self.requestTabs.currentWidget().deleteLater()

    def addFilter(self):
        self.requestTabs.currentWidget().addFilter()

    def removeFilter(self):
        self.requestTabs.currentWidget().removeFilters()

    def getQuery(self):
        query = OverpassQuery()

        switcher = {
            "Adjacent": Surround.ADJACENT,
            "Around": Surround.AROUND,
            "None": Surround.NONE
        }

        for requestWidget in self.findChildren(RequestWidget):
            selectedSurrounding = [b for b in requestWidget.findChildren(QRadioButton) if b.isChecked()][0]
            request = OverpassRequest(switcher.get(selectedSurrounding.objectName()))
            for filterWidget in requestWidget.findChildren(FilterWidget):
                request.addFilter(filterWidget.getKey(), filterWidget.getValue(), filterWidget.isExactValueSelected())

            query.addRequest(requestWidget.objectName(), request)

        return query
