import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription } from '@/components/ui/alert'

const TOKEN_REGEX = /^[a-fA-F0-9]{64}$/

type UnsubscribeStatus = 'idle' | 'pending' | 'success' | 'error'

/**
 * Validates query params from the unsubscribe email link.
 * Returns an error string if invalid, or null if both params are valid.
 */
function validateParams(userIdParam: string | null, tokenParam: string | null): string | null {
  if (!userIdParam) return 'Missing required parameter: user_id'
  if (!tokenParam) return 'Missing required parameter: token'
  if (!/^\d+$/.test(userIdParam)) return 'Invalid user_id: must be numeric'
  if (!TOKEN_REGEX.test(tokenParam)) return 'Invalid token: must be 64 hex characters'
  return null
}

/**
 * Maps raw errors from the unsubscribe axios call to safe user-facing messages.
 */
function classifyError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status
    if (status === 400) {
      const errorText = (err.response?.data?.error as string | undefined) ?? ''
      if (/invalid|token|expired/i.test(errorText)) {
        return 'Invalid or expired unsubscribe link. Check your email.'
      }
      return 'Invalid unsubscribe request'
    }
    if (typeof status === 'number' && status >= 500) {
      return 'Server error — please try again later'
    }
    if (!err.response) return 'Network error — check your connection'
  }
  return 'An unexpected error occurred'
}

/**
 * Public landing page for one-click email unsubscription.
 *
 * Reads user_id and token from query params (injected by the email link),
 * validates them client-side, then fires the unsubscribe request on mount.
 * No authentication required.
 *
 * Uses a ref to prevent React 18 StrictMode's double-mount from sending two
 * concurrent requests. State is managed via useState rather than useMutation
 * so the success/error update always reaches the component regardless of
 * how React Query's observer subscription is handled during StrictMode cycles.
 */
export default function Unsubscribe() {
  const [searchParams] = useSearchParams()
  const userIdParam = searchParams.get('user_id')
  const tokenParam = searchParams.get('token')

  const validationError = validateParams(userIdParam, tokenParam)

  const [status, setStatus] = useState<UnsubscribeStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const hasFiredRef = useRef(false)

  useEffect(() => {
    if (hasFiredRef.current) return
    if (validationError) return
    hasFiredRef.current = true

    const userId = parseInt(userIdParam as string, 10)
    const token = tokenParam as string

    setStatus('pending')
    axios
      .get('/api/unsubscribe', { params: { user_id: userId, token } })
      .then(() => setStatus('success'))
      .catch((err: unknown) => {
        setErrorMessage(classifyError(err))
        setStatus('error')
      })
  }, [validationError, userIdParam, tokenParam])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
      <div className="mx-auto w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 className="mb-6 text-2xl font-semibold text-gray-900">Unsubscribe</h1>

        {validationError && (
          <Alert variant="destructive">
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        )}

        {!validationError && status === 'pending' && <LoadingSpinner message="Unsubscribing..." />}

        {!validationError && status === 'error' && errorMessage && (
          <Alert variant="destructive">
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        )}

        {!validationError && status === 'success' && (
          <Alert>
            <AlertDescription>
              You've been unsubscribed from all email notifications.{' '}
              <Link to="/" className="underline">
                Go to home
              </Link>
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  )
}
