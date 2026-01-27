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
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
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
                  <TableCell width={120}>Czas (min)</TableCell>
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
                          type="number"
                          value={entry.duration}
                          onChange={(e) => onDurationChange(taskId, e.target.value)}
                          disabled={disabled}
                          error={hasError}
                          helperText={
                            isEmpty
                              ? "Wymagane"
                              : isZero
                              ? "Musi być > 0"
                              : ""
                          }
                          inputProps={{
                            min: 1,
                            step: 1,
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
              Suma: {minutesToHHMM(totalMinutes)} ({totalMinutes} min)
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
