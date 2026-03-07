import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CommentModerateButton } from '@/components/comments/CommentModerateButton'

const { mockApprove, mockAdminDelete } = vi.hoisted(() => ({
  mockApprove: vi.fn(),
  mockAdminDelete: vi.fn(),
}))

vi.mock('@/hooks/useComments', () => ({
  useApproveComment: mockApprove,
  useAdminDeleteComment: mockAdminDelete,
}))
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    getToken: vi.fn(async () => 'mock-token'),
    isLoaded: true,
    user: null,
    role: 'admin' as const,
  })),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const makeMockMutation = (overrides: Record<string, unknown> = {}) => ({
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
  ...overrides,
})

/**
 * Test suite for CommentModerateButton component
 *
 * Covers approve and admin-delete interactions, confirmation dialog
 * before destructive delete, and disabled states while mutations are pending.
 */
describe('CommentModerateButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApprove.mockReturnValue(makeMockMutation())
    mockAdminDelete.mockReturnValue(makeMockMutation())
  })

  /**
   * Both actions must be visible so admins can take action without
   * hunting through menus.
   */
  it('renders Approve and Delete buttons', () => {
    renderWithQueryClient(<CommentModerateButton commentId={1} postSlug="test-post" />)

    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
  })

  /**
   * Approve must call the mutation with the correct commentId immediately
   * without requiring a confirmation dialog, to minimise friction during
   * bulk moderation.
   */
  it('calls useApproveComment.mutate with correct commentId when Approve is clicked', async () => {
    const approveMutate = vi.fn()
    mockApprove.mockReturnValue(makeMockMutation({ mutate: approveMutate }))

    renderWithQueryClient(<CommentModerateButton commentId={42} postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /approve/i }))

    expect(approveMutate).toHaveBeenCalledOnce()
    expect(approveMutate).toHaveBeenCalledWith({ commentId: 42 })
  })

  /**
   * Delete is destructive and irreversible — the AlertDialog confirmation
   * must intercept the action before the mutation fires to prevent
   * accidental permanent removal.
   */
  it('opens confirmation dialog when Delete button is clicked', async () => {
    renderWithQueryClient(<CommentModerateButton commentId={1} postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /delete/i }))

    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
  })

  /**
   * Confirming the dialog must invoke the admin delete mutation with the
   * correct commentId so the backend removes the correct record.
   */
  it('calls useAdminDeleteComment.mutate with correct commentId when deletion is confirmed', async () => {
    const deleteMutate = vi.fn()
    mockAdminDelete.mockReturnValue(makeMockMutation({ mutate: deleteMutate }))

    renderWithQueryClient(<CommentModerateButton commentId={7} postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    const confirmButton = await screen.findByRole('button', { name: /confirm|yes|delete/i })
    await userEvent.click(confirmButton)

    expect(deleteMutate).toHaveBeenCalledOnce()
    expect(deleteMutate).toHaveBeenCalledWith({ commentId: 7 })
  })

  /**
   * Cancelling the dialog must NOT fire the delete mutation — the admin
   * explicitly chose to abort the action.
   */
  it('does not call useAdminDeleteComment.mutate when dialog is cancelled', async () => {
    const deleteMutate = vi.fn()
    mockAdminDelete.mockReturnValue(makeMockMutation({ mutate: deleteMutate }))

    renderWithQueryClient(<CommentModerateButton commentId={1} postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    const cancelButton = await screen.findByRole('button', { name: /cancel/i })
    await userEvent.click(cancelButton)

    expect(deleteMutate).not.toHaveBeenCalled()
  })

  /**
   * Both buttons must be disabled while any mutation is in flight to
   * prevent duplicate submissions during slow network conditions.
   */
  it('disables both buttons while approve mutation isPending', () => {
    mockApprove.mockReturnValue(makeMockMutation({ isPending: true, status: 'pending' }))

    renderWithQueryClient(<CommentModerateButton commentId={1} postSlug="test-post" />)

    expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /delete/i })).toBeDisabled()
  })

  /**
   * Both buttons must be disabled while the delete mutation is in flight
   * for the same reason.
   */
  it('disables both buttons while admin delete mutation isPending', () => {
    mockAdminDelete.mockReturnValue(makeMockMutation({ isPending: true, status: 'pending' }))

    renderWithQueryClient(<CommentModerateButton commentId={1} postSlug="test-post" />)

    expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /delete/i })).toBeDisabled()
  })

  /**
   * The onModerated callback must fire after a successful approve so the
   * parent can refresh or remove the comment from its list.
   */
  it('calls onModerated callback after successful approve', async () => {
    const onModerated = vi.fn()
    const approveMutate = vi.fn((_vars: unknown, options?: { onSuccess?: () => void }) => {
      options?.onSuccess?.()
    })
    mockApprove.mockReturnValue(makeMockMutation({ mutate: approveMutate }))

    renderWithQueryClient(
      <CommentModerateButton commentId={1} postSlug="test-post" onModerated={onModerated} />
    )

    await userEvent.click(screen.getByRole('button', { name: /approve/i }))

    await waitFor(() => expect(onModerated).toHaveBeenCalled())
  })
})
