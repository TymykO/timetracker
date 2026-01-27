/**
 * AppShell - główny layout aplikacji.
 * 
 * Zapewnia:
 * - AppBar z tytułem "TimeTracker"
 * - Email użytkownika + przycisk Wyloguj (tylko dla zalogowanych)
 * - Container dla zawartości
 * 
 * Używa useQuery do pobierania danych użytkownika z /api/me.
 * Przycisk Wyloguj jest widoczny tylko gdy użytkownik jest zalogowany.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Box,
  Button,
  Container,
  Toolbar,
  Typography,
} from '@mui/material';
import { api } from '../app/api_client';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Sprawdź czy jesteśmy na chronionej stronie (nie na /login, /set-password, etc.)
  const isPublicRoute = [
    '/login',
    '/set-password',
    '/forgot-password',
    '/reset-password',
  ].some((route) => location.pathname.startsWith(route));

  // Pobierz dane użytkownika (tylko jeśli nie jesteśmy na publicznej stronie)
  const { data: user } = useQuery({
    queryKey: ['me'],
    queryFn: () => api.me(),
    enabled: !isPublicRoute, // nie odpytuj API na publicznych stronach
    retry: false,
  });

  const handleLogout = async () => {
    try {
      await api.logout();
      // Wyczyść cache Query Client
      queryClient.clear();
      // Przekieruj na login
      navigate('/login', { replace: true });
    } catch (err) {
      console.error('Logout failed:', err);
      // Nawet jeśli logout się nie powiedzie, przekieruj na login
      queryClient.clear();
      navigate('/login', { replace: true });
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 0 }}>
            TimeTracker
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          {user && (
            <>
              <Typography variant="body1" sx={{ mr: 2 }}>
                {user.email}
              </Typography>
              <Button color="inherit" onClick={handleLogout}>
                Wyloguj
              </Button>
            </>
          )}
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ flex: 1, py: 4 }}>
        {children}
      </Container>
    </Box>
  );
}
