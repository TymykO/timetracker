/**
 * TimeTracker - główny komponent aplikacji.
 * 
 * Setup:
 * - QueryClientProvider (TanStack Query dla cache)
 * - AppShell (layout z AppBar + Container)
 * - AppRouter (routing)
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./app/router";
import { queryClient } from "./app/query";
import { AppShell } from "./components/AppShell";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell>
          <AppRouter />
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
