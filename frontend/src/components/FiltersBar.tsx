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
  Autocomplete,
  TextField,
  Stack,
} from "@mui/material";

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

  const handleProjectPhaseChange = (_: any, newValue: string | null) => {
    onFiltersChange({
      ...filters,
      projectPhase: newValue,
    });
  };

  const handleDepartmentChange = (_: any, newValue: string | null) => {
    onFiltersChange({
      ...filters,
      department: newValue,
    });
  };

  const handleDisciplineChange = (_: any, newValue: string | null) => {
    onFiltersChange({
      ...filters,
      discipline: newValue,
    });
  };

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction="row" spacing={2} flexWrap="wrap">
        <Box sx={{ minWidth: 200, flex: 1 }}>
          <Autocomplete
            options={[null, ...projectPhases]}
            value={filters.projectPhase}
            onChange={handleProjectPhaseChange}
            getOptionLabel={(option) => option || "Wszystkie"}
            isOptionEqualToValue={(option, value) => option === value}
            renderInput={(params) => (
              <TextField {...params} label="Faza projektu" />
            )}
            size="small"
            fullWidth
          />
        </Box>

        <Box sx={{ minWidth: 200, flex: 1 }}>
          <Autocomplete
            options={[null, ...departments]}
            value={filters.department}
            onChange={handleDepartmentChange}
            getOptionLabel={(option) => option || "Wszystkie"}
            isOptionEqualToValue={(option, value) => option === value}
            renderInput={(params) => (
              <TextField {...params} label="Dział" />
            )}
            size="small"
            fullWidth
          />
        </Box>

        <Box sx={{ minWidth: 200, flex: 1 }}>
          <Autocomplete
            options={[null, ...disciplines]}
            value={filters.discipline}
            onChange={handleDisciplineChange}
            getOptionLabel={(option) => option || "Wszystkie"}
            isOptionEqualToValue={(option, value) => option === value}
            renderInput={(params) => (
              <TextField {...params} label="Branża" />
            )}
            size="small"
            fullWidth
          />
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
