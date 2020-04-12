var mapId = eval(document.body.children[0].id);
var polygon = null;

function draw() {
    if(polygon != null) {
        polygon.removeFrom(mapId);
    }
    polygon = L.polygon(latlngs, {color: 'red'}).addTo(mapId);
}

mapId.on('click', function(e) {
    if (isClickActivated){
        latlngs.push(e.latlng);
        draw();
    }
});

function cleanPolygon() {
    if(polygon != null)
        polygon.removeFrom(mapId);
    latlngs = [];
}

function disablePolygon() {
    isClickActivated = false;
}

function enablePolygon() {
    isClickActivated = true;
}

function getPolygons() {
    coors = [];
    for(i in latlngs){
        coors.push([latlngs[i].lat, latlngs[i].lng]);
    }
    return [coors, isClickActivated.toString()];
}

document.onkeydown = function KeyPress(e) {
    var evtobj = window.event? event : e;
    if (evtobj.keyCode === 90 && (event.ctrlKey || event.metaKey)) {
        latlngs.pop();
        draw();
    }
};

draw();