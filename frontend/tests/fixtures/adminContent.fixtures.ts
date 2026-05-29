import type {
  AdminComment,
  AdminPost,
  CommentsResponse,
  PostsResponse,
} from '@/services/admin/adminApi'

/**
 * Factory function to create a mock AdminPost with sensible defaults.
 *
 * @param overrides - Partial fields to override defaults
 * @returns AdminPost object
 */
export function createMockAdminPost(overrides: Partial<AdminPost> = {}): AdminPost {
  return {
    id: 1,
    slug: 'hello-world',
    title: 'Hello World',
    author: 'Admin User',
    author_id: 42,
    published_at: '2026-01-15T12:00:00Z',
    created_at: '2026-01-10T09:00:00Z',
    ...overrides,
  }
}

/**
 * Factory function to create a PostsResponse with paginated data.
 *
 * @param posts - Array of posts to include
 * @param total - Total post count across all pages
 * @param totalPages - Total number of pages
 * @param page - Current page number (1-indexed)
 * @param limit - Results per page
 * @returns PostsResponse object
 */
export function createMockPostsResponse(
  posts: AdminPost[] = [],
  total: number = 0,
  totalPages: number = 0,
  page: number = 1,
  limit: number = 50
): PostsResponse {
  return {
    posts,
    total_count: total,
    total_pages: totalPages,
    page,
    limit,
  }
}

/**
 * Factory function to create a PostsResponse with multiple pages of data.
 *
 * @param postCount - Number of posts to create for this page
 * @param page - Current page number
 * @param pageSize - Results per page
 * @param totalCount - Total posts across all pages
 * @returns PostsResponse object with pagination metadata
 */
export function createMockPaginatedPostsResponse(
  postCount: number = 3,
  page: number = 1,
  pageSize: number = 3,
  totalCount: number = 10
): PostsResponse {
  const posts = Array.from({ length: postCount }, (_, i) =>
    createMockAdminPost({
      id: (page - 1) * pageSize + i + 1,
      slug: `post-${(page - 1) * pageSize + i + 1}`,
      title: `Post ${(page - 1) * pageSize + i + 1}`,
    })
  )
  const totalPages = Math.ceil(totalCount / pageSize)
  return createMockPostsResponse(posts, totalCount, totalPages, page, pageSize)
}

/**
 * Factory function to create a mock AdminComment with sensible defaults.
 *
 * @param overrides - Partial fields to override defaults
 * @returns AdminComment object
 */
export function createMockAdminComment(overrides: Partial<AdminComment> = {}): AdminComment {
  return {
    id: 1,
    text: 'Great post! Really enjoyed reading this.',
    author: 'Alice',
    author_id: 10,
    post_title: 'Hello World',
    post_id: 5,
    created_at: '2026-03-01T10:00:00Z',
    ...overrides,
  }
}

/**
 * Factory function to create an AdminComment with text exceeding 100 characters.
 *
 * @param overrides - Partial fields to override defaults
 * @returns AdminComment object with long text content
 */
export function createMockLongTextAdminComment(
  overrides: Partial<AdminComment> = {}
): AdminComment {
  return createMockAdminComment({
    text: 'This is a very long comment that exceeds the one hundred character limit set for display truncation in the admin comments table view.',
    ...overrides,
  })
}

/**
 * Factory function to create a CommentsResponse with paginated data.
 *
 * @param comments - Array of comments to include
 * @param total - Total comment count across all pages
 * @param totalPages - Total number of pages
 * @param page - Current page number (1-indexed)
 * @param limit - Results per page
 * @returns CommentsResponse object
 */
export function createMockCommentsResponse(
  comments: AdminComment[] = [],
  total: number = 0,
  totalPages: number = 0,
  page: number = 1,
  limit: number = 50
): CommentsResponse {
  return {
    comments,
    total_count: total,
    total_pages: totalPages,
    page,
    limit,
  }
}

/**
 * Factory function to create a CommentsResponse with multiple pages of data.
 *
 * @param commentCount - Number of comments to create for this page
 * @param page - Current page number
 * @param pageSize - Results per page
 * @param totalCount - Total comments across all pages
 * @returns CommentsResponse object with pagination metadata
 */
export function createMockPaginatedCommentsResponse(
  commentCount: number = 3,
  page: number = 1,
  pageSize: number = 3,
  totalCount: number = 10
): CommentsResponse {
  const comments = Array.from({ length: commentCount }, (_, i) =>
    createMockAdminComment({
      id: (page - 1) * pageSize + i + 1,
      text: `Comment ${(page - 1) * pageSize + i + 1}`,
      author: `User ${(page - 1) * pageSize + i + 1}`,
    })
  )
  const totalPages = Math.ceil(totalCount / pageSize)
  return createMockCommentsResponse(comments, totalCount, totalPages, page, pageSize)
}
