import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import TrafficLogo from "../components/TrafficLogo.jsx";

export default function ForgotPassword() {
  const [step, setStep] = useState(1); // 1: email, 2: otp + new password
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const navigate = useNavigate();

  const handleSendOTP = async () => {
    if (!email) { setError("Please enter your email."); return; }
    setLoading(true);
    setError(null);
    try {
      await axios.post("${import.meta.env.VITE_API_URL}/auth/forgot-password", { email });
      setSuccess("OTP sent to your email!");
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || "Email not found.");
    }
    setLoading(false);
  };

  const handleResetPassword = async () => {
    if (!otp || !newPassword || !confirm) { setError("Please fill all fields."); return; }
    if (newPassword !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    setError(null);
    try {
      await axios.post("${import.meta.env.VITE_API_URL}/auth/verify-otp", {
        email, otp, new_password: newPassword
      });
      setSuccess("Password reset successful!");
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid OTP.");
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
          <h2 className="form-title">
            {step === 1 ? "Forgot Password" : "Reset Password"}
          </h2>
          <p className="form-sub">
            {step === 1
              ? "Enter your email to receive an OTP"
              : `OTP sent to ${email}`}
          </p>

          {step === 1 ? (
            <div className="field">
              <label className="field-label">Email</label>
              <input
                className="field-input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          ) : (
            <>
              <div className="field">
                <label className="field-label">OTP</label>
                <input
                  className="field-input"
                  type="text"
                  placeholder="Enter 6-digit OTP"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  maxLength={6}
                />
              </div>
              <div className="field">
                <label className="field-label">New Password</label>
                <input
                  className="field-input"
                  type="password"
                  placeholder="New password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div className="field">
                <label className="field-label">Confirm Password</label>
                <input
                  className="field-input"
                  type="password"
                  placeholder="Confirm new password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </div>
            </>
          )}

          {error && <div className="auth-error">{error}</div>}
          {success && (
            <div style={{
              fontSize: "12px", color: "#10B981",
              background: "rgba(16,185,129,0.1)",
              border: "1px solid rgba(16,185,129,0.2)",
              padding: "8px 12px", borderRadius: "6px"
            }}>{success}</div>
          )}

          <button
            className="auth-btn"
            onClick={step === 1 ? handleSendOTP : handleResetPassword}
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : step === 1
              ? "Send OTP →"
              : "Reset Password →"}
          </button>

          {step === 2 && (
            <button
              style={{
                background: "none", border: "none",
                color: "#64748B", fontSize: "13px",
                cursor: "pointer", textAlign: "center"
              }}
              onClick={() => { setStep(1); setError(null); setSuccess(null); }}
            >
              ← Back to email
            </button>
          )}

          <p className="auth-switch">
            Remember password?{" "}
            <Link to="/login" className="auth-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}