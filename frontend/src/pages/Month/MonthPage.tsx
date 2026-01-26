/**
 * MonthPage - widok podsumowania miesiąca.
 * 
 * Funkcjonalności:
 * - Wyświetla tabelę dni z metrykami (czas pracy, nadgodziny, wpisy)
 * - Nawigacja między miesiącami (prev/next)
 * - Blokada przyszłych miesięcy
 * - Kliknięcie w dzień otwiera Day view
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../app/api_client";
import { MonthTable } from "../../components/MonthTable";
import type { MonthSummary } from "../../types/dto";

// Helper: dodaj/odejmij miesiące od stringa YYYY-MM
function addMonths(yearMonth: string, delta: number): string {
  const [year, month] = yearMonth.split("-").map(Number);
  const date = new Date(year, month - 1 + delta, 1);
  const newYear = date.getFullYear();
  const newMonth = String(date.getMonth() + 1).padStart(2, "0");
  return `${newYear}-${newMonth}`;
}

// Helper: nazwa miesiąca po polsku
function getMonthName(yearMonth: string): string {
  const [year, month] = yearMonth.split("-").map(Number);
  const monthNames = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"
  ];
  return `${monthNames[month - 1]} ${year}`;
}

// Helper: sprawdź czy month jest w przyszłości (nie można go wyświetlić)
function isMonthInFuture(yearMonth: string): boolean {
  const [year, month] = yearMonth.split("-").map(Number);
  const targetDate = new Date(year, month - 1, 1);
  const now = new Date();
  const currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  return targetDate > currentMonth;
}

export default function MonthPage() {
  const { yearMonth } = useParams<{ yearMonth: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<MonthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch danych miesiąca
  useEffect(() => {
    if (!yearMonth) return;

    const fetchMonth = async () => {
      setLoading(true);
      setError(null);

      try {
        const summary = await api.getMonthSummary(yearMonth);
        setData(summary);
      } catch (err: any) {
        console.error("Failed to fetch month summary:", err);
        if (err.status === 400) {
          setError("Nie można załadować przyszłego miesiąca.");
        } else if (err.status === 401) {
          // AuthGuard powinien obsłużyć, ale na wszelki wypadek
          navigate("/login");
        } else {
          setError("Nie udało się załadować danych miesiąca. Spróbuj ponownie.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMonth();
  }, [yearMonth, navigate]);

  // Handlers dla nawigacji
  const handlePrevMonth = () => {
    if (yearMonth) {
      const prev = addMonths(yearMonth, -1);
      navigate(`/month/${prev}`);
    }
  };

  const handleNextMonth = () => {
    if (yearMonth) {
      const next = addMonths(yearMonth, 1);
      if (!isMonthInFuture(next)) {
        navigate(`/month/${next}`);
      }
    }
  };

  // Handler dla kliknięcia w dzień
  const handleDayClick = (date: string) => {
    navigate(`/day/${date}`);
  };

  // Sprawdź czy przycisk "Następny" powinien być wyłączony
  const isNextDisabled = yearMonth ? isMonthInFuture(addMonths(yearMonth, 1)) : true;

  return (
    <div style={styles.container}>
      {/* Header z nawigacją */}
      <div style={styles.header}>
        <button onClick={handlePrevMonth} style={styles.button}>
          ← Poprzedni
        </button>
        <h1 style={styles.title}>
          {yearMonth ? getMonthName(yearMonth) : ""}
        </h1>
        <button
          onClick={handleNextMonth}
          disabled={isNextDisabled}
          style={{
            ...styles.button,
            opacity: isNextDisabled ? 0.5 : 1,
            cursor: isNextDisabled ? 'not-allowed' : 'pointer',
          }}
        >
          Następny →
        </button>
      </div>

      {/* Stany: loading, error, data */}
      {loading && (
        <div style={styles.message}>Ładowanie...</div>
      )}

      {error && (
        <div style={styles.error}>{error}</div>
      )}

      {!loading && !error && data && (
        <MonthTable days={data.days} onDayClick={handleDayClick} />
      )}
    </div>
  );
}

// Podstawowe style
const styles = {
  container: {
    padding: "2rem",
    maxWidth: "1200px",
    margin: "0 auto",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1.5rem",
  },
  title: {
    margin: 0,
    fontSize: "1.8rem",
  },
  button: {
    padding: "0.5rem 1rem",
    fontSize: "1rem",
    border: "1px solid #ddd",
    borderRadius: "4px",
    backgroundColor: "white",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  message: {
    textAlign: "center" as const,
    padding: "2rem",
    fontSize: "1.1rem",
    color: "#666",
  },
  error: {
    textAlign: "center" as const,
    padding: "1rem",
    backgroundColor: "#ffebee",
    color: "#c62828",
    borderRadius: "4px",
    marginTop: "1rem",
  },
};
