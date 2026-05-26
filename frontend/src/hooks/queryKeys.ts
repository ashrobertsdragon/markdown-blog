import type { PostFilter } from '@/services/postsApi'

/**
 * Query key factory for React Query cache management
 *
 * Centralized query key definitions ensure consistent caching behavior
 * and simplify cache invalidation across the application.
 */
export const queryKeys = {
  /**
   * Query key for fetching a single draft by slug
   */
  draft: (slug: string) => ['draft', slug] as const,

  /**
   * Query key for listing authenticated user's posts with optional filtering
   */
  myPosts: (params?: { filter?: PostFilter; page?: number; limit?: number }) =>
    ['myPosts', params ?? {}] as const,

  /**
   * Query key for fetching a single published post by slug (public)
   */
  publicPost: (slug: string) => ['publicPost', slug] as const,

  /**
   * Query key for fetching revision history with optional pagination
   */
  revisionHistory: (slug: string, params?: { skip?: number; limit?: number }) =>
    ['revisionHistory', slug, params ?? {}] as const,

  /**
   * Query key for fetching a single revision by slug and SHA
   */
  revisionDetail: (slug: string, sha: string) => ['revisionDetail', slug, sha] as const,

  /**
   * Query key for fetching diff between two revisions
   */
  revisionDiff: (slug: string, sha1: string, sha2: string) =>
    ['revisionDiff', slug, sha1, sha2] as const,

  /**
   * Query key for the authenticated user's notification preferences
   */
  notificationPreferences: () => ['notificationPreferences'] as const,

  /**
   * Query key factory for admin-scoped queries
   */
  admin: {
    /**
     * Query key namespace root for all admin queries — used for
     * cache invalidation across all admin queries (users, posts, etc).
     */
    all: () => ['admin'] as const,
    /**
     * Query key for paginated user list — each page/limit combination is a
     * distinct cache entry so navigation between pages does not overwrite data.
     */
    users: (page?: number, limit?: number) =>
      ['admin', 'users', { page: page ?? 1, limit: limit ?? 50 }] as const,
    /**
     * Query key for paginated posts list — each page/limit combination is a
     * distinct cache entry so navigation between pages does not overwrite data.
     */
    posts: (page?: number, limit?: number) =>
      ['admin', 'posts', { page: page ?? 1, limit: limit ?? 50 }] as const,
    /**
     * Query key for paginated comments list — each page/limit combination is a
     * distinct cache entry so navigation between pages does not overwrite data.
     */
    comments: (page?: number, limit?: number) =>
      ['admin', 'comments', { page: page ?? 1, limit: limit ?? 50 }] as const,
    /**
     * Query key for system health — single entry, auto-refreshed on interval.
     */
    systemHealth: () => ['admin', 'system-health'] as const,
    /**
     * Query key for error logs — keyed by limit so different caps store
     * independently in cache.
     */
    errorLogs: (limit?: number) => ['admin', 'error-logs', { limit: limit ?? 50 }] as const,
  },
}
