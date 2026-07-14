import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { apiGet } from "@/utils/api";

/**
 * Thin wrapper around `useQuery` + `apiGet` that standardises cache/stale
 * behaviour across all data-fetching pages.
 *
 * @param key  - React Query cache key (array of strings)
 * @param path - Backend API path, e.g. "/api/analytics"
 * @param options - Optional overrides for staleTime, refetchInterval, enabled, etc.
 */
export function useApiQuery<T>(
  key: string[],
  path: string,
  options?: {
    staleTime?: number;
    refetchInterval?: number;
    enabled?: boolean;
  },
) {
  return useQuery<T>({
    queryKey: key,
    queryFn: () => apiGet<T>(path),
    staleTime: options?.staleTime ?? 60_000, // 1 min default
    gcTime: options?.staleTime ? options.staleTime * 2 : 120_000,
    refetchOnWindowFocus: false,
    ...options,
  });
}
