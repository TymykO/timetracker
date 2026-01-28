/**
 * MonthTable - tabela wyświetlająca dni miesiąca z metrykami.
 * 
 * Odpowiedzialności:
 * - Renderowanie tabeli z kolumnami: Data | Typ dnia | Czas pracy | Nadgodziny | Wpisy
 * - Formatowanie minut na hh:mm
 * - Wizualne oznaczanie dni przyszłych (wyłączone)
 * - Obsługa kliknięcia w wiersz
 */

import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import RemoveIcon from "@mui/icons-material/Remove";
import type { MonthDay } from "../types/dto";
import { minutesToHHMM } from "../utils/timeUtils";

interface Props {
  days: MonthDay[];
  onDayClick: (date: string) => void;
}

// Helper: formatowanie daty na czytelny format (np. "2025-01-15" -> "15 Sty")
function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  const day = date.getDate();
  const monthNames = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"];
  const month = monthNames[date.getMonth()];
  const weekdayNames = ["Nd", "Pn", "Wt", "Śr", "Czw", "Pt", "Sob"];
  const weekday = weekdayNames[date.getDay()];
  return `${day} ${month} (${weekday})`;
}

export function MonthTable({ days, onDayClick }: Props) {
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Data</TableCell>
            <TableCell>Typ dnia</TableCell>
            <TableCell>Czas pracy</TableCell>
            <TableCell>Nadgodziny</TableCell>
            <TableCell align="center">Wpisy</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {days.map((day) => {
            const isClickable = !day.is_future;
            
            return (
              <TableRow
                key={day.date}
                onClick={() => isClickable && onDayClick(day.date)}
                sx={{
                  cursor: isClickable ? 'pointer' : 'not-allowed',
                  opacity: day.is_future ? 0.5 : 1,
                  backgroundColor: day.is_future ? 'action.disabledBackground' : 'transparent',
                  '&:hover': isClickable ? {
                    backgroundColor: 'action.hover',
                  } : {},
                }}
              >
                <TableCell>{formatDate(day.date)}</TableCell>
                <TableCell>{day.day_type === "Working" ? "Roboczy" : "Wolny"}</TableCell>
                <TableCell>{minutesToHHMM(day.working_time_raw_minutes)}</TableCell>
                <TableCell>{minutesToHHMM(day.overtime_minutes)}</TableCell>
                <TableCell align="center">
                  {day.has_entries ? (
                    <CheckIcon fontSize="small" color="success" />
                  ) : (
                    <RemoveIcon fontSize="small" color="disabled" />
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
