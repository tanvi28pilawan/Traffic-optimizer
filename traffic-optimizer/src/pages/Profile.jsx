import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const MODE_CONFIG = {
  normal: { color: "#10B981", icon: "🗺", label: "Normal" },
  emergency: { color: "#EF4444", icon: "🚑", label: "Emergency" },
  delivery: { color: "#3B82F6", icon: "📦", label: "Delivery" },
  None: { color: "#475569", icon: "—", label: "None" },
};

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await axios.get("http://localhost:8000/auth/profile", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setProfile(res.data);
        setNewName(res.data.name);
      } catch (err) {
        console.error("Failed to fetch profile");
      }
      setLoading(false);
    };
    fetchProfile();
  }, []);

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-IN", {
      day: "numeric", month: "long", year: "numeric"
    });
  };

  const getInitials = (name) => {
    return name?.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) || "U";
  };

  const handleSaveName = async () => {
  if (!newName.trim()) return;

  try {
    const token = localStorage.getItem("token");
    await axios.put(
      "http://localhost:8000/auth/profile/name",
      { name: newName.trim() },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    setProfile((prev) => ({ ...prev, name: newName.trim() }));
    localStorage.setItem("userName", newName.trim());
    setEditing(false);
  } catch (err) {
    console.error("Failed to update name", err);
  }
};

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    navigate("/login");
  };

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh", background: "#0F172A",
        display: "flex", flexDirection: "column",width:"100vw",
        alignItems: "center", justifyContent: "center",
        gap: "16px", color: "#64748B"
      }}>
        <div className="profile-spinner"></div>
        <p>Loading profile...</p>
      </div>
    );
  }

  const modeConfig = MODE_CONFIG[profile?.favourite_mode] || MODE_CONFIG.None;

  return (
    <div style={{ minHeight: "100vh", background: "#0F172A", display: "flex", flexDirection: "column", width: "100%" }}>

      <nav className="mode-nav">
        <div className="nav-logo">
          <div className="nav-icon">T</div>
          <span className="nav-name">TrafficOpt</span>
        </div>
        <div className="nav-right">
          <button className="logout-btn" onClick={() => navigate("/select")}>← Back</button>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </nav>

      <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
        {[...Array(20)].map((_, i) => (
          <div key={i} style={{
            position: "absolute",
            width: `${Math.random() * 6 + 2}px`,
            height: `${Math.random() * 6 + 2}px`,
            background: i % 3 === 0 ? "#10B981" : i % 3 === 1 ? "#3B82F6" : "#EF4444",
            borderRadius: "50%",
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            opacity: 0.15,
            animation: `float ${3 + Math.random() * 4}s ease-in-out infinite alternate`,
            animationDelay: `${Math.random() * 2}s`,
          }} />
        ))}
      </div>

      <div style={{
        flex: 1, maxWidth: "680px", width: "100%",
        margin: "0 auto", padding: "40px 24px",
        display: "flex", flexDirection: "column", gap: "20px",
        position: "relative", zIndex: 1
      }}>

        <div style={{
          background: "linear-gradient(135deg, #1E293B 0%, #0F172A 100%)",
          border: "1px solid #334155", borderRadius: "20px",
          padding: "32px", display: "flex", alignItems: "center",
          gap: "24px", position: "relative", overflow: "hidden"
        }}>
          <div style={{
            position: "absolute", top: "-40px", right: "-40px",
            width: "200px", height: "200px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(16,185,129,0.15) 0%, transparent 70%)",
            pointerEvents: "none"
          }} />

          <div style={{
            width: "80px", height: "80px", borderRadius: "50%",
            background: "linear-gradient(135deg, #10B981, #3B82F6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "28px", fontWeight: "700", color: "white",
            flexShrink: 0, boxShadow: "0 8px 24px rgba(16,185,129,0.4)",
            animation: "avatarPulse 3s ease-in-out infinite"
          }}>
            {getInitials(profile?.name)}
          </div>

          <div style={{ flex: 1 }}>
            {editing ? (
              <div style={{ display: "flex", gap: "8px", marginBottom: "4px" }}>
                <input
                  className="profile-name-input"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  autoFocus
                />
                <button className="profile-save-btn" onClick={handleSaveName}>
                  Save
                </button>
                <button className="profile-cancel-btn" onClick={() => setEditing(false)}>
                  Cancel
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                <h1 style={{ fontSize: "24px", fontWeight: "600", color: "#F8FAFC" }}>
                  {profile?.name}
                </h1>
                <button className="profile-edit-btn" onClick={() => setEditing(true)}>✏️</button>
              </div>
            )}
            <p style={{ fontSize: "14px", color: "#64748B", marginBottom: "4px" }}>{profile?.email}</p>
            <p style={{ fontSize: "12px", color: "#475569" }}>
              🗓 Member since {formatDate(profile?.created_at)}
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
          {[
            { number: profile?.total_routes, label: "Total Routes", color: "#10B981" },
            { number: modeConfig.icon, label: "Fav Mode", sub: modeConfig.label, color: modeConfig.color },
            { number: profile?.recent_routes?.length || 0, label: "Recent", color: "#3B82F6" },
          ].map((stat, i) => (
            <div key={i}
              style={{
                background: "#1E293B", border: "1px solid #334155",
                borderTop: `3px solid ${stat.color}`,
                borderRadius: "14px", padding: "20px",
                textAlign: "center", display: "flex",
                flexDirection: "column", alignItems: "center", gap: "6px",
                transition: "transform 0.2s", cursor: "default",
              }}
              onMouseEnter={e => e.currentTarget.style.transform = "translateY(-4px)"}
              onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}
            >
              <p style={{ fontSize: "32px", fontWeight: "700", color: stat.color }}>
                {stat.number}
              </p>
              {stat.sub && <p style={{ fontSize: "13px", color: "#F8FAFC", fontWeight: "500" }}>{stat.sub}</p>}
              <p style={{ fontSize: "11px", color: "#64748B", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {stat.label}
              </p>
            </div>
          ))}
        </div>

        <div>
          <p style={{
            fontSize: "11px", fontWeight: "600", letterSpacing: "0.1em",
            textTransform: "uppercase", color: "#475569", marginBottom: "12px"
          }}>
            Recent Routes
          </p>

          {profile?.recent_routes?.length === 0 ? (
            <div style={{
              textAlign: "center", color: "#64748B", fontSize: "14px",
              padding: "32px", background: "#1E293B", borderRadius: "14px",
              border: "1px solid #334155"
            }}>
              <p style={{ marginBottom: "16px" }}>No routes yet!</p>
              <button className="auth-btn" onClick={() => navigate("/select")}>
                Find a Route →
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {profile?.recent_routes?.map((route, i) => {
                const config = MODE_CONFIG[route.mode] || MODE_CONFIG.normal;
                return (
                  <div key={i} style={{
                    background: "#1E293B",
                    border: "1px solid #334155",
                    borderLeft: `3px solid ${config.color}`,
                    borderRadius: "12px", padding: "16px 20px",
                    display: "flex", alignItems: "center", gap: "14px",
                    transition: "transform 0.15s",
                    cursor: "default"
                  }}
                    onMouseEnter={e => e.currentTarget.style.transform = "translateX(6px)"}
                    onMouseLeave={e => e.currentTarget.style.transform = "translateX(0)"}
                  >
                    <span style={{ fontSize: "24px" }}>{config.icon}</span>
                    <div style={{ flex: 1 }}>
                      <span style={{
                        fontSize: "10px", fontWeight: "600",
                        letterSpacing: "0.1em", textTransform: "uppercase",
                        color: config.color
                      }}>
                        {config.label} Mode
                      </span>
                      <p style={{ fontSize: "13px", color: "#94A3B8", marginTop: "3px" }}>
                        From: <strong style={{ color: "#F8FAFC" }}>{route.source}</strong>
                      </p>
                      {route.destination && (
                        <p style={{ fontSize: "13px", color: "#94A3B8" }}>
                          To: <strong style={{ color: "#F8FAFC" }}>{route.destination}</strong>
                        </p>
                      )}
                      <p style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
                        {formatDate(route.created_at)}
                      </p>
                    </div>
                    <span style={{ fontSize: "18px", color: "#334155" }}>→</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {[
            { icon: "📋", label: "View Full History", onClick: () => navigate("/history"), color: "#3B82F6" },
            { icon: "🗺", label: "Find New Route", onClick: () => navigate("/select"), color: "#10B981" },
            { icon: "🚪", label: "Logout", onClick: handleLogout, color: "#EF4444", danger: true },
          ].map((btn, i) => (
            <button key={i} onClick={btn.onClick} style={{
              padding: "16px 20px",
              background: btn.danger ? "rgba(239,68,68,0.05)" : "#1E293B",
              border: `1px solid ${btn.danger ? "rgba(239,68,68,0.2)" : "#334155"}`,
              borderRadius: "12px",
              color: btn.danger ? "#EF4444" : "#F8FAFC",
              fontSize: "14px", fontWeight: "500",
              cursor: "pointer", textAlign: "left",
              display: "flex", alignItems: "center", gap: "12px",
              transition: "transform 0.15s, border-color 0.15s",
            }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = "translateX(6px)";
                e.currentTarget.style.borderColor = btn.color;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = "translateX(0)";
                e.currentTarget.style.borderColor = btn.danger ? "rgba(239,68,68,0.2)" : "#334155";
              }}
            >
              <span style={{
                width: "36px", height: "36px", borderRadius: "8px",
                background: `${btn.color}22`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "18px", flexShrink: 0
              }}>{btn.icon}</span>
              {btn.label}
              <span style={{ marginLeft: "auto", color: "#475569" }}>→</span>
            </button>
          ))}
        </div>

      </div>

      <style>{`
        @keyframes float {
          from { transform: translateY(0px); }
          to { transform: translateY(-20px); }
        }
        @keyframes avatarPulse {
          0%, 100% { box-shadow: 0 8px 24px rgba(16,185,129,0.4); }
          50% { box-shadow: 0 8px 32px rgba(16,185,129,0.7); }
        }
        .profile-name-input {
          background: #0F172A;
          border: 1px solid #10B981;
          border-radius: 6px;
          color: #F8FAFC;
          font-size: 18px;
          padding: 6px 10px;
          outline: none;
          flex: 1;
        }
        .profile-save-btn {
          padding: 6px 14px;
          background: #10B981;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .profile-cancel-btn {
          padding: 6px 14px;
          background: none;
          color: #64748B;
          border: 1px solid #334155;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
        }
        .profile-edit-btn {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 16px;
          padding: 4px;
          border-radius: 4px;
          transition: transform 0.15s;
        }
        .profile-edit-btn:hover { transform: scale(1.2); }
        .profile-spinner {
          width: 36px; height: 36px;
          border: 3px solid #334155;
          border-top-color: #10B981;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}