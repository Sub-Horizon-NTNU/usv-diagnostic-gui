import base64
import math
import os
from ament_index_python.packages import get_package_share_directory
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, pyqtSlot


def _load_boat_icon() -> str:
    try:
        config_dir = os.path.join(
            get_package_share_directory('usv_diagnostic_gui'), 'config'
        )
        img_path = os.path.join(config_dir, 'usv_image.png')
        with open(img_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ''


def _make_compass_svg(size=160) -> str:
    cx = cy = size / 2
    outer_r = size / 2 - 3
    inner_major_r = outer_r - 11   # long tick
    inner_minor_r = outer_r - 6    # short tick
    label_r = outer_r - 24

    parts = []
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" '
        f'fill="rgba(20,20,20,0.87)" stroke="#555" stroke-width="1.5"/>'
    )

    cardinals = {
        0:   ('N', '#ff5555', 13, 'bold'),
        90:  ('E', '#bbbbbb', 12, 'normal'),
        180: ('S', '#bbbbbb', 12, 'normal'),
        270: ('W', '#bbbbbb', 12, 'normal'),
    }

    for deg in range(0, 360, 5):
        s = math.sin(math.radians(deg))
        c = math.cos(math.radians(deg))

        is_major = deg % 30 == 0
        is_minor = deg % 10 == 0 and not is_major
        if not (is_major or is_minor):
            continue

        ir = inner_major_r if is_major else inner_minor_r
        x1 = cx + outer_r * s
        y1 = cy - outer_r * c
        x2 = cx + ir * s
        y2 = cy - ir * c
        sw = '1.5' if is_major else '0.8'
        stroke = '#777' if is_major else '#555'
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

        if is_major:
            lx = cx + label_r * s
            ly = cy - label_r * c
            if deg in cardinals:
                label, color, fs, fw = cardinals[deg]
            else:
                label, color, fs, fw = str(deg), '#777777', 9, 'normal'
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dy="0.35em" '
                f'fill="{color}" font-size="{fs}" font-weight="{fw}" '
                f'font-family="sans-serif">{label}</text>'
            )

    rx, ry, rw, rh = cx - 18, cy + 12, 36, 17
    parts.append(
        f'<rect x="{rx:.0f}" y="{ry:.0f}" width="{rw}" height="{rh}" rx="3" '
        f'fill="rgba(0,0,0,0.65)" stroke="#444" stroke-width="0.8"/>'
    )
    parts.append(
        f'<text id="compass-heading-text" x="{cx:.0f}" y="{ry + rh*0.72:.0f}" '
        f'text-anchor="middle" fill="#ffffff" font-size="11" '
        f'font-family="monospace" font-weight="bold">000&#176;</text>'
    )

    # needle points North (up) at heading 0
    nt = cy - outer_r + 14   # north tip y
    st = cy + outer_r - 14   # south tip y
    w = 5.5                   # half-width
    parts.append(
        f'<g id="compass-needle" transform="rotate(0,{cx:.0f},{cy:.0f})">'
        f'<polygon points="{cx},{nt:.0f} {cx-w},{cy:.0f} {cx},{cy-12:.0f} {cx+w},{cy:.0f}" fill="#ff5555"/>'
        f'<polygon points="{cx},{st:.0f} {cx-w},{cy:.0f} {cx},{cy+12:.0f} {cx+w},{cy:.0f}" fill="#cccccc"/>'
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="#ffffff" stroke="#333" stroke-width="1"/>'
        f'</g>'
    )

    content = '\n  '.join(parts)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">\n  {content}\n</svg>'
    )


_BOAT_DATA_URL = _load_boat_icon()
_COMPASS_SVG = _make_compass_svg()
_COMPASS_CX = 80   # half of the compass SVG size (160)

