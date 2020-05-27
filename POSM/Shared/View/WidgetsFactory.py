import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy

from Shared.View.IconButton import IconButton
from Shared.constants import picturesDir


class WidgetFactory(object):

    @staticmethod
    def buildIconButtonGroup(buttonsSetting, alignment=Qt.AlignRight):
        buttonsList = QWidget()
        buttonsListLayout = QHBoxLayout()
        buttonsList.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        buttonsListLayout.setAlignment(alignment)
        buttonsListLayout.setSpacing(0)
        buttonsListLayout.setContentsMargins(0, 0, 0, 0)
        buttonsList.setLayout(buttonsListLayout)

        for setting in buttonsSetting:
            button = IconButton(QIcon(os.path.join(picturesDir, setting["image"])),
                                buttonsList.windowHandle(),
                                buttonsList.height())
            button.setToolTip(setting["tooltip"])
            button.setFlat(True)
            if setting["checkable"]:
                button.setCheckable(True)
                button.toggled.connect(setting["action"])
            else:
                button.clicked.connect(setting["action"])
            buttonsListLayout.addWidget(button)

        return buttonsList
