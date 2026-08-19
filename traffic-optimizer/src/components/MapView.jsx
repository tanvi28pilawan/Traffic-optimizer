import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL("leaflet/dist/images/marker-icon-2x.png", import.meta.url).href,
  iconUrl: new URL("leaflet/dist/images/marker-icon.png", import.meta.url).href,
  shadowUrl: new URL("leaflet/dist/images/marker-shadow.png", import.meta.url).href,
});

const createMarker = (colorStart, colorEnd, emoji, label) => L.divIcon({
  className: "",
  html: `
    <div class="marker-root">
      <div class="marker-glow"></div>
      <div class="marker-badge">${emoji}</div>
      <div class="marker-label">${label}</div>
    </div>
    <style>
      .marker-root {
        display: flex;
        flex-direction: column;
        align-items: center;
        pointer-events: none;
      }
      .marker-glow {
        position: absolute;
        width: 68px;
        height: 68px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0) 50%);
        filter: blur(5px);
        opacity: 0.85;
        animation: marker-pulse 2.5s ease-in-out infinite;
      }
      .marker-badge {
        position: relative;
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: radial-gradient(circle at 25% 25%, ${colorStart}, ${colorEnd});
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 900;
        box-shadow: 0 10px 22px rgba(0,0,0,0.25), inset 0 0 0 2px rgba(255,255,255,0.4);
        z-index: 1;
      }
      .marker-badge::before {
        content: "";
        position: absolute;
        inset: 6px;
        border-radius: 50%;
        background: rgba(255,255,255,0.18);
      }
      .marker-label {
        margin-top: 8px;
        font-size: 11px;
        font-weight: 800;
        color: #111;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        text-shadow: 0 1px 2px rgba(255,255,255,0.9);
      }
      @keyframes marker-pulse {
        0%, 100% { transform: scale(0.95); opacity: 0.85; }
        50% { transform: scale(1); opacity: 1; }
      }
    </style>
  `,
  iconSize: [52, 74],
  iconAnchor: [26, 74],
  popupAnchor: [0, -68],
});

const MARKERS = {
  source: (mode) => createMarker(
    mode === "emergency" ? "#FCA5A5" : mode === "delivery" ? "#93C5FD" : "#6EE7B7",
    mode === "emergency" ? "#DC2626" : mode === "delivery" ? "#2563EB" : "#059669",
    "📍", "SOURCE"
  ),
  destination: createMarker("#FDBA74", "#F59E0B", "🏁", "DESTINATION"),
  hospital: createMarker("#FCA5A5", "#EF4444", "🏥", "HOSPITAL"),
  stop: (i, color) => createMarker(color, color, `${i + 1}`, `STOP ${i + 1}`),
};

const MODE_COLORS = {
  normal: "#10B981",
  emergency: "#EF4444",
  delivery: "#3B82F6",
};

function MapUpdater({ route }) {
  const map = useMap();

  useEffect(() => {
    if (route?.path && route.path.length > 0) {
      const bounds = route.path.map(coord => [coord[0], coord[1]]);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [route, map]);

  return null;
}

export default function MapView({ mode, route }) {
  const color = MODE_COLORS[mode] || "#10B981";
  const center = [19.8762, 75.3433];

  return (
    <MapContainer
      center={center}
      zoom={13}
      style={{ width: "100%", height: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <MapUpdater route={route} />

      {route?.path && (
        <Polyline positions={route.path} color={color} weight={5} opacity={0.85} />
      )}

      {route?.source && (
        <Marker position={route.source} icon={MARKERS.source(mode)}>
          <Popup><strong>📍 Source</strong></Popup>
        </Marker>
      )}

      {mode === "normal" && route?.destination && (
        <Marker position={route.destination} icon={MARKERS.destination}>
          <Popup>
            <strong>🏁 Destination</strong>
            {route.distance_km && <><br />{route.distance_km} km</>}
          </Popup>
        </Marker>
      )}

      {mode === "emergency" && route?.hospitals?.map((h, i) => (
        <Marker key={i} position={h.coords} icon={MARKERS.hospital}>
          <Popup>
            <strong>🏥 {h.name}</strong>
            {h.distance_km && <><br />{h.distance_km} km away</>}
          </Popup>
        </Marker>
      ))}

      {mode === "emergency" && route?.destination && (
        <Marker position={route.destination} icon={MARKERS.hospital}>
          <Popup>
            <strong>🏥 {route.nearest_hospital}</strong>
            <br />{route.distance_km} km
          </Popup>
        </Marker>
      )}

      {mode === "delivery" && route?.stops?.map((stop, i) => (
        <Marker key={i} position={stop.coords} icon={MARKERS.stop(i, color)}>
          <Popup>
            <strong>Stop {i + 1}</strong>
            <br />{stop.name}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}