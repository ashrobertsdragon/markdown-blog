import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useErrorLogs, useSystemHealth } from '@/hooks/admin/useSystemHealth'
import { adminApi, type ErrorLogsResponse, type SystemHealth } from '@/services/admin/adminApi'

vi.mock('@/services/admin/adminApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-admin-token'),
    isSignedIn: true,
    isLoaded: true,
    user: null,
    role: 'admin',
  })),
}))

/**
 * Test suite for admin useSystemHealth and useErrorLogs hooks.
 *
 * Verifies that useSystemHealth fetches system health data with auto-refresh
 * and that useErrorLogs fetches error log entries with limit clamping and
 * cache key isolation.
 */
describe('admin useSystemHealth hooks', () => {
  let queryClient: QueryClient

  const createWrapper = () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    return wrapper
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
    queryClient.clear()
  })

  const mockSystemHealth: SystemHealth = {
    status: 'healthy',
    database: 'healthy',
    filesystem: 'healthy',
    github_api: 'healthy',
    uptime_seconds: 3600,
    checked_at: '2026-05-25T12:00:00Z',
  }

  const mockErrorLogsResponse: ErrorLogsResponse = {
    errors: [
      {
        id: 1,
        level: 'error',
        message: 'Database connection timeout',
        timestamp: '2026-05-25T11:55:00Z',
        context: { endpoint: '/api/posts' },
      },
      {
        id: 2,
        level: 'warning',
        message: 'GitHub API rate limit at 80%',
        timestamp: '2026-05-25T11:50:00Z',
        context: { remaining: 200 },
      },
    ],
    total_count: 2,
    limit: 50,
  }

  /**
   * Tests for useSystemHealth()
   *
   * Admin-only query. Requires a valid JWT token before calling the API.
   * Configured with refetchInterval of 60 seconds for auto-refresh.
   * Query is disabled until auth has loaded and the user is signed in.
   */
  describe('useSystemHealth', () => {
    it('should fetch system health on mount', async () => {
      vi.mocked(adminApi.getSystemHealth).mockResolvedValueOnce(mockSystemHealth)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getSystemHealth).toHaveBeenCalledWith('mock-admin-token')
      expect(adminApi.getSystemHealth).toHaveBeenCalledTimes(1)
    })

    it('should return full SystemHealth data on success', async () => {
      vi.mocked(adminApi.getSystemHealth).mockResolvedValueOnce(mockSystemHealth)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockSystemHealth)
      expect(result.current.data?.status).toBe('healthy')
      expect(result.current.data?.database).toBe('healthy')
      expect(result.current.data?.uptime_seconds).toBe(3600)
    })

    it('should return loading state initially while fetch is pending', () => {
      vi.mocked(adminApi.getSystemHealth).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when API call fails', async () => {
      const apiError = new Error('Service unavailable')
      vi.mocked(adminApi.getSystemHealth).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(apiError)
      expect(result.current.data).toBeUndefined()
    })

    it('should throw authentication error when token is unavailable', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: true,
        isLoaded: true,
        user: null,
        role: 'admin',
      })

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.getSystemHealth).not.toHaveBeenCalled()
    })

    it('should cache data under ["admin", "system-health"] key', async () => {
      vi.mocked(adminApi.getSystemHealth).mockResolvedValueOnce(mockSystemHealth)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cached = queryClient.getQueryData(['admin', 'system-health'])
      expect(cached).toEqual(mockSystemHealth)
    })

    it('should not execute query when isLoaded is false', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => 'mock-admin-token'),
        isSignedIn: true,
        isLoaded: false,
        user: null,
        role: 'admin',
      })

      renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(adminApi.getSystemHealth).not.toHaveBeenCalled()
    })

    it('should not execute query when isSignedIn is false', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => 'mock-admin-token'),
        isSignedIn: false,
        isLoaded: true,
        user: null,
        role: 'authenticated',
      })

      renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(adminApi.getSystemHealth).not.toHaveBeenCalled()
    })

    it('should handle degraded status without throwing', async () => {
      const degradedHealth: SystemHealth = {
        ...mockSystemHealth,
        status: 'degraded',
        github_api: 'degraded',
      }
      vi.mocked(adminApi.getSystemHealth).mockResolvedValueOnce(degradedHealth)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.status).toBe('degraded')
      expect(result.current.data?.github_api).toBe('degraded')
      expect(result.current.isError).toBe(false)
    })

    it('should handle unhealthy status without throwing', async () => {
      const unhealthyHealth: SystemHealth = {
        ...mockSystemHealth,
        status: 'unhealthy',
        database: 'unhealthy',
      }
      vi.mocked(adminApi.getSystemHealth).mockResolvedValueOnce(unhealthyHealth)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.status).toBe('unhealthy')
      expect(result.current.isError).toBe(false)
    })

    it('should propagate 403 Forbidden error from API', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.getSystemHealth).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate 500 Internal Server Error from API', async () => {
      const serverError = {
        isAxiosError: true,
        response: { status: 500, data: { error: 'Internal Server Error' } },
      }
      vi.mocked(adminApi.getSystemHealth).mockRejectedValueOnce(serverError)

      const { result } = renderHook(() => useSystemHealth(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })

  /**
   * Tests for useErrorLogs()
   *
   * Admin-only query. Requires a valid JWT token before calling the API.
   * Limit is clamped to [1, 100] and floored. Results are cached under
   * the `queryKeys.admin.errorLogs(limit)` key. Query is disabled until
   * auth has loaded and the user is signed in.
   */
  describe('useErrorLogs', () => {
    it('should fetch error logs with default limit (50)', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getErrorLogs).toHaveBeenCalledWith(50, 'mock-admin-token')
      expect(adminApi.getErrorLogs).toHaveBeenCalledTimes(1)
    })

    it('should fetch with a custom limit parameter', async () => {
      const customResponse: ErrorLogsResponse = { ...mockErrorLogsResponse, limit: 10 }
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(customResponse)

      const { result } = renderHook(() => useErrorLogs({ limit: 10 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getErrorLogs).toHaveBeenCalledWith(10, 'mock-admin-token')
    })

    it('should return ErrorLogsResponse with errors array and metadata', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockErrorLogsResponse)
      expect(result.current.data?.errors).toHaveLength(2)
      expect(result.current.data?.total_count).toBe(2)
      expect(result.current.data?.limit).toBe(50)
    })

    it('should return loading state initially while fetch is pending', () => {
      vi.mocked(adminApi.getErrorLogs).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when API call fails', async () => {
      const apiError = new Error('Forbidden')
      vi.mocked(adminApi.getErrorLogs).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(apiError)
    })

    it('should throw authentication error when token is unavailable', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: true,
        isLoaded: true,
        user: null,
        role: 'admin',
      })

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.getErrorLogs).not.toHaveBeenCalled()
    })

    it('should cache data under ["admin", "error-logs", { limit }] key', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      const { result } = renderHook(() => useErrorLogs({ limit: 50 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cached = queryClient.getQueryData(['admin', 'error-logs', { limit: 50 }])
      expect(cached).toEqual(mockErrorLogsResponse)
    })

    it('should store separate cache entries for different limit values', async () => {
      const limit10Response: ErrorLogsResponse = { ...mockErrorLogsResponse, limit: 10 }
      const limit25Response: ErrorLogsResponse = { ...mockErrorLogsResponse, limit: 25 }

      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(limit10Response)

      const { result: r10 } = renderHook(() => useErrorLogs({ limit: 10 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(r10.current.isSuccess).toBe(true))

      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(limit25Response)

      const { result: r25 } = renderHook(() => useErrorLogs({ limit: 25 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(r25.current.isSuccess).toBe(true))

      const cached10 = queryClient.getQueryData(['admin', 'error-logs', { limit: 10 }])
      const cached25 = queryClient.getQueryData(['admin', 'error-logs', { limit: 25 }])

      expect(cached10).toEqual(limit10Response)
      expect(cached25).toEqual(limit25Response)
      expect(cached10).not.toEqual(cached25)
    })

    it('should clamp limit of 0 to 1', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      renderHook(() => useErrorLogs({ limit: 0 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getErrorLogs).toHaveBeenCalledWith(1, 'mock-admin-token'))
    })

    it('should clamp negative limit to 1', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      renderHook(() => useErrorLogs({ limit: -10 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getErrorLogs).toHaveBeenCalledWith(1, 'mock-admin-token'))
    })

    it('should cap limit at 100 to prevent over-fetching', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      renderHook(() => useErrorLogs({ limit: 9999 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getErrorLogs).toHaveBeenCalledWith(100, 'mock-admin-token')
      )
    })

    it('should floor fractional limit values', async () => {
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(mockErrorLogsResponse)

      renderHook(() => useErrorLogs({ limit: 25.9 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getErrorLogs).toHaveBeenCalledWith(25, 'mock-admin-token')
      )
    })

    it('should not execute query when isLoaded is false', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => 'mock-admin-token'),
        isSignedIn: true,
        isLoaded: false,
        user: null,
        role: 'admin',
      })

      renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(adminApi.getErrorLogs).not.toHaveBeenCalled()
    })

    it('should not execute query when isSignedIn is false', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => 'mock-admin-token'),
        isSignedIn: false,
        isLoaded: true,
        user: null,
        role: 'authenticated',
      })

      renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(adminApi.getErrorLogs).not.toHaveBeenCalled()
    })

    it('should handle an empty errors list gracefully', async () => {
      const emptyResponse: ErrorLogsResponse = {
        errors: [],
        total_count: 0,
        limit: 50,
      }
      vi.mocked(adminApi.getErrorLogs).mockResolvedValueOnce(emptyResponse)

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.errors).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })

    it('should propagate 403 Forbidden error from API', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.getErrorLogs).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate 500 Internal Server Error from API', async () => {
      const serverError = {
        isAxiosError: true,
        response: { status: 500, data: { error: 'Internal Server Error' } },
      }
      vi.mocked(adminApi.getErrorLogs).mockRejectedValueOnce(serverError)

      const { result } = renderHook(() => useErrorLogs(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })
})
