import { QueryClient, QueryClientProvider, type UseMutationResult } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CommentForm } from '@/components/comments/CommentForm'
import { usePostComment } from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'

vi.mock('@/hooks/useComments', () => ({
  usePostComment: vi.fn(),
}))
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({ isSignedIn: true })),
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>)
}

/**
 * Test suite for CommentForm component
 *
 * Covers the full surface of the comment submission form: access
 * control, validation constraints (empty / length), character counter
 * feedback, submission flow, post-success cleanup, and error display
 * including the special rate-limit message.
 */
describe('CommentForm', () => {
  const mockMutate = vi.fn()

  const createMockMutation = (
    overrides: Partial<
      UseMutationResult<CommentResponse, Error, { slug: string; text: string }>
    > = {}
  ): UseMutationResult<CommentResponse, Error, { slug: string; text: string }> =>
    ({
      mutate: mockMutate,
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
    }) as UseMutationResult<CommentResponse, Error, { slug: string; text: string }>

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usePostComment).mockReturnValue(createMockMutation())
  })

  /**
   * Verifies the form renders the textarea when the user is signed in,
   * since the component gates rendering on authentication state.
   */
  it('renders textarea when isSignedIn is true', () => {
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  /**
   * Verifies the unauthenticated state renders a sign-in prompt and no
   * textarea, preventing anonymous submissions from reaching the form.
   */
  it('shows "Sign in to comment" and no textarea when isSignedIn is false', async () => {
    const { useAuth } = await import('@/hooks/useAuth')
    vi.mocked(useAuth).mockReturnValueOnce({
      isSignedIn: false,
      getToken: vi.fn(),
      isLoaded: true,
      user: null,
      role: 'authenticated',
    })

    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    expect(screen.getByText(/sign in to comment/i)).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  /**
   * Submit button must be disabled when the textarea is empty to
   * prevent submitting blank comments.
   */
  it('submit button is disabled when text is empty', () => {
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    expect(screen.getByRole('button', { name: /submit/i })).toBeDisabled()
  })

  /**
   * Submit button must be disabled when text exceeds 5000 characters
   * to match the backend validation limit.
   */
  it('submit button is disabled when text exceeds 5000 characters', () => {
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'a'.repeat(5001) } })

    expect(screen.getByRole('button', { name: /submit/i })).toBeDisabled()
  })

  /**
   * Submit button must be enabled for any non-empty text up to and
   * including the 5000-character limit.
   */
  it('submit button is enabled when text is between 1 and 5000 characters', () => {
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hello world' } })

    expect(screen.getByRole('button', { name: /submit/i })).toBeEnabled()
  })

  /**
   * The character counter must be visible so users know the limit
   * before they start typing.
   */
  it('shows character counter "0 / 5000" when textarea is empty', () => {
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    expect(screen.getByText('0 / 5000')).toBeInTheDocument()
  })

  /**
   * Counter must reflect the live character count so users can self-
   * moderate before hitting the limit.
   */
  it('character counter updates as user types', () => {
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hello' } })

    expect(screen.getByText('5 / 5000')).toBeInTheDocument()
  })

  /**
   * On submit, mutate must receive the exact slug and trimmed text so
   * the correct post receives the comment.
   */
  it('calls mutate with { slug, text } on form submission', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'My comment text' } })
    await user.click(screen.getByRole('button', { name: /submit/i }))

    expect(mockMutate).toHaveBeenCalledWith(
      { slug: 'test-post', text: 'My comment text' },
      expect.any(Object)
    )
  })

  /**
   * After a successful submission the textarea must be cleared so the
   * user can immediately write another comment without manual clearing.
   */
  it('clears textarea after successful submission via onSuccess callback', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'My comment text' } })
    await user.click(screen.getByRole('button', { name: /submit/i }))

    const onSuccessCallback = mockMutate.mock.calls[0][1].onSuccess
    act(() => {
      onSuccessCallback()
    })

    expect(screen.getByRole('textbox')).toHaveValue('')
  })

  /**
   * The onCommentPosted prop callback must fire after success so parent
   * components can react (e.g. refetch, scroll to new comment).
   */
  it('calls onCommentPosted after successful submission', async () => {
    const user = userEvent.setup()
    const onCommentPosted = vi.fn()
    renderWithQueryClient(<CommentForm postSlug="test-post" onCommentPosted={onCommentPosted} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'My comment text' } })
    await user.click(screen.getByRole('button', { name: /submit/i }))

    const onSuccessCallback = mockMutate.mock.calls[0][1].onSuccess
    act(() => {
      onSuccessCallback()
    })

    expect(onCommentPosted).toHaveBeenCalledTimes(1)
  })

  /**
   * Submit button must be disabled while a mutation is in flight to
   * prevent duplicate submissions.
   */
  it('submit button is disabled when isPending is true', () => {
    vi.mocked(usePostComment).mockReturnValue(
      createMockMutation({ isPending: true, isIdle: false, status: 'pending' })
    )
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hello' } })

    expect(screen.getByRole('button', { name: /submit/i })).toBeDisabled()
  })

  /**
   * A generic error message must be visible when the mutation enters
   * the error state so the user knows the submission failed.
   */
  it('shows a generic error message when isError is true', () => {
    vi.mocked(usePostComment).mockReturnValue(
      createMockMutation({
        isError: true,
        error: new Error('Something went wrong'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
  })

  /**
   * When the error carries a retryAfter value the form must surface the
   * specific wait time so users know when they can try again instead of
   * seeing a generic failure message.
   */
  it('shows rate limit message "Please wait 30 seconds" when error has retryAfter: 30', () => {
    const rateLimitError = Object.assign(new Error('Rate limit exceeded'), { retryAfter: 30 })
    vi.mocked(usePostComment).mockReturnValue(
      createMockMutation({
        isError: true,
        error: rateLimitError,
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )
    renderWithQueryClient(<CommentForm postSlug="test-post" />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/please wait 30 seconds/i)).toBeInTheDocument()
  })
})
