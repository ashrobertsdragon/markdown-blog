import { act } from '@testing-library/react'
import type { AxiosResponse } from 'axios'
import axios, { AxiosError } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '../../test-utils'

const TOKEN = 'a'.repeat(64)

/** Build a minimal AxiosError with the given status and error body. */
function makeAxiosError(status: number, errorText: string): AxiosError {
  const err = new AxiosError(`Request failed with status code ${status}`)
  err.response = {
    status,
    data: { error: errorText },
    headers: {},
    config: err.config ?? ({} as AxiosError['config']),
    statusText: String(status),
  } as AxiosResponse
  return err
}

/**
 * Test suite for the Unsubscribe page.
 *
 * The component uses plain axios + useState rather than useMutation, so tests
 * spy on axios.get and control resolution to assert rendering at each phase.
 *
 * vi.useRealTimers() is called in beforeEach to override the global fake-timer
 * config so that promise microtasks resolve naturally; the one test that needs
 * fake timers enables them locally.
 */
describe('Unsubscribe page', () => {
  let getSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.useRealTimers()
    getSpy = vi.spyOn(axios, 'get').mockResolvedValue({ data: { message: 'ok', user_id: 1 } })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  it('renders loading spinner initially', () => {
    getSpy.mockReturnValue(new Promise(() => {}))

    act(() => {
      render(<div />, { initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`] })
    })

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows success alert when unsubscribe succeeds', async () => {
    await act(async () => {
      render(<div />, { initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`] })
    })

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent(/unsubscribed/i)
  })

  it('success alert remains visible and does not auto-dismiss', async () => {
    vi.useFakeTimers({
      toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'],
    })

    await act(async () => {
      render(<div />, { initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`] })
    })

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())

    vi.advanceTimersByTime(10000)

    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('shows error alert when unsubscribe fails with invalid token', async () => {
    getSpy.mockRejectedValue(makeAxiosError(400, 'Invalid or expired unsubscribe token'))

    await act(async () => {
      render(<div />, { initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`] })
    })

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent(/invalid or expired unsubscribe link/i)
  })

  it('displays error when user_id param is missing and does not call get', () => {
    render(<div />, { initialEntries: [`/unsubscribe?token=${TOKEN}`] })

    expect(screen.getByRole('alert')).toHaveTextContent(/user_id/i)
    expect(getSpy).not.toHaveBeenCalled()
  })

  it('displays error when token param is missing and does not call get', () => {
    render(<div />, { initialEntries: ['/unsubscribe?user_id=1'] })

    expect(screen.getByRole('alert')).toHaveTextContent(/token/i)
    expect(getSpy).not.toHaveBeenCalled()
  })

  it('displays error when token is not 64 hex characters and does not call get', () => {
    render(<div />, { initialEntries: ['/unsubscribe?user_id=1&token=tooshort'] })

    expect(screen.getByRole('alert')).toHaveTextContent(/invalid.*token/i)
    expect(getSpy).not.toHaveBeenCalled()
  })

  it('displays error when user_id is not numeric and does not call get', () => {
    render(<div />, { initialEntries: [`/unsubscribe?user_id=abc&token=${TOKEN}`] })

    expect(screen.getByRole('alert')).toHaveTextContent(/invalid.*user/i)
    expect(getSpy).not.toHaveBeenCalled()
  })

  it('shows link to home on success', async () => {
    await act(async () => {
      render(<div />, { initialEntries: [`/unsubscribe?user_id=1&token=${TOKEN}`] })
    })

    await waitFor(() =>
      expect(screen.getByRole('link', { name: /go to home/i })).toBeInTheDocument()
    )
  })
})
