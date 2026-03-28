import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { queryKeys } from '@/hooks/queryKeys'
import { useAuth } from '@/hooks/useAuth'
import {
  type NotificationPreferences,
  type NotificationPreferencesUpdate,
  notificationsApi,
} from '@/services/notificationsApi'

const ALLOWED_PREFERENCE_KEYS: ReadonlySet<string> = new Set([
  'notify_on_comment_replies',
  'notify_on_mentions',
  'notify_on_new_posts',
])

/**
 * Maps axios errors from the notifications API to safe user-facing error messages.
 * Prevents raw backend messages or axios internals from leaking to the UI.
 *
 * @param err - Unknown error thrown by the API call
 * @param context - Which operation failed, used to produce the right message
 */
function classifyNotificationsError(err: unknown, context: 'fetch' | 'update'): never {
  if (isAxiosError(err)) {
    const status = err.response?.status
    if (status === 401) {
      throw new Error('Authentication required')
    }
    if (status === 429) {
      const retryAfter = (err.response?.data?.retry_after as number | undefined) ?? 60
      throw Object.assign(new Error('Too many requests. Please wait before trying again.'), {
        retryAfter,
      })
    }
    if (typeof status === 'number' && status >= 500) {
      throw new Error('Server error — please try again later')
    }
    if (context === 'fetch') {
      throw new Error('Failed to load notification preferences')
    }
    throw new Error('Failed to update notification preferences')
  }
  throw err
}

/**
 * Strips keys from an update payload that are not in the allowed preferences whitelist.
 * Silently discards unknown keys to prevent prototype pollution or unexpected field writes.
 *
 * @param updates - Raw update object from caller
 * @returns New object containing only whitelisted keys
 */
function sanitizeUpdates(updates: NotificationPreferencesUpdate): NotificationPreferencesUpdate {
  return Object.fromEntries(
    Object.entries(updates).filter(([key]) => ALLOWED_PREFERENCE_KEYS.has(key))
  ) as NotificationPreferencesUpdate
}

/**
 * Query hook for fetching the authenticated user's notification preferences
 *
 * Disabled when no token is available to prevent spurious 401 requests on
 * page load. The query is keyed by `queryKeys.notificationPreferences()` so
 * the mutation hook can invalidate it after a successful update.
 */
export function useNotificationPreferences(): UseQueryResult<NotificationPreferences, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.notificationPreferences(),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      try {
        const response = await notificationsApi.fetchNotificationPreferences(token)
        return response.preferences
      } catch (err) {
        classifyNotificationsError(err, 'fetch')
      }
    },
    enabled: auth.isSignedIn === true,
  })
}

/**
 * Mutation hook for updating notification preferences
 *
 * Applies an optimistic update immediately so the UI reflects the change
 * before the server round-trip completes. On success the cache is invalidated
 * to pull in the server-confirmed values. On error the previous cached value
 * is restored to keep the UI consistent.
 *
 * Unknown keys in the update payload are silently stripped before the optimistic
 * update and before the API call to prevent unexpected field writes.
 */
export function useUpdateNotificationPreferences(): UseMutationResult<
  NotificationPreferences,
  Error,
  NotificationPreferencesUpdate
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (updates: NotificationPreferencesUpdate) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      try {
        const response = await notificationsApi.updateNotificationPreferences(
          token,
          sanitizeUpdates(updates)
        )
        return response.preferences
      } catch (err) {
        classifyNotificationsError(err, 'update')
      }
    },
    onMutate: async (updates: NotificationPreferencesUpdate) => {
      const safeUpdates = sanitizeUpdates(updates)
      await queryClient.cancelQueries({ queryKey: queryKeys.notificationPreferences() })
      const previousData = queryClient.getQueryData<NotificationPreferences>(
        queryKeys.notificationPreferences()
      )
      queryClient.setQueryData<NotificationPreferences>(
        queryKeys.notificationPreferences(),
        prev => (prev ? { ...prev, ...safeUpdates } : prev)
      )
      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notificationPreferences() })
    },
    onError: (_err, _vars, context) => {
      if (context?.previousData !== undefined) {
        queryClient.setQueryData(queryKeys.notificationPreferences(), context.previousData)
      }
    },
  })
}
