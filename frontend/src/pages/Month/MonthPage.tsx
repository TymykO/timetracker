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
import { useQuery } from "@tanstack/react-query";
import { ButtonGroup, Button, Grid, Box } from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { api } from "../../app/api_client";
import { MonthTable } from "../../components/MonthTable";
import { MonthSummaryPanel } from "../../components/MonthSummaryPanel";
import { Page } from "../../components/Page";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
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

  // Pobierz profil użytkownika z cache (AuthGuard już go załadował)
  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.me(),
  });
  const dailyNormMinutes = user?.daily_norm_minutes ?? 480;

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

  // Actions: przyciski nawigacji
  const actions = (
    <ButtonGroup variant="outlined">
      <Button onClick={handlePrevMonth} startIcon={<ChevronLeftIcon />}>
        Poprzedni
      </Button>
      <Button
        onClick={handleNextMonth}
        disabled={isNextDisabled}
        endIcon={<ChevronRightIcon />}
      >
        Następny
      </Button>
    </ButtonGroup>
  );

  return (
    <Page title={yearMonth ? getMonthName(yearMonth) : ""} actions={actions}>
      {loading && <LoadingState message="Ładowanie miesiąca..." />}

      {error && <ErrorState message={error} />}

      {!loading && !error && data && (
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3, flexWrap: 'wrap' }}>
          <Box sx={{ flex: '1 1 auto', minWidth: 0, maxWidth: 800 }}>
            <MonthTable days={data.days} onDayClick={handleDayClick} />
          </Box>
          <Box sx={{ flex: '0 0 auto', width: { xs: '100%', md: 400 } }}>
            <MonthSummaryPanel 
              days={data.days} 
              dailyNormMinutes={dailyNormMinutes}
            />
          </Box>
        </Box>
      )}
    </Page>
  );
}
