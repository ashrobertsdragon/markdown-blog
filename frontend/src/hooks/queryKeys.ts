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
}
