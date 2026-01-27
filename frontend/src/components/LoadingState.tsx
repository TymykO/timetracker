/**
 * LoadingState - komponent wyświetlający stan ładowania.
 * 
 * Props:
 * - message (opcjonalne): tekst do wyświetlenia obok spinnera
 */

import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message }: LoadingStateProps) {
  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight={200}
    >
      <CircularProgress />
      {message && (
        <Typography sx={{ ml: 2 }} color="text.secondary">
          {message}
        </Typography>
      )}
    </Box>
  );
}
