/**
 * LoginPage - strona logowania.
 * 
 * Funkcjonalności:
 * - Formularz email + password
 * - Walidacja i obsługa błędów
 * - Przekierowanie do /month po zalogowaniu
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
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
    <div style={styles.container}>
      <div style={styles.formCard}>
        <h1 style={styles.title}>Logowanie</h1>
        
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.fieldGroup}>
            <label htmlFor="email" style={styles.label}>
              Email:
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="test@example.com"
              style={styles.input}
              disabled={loading}
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="password" style={styles.label}>
              Hasło:
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
              style={styles.input}
              disabled={loading}
            />
          </div>

          {error && (
            <div style={styles.error}>
              {error}
            </div>
          )}

          <button 
            type="submit" 
            style={{
              ...styles.button,
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
            disabled={loading}
          >
            {loading ? "Logowanie..." : "Zaloguj się"}
          </button>
        </form>

        <div style={styles.hint}>
          <strong>Dane testowe:</strong><br />
          Email: test@example.com<br />
          Hasło: testpass123
        </div>
      </div>
    </div>
  );
}

// Podstawowe style
const styles = {
  container: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    minHeight: "100vh",
    backgroundColor: "#f5f5f5",
    padding: "1rem",
  },
  formCard: {
    backgroundColor: "white",
    padding: "2rem",
    borderRadius: "8px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    width: "100%",
    maxWidth: "400px",
  },
  title: {
    margin: "0 0 1.5rem 0",
    fontSize: "1.8rem",
    textAlign: "center" as const,
  },
  form: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "1rem",
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.25rem",
  },
  label: {
    fontSize: "0.9rem",
    fontWeight: 500,
    color: "#333",
  },
  input: {
    padding: "0.75rem",
    fontSize: "1rem",
    border: "1px solid #ddd",
    borderRadius: "4px",
    outline: "none",
    transition: "border-color 0.2s",
  },
  button: {
    padding: "0.75rem",
    fontSize: "1rem",
    fontWeight: 600,
    color: "white",
    backgroundColor: "#1976d2",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    transition: "background-color 0.2s",
    marginTop: "0.5rem",
  },
  error: {
    padding: "0.75rem",
    backgroundColor: "#ffebee",
    color: "#c62828",
    borderRadius: "4px",
    fontSize: "0.9rem",
    textAlign: "center" as const,
  },
  hint: {
    marginTop: "1.5rem",
    padding: "1rem",
    backgroundColor: "#f5f5f5",
    borderRadius: "4px",
    fontSize: "0.85rem",
    color: "#666",
    lineHeight: "1.6",
  },
};
