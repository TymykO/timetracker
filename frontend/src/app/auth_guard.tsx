/**
 * AuthGuard - komponent chroniący prywatne trasy.
 * 
 * Sprawdza sesję przez API call do /api/me.
 * Przekierowuje na /login jeśli nie zalogowany.
 */

import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { api } from "./api_client";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.me(),
    retry: false, // nie retry na 401 (i tak przekieruje)
  });

  if (isLoading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        Ładowanie...
      </div>
    );
  }

  if (error || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_active) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h2>Konto nieaktywne</h2>
        <p>Skontaktuj się z administratorem.</p>
      </div>
    );
  }

  return <>{children}</>;
}
