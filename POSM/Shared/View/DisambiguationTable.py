import copy
from abc import abstractmethod

import networkx as nx
import osmnx as ox
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor


class DisambiguationTable(QAbstractTableModel):

    def __init__(self, jsonData):
        QAbstractTableModel.__init__(self)

        self.json = jsonData
        self.nodes = []
        self.data = []
        for i in jsonData["elements"]:
            if i["type"] == "way":
                self.data.append(i)
            elif i["type"] == "node":
                self.nodes.append(i)

        self.headerItems = []
        self.alt = []

    def showMore(self):
        newRowCount = min(self.rowCount + 5, len(self.alt)) if self.alt else 0
        if newRowCount != self.rowCount:
            self.beginInsertRows(QModelIndex(), self.rowCount, newRowCount - 1)
            self.rowCount = newRowCount
            self.endInsertRows()

    def showLess(self):
        newRowCount = max(self.rowCount - 5, 2) if self.alt else 0
        if newRowCount != self.rowCount:
            self.beginRemoveRows(QModelIndex(), newRowCount, self.rowCount - 1)
            self.rowCount = newRowCount
            self.endRemoveRows()

    def rowCount(self, parent=QModelIndex(), **kwargs):
        return self.rowCount

    def columnCount(self, parent=QModelIndex(), **kwargs):
        return len(self.headerItems)

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headerItems[section]
        else:
            return "{}".format(section)

    @abstractmethod
    def getAllColumns(self):
        pass

    @abstractmethod
    def getDictData(self, index):
        pass

    @abstractmethod
    def getRowJson(self, indexes):
        pass

    @abstractmethod
    def data(self, index, role=Qt.DisplayRole):
        pass

    @abstractmethod
    def updateAlt(self):
        pass


class DisconnectedWaysTable(DisambiguationTable):

    def __init__(self, jsonData):
        super().__init__(jsonData)
        self.allKeys = frozenset([])
        for i in self.data:
            self.allKeys |= frozenset(i["tags"].keys())
        self.allKeys -= frozenset(["osmid", "length"])
        ox.config(useful_tags_path=list(self.allKeys))

        self.subgraphs = []

        self.updateAlt()
        self.rowCount = min(5, len(self.alt)) if self.alt else 0

    def getAllColumns(self):
        return self.headerItems

    def getDictData(self, index):
        result = {}
        unselectedEdges = [e[2] for e in self.subgraphs[index].edges(data=True)]
        for key in self.allKeys:
            prevSize = len(unselectedEdges)
            alternatives = [self.alt[i][key] for i in list(range(len(self.alt))) if i != index]
            includedValues = self.alt[index][key].difference(*alternatives)
            if includedValues == self.alt[index][key]:
                return {key: includedValues}, []
            elif len(includedValues) != 0:
                unselectedEdges = list(filter(lambda edge: edge[key] not in list(includedValues), unselectedEdges))
                if prevSize != len(unselectedEdges):
                    result[key] = includedValues
                    if len(unselectedEdges) == 0:
                        return result, []
        ids = [edge["osmid"] for edge in unselectedEdges]
        return result, ids

    def getRowJson(self, indexes):
        if len(indexes) > 0:
            G = self.subgraphs[indexes[0].row()]
            for i in indexes[1:]:
                G = nx.union(self.subgraphs[i.row()], G)
            return G
        else:
            return None

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            return ", ".join([str(value) for value in self.alt[row][self.headerItems[column]]])
        elif role == Qt.BackgroundRole:
            return QColor(Qt.white)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight

        return None

    def updateAlt(self):
        self.alt = []
        self.subgraphs = []

        G = ox.create_graph([self.json], retain_all=True)
        updatedHeader = frozenset([])
        for nodes in nx.weakly_connected_components(G):
            subgraph = nx.induced_subgraph(G, nodes)
            self.subgraphs.append(subgraph)

            altAppend = {}
            for key in self.allKeys:
                values = []
                edges = subgraph.edges(data=True)
                for edge in edges:
                    values.append(edge[2].get(key))
                altAppend[key] = frozenset(values)
                if len(altAppend[key]) == 1 and values[0] is not None:
                    updatedHeader |= frozenset([key])
            self.alt.append(altAppend)
        self.headerItems = list(updatedHeader)


class SimilarWaysTable(DisambiguationTable):

    def __init__(self, jsonData):
        super().__init__(jsonData)
        self.allKeys = frozenset([])
        for i in self.data:
            self.allKeys |= frozenset(i["tags"].keys())
        self.allKeys -= frozenset(["osmid", "length"])
        ox.config(useful_tags_path=list(self.allKeys))

        self.headerItems = list(frozenset(["highway", "name", "maxspeed", "ref", "lanes", "oneway"]) & self.allKeys)

        self.updateAlt()
        self.rowCount = min(5, len(self.alt)) if self.alt else 0

    def updateColumns(self, keys):
        keySet = frozenset(keys)
        if keySet != frozenset(self.headerItems):
            self.beginResetModel()
            self.headerItems = list(keySet)
            self.updateAlt()
            self.rowCount = min(self.rowCount, len(self.alt)) if self.alt else 0
            self.endResetModel()

    def getSelectedColumns(self):
        return self.headerItems

    def getAllColumns(self):
        return self.allKeys

    def getDictData(self, index):
        return {k: self.alt[index][0].get(k) for k in self.headerItems}

    def getRowJson(self, indexes):
        if len(indexes) > 0:
            result = copy.deepcopy(self.json)
            result["elements"] = copy.deepcopy(self.nodes)
            for i in indexes:
                result["elements"] += self.alt[i.row()][2]
            return ox.create_graph([result], retain_all=True)
        else:
            return None

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            return self.alt[row][0].get(self.headerItems[column])
        elif role == Qt.BackgroundRole:
            return QColor(Qt.white)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight

        return None

    def updateAlt(self):
        self.alt = []

        for i in self.data:
            reducedData = {k: i["tags"].get(k) for k in self.headerItems}
            coincidence = [i for i in range(len(self.alt)) if self.alt[i][0] == reducedData]
            if len(coincidence) != 0:
                self.alt[coincidence[0]] = (
                    self.alt[coincidence[0]][0], self.alt[coincidence[0]][1] + 1, self.alt[coincidence[0]][2] + [i])
            else:
                self.alt.append((reducedData, 1, [i]))
        self.alt = sorted(self.alt, key=lambda x: x[1], reverse=True)
