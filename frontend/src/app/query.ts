/**
 * TanStack Query konfiguracja dla TimeTracker.
 * 
 * Cache settings:
 * - staleTime: 5 minut (dane są świeże przez 5 min)
 * - refetchOnWindowFocus: false (nie refetch przy powrocie do okna)
 * - retry: 1 (jedna próba retry)
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minut
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
