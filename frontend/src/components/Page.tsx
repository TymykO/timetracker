/**
 * Page - wrapper dla stron z jednolitą strukturą.
 * 
 * Zapewnia spójny layout dla wszystkich stron aplikacji:
 * - Tytuł strony
 * - Slot na akcje/przyciski (po prawej stronie tytułu)
 * - Zawartość
 * 
 * Props:
 * - title: tytuł strony
 * - actions (opcjonalne): React node z przyciskami/akcjami
 * - children: zawartość strony
 */

import { Box, Typography, Stack } from '@mui/material';

interface PageProps {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function Page({ title, actions, children }: PageProps) {
  return (
    <Box>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 3 }}
      >
        <Typography variant="h4" component="h1">
          {title}
        </Typography>
        {actions && <Box>{actions}</Box>}
      </Stack>
      <Box>{children}</Box>
    </Box>
  );
}
