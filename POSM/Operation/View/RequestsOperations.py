from PyQt5.QtCore import Qt, QVariant, QModelIndex
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QFormLayout, QHBoxLayout, QGraphicsDropShadowEffect, QListView, QFrame, QGroupBox, \
    QVBoxLayout, QRadioButton, QSizePolicy, QPushButton, QTableView, QHeaderView, QComboBox, QMessageBox

from Operation.Model.OverpassOperations import OverpassUnion, OverpassIntersection, OverpassDiff
from Query.Model.OverpassQuery import OverpassQuery
from Shared.View.HorizontalLine import HorizontalLine
from Shared.View.OperationsTableModel import OperationsTableModel


class RequestsOperations(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.initUI()
        self.__ops = {}

    def initUI(self):
        self.layout = QFormLayout()
        self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        twoListsOfSets = QWidget()
        twoListsOfSets.setLayout(QHBoxLayout())
        twoListsOfSets.layout().setContentsMargins(5, 10, 5, 5)
        twoListsOfSets.layout().setSpacing(0)

        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        effect.setColor(QColor(0, 0, 0, 160))
        effect.setOffset(0.0)

        self.requestList = QListView()
        self.requestList.setSpacing(3)
        self.requestList.setAutoFillBackground(True)
        self.requestList.setGraphicsEffect(effect)
        self.requestList.setFrameStyle(QFrame.NoFrame)
        self.requestList.viewport().setAutoFillBackground(False)
        self.requestList.setFlow(QListView.LeftToRight)
        self.requestList.setWrapping(True)
        self.requestList.setResizeMode(QListView.Adjust)
        self.requestList.setUniformItemSizes(True)
        self.requestsModel = QStandardItemModel()
        self.requestList.setModel(self.requestsModel)

        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        effect.setColor(QColor(0, 0, 0, 160))
        effect.setOffset(0.0)

        self.requestList2 = QListView()
        self.requestList2.setSpacing(3)
        self.requestList2.setAutoFillBackground(True)
        self.requestList2.setGraphicsEffect(effect)
        self.requestList2.setFrameStyle(QFrame.NoFrame)
        self.requestList2.viewport().setAutoFillBackground(False)
        self.requestList2.setFlow(QListView.LeftToRight)
        self.requestList2.setWrapping(True)
        self.requestList2.setResizeMode(QListView.Adjust)
        self.requestList2.setUniformItemSizes(True)
        self.requestsModel2 = QStandardItemModel()
        self.requestList2.setModel(self.requestsModel2)

        twoListsOfSets.layout().addWidget(self.requestList)
        twoListsOfSets.layout().addWidget(self.requestList2)

        self.layout.addRow("SETS", twoListsOfSets)
        self.layout.addRow(HorizontalLine(self))

        self.operationSelection = QGroupBox()
        self.operationSelection.setFlat(True)
        self.operationSelection.setLayout(QVBoxLayout())

        self.buttonIntersection = QRadioButton("Intersection")
        self.operationSelection.layout().addWidget(self.buttonIntersection)
        self.buttonIntersection.clicked.connect(self.__disableSecondRequestList)
        self.buttonIntersection.click()

        self.buttonUnion = QRadioButton("Union")
        self.operationSelection.layout().addWidget(self.buttonUnion)
        self.buttonUnion.clicked.connect(self.__disableSecondRequestList)

        self.buttonDiff = QRadioButton("Difference")
        self.operationSelection.layout().addWidget(self.buttonDiff)
        self.buttonDiff.clicked.connect(self.__enableSecondRequestList)

        self.layout.addRow("OPERATION", self.operationSelection)

        self.buttonApplyWidget = QWidget()
        self.buttonApplyWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.buttonApplyLayout = QHBoxLayout()
        self.buttonApplyLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonApplyWidget.setLayout(self.buttonApplyLayout)
        self.buttonApply = QPushButton("Apply")
        self.buttonApply.clicked.connect(self.__applyOp)
        self.operationSelection.layout().addWidget(self.buttonApply)
        self.buttonApplyLayout.addWidget(self.buttonApply, alignment=Qt.AlignRight)
        self.layout.addRow("", self.buttonApplyWidget)
        self.layout.addRow(HorizontalLine(self))

        self.layout.addRow("RESULTS", None)

        self.resultingSets = QTableView()
        self.resultingSets.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resultingSets.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.resultingSets.setModel(OperationsTableModel())
        self.layout.addRow(self.resultingSets)
        self.layout.addRow(HorizontalLine(self))

        self.outputSetSelection = QComboBox()
        self.outputSetSelection.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.layout.addRow("OUTPUT SET", self.outputSetSelection)

        self.setLayout(self.layout)

    def outputSet(self):
        return self.outputSetSelection.currentText()

    @property
    def ops(self):
        return self.__ops

    def __applyOp(self):
        includedSets = [self.requestsModel.item(i).text() for i in range(self.requestsModel.rowCount()) if
                        self.requestsModel.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]

        if self.buttonUnion.isChecked():
            if len(includedSets) > 1:
                self.__addOp(OverpassUnion(), includedSets)
        elif self.buttonIntersection.isChecked():
            if len(includedSets) > 1:
                self.__addOp(OverpassIntersection(), includedSets)
        elif self.buttonDiff.isChecked():
            excludedSets = [self.requestsModel2.item(i).text() for i in range(self.requestsModel2.rowCount()) if
                            self.requestsModel2.item(i).data(Qt.CheckStateRole) == QVariant(Qt.Checked)]

            if len(includedSets) == 1 and len(excludedSets) > 0:
                self.__addOp(OverpassDiff(includedSets[0]), excludedSets)

    def __addOp(self, op, sets):
        setName = OverpassQuery.getUniqueSetName()
        self.__ops[setName] = op
        self.__ops[setName].addSets(sets)
        self.resultingSets.model().addOp(setName, self.__ops[setName])
        self.addRequest(setName)
        self.cleanRequestList()

    def __enableSecondRequestList(self):
        self.requestList2.show()

    def __disableSecondRequestList(self):
        self.requestList2.hide()

    def addRequest(self, name):
        self.requestsModel.beginInsertRows(QModelIndex(), self.requestsModel.rowCount(), self.requestsModel.rowCount())
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
        self.requestsModel.appendRow(item)
        self.requestsModel.endInsertRows()

        self.requestsModel2.beginInsertRows(QModelIndex(), self.requestsModel2.rowCount(),
                                            self.requestsModel2.rowCount())
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
        self.requestsModel2.appendRow(item)
        self.requestsModel2.endInsertRows()

        self.outputSetSelection.addItem(name)

    def removeSetAndDependencies(self, setName):
        removeList = [setName]

        for set in removeList:
            removeList.extend([i for i in self.__removeSet(set) if i not in removeList])

    def __removeSet(self, setName):
        dependencies = []
        for opName in self.__ops.keys():
            self.__ops[opName].removeSet(setName)
            if not self.__ops[opName].isValid():
                dependencies.append(opName)

        for i in range(self.requestsModel.rowCount()):
            if self.requestsModel.item(i).text() == setName:
                self.requestsModel.beginRemoveRows(QModelIndex(), i, i)
                self.requestsModel.removeRow(i)
                self.requestsModel.endInsertRows()

                self.requestsModel2.beginRemoveRows(QModelIndex(), i, i)
                self.requestsModel2.removeRow(i)
                self.requestsModel2.endInsertRows()

                self.outputSetSelection.removeItem(i)
                break

        if setName in self.__ops.keys():
            self.resultingSets.model().removeOp(setName)
            del self.__ops[setName]

        return dependencies

    def cleanRequestList(self):
        for i in range(self.requestsModel.rowCount()):
            self.requestsModel.item(i).setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)
            self.requestsModel2.item(i).setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace and self.resultingSets.hasFocus():

            advice = "Are you sure?\nAll sets containing this one will be deleted if they are no longer valid"
            reply = QMessageBox.question(self, "Remove request operation", advice)

            if reply == QMessageBox.Yes:
                select = self.resultingSets.selectionModel()
                while len(select.selectedRows()) > 0:
                    self.removeSetAndDependencies(
                        self.resultingSets.model().getOpByIndex(select.selectedRows()[0].row()))

        event.accept()