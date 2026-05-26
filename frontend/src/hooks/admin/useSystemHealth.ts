import { type UseQueryResult, useQuery } from '@tanstack/react-query'
import { queryKeys } from '@/hooks/queryKeys'
import { useAuth } from '@/hooks/useAuth'
import { adminApi, type ErrorLogsResponse, type SystemHealth } from '@/services/admin/adminApi'

/**
 * Query hook for fetching system health status (admin only).
 *
 * Automatically re-fetches every 60 seconds so the dashboard stays current
 * without manual refresh. Query is disabled until auth has loaded and the
 * user is signed in. Degraded or unhealthy responses are treated as
 * successful query results — the caller inspects `data.status` to render
 * the appropriate indicator.
 *
 * @returns React Query result containing `SystemHealth` on success
 */
export function useSystemHealth(): UseQueryResult<SystemHealth, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.admin.systemHealth(),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.getSystemHealth(token)
    },
    enabled: auth.isLoaded && auth.isSignedIn === true,
    refetchInterval: 60_000,
  })
}

/**
 * Query hook for fetching recent application error logs (admin only).
 *
 * Fetches a JWT token on each request and throws 'Authentication required'
 * before calling the API when the token is unavailable. The `limit` parameter
 * is clamped to [1, 100] and floored so the API always receives a safe
 * integer. Results are cached under `queryKeys.admin.errorLogs(limit)` so
 * different limit values store independently.
 *
 * @param options - Query options
 * @param options.limit - Maximum number of log entries to return (default: 50)
 * @returns React Query result containing `ErrorLogsResponse` on success
 */
export function useErrorLogs({ limit = 50 } = {}): UseQueryResult<ErrorLogsResponse, Error> {
  const auth = useAuth()

  const safeLimit = Math.min(100, Math.max(1, Math.floor(limit)))

  return useQuery({
    queryKey: queryKeys.admin.errorLogs(safeLimit),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.getErrorLogs(safeLimit, token)
    },
    enabled: auth.isLoaded && auth.isSignedIn === true,
  })
}
