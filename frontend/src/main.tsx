/**
 * Entry point aplikacji TimeTracker.
 * 
 * Setup:
 * - Material UI ThemeProvider + CssBaseline
 * - Konfiguracja dayjs (polskie locale)
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import dayjs from 'dayjs'
import 'dayjs/locale/pl'
import './index.css'
import App from './App.tsx'
import { theme } from './app/theme'

// Konfiguracja dayjs - polskie locale
dayjs.locale('pl')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </StrictMode>,
)
