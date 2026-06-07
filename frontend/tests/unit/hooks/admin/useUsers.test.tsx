import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useUpdateUserRole, useUsers } from '@/hooks/admin/useUsers'
import type { User, UserRole, UsersResponse } from '@/services/admin/adminApi'
import { adminApi } from '@/services/admin/adminApi'

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
 * Test suite for admin useUsers hooks.
 *
 * Verifies that useUsers fetches paginated user data through adminApi with
 * correct pagination params and cache keys, and that useUpdateUserRole
 * mutates with valid args, invalidates the users cache on success, and
 * propagates errors without invalidating cache on failure.
 */
describe('admin useUsers hooks', () => {
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
    vi.clearAllMocks()
    queryClient.clear()
  })

  const mockUser: User = {
    id: 1,
    clerk_id: 'clerk_abc123',
    email: 'admin@example.com',
    display_name: 'Admin User',
    role: 'admin',
    created_at: '2026-01-01T00:00:00Z',
    last_login: '2026-05-20T10:00:00Z',
  }

  const mockUsersResponse: UsersResponse = {
    users: [
      mockUser,
      {
        id: 2,
        clerk_id: 'clerk_def456',
        email: 'user@example.com',
        display_name: 'Regular User',
        role: 'authenticated',
        created_at: '2026-02-01T00:00:00Z',
        last_login: null,
      },
    ],
    total_count: 2,
    total_pages: 1,
    page: 1,
    limit: 50,
  }

  /**
   * Tests for useUsers()
   *
   * Admin-only query. Must validate a JWT token before calling the API.
   * Cache key must include pagination params so different pages are stored
   * under distinct entries.
   */
  describe('useUsers', () => {
    it('should fetch users with default pagination (page=1, limit=50)', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getUsers).toHaveBeenCalledWith(1, 50, 'mock-admin-token')
      expect(adminApi.getUsers).toHaveBeenCalledTimes(1)
    })

    it('should fetch users with custom page and limit parameters', async () => {
      const page2Response: UsersResponse = { ...mockUsersResponse, page: 2, limit: 10 }
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(page2Response)

      const { result } = renderHook(() => useUsers({ page: 2, limit: 10 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getUsers).toHaveBeenCalledWith(2, 10, 'mock-admin-token')
    })

    it('should return UsersResponse with users array and pagination metadata', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockUsersResponse)
      expect(result.current.data?.users).toHaveLength(2)
      expect(result.current.data?.total_count).toBe(2)
      expect(result.current.data?.total_pages).toBe(1)
      expect(result.current.data?.page).toBe(1)
      expect(result.current.data?.limit).toBe(50)
    })

    it('should return loading state initially while fetch is pending', () => {
      vi.mocked(adminApi.getUsers).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when API call fails', async () => {
      const apiError = new Error('Forbidden')
      vi.mocked(adminApi.getUsers).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

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

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.getUsers).not.toHaveBeenCalled()
    })

    it('should cache data under ["admin", "users", { page, limit }] key', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      const { result } = renderHook(() => useUsers({ page: 1, limit: 50 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cached = queryClient.getQueryData(['admin', 'users', { page: 1, limit: 50 }])
      expect(cached).toEqual(mockUsersResponse)
    })

    it('should store separate cache entries for different page/limit combinations', async () => {
      const page1Response: UsersResponse = { ...mockUsersResponse, page: 1 }
      const page2Response: UsersResponse = {
        users: [
          {
            id: 3,
            clerk_id: 'clerk_ghi789',
            email: 'third@example.com',
            display_name: 'Third User',
            role: 'authenticated',
            created_at: '2026-03-01T00:00:00Z',
            last_login: null,
          },
        ],
        total_count: 3,
        total_pages: 2,
        page: 2,
        limit: 2,
      }

      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(page1Response)

      const { result: page1Result } = renderHook(() => useUsers({ page: 1, limit: 2 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(page1Result.current.isSuccess).toBe(true))

      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(page2Response)

      const { result: page2Result } = renderHook(() => useUsers({ page: 2, limit: 2 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(page2Result.current.isSuccess).toBe(true))

      const cached1 = queryClient.getQueryData(['admin', 'users', { page: 1, limit: 2 }])
      const cached2 = queryClient.getQueryData(['admin', 'users', { page: 2, limit: 2 }])

      expect(cached1).toEqual(page1Response)
      expect(cached2).toEqual(page2Response)
      expect(cached1).not.toEqual(cached2)
    })

    it('should propagate 403 Forbidden error from API', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.getUsers).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

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
      vi.mocked(adminApi.getUsers).mockRejectedValueOnce(serverError)

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })

    it('should handle empty user list gracefully', async () => {
      const emptyResponse: UsersResponse = {
        users: [],
        total_count: 0,
        total_pages: 0,
        page: 1,
        limit: 50,
      }
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(emptyResponse)

      const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.users).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })

    it('should clamp negative page to 1', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      renderHook(() => useUsers({ page: -5, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getUsers).toHaveBeenCalledWith(1, 50, 'mock-admin-token'))
    })

    it('should clamp zero limit to 1', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      renderHook(() => useUsers({ page: 1, limit: 0 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getUsers).toHaveBeenCalledWith(1, 1, 'mock-admin-token'))
    })

    it('should cap limit at 100 to prevent over-fetching', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      renderHook(() => useUsers({ page: 1, limit: 9999 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getUsers).toHaveBeenCalledWith(1, 100, 'mock-admin-token')
      )
    })

    it('should floor fractional page values', async () => {
      vi.mocked(adminApi.getUsers).mockResolvedValueOnce(mockUsersResponse)

      renderHook(() => useUsers({ page: 2.9, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getUsers).toHaveBeenCalledWith(2, 50, 'mock-admin-token'))
    })
  })

  /**
   * Tests for useUpdateUserRole()
   *
   * Admin-only authenticated mutation. Token must be validated before the
   * API call. Cache for ['admin', 'users'] must be invalidated on success
   * so subsequent queries reload fresh data. No cache invalidation occurs
   * when the mutation fails.
   */
  describe('useUpdateUserRole', () => {
    const updatedUser: User = {
      ...mockUser,
      role: 'authenticated' as UserRole,
    }

    it('should call adminApi.updateUserRole with userId, role, and token', async () => {
      vi.mocked(adminApi.updateUserRole).mockResolvedValueOnce(updatedUser)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 1, role: 'authenticated' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.updateUserRole).toHaveBeenCalledWith(1, 'authenticated', 'mock-admin-token')
      expect(adminApi.updateUserRole).toHaveBeenCalledTimes(1)
    })

    it('should return the updated User record on success', async () => {
      vi.mocked(adminApi.updateUserRole).mockResolvedValueOnce(updatedUser)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 1, role: 'authenticated' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(updatedUser)
      expect(result.current.data?.role).toBe('authenticated')
      expect(result.current.data?.id).toBe(1)
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

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 1, role: 'authenticated' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.updateUserRole).not.toHaveBeenCalled()
    })

    it("should invalidate ['admin', 'users'] cache on success", async () => {
      const { queryKeys } = await import('@/hooks/queryKeys')
      vi.mocked(adminApi.updateUserRole).mockResolvedValueOnce(updatedUser)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 1, role: 'authenticated' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: queryKeys.admin.all(),
      })
    })

    it('should not invalidate cache when mutation fails', async () => {
      vi.mocked(adminApi.updateUserRole).mockRejectedValueOnce(new Error('Not Found'))
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 9999, role: 'admin' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
    })

    it('should return error state with proper error on API failure', async () => {
      const apiError = new Error('User not found')
      vi.mocked(adminApi.updateUserRole).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 9999, role: 'authenticated' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(apiError)
      expect(result.current.data).toBeUndefined()
    })

    it('should propagate 404 Not Found error for unknown userId', async () => {
      const notFoundError = {
        isAxiosError: true,
        response: { status: 404, data: { error: 'User not found' } },
      }
      vi.mocked(adminApi.updateUserRole).mockRejectedValueOnce(notFoundError)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 9999, role: 'admin' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should propagate 422 Unprocessable Entity error for invalid role', async () => {
      const validationError = {
        isAxiosError: true,
        response: { status: 422, data: { error: 'Invalid role value' } },
      }
      vi.mocked(adminApi.updateUserRole).mockRejectedValueOnce(validationError)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 1, role: 'superuser' as UserRole })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 422 },
      })
    })

    it('should propagate 403 Forbidden error when caller lacks admin role', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.updateUserRole).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 2, role: 'admin' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should be in pending state during mutation', async () => {
      vi.mocked(adminApi.updateUserRole).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 1, role: 'admin' })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })

    it('should accept admin role as valid role parameter', async () => {
      const promotedUser: User = { ...mockUser, role: 'admin' }
      vi.mocked(adminApi.updateUserRole).mockResolvedValueOnce(promotedUser)

      const { result } = renderHook(() => useUpdateUserRole(), { wrapper: createWrapper() })

      result.current.mutate({ userId: 2, role: 'admin' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.updateUserRole).toHaveBeenCalledWith(2, 'admin', 'mock-admin-token')
      expect(result.current.data?.role).toBe('admin')
    })
  })

  /**
   * Integration: both hooks coexist in the same QueryClient context.
   *
   * Verifies that a successful role update invalidates the users query
   * cache, causing it to refetch automatically in a real component tree
   * where both hooks are mounted simultaneously.
   */
  describe('useUsers and useUpdateUserRole integration', () => {
    it('should refetch users after role update invalidates the cache', async () => {
      const initialResponse: UsersResponse = {
        ...mockUsersResponse,
        users: [{ ...mockUser, role: 'authenticated' as UserRole }],
      }
      const refreshedResponse: UsersResponse = {
        ...mockUsersResponse,
        users: [{ ...mockUser, role: 'admin' as UserRole }],
      }
      const updatedUser: User = { ...mockUser, role: 'admin' }

      vi.mocked(adminApi.getUsers)
        .mockResolvedValueOnce(initialResponse)
        .mockResolvedValueOnce(refreshedResponse)

      vi.mocked(adminApi.updateUserRole).mockResolvedValueOnce(updatedUser)

      const { result: usersResult } = renderHook(() => useUsers(), { wrapper: createWrapper() })
      await waitFor(() => expect(usersResult.current.isSuccess).toBe(true))
      expect(usersResult.current.data?.users[0].role).toBe('authenticated')

      const { result: mutationResult } = renderHook(() => useUpdateUserRole(), {
        wrapper: createWrapper(),
      })

      mutationResult.current.mutate({ userId: 1, role: 'admin' })
      await waitFor(() => expect(mutationResult.current.isSuccess).toBe(true))

      await waitFor(() => expect(adminApi.getUsers).toHaveBeenCalledTimes(2))
    })

    it('should not call adminApi.updateUserRole when token is null regardless of userId', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValue({
        getToken: vi.fn(async () => null),
        isSignedIn: false,
        isLoaded: true,
        user: null,
        role: 'authenticated',
      })

      const { result: mutationResult } = renderHook(() => useUpdateUserRole(), {
        wrapper: createWrapper(),
      })

      mutationResult.current.mutate({ userId: 1, role: 'admin' })
      await waitFor(() => expect(mutationResult.current.isError).toBe(true))

      expect(adminApi.updateUserRole).not.toHaveBeenCalled()
      expect(adminApi.getUsers).not.toHaveBeenCalled()
    })
  })
})
