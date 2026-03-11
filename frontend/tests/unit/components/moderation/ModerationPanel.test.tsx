import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ModerationPanel } from '@/components/moderation/ModerationPanel'
import { useFetchComments } from '@/hooks/useComments'
import {
  createMockComment,
  createMockDeletedComment,
  createMockListCommentsResponse,
  createMockPendingModerationComment,
} from '../../../fixtures/comments.fixtures'

const { mockApprove, mockAdminDelete } = vi.hoisted(() => ({
  mockApprove: vi.fn(),
  mockAdminDelete: vi.fn(),
}))

vi.mock('@/hooks/useComments', () => ({
  useFetchComments: vi.fn(),
  useApproveComment: mockApprove,
  useAdminDeleteComment: mockAdminDelete,
}))
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    getToken: vi.fn(async () => 'mock-token'),
    isLoaded: true,
    user: null,
    role: 'admin' as const,
  })),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const makeMockMutation = () => ({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
  isIdle: true,
  isSuccess: false,
  reset: vi.fn(),
  mutateAsync: vi.fn(),
  data: undefined,
  failureCount: 0,
  failureReason: null,
  isPaused: false,
  status: 'idle' as const,
  submittedAt: 0,
  variables: undefined,
  context: undefined,
})

const makeQueryResult = (
  data: ReturnType<typeof createMockListCommentsResponse> | undefined,
  overrides: Record<string, unknown> = {}
) => ({
  data,
  isLoading: false,
  isFetching: false,
  isError: false,
  error: null,
  isSuccess: data !== undefined,
  isPending: data === undefined,
  status: data !== undefined ? ('success' as const) : ('pending' as const),
  fetchStatus: 'idle' as const,
  refetch: vi.fn(),
  ...overrides,
})

const mockComments = [
  createMockComment({ id: 1, is_post_author: false, text: 'Normal approved comment', post_id: 5 }),
  createMockPendingModerationComment({ id: 2, is_post_author: false, post_id: 5 }),
  createMockDeletedComment({ id: 3, is_post_author: false, post_id: 5 }),
]

/**
 * Test suite for ModerationPanel component
 *
 * Covers the full admin moderation surface: listing all comments regardless
 * of status, filter tabs, badge display, conditional ModerateButton visibility,
 * CSV export, and loading state.
 */
