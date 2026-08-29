import { useState } from "react";
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

export default function ModeSelector({ mode, route, setRoute }) {
  const [city, setCity] = useState("Chhatrapati Sambhajinagar, Maharashtra, India");
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [stops, setStops] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [hospitals, setHospitals] = useState([]);
  const [selectedHospital, setSelectedHospital] = useState(null);
  const [routeLoading, setRouteLoading] = useState(false);

  const config = MODE_CONFIG[mode] || MODE_CONFIG.normal;

  const handleFindRoute = async () => {
    if (!source) {
      setError("Please enter source location.");
      return;
    }
    if (mode === "normal" && !destination) {
      setError("Please enter destination.");
      return;
    }

    setLoading(true);
    setError(null);
    setInfo(null);
    setHospitals([]);
    setSelectedHospital(null);

    try {
      const token = localStorage.getItem("token");
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/route/${mode}`,
        {
          mode,
          source,
          city:city,
          destination: mode !== "delivery" ? destination : null,
          stops: mode === "delivery" ? stops.split("\n").filter(s => s.trim()) : null,
        },
        { headers: { Authorization: `Bearer ${token}` } }
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
    }

    setLoading(false);
  };

  const handleHospitalSelect = async (hospital) => {
    setSelectedHospital(hospital.name);
    setRouteLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem("token");
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/route/emergency/select`,
        {
          source,
          city: city,
          hospital_lat: hospital.coords[0],
          hospital_lon: hospital.coords[1],
          hospital_name: hospital.name,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setRoute(res.data);
      setInfo(`Route to ${hospital.name} | ${res.data.distance_km} km`);
    } catch (err) {
      setError("Could not get route to this hospital.");
    }

    setRouteLoading(false);
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
  <label className="sidebar-label">City</label>
  <select
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
            <label className="sidebar-label">Delivery Stops</label>
            <textarea
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
                className={`hospital-item ${selectedHospital === h.name ? "selected" : ""}`}
                onClick={() => handleHospitalSelect(h)}
                disabled={routeLoading}
              >
                <span className="hospital-rank">{i + 1}</span>
                <span className="hospital-name">{h.name}</span>
                {h.distance_km && (
                  <span className="hospital-dist">{h.distance_km} km</span>
                )}
                {selectedHospital === h.name && (
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
            <p className="info-text">Dijkstra algorithm finds the shortest path.</p>
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