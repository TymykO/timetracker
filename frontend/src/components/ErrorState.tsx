/**
 * ErrorState - komponent wyświetlający komunikat o błędzie.
 * 
 * Props:
 * - message: treść komunikatu błędu
 * - onRetry (opcjonalne): callback dla przycisku "Spróbuj ponownie"
 */

import { Alert, AlertTitle, Button } from '@mui/material';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Alert severity="error" sx={{ mt: 2 }}>
      <AlertTitle>Błąd</AlertTitle>
      {message}
      {onRetry && (
        <Button onClick={onRetry} color="inherit" sx={{ mt: 1 }}>
          Spróbuj ponownie
        </Button>
      )}
    </Alert>
  );
}
