import type { UseMutationResult } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UnsubscribeParams } from '@/hooks/useUnsubscribe'
import { useUnsubscribe } from '@/hooks/useUnsubscribe'
import type { UnsubscribeResponse } from '@/services/notificationsApi'
import { render, screen, waitFor } from '../../test-utils'

vi.mock('@/hooks/useUnsubscribe', () => ({
  useUnsubscribe: vi.fn(),
}))

const TOKEN = 'a'.repeat(64)

const STUB_PARAMS: UnsubscribeParams = { user_id: 1, token: TOKEN }

const idleMutation: UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams> = {
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  isIdle: true,
  error: null,
  data: undefined,
  reset: vi.fn(),
  failureCount: 0,
  failureReason: null,
  isPaused: false,
  status: 'idle',
  submittedAt: 0,
  variables: undefined,
  context: undefined,
} as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>

/**
 * Test suite for the Unsubscribe page
 *
 * Verifies loading state, success/error alert rendering, auto-dismiss behaviour,
 * client-side parameter validation, and the home link shown on success.
 */
describe('Unsubscribe page', () => {
  beforeEach(() => {
    vi.mocked(useUnsubscribe).mockReturnValue(idleMutation)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  it('renders loading spinner initially', () => {
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      isPending: true,
      isIdle: false,
      status: 'pending',
      variables: STUB_PARAMS,
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`],
    })

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows success alert when unsubscribe succeeds', async () => {
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      isSuccess: true,
      isIdle: false,
      status: 'success',
      variables: STUB_PARAMS,
      data: { message: 'Successfully unsubscribed from all notifications', user_id: 1 },
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`],
    })

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent(/unsubscribed/i)
  })

  it('auto-dismisses success message after 3 seconds', async () => {
    vi.useFakeTimers()

    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      isSuccess: true,
      isIdle: false,
      status: 'success',
      variables: STUB_PARAMS,
      data: { message: 'Successfully unsubscribed from all notifications', user_id: 1 },
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`],
    })

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())

    vi.advanceTimersByTime(3000)

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('shows error alert when unsubscribe fails', async () => {
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      isError: true,
      isIdle: false,
      status: 'error',
      variables: STUB_PARAMS,
      error: new Error('Invalid or expired unsubscribe link. Check your email.'),
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`],
    })

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent(/invalid or expired unsubscribe link/i)
  })

  it('displays error when user_id param is missing and does not call mutate', () => {
    const mockMutate = vi.fn()
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      mutate: mockMutate,
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?token=${TOKEN}`],
    })

    expect(screen.getByRole('alert')).toHaveTextContent(/user_id/i)
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('displays error when token param is missing and does not call mutate', () => {
    const mockMutate = vi.fn()
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      mutate: mockMutate,
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: ['/unsubscribe?user_id=1'],
    })

    expect(screen.getByRole('alert')).toHaveTextContent(/token/i)
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('displays error when token is not 64 hex characters and does not call mutate', () => {
    const mockMutate = vi.fn()
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      mutate: mockMutate,
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: ['/unsubscribe?user_id=1&token=tooshort'],
    })

    expect(screen.getByRole('alert')).toHaveTextContent(/invalid.*token/i)
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('displays error when user_id is not numeric and does not call mutate', () => {
    const mockMutate = vi.fn()
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      mutate: mockMutate,
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?user_id=abc&token=${TOKEN}`],
    })

    expect(screen.getByRole('alert')).toHaveTextContent(/invalid.*user/i)
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('shows link to home on success', async () => {
    vi.mocked(useUnsubscribe).mockReturnValue({
      ...idleMutation,
      isSuccess: true,
      isIdle: false,
      status: 'success',
      variables: STUB_PARAMS,
      data: { message: 'Successfully unsubscribed from all notifications', user_id: 1 },
    } as unknown as UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams>)

    render(undefined as unknown as React.ReactElement, {
      initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`],
    })

    await waitFor(() =>
      expect(screen.getByRole('link', { name: /go to home|home/i })).toBeInTheDocument()
    )
  })
})
