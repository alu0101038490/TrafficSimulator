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

HTML_SCRIPTS = """

    var currentPolygon = 0;
    var interactiveMode = true
    var isClickActivated = [false];
    var polygon = [null];
    var latlngs = [[]];
    
    var manualModePolygon = null
    var manualModeLatlngs = []

    function draw() {
        if(interactiveMode) {
            if(polygon[currentPolygon] != null) {
                polygon[currentPolygon].removeFrom(%s);  
            }
            polygon[currentPolygon] = L.polygon(latlngs[currentPolygon], {color: 'red'}).addTo(%s);  
        } else {
            if(manualModePolygon != null) {
                manualModePolygon.removeFrom(%s);  
            }
            manualModePolygon = L.polygon(manualModeLatlngs, {color: 'red'}).addTo(%s);
        }
    }

    %s.on('click', function(e) { 
        if(!interactiveMode) {
            manualModeLatlngs.push(e.latlng);
            draw();
        } else if(isClickActivated[currentPolygon] && currentPolygon >= 0) {
            latlngs[currentPolygon].push(e.latlng);
            draw();
        }
    });

    function addPolygon() {
        latlngs.push([]);
        isClickActivated.push(false)
        polygon.push(null);
    }

    function cleanPolygon() {
        if(interactiveMode) {
            if(polygon[currentPolygon] != null)
                polygon[currentPolygon].removeFrom(%s);
            latlngs[currentPolygon] = [];
        } else {
            if(manualModePolygon != null)
                manualModePolygon.removeFrom(%s);
            manualModeLatlngs = [];
        }
    }

    function disablePolygon() {
        isClickActivated[currentPolygon] = false;
    }

    function enablePolygon() {
        isClickActivated[currentPolygon] = true;
    }

    function changeCurrentPolygon(i) {
        if(polygon[currentPolygon] != null)
            polygon[currentPolygon].removeFrom(%s);
        currentPolygon = i;
        draw();
    }
    
    function switchInteractiveManualMode() {
        if(interactiveMode) {
            if (polygon[currentPolygon] != null)
                polygon[currentPolygon].removeFrom(%s);
        } else {
            if (manualModePolygon)
                manualModePolygon.removeFrom(%s);
        }
        interactiveMode = !interactiveMode;
        draw();
    }
    
    function getManualPolygon() {
        result = []
        for (i in manualModeLatlngs) {
            result.push([manualModeLatlngs[i].lat, manualModeLatlngs[i].lng])
        }
        return result;
    }

    function removeCurrentPolygon() {
        cleanPolygon();
        isClickActivated.splice(currentPolygon, 1);
        latlngs.splice(currentPolygon, 1);
        polygon.splice(currentPolygon, 1);
        if(currentPolygon == polygon.length) {
            currentPolygon = currentPolygon - 1;
        }
    }

    function getPolygons() {
        result = []
        for(i in latlngs){
            aux = []
            for (j in latlngs[i]) {
                aux.push([latlngs[i][j].lat, latlngs[i][j].lng])
            }
            result.push(aux)
        }
        return [currentPolygon, result, "[" + isClickActivated.toString() + "]", getManualPolygon(), interactiveMode.toString()];
    }

    function setPolygons(current, coors, clicksActivated, manualPolygon, mode) {
        latlngs = [];
        polygons = [];
        manualModeLatlngs = [];
        manualModePolygon = null;
        interactiveMode = mode;
        isClickActivated = clicksActivated;
        for (i in coors){
            latlngs.push([]);
            for (j in coors[i]) { 
                latlngs[i].push(L.latLng(coors[i][j][0], coors[i][j][1]));
            }
            polygons.push(null);
        }
        for (i in manualPolygon) { 
            manualModeLatlngs.push(L.latLng(manualPolygon[i][0], manualPolygon[i][1]));
        }
        currentPolygon = current;
        draw();
    }

    function KeyPress(e) {
        var evtobj = window.event? event : e
        if (evtobj.keyCode == 90 && (event.ctrlKey || event.metaKey)) {
            if(interactiveMode) {
                latlngs[currentPolygon].pop();
            } else {
                manualModeLatlngs.pop()
            }
            draw();
        }
    }

    document.onkeydown = KeyPress;
    """