import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useComments, useDeleteComment } from '@/hooks/admin/useComments'
import { type AdminComment, adminApi, type CommentsResponse } from '@/services/admin/adminApi'

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
 * Test suite for admin useComments hooks.
 *
 * Verifies that useComments fetches paginated comment data through adminApi
 * with correct pagination params and cache keys, and that useDeleteComment
 * mutates with a valid comment ID, invalidates the admin cache on success,
 * and propagates errors without invalidating cache on failure.
 */
describe('admin useComments hooks', () => {
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

  const mockComment: AdminComment = {
    id: 1,
    text: 'Great post!',
    author: 'Alice',
    author_id: 10,
    post_title: 'Hello World',
    post_id: 5,
    created_at: '2026-03-01T10:00:00Z',
  }

  const mockCommentsResponse: CommentsResponse = {
    comments: [
      mockComment,
      {
        id: 2,
        text: 'Thanks for sharing.',
        author: 'Bob',
        author_id: 11,
        post_title: 'Hello World',
        post_id: 5,
        created_at: '2026-03-02T11:00:00Z',
      },
    ],
    total_count: 2,
    total_pages: 1,
    page: 1,
    limit: 50,
  }

  /**
   * Tests for useComments()
   *
   * Admin-only query. Requires a valid JWT token before calling the API.
   * Pagination params must be clamped and floored so the API always receives
   * safe integers. Cache key must include sanitised pagination params so
   * different pages are stored under distinct entries. Query must be disabled
   * until auth has loaded and the user is signed in.
   */
  describe('useComments', () => {
    it('should fetch with default params (page=1, limit=50)', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getComments).toHaveBeenCalledWith(1, 50, 'mock-admin-token')
      expect(adminApi.getComments).toHaveBeenCalledTimes(1)
    })

    it('should fetch with custom page and limit parameters', async () => {
      const page2Response: CommentsResponse = { ...mockCommentsResponse, page: 2, limit: 10 }
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(page2Response)

      const { result } = renderHook(() => useComments({ page: 2, limit: 10 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getComments).toHaveBeenCalledWith(2, 10, 'mock-admin-token')
    })

    it('should return CommentsResponse with comments array and pagination metadata', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockCommentsResponse)
      expect(result.current.data?.comments).toHaveLength(2)
      expect(result.current.data?.total_count).toBe(2)
      expect(result.current.data?.total_pages).toBe(1)
      expect(result.current.data?.page).toBe(1)
      expect(result.current.data?.limit).toBe(50)
    })

    it('should return loading state initially while fetch is pending', () => {
      vi.mocked(adminApi.getComments).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when API call fails', async () => {
      const apiError = new Error('Forbidden')
      vi.mocked(adminApi.getComments).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

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

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.getComments).not.toHaveBeenCalled()
    })

    it('should cache data under ["admin", "comments", { page, limit }] key', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      const { result } = renderHook(() => useComments({ page: 1, limit: 50 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cached = queryClient.getQueryData(['admin', 'comments', { page: 1, limit: 50 }])
      expect(cached).toEqual(mockCommentsResponse)
    })

    it('should store separate cache entries for different page/limit combinations', async () => {
      const page1Response: CommentsResponse = { ...mockCommentsResponse, page: 1 }
      const page2Response: CommentsResponse = {
        comments: [
          {
            id: 3,
            text: 'Another comment.',
            author: 'Carol',
            author_id: 12,
            post_title: 'Second Post',
            post_id: 6,
            created_at: '2026-03-05T09:00:00Z',
          },
        ],
        total_count: 3,
        total_pages: 2,
        page: 2,
        limit: 2,
      }

      vi.mocked(adminApi.getComments).mockResolvedValueOnce(page1Response)

      const { result: page1Result } = renderHook(() => useComments({ page: 1, limit: 2 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(page1Result.current.isSuccess).toBe(true))

      vi.mocked(adminApi.getComments).mockResolvedValueOnce(page2Response)

      const { result: page2Result } = renderHook(() => useComments({ page: 2, limit: 2 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(page2Result.current.isSuccess).toBe(true))

      const cached1 = queryClient.getQueryData(['admin', 'comments', { page: 1, limit: 2 }])
      const cached2 = queryClient.getQueryData(['admin', 'comments', { page: 2, limit: 2 }])

      expect(cached1).toEqual(page1Response)
      expect(cached2).toEqual(page2Response)
      expect(cached1).not.toEqual(cached2)
    })

    it('should clamp negative page to 1', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      renderHook(() => useComments({ page: -5, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getComments).toHaveBeenCalledWith(1, 50, 'mock-admin-token')
      )
    })

    it('should clamp zero limit to 1', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      renderHook(() => useComments({ page: 1, limit: 0 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getComments).toHaveBeenCalledWith(1, 1, 'mock-admin-token')
      )
    })

    it('should cap limit at 100 to prevent over-fetching', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      renderHook(() => useComments({ page: 1, limit: 9999 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getComments).toHaveBeenCalledWith(1, 100, 'mock-admin-token')
      )
    })

    it('should floor fractional page values', async () => {
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(mockCommentsResponse)

      renderHook(() => useComments({ page: 2.9, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getComments).toHaveBeenCalledWith(2, 50, 'mock-admin-token')
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

      renderHook(() => useComments(), { wrapper: createWrapper() })

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(adminApi.getComments).not.toHaveBeenCalled()
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

      renderHook(() => useComments(), { wrapper: createWrapper() })

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(adminApi.getComments).not.toHaveBeenCalled()
    })

    it('should handle an empty comments list gracefully', async () => {
      const emptyResponse: CommentsResponse = {
        comments: [],
        total_count: 0,
        total_pages: 0,
        page: 1,
        limit: 50,
      }
      vi.mocked(adminApi.getComments).mockResolvedValueOnce(emptyResponse)

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.comments).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })

    it('should propagate 403 Forbidden error from API', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.getComments).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

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
      vi.mocked(adminApi.getComments).mockRejectedValueOnce(serverError)

      const { result } = renderHook(() => useComments(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })

  /**
   * Tests for useDeleteComment()
   *
   * Admin-only authenticated mutation. Token must be validated before the
   * API call. The ['admin'] cache namespace must be invalidated on success
   * so all admin queries reload fresh data. No cache invalidation occurs
   * when the mutation fails, preserving stale data for retry scenarios.
   */
  describe('useDeleteComment', () => {
    it('should call adminApi.deleteComment with commentId and token', async () => {
      vi.mocked(adminApi.deleteComment).mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.deleteComment).toHaveBeenCalledWith(1, 'mock-admin-token')
      expect(adminApi.deleteComment).toHaveBeenCalledTimes(1)
    })

    it('should return undefined data after successful deletion', async () => {
      vi.mocked(adminApi.deleteComment).mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

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

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 1 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.deleteComment).not.toHaveBeenCalled()
    })

    it("should invalidate ['admin'] cache on successful deletion", async () => {
      const { queryKeys } = await import('@/hooks/queryKeys')
      vi.mocked(adminApi.deleteComment).mockResolvedValueOnce(undefined)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: queryKeys.admin.all(),
      })
    })

    it('should not invalidate cache when mutation fails', async () => {
      vi.mocked(adminApi.deleteComment).mockRejectedValueOnce(new Error('Not Found'))
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
    })

    it('should return error state with proper error on API failure', async () => {
      const apiError = new Error('Comment not found')
      vi.mocked(adminApi.deleteComment).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(apiError)
      expect(result.current.data).toBeUndefined()
    })

    it('should be in pending state during mutation', async () => {
      vi.mocked(adminApi.deleteComment).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 1 })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })

    it('should propagate 404 Not Found error for unknown commentId', async () => {
      const notFoundError = {
        isAxiosError: true,
        response: { status: 404, data: { error: 'Comment not found' } },
      }
      vi.mocked(adminApi.deleteComment).mockRejectedValueOnce(notFoundError)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should propagate 403 Forbidden error when caller lacks admin role', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.deleteComment).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ commentId: 2 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should handle multiple sequential deletions correctly', async () => {
      vi.mocked(adminApi.deleteComment)
        .mockResolvedValueOnce(undefined)
        .mockResolvedValueOnce(undefined)

      const { result: first } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })
      first.current.mutate({ commentId: 1 })
      await waitFor(() => expect(first.current.isSuccess).toBe(true))

      const { result: second } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })
      second.current.mutate({ commentId: 2 })
      await waitFor(() => expect(second.current.isSuccess).toBe(true))

      expect(adminApi.deleteComment).toHaveBeenCalledTimes(2)
      expect(adminApi.deleteComment).toHaveBeenNthCalledWith(1, 1, 'mock-admin-token')
      expect(adminApi.deleteComment).toHaveBeenNthCalledWith(2, 2, 'mock-admin-token')
    })
  })

  /**
   * Integration: useComments and useDeleteComment coexist in the same QueryClient.
   *
   * Verifies that a successful deletion invalidates the comments query cache,
   * causing it to refetch automatically when both hooks are mounted in the
   * same component tree, mirroring real admin dashboard behaviour.
   */
  describe('useComments and useDeleteComment integration', () => {
    it('should operate independently within the same QueryClient context', async () => {
      vi.mocked(adminApi.getComments)
        .mockResolvedValueOnce(mockCommentsResponse)
        .mockResolvedValueOnce(mockCommentsResponse)
      vi.mocked(adminApi.deleteComment).mockResolvedValueOnce(undefined)

      const { result: commentsResult } = renderHook(() => useComments(), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(commentsResult.current.isSuccess).toBe(true))

      const { result: deleteResult } = renderHook(() => useDeleteComment(), {
        wrapper: createWrapper(),
      })
      deleteResult.current.mutate({ commentId: 1 })
      await waitFor(() => expect(deleteResult.current.isSuccess).toBe(true))

      expect(adminApi.getComments).toHaveBeenCalledTimes(2)
      expect(adminApi.deleteComment).toHaveBeenCalledTimes(1)
    })

    it('should cause comments query to refetch after deleteComment invalidates the cache', async () => {
      const initialResponse: CommentsResponse = {
        ...mockCommentsResponse,
        comments: [mockComment, mockCommentsResponse.comments[1]],
      }
      const refreshedResponse: CommentsResponse = {
        ...mockCommentsResponse,
        comments: [mockCommentsResponse.comments[1]],
        total_count: 1,
      }

      vi.mocked(adminApi.getComments)
        .mockResolvedValueOnce(initialResponse)
        .mockResolvedValueOnce(refreshedResponse)

      vi.mocked(adminApi.deleteComment).mockResolvedValueOnce(undefined)

      const { result: commentsResult } = renderHook(() => useComments(), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(commentsResult.current.isSuccess).toBe(true))
      expect(commentsResult.current.data?.comments).toHaveLength(2)

      const { result: deleteResult } = renderHook(() => useDeleteComment(), {
        wrapper: createWrapper(),
      })
      deleteResult.current.mutate({ commentId: 1 })
      await waitFor(() => expect(deleteResult.current.isSuccess).toBe(true))

      await waitFor(() => expect(adminApi.getComments).toHaveBeenCalledTimes(2))
    })
  })
})
