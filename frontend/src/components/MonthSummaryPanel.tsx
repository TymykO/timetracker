/**
 * MonthSummaryPanel - panel podsumowania miesiąca.
 * 
 * Wyświetla kluczowe statystyki:
 * - Łączny czas pracy
 * - Nadgodziny
 * - Norma miesiąca
 * - Postęp wykonania normy
 * - Higiena wpisów (dni z wpisami vs brakujące)
 */

import { Paper, Typography, Box, LinearProgress } from "@mui/material";
import type { MonthDay } from "../types/dto";
import { minutesToHHMM } from "../utils/timeUtils";

interface Props {
  days: MonthDay[];
  dailyNormMinutes: number;
}

// Helper subkomponent dla wyświetlania pojedynczej statystyki
function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ mb: 2, textAlign: "center" }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" sx={{ fontWeight: 500 }}>
        {value}
      </Typography>
    </Box>
  );
}

export function MonthSummaryPanel({ days, dailyNormMinutes }: Props) {
  // 1. Łączny czas pracy (suma working_time_raw_minutes ze wszystkich dni)
  const totalWorkMinutes = days.reduce((sum, day) => 
    sum + day.working_time_raw_minutes, 0
  );

  // 2. Łączne nadgodziny (suma overtime_minutes ze wszystkich dni)
  const totalOvertimeMinutes = days.reduce((sum, day) => 
    sum + day.overtime_minutes, 0
  );

  // 3. Norma miesiąca (liczba dni roboczych * norma dzienna)
  const workingDaysCount = days.filter(d => 
    d.day_type === "Working"
  ).length;
  const monthlyNormMinutes = workingDaysCount * dailyNormMinutes;

  // 4. Postęp wykonania normy
  const progressPercent = monthlyNormMinutes > 0
    ? Math.round((totalWorkMinutes / monthlyNormMinutes) * 100)
    : 0;
  const progressForBar = Math.min(progressPercent, 100);

  // 5. Higiena wpisów
  const daysWithEntries = days.filter(d => 
    d.day_type === "Working" && d.has_entries
  ).length;
  const missingDays = workingDaysCount - daysWithEntries;

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom align="center">
        Podsumowanie miesiąca
      </Typography>

      {/* Sekcja: Kluczowe statystyki */}
      <Box sx={{ my: 3 }}>
        <StatItem 
          label="Łącznie czasu pracy" 
          value={minutesToHHMM(totalWorkMinutes)} 
        />
        <StatItem 
          label="Nadgodziny" 
          value={minutesToHHMM(totalOvertimeMinutes)} 
        />
        <StatItem 
          label="Norma miesiąca" 
          value={minutesToHHMM(monthlyNormMinutes)} 
        />
      </Box>

      {/* Sekcja: Postęp wykonania normy */}
      <Box sx={{ my: 3 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom align="center">
          Wykonanie normy: {progressPercent}%
          {progressPercent > 100 && ` (nadwyżka: ${minutesToHHMM(totalWorkMinutes - monthlyNormMinutes)})`}
        </Typography>
        <LinearProgress 
          variant="determinate" 
          value={progressForBar}
          sx={{ height: 8, borderRadius: 1 }}
        />
      </Box>

      {/* Sekcja: Higiena wpisów */}
      <Box sx={{ mt: 3, textAlign: "center" }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Dni z wpisami: {daysWithEntries} / {workingDaysCount}
        </Typography>
        <Typography 
          variant="body2" 
          color={missingDays > 0 ? "warning.main" : "success.main"}
        >
          Brakujące dni robocze: {missingDays}
        </Typography>
      </Box>
    </Paper>
  );
}
