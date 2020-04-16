var request;
new QWebChannel(qt.webChannelTransport, function (channel) {
    request = channel.objects.request;
});

var coors = %s;
var latlngs = [];
for (i in coors) {
    latlngs.push(L.latLng(coors[i][0], coors[i][1]));
}

var isClickActivated = %s;

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
    request.__setPolygons__([]);
}

function disablePolygon() {
    isClickActivated = false;
}

function enablePolygon() {
    isClickActivated = true;
}

function getPolygons() {
    return latlngs;
}

document.onkeydown = function KeyPress(e) {
    if (e.key === "z" && (e.ctrlKey || e.metaKey)) {
        latlngs.pop();
        draw();
        request.__setPolygons__(getPolygons());
    }
};

mapId.on('click', function (e) {
    if (isClickActivated) {
        latlngs.push(e.latlng);
        draw();
        request.__setPolygons__(getPolygons());
    }
});

draw();