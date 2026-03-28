import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from '@/hooks/useNotificationPreferences'
import type { NotificationPreferences } from '@/services/notificationsApi'
import { notificationsApi } from '@/services/notificationsApi'

vi.mock('@/services/notificationsApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-token'),
    isSignedIn: true,
    isLoaded: true,
    user: null,
    role: 'authenticated' as const,
  })),
}))

/**
 * Test suite for useNotificationPreferences and useUpdateNotificationPreferences hooks
 *
 * Verifies query enablement, cache key usage, optimistic updates, rollback on
 * error, and query invalidation on success — without coupling to implementation.
 */
describe('useNotificationPreferences hooks', () => {
  let queryClient: QueryClient

  const createWrapper = () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    return wrapper
  }

  const mockPreferences: NotificationPreferences = {
    user_id: 1,
    notify_on_comment_replies: true,
    notify_on_mentions: false,
    notify_on_new_posts: true,
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

  /**
   * Tests for useNotificationPreferences()
   *
   * Read-only query. Must be disabled when unauthenticated to prevent
   * spurious 401 requests on page load.
   */
  describe('useNotificationPreferences', () => {
    it('should fetch preferences when authenticated', async () => {
      vi.mocked(notificationsApi.fetchNotificationPreferences).mockResolvedValueOnce({
        preferences: mockPreferences,
      })

      const { result } = renderHook(() => useNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(notificationsApi.fetchNotificationPreferences).toHaveBeenCalledWith('mock-token')
      expect(result.current.data).toEqual(mockPreferences)
    })

    it('should not fetch when user is not authenticated', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: false,
        isLoaded: true,
        user: null,
        role: 'authenticated' as const,
      })

      const { result } = renderHook(() => useNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(notificationsApi.fetchNotificationPreferences).not.toHaveBeenCalled()
    })

    it('should return loading state while fetching', () => {
      vi.mocked(notificationsApi.fetchNotificationPreferences).mockImplementation(
        () => new Promise(() => {})
      )

      const { result } = renderHook(() => useNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should return error state when fetch fails', async () => {
      const mockError = new Error('Server error')
      vi.mocked(notificationsApi.fetchNotificationPreferences).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(mockError)
      expect(result.current.data).toBeUndefined()
    })

    it('should return all preference fields on success', async () => {
      vi.mocked(notificationsApi.fetchNotificationPreferences).mockResolvedValueOnce({
        preferences: mockPreferences,
      })

      const { result } = renderHook(() => useNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.notify_on_comment_replies).toBe(true)
      expect(result.current.data?.notify_on_mentions).toBe(false)
      expect(result.current.data?.notify_on_new_posts).toBe(true)
    })
  })

  /**
   * Tests for useUpdateNotificationPreferences()
   *
   * Write mutation. Must apply optimistic update before the server round-trip,
   * invalidate the preferences query key on success, and roll back cache on error.
   */
  describe('useUpdateNotificationPreferences', () => {
    it('should call notificationsApi.updateNotificationPreferences with token and updates', async () => {
      const updated: NotificationPreferences = { ...mockPreferences, notify_on_mentions: true }
      vi.mocked(notificationsApi.updateNotificationPreferences).mockResolvedValueOnce({
        preferences: updated,
      })

      queryClient.setQueryData(['notificationPreferences'], mockPreferences)

      const { result } = renderHook(() => useUpdateNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ notify_on_mentions: true })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(notificationsApi.updateNotificationPreferences).toHaveBeenCalledWith('mock-token', {
        notify_on_mentions: true,
      })
    })

    it('should apply optimistic update to cache before server responds', async () => {
      vi.mocked(notificationsApi.updateNotificationPreferences).mockImplementation(
        () => new Promise(() => {})
      )

      queryClient.setQueryData(['notificationPreferences'], mockPreferences)

      const { result } = renderHook(() => useUpdateNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ notify_on_mentions: true })

      await waitFor(() => expect(result.current.isPending).toBe(true))

      const cached = queryClient.getQueryData<NotificationPreferences>(['notificationPreferences'])
      expect(cached?.notify_on_mentions).toBe(true)
    })

    it('should invalidate notificationPreferences query key on success', async () => {
      const updated: NotificationPreferences = { ...mockPreferences, notify_on_new_posts: false }
      vi.mocked(notificationsApi.updateNotificationPreferences).mockResolvedValueOnce({
        preferences: updated,
      })

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUpdateNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ notify_on_new_posts: false })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['notificationPreferences'] })
      )
    })

    it('should roll back optimistic update when mutation fails', async () => {
      vi.mocked(notificationsApi.updateNotificationPreferences).mockRejectedValueOnce(
        new Error('Server error')
      )

      queryClient.setQueryData(['notificationPreferences'], mockPreferences)

      const { result } = renderHook(() => useUpdateNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ notify_on_mentions: true })

      await waitFor(() => expect(result.current.isError).toBe(true))

      const cached = queryClient.getQueryData<NotificationPreferences>(['notificationPreferences'])
      expect(cached?.notify_on_mentions).toBe(false)
    })

    it('should return isPending true during mutation', async () => {
      vi.mocked(notificationsApi.updateNotificationPreferences).mockImplementation(
        () => new Promise(() => {})
      )

      const { result } = renderHook(() => useUpdateNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ notify_on_comment_replies: false })

      await waitFor(() => expect(result.current.isPending).toBe(true))
    })

    it('should throw when getToken returns null', async () => {
      const { useAuth } = await import('@/hooks/useAuth')
      vi.mocked(useAuth).mockReturnValueOnce({
        getToken: vi.fn(async () => null),
        isSignedIn: true,
        isLoaded: true,
        user: null,
        role: 'authenticated' as const,
      })

      const { result } = renderHook(() => useUpdateNotificationPreferences(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ notify_on_mentions: true })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Authentication required')
      expect(notificationsApi.updateNotificationPreferences).not.toHaveBeenCalled()
    })
  })
})