_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body {{ margin: 0; padding: 0; height: 100%; background: #1e1e1e; }}
    #map {{ width: 100%; height: 100%; }}
    .usv-icon img {{ transform-origin: center; }}
    #pos-lost {{
      display: none;
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: 1000;
      background: rgba(180, 0, 0, 0.82);
      color: #ffffff;
      font-family: sans-serif;
      font-size: 18px;
      font-weight: bold;
      padding: 14px 24px;
      border-radius: 6px;
      letter-spacing: 1px;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="pos-lost">USV POSITION NOT DETECTED</div>
  <script>
    var map = L.map('map').setView([0, 0], 2);

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }}).addTo(map);

    var BOAT_SRC = "{boat_src}";
    var ICON_SIZE = 34;

    function makeIcon(heading) {{
      var rotate = heading - 90;
      var html = BOAT_SRC
        ? '<img src="' + BOAT_SRC + '" style="width:' + ICON_SIZE + 'px;height:' + ICON_SIZE + 'px;transform:rotate(' + rotate + 'deg);">'
        : '<div style="width:14px;height:14px;background:#00aaff;border:2px solid #fff;border-radius:50%;box-shadow:0 0 6px #00aaff;"></div>';
      var size = BOAT_SRC ? ICON_SIZE : 14;
      var anchor = size / 2;
      return L.divIcon({{html: html, iconSize: [size, size], iconAnchor: [anchor, anchor], className: 'usv-icon'}});
    }}

    var usvMarker = null;
    var trackLine = null;
    var fovPolygon = null;
    var trackCoords = [];
    var autoFollow = true;
    var firstFix = true;

    var FOV_DEG = 72;
    var FOV_RANGE_M = 20;

    function destinationPoint(lat, lon, bearing_deg, dist_m) {{
      var R = 6371000;
      var lat_r = lat * Math.PI / 180;
      var lon_r = lon * Math.PI / 180;
      var b_r   = bearing_deg * Math.PI / 180;
      var lat2  = Math.asin(Math.sin(lat_r) * Math.cos(dist_m / R) +
                            Math.cos(lat_r) * Math.sin(dist_m / R) * Math.cos(b_r));
      var lon2  = lon_r + Math.atan2(Math.sin(b_r) * Math.sin(dist_m / R) * Math.cos(lat_r),
                                     Math.cos(dist_m / R) - Math.sin(lat_r) * Math.sin(lat2));
      return [lat2 * 180 / Math.PI, lon2 * 180 / Math.PI];
    }}

    function updateFov(lat, lon, heading) {{
      var half = FOV_DEG / 2;
      var origin = destinationPoint(lat, lon, heading, 0.5);
      var pts = [origin];
      var steps = 16;
      for (var i = 0; i <= steps; i++) {{
        var angle = heading - half + FOV_DEG * i / steps;
        pts.push(destinationPoint(origin[0], origin[1], angle, FOV_RANGE_M));
      }}
      pts.push(origin);
      if (!fovPolygon) {{
        fovPolygon = L.polygon(pts, {{
          color: '#ffdd00', weight: 1, opacity: 0.7,
          fillColor: '#ffdd00', fillOpacity: 0.12
        }}).addTo(map);
      }} else {{
        fovPolygon.setLatLngs(pts);
      }}
    }}

    function updatePosition(lat, lon, heading) {{
      var latlng = [lat, lon];

      if (!usvMarker) {{
        usvMarker = L.marker(latlng, {{icon: makeIcon(heading)}}).addTo(map);
      }} else {{
        usvMarker.setLatLng(latlng);
        usvMarker.setIcon(makeIcon(heading));
      }}

      trackCoords.push(latlng);
      if (!trackLine) {{
        trackLine = L.polyline(trackCoords, {{color: '#00aaff', weight: 2, opacity: 0.6}}).addTo(map);
      }} else {{
        trackLine.setLatLngs(trackCoords);
      }}

      if (firstFix) {{
        map.setView(latlng, 16);
        firstFix = false;
      }} else if (autoFollow) {{
        map.panTo(latlng);
      }}

      updateFov(lat, lon, heading);
      updateCompass(heading);
    }}

    function setAutoFollow(val) {{ autoFollow = val; }}

    function showPositionLost() {{ document.getElementById('pos-lost').style.display = 'block'; }}
    function hidePositionLost() {{ document.getElementById('pos-lost').style.display = 'none'; }}

    function clearTrack() {{
      trackCoords = [];
      if (trackLine) {{ trackLine.setLatLngs([]); }}
    }}

    var compassControl = L.control({{position: 'bottomright'}});
    compassControl.onAdd = function() {{
      var div = L.DomUtil.create('div');
      div.innerHTML = `{compass_svg}`;
      L.DomEvent.disableClickPropagation(div);
      return div;
    }};
    compassControl.addTo(map);

    function updateCompass(heading) {{
      var needle = document.getElementById('compass-needle');
      if (needle) {{
        needle.setAttribute('transform', 'rotate(' + heading + ',{compass_cx},{compass_cx})');
      }}
      var txt = document.getElementById('compass-heading-text');
      if (txt) {{
        var deg = Math.round(heading) % 360;
        txt.textContent = deg.toString().padStart(3, '0') + '\u00b0';
      }}
    }}
  </script>
</body>
</html>""".format(boat_src=_BOAT_DATA_URL, compass_svg=_COMPASS_SVG, compass_cx=_COMPASS_CX)


class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        toolbar = QHBoxLayout()

        self._follow_btn = QPushButton("Following USV")
        self._follow_btn.setCheckable(True)
        self._follow_btn.setChecked(True)
        self._follow_btn.toggled.connect(self._on_follow_toggled)
        self._follow_btn.setStyleSheet(
            "QPushButton { background-color: #3c3c3c; color: white; border: 1px solid #555; padding: 4px 10px; border-radius: 3px; }"
            "QPushButton:checked { background-color: #005f8e; color: white; }"
            "QPushButton:hover { background-color: #4a4a4a; }"
        )

        clear_btn = QPushButton("Clear Track")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #3c3c3c; color: white; border: 1px solid #555; padding: 4px 10px; border-radius: 3px; }"
            "QPushButton:hover { background-color: #4a4a4a; }"
        )
        clear_btn.clicked.connect(self._clear_track)

        toolbar.addWidget(self._follow_btn)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._view = QWebEngineView()
        self._view.setHtml(_MAP_HTML, QUrl("about:blank"))
        layout.addWidget(self._view, 1)

        self._pos_timer = QTimer(self)
        self._pos_timer.setSingleShot(True)
        self._pos_timer.setInterval(2000)
        self._pos_timer.timeout.connect(
            lambda: self._view.page().runJavaScript("showPositionLost();")
        )
        self._pos_timer.start()

    @pyqtSlot(float, float, float)
    def update_position(self, lat: float, lon: float, heading: float):
        self._pos_timer.start()
        self._view.page().runJavaScript(f"hidePositionLost(); updatePosition({lat}, {lon}, {heading});")

    def _on_follow_toggled(self, checked: bool):
        self._follow_btn.setText("Following USV" if checked else "Free View")
        val = "true" if checked else "false"
        self._view.page().runJavaScript(f"setAutoFollow({val});")

    def _clear_track(self):
        self._view.page().runJavaScript("clearTrack();")
