import type { UserResource } from '@clerk/shared/types'
import type { UseQueryResult } from '@tanstack/react-query'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RevisionDetail } from '@/components/revision/RevisionDetail'
import { RevisionTimeline } from '@/components/revision/RevisionTimeline'
import { useAuth } from '@/hooks/useAuth'
import type {
  ListRevisionsResponse,
  RevisionDetail as RevisionDetailType,
} from '@/services/revisionsApi'

vi.mock('@/services/revisionsApi')
vi.mock('@/hooks/useAuth')

const mockUseRevisionHistory = vi.hoisted(() => vi.fn())
const mockUseRevisionDetail = vi.hoisted(() => vi.fn())
const mockUseRevertRevision = vi.hoisted(() => vi.fn())

vi.mock('@/hooks/useRevisions', () => ({
  useRevisionHistory: mockUseRevisionHistory,
  useRevisionDetail: mockUseRevisionDetail,
  useRevertRevision: mockUseRevertRevision,
}))

describe('Revision Workflow Integration Tests', () => {
  let queryClient: QueryClient
  const user = userEvent.setup()

  const mockRevisions: ListRevisionsResponse = {
    revisions: [
      {
        id: '1',
        commit_sha: 'abc123def456',
        short_sha: 'abc123d',
        author: { id: '42', name: 'Test Author' },
        timestamp: '2026-02-15T10:00:00Z',
        relative_time: '2 hours ago',
        commit_message: 'Initial commit',
        is_revert: false,
      },
      {
        id: '2',
        commit_sha: '789ghi012jkl',
        short_sha: '789ghi0',
        author: { id: '42', name: 'Test Author' },
        timestamp: '2026-02-15T09:00:00Z',
        relative_time: '3 hours ago',
        commit_message: 'Updated content',
        is_revert: false,
      },
      {
        id: '3',
        commit_sha: 'def456abc789',
        short_sha: 'def456a',
        author: { id: '43', name: 'Other Author' },
        timestamp: '2026-02-15T08:00:00Z',
        relative_time: '4 hours ago',
        commit_message: 'Revert to previous version',
        is_revert: true,
      },
    ],
    total_count: 3,
    has_more: false,
  }

  const mockRevisionDetail: RevisionDetailType = {
    id: '2',
    commit_sha: '789ghi012jkl',
    short_sha: '789ghi0',
    author: { id: '42', name: 'Test Author' },
    timestamp: '2026-02-15T09:00:00Z',
    commit_message: 'Updated content',
    markdown_content: '# Updated Post\n\nThis is the updated content.',
    html_content: '<h1>Updated Post</h1>\n<p>This is the updated content.</p>',
    is_current: false,
    is_revert: false,
  }

  const createWrapper = () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    return wrapper
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
        mutations: {
          retry: false,
        },
      },
    })
    vi.clearAllMocks()

    // Default mock implementation for useRevertRevision to avoid destructuring errors
    mockUseRevertRevision.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      reset: vi.fn(),
    })
  })

  describe('Permission-Based Workflows', () => {
    describe('Reader (not authenticated)', () => {
      beforeEach(() => {
        vi.mocked(useAuth).mockReturnValue({
          user: null,
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          getToken: vi.fn(async () => null),
        })
      })

      it('cannot see timeline or revert buttons - unauthenticated', () => {
        mockUseRevisionHistory.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisions,
          error: null,
        } as UseQueryResult<ListRevisionsResponse, Error>)

        render(
          <RevisionTimeline
            slug="test-post"
            currentSha="abc123d"
            onSelectRevision={vi.fn()}
            isAuthor={false}
          />,
          {
            wrapper: createWrapper(),
          }
        )

        const revisionItem = screen.getByTestId('revision-item-abc123d')
        expect(revisionItem).not.toHaveAttribute('role', 'button')
      })
    })

    describe('Authenticated Reader', () => {
      beforeEach(() => {
        vi.mocked(useAuth).mockReturnValue({
          user: { id: 'user-123' } as unknown as UserResource,
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          getToken: vi.fn(async () => 'mock-token'),
        })
      })

      it('can see timeline but cannot revert', async () => {
        mockUseRevisionHistory.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisions,
          error: null,
        } as UseQueryResult<ListRevisionsResponse, Error>)

        render(
          <RevisionTimeline
            slug="test-post"
            currentSha="abc123d"
            onSelectRevision={vi.fn()}
            isAuthor={false}
          />,
          {
            wrapper: createWrapper(),
          }
        )

        const timeline = screen.getByTestId('revision-timeline-container')
        expect(timeline).toBeInTheDocument()

        const revisionItem = screen.getByTestId('revision-item-789ghi0')
        expect(revisionItem).not.toHaveAttribute('role', 'button')
      })

      it('revision items are not clickable in read-only mode', async () => {
        mockUseRevisionHistory.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisions,
          error: null,
        } as UseQueryResult<ListRevisionsResponse, Error>)

        const mockSelect = vi.fn()

        render(
          <RevisionTimeline
            slug="test-post"
            currentSha="abc123d"
            onSelectRevision={mockSelect}
            isAuthor={false}
          />,
          {
            wrapper: createWrapper(),
          }
        )

        const revisionItem = screen.getByTestId('revision-item-789ghi0')
        await user.click(revisionItem)

        expect(mockSelect).not.toHaveBeenCalled()
      })
    })

    describe('Post Author', () => {
      beforeEach(() => {
        vi.mocked(useAuth).mockReturnValue({
          user: { id: 'author-id' } as unknown as UserResource,
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          getToken: vi.fn(async () => 'author-token'),
        })
      })

      it('can see timeline and revert buttons', async () => {
        mockUseRevisionHistory.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisions,
          error: null,
        } as UseQueryResult<ListRevisionsResponse, Error>)

        mockUseRevisionDetail.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisionDetail,
          error: null,
        } as UseQueryResult<RevisionDetailType, Error>)

        render(
          <>
            <RevisionTimeline
              slug="test-post"
              currentSha="abc123d"
              onSelectRevision={vi.fn()}
              isAuthor={true}
            />
            <RevisionDetail
              slug="test-post"
              revisionSha="789ghi0"
              isAuthor={true}
              onRevertSuccess={vi.fn()}
            />
          </>,
          {
            wrapper: createWrapper(),
          }
        )

        const timeline = screen.getByTestId('revision-timeline-container')
        expect(timeline).toBeInTheDocument()

        const revertButton = screen.getByTestId('revision-detail-revert-button')
        expect(revertButton).toBeInTheDocument()
      })

      it('revision items are clickable in author mode', async () => {
        mockUseRevisionHistory.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisions,
          error: null,
        } as UseQueryResult<ListRevisionsResponse, Error>)

        const mockSelect = vi.fn()

        render(
          <RevisionTimeline
            slug="test-post"
            currentSha="abc123d"
            onSelectRevision={mockSelect}
            isAuthor={true}
          />,
          {
            wrapper: createWrapper(),
          }
        )

        const revisionItem = screen.getByTestId('revision-item-789ghi0')
        expect(revisionItem).toHaveAttribute('role', 'button')

        await user.click(revisionItem)

        expect(mockSelect).toHaveBeenCalledWith('789ghi0')
      })
    })

    describe('Admin', () => {
      beforeEach(() => {
        vi.mocked(useAuth).mockReturnValue({
          user: { id: 'admin-id' } as unknown as UserResource,
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          getToken: vi.fn(async () => 'admin-token'),
        })
      })

      it('can see timeline and revert buttons', async () => {
        mockUseRevisionHistory.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisions,
          error: null,
        } as UseQueryResult<ListRevisionsResponse, Error>)

        mockUseRevisionDetail.mockReturnValue({
          isLoading: false,
          isError: false,
          isSuccess: true,
          data: mockRevisionDetail,
          error: null,
        } as UseQueryResult<RevisionDetailType, Error>)

        render(
          <>
            <RevisionTimeline
              slug="test-post"
              currentSha="abc123d"
              onSelectRevision={vi.fn()}
              isAuthor={true}
            />
            <RevisionDetail
              slug="test-post"
              revisionSha="789ghi0"
              isAuthor={true}
              onRevertSuccess={vi.fn()}
            />
          </>,
          {
            wrapper: createWrapper(),
          }
        )

        const timeline = screen.getByTestId('revision-timeline-container')
        expect(timeline).toBeInTheDocument()

        const revertButton = screen.getByTestId('revision-detail-revert-button')
        expect(revertButton).toBeInTheDocument()
      })
    })
  })

  describe('Basic Interaction Tests', () => {
    beforeEach(() => {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: 'author-id' } as unknown as UserResource,
        isLoaded: true,
        isSignedIn: true,
        role: 'author',
        getToken: vi.fn(async () => 'author-token'),
      })
    })

    it('renders timeline with revision list', async () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisions,
        error: null,
      } as UseQueryResult<ListRevisionsResponse, Error>)

      render(
        <RevisionTimeline
          slug="test-post"
          currentSha="abc123d"
          onSelectRevision={vi.fn()}
          isAuthor={true}
        />,
        {
          wrapper: createWrapper(),
        }
      )

      const timeline = screen.getByTestId('revision-timeline-container')
      expect(timeline).toBeInTheDocument()

      expect(screen.getByTestId('revision-item-abc123d')).toBeInTheDocument()
      expect(screen.getByTestId('revision-item-789ghi0')).toBeInTheDocument()
    })

    it('renders revision detail with content', async () => {
      mockUseRevisionDetail.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionDetail,
        error: null,
      } as UseQueryResult<RevisionDetailType, Error>)

      render(
        <RevisionDetail
          slug="test-post"
          revisionSha="789ghi0"
          isAuthor={true}
          onRevertSuccess={vi.fn()}
        />,
        {
          wrapper: createWrapper(),
        }
      )

      const detail = screen.getByTestId('revision-detail')
      expect(detail).toBeInTheDocument()

      expect(screen.getByText('Updated content')).toBeInTheDocument()
    })

    it('clicking revision item calls onSelectRevision', async () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisions,
        error: null,
      } as UseQueryResult<ListRevisionsResponse, Error>)

      const mockSelect = vi.fn()

      render(
        <RevisionTimeline
          slug="test-post"
          currentSha="abc123d"
          onSelectRevision={mockSelect}
          isAuthor={true}
        />,
        {
          wrapper: createWrapper(),
        }
      )

      const revisionItem = screen.getByTestId('revision-item-789ghi0')
      await user.click(revisionItem)

      expect(mockSelect).toHaveBeenCalledWith('789ghi0')
    })
  })
})
