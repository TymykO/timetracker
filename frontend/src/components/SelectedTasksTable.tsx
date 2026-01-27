/**
 * SelectedTasksTable - tabela wybranych tasków z inputami duration.
 * 
 * Odpowiedzialności:
 * - Wyświetlanie wybranych tasków w tabeli
 * - Inputy do wprowadzania czasu (duration_minutes_raw)
 * - Przycisk usuwania taska
 * - Walidacja per-entry (empty/zero)
 * - Footer z sumą i błędem jeśli suma > 1440
 */

import {
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  IconButton,
  Alert,
  Box,
  InputAdornment,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import ArrowDropUpIcon from "@mui/icons-material/ArrowDropUp";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import type { Task } from "../types/dto";

interface SelectedEntry {
  task: Task;
  duration: number | "";
}

interface SelectedTasksTableProps {
  selectedTasks: Map<number, SelectedEntry>;
  onDurationChange: (taskId: number, value: string) => void;
  onRemoveTask: (taskId: number) => void;
  disabled: boolean;
  totalMinutes: number;
  showTotalError: boolean;
}

// Helper: konwersja minut na format hh:mm
function minutesToHHMM(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

// Helper: konwersja minut na format HH:MM dla inputu type="time"
function minutesToTimeInput(minutes: number | ""): string {
  if (minutes === "") return "";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

// Helper: konwersja h:mm na minuty z zaokrągleniem do 30 min
function timeInputToMinutes(timeStr: string): number | "" {
  if (!timeStr || timeStr.trim() === "") return "";
  
  const parts = timeStr.split(":");
  if (parts.length !== 2) return "";
  
  const hours = parseInt(parts[0], 10);
  const mins = parseInt(parts[1], 10);
  
  if (isNaN(hours) || isNaN(mins)) return "";
  
  let totalMinutes = hours * 60 + mins;
  
  // Zaokrąglenie do najbliższych 30 minut
  totalMinutes = Math.round(totalMinutes / 30) * 30;
  
  return totalMinutes;
}

export function SelectedTasksTable({
  selectedTasks,
  onDurationChange,
  onRemoveTask,
  disabled,
  totalMinutes,
  showTotalError,
}: SelectedTasksTableProps) {
  const entries = Array.from(selectedTasks.entries());

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Wybrane taski
      </Typography>

      {entries.length === 0 ? (
        <Box sx={{ py: 3, textAlign: "center" }}>
          <Typography variant="body2" color="text.secondary">
            Nie wybrano żadnych tasków
          </Typography>
        </Box>
      ) : (
        <>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Task</TableCell>
                  <TableCell width={140}>Czas (h:mm)</TableCell>
                  <TableCell width={60} align="center">
                    Akcje
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {entries.map(([taskId, entry]) => {
                  const isEmpty = entry.duration === "";
                  const isZero = entry.duration === 0;
                  const hasError = isEmpty || isZero;

                  return (
                    <TableRow key={taskId}>
                      <TableCell>
                        <Typography variant="body2">
                          {entry.task.display_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          type="text"
                          value={minutesToTimeInput(entry.duration)}
                          onChange={(e) => {
                            const minutes = timeInputToMinutes(e.target.value);
                            onDurationChange(taskId, String(minutes));
                          }}
                          onBlur={(e) => {
                            // Zaokrąglenie przy opuszczeniu pola
                            const minutes = timeInputToMinutes(e.target.value);
                            if (minutes !== "") {
                              onDurationChange(taskId, String(minutes));
                            }
                          }}
                          disabled={disabled}
                          error={hasError}
                          helperText={
                            isEmpty
                              ? "Wymagane (np. 2:00, 4:30)"
                              : isZero
                              ? "Musi być > 0"
                              : ""
                          }
                          placeholder="0:00"
                          InputProps={{
                            endAdornment: !disabled && (
                              <InputAdornment position="end">
                                <Box sx={{ display: "flex", flexDirection: "column", gap: 0 }}>
                                  <IconButton
                                    size="small"
                                    onClick={() => {
                                      const current = typeof entry.duration === "number" ? entry.duration : 0;
                                      const newValue = current + 30;
                                      if (newValue <= 1440) {
                                        onDurationChange(taskId, String(newValue));
                                      }
                                    }}
                                    sx={{ p: 0, height: 16 }}
                                  >
                                    <ArrowDropUpIcon fontSize="small" />
                                  </IconButton>
                                  <IconButton
                                    size="small"
                                    onClick={() => {
                                      const current = typeof entry.duration === "number" ? entry.duration : 0;
                                      const newValue = Math.max(0, current - 30);
                                      onDurationChange(taskId, String(newValue));
                                    }}
                                    sx={{ p: 0, height: 16 }}
                                  >
                                    <ArrowDropDownIcon fontSize="small" />
                                  </IconButton>
                                </Box>
                              </InputAdornment>
                            ),
                          }}
                          fullWidth
                        />
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          aria-label="usuń task"
                          disabled={disabled}
                          onClick={() => onRemoveTask(taskId)}
                          color="error"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>

          <Box sx={{ mt: 2, p: 2, backgroundColor: "action.hover", borderRadius: 1 }}>
            <Typography variant="body1" fontWeight="bold">
              Suma: {minutesToHHMM(totalMinutes)}
            </Typography>
          </Box>

          {showTotalError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Suma czasu przekracza 24h (1440 min). Maksymalna suma: 1440 min.
            </Alert>
          )}
        </>
      )}
    </Paper>
  );
}
