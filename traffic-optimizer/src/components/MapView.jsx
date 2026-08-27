import { useEffect, useRef, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import NavigationOverlay from "./NavigationOverlay";

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL(
    "leaflet/dist/images/marker-icon-2x.png",
    import.meta.url
  ).href,
  iconUrl: new URL(
    "leaflet/dist/images/marker-icon.png",
    import.meta.url
  ).href,
  shadowUrl: new URL(
    "leaflet/dist/images/marker-shadow.png",
    import.meta.url
  ).href,
});


// ======================================================
// CUSTOM MARKERS
// ======================================================

const createMarker = (
  colorStart,
  colorEnd,
  emoji,
  label
) =>
  L.divIcon({
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
          background: radial-gradient(
            circle,
            rgba(255,255,255,0.65) 0%,
            rgba(255,255,255,0) 50%
          );
          filter: blur(5px);
          opacity: 0.85;
          animation: marker-pulse 2.5s ease-in-out infinite;
        }

        .marker-badge {
          position: relative;
          width: 52px;
          height: 52px;
          border-radius: 50%;
          background: radial-gradient(
            circle at 25% 25%,
            ${colorStart},
            ${colorEnd}
          );
          color: #fff;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 22px;
          font-weight: 900;
          box-shadow:
            0 10px 22px rgba(0,0,0,0.25),
            inset 0 0 0 2px rgba(255,255,255,0.4);
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
          color: white;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        }

        @keyframes marker-pulse {
          0%, 100% {
            transform: scale(0.95);
            opacity: 0.85;
          }

          50% {
            transform: scale(1);
            opacity: 1;
          }
        }
      </style>
    `,

    iconSize: [52, 74],
    iconAnchor: [26, 74],
    popupAnchor: [0, -68],
  });


// ======================================================
// LIVE GPS ICON
// ======================================================

const liveLocationIcon = L.divIcon({
  className: "",

  html: `
    <div
      style="
        position: relative;
        width: 20px;
        height: 20px;
      "
    >
      <div
        style="
          position: absolute;
          inset: 0;
          border-radius: 50%;
          background: rgba(59,130,246,0.3);
          animation: livePulse 2s ease-in-out infinite;
        "
      ></div>

      <div
        style="
          position: absolute;
          inset: 4px;
          border-radius: 50%;
          background: #3B82F6;
          border: 2px solid white;
          box-shadow: 0 2px 8px rgba(59,130,246,0.6);
        "
      ></div>
    </div>

    <style>
      @keyframes livePulse {
        0%, 100% {
          transform: scale(1);
          opacity: 0.6;
        }

        50% {
          transform: scale(2);
          opacity: 0;
        }
      }
    </style>
  `,

  iconSize: [20, 20],
  iconAnchor: [10, 10],
});


// ======================================================
// MARKERS
// ======================================================

const MARKERS = {
  source: (mode) =>
    createMarker(
      mode === "emergency"
        ? "#FCA5A5"
        : mode === "delivery"
        ? "#93C5FD"
        : "#6EE7B7",

      mode === "emergency"
        ? "#DC2626"
        : mode === "delivery"
        ? "#2563EB"
        : "#059669",

      "📍",
      "SOURCE"
    ),

  destination: createMarker(
    "#FDBA74",
    "#F59E0B",
    "🏁",
    "DESTINATION"
  ),

  hospital: createMarker(
    "#FCA5A5",
    "#EF4444",
    "🏥",
    "HOSPITAL"
  ),

  stop: (i, color) =>
    createMarker(
      color,
      color,
      `${i + 1}`,
      `STOP ${i + 1}`
    ),
};


// ======================================================
// MODE COLORS
// ======================================================

const MODE_COLORS = {
  normal: "#10B981",
  emergency: "#EF4444",
  delivery: "#3B82F6",
};


// ======================================================
// MAP FIT ROUTE
// ======================================================

function MapUpdater({ route }) {
  const map = useMap();

  useEffect(() => {
    if (
      route?.path &&
      route.path.length > 0
    ) {
      const bounds = route.path.map(
        (coord) => [coord[0], coord[1]]
      );

      map.fitBounds(bounds, {
        padding: [50, 50],
      });
    }
  }, [route, map]);

  return null;
}


// ======================================================
// LIVE LOCATION
// ======================================================

function LiveLocation({ onLocationChange }) {
  const map = useMap();
  const markerRef = useRef(null);

  useEffect(() => {
    if (!navigator.geolocation) {
      console.log(
        "Geolocation is not supported."
      );

      return;
    }


    // Create GPS marker
    const marker = L.marker(
      [0, 0],
      {
        icon: liveLocationIcon,
      }
    ).addTo(map);

    markerRef.current = marker;


    // Watch user's GPS position
    const watchId =
      navigator.geolocation.watchPosition(

        (pos) => {
          const {
            latitude,
            longitude,
          } = pos.coords;

          const location = [
            latitude,
            longitude,
          ];


          // Move blue GPS marker
          marker.setLatLng(location);


          // Send location to NavigationOverlay
          if (onLocationChange) {
            onLocationChange(location);
          }
        },


        (err) => {
          console.log(
            "Location error:",
            err
          );
        },


        {
          enableHighAccuracy: true,
          maximumAge: 3000,
          timeout: 10000,
        }
      );


    // Cleanup GPS watcher
    return () => {
      navigator.geolocation.clearWatch(
        watchId
      );

      map.removeLayer(marker);
    };

  }, [map, onLocationChange]);


  return null;
}


// ======================================================
// MAIN MAP
// ======================================================

export default function MapView({
  mode,
  route,
}) {

  // GPS location shared with NavigationOverlay
  const [
    gpsLocation,
    setGpsLocation,
  ] = useState(null);


  const color =
    MODE_COLORS[mode] ||
    "#10B981";


  const center = [
    19.8762,
    75.3433,
  ];


  return (
    <div className="map-wrapper">

      <MapContainer
        center={center}
        zoom={13}
        style={{
          width: "100%",
          height: "100%",
        }}
      >

        {/* =================================================
            MAP TILES
        ================================================= */}

        <TileLayer
          attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>'
          url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
        />


        {/* =================================================
            MAP CONTROLS
        ================================================= */}

        <MapUpdater route={route} />


        {/* =================================================
            LIVE GPS
        ================================================= */}

        <LiveLocation
          onLocationChange={
            setGpsLocation
          }
        />


        {/* =================================================
            ROUTE
        ================================================= */}

        {route?.path && (
          <Polyline
            positions={route.path}
            color={color}
            weight={5}
            opacity={0.85}
          />
        )}


        {/* =================================================
            SOURCE
        ================================================= */}

        {route?.source && (
          <Marker
            position={route.source}
            icon={MARKERS.source(mode)}
          >
            <Popup>
              📍 Source
            </Popup>
          </Marker>
        )}


        {/* =================================================
            NORMAL DESTINATION
        ================================================= */}

        {mode === "normal" &&
          route?.destination && (

            <Marker
              position={route.destination}
              icon={MARKERS.destination}
            >

              <Popup>
                🏁 Destination —{" "}
                {route.distance_km} km
              </Popup>

            </Marker>
          )}


        {/* =================================================
            EMERGENCY HOSPITALS
        ================================================= */}

        {mode === "emergency" &&
          route?.hospitals?.map(
            (h, i) => (

              <Marker
                key={i}
                position={h.coords}
                icon={MARKERS.hospital}
              >

                <Popup>
                  🏥 {h.name} —{" "}
                  {h.distance_km} km
                </Popup>

              </Marker>
            )
          )}


        {/* =================================================
            SELECTED EMERGENCY DESTINATION
        ================================================= */}

        {mode === "emergency" &&
          route?.destination && (

            <Marker
              position={route.destination}
              icon={MARKERS.hospital}
            >

              <Popup>
                🏥{" "}
                {route.nearest_hospital} —{" "}
                {route.distance_km} km
              </Popup>

            </Marker>
          )}


        {/* =================================================
            DELIVERY STOPS
        ================================================= */}

        {mode === "delivery" &&
          route?.stops?.map(
            (stop, i) => (

              <Marker
                key={i}
                position={stop.coords}
                icon={MARKERS.stop(
                  i,
                  color
                )}
              >

                <Popup>
                  Stop {i + 1}:{" "}
                  {stop.name}
                </Popup>

              </Marker>
            )
          )}

      </MapContainer>


      {/* =================================================
          NAVIGATION OVERLAY
      ================================================= */}

      <NavigationOverlay
        route={route}
        mode={mode}
        gpsLocation={gpsLocation}
      />

    </div>
  );
}