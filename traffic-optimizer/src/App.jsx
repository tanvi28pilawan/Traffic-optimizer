import { useParams, useNavigate } from "react-router-dom";
import ModeSelector from "./components/ModeSelector";
import MapView from "./components/MapView";
import { useState } from "react";

export default function App() {
  const { mode } = useParams();
  const navigate = useNavigate();
  const [route, setRoute] = useState(null);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div className="header-icon">T</div>
          <span className="logo">TrafficOpt</span>
          <span className="tagline">Intelligent Routing System</span>
        </div>
        <div className="header-right">
          <button className="back-btn" onClick={() => navigate("/select")}>
            ← Change Mode
          </button>
          <button className="logout-btn-header" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <div className="main-layout">
        <aside className="sidebar">
          <ModeSelector mode={mode} route={route} setRoute={setRoute} />
        </aside>
        <main className="map-area">
          <MapView mode={mode} route={route} />
        </main>
      </div>
    </div>
  );
}