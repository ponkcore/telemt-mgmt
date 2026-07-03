// Main app with React Router routes (login, dashboard, users, links).
// Auth guard: redirects to /login if not authenticated.
// AC5: 401 API responses redirect to login (handled in api/client.ts interceptor).
// AC6: dark theme with sidebar navigation (Layout + Sidebar components).

import { type ReactNode, useEffect } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import { api } from "./api/client";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Links } from "./pages/Links";
import { Login } from "./pages/Login";
import { Users } from "./pages/Users";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (!api.isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Layout>{children}</Layout>;
}

function AppRoutes() {
  // AC5: check auth on route change — if token removed (e.g. by 401 interceptor),
  // redirect to login.
  const location = useLocation();
  useEffect(() => {
    if (location.pathname !== "/login" && !api.isAuthenticated()) {
      window.location.href = "/login";
    }
  }, [location.pathname]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute>
            <Users />
          </ProtectedRoute>
        }
      />
      <Route
        path="/links"
        element={
          <ProtectedRoute>
            <Links />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
