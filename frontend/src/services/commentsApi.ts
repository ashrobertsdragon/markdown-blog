import { apiClient } from './postsApi'

/**
 * A single comment returned from the API
 */
export interface CommentResponse {
  id: number
  post_id: number
  is_post_author: boolean
  text: string
  parent_id: number | null
  created_at: string
  updated_at: string
  is_deleted: boolean
  is_pending_moderation: boolean
}

/**
 * Paginated list of comments response
 */
export interface ListCommentsResponse {
  comments: CommentResponse[]
  total_count: number
  has_more: boolean
}

/**
 * Helper to create authorization header config
 */
const getAuthHeaders = (token: string) => ({
  headers: { Authorization: `Bearer ${token}` },
})

/**
 * Comments API service object
 */
export const commentsApi = {
  /**
   * List comments for a post (public — no auth required)
   *
   * @param slug - Post slug identifier
   * @param skip - Number of comments to skip (offset)
   * @param limit - Maximum number of comments to return
   * @returns Paginated list of comments
   * @throws AxiosError on not found (404)
   */
  async listComments(slug: string, skip: number, limit: number): Promise<ListCommentsResponse> {
    const response = await apiClient.get<ListCommentsResponse>(`/posts/${slug}/comments`, {
      params: { skip, limit },
    })
    return response.data
  },

  /**
   * Post a new top-level comment on a post
   *
   * @param slug - Post slug identifier
   * @param text - Comment text content
   * @param token - JWT authentication token
   * @returns Created comment data
   * @throws AxiosError on unauthorized (401), not found (404), or rate limit (429)
   */
  async postComment(slug: string, text: string, token: string): Promise<CommentResponse> {
    const response = await apiClient.post<CommentResponse>(
      `/posts/${slug}/comments`,
      { text },
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Delete a comment by id
   *
   * @param slug - Post slug identifier
   * @param commentId - Comment id to delete
   * @param token - JWT authentication token
   * @returns void (204 No Content)
   * @throws AxiosError on unauthorized (401), not found (404), or forbidden (403)
   */
  async deleteComment(slug: string, commentId: number, token: string): Promise<void> {
    await apiClient.delete(`/posts/${slug}/comments/${commentId}`, getAuthHeaders(token))
  },

  /**
   * Post a reply to an existing comment
   *
   * @param slug - Post slug identifier
   * @param parentId - Id of the comment being replied to
   * @param text - Reply text content
   * @param token - JWT authentication token
   * @returns Created reply comment data
   * @throws AxiosError on unauthorized (401), not found (404), or rate limit (429)
   */
  async replyToComment(
    slug: string,
    parentId: number,
    text: string,
    token: string
  ): Promise<CommentResponse> {
    const response = await apiClient.post<CommentResponse>(
      `/posts/${slug}/comments/${parentId}/reply`,
      { text },
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Approve a comment held in the moderation queue
   *
   * Clears the is_pending_moderation flag so the comment becomes publicly
   * visible without any other changes to its content.
   *
   * @param commentId - Comment id to approve
   * @param token - JWT authentication token (admin role required)
   * @returns Updated comment data with is_pending_moderation false
   * @throws AxiosError on unauthorized (401), forbidden (403), or not found (404)
   */
  async approveComment(commentId: number, token: string): Promise<CommentResponse> {
    const response = await apiClient.put<CommentResponse>(
      `/admin/comments/${commentId}/approve`,
      {},
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Permanently delete a comment via the admin endpoint
   *
   * Unlike the user-facing delete which soft-deletes, the admin endpoint
   * performs a hard delete that bypasses ownership checks.
   *
   * @param commentId - Comment id to delete
   * @param token - JWT authentication token (admin role required)
   * @returns void (204 No Content)
   * @throws AxiosError on unauthorized (401), forbidden (403), or not found (404)
   */
  async adminDeleteComment(commentId: number, token: string): Promise<void> {
    await apiClient.delete(`/admin/comments/${commentId}`, getAuthHeaders(token))
  },
}
