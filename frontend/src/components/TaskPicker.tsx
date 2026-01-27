/**
 * TaskPicker - komponent wyświetlający listę dostępnych tasków.
 * 
 * Odpowiedzialności:
 * - Wyświetlanie listy tasków (już przefiltrowanych)
 * - Przycisk dodawania (+) dla każdego taska
 * - Obsługa disabled state
 * - Scroll dla długich list
 */

import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Box,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import type { Task } from "../types/dto";

interface TaskPickerProps {
  tasks: Task[];
  onAddTask: (task: Task) => void;
  disabled: boolean;
}

export function TaskPicker({ tasks, onAddTask, disabled }: TaskPickerProps) {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Dostępne taski
      </Typography>

      {tasks.length === 0 ? (
        <Box sx={{ py: 3, textAlign: "center" }}>
          <Typography variant="body2" color="text.secondary">
            Brak dostępnych tasków
          </Typography>
        </Box>
      ) : (
        <List
          sx={{
            maxHeight: 500,
            overflow: "auto",
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
          }}
        >
          {tasks.map((task) => (
            <ListItem
              key={task.id}
              divider
              sx={{
                "&:hover": {
                  backgroundColor: disabled ? "transparent" : "action.hover",
                },
              }}
            >
              <ListItemText
                primary={task.display_name}
                secondary={
                  [task.project_phase, task.department, task.discipline]
                    .filter(Boolean)
                    .join(" • ") || "Brak kategorii"
                }
              />
              <ListItemSecondaryAction>
                <IconButton
                  edge="end"
                  aria-label="dodaj task"
                  disabled={disabled}
                  onClick={() => onAddTask(task)}
                  color="primary"
                >
                  <AddIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
}
