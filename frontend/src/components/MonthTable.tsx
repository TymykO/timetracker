/**
 * MonthTable - tabela wyświetlająca dni miesiąca z metrykami.
 * 
 * Odpowiedzialności:
 * - Renderowanie tabeli z kolumnami: Data | Typ dnia | Czas pracy | Nadgodziny | Wpisy
 * - Formatowanie minut na hh:mm
 * - Wizualne oznaczanie dni przyszłych (wyłączone)
 * - Obsługa kliknięcia w wiersz
 */

import type { MonthDay } from "../types/dto";

interface Props {
  days: MonthDay[];
  onDayClick: (date: string) => void;
}

// Helper: konwersja minut na format hh:mm
function minutesToHHMM(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
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
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.th}>Data</th>
          <th style={styles.th}>Typ dnia</th>
          <th style={styles.th}>Czas pracy</th>
          <th style={styles.th}>Nadgodziny</th>
          <th style={styles.th}>Wpisy</th>
        </tr>
      </thead>
      <tbody>
        {days.map((day) => {
          const isClickable = !day.is_future;
          
          return (
            <tr
              key={day.date}
              onClick={() => isClickable && onDayClick(day.date)}
              style={{
                ...styles.tr,
                cursor: isClickable ? 'pointer' : 'not-allowed',
                opacity: day.is_future ? 0.5 : 1,
                backgroundColor: day.is_future ? '#f5f5f5' : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (isClickable) {
                  e.currentTarget.style.backgroundColor = '#e3f2fd';
                }
              }}
              onMouseLeave={(e) => {
                if (isClickable) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              <td style={styles.td}>{formatDate(day.date)}</td>
              <td style={styles.td}>{day.day_type === "Working" ? "Roboczy" : "Wolny"}</td>
              <td style={styles.td}>{minutesToHHMM(day.working_time_raw_minutes)}</td>
              <td style={styles.td}>{minutesToHHMM(day.overtime_minutes)}</td>
              <td style={styles.td}>{day.has_entries ? '✓' : '—'}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// Podstawowe style inline
const styles = {
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    marginTop: '1rem',
  },
  th: {
    textAlign: 'left' as const,
    padding: '0.75rem',
    borderBottom: '2px solid #ddd',
    fontWeight: 600,
  },
  tr: {
    transition: 'background-color 0.2s',
  },
  td: {
    padding: '0.75rem',
    borderBottom: '1px solid #eee',
  },
};
