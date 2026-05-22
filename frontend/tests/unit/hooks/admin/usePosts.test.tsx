import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { usePosts, useUnpublishPost } from '@/hooks/admin/usePosts'
import type { AdminPost, PostsResponse, UnpublishPostResponse } from '@/services/admin/adminApi'
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
 * Test suite for admin usePosts hooks.
 *
 * Verifies that usePosts fetches paginated post data through adminApi with
 * correct pagination params and cache keys, and that useUnpublishPost
 * mutates with a valid post ID, invalidates the admin cache on success, and
 * propagates errors without invalidating cache on failure.
 */
describe('admin usePosts hooks', () => {
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

  const mockPost: AdminPost = {
    id: 1,
    slug: 'hello-world',
    title: 'Hello World',
    author: 'Admin User',
    author_id: 42,
    published_at: '2026-01-15T12:00:00Z',
    created_at: '2026-01-10T09:00:00Z',
  }

  const mockPostsResponse: PostsResponse = {
    posts: [
      mockPost,
      {
        id: 2,
        slug: 'second-post',
        title: 'Second Post',
        author: 'Regular User',
        author_id: 7,
        published_at: '2026-02-01T08:00:00Z',
        created_at: '2026-01-28T14:30:00Z',
      },
    ],
    total_count: 2,
    total_pages: 1,
    page: 1,
    limit: 50,
  }

  const mockUnpublishResponse: UnpublishPostResponse = {
    message: 'Post unpublished successfully',
    post_id: 1,
  }

  /**
   * Tests for usePosts()
   *
   * Admin-only query. Must validate a JWT token before calling the API.
   * Cache key must include pagination params so different pages are stored
   * under distinct entries. Query is disabled until auth is loaded and user
   * is signed in.
   */
  describe('usePosts', () => {
    it('should fetch posts with default pagination (page=1, limit=50)', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getPosts).toHaveBeenCalledWith(1, 50, 'mock-admin-token')
      expect(adminApi.getPosts).toHaveBeenCalledTimes(1)
    })

    it('should fetch posts with custom page and limit parameters', async () => {
      const page2Response: PostsResponse = { ...mockPostsResponse, page: 2, limit: 10 }
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(page2Response)

      const { result } = renderHook(() => usePosts({ page: 2, limit: 10 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getPosts).toHaveBeenCalledWith(2, 10, 'mock-admin-token')
    })

    it('should return PostsResponse with posts array and pagination metadata', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockPostsResponse)
      expect(result.current.data?.posts).toHaveLength(2)
      expect(result.current.data?.total_count).toBe(2)
      expect(result.current.data?.total_pages).toBe(1)
      expect(result.current.data?.page).toBe(1)
      expect(result.current.data?.limit).toBe(50)
    })

    it('should return loading state initially while fetch is pending', () => {
      vi.mocked(adminApi.getPosts).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when API call fails', async () => {
      const apiError = new Error('Forbidden')
      vi.mocked(adminApi.getPosts).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

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

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.getPosts).not.toHaveBeenCalled()
    })

    it('should not fetch when auth is not yet loaded', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => 'mock-admin-token'),
        isSignedIn: true,
        isLoaded: false,
        user: null,
        role: 'admin',
      })

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      expect(result.current.isFetching).toBe(false)
      expect(result.current.isLoading).toBe(false)
      expect(adminApi.getPosts).not.toHaveBeenCalled()
    })

    it('should not fetch when user is not signed in', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: false,
        isLoaded: true,
        user: null,
        role: 'authenticated',
      })

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      expect(result.current.isFetching).toBe(false)
      expect(result.current.isLoading).toBe(false)
      expect(adminApi.getPosts).not.toHaveBeenCalled()
    })

    it('should fetch when auth is loaded and user is signed in', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.getPosts).toHaveBeenCalledTimes(1)
    })

    it('should cache data under ["admin", "posts", { page, limit }] key', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      const { result } = renderHook(() => usePosts({ page: 1, limit: 50 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cached = queryClient.getQueryData(['admin', 'posts', { page: 1, limit: 50 }])
      expect(cached).toEqual(mockPostsResponse)
    })

    it('should store separate cache entries for different page/limit combinations', async () => {
      const page1Response: PostsResponse = { ...mockPostsResponse, page: 1 }
      const page2Response: PostsResponse = {
        posts: [
          {
            id: 3,
            slug: 'third-post',
            title: 'Third Post',
            author: 'Another User',
            author_id: 13,
            published_at: '2026-03-01T10:00:00Z',
            created_at: '2026-02-25T09:00:00Z',
          },
        ],
        total_count: 3,
        total_pages: 2,
        page: 2,
        limit: 2,
      }

      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(page1Response)

      const { result: page1Result } = renderHook(() => usePosts({ page: 1, limit: 2 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(page1Result.current.isSuccess).toBe(true))

      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(page2Response)

      const { result: page2Result } = renderHook(() => usePosts({ page: 2, limit: 2 }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(page2Result.current.isSuccess).toBe(true))

      const cached1 = queryClient.getQueryData(['admin', 'posts', { page: 1, limit: 2 }])
      const cached2 = queryClient.getQueryData(['admin', 'posts', { page: 2, limit: 2 }])

      expect(cached1).toEqual(page1Response)
      expect(cached2).toEqual(page2Response)
      expect(cached1).not.toEqual(cached2)
    })

    it('should clamp page less than 1 to 1', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      renderHook(() => usePosts({ page: -3, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getPosts).toHaveBeenCalledWith(1, 50, 'mock-admin-token'))
    })

    it('should clamp zero page to 1', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      renderHook(() => usePosts({ page: 0, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getPosts).toHaveBeenCalledWith(1, 50, 'mock-admin-token'))
    })

    it('should cap limit at 100 to prevent over-fetching', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      renderHook(() => usePosts({ page: 1, limit: 9999 }), { wrapper: createWrapper() })

      await waitFor(() =>
        expect(adminApi.getPosts).toHaveBeenCalledWith(1, 100, 'mock-admin-token')
      )
    })

    it('should clamp zero limit to 1', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      renderHook(() => usePosts({ page: 1, limit: 0 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getPosts).toHaveBeenCalledWith(1, 1, 'mock-admin-token'))
    })

    it('should floor fractional page values', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      renderHook(() => usePosts({ page: 3.7, limit: 50 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getPosts).toHaveBeenCalledWith(3, 50, 'mock-admin-token'))
    })

    it('should floor fractional limit values', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)

      renderHook(() => usePosts({ page: 1, limit: 25.9 }), { wrapper: createWrapper() })

      await waitFor(() => expect(adminApi.getPosts).toHaveBeenCalledWith(1, 25, 'mock-admin-token'))
    })

    it('should handle empty posts list gracefully', async () => {
      const emptyResponse: PostsResponse = {
        posts: [],
        total_count: 0,
        total_pages: 0,
        page: 1,
        limit: 50,
      }
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(emptyResponse)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.posts).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })

    it('should propagate 401 Unauthorized error from API', async () => {
      const unauthorizedError = {
        isAxiosError: true,
        response: { status: 401, data: { error: 'Unauthorized' } },
      }
      vi.mocked(adminApi.getPosts).mockRejectedValueOnce(unauthorizedError)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should propagate 403 Forbidden error from API', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.getPosts).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate 404 Not Found error from API', async () => {
      const notFoundError = {
        isAxiosError: true,
        response: { status: 404, data: { error: 'Not found' } },
      }
      vi.mocked(adminApi.getPosts).mockRejectedValueOnce(notFoundError)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should propagate 500 Internal Server Error from API', async () => {
      const serverError = {
        isAxiosError: true,
        response: { status: 500, data: { error: 'Internal Server Error' } },
      }
      vi.mocked(adminApi.getPosts).mockRejectedValueOnce(serverError)

      const { result } = renderHook(() => usePosts(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })

  /**
   * Tests for useUnpublishPost()
   *
   * Admin-only authenticated mutation. Token must be validated before the
   * API call. Cache for ['admin', 'posts'] (and all admin queries) must be
   * invalidated on success so subsequent queries reload fresh data. No cache
   * invalidation occurs when the mutation fails.
   */
  describe('useUnpublishPost', () => {
    it('should call adminApi.unpublishPost with postId and token', async () => {
      vi.mocked(adminApi.unpublishPost).mockResolvedValueOnce(mockUnpublishResponse)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(adminApi.unpublishPost).toHaveBeenCalledWith(1, 'mock-admin-token')
      expect(adminApi.unpublishPost).toHaveBeenCalledTimes(1)
    })

    it('should return UnpublishPostResponse on success', async () => {
      vi.mocked(adminApi.unpublishPost).mockResolvedValueOnce(mockUnpublishResponse)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockUnpublishResponse)
      expect(result.current.data?.post_id).toBe(1)
      expect(result.current.data?.message).toBe('Post unpublished successfully')
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

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(adminApi.unpublishPost).not.toHaveBeenCalled()
    })

    it("should invalidate ['admin', 'users'] cache on success", async () => {
      const { queryKeys } = await import('@/hooks/queryKeys')
      vi.mocked(adminApi.unpublishPost).mockResolvedValueOnce(mockUnpublishResponse)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: queryKeys.admin.all(),
      })
    })

    it('should not invalidate a specific post cache entry on success', async () => {
      vi.mocked(adminApi.unpublishPost).mockResolvedValueOnce(mockUnpublishResponse)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const specificPostInvalidations = invalidateSpy.mock.calls.filter(
        ([options]) =>
          Array.isArray((options as { queryKey?: unknown }).queryKey) &&
          (options as { queryKey?: unknown[] }).queryKey?.includes(1)
      )
      expect(specificPostInvalidations).toHaveLength(0)
    })

    it('should not invalidate cache when mutation fails', async () => {
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(new Error('Not Found'))
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
    })

    it('should return error state with proper error on API failure', async () => {
      const apiError = new Error('Post not found')
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(apiError)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(apiError)
      expect(result.current.data).toBeUndefined()
    })

    it('should be in pending state during mutation', async () => {
      vi.mocked(adminApi.unpublishPost).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })

    it('should propagate 401 Unauthorized error', async () => {
      const unauthorizedError = {
        isAxiosError: true,
        response: { status: 401, data: { error: 'Unauthorized' } },
      }
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(unauthorizedError)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should propagate 403 Forbidden error when caller lacks admin role', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 2 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate 404 Not Found error for unknown postId', async () => {
      const notFoundError = {
        isAxiosError: true,
        response: { status: 404, data: { error: 'Post not found' } },
      }
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(notFoundError)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should propagate 409 Conflict error when post is already unpublished', async () => {
      const conflictError = {
        isAxiosError: true,
        response: { status: 409, data: { error: 'Post is already unpublished' } },
      }
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(conflictError)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 5 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 409 },
      })
    })

    it('should handle multiple sequential unpublish calls correctly', async () => {
      const firstResponse: UnpublishPostResponse = {
        message: 'Post unpublished successfully',
        post_id: 1,
      }
      const secondResponse: UnpublishPostResponse = {
        message: 'Post unpublished successfully',
        post_id: 2,
      }

      vi.mocked(adminApi.unpublishPost)
        .mockResolvedValueOnce(firstResponse)
        .mockResolvedValueOnce(secondResponse)

      const { result } = renderHook(() => useUnpublishPost(), { wrapper: createWrapper() })

      result.current.mutate({ postId: 1 })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(result.current.data?.post_id).toBe(1)

      result.current.mutate({ postId: 2 })
      await waitFor(() => expect(result.current.data?.post_id).toBe(2))

      expect(adminApi.unpublishPost).toHaveBeenCalledTimes(2)
      expect(adminApi.unpublishPost).toHaveBeenNthCalledWith(1, 1, 'mock-admin-token')
      expect(adminApi.unpublishPost).toHaveBeenNthCalledWith(2, 2, 'mock-admin-token')
    })
  })

  /**
   * Integration: both hooks coexist in the same QueryClient context.
   *
   * Verifies that a successful unpublish invalidates the posts query cache,
   * causing it to refetch automatically in a real component tree where both
   * hooks are mounted simultaneously.
   */
  describe('usePosts and useUnpublishPost integration', () => {
    it('should refetch posts after unpublish invalidates the cache', async () => {
      const initialResponse: PostsResponse = {
        ...mockPostsResponse,
        posts: [mockPost],
        total_count: 1,
      }
      const refreshedResponse: PostsResponse = {
        posts: [],
        total_count: 0,
        total_pages: 0,
        page: 1,
        limit: 50,
      }

      vi.mocked(adminApi.getPosts)
        .mockResolvedValueOnce(initialResponse)
        .mockResolvedValueOnce(refreshedResponse)

      vi.mocked(adminApi.unpublishPost).mockResolvedValueOnce(mockUnpublishResponse)

      const { result: postsResult } = renderHook(() => usePosts(), { wrapper: createWrapper() })
      await waitFor(() => expect(postsResult.current.isSuccess).toBe(true))
      expect(postsResult.current.data?.total_count).toBe(1)

      const { result: mutationResult } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      mutationResult.current.mutate({ postId: 1 })
      await waitFor(() => expect(mutationResult.current.isSuccess).toBe(true))

      await waitFor(() => expect(adminApi.getPosts).toHaveBeenCalledTimes(2))
    })

    it('should leave posts cache intact when unpublish mutation fails', async () => {
      vi.mocked(adminApi.getPosts).mockResolvedValueOnce(mockPostsResponse)
      vi.mocked(adminApi.unpublishPost).mockRejectedValueOnce(new Error('Conflict'))
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result: postsResult } = renderHook(() => usePosts(), { wrapper: createWrapper() })
      await waitFor(() => expect(postsResult.current.isSuccess).toBe(true))

      const { result: mutationResult } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      mutationResult.current.mutate({ postId: 1 })
      await waitFor(() => expect(mutationResult.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
      expect(adminApi.getPosts).toHaveBeenCalledTimes(1)
    })

    it('should not call adminApi.unpublishPost when token is null regardless of postId', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: false,
        isLoaded: true,
        user: null,
        role: 'authenticated',
      })

      const { result: mutationResult } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      mutationResult.current.mutate({ postId: 1 })
      await waitFor(() => expect(mutationResult.current.isError).toBe(true))

      expect(adminApi.unpublishPost).not.toHaveBeenCalled()
      expect(adminApi.getPosts).not.toHaveBeenCalled()
    })

    it('should handle parallel unpublish calls without corrupting cache invalidation', async () => {
      const firstResponse: UnpublishPostResponse = { message: 'Unpublished', post_id: 10 }
      const secondResponse: UnpublishPostResponse = { message: 'Unpublished', post_id: 11 }
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      vi.mocked(adminApi.unpublishPost)
        .mockResolvedValueOnce(firstResponse)
        .mockResolvedValueOnce(secondResponse)

      const { result: mutation1 } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })
      const { result: mutation2 } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      mutation1.current.mutate({ postId: 10 })
      mutation2.current.mutate({ postId: 11 })

      await waitFor(() => {
        expect(mutation1.current.isSuccess).toBe(true)
        expect(mutation2.current.isSuccess).toBe(true)
      })

      expect(adminApi.unpublishPost).toHaveBeenCalledTimes(2)
      expect(invalidateSpy).toHaveBeenCalledTimes(2)
    })
  })
})
