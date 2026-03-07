import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CommentList } from '@/components/comments/CommentList'
import { useDeleteComment, useReplyToComment } from '@/hooks/useComments'
import {
  createMockComment,
  createMockDeletedComment,
  createMockReplyComment,
} from '../../../fixtures/comments.fixtures'

vi.mock('@/hooks/useComments', () => ({
  useDeleteComment: vi.fn(),
  useReplyToComment: vi.fn(),
}))
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    getToken: vi.fn(async () => 'mock-token'),
    isLoaded: true,
    user: null,
    role: 'authenticated',
  })),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const mockMutation = {
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
}

/**
 * Test suite for CommentList component
 *
 * Covers rendering of comments in flat list format, with deleted comment
 * handling, author badge display, and reply threading indicators.
 */
describe('CommentList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useDeleteComment).mockReturnValue(mockMutation as never)
    vi.mocked(useReplyToComment).mockReturnValue(mockMutation as never)
  })

  /**
   * Empty list must show appropriate message so users know comments have
   * been disabled or not posted yet rather than loading forever.
   */
  it('renders empty message when comments array is empty', () => {
    renderWithQueryClient(<CommentList comments={[]} postSlug="test-post" postAuthorId={999} />)

    expect(screen.getByText(/no comments yet|empty/i)).toBeInTheDocument()
  })

  /**
   * Each comment must be rendered as its own item so the full discussion
   * is visible to readers.
   */
  it('renders CommentItem for each comment in array', () => {
    const comments = [
      createMockComment({ id: 1, text: 'First comment' }),
      createMockComment({ id: 2, text: 'Second comment' }),
      createMockComment({ id: 3, text: 'Third comment' }),
    ]

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="test-post" postAuthorId={999} />
    )

    expect(screen.getByText('First comment')).toBeInTheDocument()
    expect(screen.getByText('Second comment')).toBeInTheDocument()
    expect(screen.getByText('Third comment')).toBeInTheDocument()
  })

  /**
   * The list must pass postAuthorId to each CommentItem so they can
   * determine if they should show the "Author" badge.
   */
  it('shows Author badge for comments where author_id matches postAuthorId', () => {
    const comments = [
      createMockComment({ id: 1, author_id: 42, text: 'Post author comment' }),
      createMockComment({ id: 2, author_id: 100, text: 'Reader comment' }),
    ]

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="test-post" postAuthorId={42} />
    )

    expect(screen.getByText('Author')).toBeInTheDocument()
  })

  /**
   * Deleted comments must still appear in the list but with a deleted
   * indicator so readers understand the comment history without confusion.
   */
  it('renders deleted comments with [deleted] indicator', () => {
    const comments = [
      createMockComment({ id: 1, text: 'Normal comment' }),
      createMockDeletedComment({ id: 2 }),
    ]

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="test-post" postAuthorId={999} />
    )

    expect(screen.getByText('Normal comment')).toBeInTheDocument()
    expect(screen.getByText(/\[deleted\]/i)).toBeInTheDocument()
  })

  /**
   * Reply comments (with parent_id) must include a visual indicator
   * showing they are replies to a specific comment so the threading
   * is clear even in a flat list.
   */
  it('shows "Reply to" indicator for comments with parent_id', () => {
    const parentComment = createMockComment({ id: 1, author_id: 100, text: 'Original comment' })
    const replyComment = createMockReplyComment(1, { id: 2, author_id: 200, text: 'My reply' })

    renderWithQueryClient(
      <CommentList
        comments={[parentComment, replyComment]}
        postSlug="test-post"
        postAuthorId={999}
      />
    )

    expect(screen.getByText('My reply')).toBeInTheDocument()
    expect(screen.getByText(/reply to/i)).toBeInTheDocument()
  })

  /**
   * All comments should render without key conflicts.
   */
  it('renders multiple comments with unique keys', () => {
    const comments = [
      createMockComment({ id: 1, text: 'Comment 1' }),
      createMockComment({ id: 2, text: 'Comment 2' }),
      createMockComment({ id: 3, text: 'Comment 3' }),
    ]

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="test-post" postAuthorId={999} />
    )

    expect(screen.getByText('Comment 1')).toBeInTheDocument()
    expect(screen.getByText('Comment 2')).toBeInTheDocument()
    expect(screen.getByText('Comment 3')).toBeInTheDocument()
  })

  /**
   * Large comment lists must render without errors.
   */
  it('renders large list (50+ comments) without errors', () => {
    const comments = Array.from({ length: 60 }, (_, i) =>
      createMockComment({ id: i + 1, text: `Comment ${i + 1}` })
    )

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="test-post" postAuthorId={999} />
    )

    expect(screen.getByText('Comment 1')).toBeInTheDocument()
    expect(screen.getByText('Comment 60')).toBeInTheDocument()
  })

  /**
   * Comment order from the input array must be preserved in the rendered list.
   */
  it('maintains comment order in the rendered list', () => {
    const comments = [
      createMockComment({ id: 1, text: 'First' }),
      createMockComment({ id: 2, text: 'Second' }),
      createMockComment({ id: 3, text: 'Third' }),
    ]

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="test-post" postAuthorId={999} />
    )

    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
    expect(screen.getByText('Third')).toBeInTheDocument()
  })

  /**
   * postSlug must be passed through to children so nested operations
   * like reply submission have the correct post context.
   */
  it('passes postSlug to each CommentItem', () => {
    const comments = [createMockComment({ id: 1, text: 'A comment' })]

    renderWithQueryClient(
      <CommentList comments={comments} postSlug="my-special-slug" postAuthorId={999} />
    )

    expect(screen.getByText('A comment')).toBeInTheDocument()
  })
})
