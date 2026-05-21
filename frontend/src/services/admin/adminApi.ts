import { getAuthHeaders } from '@/services/auth-headers'
import { apiClient } from '@/services/postsApi'

/**
 * User role types
 */
export type UserRole = 'admin' | 'authenticated'

/**
 * A single user record returned by admin user endpoints
 */
export interface User {
  id: number
  clerk_id: string
  email: string
  display_name: string
  role: UserRole
  created_at: string
  last_login: string | null
}

/**
 * Paginated user list response
 */
export interface UsersResponse {
  users: User[]
  total_count: number
  total_pages: number
  page: number
  limit: number
}

/**
 * A recent post entry within a user activity summary
 */
export interface ActivityPost {
  id: number
  slug: string
  title: string
  published: boolean
  created_at: string
}

/**
 * A recent comment entry within a user activity summary
 */
export interface ActivityComment {
  id: number
  post_slug: string
  text: string
  created_at: string
}

/**
 * User activity summary returned by the activity endpoint
 */
export interface UserActivity {
  user_id: number
  last_login: string | null
  post_count: number
  comment_count: number
  recent_posts: ActivityPost[]
  recent_comments: ActivityComment[]
}

/**
 * System health status type
 */
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy'

/**
 * System health status returned by the health endpoint
 */
export interface SystemHealth {
  status: HealthStatus
  database: HealthStatus
  filesystem: HealthStatus
  github_api: HealthStatus
  uptime_seconds: number
  checked_at: string
}

/**
 * Error log level type
 */
export type ErrorLogLevel = 'error' | 'warning' | 'info' | 'debug'

/**
 * A single error log entry
 */
export interface ErrorLogEntry {
  id: number
  level: ErrorLogLevel
  message: string
  timestamp: string
  context: Record<string, unknown>
}

/**
 * Error logs response with entries and metadata
 */
export interface ErrorLogsResponse {
  errors: ErrorLogEntry[]
  total_count: number
  limit: number
}

/**
 * A single published post record returned by the admin posts endpoint
 */
export interface AdminPost {
  id: number
  slug: string
  title: string
  author: string
  author_id: number
  published_at: string
  created_at: string
}

/**
 * Paginated published post list response
 */
export interface PostsResponse {
  posts: AdminPost[]
  total_count: number
  total_pages: number
  page: number
  limit: number
}

/**
 * Response from the unpublish post endpoint
 */
export interface UnpublishPostResponse {
  message: string
  post_id: number
}

/**
 * Admin API service object providing methods for all admin endpoints.
 * All methods require a valid admin JWT token.
 */
export const adminApi = {
  /**
   * Retrieve a paginated list of all users
   *
   * @param page - Page number (1-indexed)
   * @param limit - Results per page
   * @param token - Admin JWT authentication token
   * @returns Paginated user list with total count and page metadata
   * @throws AxiosError on unauthorized (401), forbidden (403), or server error (500)
   */
  async getUsers(page: number, limit: number, token: string): Promise<UsersResponse> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.get<UsersResponse>('/admin/users', {
      params: { page, limit },
      ...getAuthHeaders(token),
    })
    return response.data
  },

  /**
   * Update the role of a specific user
   *
   * @param userId - Numeric user ID
   * @param role - New role value (e.g. "admin" or "authenticated")
   * @param token - Admin JWT authentication token
   * @returns Updated user record
   * @throws AxiosError on not found (404), invalid role (422), unauthorized (401), or forbidden (403)
   */
  async updateUserRole(userId: number, role: UserRole, token: string): Promise<User> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.put<User>(
      `/admin/users/${userId}/role`,
      { role },
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Retrieve activity summary for a specific user
   *
   * @param userId - Numeric user ID
   * @param token - Admin JWT authentication token
   * @returns User activity including post count, comment count, and recent items
   * @throws AxiosError on not found (404), unauthorized (401), or forbidden (403)
   */
  async getUserActivity(userId: number, token: string): Promise<UserActivity> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.get<UserActivity>(
      `/admin/users/${userId}/activity`,
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Retrieve a paginated list of all published posts (admin only)
   *
   * @param page - Page number (1-indexed)
   * @param limit - Results per page
   * @param token - Admin JWT authentication token
   * @returns Paginated published post list with total count and page metadata
   * @throws AxiosError on unauthorized (401), forbidden (403), or server error (500)
   */
  async getPosts(page: number, limit: number, token: string): Promise<PostsResponse> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.get<PostsResponse>('/admin/posts', {
      params: { page, limit },
      ...getAuthHeaders(token),
    })
    return response.data
  },

  /**
   * Unpublish a published post by its numeric ID
   *
   * @param postId - Numeric post ID
   * @param token - Admin JWT authentication token
   * @returns Success message and post ID
   * @throws AxiosError on not found (404), conflict (409), unauthorized (401), or forbidden (403)
   */
  async unpublishPost(postId: number, token: string): Promise<UnpublishPostResponse> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.post<UnpublishPostResponse>(
      `/admin/posts/${postId}/unpublish`,
      {},
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Delete a comment by its numeric ID (admin moderation)
   *
   * @param commentId - Numeric comment ID
   * @param token - Admin JWT authentication token
   * @returns void — 204 No Content on success
   * @throws AxiosError on not found (404), unauthorized (401), or forbidden (403)
   */
  async deleteComment(commentId: number, token: string): Promise<void> {
    if (!token) throw new Error('Authentication required')
    await apiClient.delete(`/admin/comments/${commentId}`, getAuthHeaders(token))
  },

  /**
   * Retrieve the current system health status
   *
   * @param token - Admin JWT authentication token
   * @returns Health status for each subsystem with uptime in seconds
   * @throws AxiosError on unauthorized (401), forbidden (403), or server error (500)
   */
  async getSystemHealth(token: string): Promise<SystemHealth> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.get<SystemHealth>(
      '/admin/system/health',
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Retrieve recent application error logs
   *
   * @param limit - Maximum number of entries to return
   * @param token - Admin JWT authentication token
   * @returns Error log entries with level, message, timestamp, and context
   * @throws AxiosError on unauthorized (401), forbidden (403), or server error (500)
   */
  async getErrorLogs(limit: number, token: string): Promise<ErrorLogsResponse> {
    if (!token) throw new Error('Authentication required')
    const response = await apiClient.get<ErrorLogsResponse>('/admin/system/errors', {
      params: { limit },
      ...getAuthHeaders(token),
    })
    return response.data
  },
}
