/**
 * TimeTracker - główny komponent aplikacji.
 * 
 * Setup:
 * - QueryClientProvider (TanStack Query dla cache)
 * - AppShell (layout z AppBar + Container)
 * - AppRouter (routing)
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { AppRouter } from "./app/router";
import { queryClient } from "./app/query";
import { AppShell } from "./components/AppShell";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell>
        <AppRouter />
      </AppShell>
    </QueryClientProvider>
  );
}

export default App;
