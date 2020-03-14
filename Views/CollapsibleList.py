from PyQt5.QtWidgets import QMenu, QPushButton, QCheckBox, QWidgetAction


class CheckableComboBox(QPushButton):

    def __init__(self, title):
        super(CheckableComboBox, self).__init__()
        self.setText(title)
        self.toolMenu = QMenu(self)
        self.toolMenu.setMaximumHeight(200)
        self.setMenu(self.toolMenu)

    def addItem(self, text, checked=False):
        checkBox = QCheckBox(self.toolMenu)
        checkBox.setText(text)
        checkBox.setChecked(checked)

        checkableAction = QWidgetAction(self.toolMenu)
        checkableAction.setDefaultWidget(checkBox)
        self.toolMenu.addAction(checkableAction)

    def setDropdownMenuSignal(self, f):
        self.toolMenu.aboutToHide.connect(f)

    def getSelectedItems(self):
        return [a.defaultWidget().text() for a in self.toolMenu.actions() if a.defaultWidget().isChecked()]
