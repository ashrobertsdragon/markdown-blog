import { apiClient } from './postsApi'

/**
 * Shape of a single user's notification preferences returned by the API
 */
export interface NotificationPreferences {
  user_id: number
  notify_on_comment_replies: boolean
  notify_on_mentions: boolean
  notify_on_new_posts: boolean
}

/**
 * Response envelope for GET and PUT /api/user/notification-preferences
 */
export interface NotificationPreferencesResponse {
  preferences: NotificationPreferences
}

/**
 * Partial update payload for PUT /api/user/notification-preferences
 */
export type NotificationPreferencesUpdate = Partial<Omit<NotificationPreferences, 'user_id'>>

/**
 * Helper to create authorization header config
 */
const getAuthHeaders = (token: string) => ({
  headers: { Authorization: `Bearer ${token}` },
})

/**
 * Response envelope for GET /api/unsubscribe
 */
export interface UnsubscribeResponse {
  message: string
  user_id: number
}

export const notificationsApi = {
  /**
   * Fetch the authenticated user's notification preferences
   *
   * Requires a valid JWT — the backend returns 401 if the token is absent or invalid.
   *
   * @param token - JWT authentication token
   * @returns Notification preferences response envelope
   * @throws AxiosError on 401 (unauthorized) or 500 (server error)
   */
  async fetchNotificationPreferences(token: string): Promise<NotificationPreferencesResponse> {
    const response = await apiClient.get<NotificationPreferencesResponse>(
      '/user/notification-preferences',
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Update the authenticated user's notification preferences
   *
   * Accepts a partial payload — only the provided keys are updated on the backend.
   * Requires a valid JWT — the backend returns 401 if the token is absent or invalid.
   *
   * @param token - JWT authentication token
   * @param updates - Partial preferences to update
   * @returns Updated notification preferences response envelope
   * @throws AxiosError on 400 (bad request), 401 (unauthorized), or 500 (server error)
   */
  async updateNotificationPreferences(
    token: string,
    updates: NotificationPreferencesUpdate
  ): Promise<NotificationPreferencesResponse> {
    const response = await apiClient.put<NotificationPreferencesResponse>(
      '/user/notification-preferences',
      updates,
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Unsubscribe a user from all notifications using a signed token
   *
   * No authentication header required — the token in the query string is the
   * proof of identity. Called from the public /unsubscribe landing page.
   *
   * @param user_id - User primary key from the email link
   * @param token - 64-character HMAC-SHA256 hex digest from the email link
   * @returns Unsubscribe confirmation response
   * @throws AxiosError on 400 (invalid/expired token) or 5xx (server error)
   */
  async unsubscribeWithToken(user_id: number, token: string): Promise<UnsubscribeResponse> {
    const response = await apiClient.get<UnsubscribeResponse>('/unsubscribe', {
      params: { user_id, token },
    })
    return response.data
  },
}
