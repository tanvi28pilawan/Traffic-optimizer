import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ModeSelect from "./pages/ModeSelect";
import History from "./pages/History";
import App from "./App";
import Profile from "./pages/Profile";
import ForgotPassword from "./pages/ForgotPassword";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" />;
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/select" element={
          <PrivateRoute><ModeSelect /></PrivateRoute>
        } />
        <Route path="/history" element={
          <PrivateRoute><History /></PrivateRoute>
        } />
        <Route path="/profile" element={
          <PrivateRoute><Profile /></PrivateRoute>
        } />
        <Route path="/app/:mode" element={
          <PrivateRoute><App /></PrivateRoute>
        } />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  );
}