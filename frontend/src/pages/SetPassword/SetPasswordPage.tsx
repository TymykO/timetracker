/**
 * SetPasswordPage - strona ustawiania hasła (invite flow).
 * 
 * Funkcjonalności:
 * - Walidacja tokenu z URL query params
 * - Formularz ustawiania hasła (password + confirm)
 * - Przekierowanie do /login po sukcesie
 */

import { useState, useEffect, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
} from "@mui/material";
import { api } from "../../app/api_client";
import { LoadingState } from "../../components/LoadingState";

export default function SetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);

  // Walidacja tokenu przy montowaniu
  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setError("Brak tokenu w URL. Link może być nieprawidłowy.");
        setValidating(false);
        return;
      }

      try {
        await api.validateInviteToken(token);
        setTokenValid(true);
      } catch (err: any) {
        console.error("Token validation failed:", err);
        if (err.status === 400) {
          setError("Token jest nieprawidłowy lub wygasł.");
        } else {
          setError("Nie udało się zweryfikować tokenu.");
        }
      } finally {
        setValidating(false);
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Walidacja lokalna
    if (password !== confirmPassword) {
      setError("Hasła nie są identyczne");
      return;
    }

    if (password.length < 8) {
      setError("Hasło musi mieć co najmniej 8 znaków");
      return;
    }

    if (!token) {
      setError("Brak tokenu");
      return;
    }

    setLoading(true);

    try {
      await api.setPassword(token, password);
      // Sukces - przekieruj do logowania
      navigate("/login", { replace: true });
    } catch (err: any) {
      console.error("Set password failed:", err);
      if (err.status === 400) {
        setError("Token wygasł lub hasło nie spełnia wymagań");
      } else {
        setError("Wystąpił błąd. Spróbuj ponownie.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (validating) {
    return (
      <Box display="flex" justifyContent="center" minHeight="100vh" alignItems="center">
        <LoadingState message="Weryfikacja tokenu..." />
      </Box>
    );
  }

  if (!tokenValid) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        sx={{ backgroundColor: 'grey.100', p: 2 }}
      >
        <Card sx={{ width: '100%', maxWidth: 400 }}>
          <CardContent sx={{ p: 3 }}>
            <Alert severity="error" sx={{ mb: 3 }}>
              {error || "Token jest nieprawidłowy"}
            </Alert>
            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => navigate("/login")}
            >
              Wróć do logowania
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      sx={{ backgroundColor: 'grey.100', p: 2 }}
    >
      <Card sx={{ width: '100%', maxWidth: 400 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h4" component="h1" align="center" gutterBottom>
            Ustaw hasło
          </Typography>
          
          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
            <TextField
              id="password"
              label="Nowe hasło"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              autoComplete="new-password"
              placeholder="••••••••"
              disabled={loading}
              margin="normal"
            />

            <TextField
              id="confirm-password"
              label="Powtórz hasło"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              fullWidth
              autoComplete="new-password"
              placeholder="••••••••"
              disabled={loading}
              margin="normal"
            />

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            <Button
              type="submit"
              variant="contained"
              fullWidth
              size="large"
              disabled={loading}
              sx={{ mt: 3 }}
            >
              {loading ? "Zapisywanie..." : "Ustaw hasło"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
