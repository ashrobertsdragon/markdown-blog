import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UseCommentStreamResult } from '@/hooks/useCommentStream'
import { useCommentStream } from '@/hooks/useCommentStream'
import type { ListCommentsResponse } from '@/services/commentsApi'
import { commentsApi } from '@/services/commentsApi'

vi.mock('@/services/commentsApi')

/**
 * Factory that builds a minimal EventSource mock whose addEventListener
 * calls can be captured and driven by tests. Each test gets a fresh
 * instance so spy state does not bleed across cases.
 */
const buildMockEventSource = (readyState = 1) => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
  readyState,
})

type MockEventSource = ReturnType<typeof buildMockEventSource>

/**
 * Helper that retrieves the handler registered for a given EventSource
 * event name from a mock instance.
 *
 * Why: tests need to invoke EventSource event callbacks synchronously to
 * drive hook state transitions without real network activity.
 */
const getEventHandler = (
  mock: MockEventSource,
  eventName: string
): ((event: Event) => void) | undefined => {
  const call = mock.addEventListener.mock.calls.find(([name]) => name === eventName)
  return call?.[1] as ((event: Event) => void) | undefined
}

/**
 * Builds a minimal MessageEvent-like object for SSE comment events.
 *
 * Typed as `unknown` and cast internally so callers do not need to satisfy
 * the full DOM MessageEvent interface — jsdom supplies a constructor but
 * the hook only reads `.data`.
 */
const buildCommentEvent = (data: unknown): MessageEvent =>
  new MessageEvent('comment', { data: JSON.stringify(data) })

/**
 * Full test suite for useCommentStream.
 *
 * The hook manages a Server-Sent Events connection to
 * `/api/posts/{slug}/comments/stream` and optionally falls back to
 * polling the REST endpoint when SSE fails. Tests here exercise the
 * entire public contract without touching the implementation file.
 */
