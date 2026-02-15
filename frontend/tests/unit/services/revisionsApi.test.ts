import type { AxiosError } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * Hoist the mock instance so it's available to the vi.mock factory
 */
const { mockAxiosInstance } = vi.hoisted(() => ({
  mockAxiosInstance: {
    get: vi.fn(),
    post: vi.fn(),
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

import { revisionsApi } from '@/services/revisionsApi'

/**
 * Test suite for revisions API client service
 *
 * Tests all 4 API methods with comprehensive coverage of:
 * - Correct HTTP methods and endpoints
 * - Authorization header injection
 * - Request body formatting
 * - Response type validation
 * - Query parameter handling
 * - Error handling and propagation
 */
describe('revisionsApi', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  /**
   * Tests for listRevisions()
   * GET /api/posts/:slug/revisions
   */
  describe('listRevisions', () => {
    it('should call GET /api/posts/:slug/revisions with default pagination and Authorization header', async () => {
      const mockResponse = {
        data: {
          revisions: [
            {
              id: 'uuid-1',
              commit_sha: 'abc123def456789012345678901234567890abcd',
              short_sha: 'abc123d',
              author: { id: 'author-uuid-1', name: 'Author One' },
              timestamp: '2024-11-10T15:30:00Z',
              relative_time: '2 days ago',
              commit_message: 'Update introduction',
              is_revert: false,
            },
            {
              id: 'uuid-2',
              commit_sha: 'def456abc789012345678901234567890abcdef1',
              short_sha: 'def456a',
              author: { id: 'author-uuid-2', name: 'Author Two' },
              timestamp: '2024-11-09T14:20:00Z',
              relative_time: '3 days ago',
              commit_message: 'Fix typo in section 3',
              is_revert: false,
            },
          ],
          total_count: 42,
          has_more: true,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.listRevisions('test-post', 0, 20, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/posts/test-post/revisions', {
        params: { skip: 0, limit: 20 },
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })

      expect(result).toEqual(mockResponse.data)
      expect(result.revisions).toHaveLength(2)
      expect(result.total_count).toBe(42)
      expect(result.has_more).toBe(true)
    })

    it('should call GET /api/posts/:slug/revisions with custom pagination parameters', async () => {
      const mockResponse = {
        data: {
          revisions: [],
          total_count: 100,
          has_more: true,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      await revisionsApi.listRevisions('test-post', 40, 10, 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/posts/test-post/revisions', {
        params: { skip: 40, limit: 10 },
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
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

      await expect(
        revisionsApi.listRevisions('nonexistent-post', 0, 20, 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when user not authorized (403 Forbidden)', async () => {
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

      await expect(
        revisionsApi.listRevisions('another-users-post', 0, 20, 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
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

      await expect(
        revisionsApi.listRevisions('test-post', 0, 20, 'invalid-token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should handle empty revisions list correctly', async () => {
      const mockResponse = {
        data: {
          revisions: [],
          total_count: 0,
          has_more: false,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.listRevisions('new-post', 0, 20, 'mock-jwt-token')

      expect(result.revisions).toEqual([])
      expect(result.total_count).toBe(0)
      expect(result.has_more).toBe(false)
    })
  })

  /**
   * Tests for getRevision()
   * GET /api/posts/:slug/revisions/:sha
   */
  describe('getRevision', () => {
    it('should call GET /api/posts/:slug/revisions/:sha with Authorization header', async () => {
      const mockResponse = {
        data: {
          id: 'uuid-1',
          commit_sha: 'abc123def456789012345678901234567890abcd',
          short_sha: 'abc123d',
          author: { id: 'author-uuid-1', name: 'Author One' },
          timestamp: '2024-11-10T15:30:00Z',
          commit_message: 'Update post introduction',
          markdown_content: '# My Post\n\nThis is the updated introduction.',
          html_content: '<h1>My Post</h1>\n<p>This is the updated introduction.</p>',
          is_current: false,
          is_revert: false,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getRevision('test-post', 'abc123d', 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/posts/test-post/revisions/abc123d', {
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })

      expect(result).toEqual(mockResponse.data)
      expect(result.markdown_content).toBeTruthy()
      expect(result.html_content).toBeTruthy()
    })

    it('should handle current revision correctly (is_current: true)', async () => {
      const mockResponse = {
        data: {
          id: 'uuid-current',
          commit_sha: 'current123456789012345678901234567890abc',
          short_sha: 'current',
          author: { id: 'author-uuid-1', name: 'Author One' },
          timestamp: '2024-11-11T10:00:00Z',
          commit_message: 'Latest update',
          markdown_content: '# Current Version',
          html_content: '<h1>Current Version</h1>',
          is_current: true,
          is_revert: false,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getRevision('test-post', 'current', 'mock-jwt-token')

      expect(result.is_current).toBe(true)
    })

    it('should handle revert commit correctly (is_revert: true)', async () => {
      const mockResponse = {
        data: {
          id: 'uuid-revert',
          commit_sha: 'revert123456789012345678901234567890abc',
          short_sha: 'revert1',
          author: { id: 'author-uuid-1', name: 'Author One' },
          timestamp: '2024-11-10T16:00:00Z',
          commit_message: 'Revert to abc123d',
          markdown_content: '# Reverted Content',
          html_content: '<h1>Reverted Content</h1>',
          is_current: false,
          is_revert: true,
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getRevision('test-post', 'revert1', 'mock-jwt-token')

      expect(result.is_revert).toBe(true)
    })

    it('should throw AxiosError when revision not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Revision not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(
        revisionsApi.getRevision('test-post', 'nonexistent-sha', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when user not authorized (403 Forbidden)', async () => {
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

      await expect(
        revisionsApi.getRevision('another-users-post', 'abc123d', 'token')
      ).rejects.toMatchObject({
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

      await expect(revisionsApi.getRevision('test-post', 'abc123d', 'token')).rejects.toMatchObject(
        {
          isAxiosError: true,
          response: { status: 500 },
        }
      )
    })
  })

  /**
   * Tests for getDiff()
   * GET /api/posts/:slug/revisions/:sha1/diff/:sha2
   */
  describe('getDiff', () => {
    it('should call GET /api/posts/:slug/revisions/:sha1/diff/:sha2 with Authorization header', async () => {
      const mockResponse = {
        data: {
          from_revision: { sha: 'abc123d', timestamp: '2024-11-09T15:30:00Z' },
          to_revision: { sha: 'def456a', timestamp: '2024-11-10T15:30:00Z' },
          diff_lines: [
            { type: 'context', content: '# Introduction' },
            { type: 'deletion', content: '- Old paragraph explaining the concept.' },
            { type: 'addition', content: '+ New paragraph with updated explanation.' },
            { type: 'context', content: '' },
            { type: 'context', content: '## Section 2' },
          ],
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getDiff('test-post', 'abc123d', 'def456a', 'mock-jwt-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/posts/test-post/revisions/abc123d/diff/def456a',
        {
          headers: { Authorization: 'Bearer mock-jwt-token' },
        }
      )

      expect(result).toEqual(mockResponse.data)
      expect(result.diff_lines).toHaveLength(5)
      expect(result.from_revision.sha).toBe('abc123d')
      expect(result.to_revision.sha).toBe('def456a')
    })

    it('should handle diff with only additions', async () => {
      const mockResponse = {
        data: {
          from_revision: { sha: 'abc123d', timestamp: '2024-11-09T15:30:00Z' },
          to_revision: { sha: 'def456a', timestamp: '2024-11-10T15:30:00Z' },
          diff_lines: [
            { type: 'context', content: '# Title' },
            { type: 'addition', content: '+ New section added here.' },
            { type: 'addition', content: '+ Another new line.' },
          ],
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getDiff('test-post', 'abc123d', 'def456a', 'token')

      expect(result.diff_lines.filter(line => line.type === 'addition')).toHaveLength(2)
      expect(result.diff_lines.filter(line => line.type === 'deletion')).toHaveLength(0)
    })

    it('should handle diff with only deletions', async () => {
      const mockResponse = {
        data: {
          from_revision: { sha: 'abc123d', timestamp: '2024-11-09T15:30:00Z' },
          to_revision: { sha: 'def456a', timestamp: '2024-11-10T15:30:00Z' },
          diff_lines: [
            { type: 'context', content: '# Title' },
            { type: 'deletion', content: '- Removed line 1.' },
            { type: 'deletion', content: '- Removed line 2.' },
          ],
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getDiff('test-post', 'abc123d', 'def456a', 'token')

      expect(result.diff_lines.filter(line => line.type === 'deletion')).toHaveLength(2)
      expect(result.diff_lines.filter(line => line.type === 'addition')).toHaveLength(0)
    })

    it('should handle diff with no changes (only context)', async () => {
      const mockResponse = {
        data: {
          from_revision: { sha: 'abc123d', timestamp: '2024-11-09T15:30:00Z' },
          to_revision: { sha: 'abc123d', timestamp: '2024-11-09T15:30:00Z' },
          diff_lines: [
            { type: 'context', content: '# Title' },
            { type: 'context', content: 'Content here.' },
          ],
        },
      }

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.getDiff('test-post', 'abc123d', 'abc123d', 'token')

      expect(result.diff_lines.every(line => line.type === 'context')).toBe(true)
    })

    it('should throw AxiosError when revision not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Revision not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(
        revisionsApi.getDiff('test-post', 'invalid-sha', 'abc123d', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when user not authorized (403 Forbidden)', async () => {
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

      await expect(
        revisionsApi.getDiff('another-users-post', 'abc123d', 'def456a', 'token')
      ).rejects.toMatchObject({
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

      await expect(
        revisionsApi.getDiff('test-post', 'abc123d', 'def456a', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })

  /**
   * Tests for revertToRevision()
   * POST /api/posts/:slug/revert
   */
  describe('revertToRevision', () => {
    it('should call POST /api/posts/:slug/revert with target_sha and Authorization header', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Post reverted to abc123d',
          new_commit_sha: 'xyz789abc012345678901234567890abcdef123',
          redirect_url: '/edit/test-post',
        },
      }

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await revisionsApi.revertToRevision('test-post', 'abc123d', 'mock-jwt-token')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/posts/test-post/revert',
        { target_sha: 'abc123d' },
        { headers: { Authorization: 'Bearer mock-jwt-token' } }
      )

      expect(result).toEqual(mockResponse.data)
      expect(result.success).toBe(true)
      expect(result.new_commit_sha).toBeTruthy()
      expect(result.redirect_url).toBe('/edit/test-post')
    })

    it('should throw AxiosError when target revision not found (404 Not Found)', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Revision not found' },
          statusText: 'Not Found',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 404',
        name: 'AxiosError',
      }

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(
        revisionsApi.revertToRevision('test-post', 'nonexistent-sha', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 404 },
      })
    })

    it('should throw AxiosError when user not authorized (403 Forbidden)', async () => {
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

      await expect(
        revisionsApi.revertToRevision('another-users-post', 'abc123d', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 403 },
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

      await expect(
        revisionsApi.revertToRevision('test-post', 'abc123d', 'invalid-token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
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

      mockAxiosInstance.post.mockRejectedValueOnce(mockError)

      await expect(
        revisionsApi.revertToRevision('test-post', 'abc123d', 'token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })
})
