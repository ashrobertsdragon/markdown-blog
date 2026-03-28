import { type UseMutationResult, useMutation } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { notificationsApi, type UnsubscribeResponse } from '@/services/notificationsApi'

/**
 * Variables accepted by the useUnsubscribe mutation.
 * Derived from query params on the public /unsubscribe landing page.
 */
export interface UnsubscribeParams {
  user_id: number
  token: string
}

/**
 * Maps axios errors from the unsubscribe endpoint to safe user-facing messages.
 *
 * The endpoint is public (no auth header), so 401 is not expected.
 * A 400 with "invalid token" text means the link has expired or was tampered with.
 */
function classifyUnsubscribeError(err: unknown): never {
  if (isAxiosError(err)) {
    const status = err.response?.status
    if (status === 400) {
      const errorText = (err.response?.data?.error as string | undefined) ?? ''
      if (
        errorText.toLowerCase().includes('invalid') ||
        errorText.toLowerCase().includes('token') ||
        errorText.toLowerCase().includes('expired')
      ) {
        throw new Error('Invalid or expired unsubscribe link. Check your email.')
      }
      throw new Error('Invalid unsubscribe request')
    }
    if (typeof status === 'number' && status >= 500) {
      throw new Error('Server error — please try again later')
    }
    if (!err.response) {
      throw new Error('Network error — check your connection')
    }
  }
  throw err
}

/**
 * Mutation hook for the public one-click unsubscribe flow.
 *
 * No authentication is required — the signed token in the query string
 * is the proof of identity. Errors are classified into user-facing messages
 * so the landing page never exposes raw API internals.
 */
export function useUnsubscribe(): UseMutationResult<UnsubscribeResponse, Error, UnsubscribeParams> {
  return useMutation({
    mutationFn: async ({ user_id, token }: UnsubscribeParams) => {
      try {
        return await notificationsApi.unsubscribeWithToken(user_id, token)
      } catch (err) {
        classifyUnsubscribeError(err)
      }
    },
  })
}
