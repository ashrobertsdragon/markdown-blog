import { useEffect, useState } from 'react'
import { NotificationToggle } from '@/components/preferences/NotificationToggle'
import { useAuth } from '@/hooks/useAuth'
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from '@/hooks/useNotificationPreferences'
import type { NotificationPreferencesUpdate } from '@/services/notificationsApi'

/**
 * Settings page for managing per-user notification preferences
 *
 * Fetches current preferences via useNotificationPreferences and renders
 * one NotificationToggle per preference flag. Unauthenticated users see a
 * sign-in prompt. Shows a success alert on save that auto-dismisses after
 * 3 seconds, and a persistent error alert on failure that can be dismissed.
 * Initial fetch errors are surfaced instead of rendering blank toggles.
 */
export default function NotificationPreferences(): React.ReactElement {
  const { isSignedIn } = useAuth()
  const { data: preferences, isLoading, isError, error } = useNotificationPreferences()
  const mutation = useUpdateNotificationPreferences()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (successMessage === null) return
    const timer = setTimeout(() => setSuccessMessage(null), 3000)
    return () => clearTimeout(timer)
  }, [successMessage])

  if (!isSignedIn) {
    return <div>Please sign in to manage your notification preferences.</div>
  }

  if (isLoading) {
    return <output aria-label="Loading preferences" />
  }

  if (isError) {
    return <div role="alert">{error?.message ?? 'Failed to load notification preferences.'}</div>
  }

  const handleToggle = async (field: keyof NotificationPreferencesUpdate, value: boolean) => {
    setErrorMessage(null)
    try {
      await mutation.mutateAsync({ [field]: value })
      setSuccessMessage('Preferences saved.')
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  return (
    <div>
      <h1>Notification Preferences</h1>
      {successMessage !== null && <div role="alert">{successMessage}</div>}
      {errorMessage !== null && (
        <div role="alert">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)} aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}
      <fieldset>
        <legend>Email Notifications</legend>
        <NotificationToggle
          label="Notify on comment replies"
          checked={preferences?.notify_on_comment_replies ?? false}
          onToggle={value => handleToggle('notify_on_comment_replies', value)}
          disabled={mutation.isPending}
        />
        <NotificationToggle
          label="Notify on mentions"
          checked={preferences?.notify_on_mentions ?? false}
          onToggle={value => handleToggle('notify_on_mentions', value)}
          disabled={mutation.isPending}
        />
        <NotificationToggle
          label="Notify on new posts"
          checked={preferences?.notify_on_new_posts ?? false}
          onToggle={value => handleToggle('notify_on_new_posts', value)}
          disabled={mutation.isPending}
        />
      </fieldset>
    </div>
  )
}
