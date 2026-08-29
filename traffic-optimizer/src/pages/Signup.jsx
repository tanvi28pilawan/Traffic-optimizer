import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import TrafficLogo from "../components/TrafficLogo.jsx";

export default function Signup() {
  const [form, setForm] = useState({
  name: "", email: "", password: "", confirm: "", role: "normal"
});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.password) {
      setError("Please fill all fields.");
      return;
    }
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/auth/signup`, {
  name: form.name,
  email: form.email,
  password: form.password,
  role: form.role,
});
      navigate("/login");
    } catch (err) {
      setError(err.response?.data?.detail || "Signup failed. Try again.");
    }
    setLoading(false);
  };

  return (
   <div className="auth-page">
  <div className="auth-card">
    <div className="auth-brand">
      <TrafficLogo />
      <p className="brand-sub">Intelligent Routing System</p>
    </div>

        <div className="auth-form">
          <h2 className="form-title">Create account</h2>
          <p className="form-sub">Start optimizing your routes today</p>

          <div className="field">
  <label className="field-label">Full Name</label>
  <input
    className="field-input"
    type="text"
    name="name"
    placeholder="Your name"
    value={form.name}
    onChange={handleChange}
  />
</div>

<div className="field">
  <label className="field-label">I am a</label>
  <select
    className="field-input"
    name="role"
    value={form.role}
    onChange={handleChange}
    style={{ cursor: "pointer" }}
  >
    <option value="normal">Normal User</option>
    <option value="emergency">Emergency Driver 🚑</option>
    <option value="delivery">Delivery Rider 📦</option>
  </select>
</div>

          <div className="field">
            <label className="field-label">Email</label>
            <input
              className="field-input"
              type="email"
              name="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
            />
          </div>

          <div className="field">
            <label className="field-label">Password</label>
            <input
              className="field-input"
              type="password"
              name="password"
              placeholder="Min 8 characters"
              value={form.password}
              onChange={handleChange}
            />
          </div>

          <div className="field">
            <label className="field-label">Confirm Password</label>
            <input
              className="field-input"
              type="password"
              name="confirm"
              placeholder="Re-enter password"
              value={form.confirm}
              onChange={handleChange}
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button
            className="auth-btn"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? "Creating account..." : "Create Account →"}
          </button>

          <p className="auth-switch">
            Already have an account?{" "}
            <Link to="/login" className="auth-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}