from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor


class OperationsTableModel(QAbstractTableModel):

    def __init__(self):
        QAbstractTableModel.__init__(self)

        self.headerItems = ["Name", "Type", "Components"]
        self.ops = []

    def addOp(self, name, op):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self.ops.append((name, op))
        self.endInsertRows()

    def removeOp(self, opToRemove):
        for i in range(len(self.ops)):
            if self.ops[i][0] == opToRemove:
                self.beginRemoveRows(QModelIndex(), i, i)
                self.ops.pop(i)
                self.endRemoveRows()
                break

    def getOpByIndex(self, i):
        return self.ops[i][0]

    def rowCount(self, parent=QModelIndex(), **kwargs):
        return len(self.ops)

    def columnCount(self, parent=QModelIndex(), **kwargs):
        return len(self.headerItems)

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headerItems[section]
        else:
            return "{}".format(section)

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            if column == 0:
                return self.ops[row][0]
            elif column == 1:
                return self.ops[row][1].getType()
            elif column == 2:
                if self.ops[row][1].getType() == "Difference":
                    return "%s - %s" % (self.ops[row][1].includedSet, ",".join(self.ops[row][1].sets))
                else:
                    return ",".join(self.ops[row][1].sets)
        elif role == Qt.BackgroundRole:
            return QColor(QColor(42, 42, 42))
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight
        elif role == Qt.ForegroundRole:
            return QColor(QColor(160, 160, 160))

        return None