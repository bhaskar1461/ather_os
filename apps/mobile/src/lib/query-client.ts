/**
 * TanStack Query client with sensible defaults for the AetherOS mobile app.
 *
 * - Astrology readings are expensive (LLM call) → 5 min stale time
 * - Profiles/chats are cheap → 1 min stale time
 * - Retry 2x on failure with exponential backoff
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 30 * 60 * 1000,   // 30 minutes cache
      retry: 2,
      refetchOnWindowFocus: false, // RN doesn't have window focus
    },
    mutations: {
      retry: 1,
    },
  },
});
