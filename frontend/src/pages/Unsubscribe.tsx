import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useUnsubscribe } from '@/hooks/useUnsubscribe'

const TOKEN_REGEX = /^[a-f0-9]{64}$/

/**
 * Validates query params from the unsubscribe email link.
 * Returns an error string if invalid, or null if both params are valid.
 */
function validateParams(userIdParam: string | null, tokenParam: string | null): string | null {
  if (!userIdParam) return 'Missing required parameter: user_id'
  if (!tokenParam) return 'Missing required parameter: token'
  if (!/^\d+$/.test(userIdParam)) return 'Invalid user_id: must be numeric'
  if (!TOKEN_REGEX.test(tokenParam)) return 'Invalid token: must be 64 lowercase hex characters'
  return null
}

/**
 * Public landing page for one-click email unsubscription.
 *
 * Reads user_id and token from query params (injected by the email link),
 * validates them client-side, then fires the unsubscribe mutation on mount.
 * No authentication required.
 */
export default function Unsubscribe() {
  const [searchParams] = useSearchParams()
  const userIdParam = searchParams.get('user_id')
  const tokenParam = searchParams.get('token')

  const validationError = validateParams(userIdParam, tokenParam)

  const { mutate, isPending, isSuccess, isError, error } = useUnsubscribe()

  const [showSuccess, setShowSuccess] = useState(false)
  const hasFired = useRef(false)

  useEffect(() => {
    if (!validationError && !hasFired.current) {
      hasFired.current = true
      mutate({ user_id: parseInt(userIdParam as string, 10), token: tokenParam as string })
    }
  }, [mutate, validationError, userIdParam, tokenParam])

  useEffect(() => {
    if (isSuccess) {
      setShowSuccess(true)
    }
  }, [isSuccess])

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => setShowSuccess(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [showSuccess])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
      <div className="mx-auto w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 className="mb-6 text-2xl font-semibold text-gray-900">Unsubscribe</h1>

        {validationError && (
          <Alert variant="destructive">
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        )}

        {!validationError && isPending && <LoadingSpinner message="Unsubscribing..." />}

        {!validationError && isError && error && (
          <Alert variant="destructive">
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        )}

        {!validationError && showSuccess && (
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