describe('ModerationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApprove.mockReturnValue(makeMockMutation())
    mockAdminDelete.mockReturnValue(makeMockMutation())
    vi.mocked(useFetchComments).mockReturnValue(
      makeQueryResult(createMockListCommentsResponse(mockComments, mockComments.length)) as never
    )
  })

  /**
   * All comments must appear in the list regardless of status so admins
   * have full visibility — unlike the public comment section which hides
   * deleted and pending items.
   */
  it('renders all comments including pending and deleted', () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    expect(screen.getByText('Normal approved comment')).toBeInTheDocument()
    expect(screen.getByText('This comment looks suspicious and needs review')).toBeInTheDocument()
  })

  /**
   * The comment count must be visible so admins can gauge the moderation
   * workload at a glance without counting rows.
   */
  it('shows comment count', () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    expect(screen.getByText(/3 of 3/)).toBeInTheDocument()
  })

  /**
   * The Pending filter must narrow the list to only comments awaiting
   * moderation, hiding normal and deleted entries.
   */
  it('shows only pending comments when Pending filter is active', async () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /pending/i }))

    expect(screen.getByText('This comment looks suspicious and needs review')).toBeInTheDocument()
    expect(screen.queryByText('Normal approved comment')).not.toBeInTheDocument()
  })

  /**
   * The Deleted filter must narrow the list to only soft-deleted comments
   * so admins can audit removed content.
   */
  it('shows only deleted comments when Deleted filter is active', async () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /^deleted$/i }))

    expect(screen.queryByText('Normal approved comment')).not.toBeInTheDocument()
    expect(
      screen.queryByText('This comment looks suspicious and needs review')
    ).not.toBeInTheDocument()
  })

  /**
   * Switching back to All after using a filter must restore the full list.
   */
  it('shows all comments when All filter is active', async () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /pending/i }))
    await userEvent.click(screen.getByRole('button', { name: /^all$/i }))

    expect(screen.getByText('Normal approved comment')).toBeInTheDocument()
    expect(screen.getByText('This comment looks suspicious and needs review')).toBeInTheDocument()
  })

  /**
   * Deleted comments must NOT show a CommentModerateButton because the
   * delete action has already been taken and approve makes no sense.
   */
  it('does not render moderation buttons for deleted comments', async () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    await userEvent.click(screen.getByRole('button', { name: /^deleted$/i }))

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
  })

  /**
   * Pending comments must show a yellow "Pending" badge so admins can
   * identify items needing action at a glance.
   */
  it('shows Pending badge for comments with is_pending_moderation true', () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    const pendingElements = screen.getAllByText('Pending')
    const hasBadge = pendingElements.some(el => el.tagName === 'SPAN')
    expect(hasBadge).toBe(true)
  })

  /**
   * Deleted comments must show a "Deleted" badge to clearly distinguish
   * them from active comments in the all-comments view.
   */
  it('shows Deleted badge for comments with is_deleted true', () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    const deletedElements = screen.getAllByText('Deleted')
    const hasBadge = deletedElements.some(el => el.tagName === 'SPAN')
    expect(hasBadge).toBe(true)
  })

  /**
   * The Export CSV button must trigger a download with the correct header
   * and data rows so admins get usable exports. Asserts both the download
   * flow (createObjectURL, anchor click) and the blob content.
   */
  it('triggers CSV download with correct content when Export CSV button is clicked', async () => {
    let capturedBlob: Blob | null = null
    const createObjectURL = vi.fn((blob: Blob) => {
      capturedBlob = blob
      return 'blob:mock-url'
    })
    const revokeObjectURL = vi.fn()
    Object.defineProperty(window, 'URL', {
      value: { createObjectURL, revokeObjectURL },
      writable: true,
    })

    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    const clickSpy = vi.fn()
    const anchorElement = { href: '', download: '', click: clickSpy, style: {} }
    const originalCreateElement = document.createElement.bind(document)
    const createElementSpy = vi
      .spyOn(document, 'createElement')
      .mockImplementation((tag: string) => {
        if (tag === 'a') return anchorElement as unknown as HTMLElement
        return originalCreateElement(tag)
      })
    const appendChildSpy = vi
      .spyOn(document.body, 'appendChild')
      .mockReturnValue(anchorElement as unknown as Node)
    const removeChildSpy = vi
      .spyOn(document.body, 'removeChild')
      .mockReturnValue(anchorElement as unknown as Node)

    try {
      await userEvent.click(screen.getByRole('button', { name: /export csv/i }))

      expect(createObjectURL).toHaveBeenCalledOnce()
      expect(clickSpy).toHaveBeenCalledOnce()

      expect(capturedBlob).not.toBeNull()
      const csvContent = await new Promise<string>(resolve => {
        const reader = new FileReader()
        reader.onload = e => resolve(e.target?.result as string)
        reader.readAsText(capturedBlob as unknown as Blob)
      })
      const lines = csvContent.split('\n')

      expect(lines[0]).toBe('id,post_id,is_post_author,text,status,created_at')

      const firstDataRow = lines[1]
      expect(firstDataRow).toContain('1')
      expect(firstDataRow).toContain('5')
      expect(firstDataRow).toContain('false')
      expect(firstDataRow).toContain('Normal approved comment')
      expect(firstDataRow).toContain('published')
      expect(firstDataRow).toContain('2026-02-01T10:00:00Z')
    } finally {
      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
      removeChildSpy.mockRestore()
    }
  })

  /**
   * Loading state must be visible when the query is in flight so admins
   * know data is coming rather than seeing an empty panel.
   */
  it('shows loading state while fetching comments', () => {
    vi.mocked(useFetchComments).mockReturnValue(
      makeQueryResult(undefined, {
        isLoading: true,
        isPending: true,
        status: 'pending',
      }) as never
    )

    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    expect(screen.getByRole('status') ?? screen.getByText(/loading/i)).toBeInTheDocument()
  })

  /**
   * The comment text must be truncated at 100 characters so long comments
   * do not break the table layout.
   */
  it('truncates comment text longer than 100 characters', () => {
    const longText = 'A'.repeat(150)
    vi.mocked(useFetchComments).mockReturnValue(
      makeQueryResult(
        createMockListCommentsResponse([createMockComment({ id: 99, text: longText })], 1)
      ) as never
    )

    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    expect(screen.queryByText(longText)).not.toBeInTheDocument()
    expect(screen.getByText(new RegExp(`${'A'.repeat(97)}`))).toBeInTheDocument()
  })

  /**
   * Non-deleted, non-pending comments must show moderation buttons so
   * admins can take action on active content.
   */
  it('renders moderation buttons for active comments', () => {
    vi.mocked(useFetchComments).mockReturnValue(
      makeQueryResult(
        createMockListCommentsResponse([createMockComment({ id: 1, text: 'Active comment' })], 1)
      ) as never
    )

    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument()
  })

  /**
   * The within() helper must be able to target individual comment rows
   * so tests can assert per-row button presence without false positives.
   */
  it('renders deleted comment row without moderation buttons in all-comments view', () => {
    renderWithQueryClient(<ModerationPanel postSlug="test-post" />)

    const deletedBadge = screen.getAllByText('Deleted').find(el => el.tagName === 'SPAN')
    expect(deletedBadge).toBeDefined()
    const row = deletedBadge?.closest('[data-testid="comment-row"]')
    expect(row).not.toBeNull()
    expect(
      within(row as HTMLElement).queryByRole('button', { name: /approve/i })
    ).not.toBeInTheDocument()
  })
})
