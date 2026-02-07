import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  useCreateDraft,
  useDeleteDraft,
  useDraft,
  useMyPosts,
  usePublishPost,
  useSaveDraft,
  useUnpublishPost,
} from '@/hooks/usePosts'
import type { ListPostsResponse, PostFilter, PostResponse } from '@/services/postsApi'
import { postsApi } from '@/services/postsApi'

/**
 * Mock dependencies for isolated testing
 */
vi.mock('@/services/postsApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-token'),
  })),
}))

/**
 * Test suite for React Query hooks for post/draft management
 *
 * Tests 7 custom hooks with comprehensive coverage of:
 * - Query behavior (loading, success, error states)
 * - Mutation behavior (optimistic updates, cache invalidation)
 * - Authentication token handling
 * - Query parameter variations
 * - Cache key management
 * - Error propagation
 */
describe('usePosts hooks', () => {
  let queryClient: QueryClient

  /**
   * Wrapper component for React Query hooks
   */
  const createWrapper = () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    return wrapper
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
        mutations: {
          retry: false,
        },
      },
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
    queryClient.clear()
  })

  /**
   * Tests for useDraft(slug)
   * Queries a single draft by slug
   */
  describe('useDraft', () => {
    const mockPost: PostResponse = {
      id: 1,
      slug: 'test-post',
      title: 'Test Post',
      author_id: 42,
      html_content: '<p>Content</p>',
      published: false,
      published_at: null,
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-03T10:00:00Z',
    }

    it('should call postsApi.getDraft with slug and token', async () => {
      vi.mocked(postsApi.getDraft).mockResolvedValueOnce(mockPost)

      const { result } = renderHook(() => useDraft('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.getDraft).toHaveBeenCalledWith('test-post', 'mock-token')
      expect(postsApi.getDraft).toHaveBeenCalledTimes(1)
    })

    it('should return loading state initially', () => {
      vi.mocked(postsApi.getDraft).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useDraft('test-post'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return data on successful fetch', async () => {
      vi.mocked(postsApi.getDraft).mockResolvedValueOnce(mockPost)

      const { result } = renderHook(() => useDraft('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockPost)
      expect(result.current.isError).toBe(false)
    })

    it('should return error on failed fetch (404 Not Found)', async () => {
      const mockError = new Error('Draft not found')
      vi.mocked(postsApi.getDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useDraft('nonexistent'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error on authorization failure (403 Forbidden)', async () => {
      const mockError = new Error('Forbidden')
      vi.mocked(postsApi.getDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useDraft('another-users-draft'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should use correct query key for caching', async () => {
      vi.mocked(postsApi.getDraft).mockResolvedValueOnce(mockPost)

      const { result } = renderHook(() => useDraft('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cachedData = queryClient.getQueryData(['draft', 'test-post'])
      expect(cachedData).toEqual(mockPost)
    })
  })

  /**
   * Tests for useMyPosts(filter?, page?, limit?)
   * Queries paginated list of user's posts with optional filtering
   */
  describe('useMyPosts', () => {
    const mockListResponse: ListPostsResponse = {
      posts: [
        {
          id: 1,
          slug: 'post-1',
          title: 'Post 1',
          author_id: 42,
          html_content: '<p>Content 1</p>',
          published: true,
          published_at: '2026-02-03T10:00:00Z',
          created_at: '2026-02-03T09:00:00Z',
          updated_at: '2026-02-03T10:00:00Z',
        },
        {
          id: 2,
          slug: 'post-2',
          title: 'Post 2',
          author_id: 42,
          html_content: '',
          published: false,
          published_at: null,
          created_at: '2026-02-03T11:00:00Z',
          updated_at: '2026-02-03T11:00:00Z',
        },
      ],
      total_count: 2,
      total_pages: 1,
      page: 1,
      limit: 20,
    }

    it('should call postsApi.listMyPosts with default params', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useMyPosts(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.listMyPosts).toHaveBeenCalledWith(undefined, 1, 20, 'mock-token')
      expect(result.current.data).toEqual(mockListResponse)
    })

    it('should handle filter parameter correctly', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce({
        ...mockListResponse,
        posts: [mockListResponse.posts[1]],
        total_count: 1,
      })

      const { result } = renderHook(() => useMyPosts('drafts'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.listMyPosts).toHaveBeenCalledWith('drafts', 1, 20, 'mock-token')
    })

    it('should handle custom page parameter', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce({
        ...mockListResponse,
        page: 2,
      })

      const { result } = renderHook(() => useMyPosts(undefined, 2), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.listMyPosts).toHaveBeenCalledWith(undefined, 2, 20, 'mock-token')
    })

    it('should handle custom limit parameter', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce({
        ...mockListResponse,
        limit: 10,
      })

      const { result } = renderHook(() => useMyPosts(undefined, 1, 10), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.listMyPosts).toHaveBeenCalledWith(undefined, 1, 10, 'mock-token')
    })

    it('should handle all parameters together', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useMyPosts('published', 3, 5), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.listMyPosts).toHaveBeenCalledWith('published', 3, 5, 'mock-token')
    })

    it('should return paginated data correctly', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce(mockListResponse)

      const { result } = renderHook(() => useMyPosts(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.posts).toHaveLength(2)
      expect(result.current.data?.total_count).toBe(2)
      expect(result.current.data?.total_pages).toBe(1)
      expect(result.current.data?.page).toBe(1)
    })

    it('should handle empty results', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce({
        posts: [],
        total_count: 0,
        total_pages: 0,
        page: 1,
        limit: 20,
      })

      const { result } = renderHook(() => useMyPosts(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.posts).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })

    it('should use correct query key with parameters', async () => {
      vi.mocked(postsApi.listMyPosts).mockResolvedValueOnce(mockListResponse)

      const filter: PostFilter = 'drafts'
      const { result } = renderHook(() => useMyPosts(filter, 2, 10), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cachedData = queryClient.getQueryData([
        'myPosts',
        { filter: 'drafts', page: 2, limit: 10 },
      ])
      expect(cachedData).toEqual(mockListResponse)
    })

    it('should return error on failed request (401 Unauthorized)', async () => {
      const mockError = new Error('Unauthorized')
      vi.mocked(postsApi.listMyPosts).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useMyPosts(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })
  })

  /**
   * Tests for useCreateDraft()
   * Mutation hook for creating new draft posts
   */
  describe('useCreateDraft', () => {
    const mockPost: PostResponse = {
      id: 1,
      slug: 'new-post',
      title: 'New Post',
      author_id: 42,
      html_content: '',
      published: false,
      published_at: null,
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-03T10:00:00Z',
    }

    it('should call postsApi.createDraft with correct parameters', async () => {
      vi.mocked(postsApi.createDraft).mockResolvedValueOnce(mockPost)

      const { result } = renderHook(() => useCreateDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'new-post', title: 'New Post' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.createDraft).toHaveBeenCalledWith('new-post', 'New Post', 'mock-token')
    })

    it('should invalidate myPosts cache on success', async () => {
      vi.mocked(postsApi.createDraft).mockResolvedValueOnce(mockPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useCreateDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'new-post', title: 'New Post' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['myPosts', {}],
      })
    })

    it('should return created post data', async () => {
      vi.mocked(postsApi.createDraft).mockResolvedValueOnce(mockPost)

      const { result } = renderHook(() => useCreateDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'new-post', title: 'New Post' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockPost)
    })

    it('should handle error on duplicate slug (409 Conflict)', async () => {
      const mockError = new Error('Slug already exists')
      vi.mocked(postsApi.createDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useCreateDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'existing-slug', title: 'Test' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle validation error (400 Bad Request)', async () => {
      const mockError = new Error('Invalid slug format')
      vi.mocked(postsApi.createDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useCreateDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'invalid slug!', title: 'Test' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should be in loading state during mutation', async () => {
      vi.mocked(postsApi.createDraft).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useCreateDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'new-post', title: 'New Post' })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })
  })

  /**
   * Tests for useSaveDraft()
   * Mutation hook for saving draft content
   */
  describe('useSaveDraft', () => {
    const mockPost: PostResponse = {
      id: 1,
      slug: 'test-post',
      title: 'Test Post',
      author_id: 42,
      html_content: '<p>Updated content</p>',
      published: false,
      published_at: null,
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-03T10:30:00Z',
    }

    it('should call postsApi.saveDraft with correct parameters', async () => {
      vi.mocked(postsApi.saveDraft).mockResolvedValueOnce(mockPost)

      const { result } = renderHook(() => useSaveDraft(), {
        wrapper: createWrapper(),
      })

      const content = '# Updated Title\n\nUpdated content'
      result.current.mutate({ slug: 'test-post', content })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.saveDraft).toHaveBeenCalledWith('test-post', content, 'mock-token')
    })

    it('should invalidate specific draft cache on success', async () => {
      vi.mocked(postsApi.saveDraft).mockResolvedValueOnce(mockPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useSaveDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({
        slug: 'test-post',
        content: 'New content',
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['draft', 'test-post'],
      })
    })

    it('should invalidate myPosts cache on success', async () => {
      vi.mocked(postsApi.saveDraft).mockResolvedValueOnce(mockPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useSaveDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({
        slug: 'test-post',
        content: 'New content',
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['draft', 'test-post'],
      })
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['myPosts', {}],
      })
      expect(invalidateSpy).toHaveBeenCalledTimes(2)
    })

    it('should perform optimistic update', async () => {
      vi.mocked(postsApi.saveDraft).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockPost), 100))
      )

      queryClient.setQueryData(['draft', 'test-post'], {
        ...mockPost,
        html_content: '<p>Old content</p>',
      })

      const { result } = renderHook(() => useSaveDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({
        slug: 'test-post',
        content: 'New content',
      })

      const optimisticData = queryClient.getQueryData<PostResponse>(['draft', 'test-post'])
      expect(optimisticData?.html_content).toBeDefined()

      await waitFor(() => expect(result.current.isSuccess).toBe(true))
    })

    it('should handle validation error (422 Unprocessable Entity)', async () => {
      const mockError = new Error('Invalid markdown content')
      vi.mocked(postsApi.saveDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useSaveDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({
        slug: 'test-post',
        content: '<script>malicious</script>',
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle not found error (404 Not Found)', async () => {
      const mockError = new Error('Draft not found')
      vi.mocked(postsApi.saveDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useSaveDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({
        slug: 'nonexistent',
        content: 'content',
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })
  })

  /**
   * Tests for usePublishPost()
   * Mutation hook for publishing draft posts
   */
  describe('usePublishPost', () => {
    const mockPublishedPost: PostResponse = {
      id: 1,
      slug: 'test-post',
      title: 'Test Post',
      author_id: 42,
      html_content: '<p>Content</p>',
      published: true,
      published_at: '2026-02-03T11:00:00Z',
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-03T11:00:00Z',
    }

    it('should call postsApi.publishPost with slug', async () => {
      vi.mocked(postsApi.publishPost).mockResolvedValueOnce(mockPublishedPost)

      const { result } = renderHook(() => usePublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.publishPost).toHaveBeenCalledWith('test-post', 'mock-token')
    })

    it('should invalidate draft cache on success', async () => {
      vi.mocked(postsApi.publishPost).mockResolvedValueOnce(mockPublishedPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => usePublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['draft', 'test-post'],
      })
    })

    it('should invalidate myPosts cache on success', async () => {
      vi.mocked(postsApi.publishPost).mockResolvedValueOnce(mockPublishedPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => usePublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['myPosts', {}],
      })
    })

    it('should return published post data with published=true', async () => {
      vi.mocked(postsApi.publishPost).mockResolvedValueOnce(mockPublishedPost)

      const { result } = renderHook(() => usePublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.published).toBe(true)
      expect(result.current.data?.published_at).not.toBeNull()
    })

    it('should handle not found error (404 Not Found)', async () => {
      const mockError = new Error('Draft not found')
      vi.mocked(postsApi.publishPost).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => usePublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('nonexistent')

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle already published error (409 Conflict)', async () => {
      const mockError = new Error('Post already published')
      vi.mocked(postsApi.publishPost).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => usePublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('already-published')

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })
  })

  /**
   * Tests for useUnpublishPost()
   * Mutation hook for unpublishing posts
   */
  describe('useUnpublishPost', () => {
    const mockUnpublishedPost: PostResponse = {
      id: 1,
      slug: 'test-post',
      title: 'Test Post',
      author_id: 42,
      html_content: '<p>Content</p>',
      published: false,
      published_at: null,
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-03T11:30:00Z',
    }

    it('should call postsApi.unpublishPost with slug', async () => {
      vi.mocked(postsApi.unpublishPost).mockResolvedValueOnce(mockUnpublishedPost)

      const { result } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.unpublishPost).toHaveBeenCalledWith('test-post', 'mock-token')
    })

    it('should invalidate draft cache on success', async () => {
      vi.mocked(postsApi.unpublishPost).mockResolvedValueOnce(mockUnpublishedPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['draft', 'test-post'],
      })
    })

    it('should invalidate myPosts cache on success', async () => {
      vi.mocked(postsApi.unpublishPost).mockResolvedValueOnce(mockUnpublishedPost)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['myPosts', {}],
      })
    })

    it('should return unpublished post data with published=false', async () => {
      vi.mocked(postsApi.unpublishPost).mockResolvedValueOnce(mockUnpublishedPost)

      const { result } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.published).toBe(false)
      expect(result.current.data?.published_at).toBeNull()
    })

    it('should handle not found error (404 Not Found)', async () => {
      const mockError = new Error('Post not found')
      vi.mocked(postsApi.unpublishPost).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('nonexistent')

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle not published error (409 Conflict)', async () => {
      const mockError = new Error('Post not published')
      vi.mocked(postsApi.unpublishPost).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useUnpublishPost(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('not-published')

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })
  })

  /**
   * Tests for useDeleteDraft()
   * Mutation hook for deleting draft posts
   */
  describe('useDeleteDraft', () => {
    it('should call postsApi.deleteDraft with slug', async () => {
      vi.mocked(postsApi.deleteDraft).mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useDeleteDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(postsApi.deleteDraft).toHaveBeenCalledWith('test-post', 'mock-token')
    })

    it('should invalidate myPosts cache on success', async () => {
      vi.mocked(postsApi.deleteDraft).mockResolvedValueOnce(undefined)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useDeleteDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['myPosts', {}],
      })
    })

    it('should remove draft from cache on success', async () => {
      vi.mocked(postsApi.deleteDraft).mockResolvedValueOnce(undefined)

      const removeSpy = vi.spyOn(queryClient, 'removeQueries')

      const { result } = renderHook(() => useDeleteDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(removeSpy).toHaveBeenCalledWith({
        queryKey: ['draft', 'test-post'],
      })
    })

    it('should handle not found error (404 Not Found)', async () => {
      const mockError = new Error('Draft not found')
      vi.mocked(postsApi.deleteDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useDeleteDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('nonexistent')

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle forbidden error (403 Forbidden)', async () => {
      const mockError = new Error('Forbidden')
      vi.mocked(postsApi.deleteDraft).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useDeleteDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('another-users-draft')

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should return undefined on successful deletion', async () => {
      vi.mocked(postsApi.deleteDraft).mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useDeleteDraft(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('test-post')

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toBeUndefined()
    })
  })
})