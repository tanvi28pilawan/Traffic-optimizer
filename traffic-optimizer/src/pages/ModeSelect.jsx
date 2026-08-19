import { useNavigate } from "react-router-dom";

const MODES = [
  {
    id: "normal",
    tag: "Normal",
    title: "Shortest Path",
    desc: "Find the most efficient route between any two points on the map.",
    features: ["Dijkstra / A* algorithm", "Distance or time weight", "Real-time road graph"],
    color: "#10B981",
    bg: "rgba(16,185,129,0.12)",
    icon: "🗺",
    btn: "Enter Normal Mode →",
  },
  {
    id: "emergency",
    tag: "Emergency",
    title: "Critical Response",
    desc: "Fastest path to the nearest hospital with priority lane routing.",
    features: ["Hospital proximity search", "Priority lane routing", "Modified A* + POI layer"],
    color: "#EF4444",
    bg: "rgba(239,68,68,0.12)",
    icon: "🚑",
    btn: "Enter Emergency Mode →",
  },
  {
    id: "delivery",
    tag: "Delivery",
    title: "Multi-Stop Route",
    desc: "Optimized sequence routing across multiple delivery waypoints.",
    features: ["Nearest-neighbor TSP", "2-opt optimization", "Multiple waypoints"],
    color: "#3B82F6",
    bg: "rgba(59,130,246,0.12)",
    icon: "📦",
    btn: "Enter Delivery Mode →",
  },
];

export default function ModeSelect() {
  const navigate = useNavigate();

  const handleSelect = (modeId) => {
    navigate(`/app/${modeId}`);
  };

  
  <button className="logout-btn" onClick={() => navigate("/history")}>
  History
</button>
  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <div className="mode-page">
      <nav className="mode-nav">
        <div className="nav-logo">
          <div className="nav-icon">T</div>
          <span className="nav-name">TrafficOpt</span>
        </div>
       <div className="nav-right">
  <span className="nav-user">{localStorage.getItem("userName") || "User"}</span>
  <button className="logout-btn" onClick={() => navigate("/profile")}>
    Profile
  </button>
  <button className="logout-btn" onClick={() => navigate("/history")}>
    History
  </button>
  <button className="logout-btn" onClick={handleLogout}>Logout</button>
</div>
      </nav>

      <div className="mode-body">
        <div className="mode-heading">
          <p className="mode-label">Routing System</p>
          <h1 className="mode-title">Choose your routing mode</h1>
          <p className="mode-sub">Select a mode below to begin optimizing your route</p>
        </div>

        <div className="mode-cards">
          {MODES.map((m) => (
            <div key={m.id} className="mcard" style={{ "--mc": m.color, "--mbg": m.bg }}>
              <div className="mcard-bar" />
              <div className="mcard-icon-wrap">
                <span className="mcard-icon">{m.icon}</span>
              </div>
              <p className="mcard-tag">{m.tag}</p>
              <h2 className="mcard-title">{m.title}</h2>
              <p className="mcard-desc">{m.desc}</p>
              <ul className="mcard-features">
                {m.features.map((f) => (
                  <li key={f} className="mcard-feat">
                    <span className="mcard-dot" />
                    {f}
                  </li>
                ))}
              </ul>
              <button className="mcard-btn" onClick={() => handleSelect(m.id)}>
                {m.btn}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}