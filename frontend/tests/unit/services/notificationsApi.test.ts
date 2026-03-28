import type { AxiosError } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * Hoist the mock axios instance so it is available inside the vi.mock factory
 */
const { mockAxiosInstance } = vi.hoisted(() => ({
  mockAxiosInstance: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

import { notificationsApi } from '@/services/notificationsApi'

/**
 * Test suite for notifications API client service
 *
 * Covers GET preferences, PUT preferences, and error propagation for
 * all common HTTP error codes returned by the backend.
 */
describe('notificationsApi', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  /**
   * Tests for fetchNotificationPreferences()
   * GET /api/user/notification-preferences
   *
   * Requires authentication — Authorization header must be present.
   */
  describe('fetchNotificationPreferences', () => {
    const mockPreferences = {
      user_id: 1,
      notify_on_comment_replies: true,
      notify_on_mentions: false,
      notify_on_new_posts: true,
    }

    it('should call GET /api/user/notification-preferences with Authorization header', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({
        data: { preferences: mockPreferences },
      })

      const result = await notificationsApi.fetchNotificationPreferences('mock-token')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/user/notification-preferences', {
        headers: { Authorization: 'Bearer mock-token' },
      })
      expect(result).toEqual({ preferences: mockPreferences })
    })

    it('should return all preference fields from the response', async () => {
      mockAxiosInstance.get.mockResolvedValueOnce({
        data: { preferences: mockPreferences },
      })

      const result = await notificationsApi.fetchNotificationPreferences('token')

      expect(result.preferences.user_id).toBe(1)
      expect(result.preferences.notify_on_comment_replies).toBe(true)
      expect(result.preferences.notify_on_mentions).toBe(false)
      expect(result.preferences.notify_on_new_posts).toBe(true)
    })

    it('should throw AxiosError on 401 Unauthorized', async () => {
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
        notificationsApi.fetchNotificationPreferences('bad-token')
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError on 500 Internal Server Error', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 500,
          data: { error: 'Internal Server Error' },
          statusText: 'Internal Server Error',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 500',
        name: 'AxiosError',
      }

      mockAxiosInstance.get.mockRejectedValueOnce(mockError)

      await expect(notificationsApi.fetchNotificationPreferences('token')).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })

  /**
   * Tests for updateNotificationPreferences()
   * PUT /api/user/notification-preferences
   *
   * Requires authentication — Authorization header must be present.
   * Accepts partial updates so only provided keys need to be sent.
   */
  describe('updateNotificationPreferences', () => {
    const mockUpdatedPreferences = {
      user_id: 1,
      notify_on_comment_replies: false,
      notify_on_mentions: true,
      notify_on_new_posts: true,
    }

    it('should call PUT /api/user/notification-preferences with body and Authorization header', async () => {
      mockAxiosInstance.put.mockResolvedValueOnce({
        data: { preferences: mockUpdatedPreferences },
      })

      const updates = { notify_on_comment_replies: false, notify_on_mentions: true }
      const result = await notificationsApi.updateNotificationPreferences('mock-token', updates)

      expect(mockAxiosInstance.put).toHaveBeenCalledWith(
        '/user/notification-preferences',
        updates,
        { headers: { Authorization: 'Bearer mock-token' } }
      )
      expect(result).toEqual({ preferences: mockUpdatedPreferences })
    })

    it('should send only the provided keys — partial update is allowed', async () => {
      mockAxiosInstance.put.mockResolvedValueOnce({
        data: { preferences: mockUpdatedPreferences },
      })

      const partialUpdate = { notify_on_new_posts: false }
      await notificationsApi.updateNotificationPreferences('token', partialUpdate)

      const callBody = mockAxiosInstance.put.mock.calls[0][1]
      expect(callBody).toEqual({ notify_on_new_posts: false })
      expect(callBody).not.toHaveProperty('notify_on_comment_replies')
      expect(callBody).not.toHaveProperty('notify_on_mentions')
    })

    it('should return updated preferences with all fields', async () => {
      mockAxiosInstance.put.mockResolvedValueOnce({
        data: { preferences: mockUpdatedPreferences },
      })

      const result = await notificationsApi.updateNotificationPreferences('token', {
        notify_on_comment_replies: false,
      })

      expect(result.preferences.notify_on_comment_replies).toBe(false)
      expect(result.preferences.notify_on_mentions).toBe(true)
      expect(result.preferences.notify_on_new_posts).toBe(true)
    })

    it('should throw AxiosError on 401 Unauthorized', async () => {
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

      await expect(
        notificationsApi.updateNotificationPreferences('bad-token', { notify_on_mentions: true })
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 401 },
      })
    })

    it('should throw AxiosError on 400 Bad Request for invalid payload', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 400,
          data: { error: 'Invalid field' },
          statusText: 'Bad Request',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 400',
        name: 'AxiosError',
      }

      mockAxiosInstance.put.mockRejectedValueOnce(mockError)

      await expect(
        notificationsApi.updateNotificationPreferences('token', { notify_on_mentions: true })
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 400 },
      })
    })

    it('should throw AxiosError on 500 Internal Server Error', async () => {
      const mockError: Partial<AxiosError> = {
        isAxiosError: true,
        response: {
          status: 500,
          data: { error: 'Internal Server Error' },
          statusText: 'Internal Server Error',
          headers: {},
          config: {} as never,
        },
        message: 'Request failed with status code 500',
        name: 'AxiosError',
      }

      mockAxiosInstance.put.mockRejectedValueOnce(mockError)

      await expect(
        notificationsApi.updateNotificationPreferences('token', { notify_on_mentions: false })
      ).rejects.toMatchObject({
        isAxiosError: true,
        response: { status: 500 },
      })
    })
  })
})
