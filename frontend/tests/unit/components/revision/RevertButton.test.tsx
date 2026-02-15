import { QueryClient, QueryClientProvider, type UseMutationResult } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RevertButton } from '@/components/revision/RevertButton'
import { useRevertRevision } from '@/hooks/useRevisions'
import type { RevertResponse } from '@/services/revisionsApi'

vi.mock('@/hooks/useRevisions', () => ({
  useRevertRevision: vi.fn(),
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>)
}

describe('RevertButton', () => {
  const mockMutate = vi.fn()
  const mockReset = vi.fn()

  const defaultProps = {
    slug: 'test-post',
    targetSha: 'abc123def456',
    commitMessage: 'Initial commit',
    onSuccess: vi.fn(),
  }

  const createMockMutationResult = (
    overrides: Partial<
      UseMutationResult<RevertResponse, Error, { slug: string; targetSha: string }>
    > = {}
  ): UseMutationResult<RevertResponse, Error, { slug: string; targetSha: string }> =>
    ({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      error: null,
      reset: mockReset,
      data: undefined,
      isIdle: true,
      isSuccess: false,
      failureCount: 0,
      failureReason: null,
      isPaused: false,
      status: 'idle',
      submittedAt: 0,
      variables: undefined,
      mutateAsync: vi.fn(),
      context: undefined,
      ...overrides,
    }) as UseMutationResult<RevertResponse, Error, { slug: string; targetSha: string }>

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useRevertRevision).mockReturnValue(createMockMutationResult())
  })

  it('renders revert button with correct label', () => {
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    expect(screen.getByRole('button', { name: /revert/i })).toBeInTheDocument()
  })

  it('opens confirmation dialog when button is clicked', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    const button = screen.getByRole('button', { name: /revert/i })
    await user.click(button)

    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText(/confirm revert/i)).toBeInTheDocument()
  })

  it('displays commit message in dialog description', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByText(/abc123d: Initial commit/i)).toBeInTheDocument()
  })

  it('displays short SHA (7 characters) in dialog description', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByText(/abc123d/i)).toBeInTheDocument()
    expect(screen.queryByText(/abc123def456/i)).not.toBeInTheDocument()
  })

  it('closes dialog when cancel button is clicked', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })

  it('calls mutate when confirm button is clicked', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    expect(mockMutate).toHaveBeenCalledWith(
      {
        slug: 'test-post',
        targetSha: 'abc123def456',
      },
      expect.any(Object)
    )
  })

  it('calls onSuccess callback after successful revert', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()

    renderWithQueryClient(<RevertButton {...defaultProps} onSuccess={onSuccess} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    const mutateCall = mockMutate.mock.calls[0][1]
    mutateCall.onSuccess()

    expect(onSuccess).toHaveBeenCalled()
  })

  it('closes dialog after successful revert', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    const mutateCall = mockMutate.mock.calls[0][1]
    mutateCall.onSuccess()

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })

  it('disables button when isPending is true', () => {
    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: true,
        isIdle: false,
        status: 'pending',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    const button = screen.getByRole('button', { name: /revert to revision abc123d/i })
    expect(button).toBeDisabled()
    expect(button).toHaveTextContent(/reverting/i)
  })

  it('shows loading text when isPending is true', () => {
    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: true,
        isIdle: false,
        status: 'pending',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    expect(screen.getByText(/reverting/i)).toBeInTheDocument()
  })

  it('disables confirm button when isPending is true', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: true,
        isIdle: false,
        status: 'pending',
      })
    )

    const confirmButton = screen.getByRole('button', { name: /confirm/i })
    await user.click(confirmButton)

    expect(mockMutate).toHaveBeenCalled()
  })

  it('displays error message when isError is true', () => {
    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: false,
        isError: true,
        error: new Error('Revert failed'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/revert failed/i)).toBeInTheDocument()
  })

  it('shows error message in alert component', () => {
    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: false,
        isError: true,
        error: new Error('Network error'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    expect(screen.getByText(/network error/i)).toBeInTheDocument()
  })

  it('clears error when reset is called after error', () => {
    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: false,
        isError: true,
        error: new Error('Revert failed'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    expect(mockReset).not.toHaveBeenCalled()
  })

  it('renders with variant destructive for warning', () => {
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    const button = screen.getByRole('button', { name: /revert/i })
    expect(button).toHaveClass('bg-destructive')
  })

  it('handles commit message truncation for long messages', async () => {
    const user = userEvent.setup()
    const longMessage = 'A'.repeat(200)
    renderWithQueryClient(<RevertButton {...defaultProps} commitMessage={longMessage} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByText(new RegExp(longMessage.slice(0, 50)))).toBeInTheDocument()
  })

  it('handles empty commit message', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} commitMessage="" />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByText(/abc123d:/i)).toBeInTheDocument()
  })

  it('has proper aria-label for accessibility', () => {
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    const button = screen.getByRole('button', { name: /revert to revision abc123d/i })
    expect(button).toBeInTheDocument()
  })

  it('dialog has proper aria-labels', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByRole('alertdialog')).toHaveAttribute('aria-describedby')
  })

  it('prevents multiple simultaneous revert operations', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    const confirmButton = screen.getByRole('button', { name: /confirm/i })
    await user.click(confirmButton)

    expect(mockMutate).toHaveBeenCalledTimes(1)
  })

  it('renders error alert with proper role', () => {
    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: false,
        isError: true,
        error: new Error('Failed'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
  })

  it('handles SHA shorter than 7 characters', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} targetSha="abc" />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByText(/abc:/i)).toBeInTheDocument()
  })

  it('resets error state when dialog is reopened', async () => {
    const user = userEvent.setup()

    vi.mocked(useRevertRevision).mockReturnValue(
      createMockMutationResult({
        isPending: false,
        isError: true,
        error: new Error('Previous error'),
        isIdle: false,
        failureCount: 1,
        status: 'error',
      })
    )

    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(mockReset).toHaveBeenCalled()
  })

  it('maintains focus management in dialog', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    const revertButton = screen.getByRole('button', { name: /revert/i })
    await user.click(revertButton)

    const dialog = screen.getByRole('alertdialog')
    expect(dialog).toBeInTheDocument()

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })

  it('displays warning in dialog description', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByText(/will overwrite the current draft/i)).toBeInTheDocument()
  })

  it('uses destructive variant for confirm button', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))

    const confirmButton = screen.getByRole('button', { name: /confirm/i })
    expect(confirmButton).toHaveClass('bg-destructive')
  })

  it('allows reopening dialog after cancellation', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))
    await user.click(screen.getByRole('button', { name: /cancel/i }))

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /revert/i }))

    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
  })

  it('handles rapid open/close cycles', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<RevertButton {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /revert/i }))
    await user.keyboard('{Escape}')
    await user.click(screen.getByRole('button', { name: /revert/i }))
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })
})
