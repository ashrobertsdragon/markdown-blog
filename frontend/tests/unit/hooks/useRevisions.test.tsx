import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  useRevertRevision,
  useRevisionDetail,
  useRevisionDiff,
  useRevisionHistory,
} from '@/hooks/useRevisions'
import type {
  DiffResponse,
  ListRevisionsResponse,
  RevertResponse,
  RevisionDetail,
} from '@/services/revisionsApi'
import { revisionsApi } from '@/services/revisionsApi'

vi.mock('@/services/revisionsApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-token'),
  })),
}))

describe('useRevisions hooks', () => {
  let queryClient: QueryClient

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

  describe('useRevisionHistory', () => {
    const mockRevisions: ListRevisionsResponse = {
      revisions: [
        {
          id: '1',
          commit_sha: 'abc123def456',
          short_sha: 'abc123d',
          author_id: '42',
          timestamp: '2026-02-15T10:00:00Z',
          relative_time: '2 hours ago',
          commit_message: 'Initial commit',
          is_revert: false,
        },
        {
          id: '2',
          commit_sha: '789ghi012jkl',
          short_sha: '789ghi0',
          author_id: '42',
          timestamp: '2026-02-15T09:00:00Z',
          relative_time: '3 hours ago',
          commit_message: 'Updated content',
          is_revert: false,
        },
      ],
      total_count: 2,
      has_more: false,
    }

    it('should call revisionsApi.listRevisions with slug and default pagination', async () => {
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(mockRevisions)

      const { result } = renderHook(() => useRevisionHistory('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.listRevisions).toHaveBeenCalledWith('test-post', 0, 20, 'mock-token')
      expect(revisionsApi.listRevisions).toHaveBeenCalledTimes(1)
    })

    it('should call revisionsApi.listRevisions with custom skip parameter', async () => {
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(mockRevisions)

      const { result } = renderHook(() => useRevisionHistory('test-post', 10), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.listRevisions).toHaveBeenCalledWith('test-post', 10, 20, 'mock-token')
    })

    it('should call revisionsApi.listRevisions with custom limit parameter', async () => {
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(mockRevisions)

      const { result } = renderHook(() => useRevisionHistory('test-post', 0, 50), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.listRevisions).toHaveBeenCalledWith('test-post', 0, 50, 'mock-token')
    })

    it('should call revisionsApi.listRevisions with both skip and limit', async () => {
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(mockRevisions)

      const { result } = renderHook(() => useRevisionHistory('test-post', 30, 10), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.listRevisions).toHaveBeenCalledWith('test-post', 30, 10, 'mock-token')
    })

    it('should return loading state initially', () => {
      vi.mocked(revisionsApi.listRevisions).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useRevisionHistory('test-post'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return data on successful fetch', async () => {
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(mockRevisions)

      const { result } = renderHook(() => useRevisionHistory('test-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockRevisions)
      expect(result.current.isError).toBe(false)
      expect(result.current.data?.revisions).toHaveLength(2)
    })

    it('should return error on failed fetch', async () => {
      const mockError = new Error('Not found')
      vi.mocked(revisionsApi.listRevisions).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevisionHistory('nonexistent'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
      expect(result.current.data).toBeUndefined()
    })

    it('should not fetch when slug is empty', () => {
      const { result } = renderHook(() => useRevisionHistory(''), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.listRevisions).not.toHaveBeenCalled()
    })

    it('should use correct query key for caching', async () => {
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(mockRevisions)

      const { result } = renderHook(() => useRevisionHistory('test-post', 10, 30), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cachedData = queryClient.getQueryData([
        'revisionHistory',
        'test-post',
        { skip: 10, limit: 30 },
      ])
      expect(cachedData).toEqual(mockRevisions)
    })

    it('should handle empty revision list', async () => {
      const emptyResponse: ListRevisionsResponse = {
        revisions: [],
        total_count: 0,
        has_more: false,
      }
      vi.mocked(revisionsApi.listRevisions).mockResolvedValueOnce(emptyResponse)

      const { result } = renderHook(() => useRevisionHistory('new-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.revisions).toEqual([])
      expect(result.current.data?.total_count).toBe(0)
    })

    it('should handle forbidden error', async () => {
      const mockError = new Error('Forbidden')
      vi.mocked(revisionsApi.listRevisions).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevisionHistory('another-users-post'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })
  })

  describe('useRevisionDetail', () => {
    const mockRevisionDetail: RevisionDetail = {
      id: '1',
      commit_sha: 'abc123def456',
      short_sha: 'abc123d',
      author_id: '42',
      timestamp: '2026-02-15T10:00:00Z',
      commit_message: 'Initial commit',
      markdown_content: '# Test Post\n\nContent here',
      html_content: '<h1>Test Post</h1>\n<p>Content here</p>',
      is_current: true,
      is_revert: false,
    }

    it('should call revisionsApi.getRevision with slug and sha', async () => {
      vi.mocked(revisionsApi.getRevision).mockResolvedValueOnce(mockRevisionDetail)

      const { result } = renderHook(() => useRevisionDetail('test-post', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.getRevision).toHaveBeenCalledWith('test-post', 'abc123d', 'mock-token')
      expect(revisionsApi.getRevision).toHaveBeenCalledTimes(1)
    })

    it('should return loading state initially', () => {
      vi.mocked(revisionsApi.getRevision).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useRevisionDetail('test-post', 'abc123d'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return data on successful fetch', async () => {
      vi.mocked(revisionsApi.getRevision).mockResolvedValueOnce(mockRevisionDetail)

      const { result } = renderHook(() => useRevisionDetail('test-post', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockRevisionDetail)
      expect(result.current.isError).toBe(false)
    })

    it('should return error on failed fetch', async () => {
      const mockError = new Error('Revision not found')
      vi.mocked(revisionsApi.getRevision).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevisionDetail('test-post', 'nonexistent'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
      expect(result.current.data).toBeUndefined()
    })

    it('should not fetch when slug is missing', () => {
      const { result } = renderHook(() => useRevisionDetail('', 'abc123d'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getRevision).not.toHaveBeenCalled()
    })

    it('should not fetch when sha is missing', () => {
      const { result } = renderHook(() => useRevisionDetail('test-post', ''), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getRevision).not.toHaveBeenCalled()
    })

    it('should not fetch when both slug and sha are missing', () => {
      const { result } = renderHook(() => useRevisionDetail('', ''), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getRevision).not.toHaveBeenCalled()
    })

    it('should use correct query key for caching', async () => {
      vi.mocked(revisionsApi.getRevision).mockResolvedValueOnce(mockRevisionDetail)

      const { result } = renderHook(() => useRevisionDetail('test-post', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cachedData = queryClient.getQueryData(['revisionDetail', 'test-post', 'abc123d'])
      expect(cachedData).toEqual(mockRevisionDetail)
    })

    it('should handle server error', async () => {
      const mockError = new Error('Internal server error')
      vi.mocked(revisionsApi.getRevision).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevisionDetail('test-post', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle full SHA and short SHA identically', async () => {
      vi.mocked(revisionsApi.getRevision).mockResolvedValueOnce(mockRevisionDetail)

      const { result } = renderHook(
        () => useRevisionDetail('test-post', 'abc123def456789012345678901234567890abcd'),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.getRevision).toHaveBeenCalledWith(
        'test-post',
        'abc123def456789012345678901234567890abcd',
        'mock-token'
      )
    })
  })

  describe('useRevisionDiff', () => {
    const mockDiffResponse: DiffResponse = {
      from_revision: {
        sha: '789ghi0',
        timestamp: '2026-02-15T09:00:00Z',
      },
      to_revision: {
        sha: 'abc123d',
        timestamp: '2026-02-15T10:00:00Z',
      },
      diff_lines: [
        { type: 'context', content: '# Test Post' },
        { type: 'deletion', content: 'Old content' },
        { type: 'addition', content: 'New content' },
        { type: 'context', content: '' },
      ],
    }

    it('should call revisionsApi.getDiff with slug and both SHAs', async () => {
      vi.mocked(revisionsApi.getDiff).mockResolvedValueOnce(mockDiffResponse)

      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.getDiff).toHaveBeenCalledWith(
        'test-post',
        '789ghi0',
        'abc123d',
        'mock-token'
      )
      expect(revisionsApi.getDiff).toHaveBeenCalledTimes(1)
    })

    it('should return loading state initially', () => {
      vi.mocked(revisionsApi.getDiff).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', 'abc123d'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return data on successful fetch', async () => {
      vi.mocked(revisionsApi.getDiff).mockResolvedValueOnce(mockDiffResponse)

      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockDiffResponse)
      expect(result.current.isError).toBe(false)
      expect(result.current.data?.diff_lines).toHaveLength(4)
    })

    it('should return error on failed fetch', async () => {
      const mockError = new Error('Revision not found')
      vi.mocked(revisionsApi.getDiff).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevisionDiff('test-post', 'invalid', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
      expect(result.current.data).toBeUndefined()
    })

    it('should not fetch when slug is missing', () => {
      const { result } = renderHook(() => useRevisionDiff('', '789ghi0', 'abc123d'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getDiff).not.toHaveBeenCalled()
    })

    it('should not fetch when sha1 is missing', () => {
      const { result } = renderHook(() => useRevisionDiff('test-post', '', 'abc123d'), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getDiff).not.toHaveBeenCalled()
    })

    it('should not fetch when sha2 is missing', () => {
      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', ''), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getDiff).not.toHaveBeenCalled()
    })

    it('should not fetch when all parameters are missing', () => {
      const { result } = renderHook(() => useRevisionDiff('', '', ''), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(revisionsApi.getDiff).not.toHaveBeenCalled()
    })

    it('should use correct query key for caching', async () => {
      vi.mocked(revisionsApi.getDiff).mockResolvedValueOnce(mockDiffResponse)

      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const cachedData = queryClient.getQueryData([
        'revisionDiff',
        'test-post',
        '789ghi0',
        'abc123d',
      ])
      expect(cachedData).toEqual(mockDiffResponse)
    })

    it('should handle server error', async () => {
      const mockError = new Error('Internal server error')
      vi.mocked(revisionsApi.getDiff).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', 'abc123d'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle forbidden error', async () => {
      const mockError = new Error('Forbidden')
      vi.mocked(revisionsApi.getDiff).mockRejectedValueOnce(mockError)

      const { result } = renderHook(
        () => useRevisionDiff('another-users-post', '789ghi0', 'abc123d'),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle empty diff', async () => {
      const emptyDiff: DiffResponse = {
        from_revision: { sha: '789ghi0', timestamp: '2026-02-15T09:00:00Z' },
        to_revision: { sha: '789ghi0', timestamp: '2026-02-15T09:00:00Z' },
        diff_lines: [],
      }
      vi.mocked(revisionsApi.getDiff).mockResolvedValueOnce(emptyDiff)

      const { result } = renderHook(() => useRevisionDiff('test-post', '789ghi0', '789ghi0'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.diff_lines).toEqual([])
    })
  })

  describe('useRevertRevision', () => {
    const mockRevertResponse: RevertResponse = {
      success: true,
      message: 'Successfully reverted to revision abc123d',
      new_commit_sha: 'def456abc789',
      redirect_url: '/posts/test-post',
    }

    it('should call revisionsApi.revertToRevision with correct parameters', async () => {
      vi.mocked(revisionsApi.revertToRevision).mockResolvedValueOnce(mockRevertResponse)

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(revisionsApi.revertToRevision).toHaveBeenCalledWith(
        'test-post',
        'abc123d',
        'mock-token'
      )
    })

    it('should invalidate revisionHistory cache on success', async () => {
      vi.mocked(revisionsApi.revertToRevision).mockResolvedValueOnce(mockRevertResponse)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['revisionHistory', 'test-post', {}],
      })
    })

    it('should invalidate revisionDetail cache on success', async () => {
      vi.mocked(revisionsApi.revertToRevision).mockResolvedValueOnce(mockRevertResponse)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['revisionDetail', 'test-post'],
      })
    })

    it('should invalidate both caches on success', async () => {
      vi.mocked(revisionsApi.revertToRevision).mockResolvedValueOnce(mockRevertResponse)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledTimes(2)
    })

    it('should return revert response data', async () => {
      vi.mocked(revisionsApi.revertToRevision).mockResolvedValueOnce(mockRevertResponse)

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual(mockRevertResponse)
      expect(result.current.data?.success).toBe(true)
      expect(result.current.data?.new_commit_sha).toBe('def456abc789')
    })

    it('should handle error on not found', async () => {
      const mockError = new Error('Revision not found')
      vi.mocked(revisionsApi.revertToRevision).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'nonexistent' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle forbidden error', async () => {
      const mockError = new Error('Forbidden')
      vi.mocked(revisionsApi.revertToRevision).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'another-users-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle unauthorized error', async () => {
      const mockError = new Error('Unauthorized')
      vi.mocked(revisionsApi.revertToRevision).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should handle server error', async () => {
      const mockError = new Error('Internal server error')
      vi.mocked(revisionsApi.revertToRevision).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
    })

    it('should be in loading state during mutation', async () => {
      vi.mocked(revisionsApi.revertToRevision).mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })

    it('should not invalidate caches on error', async () => {
      const mockError = new Error('Revert failed')
      vi.mocked(revisionsApi.revertToRevision).mockRejectedValueOnce(mockError)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useRevertRevision(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ slug: 'test-post', targetSha: 'abc123d' })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(invalidateSpy).not.toHaveBeenCalled()
    })
  })
})
