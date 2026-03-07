import type { AxiosError } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * Hoist the mock instance so it's available to the vi.mock factory
 */
const { mockAxiosInstance } = vi.hoisted(() => ({
  mockAxiosInstance: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

/**
 * Mock axios module for isolated unit testing
 */
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

import { commentsApi } from '@/services/commentsApi'

/**
 * Test suite for comments API client service
 *
 * Tests all 4 API methods with comprehensive coverage of:
 * - Correct HTTP methods and endpoints
 * - Authorization header injection (or intentional absence for public routes)
 * - Request body formatting
 * - Response type validation
 * - Query parameter handling
 * - Error handling and propagation including rate-limit responses
 */
describe('commentsApi', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  /**
   * Tests for listComments()
   * GET /api/posts/:slug/comments?skip=X&limit=Y
   *
   * This is a public endpoint — no Authorization header should be sent.
   */
  describe('listComments', () => {
    it('should call GET /api/posts/:slug/comments with skip and limit params', async () => {
      const mockResponse = {
        data: {
          comments: [
            {
              id: 1,
              post_id: 10,
              author_id: 42,
              text: 'Great post!',
              parent_id: null,
              created_at: '2026-03-01T10:00:00Z',
              updated_at: '2026-03-01T10:00:00Z',
              is_deleted: false,
              is_pending_moderation: false,
            },
          ],
          total_count: 1,
          has_more: false,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await commentsApi.listComments('test-post', 0, 50)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/posts/test-post/comments', {
        params: { skip: 0, limit: 50 },
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should call GET with custom skip and limit values', async () => {
      const mockResponse = {
        data: { comments: [], total_count: 100, has_more: true },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      await commentsApi.listComments('another-post', 50, 25)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/posts/another-post/comments', {
        params: { skip: 50, limit: 25 },
      })
    })

    it('should not send an Authorization header because the endpoint is public', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({
        data: { comments: [], total_count: 0, has_more: false },
      })

      await commentsApi.listComments('test-post', 0, 50)

      const callArg = mockAxiosInstance.get.mock.calls[0][1]
      expect(callArg).not.toHaveProperty('headers')
    })

    it('should return all comment fields from the response', async () => {
      const comment = {
        id: 7,
        post_id: 3,
        author_id: 99,
        text: 'Interesting take.',
        parent_id: null,
        created_at: '2026-03-02T08:00:00Z',
        updated_at: '2026-03-02T08:00:00Z',
        is_deleted: false,
        is_pending_moderation: true,
      }
      mockAxiosInstance.get.mockResolvedValueOnce({
        data: { comments: [comment], total_count: 1, has_more: false },
      })

      const result = await commentsApi.listComments('test-post', 0, 50)

      expect(result.comments[0]).toEqual(comment)
      expect(result.comments[0].is_pending_moderation).toBe(true)
    })

    it('should handle empty comment list', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({
        data: { comments: [], total_count: 0, has_more: false },
      })

      const result = await commentsApi.listComments('new-post', 0, 50)

      expect(result.comments).toEqual([])
      expect(result.total_count).toBe(0)
      expect(result.has_more).toBe(false)
    })

    it('should throw AxiosError when post not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Post not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(commentsApi.listComments('nonexistent-post', 0, 50)).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })
  })

  /**
   * Tests for postComment()
   * POST /api/posts/:slug/comments
   *
   * Requires authentication — Authorization header must be present.
   */
  describe('postComment', () => {
    it('should call POST /api/posts/:slug/comments with text body and Authorization header', async () => {
      const mockResponse = {
        data: {
          id: 5,
          post_id: 10,
          author_id: 42,
          text: 'This is my comment.',
          parent_id: null,
          created_at: '2026-03-01T12:00:00Z',
          updated_at: '2026-03-01T12:00:00Z',
          is_deleted: false,
          is_pending_moderation: false,
        },
      }

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await commentsApi.postComment('test-post', 'This is my comment.', 'mock-token')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/posts/test-post/comments',
        { text: 'This is my comment.' },
        { headers: { Authorization: 'Bearer mock-token' } }
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('should return the created comment with all fields', async () => {
      const created = {
        id: 12,
        post_id: 3,
        author_id: 7,
        text: 'Hello world.',
        parent_id: null,
        created_at: '2026-03-05T09:00:00Z',
        updated_at: '2026-03-05T09:00:00Z',
        is_deleted: false,
        is_pending_moderation: false,
      }
      mockAxiosInstance.post.mockResolvedValueOnce({ data: created })

      const result = await commentsApi.postComment('a-post', 'Hello world.', 'token')

      expect(result).toEqual(created)
      expect(result.id).toBe(12)
    })

    it('should throw AxiosError when token is missing or invalid (401 Unauthorized)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 401,
          data: { error: 'Unauthorized' },
          statusText: 'Unauthorized',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 401',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(commentsApi.postComment('test-post', 'text', 'bad-token')).rejects.toMatchObject(
        {
          isAxiosError: true,
          response: { status: 401 },
        }
      )
    })

    it('should throw AxiosError when post not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Post not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(
        commentsApi.postComment('nonexistent-post', 'text', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError with retry_after when rate limited (429 Too Many Requests)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 429,
          data: { error: 'Rate limit exceeded', retry_after: 30 },
          statusText: 'Too Many Requests',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 429',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(commentsApi.postComment('test-post', 'text', 'token')).rejects.toMatchObject({
        isAxiosError: true,
        response: {
          status: 429,
          data: { retry_after: 30 },
        },
      })
    })
  })

  /**
   * Tests for deleteComment()
   * DELETE /api/posts/:slug/comments/:id
   *
   * Returns void (204 No Content) on success.
   * Requires authentication — Authorization header must be present.
   */
  describe('deleteComment', () => {
    it('should call DELETE /api/posts/:slug/comments/:id with Authorization header', async () => {
      mockAxiosInstance.delete.mockResolvedValueOnce({ status: 204, data: null })

      await commentsApi.deleteComment('test-post', 5, 'mock-token')

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/posts/test-post/comments/5', {
        headers: { Authorization: 'Bearer mock-token' },
      })
    })

    it('should return void (undefined) on 204 response', async () => {
      mockAxiosInstance.delete.mockResolvedValueOnce({ status: 204, data: null })

      const result = await commentsApi.deleteComment('test-post', 5, 'mock-token')

      expect(result).toBeUndefined()
    })

    it('should throw AxiosError when token is missing or invalid (401 Unauthorized)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 401,
          data: { error: 'Unauthorized' },
          statusText: 'Unauthorized',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 401',
        name: 'AxiosError',
      }

      mockAxiosInstance.delete.mockRejectedValueOnce(mockError)

      await expect(commentsApi.deleteComment('test-post', 5, 'bad-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when comment not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Comment not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.delete.mockRejectedValueOnce(mockError)

      await expect(commentsApi.deleteComment('test-post', 9999, 'token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when user is not the comment owner (403 Forbidden)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 403,
          data: { error: 'Forbidden' },
          statusText: 'Forbidden',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 403',
        name: 'AxiosError',
      }

      mockAxiosInstance.delete.mockRejectedValueOnce(mockError)

      await expect(
        commentsApi.deleteComment('test-post', 5, 'other-users-token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })
  })

  /**
   * Tests for replyToComment()
   * POST /api/posts/:slug/comments/:id/reply
   *
   * Requires authentication — Authorization header must be present.
   */
  describe('replyToComment', () => {
    it('should call POST /api/posts/:slug/comments/:id/reply with text body and Authorization header', async () => {
      const mockResponse = {
        data: {
          id: 20,
          post_id: 10,
          author_id: 42,
          text: '@alice Great point!',
          parent_id: 5,
          created_at: '2026-03-01T13:00:00Z',
          updated_at: '2026-03-01T13:00:00Z',
          is_deleted: false,
          is_pending_moderation: false,
        },
      }

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await commentsApi.replyToComment(
        'test-post',
        5,
        '@alice Great point!',
        'mock-token'
      )

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/posts/test-post/comments/5/reply',
        { text: '@alice Great point!' },
        { headers: { Authorization: 'Bearer mock-token' } }
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('should return reply with parent_id set to the target comment id', async () => {
      const reply = {
        id: 21,
        post_id: 10,
        author_id: 42,
        text: '@bob agreed.',
        parent_id: 8,
        created_at: '2026-03-05T10:00:00Z',
        updated_at: '2026-03-05T10:00:00Z',
        is_deleted: false,
        is_pending_moderation: false,
      }
      mockAxiosInstance.post.mockResolvedValueOnce({ data: reply })

      const result = await commentsApi.replyToComment('test-post', 8, '@bob agreed.', 'token')

      expect(result.parent_id).toBe(8)
    })

    it('should throw AxiosError when token is missing or invalid (401 Unauthorized)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 401,
          data: { error: 'Unauthorized' },
          statusText: 'Unauthorized',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 401',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(
        commentsApi.replyToComment('test-post', 5, 'text', 'bad-token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when parent comment not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Comment not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(
        commentsApi.replyToComment('test-post', 9999, 'text', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError with retry_after when rate limited (429 Too Many Requests)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 429,
          data: { error: 'Rate limit exceeded', retry_after: 60 },
          statusText: 'Too Many Requests',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 429',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(
        commentsApi.replyToComment('test-post', 5, 'text', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: {
          status: 429,
          data: { retry_after: 60 },
        },
      })
    })
  })
})
