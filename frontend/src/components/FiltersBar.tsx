/**
 * FiltersBar - komponent do filtrowania listy tasków.
 * 
 * Odpowiedzialności:
 * - 3 dropdowny: project_phase, department, discipline
 * - TextField dla wyszukiwania tekstowego
 * - Debounce dla search (300ms)
 */

import { useState, useEffect } from "react";
import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Stack,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";

export interface Filters {
  projectPhase: string | null;
  department: string | null;
  discipline: string | null;
  search: string;
}

interface FiltersBarProps {
  projectPhases: string[];
  departments: string[];
  disciplines: string[];
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
}

export function FiltersBar({
  projectPhases,
  departments,
  disciplines,
  filters,
  onFiltersChange,
}: FiltersBarProps) {
  // Local state dla search z debounce
  const [searchValue, setSearchValue] = useState(filters.search);

  // Debounce search - aktualizuj filters dopiero po 300ms
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchValue !== filters.search) {
        onFiltersChange({ ...filters, search: searchValue });
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchValue]);

  // Sync searchValue gdy filters.search zmieni się z zewnątrz
  useEffect(() => {
    setSearchValue(filters.search);
  }, [filters.search]);

  const handleProjectPhaseChange = (event: SelectChangeEvent) => {
    const value = event.target.value;
    onFiltersChange({
      ...filters,
      projectPhase: value === "" ? null : value,
    });
  };

  const handleDepartmentChange = (event: SelectChangeEvent) => {
    const value = event.target.value;
    onFiltersChange({
      ...filters,
      department: value === "" ? null : value,
    });
  };

  const handleDisciplineChange = (event: SelectChangeEvent) => {
    const value = event.target.value;
    onFiltersChange({
      ...filters,
      discipline: value === "" ? null : value,
    });
  };

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction="row" spacing={2} flexWrap="wrap">
        <Box sx={{ minWidth: 200, flex: 1 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="project-phase-label">Faza projektu</InputLabel>
            <Select
              labelId="project-phase-label"
              value={filters.projectPhase || ""}
              label="Faza projektu"
              onChange={handleProjectPhaseChange}
            >
              <MenuItem value="">
                <em>Wszystkie</em>
              </MenuItem>
              {projectPhases.map((phase) => (
                <MenuItem key={phase} value={phase}>
                  {phase}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <Box sx={{ minWidth: 200, flex: 1 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="department-label">Dział</InputLabel>
            <Select
              labelId="department-label"
              value={filters.department || ""}
              label="Dział"
              onChange={handleDepartmentChange}
            >
              <MenuItem value="">
                <em>Wszystkie</em>
              </MenuItem>
              {departments.map((dept) => (
                <MenuItem key={dept} value={dept}>
                  {dept}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <Box sx={{ minWidth: 200, flex: 1 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="discipline-label">Branża</InputLabel>
            <Select
              labelId="discipline-label"
              value={filters.discipline || ""}
              label="Branża"
              onChange={handleDisciplineChange}
            >
              <MenuItem value="">
                <em>Wszystkie</em>
              </MenuItem>
              {disciplines.map((disc) => (
                <MenuItem key={disc} value={disc}>
                  {disc}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <Box sx={{ minWidth: 200, flex: 1 }}>
          <TextField
            fullWidth
            size="small"
            label="Szukaj"
            placeholder="Wpisz aby wyszukać..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
          />
        </Box>
      </Stack>
    </Box>
  );
}
