/**
 * Router dla TimeTracker SPA.
 * 
 * Trasy:
 * - Publiczne: /login, /set-password, /forgot-password, /reset-password
 * - Chronione: /month/:yearMonth, /day/:date
 */

import { Routes, Route, Navigate } from "react-router-dom";
import { AuthGuard } from "./auth_guard";

// Page imports
import LoginPage from "../pages/Login/LoginPage";
import SetPasswordPage from "../pages/SetPassword/SetPasswordPage";
import ForgotPasswordPage from "../pages/ForgotPassword/ForgotPasswordPage";
import ResetPasswordPage from "../pages/ResetPassword/ResetPasswordPage";
import MonthPage from "../pages/Month/MonthPage";
import DayPage from "../pages/Day/DayPage";

export function AppRouter() {
  // Default redirect do obecnego miesiąca
  const now = new Date();
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  return (
    <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/set-password" element={<SetPasswordPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Protected routes */}
        <Route
          path="/month/:yearMonth"
          element={
            <AuthGuard>
              <MonthPage />
            </AuthGuard>
          }
        />
        <Route
          path="/day/:date"
          element={
            <AuthGuard>
              <DayPage />
            </AuthGuard>
          }
        />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to={`/month/${currentMonth}`} replace />} />
        <Route path="*" element={<Navigate to={`/month/${currentMonth}`} replace />} />
      </Routes>
  );
}
