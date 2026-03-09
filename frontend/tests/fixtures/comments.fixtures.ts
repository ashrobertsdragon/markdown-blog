import type { CommentResponse, ListCommentsResponse } from '@/services/commentsApi'

/**
 * Factory function to create a mock CommentResponse with sensible defaults
 *
 * @param overrides - Partial comment fields to override defaults
 * @returns CommentResponse object
 */
export function createMockComment(overrides: Partial<CommentResponse> = {}): CommentResponse {
  return {
    id: 1,
    post_id: 10,
    is_post_author: false,
    text: 'This is a great post!',
    parent_id: null,
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-01T10:00:00Z',
    is_deleted: false,
    is_pending_moderation: false,
    ...overrides,
  }
}

/**
 * Factory function to create a mock reply comment (with parent_id)
 *
 * @param parentId - ID of the parent comment being replied to
 * @param overrides - Partial comment fields to override defaults
 * @returns CommentResponse object with parent_id set
 */
export function createMockReplyComment(
  parentId: number = 1,
  overrides: Partial<CommentResponse> = {}
): CommentResponse {
  return createMockComment({
    id: 2,
    text: 'I disagree because...',
    parent_id: parentId,
    ...overrides,
  })
}

/**
 * Factory function to create a deleted comment
 *
 * @param overrides - Partial comment fields to override defaults
 * @returns CommentResponse object with is_deleted = true
 */
export function createMockDeletedComment(
  overrides: Partial<CommentResponse> = {}
): CommentResponse {
  return createMockComment({
    text: '[deleted by author]',
    is_deleted: true,
    ...overrides,
  })
}

/**
 * Factory function to create a comment pending moderation
 *
 * @param overrides - Partial comment fields to override defaults
 * @returns CommentResponse object with is_pending_moderation = true
 */
export function createMockPendingModerationComment(
  overrides: Partial<CommentResponse> = {}
): CommentResponse {
  return createMockComment({
    text: 'This comment looks suspicious and needs review',
    is_pending_moderation: true,
    ...overrides,
  })
}

/**
 * Factory function to create a ListCommentsResponse with default pagination
 *
 * @param comments - Array of comments to include, or undefined for default array
 * @param total - Total comment count across all pages
 * @param hasMore - Whether more comments exist beyond this page
 * @returns ListCommentsResponse object
 */
export function createMockListCommentsResponse(
  comments?: CommentResponse[],
  total: number = 0,
  hasMore: boolean = false
): ListCommentsResponse {
  return {
    comments: comments ?? [],
    total_count: total,
    has_more: hasMore,
  }
}
