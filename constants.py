from enum import Enum


class Surround(Enum):
    AROUND = 1
    ADJACENT = 2
    NONE = 3


class OsmType(Enum):
    NODES = "node"
    WAYS = "way"
    RELATIONS = "rel"
    AREA = "area"
    NW = "nw"
    NR = "nr"
    WR = "wr"
    NWR = "nwr"

    @classmethod
    def getType(self, node, way, rel, area):
        binaryType = (1 * node) | (2 * way) | (4 * rel)

        switchCase = [0, OsmType.NODES, OsmType.WAYS, OsmType.NW, OsmType.RELATIONS, OsmType.NR, OsmType.WR,
                      OsmType.NWR]

        if area:
            return OsmType.AREA
        elif binaryType == 0:
            raise RuntimeError("No type selected.")
        else:
            return switchCase[binaryType]


APP_STYLESHEET = """

    QGroupBox:flat {
        border: none;
    }

    QToolBox::tab {
        background: #454545;
    }

    QToolButton {
        background-color: #f6f7fa;
    }

    QToolButton:pressed {
        background-color: #dadbde;
    }

    QToolTip {
        border: 2px solid darkkhaki;
        padding: 5px;
        border-radius: 3px;
        opacity: 200;
    }   

    FilterWidget {
        background: #353535;
        border: 0px solid green;
        border-radius: 7px;
    }

    QCalendarWidget QToolButton {
        background-color: #2A2A2A;
    }

    QCalendarWidget QToolButton::menu-indicator{image: none;}

    QCalendarWidget QWidget#qt_calendar_navigationbar
    { 
        background-color: #2A2A2A; 
    }

    """

JS_SCRIPT_ROUTE = """
    <script>
        var isClickActivated = {};
        var latlngs = {};
    </script>
    <script src="../javascript/polygonsManagement.js"></script>
"""
