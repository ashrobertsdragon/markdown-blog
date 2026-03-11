import { QueryClient, QueryClientProvider, type UseMutationResult } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReplyForm } from '@/components/comments/ReplyForm'
import { useReplyToComment } from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'
import { createMockComment } from '../../../fixtures/comments.fixtures'

vi.mock('@/hooks/useComments', () => ({
  useReplyToComment: vi.fn(),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const createMockMutation = (
  overrides: Partial<
    UseMutationResult<CommentResponse, Error, { slug: string; parentId: number; text: string }>
  > = {}
): UseMutationResult<CommentResponse, Error, { slug: string; parentId: number; text: string }> =>
  ({
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
    ...overrides,
  }) as UseMutationResult<CommentResponse, Error, { slug: string; parentId: number; text: string }>

/**
 * Test suite for ReplyForm component
 *
 * Covers the full reply form surface: pre-filled mention, character counter
 * (excluding the mention prefix), submit gating (empty body, over-limit,
 * pending), whitespace-only guard in handleSubmit, cancel, successful
 * submission args, onCancel-after-success, and error display including
 * the rate-limit retryAfter message.
 */
describe('ReplyForm', () => {
  const mockMutate = vi.fn()
  const parentComment = createMockComment({ id: 42 })
  const parentMention = '@comment42 '
  const maxReplyLength = 5000 - parentMention.length

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useReplyToComment).mockReturnValue(createMockMutation({ mutate: mockMutate }))
  })

  /**
   * Textarea must be pre-filled with the parent mention so the user
   * immediately sees whom they are replying to.
   */
  it('pre-fills textarea with parent comment mention', () => {
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    expect(screen.getByRole('textbox')).toHaveValue(parentMention)
  })

  /**
   * Reply button must be disabled when no body text has been added
   * beyond the pre-filled mention so blank replies cannot be submitted.
   */
  it('reply button is disabled when body is empty', () => {
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    expect(screen.getByRole('button', { name: /reply/i })).toBeDisabled()
  })

  /**
   * Reply button must be enabled once the user has typed at least one
   * character of body text beyond the mention prefix.
   */
  it('reply button is enabled when body text is present', () => {
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}hello` },
    })

    expect(screen.getByRole('button', { name: /reply/i })).toBeEnabled()
  })

  /**
   * Reply button must be disabled when the body length plus the mention
   * prefix exceeds the 5000-character hard limit.
   */
  it('reply button is disabled when body exceeds max length', () => {
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}${'a'.repeat(maxReplyLength + 1)}` },
    })

    expect(screen.getByRole('button', { name: /reply/i })).toBeDisabled()
  })

  /**
   * Reply button must be disabled during an in-flight mutation to prevent
   * duplicate submissions.
   */
  it('reply button is disabled when mutation is pending', () => {
    vi.mocked(useReplyToComment).mockReturnValue(
      createMockMutation({ mutate: mockMutate, isPending: true, isIdle: false, status: 'pending' })
    )
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}hello` },
    })

    expect(screen.getByRole('button', { name: /reply/i })).toBeDisabled()
  })

  /**
   * The character counter must show body length against the effective max
   * (total limit minus mention prefix) so users know how much space remains.
   */
  it('character counter reflects body length excluding mention prefix', () => {
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}hello` },
    })

    expect(screen.getByText(`5 / ${maxReplyLength}`)).toBeInTheDocument()
  })

  /**
   * Cancel button must invoke onCancel immediately without any mutation
   * so the user can dismiss the form without side effects.
   */
  it('cancel button calls onCancel', async () => {
    const onCancel = vi.fn()
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={onCancel} />
    )

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  /**
   * On submit mutate must receive the full textarea value (mention +
   * body) as text so the backend can preserve the @mention thread link.
   */
  it('calls mutate with slug, parentId, and full text on submit', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}great reply` },
    })
    await user.click(screen.getByRole('button', { name: /reply/i }))

    expect(mockMutate).toHaveBeenCalledWith(
      { slug: 'test-post', parentId: 42, text: `${parentMention}great reply` },
      expect.any(Object)
    )
  })

  /**
   * A whitespace-only body must not reach the API — the handleSubmit guard
   * must bail before calling mutate when the trimmed reply is empty.
   */
  it('does not call mutate when reply body is whitespace only', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}   ` },
    })
    await user.click(screen.getByRole('button', { name: /reply/i }))

    expect(mockMutate).not.toHaveBeenCalled()
  })

  /**
   * After a successful reply the onCancel callback must fire so the parent
   * component can hide the reply form without user interaction.
   */
  it('calls onCancel after successful mutation via onSuccess callback', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={onCancel} />
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: `${parentMention}great reply` },
    })
    await user.click(screen.getByRole('button', { name: /reply/i }))

    const onSuccess = mockMutate.mock.calls[0][1].onSuccess
    act(() => {
      onSuccess()
    })

    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  /**
   * When the error carries a retryAfter value the form must surface the
   * specific wait time so users know when they can try again.
   */
  it('shows rate-limit message when error has retryAfter', () => {
    const rateLimitError = Object.assign(new Error('Rate limited'), { retryAfter: 60 })
    vi.mocked(useReplyToComment).mockReturnValue(
      createMockMutation({
        mutate: mockMutate,
        isError: true,
        error: rateLimitError,
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/please wait 60 seconds/i)).toBeInTheDocument()
  })

  /**
   * A generic error without retryAfter must show the raw error message
   * so users understand what went wrong.
   */
  it('shows generic error message when isError is true without retryAfter', () => {
    vi.mocked(useReplyToComment).mockReturnValue(
      createMockMutation({
        mutate: mockMutate,
        isError: true,
        error: new Error('Something went wrong'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )
    renderWithQueryClient(
      <ReplyForm parentComment={parentComment} postSlug="test-post" onCancel={vi.fn()} />
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
  })
})
