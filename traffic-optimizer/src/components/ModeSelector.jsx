import { useState, useEffect, useRef } from "react";
import axios from "axios";
import LocationInput from "../components/LocationInput";

const MODE_CONFIG = {
  normal: {
    color: "#10B981",
    label: "Normal Mode",
    icon: "🗺",
    desc: "Find shortest path between two points",
  },
  emergency: {
    color: "#EF4444",
    label: "Emergency Mode",
    icon: "🚑",
    desc: "Fastest route with nearby hospitals",
  },
  delivery: {
    color: "#3B82F6",
    label: "Delivery Mode",
    icon: "📦",
    desc: "Optimized multi-stop delivery route",
  },
};

// Small icon per instruction type, purely cosmetic
const TURN_ICON = {
  "Turn left": "⬅",
  "Turn right": "➡",
  "Make a U-turn": "↩",
  "Start your journey": "🏁",
  "You have arrived at your destination!": "🏁",
};

function formatStepDistance(m) {
  if (!m) return "";
  if (m < 1000) return `${m} m`;
  return `${(m / 1000).toFixed(1)} km`;
}

// Small helper so we don't repeat this in every handler
function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return { Authorization: `Bearer ${token}` };
}

export default function ModeSelector({ mode, route, setRoute }) {
  const [city, setCity] = useState("Chhatrapati Sambhajinagar, Maharashtra, India");
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [stops, setStops] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [hospitals, setHospitals] = useState([]);
  const [selectedHospitalIndex, setSelectedHospitalIndex] = useState(null);
  const [routeLoading, setRouteLoading] = useState(false);

  const config = MODE_CONFIG[mode] || MODE_CONFIG.normal;

  // Keep track of the previous mode so we only reset on an actual mode change,
  // not on every render.
  const prevModeRef = useRef(mode);

  useEffect(() => {
    if (prevModeRef.current !== mode) {
      // Reset everything tied to the previous mode's flow so stale
      // directions/hospitals/errors from another mode don't linger.
      setRoute(null);
      setError(null);
      setInfo(null);
      setHospitals([]);
      setSelectedHospitalIndex(null);
      setRouteLoading(false);
      setDestination("");
      setStops("");
      // Deliberately NOT resetting `source` or `city` — those are usually
      // still valid/useful across mode switches. Remove if you'd rather
      // clear everything.
      prevModeRef.current = mode;
    }
  }, [mode, setRoute]);

  const handleFindRoute = async () => {
    if (!source) {
      setError("Please enter source location.");
      return;
    }
    if (mode === "normal" && !destination) {
      setError("Please enter destination.");
      return;
    }
    if (mode === "delivery" && !stops.trim()) {
      setError("Please enter at least one delivery stop.");
      return;
    }

    setLoading(true);
    setError(null);
    setInfo(null);
    setHospitals([]);
    setSelectedHospitalIndex(null);

    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/route/${mode}`,
        {
          mode,
          source,
          city: city,
          destination: mode !== "delivery" ? destination : null,
          stops:
            mode === "delivery"
              ? stops.split("\n").map((s) => s.trim()).filter(Boolean)
              : null,
        },
        { headers: getAuthHeaders() }
      );

      setRoute(res.data);

      if (mode === "emergency") {
        setHospitals(res.data.hospitals || []);
        setInfo(`Nearest: ${res.data.nearest_hospital} | ${res.data.distance_km} km`);
      } else {
        setInfo(`Route found! Distance: ${res.data.distance_km} km`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Could not find route. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleHospitalSelect = async (hospital, index) => {
    setSelectedHospitalIndex(index);
    setRouteLoading(true);
    setError(null);

    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/route/emergency/select`,
        {
          source,
          city: city,
          hospital_lat: hospital.coords[0],
          hospital_lon: hospital.coords[1],
          hospital_name: hospital.name,
        },
        { headers: getAuthHeaders() }
      );

      setRoute(res.data);
      setInfo(`Route to ${hospital.name} | ${res.data.distance_km} km`);
    } catch (err) {
      setError("Could not get route to this hospital.");
    } finally {
      setRouteLoading(false);
    }
  };

  return (
    <div className="sidebar-inner">
      <div className="mode-badge" style={{ "--mc": config.color }}>
        <span className="mode-badge-icon">{config.icon}</span>
        <div>
          <p className="mode-badge-label">{config.label}</p>
          <p className="mode-badge-desc">{config.desc}</p>
        </div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-section-title">Route Details</p>

        <div className="sidebar-field">
          <label className="sidebar-label" htmlFor="city-select">City</label>
          <select
            id="city-select"
            className="sidebar-input"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          >
            <option value="Chhatrapati Sambhajinagar, Maharashtra, India">Chhatrapati Sambhajinagar</option>
            <option value="Pune, Maharashtra, India">Pune</option>
            <option value="Nagpur, Maharashtra, India">Nagpur</option>
            <option value="Bangalore, Karnataka, India">Bangalore</option>
          </select>
        </div>

        <LocationInput
          label="Source"
          placeholder="Enter starting point"
          value={source}
          onChange={setSource}
          city={city}
        />

        {mode === "delivery" ? (
          <div className="sidebar-field">
            <label className="sidebar-label" htmlFor="delivery-stops">Delivery Stops</label>
            <textarea
              id="delivery-stops"
              className="sidebar-input sidebar-textarea"
              placeholder={"Stop 1\nStop 2\nStop 3"}
              value={stops}
              onChange={(e) => setStops(e.target.value)}
            />
          </div>
        ) : mode === "normal" ? (
          <LocationInput
            label="Destination"
            placeholder="Enter destination"
            value={destination}
            onChange={setDestination}
            city={city}
          />
        ) : null}

        {error && <p className="sidebar-error">{error}</p>}
        {info && <p className="sidebar-info-msg">{info}</p>}

        <button
          className="sidebar-btn"
          style={{ "--mc": config.color }}
          onClick={handleFindRoute}
          disabled={loading}
        >
          {loading ? "Finding route..." : "Find Route →"}
        </button>
      </div>

      {mode === "emergency" && hospitals.length > 0 && (
        <div className="sidebar-section">
          <p className="sidebar-section-title">Nearby Hospitals</p>
          <div className="hospital-list">
            {hospitals.map((h, i) => (
              <button
                key={i}
                className={`hospital-item ${selectedHospitalIndex === i ? "selected" : ""}`}
                onClick={() => handleHospitalSelect(h, i)}
                disabled={routeLoading}
              >
                <span className="hospital-rank">{i + 1}</span>
                <span className="hospital-name">{h.name}</span>
                {h.distance_km && (
                  <span className="hospital-dist">{h.distance_km} km</span>
                )}
                {selectedHospitalIndex === i && (
                  <span className="hospital-check">✓</span>
                )}
              </button>
            ))}
          </div>
          {routeLoading && <p className="sidebar-info-msg">Getting route...</p>}
        </div>
      )}

      {route?.directions && route.directions.length > 0 && (
        <div className="sidebar-section">
          <p className="sidebar-section-title">Directions</p>
          <div className="directions-list">
            {route.directions.map((d) => (
              <div key={d.step} className="direction-item">
                <span className="direction-icon">
                  {TURN_ICON[d.instruction] || "•"}
                </span>
                <div className="direction-text">
                  <p className="direction-instruction">{d.instruction}</p>
                  {d.distance_m > 0 && (
                    <p className="direction-distance">
                      {formatStepDistance(d.distance_m)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="sidebar-info" style={{ "--mc": config.color }}>
        {mode === "normal" && (
          <>
            <p className="info-title">How it works</p>
            <p className="info-text">A* algorithm finds the shortest path efficiently.</p>
          </>
        )}
        {mode === "emergency" && (
          <>
            <p className="info-title">Emergency routing</p>
            <p className="info-text">Shows nearest hospitals — click any to get route.</p>
          </>
        )}
        {mode === "delivery" && (
          <>
            <p className="info-title">Delivery optimization</p>
            <p className="info-text">TSP algorithm finds the most efficient stop sequence.</p>
          </>
        )}
      </div>
    </div>
  );
}