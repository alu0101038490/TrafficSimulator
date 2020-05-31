var latlngs = %s;
var mapId = eval(document.body.children[0].id);
var polygon = null;

function draw() {
    if (polygon != null) {
        polygon.removeFrom(mapId);
    }
    polygon = L.polygon(latlngs, {color: 'red'}).addTo(mapId);
}

function cleanPolygon() {
    if (polygon != null)
        polygon.removeFrom(mapId);
    latlngs = [];
}

function getPolygons() {
    const result = [];
    for(const i in latlngs){
        result.push([latlngs[i].lat, latlngs[i].lng])
    }
    return result;
}

document.onkeydown = function KeyPress(e) {
    if (e.key === "z" && (e.ctrlKey || e.metaKey)) {
        latlngs.pop();
        draw();
    }
};

mapId.on('click', function (e) {
    latlngs.push(e.latlng);
    draw();
});

draw();