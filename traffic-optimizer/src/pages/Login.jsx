import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import TrafficLogo from "../components/TrafficLogo.jsx";

export default function Login() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async () => {
    if (!form.email || !form.password) {
      setError("Please enter email and password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await axios.post(
        "http://localhost:8000/auth/login",
        form
      );

      localStorage.setItem("token", res.data.token);
      localStorage.setItem("userName", res.data.name);
      localStorage.setItem("userRole", res.data.role);

      if (res.data.role === "emergency") {
        navigate("/app/emergency");
      } else if (res.data.role === "delivery") {
        navigate("/app/delivery");
      } else {
        navigate("/select");
      }
    } catch (err) {
      const detail = err.response?.data?.detail;

      if (Array.isArray(detail)) {
        setError("Invalid email or password.");
      } else {
        setError(detail || "Login failed. Check credentials.");
      }
    }

    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        {/* TrafficOpt Branding */}
        <div className="auth-brand">
          <TrafficLogo />
          <p className="brand-sub">
            Intelligent Routing System
          </p>
        </div>

        {/* Login Form */}
        <div className="auth-form">
          <h2 className="form-title">Welcome back</h2>

          <p className="form-sub">
            Sign in to your account
          </p>

          {/* Email */}
          <div className="field">
            <label className="field-label">
              Email
            </label>

            <input
              className="field-input"
              type="email"
              name="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
            />
          </div>

          {/* Password */}
          <div className="field">
            <label className="field-label">
              Password
            </label>

            <input
              className="field-input"
              type="password"
              name="password"
              placeholder="••••••••"
              value={form.password}
              onChange={handleChange}
            />
          </div>

          {/* Forgot Password */}
          <div style={{ textAlign: "right" }}>
            <Link
              to="/forgot-password"
              className="auth-link"
              style={{ fontSize: "12px" }}
            >
              Forgot password?
            </Link>
          </div>

          {/* Error */}
          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          {/* Sign In Button */}
          <button
            className="auth-btn"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In →"}
          </button>

          {/* Signup */}
          <p className="auth-switch">
            Don't have an account?{" "}
            <Link
              to="/signup"
              className="auth-link"
            >
              Create one
            </Link>
          </p>
        </div>

      </div>
    </div>
  );
}