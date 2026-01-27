/**
 * AuthGuard - komponent chroniący prywatne trasy.
 * 
 * Sprawdza sesję przez API call do /api/me.
 * Przekierowuje na /login jeśli nie zalogowany.
 */

import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { Alert, AlertTitle, Card, CardContent } from "@mui/material";
import { api } from "./api_client";
import { LoadingState } from "../components/LoadingState";

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
    return <LoadingState message="Sprawdzanie sesji..." />;
  }

  if (error || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_active) {
    return (
      <Card sx={{ maxWidth: 600, mx: "auto", mt: 4 }}>
        <CardContent>
          <Alert severity="warning">
            <AlertTitle>Konto nieaktywne</AlertTitle>
            Twoje konto zostało dezaktywowane. Skontaktuj się z administratorem.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return <>{children}</>;
}
