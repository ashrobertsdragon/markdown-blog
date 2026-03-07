import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  useDeleteComment,
  useFetchComments,
  usePostComment,
  useReplyToComment,
} from '@/hooks/useComments'
import type { CommentResponse, ListCommentsResponse } from '@/services/commentsApi'
import { commentsApi } from '@/services/commentsApi'

vi.mock('@/services/commentsApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-token'),
    isSignedIn: true,
  })),
}))

/**
 * Test suite for useComments hooks
 *
 * Verifies that each hook correctly delegates to commentsApi, manages
 * React Query cache keys, and propagates errors — including rate-limit
 * responses — without coupling tests to implementation details.
 */
describe('useComments hooks', () => {
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

  /**
   * Tests for useFetchComments()
   *
   * Public query — no token needed. The hook should be disabled when
   * slug is empty to avoid unnecessary network requests.
   */
  describe('useFetchComments', () => {
    const mockListResponse: ListCommentsResponse = {
      comments: [
        {
          id: 1,
          post_id: 10,
          author_id: 42,
          text: 'First comment',
          parent_id: null,
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-01T10:00:00Z',
          is_deleted: false,
          is_pending_moderation: false,
        },
      ],
      total_count: 1,
      has_more: false,
    }

    it('should call commentsApi.listComments with slug, skip, and limit', async () => {
      vi.mocked(commentsApi.listComments).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useFetchComments('test-post', { skip: 0, limit: 50 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(commentsApi.listComments).toHaveBeenCalledWith('test-post', 0, 50)
      expect(commentsApi.listComments).toHaveBeenCalledTimes(1)
    })

    it('should use default skip=0 and limit=50 when options are omitted', async () => {
      vi.mocked(commentsApi.listComments).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useFetchComments('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(commentsApi.listComments).toHaveBeenCalledWith('test-post', 0, 50)
    })

    it('should return data on successful fetch', async () => {
      vi.mocked(commentsApi.listComments).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useFetchComments('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockListResponse)
      expect(result.current.data?.comments).toHaveLength(1)
    })

    it('should return loading state initially', () => {
      vi.mocked(commentsApi.listComments).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useFetchComments('test-post'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when fetch fails', async () => {
      const mockError = new Error('Post not found')
      vi.mocked(commentsApi.listComments).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useFetchComments('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
      expect(result.current.data).toBeUndefined()
    })

    it('should be disabled and not fetch when slug is empty', () => {
      const { result } = renderHook(() => useFetchComments(''), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(commentsApi.listComments).not.toHaveBeenCalled()
    })

    it('should cache under queryKey ["comments", slug, { skip, limit }]', async () => {
      vi.mocked(commentsApi.listComments).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useFetchComments('test-post', { skip: 10, limit: 25 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cached = queryClient.getQueryData(['comments', 'test-post', { skip: 10, limit: 25 }])
      expect(cached).toEqual(mockListResponse)
    })

    it('should handle empty comment list', async () => {
      const empty: ListCommentsResponse = { comments: [], total_count: 0, has_more: false }
      vi.mocked(commentsApi.listComments).mockResolvedValueOnce(empty)

      const { result } = renderHook(() => useFetchComments('new-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.comments).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })
  })

  /**
   * Tests for usePostComment()
   *
   * Authenticated mutation. The hook must throw when getToken returns null
   * rather than sending an unauthenticated request. Cache invalidation
   * must target the correct key on success.
   */
  describe('usePostComment', () => {
    const mockComment: CommentResponse = {
      id: 5,
      post_id: 10,
      author_id: 42,
      text: 'Hello!',
      parent_id: null,
      created_at: '2026-03-01T12:00:00Z',
      updated_at: '2026-03-01T12:00:00Z',
      is_deleted: false,
      is_pending_moderation: false,
    }

    it('should call commentsApi.postComment with slug, text, and token', async () => {
      vi.mocked(commentsApi.postComment).mockResolvedValueOnce(mockComment)

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(commentsApi.postComment).toHaveBeenCalledWith('test-post', 'Hello!', 'mock-token')
    })

    it('should return the created comment on success', async () => {
      vi.mocked(commentsApi.postComment).mockResolvedValueOnce(mockComment)

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockComment)
    })

    it('should throw when getToken returns null', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: true,
        isLoaded: true,
        user: null,
        role: 'authenticated',
      })

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(commentsApi.postComment).not.toHaveBeenCalled()
    })

    it('should invalidate ["comments", slug, {}] cache on success', async () => {
      vi.mocked(commentsApi.postComment).mockResolvedValueOnce(mockComment)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['comments', 'test-post', {}],
      })
    })

    it('should not invalidate cache on error', async () => {
      vi.mocked(commentsApi.postComment).mockRejectedValueOnce(new Error('Unauthorized'))
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
    })

    it('should propagate rate-limit error with retryAfter when 429', async () => {
      const rateLimitError = {
        isAxiosError: true,
        response: {
          status: 429,
          data: { error: 'Rate limit exceeded', retry_after: 30 },
        },
      }
      vi.mocked(commentsApi.postComment).mockRejectedValueOnce(rateLimitError)

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 429, data: { retry_after: 30 } },
      })
    })

    it('should be in pending state during mutation', async () => {
      vi.mocked(commentsApi.postComment).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => usePostComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', text: 'Hello!' })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })
  })

  /**
   * Tests for useDeleteComment()
   *
   * Authenticated mutation that returns void. Cache invalidation must
   * occur for the post's comment list regardless of pagination params.
   */
  describe('useDeleteComment', () => {
    it('should call commentsApi.deleteComment with slug, commentId, and token', async () => {
      vi.mocked(commentsApi.deleteComment).mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', commentId: 7 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(commentsApi.deleteComment).toHaveBeenCalledWith('test-post', 7, 'mock-token')
    })

    it('should invalidate comments cache for the post on success', async () => {
      vi.mocked(commentsApi.deleteComment).mockResolvedValueOnce(undefined)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', commentId: 7 })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(['comments', 'test-post']) })
      )
    })

    it('should propagate 403 Forbidden error', async () => {
      const forbiddenError = {
        isAxiosError: true,
        response: { status: 403, data: { error: 'Forbidden' } },
      }
      vi.mocked(commentsApi.deleteComment).mockRejectedValueOnce(forbiddenError)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', commentId: 7 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate 404 Not Found error', async () => {
      const notFoundError = {
        isAxiosError: true,
        response: { status: 404, data: { error: 'Comment not found' } },
      }
      vi.mocked(commentsApi.deleteComment).mockRejectedValueOnce(notFoundError)

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', commentId: 9999 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should not invalidate cache on error', async () => {
      vi.mocked(commentsApi.deleteComment).mockRejectedValueOnce(new Error('Forbidden'))
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useDeleteComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', commentId: 7 })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
    })
  })

  /**
   * Tests for useReplyToComment()
   *
   * Authenticated mutation. Rate-limit errors from the API must surface
   * unchanged so the UI layer can display the retry_after duration.
   */
  describe('useReplyToComment', () => {
    const mockReply: CommentResponse = {
      id: 20,
      post_id: 10,
      author_id: 42,
      text: '@alice agreed.',
      parent_id: 5,
      created_at: '2026-03-01T13:00:00Z',
      updated_at: '2026-03-01T13:00:00Z',
      is_deleted: false,
      is_pending_moderation: false,
    }

    it('should call commentsApi.replyToComment with slug, parentId, text, and token', async () => {
      vi.mocked(commentsApi.replyToComment).mockResolvedValueOnce(mockReply)

      const { result } = renderHook(() => useReplyToComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', parentId: 5, text: '@alice agreed.' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(commentsApi.replyToComment).toHaveBeenCalledWith(
        'test-post',
        5,
        '@alice agreed.',
        'mock-token'
      )
    })

    it('should return the created reply on success', async () => {
      vi.mocked(commentsApi.replyToComment).mockResolvedValueOnce(mockReply)

      const { result } = renderHook(() => useReplyToComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', parentId: 5, text: '@alice agreed.' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockReply)
      expect(result.current.data?.parent_id).toBe(5)
    })

    it('should invalidate comments cache for the post on success', async () => {
      vi.mocked(commentsApi.replyToComment).mockResolvedValueOnce(mockReply)
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useReplyToComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', parentId: 5, text: '@alice agreed.' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(['comments', 'test-post']) })
      )
    })

    it('should propagate rate-limit error with retry_after when 429', async () => {
      const rateLimitError = {
        isAxiosError: true,
        response: {
          status: 429,
          data: { error: 'Rate limit exceeded', retry_after: 60 },
        },
      }
      vi.mocked(commentsApi.replyToComment).mockRejectedValueOnce(rateLimitError)

      const { result } = renderHook(() => useReplyToComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', parentId: 5, text: 'text' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 429, data: { retry_after: 60 } },
      })
    })

    it('should propagate 404 error when parent comment does not exist', async () => {
      const notFoundError = {
        isAxiosError: true,
        response: { status: 404, data: { error: 'Comment not found' } },
      }
      vi.mocked(commentsApi.replyToComment).mockRejectedValueOnce(notFoundError)

      const { result } = renderHook(() => useReplyToComment(), { wrapper: createWrapper() })

      result.current.mutate({ slug: 'test-post', parentId: 9999, text: 'text' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })
  })
})
