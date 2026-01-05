import React from "react";
import { Navigate } from "react-router-dom";
import { useStore } from "../../store/useStore";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useStore((state) => state.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}
