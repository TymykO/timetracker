/**
 * LoginPage - strona logowania.
 * 
 * Funkcjonalności:
 * - Formularz email + password
 * - Walidacja i obsługa błędów
 * - Przekierowanie do /month po zalogowaniu
 */

import { useState, type FormEvent } from "react";
import { useNavigate, Link as RouterLink } from "react-router-dom";
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

export default function LoginPage() {
  const navigate = useNavigate();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.login(email, password);
      
      // Po zalogowaniu przekieruj do obecnego miesiąca
      const now = new Date();
      const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
      navigate(`/month/${currentMonth}`, { replace: true });
    } catch (err: any) {
      console.error("Login failed:", err);
      if (err.status === 400 || err.status === 401) {
        setError("Nieprawidłowy email lub hasło");
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
            Logowanie
          </Typography>
          
          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
            <TextField
              id="email"
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              fullWidth
              autoComplete="email"
              placeholder="test@example.com"
              disabled={loading}
              margin="normal"
            />

            <TextField
              id="password"
              label="Hasło"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              autoComplete="current-password"
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
              {loading ? "Logowanie..." : "Zaloguj się"}
            </Button>

            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Link
                component={RouterLink}
                to="/forgot-password"
                variant="body2"
                sx={{ textDecoration: 'none' }}
              >
                Zapomniałeś hasła?
              </Link>
            </Box>
          </Box>

          <Box
            sx={{
              mt: 3,
              p: 2,
              backgroundColor: 'grey.100',
              borderRadius: 1,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              <strong>Dane testowe:</strong><br />
              Email: test@example.com<br />
              Hasło: testpass123
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
