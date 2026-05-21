import type { AxiosError } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * Hoist the mock instance so it's available to the vi.mock factory.
 * All admin API methods require token auth, so every HTTP verb is needed.
 */
const { mockAxiosInstance } = vi.hoisted(() => ({
  mockAxiosInstance: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

/**
 * Mock axios module for isolated unit testing.
 * adminApi reuses the shared apiClient from postsApi, which calls axios.create().
 */
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

import { adminApi } from '@/services/admin/adminApi'

/**
 * Test suite for the admin API client service.
 *
 * Covers all 7 admin API methods:
 * - getUsers         GET  /api/admin/users
 * - updateUserRole   PUT  /api/admin/users/:id/role
 * - getUserActivity  GET  /api/admin/users/:id/activity
 * - unpublishPost    POST /api/admin/posts/:id/unpublish
 * - deleteComment    DELETE /api/admin/comments/:id
 * - getSystemHealth  GET  /api/admin/system/health
 * - getErrorLogs     GET  /api/admin/system/errors
 *
 * Each test group verifies:
 * - Correct HTTP method and URL
 * - Bearer token in Authorization header
 * - Request body / query params formatted correctly
 * - Response data returned without wrapping
 * - AxiosError propagated unchanged for HTTP error responses
 * - Network errors (no response) propagated unchanged
 */
describe('adminApi', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  // ---------------------------------------------------------------------------
  // getUsers — GET /api/admin/users
  // ---------------------------------------------------------------------------

  /**
   * Tests for getUsers(page, limit, token)
   * GET /api/admin/users?page=X&limit=Y
   */
  describe('getUsers', () => {
    it('should call GET /api/admin/users with page, limit, and Authorization header', async () => {
      const mockResponse = {
        data: {
          users: [
            {
              id: 1,
              clerk_id: 'user_abc123',
              email: 'alice@example.com',
              display_name: 'Alice',
              role: 'authenticated',
              created_at: '2026-01-01T10:00:00Z',
              last_login: '2026-05-01T08:00:00Z',
            },
            {
              id: 2,
              clerk_id: 'user_def456',
              email: 'bob@example.com',
              display_name: 'Bob',
              role: 'admin',
              created_at: '2026-01-02T10:00:00Z',
              last_login: '2026-05-10T09:00:00Z',
            },
          ],
          total_count: 2,
          total_pages: 1,
          page: 1,
          limit: 20,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getUsers(1, 20, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/users', {
        params: { page: 1, limit: 20 },
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
      expect(result).toEqual(mockResponse.data)
      expect(result.users).toHaveLength(2)
    })

    it('should send custom page and limit as query params', async () => {
      const mockResponse = {
        data: {
          users: [],
          total_count: 100,
          total_pages: 10,
          page: 3,
          limit: 10,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getUsers(3, 10, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/users', {
        params: { page: 3, limit: 10 },
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
      expect(result.page).toBe(3)
      expect(result.limit).toBe(10)
    })

    it('should handle an empty user list', async () => {
      const mockResponse = {
        data: {
          users: [],
          total_count: 0,
          total_pages: 0,
          page: 1,
          limit: 20,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getUsers(1, 20, 'mock-jwt-token')

      expect(result.users).toEqual([])
      expect(result.total_count).toBe(0)
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getUsers(1, 20, 'invalid-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 403,
          data: { error: 'Forbidden: admin role required' },
          statusText: 'Forbidden',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 403',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getUsers(1, 20, 'non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate network errors with no response', async () => {
      const networkError = new Error('Network Error')

      mockAxiosInstance.get.mockRejectedValueOnce(networkError)

      await expect(adminApi.getUsers(1, 20, 'mock-jwt-token')).rejects.toThrow('Network Error')
    })
  })

  // ---------------------------------------------------------------------------
  // updateUserRole — PUT /api/admin/users/:id/role
  // ---------------------------------------------------------------------------

  /**
   * Tests for updateUserRole(userId, role, token)
   * PUT /api/admin/users/:id/role  body: { role }
   */
  describe('updateUserRole', () => {
    it('should call PUT /api/admin/users/:id/role with role body and Authorization header', async () => {
      const mockResponse = {
        data: {
          id: 7,
          clerk_id: 'user_ghi789',
          email: 'carol@example.com',
          display_name: 'Carol',
          role: 'admin',
          created_at: '2026-02-01T10:00:00Z',
          last_login: '2026-05-15T12:00:00Z',
        },
      }

      mockAxiosInstance.put.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.updateUserRole(7, 'admin', 'mock-jwt-token')

      expect(mockAxiosInstance.put).toHaveBeenCalledWith(
        '/admin/users/7/role',
        { role: 'admin' },
        { headers: { Authorization: 'Bearer mock-jwt-token' } }
      )
      expect(result).toEqual(mockResponse.data)
      expect(result.role).toBe('admin')
    })

    it('should send the updated role in the request body', async () => {
      const mockResponse = {
        data: {
          id: 3,
          clerk_id: 'user_jkl012',
          email: 'dave@example.com',
          display_name: 'Dave',
          role: 'authenticated',
          created_at: '2026-03-01T10:00:00Z',
          last_login: '2026-05-12T11:00:00Z',
        },
      }

      mockAxiosInstance.put.mockResolvedValueOnce(mockResponse)

      await adminApi.updateUserRole(3, 'authenticated', 'mock-jwt-token')

      const [, body] = mockAxiosInstance.put.mock.calls[0]
      expect(body).toEqual({ role: 'authenticated' })
    })

    it('should throw AxiosError when user not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'User not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.put.mockRejectedValueOnce(mockError)

      await expect(adminApi.updateUserRole(9999, 'admin', 'mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when role value is invalid (422 Unprocessable Entity)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 422,
          data: { error: 'Invalid role: must be "admin" or "authenticated"' },
          statusText: 'Unprocessable Entity',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 422',
        name: 'AxiosError',
      }

      mockAxiosInstance.put.mockRejectedValueOnce(mockError)

      await expect(adminApi.updateUserRole(1, 'superuser', 'mock-jwt-token')).rejects.toMatchObject(
        {
          isAxiosError: true,
          response: { status: 422 },
        }
      )
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

      mockAxiosInstance.put.mockRejectedValueOnce(mockError)

      await expect(adminApi.updateUserRole(1, 'admin', 'bad-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
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

      mockAxiosInstance.put.mockRejectedValueOnce(mockError)

      await expect(adminApi.updateUserRole(1, 'admin', 'non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })
  })

  // ---------------------------------------------------------------------------
  // getUserActivity — GET /api/admin/users/:id/activity
  // ---------------------------------------------------------------------------

  /**
   * Tests for getUserActivity(userId, token)
   * GET /api/admin/users/:id/activity
   */
  describe('getUserActivity', () => {
    it('should call GET /api/admin/users/:id/activity with Authorization header', async () => {
      const mockResponse = {
        data: {
          user_id: 5,
          last_login: '2026-05-18T09:00:00Z',
          post_count: 12,
          comment_count: 47,
          recent_posts: [
            {
              id: 101,
              slug: 'my-first-post',
              title: 'My First Post',
              published: true,
              created_at: '2026-04-01T10:00:00Z',
            },
          ],
          recent_comments: [
            {
              id: 201,
              post_slug: 'another-post',
              text: 'Great article!',
              created_at: '2026-05-10T14:00:00Z',
            },
          ],
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getUserActivity(5, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/users/5/activity', {
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
      expect(result).toEqual(mockResponse.data)
      expect(result.user_id).toBe(5)
      expect(result.post_count).toBe(12)
      expect(result.comment_count).toBe(47)
    })

    it('should return activity with empty recent_posts and recent_comments for new users', async () => {
      const mockResponse = {
        data: {
          user_id: 42,
          last_login: null,
          post_count: 0,
          comment_count: 0,
          recent_posts: [],
          recent_comments: [],
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getUserActivity(42, 'mock-jwt-token')

      expect(result.recent_posts).toEqual([])
      expect(result.recent_comments).toEqual([])
      expect(result.post_count).toBe(0)
      expect(result.last_login).toBeNull()
    })

    it('should throw AxiosError when user not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'User not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getUserActivity(9999, 'mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getUserActivity(5, 'invalid-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getUserActivity(5, 'non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate network errors with no response', async () => {
      const networkError = new Error('Network Error')

      mockAxiosInstance.get.mockRejectedValueOnce(networkError)

      await expect(adminApi.getUserActivity(5, 'mock-jwt-token')).rejects.toThrow('Network Error')
    })
  })

  // ---------------------------------------------------------------------------
  // unpublishPost — POST /api/admin/posts/:id/unpublish
  // ---------------------------------------------------------------------------

  /**
   * Tests for unpublishPost(postId, token)
   * POST /api/admin/posts/:id/unpublish
   */
  describe('unpublishPost', () => {
    it('should call POST /api/admin/posts/:id/unpublish with Authorization header', async () => {
      const mockResponse = {
        data: {
          message: 'Post unpublished successfully',
          post_id: 15,
        },
      }

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.unpublishPost(15, 'mock-jwt-token')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/admin/posts/15/unpublish',
        {},
        { headers: { Authorization: 'Bearer mock-jwt-token' } }
      )
      expect(result).toEqual(mockResponse.data)
      expect(result.message).toBe('Post unpublished successfully')
    })

    it('should send an empty body with the request', async () => {
      const mockResponse = {
        data: { message: 'Post unpublished successfully', post_id: 3 },
      }

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      await adminApi.unpublishPost(3, 'mock-jwt-token')

      const [, body] = mockAxiosInstance.post.mock.calls[0]
      expect(body).toEqual({})
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

      await expect(adminApi.unpublishPost(9999, 'mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when post is already unpublished (409 Conflict)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 409,
          data: { error: 'Post is not published' },
          statusText: 'Conflict',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 409',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(adminApi.unpublishPost(5, 'mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 409 },
      })
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

      await expect(adminApi.unpublishPost(15, 'bad-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
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

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(adminApi.unpublishPost(15, 'non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })
  })

  // ---------------------------------------------------------------------------
  // deleteComment — DELETE /api/admin/comments/:id
  // ---------------------------------------------------------------------------

  /**
   * Tests for deleteComment(commentId, token)
   * DELETE /api/admin/comments/:id
   * Returns void (204 No Content) on success.
   */
  describe('deleteComment', () => {
    it('should call DELETE /api/admin/comments/:id with Authorization header', async () => {
      mockAxiosInstance.delete.mockResolvedValueOnce({ status: 204, data: null })

      await adminApi.deleteComment(88, 'mock-jwt-token')

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/admin/comments/88', {
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
    })

    it('should return void (undefined) on successful deletion', async () => {
      mockAxiosInstance.delete.mockResolvedValueOnce({ status: 204, data: null })

      const result = await adminApi.deleteComment(10, 'mock-jwt-token')

      expect(result).toBeUndefined()
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

      await expect(adminApi.deleteComment(9999, 'mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
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

      await expect(adminApi.deleteComment(88, 'bad-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
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

      await expect(adminApi.deleteComment(88, 'non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should propagate network errors with no response', async () => {
      const networkError = new Error('Network Error')

      mockAxiosInstance.delete.mockRejectedValueOnce(networkError)

      await expect(adminApi.deleteComment(88, 'mock-jwt-token')).rejects.toThrow('Network Error')
    })
  })

  // ---------------------------------------------------------------------------
  // getSystemHealth — GET /api/admin/system/health
  // ---------------------------------------------------------------------------

  /**
   * Tests for getSystemHealth(token)
   * GET /api/admin/system/health
   */
  describe('getSystemHealth', () => {
    it('should call GET /api/admin/system/health with Authorization header', async () => {
      const mockResponse = {
        data: {
          status: 'healthy',
          database: 'healthy',
          filesystem: 'healthy',
          github_api: 'healthy',
          uptime_seconds: 86400,
          checked_at: '2026-05-20T12:00:00Z',
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getSystemHealth('mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/system/health', {
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
      expect(result).toEqual(mockResponse.data)
      expect(result.status).toBe('healthy')
      expect(result.uptime_seconds).toBe(86400)
    })

    it('should return degraded status when a subsystem is unhealthy', async () => {
      const mockResponse = {
        data: {
          status: 'degraded',
          database: 'healthy',
          filesystem: 'healthy',
          github_api: 'unhealthy',
          uptime_seconds: 3600,
          checked_at: '2026-05-20T12:00:00Z',
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getSystemHealth('mock-jwt-token')

      expect(result.status).toBe('degraded')
      expect(result.github_api).toBe('unhealthy')
    })

    it('should return unhealthy status when database is down', async () => {
      const mockResponse = {
        data: {
          status: 'unhealthy',
          database: 'unhealthy',
          filesystem: 'healthy',
          github_api: 'healthy',
          uptime_seconds: 120,
          checked_at: '2026-05-20T12:00:00Z',
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getSystemHealth('mock-jwt-token')

      expect(result.status).toBe('unhealthy')
      expect(result.database).toBe('unhealthy')
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getSystemHealth('invalid-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getSystemHealth('non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should throw AxiosError on server error (500 Internal Server Error)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 500,
          data: { error: 'Internal server error' },
          statusText: 'Internal Server Error',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 500',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getSystemHealth('mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })

    it('should propagate network errors with no response', async () => {
      const networkError = new Error('Network Error')

      mockAxiosInstance.get.mockRejectedValueOnce(networkError)

      await expect(adminApi.getSystemHealth('mock-jwt-token')).rejects.toThrow('Network Error')
    })
  })

  // ---------------------------------------------------------------------------
  // getErrorLogs — GET /api/admin/system/errors
  // ---------------------------------------------------------------------------

  /**
   * Tests for getErrorLogs(limit, token)
   * GET /api/admin/system/errors?limit=X
   */
  describe('getErrorLogs', () => {
    it('should call GET /api/admin/system/errors with limit param and Authorization header', async () => {
      const mockResponse = {
        data: {
          errors: [
            {
              id: 1,
              level: 'ERROR',
              message: 'Database connection timeout',
              timestamp: '2026-05-19T22:00:00Z',
              context: { service: 'database', retries: 3 },
            },
            {
              id: 2,
              level: 'WARNING',
              message: 'GitHub API rate limit approaching',
              timestamp: '2026-05-19T20:00:00Z',
              context: { remaining: 10, reset_at: '2026-05-19T21:00:00Z' },
            },
          ],
          total_count: 2,
          limit: 50,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getErrorLogs(50, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/system/errors', {
        params: { limit: 50 },
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
      expect(result).toEqual(mockResponse.data)
      expect(result.errors).toHaveLength(2)
    })

    it('should send the custom limit value as a query param', async () => {
      const mockResponse = {
        data: { errors: [], total_count: 0, limit: 10 },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      await adminApi.getErrorLogs(10, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/system/errors', {
        params: { limit: 10 },
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
    })

    it('should handle an empty error log list', async () => {
      const mockResponse = {
        data: { errors: [], total_count: 0, limit: 50 },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getErrorLogs(50, 'mock-jwt-token')

      expect(result.errors).toEqual([])
      expect(result.total_count).toBe(0)
    })

    it('should return error entries with level, message, timestamp, and context fields', async () => {
      const entry = {
        id: 99,
        level: 'ERROR',
        message: 'Unexpected exception in publish handler',
        timestamp: '2026-05-20T08:30:00Z',
        context: { post_id: 42, handler: 'publish_post_handler' },
      }
      const mockResponse = {
        data: { errors: [entry], total_count: 1, limit: 50 },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await adminApi.getErrorLogs(50, 'mock-jwt-token')

      expect(result.errors[0]).toEqual(entry)
      expect(result.errors[0].level).toBe('ERROR')
      expect(result.errors[0].context).toMatchObject({ post_id: 42 })
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getErrorLogs(50, 'invalid-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError when caller lacks admin role (403 Forbidden)', async () => {
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

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getErrorLogs(50, 'non-admin-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
      })
    })

    it('should throw AxiosError on server error (500 Internal Server Error)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 500,
          data: { error: 'Internal server error' },
          statusText: 'Internal Server Error',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 500',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(adminApi.getErrorLogs(50, 'mock-jwt-token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })

    it('should propagate network errors with no response', async () => {
      const networkError = new Error('Network Error')

      mockAxiosInstance.get.mockRejectedValueOnce(networkError)

      await expect(adminApi.getErrorLogs(50, 'mock-jwt-token')).rejects.toThrow('Network Error')
    })
  })
})
