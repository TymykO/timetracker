/**
 * ForgotPasswordPage - strona żądania resetu hasła.
 * 
 * Funkcjonalności:
 * - Formularz z polem email
 * - Wysłanie żądania resetu hasła
 * - Wyświetlenie komunikatu o wysłaniu emaila
 */

import { useState, type FormEvent } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Link,
} from "@mui/material";
import { api } from "../../app/api_client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setLoading(true);

    try {
      await api.requestPasswordReset(email);
      setSuccess(true);
      setEmail(""); // Wyczyść pole
    } catch (err: any) {
      console.error("Password reset request failed:", err);
      if (err.status === 400) {
        setError("Nieprawidłowy adres email");
      } else {
        setError("Wystąpił błąd. Spróbuj ponownie.");
      }
    } finally {
      setLoading(false);
    }
  };

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
            Zapomniałeś hasła?
          </Typography>
          
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Podaj swój adres email, a wyślemy Ci link do resetowania hasła.
          </Typography>

          {success ? (
            <>
              <Alert severity="success">
                Link do resetowania hasła został wysłany na podany adres email.
                Sprawdź swoją skrzynkę pocztową.
              </Alert>
              <Box sx={{ mt: 3, textAlign: 'center' }}>
                <Link
                  component={RouterLink}
                  to="/login"
                  variant="body2"
                  sx={{ textDecoration: 'none' }}
                >
                  Wróć do logowania
                </Link>
              </Box>
            </>
          ) : (
            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                id="email"
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                fullWidth
                autoComplete="email"
                placeholder="twoj@email.com"
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
                {loading ? "Wysyłanie..." : "Wyślij link"}
              </Button>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Link
                  component={RouterLink}
                  to="/login"
                  variant="body2"
                  sx={{ textDecoration: 'none' }}
                >
                  Wróć do logowania
                </Link>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
