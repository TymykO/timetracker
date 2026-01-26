/**
 * TimeTracker - główny komponent aplikacji.
 * 
 * Setup:
 * - QueryClientProvider (TanStack Query dla cache)
 * - AppRouter (routing)
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { AppRouter } from "./app/router";
import { queryClient } from "./app/query";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter />
    </QueryClientProvider>
  );
}

export default App;
