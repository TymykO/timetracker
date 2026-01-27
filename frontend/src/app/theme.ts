/**
 * Konfiguracja tematu Material UI dla TimeTracker.
 * 
 * Setup:
 * - Kolory (primary: niebieski, secondary: szary)
 * - Typography (Roboto font)
 * - Polskie locale dla komponentów dat
 */

import { createTheme } from '@mui/material/styles';
import { plPL } from '@mui/material/locale';

export const theme = createTheme(
  {
    palette: {
      primary: {
        main: '#1976d2', // Material Blue
      },
      secondary: {
        main: '#757575', // Material Grey
      },
    },
    typography: {
      fontFamily: [
        'Roboto',
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'Arial',
        'sans-serif',
      ].join(','),
    },
  },
  plPL // Polskie locale dla komponentów MUI
);
