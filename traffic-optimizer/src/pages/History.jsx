import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import TrafficLogo from "../components/TrafficLogo.jsx";

const MODE_CONFIG = {
  normal: { color: "#10B981", icon: "🗺", label: "Normal" },
  emergency: { color: "#EF4444", icon: "🚑", label: "Emergency" },
  delivery: { color: "#3B82F6", icon: "📦", label: "Delivery" },
};

export default function History() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/route/history`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setRoutes(res.data);
      } catch (err) {
        console.error("Failed to fetch history");
      }
      setLoading(false);
    };
    fetchHistory();
  }, []);

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="history-page">
      <nav className="mode-nav">
        <div className="nav-logo">
          <TrafficLogo compact />
        </div>

        <div className="nav-right">
          <button
            className="logout-btn"
            onClick={() => navigate("/select")}
          >
            ← Back
          </button>

          <button
            className="logout-btn"
            onClick={() => {
              localStorage.removeItem("token");
              navigate("/login");
            }}
          >
            Logout
          </button>
        </div>
      </nav>

      <div className="history-body">
        <div className="history-heading">
          <p className="mode-label">Your Routes</p>
          <h1 className="mode-title">Route History</h1>
          <p className="mode-sub">
            All your previously searched routes
          </p>
        </div>

        {loading ? (
          <div className="history-loading">
            Loading history...
          </div>
        ) : routes.length === 0 ? (
          <div className="history-empty">
            <p>No routes found yet!</p>

            <button
              className="auth-btn"
              onClick={() => navigate("/select")}
            >
              Find a Route →
            </button>
          </div>
        ) : (
          <div className="history-list">
            {routes.map((route, i) => {
              const config =
                MODE_CONFIG[route.mode] || MODE_CONFIG.normal;

              return (
                <div
                  key={i}
                  className="history-card"
                  style={{ "--mc": config.color }}
                >
                  <div className="history-card-left">
                    <div className="history-icon">
                      {config.icon}
                    </div>
                  </div>

                  <div className="history-card-body">
                    <div className="history-card-top">
                      <span
                        className="history-mode-tag"
                        style={{ color: config.color }}
                      >
                        {config.label} Mode
                      </span>

                      <span className="history-date">
                        {formatDate(route.created_at)}
                      </span>
                    </div>

                    <p className="history-source">
                      From: <strong>{route.source}</strong>
                    </p>

                    {route.destination && (
                      <p className="history-dest">
                        To: <strong>{route.destination}</strong>
                      </p>
                    )}
                  </div>

                  <div className="history-card-bar" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}