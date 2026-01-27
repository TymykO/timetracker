/**
 * DayPage - widok edycji dnia (wpisy czasu).
 * 
 * Funkcjonalności:
 * - Ładowanie danych dnia i listy tasków
 * - Filtrowanie tasków (project_phase, department, discipline, search)
 * - Zarządzanie wybranymi taskami (dodawanie, usuwanie, zmiana duration)
 * - Walidacja (duration > 0, suma <= 1440)
 * - Zapis z invalidacją cache
 * - Nawigacja prev/next day
 */

import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ButtonGroup,
  Paper,
  Stack,
  Box,
  Chip,
  Typography,
  Snackbar,
  Alert,
} from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { api } from "../../app/api_client";
import { Page } from "../../components/Page";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { FiltersBar } from "../../components/FiltersBar";
import { TaskPicker } from "../../components/TaskPicker";
import { SelectedTasksTable } from "../../components/SelectedTasksTable";
import type { Filters } from "../../components/FiltersBar";
import type { Task, SaveDayItem } from "../../types/dto";

// ========== Helper Functions ==========

function minutesToHHMM(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

function addDays(dateStr: string, delta: number): string {
  const date = new Date(dateStr + "T00:00:00");
  date.setDate(date.getDate() + delta);
  return date.toISOString().split("T")[0];
}

function isFuture(dateStr: string): boolean {
  const target = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return target > today;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  const day = date.getDate();
  const monthNames = [
    "Styczeń",
    "Luty",
    "Marzec",
    "Kwiecień",
    "Maj",
    "Czerwiec",
    "Lipiec",
    "Sierpień",
    "Wrzesień",
    "Październik",
    "Listopad",
    "Grudzień",
  ];
  const month = monthNames[date.getMonth()];
  const year = date.getFullYear();
  const weekdayNames = [
    "Niedziela",
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
  ];
  const weekday = weekdayNames[date.getDay()];
  return `${weekday}, ${day} ${month} ${year}`;
}

// ========== Types ==========

interface SelectedEntry {
  task: Task;
  duration: number | "";
}

// ========== Main Component ==========

export default function DayPage() {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // ===== State =====

  // Filters (persystują przy dodawaniu tasków)
  const [filters, setFilters] = useState<Filters>({
    projectPhase: null,
    department: null,
    discipline: null,
    search: "",
  });

  // Selected tasks (Map dla unikalności)
  const [selectedTasks, setSelectedTasks] = useState<Map<number, SelectedEntry>>(
    new Map()
  );

  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // ===== Data Loading =====

  // Load day data
  const {
    data: dayData,
    isLoading: dayLoading,
    error: dayError,
  } = useQuery({
    queryKey: ["day", date],
    queryFn: () => api.getDay(date!),
    enabled: !!date,
  });

  // Load tasks list
  const {
    data: tasksData,
    isLoading: tasksLoading,
    error: tasksError,
  } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => api.getActiveTasks(),
    staleTime: 1000 * 60 * 10, // 10 minut
  });

  // ===== Initialize selected tasks from dayData =====

  useEffect(() => {
    if (dayData?.entries && tasksData?.tasks) {
      const map = new Map<number, SelectedEntry>();
      dayData.entries.forEach((entry) => {
        const task = tasksData.tasks.find((t) => t.id === entry.task_id);
        if (task) {
          map.set(entry.task_id, {
            task,
            duration: entry.duration_minutes_raw,
          });
        }
      });
      setSelectedTasks(map);
    }
  }, [dayData, tasksData]);

  // ===== Derived State =====

  const selectedTaskIds = useMemo(
    () => new Set(selectedTasks.keys()),
    [selectedTasks]
  );

  const filteredTasks = useMemo(() => {
    if (!tasksData?.tasks) return [];

    return tasksData.tasks.filter((task) => {
      // Exclude already selected
      if (selectedTaskIds.has(task.id)) return false;

      // Apply filters
      if (filters.projectPhase && task.project_phase !== filters.projectPhase) {
        return false;
      }
      if (filters.department && task.department !== filters.department) {
        return false;
      }
      if (filters.discipline && task.discipline !== filters.discipline) {
        return false;
      }

      // Apply search (case-insensitive, match against search_text)
      if (filters.search) {
        const searchLower = filters.search.toLowerCase().trim();
        const searchText = task.search_text?.toLowerCase() || "";
        const displayName = task.display_name?.toLowerCase() || "";
        if (!searchText.includes(searchLower) && !displayName.includes(searchLower)) {
          return false;
        }
      }

      return true;
    });
  }, [tasksData, selectedTaskIds, filters]);

  const totalMinutes = useMemo(() => {
    return Array.from(selectedTasks.values()).reduce((sum, entry) => {
      return sum + (typeof entry.duration === "number" ? entry.duration : 0);
    }, 0);
  }, [selectedTasks]);

  const hasValidationErrors = useMemo(() => {
    // Check if any duration is empty or zero
    for (const entry of selectedTasks.values()) {
      if (entry.duration === "" || entry.duration === 0) {
        return true;
      }
    }
    // Check if total > 1440
    if (totalMinutes > 1440) {
      return true;
    }
    return false;
  }, [selectedTasks, totalMinutes]);

  const canSave = useMemo(() => {
    return (
      dayData?.is_editable &&
      !hasValidationErrors &&
      !isSaving &&
      selectedTasks.size > 0
    );
  }, [dayData, hasValidationErrors, isSaving, selectedTasks]);

  // ===== Handlers =====

  const handleAddTask = (task: Task) => {
    setSelectedTasks((prev) => {
      const newMap = new Map(prev);
      newMap.set(task.id, { task, duration: "" });
      return newMap;
    });
  };

  const handleRemoveTask = (taskId: number) => {
    setSelectedTasks((prev) => {
      const newMap = new Map(prev);
      newMap.delete(taskId);
      return newMap;
    });
  };

  const handleDurationChange = (taskId: number, value: string) => {
    const numValue = value === "" ? "" : parseInt(value, 10);
    setSelectedTasks((prev) => {
      const newMap = new Map(prev);
      const entry = newMap.get(taskId);
      if (entry) {
        newMap.set(taskId, { ...entry, duration: numValue });
      }
      return newMap;
    });
  };

  const handleSave = async () => {
    if (!date || !canSave) return;

    setIsSaving(true);
    setSaveError(null);

    const items: SaveDayItem[] = Array.from(selectedTasks.values()).map(
      ({ task, duration }) => ({
        task_id: task.id,
        duration_minutes_raw: duration as number,
      })
    );

    try {
      await api.saveDay(date, items);

      // Invalidate queries
      await queryClient.invalidateQueries({ queryKey: ["day", date] });
      const [year, month] = date.split("-");
      await queryClient.invalidateQueries({
        queryKey: ["month", `${year}-${month}`],
      });

      setSaveSuccess(true);
    } catch (err: any) {
      console.error("Save failed:", err);
      setSaveError(err.message || "Błąd zapisu. Spróbuj ponownie.");
    } finally {
      setIsSaving(false);
    }
  };

  // ===== Navigation =====

  const handlePrevDay = () => {
    if (date) {
      const prev = addDays(date, -1);
      navigate(`/day/${prev}`);
    }
  };

  const handleNextDay = () => {
    if (date) {
      const next = addDays(date, 1);
      if (!isFuture(next)) {
        navigate(`/day/${next}`);
      }
    }
  };

  const handleBackToMonth = () => {
    if (date) {
      const [year, month] = date.split("-");
      navigate(`/month/${year}-${month}`);
    }
  };

  const isNextDisabled = date ? isFuture(addDays(date, 1)) : true;

  // ===== Render =====

  const loading = dayLoading || tasksLoading;
  const error = dayError || tasksError;

  const navigationButtons = (
    <Stack direction="row" spacing={1}>
      <ButtonGroup variant="outlined" size="small">
        <Button onClick={handlePrevDay} startIcon={<ChevronLeftIcon />}>
          Poprzedni
        </Button>
        <Button
          onClick={handleNextDay}
          disabled={isNextDisabled}
          endIcon={<ChevronRightIcon />}
        >
          Następny
        </Button>
      </ButtonGroup>
      <Button
        variant="outlined"
        size="small"
        startIcon={<ArrowBackIcon />}
        onClick={handleBackToMonth}
      >
        Powrót do miesiąca
      </Button>
    </Stack>
  );

  return (
    <Page title={date ? formatDate(date) : "Dzień"} actions={navigationButtons}>
      <Stack spacing={3}>
        {loading && <LoadingState message="Ładowanie danych dnia..." />}

        {error && (
          <ErrorState message="Nie udało się załadować danych. Spróbuj ponownie." />
        )}

        {!loading && !error && dayData && tasksData && (
          <>
            {/* Day Summary */}
            <Paper sx={{ p: 2 }}>
              <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                <Chip
                  label={dayData.day_type === "Working" ? "Roboczy" : "Wolny"}
                  color={dayData.day_type === "Working" ? "primary" : "default"}
                />
                <Typography variant="body1">
                  Czas pracy: <strong>{minutesToHHMM(dayData.total_raw_minutes)}</strong>
                </Typography>
                <Typography variant="body1">
                  Nadgodziny: <strong>{minutesToHHMM(dayData.total_overtime_minutes)}</strong>
                </Typography>
                {!dayData.is_editable && (
                  <Chip label="Tylko do odczytu" color="warning" size="small" />
                )}
              </Stack>
            </Paper>

            {/* Filters */}
            <Paper>
              <FiltersBar
                projectPhases={tasksData.filter_values.project_phases}
                departments={tasksData.filter_values.departments}
                disciplines={tasksData.filter_values.disciplines}
                filters={filters}
                onFiltersChange={setFilters}
              />
            </Paper>

            {/* Two columns: Available tasks | Selected tasks */}
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ alignItems: "stretch" }}
            >
              <Box sx={{ flex: 1 }}>
                <TaskPicker
                  tasks={filteredTasks}
                  onAddTask={handleAddTask}
                  disabled={!dayData.is_editable}
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <SelectedTasksTable
                  selectedTasks={selectedTasks}
                  onDurationChange={handleDurationChange}
                  onRemoveTask={handleRemoveTask}
                  disabled={!dayData.is_editable}
                  totalMinutes={totalMinutes}
                  showTotalError={totalMinutes > 1440}
                />
              </Box>
            </Stack>

            {/* Save/Cancel buttons */}
            <Box display="flex" gap={2}>
              <Button
                variant="contained"
                disabled={!canSave}
                onClick={handleSave}
                size="large"
              >
                {isSaving ? "Zapisywanie..." : "Zapisz wpisy"}
              </Button>
              <Button variant="outlined" onClick={handleBackToMonth} size="large">
                Anuluj
              </Button>
            </Box>

            {/* Error alert */}
            {saveError && (
              <Alert severity="error" onClose={() => setSaveError(null)}>
                {saveError}
              </Alert>
            )}
          </>
        )}

        {/* Success snackbar */}
        <Snackbar
          open={saveSuccess}
          autoHideDuration={3000}
          onClose={() => setSaveSuccess(false)}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        >
          <Alert severity="success" sx={{ width: "100%" }}>
            Zapisano wpisy
          </Alert>
        </Snackbar>
      </Stack>
    </Page>
  );
}
