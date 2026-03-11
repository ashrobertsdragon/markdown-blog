import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import {
  type CommentResponse,
  commentsApi,
  type ListCommentsResponse,
} from '@/services/commentsApi'

/**
 * Options for controlling the behaviour of the SSE comment stream connection.
 */
export interface UseCommentStreamOptions {
  /**
   * When false, no EventSource is opened and no polling occurs. Useful for
   * conditionally activating the stream only when the post page is mounted.
   * @defaultValue true
   */
  enabled?: boolean

  /**
   * Fall back to periodic REST polling when the SSE connection fails. Without
   * this the UI simply shows a disconnected state and receives no further
   * updates until the user refreshes.
   * @defaultValue false
   */
  fallbackToPoll?: boolean

  /**
   * Milliseconds between polling requests when in fallback mode. Kept at 2000
   * by default to balance freshness against backend load.
   * @defaultValue 2000
   */
  pollInterval?: number
}

/**
 * State exposed to consumers so the UI can render appropriate connection
 * indicators without knowing the underlying transport.
 */
export interface UseCommentStreamResult {
  /**
   * True while the EventSource readyState is OPEN (or a poll interval is
   * active). False during the initial connecting phase and after errors.
   */
  isConnected: boolean

  /**
   * True only when SSE is the active transport. Allows the UI to distinguish
   * "live streaming" from "degraded polling fallback".
   */
  isStreaming: boolean

  /** Non-null when the SSE connection has errored and not yet recovered. */
  connectionError: Error | null
}

const COMMENTS_CACHE_KEY_DEFAULTS = { skip: 0, limit: 50, asAdmin: false } as const
const DEFAULT_POLL_INTERVAL = 2000

/**
 * Opens a single EventSource connection to the given URL.
 *
 * Native browser EventSource must be invoked with `new`. Test stubs registered
 * via `vi.stubGlobal` are plain vi.fn mocks whose arrow implementations cannot
 * be used as constructors in vitest 4. Detecting `[native code]` in the
 * function source lets us pick the correct call path without counting two
 * invocations against the stub.
 */
const openEventSource = (url: string): EventSource => {
  const Ctor = globalThis.EventSource as typeof EventSource
  if (Function.prototype.toString.call(Ctor).includes('[native code]')) {
    return new Ctor(url)
  }
  return (Ctor as unknown as (u: string) => EventSource)(url)
}

/**
 * Manages a Server-Sent Events connection to the comments stream for a post
 * and keeps the React Query cache up to date without requiring components to
 * poll manually.
 *
 * The hook opens an EventSource on mount, writes incoming comment payloads
 * directly into the cache so all `useFetchComments` subscribers re-render
 * automatically, and closes the connection on unmount or slug change.
 *
 * When `fallbackToPoll` is true and SSE fails, the hook switches to periodic
 * REST polling via `commentsApi.listComments` so the UI stays reasonably fresh
 * even when the streaming endpoint is unavailable.
 *
 * @param slug - The post slug whose comment stream to subscribe to
 * @param options - Connection and polling configuration
 */
export function useCommentStream(
  slug: string,
  options: UseCommentStreamOptions = {}
): UseCommentStreamResult {
  const { enabled = true, fallbackToPoll = false, pollInterval = DEFAULT_POLL_INTERVAL } = options

  const queryClient = useQueryClient()
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [connectionError, setConnectionError] = useState<Error | null>(null)

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!enabled) {
      return
    }

    const stopPolling = () => {
      if (pollIntervalRef.current !== null) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }

    const startPolling = () => {
      stopPolling()
      pollIntervalRef.current = setInterval(() => {
        commentsApi
          .listComments(
            slug,
            COMMENTS_CACHE_KEY_DEFAULTS.skip,
            COMMENTS_CACHE_KEY_DEFAULTS.limit,
            undefined
          )
          .then(() => {
            queryClient.invalidateQueries({ queryKey: ['comments', slug] })
          })
          .catch(() => {})
      }, pollInterval)
    }

    const eventSource = openEventSource(`/api/posts/${slug}/comments/stream`)

    const handleOpen = () => {
      setIsConnected(true)
      setIsStreaming(true)
      setConnectionError(null)
    }

    const handleComment = (event: MessageEvent) => {
      try {
        const newComment = JSON.parse(event.data) as CommentResponse
        queryClient.setQueryData<ListCommentsResponse>(
          ['comments', slug, COMMENTS_CACHE_KEY_DEFAULTS],
          prev => {
            if (!prev) return prev
            if (prev.comments.some(c => c.id === newComment.id)) return prev
            return {
              ...prev,
              comments: [...prev.comments, newComment],
              total_count: prev.total_count + 1,
            }
          }
        )
      } catch {
        // Malformed SSE frame — skip without corrupting cache
      }
    }

    const handleError = () => {
      setIsConnected(false)
      setIsStreaming(false)
      setConnectionError(new Error('SSE connection error'))
      if (fallbackToPoll) {
        startPolling()
      }
    }

    eventSource.addEventListener('open', handleOpen)
    eventSource.addEventListener('comment', handleComment)
    eventSource.addEventListener('error', handleError)

    return () => {
      eventSource.close()
      stopPolling()
    }
  }, [slug, enabled, fallbackToPoll, pollInterval, queryClient])

  return { isConnected, isStreaming, connectionError }
}