describe('useCommentStream', () => {
  let queryClient: QueryClient
  let mockEventSource: MockEventSource
  let MockEventSourceConstructor: ReturnType<typeof vi.fn>

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

    mockEventSource = buildMockEventSource()
    MockEventSourceConstructor = vi.fn(() => mockEventSource)
    vi.stubGlobal('EventSource', MockEventSourceConstructor)
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    vi.useRealTimers()
    queryClient.clear()
  })

  /**
   * Verifies that the hook opens an SSE connection to the correct URL on
   * mount. The URL must include the slug so the backend streams only
   * comments for the targeted post.
   */
  it('opens EventSource to /api/posts/{slug}/comments/stream on mount', () => {
    renderHook(() => useCommentStream('my-post'), { wrapper: createWrapper() })

    expect(MockEventSourceConstructor).toHaveBeenCalledTimes(1)
    expect(MockEventSourceConstructor).toHaveBeenCalledWith('/api/posts/my-post/comments/stream')
  })

  /**
   * Verifies cleanup on unmount: the hook must call EventSource.close()
   * so the browser does not hold the connection open after the component
   * tree is destroyed.
   */
  it('calls EventSource.close() on unmount', () => {
    const { unmount } = renderHook(() => useCommentStream('my-post'), {
      wrapper: createWrapper(),
    })

    unmount()

    expect(mockEventSource.close).toHaveBeenCalledTimes(1)
  })

  /**
   * Documents the initial state the hook exposes before EventSource
   * dispatches any open event. The UI depends on these defaults to
   * render a loading/connecting indicator rather than an error state.
   */
  it('returns isConnected: false and isStreaming: false before EventSource connects', () => {
    const { result } = renderHook(() => useCommentStream('my-post'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isConnected).toBe(false)
    expect(result.current.isStreaming).toBe(false)
    expect(result.current.connectionError).toBeNull()
  })

  /**
   * Verifies that receiving a `comment` SSE event causes the hook to
   * write the payload into the React Query cache under the canonical
   * comments query key. Downstream components that read from
   * useFetchComments will re-render with the new data automatically.
   */
  it('updates query cache when comment event is received', async () => {
    const existingComment = {
      id: 1,
      post_id: 1,
      is_post_author: true,
      text: 'Existing comment',
      parent_id: null,
      created_at: '2026-03-10T11:00:00Z',
      updated_at: '2026-03-10T11:00:00Z',
      is_deleted: false,
      is_pending_moderation: false,
    }
    const cacheKey = ['comments', 'my-post', { skip: 0, limit: 50, asAdmin: false }]
    const initialCache: ListCommentsResponse = {
      comments: [existingComment],
      total_count: 1,
      has_more: false,
    }
    queryClient.setQueryData(cacheKey, initialCache)

    const newComment = {
      id: 42,
      post_id: 1,
      is_post_author: false,
      text: 'Streamed comment',
      parent_id: null,
      created_at: '2026-03-10T12:00:00Z',
      updated_at: '2026-03-10T12:00:00Z',
      is_deleted: false,
      is_pending_moderation: false,
    }

    renderHook(() => useCommentStream('my-post'), { wrapper: createWrapper() })

    const commentHandler = getEventHandler(mockEventSource, 'comment')
    expect(commentHandler).toBeDefined()

    act(() => {
      commentHandler?.(buildCommentEvent(newComment))
    })

    await waitFor(() => {
      const cached = queryClient.getQueryData(cacheKey) as ListCommentsResponse
      expect(cached).toEqual({
        comments: [existingComment, newComment],
        total_count: 2,
        has_more: false,
      })
    })
  })

  /**
   * Verifies error handling when EventSource fires its `error` event.
   * The hook must transition to a disconnected state and surface the
   * error so the UI can show a reconnection notice or fallback prompt.
   */
  it('sets connectionError when EventSource errors', async () => {
    const { result } = renderHook(() => useCommentStream('my-post'), {
      wrapper: createWrapper(),
    })

    const errorHandler = getEventHandler(mockEventSource, 'error')
    expect(errorHandler).toBeDefined()

    act(() => {
      errorHandler?.(new Event('error'))
    })

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
      expect(result.current.connectionError).toBeInstanceOf(Error)
    })
  })

  /**
   * Verifies that passing `enabled: false` suppresses all SSE activity.
   * This option exists so parent components can conditionally stream only
   * when the user is on the relevant page, avoiding spurious connections.
   */
  it('does not open EventSource when enabled is false', () => {
    renderHook(() => useCommentStream('my-post', { enabled: false }), {
      wrapper: createWrapper(),
    })

    expect(MockEventSourceConstructor).not.toHaveBeenCalled()
  })

  /**
   * Verifies the polling fallback path. When SSE fails and the caller
   * sets `fallbackToPoll: true`, the hook must switch to periodic REST
   * polling at the configured interval. Fake timers let the test advance
   * time deterministically without real waits.
   */
  it('falls back to polling when SSE errors and fallbackToPoll is true', async () => {
    vi.useFakeTimers()

    const mockListResponse: ListCommentsResponse = {
      comments: [],
      total_count: 0,
      has_more: false,
    }
    vi.mocked(commentsApi.listComments).mockResolvedValue(mockListResponse)

    renderHook(
      () =>
        useCommentStream('my-post', {
          fallbackToPoll: true,
          pollInterval: 2000,
        }),
      { wrapper: createWrapper() }
    )

    const errorHandler = getEventHandler(mockEventSource, 'error')
    expect(errorHandler).toBeDefined()

    act(() => {
      errorHandler?.(new Event('error'))
    })

    expect(commentsApi.listComments).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })

    expect(commentsApi.listComments).toHaveBeenCalledWith('my-post', 0, 50, undefined)
  })

  /**
   * Verifies that when the slug prop changes the hook closes the
   * existing EventSource before opening a new one for the new slug.
   * Leaving stale connections open would push updates for the wrong post
   * into the cache.
   */
  it('closes previous EventSource when slug changes', async () => {
    let currentSlug = 'first-post'

    const { rerender } = renderHook(() => useCommentStream(currentSlug), {
      wrapper: createWrapper(),
    })

    expect(MockEventSourceConstructor).toHaveBeenCalledTimes(1)
    expect(MockEventSourceConstructor).toHaveBeenLastCalledWith(
      '/api/posts/first-post/comments/stream'
    )

    const firstMockEventSource = mockEventSource

    const secondMockEventSource = buildMockEventSource()
    MockEventSourceConstructor.mockReturnValue(secondMockEventSource)

    currentSlug = 'second-post'
    rerender()

    await waitFor(() => {
      expect(firstMockEventSource.close).toHaveBeenCalledTimes(1)
    })

    expect(MockEventSourceConstructor).toHaveBeenCalledTimes(2)
    expect(MockEventSourceConstructor).toHaveBeenLastCalledWith(
      '/api/posts/second-post/comments/stream'
    )
  })

  /**
   * Verifies that when `enabled: false` is set the hook returns the
   * fully disconnected default state without attempting any SSE or
   * polling activity.
   */
  it('returns safe defaults when enabled is false', () => {
    const { result } = renderHook(() => useCommentStream('my-post', { enabled: false }), {
      wrapper: createWrapper(),
    })

    const state: UseCommentStreamResult = result.current

    expect(state.isConnected).toBe(false)
    expect(state.isStreaming).toBe(false)
    expect(state.connectionError).toBeNull()
  })

  /**
   * Verifies that polling uses the default 2000ms interval when
   * `pollInterval` is not explicitly provided, so the caller does not
   * have to supply a value just to activate the fallback.
   */
  it('polls at default 2000ms interval when pollInterval is omitted', async () => {
    vi.useFakeTimers()

    const mockListResponse: ListCommentsResponse = {
      comments: [],
      total_count: 0,
      has_more: false,
    }
    vi.mocked(commentsApi.listComments).mockResolvedValue(mockListResponse)

    renderHook(() => useCommentStream('my-post', { fallbackToPoll: true }), {
      wrapper: createWrapper(),
    })

    const errorHandler = getEventHandler(mockEventSource, 'error')

    act(() => {
      errorHandler?.(new Event('error'))
    })

    await act(async () => {
      vi.advanceTimersByTime(1999)
    })
    expect(commentsApi.listComments).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(1)
    })
    expect(commentsApi.listComments).toHaveBeenCalledTimes(1)
  })

  /**
   * Verifies that `isStreaming` becomes true once the EventSource
   * open event fires, distinguishing an active SSE connection from the
   * initial connecting state or the polling fallback.
   */
  it('sets isStreaming: true when SSE open event fires', async () => {
    const { result } = renderHook(() => useCommentStream('my-post'), {
      wrapper: createWrapper(),
    })

    const openHandler = getEventHandler(mockEventSource, 'open')
    expect(openHandler).toBeDefined()

    act(() => {
      openHandler?.(new Event('open'))
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true)
      expect(result.current.isConnected).toBe(true)
    })
  })

  /**
   * Verifies that `isStreaming` is false during the polling fallback
   * state, allowing the UI to distinguish between "actively streaming
   * via SSE" and "degraded polling mode".
   */
  it('sets isStreaming: false and isConnected: false while in polling fallback', async () => {
    vi.useFakeTimers()

    vi.mocked(commentsApi.listComments).mockResolvedValue({
      comments: [],
      total_count: 0,
      has_more: false,
    })

    const { result } = renderHook(() => useCommentStream('my-post', { fallbackToPoll: true }), {
      wrapper: createWrapper(),
    })

    const errorHandler = getEventHandler(mockEventSource, 'error')

    act(() => {
      errorHandler?.(new Event('error'))
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false)
      expect(result.current.isConnected).toBe(false)
    })
  })

  /**
   * Verifies that the polling interval is cleared on unmount so no
   * further fetch calls are made after the component is destroyed.
   * This prevents memory leaks and spurious state updates on unmounted
   * components.
   */
  it('stops polling on unmount', async () => {
    vi.useFakeTimers()

    vi.mocked(commentsApi.listComments).mockResolvedValue({
      comments: [],
      total_count: 0,
      has_more: false,
    })

    const { unmount } = renderHook(
      () => useCommentStream('my-post', { fallbackToPoll: true, pollInterval: 500 }),
      { wrapper: createWrapper() }
    )

    const errorHandler = getEventHandler(mockEventSource, 'error')

    act(() => {
      errorHandler?.(new Event('error'))
    })

    unmount()

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })

    expect(commentsApi.listComments).not.toHaveBeenCalled()
  })
})
