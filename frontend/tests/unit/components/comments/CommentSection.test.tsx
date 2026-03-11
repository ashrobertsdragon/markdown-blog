import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CommentSection } from '@/components/comments/CommentSection'
import {
  useDeleteComment,
  useFetchComments,
  usePostComment,
  useReplyToComment,
} from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'

vi.mock('@/hooks/useComments', () => ({
  useFetchComments: vi.fn(),
  usePostComment: vi.fn(),
  useDeleteComment: vi.fn(),
  useReplyToComment: vi.fn(),
}))
vi.mock('@/hooks/useCommentStream', () => ({
  useCommentStream: vi.fn(() => ({
    isConnected: false,
    isStreaming: false,
    connectionError: null,
  })),
}))
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    getToken: vi.fn(async () => 'mock-token'),
  })),
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>)
}

const makeComment = (overrides: Partial<CommentResponse> = {}): CommentResponse => ({
  id: 1,
  post_id: 10,
  is_post_author: false,
  text: 'A comment',
  parent_id: null,
  created_at: '2026-03-01T10:00:00Z',
  updated_at: '2026-03-01T10:00:00Z',
  is_deleted: false,
  is_pending_moderation: false,
  ...overrides,
})

/**
 * Test suite for CommentSection component
 *
 * Verifies the composition of the comment list with its loading, error,
 * and empty states, comment rendering, and that comments pending
 * moderation are hidden from non-admin readers.
 */
describe('CommentSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usePostComment).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      isIdle: true,
      isSuccess: false,
      reset: vi.fn(),
      mutateAsync: vi.fn(),
      data: undefined,
      failureCount: 0,
      failureReason: null,
      isPaused: false,
      status: 'idle',
      submittedAt: 0,
      variables: undefined,
      context: undefined,
    } as never)
    vi.mocked(useDeleteComment).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      isIdle: true,
      isSuccess: false,
      reset: vi.fn(),
      mutateAsync: vi.fn(),
      data: undefined,
      failureCount: 0,
      failureReason: null,
      isPaused: false,
      status: 'idle' as const,
      submittedAt: 0,
      variables: undefined,
      context: undefined,
    } as never)
    vi.mocked(useReplyToComment).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      isIdle: true,
      isSuccess: false,
      reset: vi.fn(),
      mutateAsync: vi.fn(),
      data: undefined,
      failureCount: 0,
      failureReason: null,
      isPaused: false,
      status: 'idle' as const,
      submittedAt: 0,
      variables: undefined,
      context: undefined,
    } as never)
  })

  /**
   * CommentForm must always be present so signed-in users can post
   * without scrolling past the list.
   */
  it('renders the CommentForm component', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: { comments: [], total_count: 0, has_more: false },
      isLoading: false,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  /**
   * A loading indicator must be shown while comments are being fetched
   * so users know content is on its way.
   */
  it('shows loading text when isLoading is true', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText(/loading comments/i)).toBeInTheDocument()
  })

  /**
   * An error message must be shown when the fetch fails so users are
   * not left staring at a blank section with no explanation.
   */
  it('shows error message when isError is true', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText(/failed to load comments/i)).toBeInTheDocument()
  })

  /**
   * "No comments yet" must be shown for posts with an empty comment
   * list so users understand discussion has not started rather than
   * assuming a loading failure.
   */
  it('shows "No comments yet" when comments array is empty', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: { comments: [], total_count: 0, has_more: false },
      isLoading: false,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText(/no comments yet/i)).toBeInTheDocument()
  })

  /**
   * Comment text must be rendered so users can read the discussion.
   */
  it('renders comment text when comments are present', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: {
        comments: [makeComment({ text: 'Great article!' })],
        total_count: 1,
        has_more: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText('Great article!')).toBeInTheDocument()
  })

  /**
   * All visible comments must be rendered when multiple are returned so
   * the full discussion is available.
   */
  it('renders multiple comments', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: {
        comments: [
          makeComment({ id: 1, text: 'First comment' }),
          makeComment({ id: 2, text: 'Second comment' }),
          makeComment({ id: 3, text: 'Third comment' }),
        ],
        total_count: 3,
        has_more: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText('First comment')).toBeInTheDocument()
    expect(screen.getByText('Second comment')).toBeInTheDocument()
    expect(screen.getByText('Third comment')).toBeInTheDocument()
  })

  /**
   * Comment text must be visible for each comment so readers can read
   * the discussion content.
   */
  it('renders comment text for each comment', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: {
        comments: [
          makeComment({ id: 1, is_post_author: false, text: 'Hello' }),
          makeComment({ id: 2, is_post_author: false, text: 'World' }),
        ],
        total_count: 2,
        has_more: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByText('World')).toBeInTheDocument()
  })

  /**
   * Comments pending moderation must not appear in the list for non-
   * admin users to prevent unreviewed content from being surfaced.
   */
  it('does not render comments where is_pending_moderation is true', () => {
    vi.mocked(useFetchComments).mockReturnValue({
      data: {
        comments: [
          makeComment({ id: 1, text: 'Approved comment', is_pending_moderation: false }),
          makeComment({ id: 2, text: 'Pending comment', is_pending_moderation: true }),
        ],
        total_count: 2,
        has_more: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as never)

    renderWithQueryClient(<CommentSection postSlug="test-post" />)

    expect(screen.getByText('Approved comment')).toBeInTheDocument()
    expect(screen.queryByText('Pending comment')).not.toBeInTheDocument()
  })
})
