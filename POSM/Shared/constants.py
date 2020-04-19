import os
import pathlib
from enum import Enum


class TagComparison(Enum):
    EQUAL = 1
    AT_MOST = 2
    AT_LEAST = 3
    CONTAIN_ALL = 4
    IS_ONE_OF = 5
    HAS_KEY = 6
    HAS_ONE_KEY = 7
    HAS_NOT_KEY = 8


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

# ==================== STYLE =====================
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

# ==================== ROUTES ====================
resDir = pathlib.Path(__file__).parent.parent.parent.absolute().joinpath("Resources")
javascriptFile = os.path.join(resDir, "javascript", "polygonsManagement.js")
tempDir = os.path.join(resDir, "temp")
tableDir = os.path.join(tempDir, "table.osm.xml")
responsePath = os.path.join(tempDir, "response.osm.xml")
tilePath = os.path.join(resDir, "temp", "tile.html")
defaultTileMap = os.path.join(resDir, "html", "tile.html")
typemapPath = os.path.join(resDir, "typemap")
picturesDir = os.path.join(resDir, "pictures")

# ==================== HTML ====================
with open(javascriptFile, "r") as f:
    JS_SCRIPT = f.read()

with open(defaultTileMap, "r") as f:
    EMPTY_HTML = f.read()
