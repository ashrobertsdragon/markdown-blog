import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useUnsubscribe } from '@/hooks/useUnsubscribe'
import { notificationsApi } from '@/services/notificationsApi'

vi.mock('@/services/notificationsApi')

/**
 * Test suite for useUnsubscribe hook
 *
 * Verifies that the mutation calls the correct API method, maps API responses
 * to success values, and classifies all error categories to user-friendly messages
 * without leaking raw backend errors or axios internals to the UI.
 */
describe('useUnsubscribe', () => {
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
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
    queryClient.clear()
  })

  it('calls unsubscribeWithToken with correct params on success', async () => {
    vi.mocked(notificationsApi.unsubscribeWithToken).mockResolvedValueOnce({
      message: 'Successfully unsubscribed from all notifications',
      user_id: 42,
    })

    const { result } = renderHook(() => useUnsubscribe(), { wrapper: createWrapper() })

    result.current.mutate({ user_id: 42, token: 'a'.repeat(64) })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(notificationsApi.unsubscribeWithToken).toHaveBeenCalledWith(42, 'a'.repeat(64))
  })

  it('returns success response on 200 status', async () => {
    const successResponse = {
      message: 'Successfully unsubscribed from all notifications',
      user_id: 42,
    }
    vi.mocked(notificationsApi.unsubscribeWithToken).mockResolvedValueOnce(successResponse)

    const { result } = renderHook(() => useUnsubscribe(), { wrapper: createWrapper() })

    result.current.mutate({ user_id: 42, token: 'b'.repeat(64) })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(successResponse)
  })

  it('throws user-friendly error on 400 invalid token', async () => {
    const axiosError = {
      isAxiosError: true,
      response: {
        status: 400,
        data: { error: 'Invalid or expired unsubscribe token' },
      },
    }
    vi.mocked(notificationsApi.unsubscribeWithToken).mockRejectedValueOnce(axiosError)

    const { result } = renderHook(() => useUnsubscribe(), { wrapper: createWrapper() })

    result.current.mutate({ user_id: 42, token: 'c'.repeat(64) })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error?.message).toMatch(
      /invalid or expired unsubscribe link|invalid unsubscribe request/i
    )
  })

  it('throws user-friendly error on 5xx server error', async () => {
    const axiosError = {
      isAxiosError: true,
      response: {
        status: 500,
        data: { error: 'Internal Server Error' },
      },
    }
    vi.mocked(notificationsApi.unsubscribeWithToken).mockRejectedValueOnce(axiosError)

    const { result } = renderHook(() => useUnsubscribe(), { wrapper: createWrapper() })

    result.current.mutate({ user_id: 42, token: 'd'.repeat(64) })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error?.message).toMatch(/server error/i)
  })

  it('throws user-friendly error on network failure', async () => {
    const networkError = {
      isAxiosError: true,
      response: undefined,
      message: 'Network Error',
    }
    vi.mocked(notificationsApi.unsubscribeWithToken).mockRejectedValueOnce(networkError)

    const { result } = renderHook(() => useUnsubscribe(), { wrapper: createWrapper() })

    result.current.mutate({ user_id: 42, token: 'e'.repeat(64) })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error?.message).toMatch(/network error/i)
  })

  it('classifies API errors correctly', async () => {
    const cases = [
      {
        status: 400,
        pattern: /invalid or expired unsubscribe link|invalid unsubscribe request/i,
      },
      { status: 503, pattern: /server error/i },
    ]

    for (const { status, pattern } of cases) {
      queryClient.clear()
      vi.clearAllMocks()

      const axiosError = {
        isAxiosError: true,
        response: { status, data: { error: 'some backend message' } },
      }
      vi.mocked(notificationsApi.unsubscribeWithToken).mockRejectedValueOnce(axiosError)

      const { result } = renderHook(() => useUnsubscribe(), { wrapper: createWrapper() })

      result.current.mutate({ user_id: 1, token: 'f'.repeat(64) })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toMatch(pattern)
    }
  })
})
