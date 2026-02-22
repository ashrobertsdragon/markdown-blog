import type { UseQueryResult } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RevisionTimeline } from '@/components/revision/RevisionTimeline'
import type { ListRevisionsResponse } from '@/services/revisionsApi'

vi.mock('@/hooks/useRevisions')

const mockUseRevisionHistory = vi.hoisted(() => vi.fn())

vi.mock('@/hooks/useRevisions', () => ({
  useRevisionHistory: mockUseRevisionHistory,
}))

/**
 * Test suite for RevisionTimeline component
 *
 * Tests chronological revision history display with pagination, selection,
 * and authorization controls. Validates all rendering states and user interactions.
 */
describe('RevisionTimeline', () => {
  const defaultProps = {
    slug: 'test-post',
    currentSha: 'abc123d',
    onSelectRevision: vi.fn(),
    isAuthor: true,
  }

  const mockRevisionsData: ListRevisionsResponse = {
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
        author: { id: '42', name: 'Test Author' },
        timestamp: '2026-02-15T08:00:00Z',
        relative_time: '4 hours ago',
        commit_message: 'Revert to previous version',
        is_revert: true,
      },
    ],
    total_count: 3,
    has_more: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering States - Loading', () => {
    it('shows loading skeleton when data is loading', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: true,
        isError: false,
        data: undefined,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const skeleton = screen.getByTestId('revision-timeline-loading')
      expect(skeleton).toBeInTheDocument()
    })

    it('does not show revision list when loading', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: true,
        isError: false,
        data: undefined,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const list = screen.queryByTestId('revision-timeline-list')
      expect(list).not.toBeInTheDocument()
    })
  })

  describe('Rendering States - Success', () => {
    it('displays list of revisions with correct data', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const list = screen.getByTestId('revision-timeline-list')
      expect(list).toBeInTheDocument()

      expect(screen.getByText('abc123d')).toBeInTheDocument()
      expect(screen.getByText('789ghi0')).toBeInTheDocument()
      expect(screen.getByText('def456a')).toBeInTheDocument()
    })

    it('shows author names for each revision', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const authorElements = screen.getAllByText('Test Author')
      expect(authorElements).toHaveLength(3)
    })

    it('shows relative timestamps for each revision', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      expect(screen.getByText('2 hours ago')).toBeInTheDocument()
      expect(screen.getByText('3 hours ago')).toBeInTheDocument()
      expect(screen.getByText('4 hours ago')).toBeInTheDocument()
    })

    it('shows commit messages for each revision', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      expect(screen.getByText('Initial commit')).toBeInTheDocument()
      expect(screen.getByText('Updated content')).toBeInTheDocument()
      expect(screen.getByText('Revert to previous version')).toBeInTheDocument()
    })

    it('does not show loading skeleton when data is loaded', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const skeleton = screen.queryByTestId('revision-timeline-loading')
      expect(skeleton).not.toBeInTheDocument()
    })
  })

  describe('Rendering States - Error', () => {
    it('shows error message when query fails', () => {
      const errorMessage = 'Failed to fetch revisions'
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: true,
        isSuccess: false,
        data: undefined,
        error: new Error(errorMessage),
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const errorElement = screen.getByTestId('revision-timeline-error')
      expect(errorElement).toBeInTheDocument()
    })

    it('shows retry button on error', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: true,
        isSuccess: false,
        data: undefined,
        error: new Error('Network error'),
        refetch: vi.fn(),
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const retryButton = screen.getByTestId('revision-timeline-retry')
      expect(retryButton).toBeInTheDocument()
    })

    it('calls refetch when retry button is clicked', () => {
      const mockRefetch = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: true,
        isSuccess: false,
        data: undefined,
        error: new Error('Network error'),
        refetch: mockRefetch,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const retryButton = screen.getByTestId('revision-timeline-retry')
      fireEvent.click(retryButton)

      expect(mockRefetch).toHaveBeenCalledTimes(1)
    })

    it('does not show revision list on error', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: true,
        isSuccess: false,
        data: undefined,
        error: new Error('Network error'),
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const list = screen.queryByTestId('revision-timeline-list')
      expect(list).not.toBeInTheDocument()
    })

    it('displays user-friendly error message for network errors', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: true,
        isSuccess: false,
        data: undefined,
        error: new Error('Failed to fetch'),
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      expect(screen.getByText(/failed to load revisions/i)).toBeInTheDocument()
    })
  })

  describe('Rendering States - Empty', () => {
    it('shows empty state message when revision list is empty', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          revisions: [],
          total_count: 0,
          has_more: false,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const emptyState = screen.getByTestId('revision-timeline-empty')
      expect(emptyState).toBeInTheDocument()
    })

    it('displays "No revisions yet" message in empty state', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          revisions: [],
          total_count: 0,
          has_more: false,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      expect(screen.getByText(/no revisions yet/i)).toBeInTheDocument()
    })

    it('does not show loading skeleton when empty', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          revisions: [],
          total_count: 0,
          has_more: false,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const skeleton = screen.queryByTestId('revision-timeline-loading')
      expect(skeleton).not.toBeInTheDocument()
    })
  })

  describe('Revision List Display - Current Revision Indicator', () => {
    it('shows visual indicator for current revision matching currentSha', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const currentRevision = screen.getByTestId('revision-item-abc123d')
      expect(currentRevision).toHaveAttribute('data-current', 'true')
    })

    it('does not show current indicator for non-current revisions', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const otherRevision = screen.getByTestId('revision-item-789ghi0')
      expect(otherRevision).toHaveAttribute('data-current', 'false')
    })

    it('shows current badge on current revision', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const currentBadge = screen.getByTestId('revision-current-badge-abc123d')
      expect(currentBadge).toBeInTheDocument()
    })
  })

  describe('Revision List Display - Revert Indicator', () => {
    it('shows visual indicator for revert revisions', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const revertIndicator = screen.getByTestId('revision-revert-badge-def456a')
      expect(revertIndicator).toBeInTheDocument()
    })

    it('does not show revert indicator for non-revert revisions', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const revertBadge = screen.queryByTestId('revision-revert-badge-abc123d')
      expect(revertBadge).not.toBeInTheDocument()
    })
  })

  describe('Revision List Display - Hover Tooltips', () => {
    it('shows tooltip with full SHA on hover', async () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const shaElement = screen.getByTestId('revision-sha-abc123d')
      expect(shaElement).toHaveAttribute('title', 'abc123def456')
    })

    it('all revision SHAs have tooltip attributes', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const sha1 = screen.getByTestId('revision-sha-abc123d')
      const sha2 = screen.getByTestId('revision-sha-789ghi0')
      const sha3 = screen.getByTestId('revision-sha-def456a')

      expect(sha1).toHaveAttribute('title', 'abc123def456')
      expect(sha2).toHaveAttribute('title', '789ghi012jkl')
      expect(sha3).toHaveAttribute('title', 'def456abc789')
    })
  })

  describe('Pagination - Load More Button', () => {
    it('shows "Load More" button when has_more is true', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          ...mockRevisionsData,
          has_more: true,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const loadMoreButton = screen.getByTestId('revision-timeline-load-more')
      expect(loadMoreButton).toBeInTheDocument()
    })

    it('hides "Load More" button when has_more is false', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          ...mockRevisionsData,
          has_more: false,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const loadMoreButton = screen.queryByTestId('revision-timeline-load-more')
      expect(loadMoreButton).not.toBeInTheDocument()
    })

    it('clicking "Load More" increases skip parameter', async () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          ...mockRevisionsData,
          has_more: true,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const loadMoreButton = screen.getByTestId('revision-timeline-load-more')
      fireEvent.click(loadMoreButton)

      await waitFor(() => {
        expect(mockUseRevisionHistory).toHaveBeenLastCalledWith('test-post', 3, 20)
      })
    })

    it('shows loading state while loading more revisions', async () => {
      mockUseRevisionHistory.mockReturnValueOnce({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          ...mockRevisionsData,
          has_more: true,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      const { rerender } = render(<RevisionTimeline {...defaultProps} />)

      const loadMoreButton = screen.getByTestId('revision-timeline-load-more')
      fireEvent.click(loadMoreButton)

      mockUseRevisionHistory.mockReturnValueOnce({
        isLoading: true,
        isError: false,
        isSuccess: false,
        data: undefined,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      rerender(<RevisionTimeline {...defaultProps} />)

      expect(screen.getByTestId('revision-timeline-load-more-loading')).toBeInTheDocument()
    })

    it('disables "Load More" button while loading', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: true,
        isError: false,
        isSuccess: false,
        data: {
          ...mockRevisionsData,
          has_more: true,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const loadMoreButton = screen.getByTestId('revision-timeline-load-more')
      expect(loadMoreButton).toBeDisabled()
    })
  })

  describe('Authorization - Author Mode', () => {
    it('shows clickable revision items when isAuthor is true', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      expect(revisionItem).toHaveAttribute('role', 'button')
    })

    it('calls onSelectRevision when revision is clicked and isAuthor is true', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} onSelectRevision={mockOnSelect} />)

      const revisionItem = screen.getByTestId('revision-item-789ghi0')
      fireEvent.click(revisionItem)

      expect(mockOnSelect).toHaveBeenCalledWith('789ghi0')
      expect(mockOnSelect).toHaveBeenCalledTimes(1)
    })

    it('calls onSelectRevision with correct SHA for each revision', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} onSelectRevision={mockOnSelect} />)

      const revision1 = screen.getByTestId('revision-item-abc123d')
      const revision2 = screen.getByTestId('revision-item-789ghi0')
      const revision3 = screen.getByTestId('revision-item-def456a')

      fireEvent.click(revision1)
      expect(mockOnSelect).toHaveBeenLastCalledWith('abc123d')

      fireEvent.click(revision2)
      expect(mockOnSelect).toHaveBeenLastCalledWith('789ghi0')

      fireEvent.click(revision3)
      expect(mockOnSelect).toHaveBeenLastCalledWith('def456a')

      expect(mockOnSelect).toHaveBeenCalledTimes(3)
    })

    it('activates revision item with Enter key when isAuthor is true', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} onSelectRevision={mockOnSelect} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      fireEvent.keyDown(revisionItem, { key: 'Enter', code: 'Enter', charCode: 13 })

      expect(mockOnSelect).toHaveBeenCalledWith('abc123d')
      expect(mockOnSelect).toHaveBeenCalledTimes(1)
    })

    it('activates revision item with Space key when isAuthor is true', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} onSelectRevision={mockOnSelect} />)

      const revisionItem = screen.getByTestId('revision-item-789ghi0')
      fireEvent.keyDown(revisionItem, { key: ' ', code: 'Space', charCode: 32 })

      expect(mockOnSelect).toHaveBeenCalledWith('789ghi0')
      expect(mockOnSelect).toHaveBeenCalledTimes(1)
    })

    it('prevents default Space key behavior to avoid page scroll', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} onSelectRevision={mockOnSelect} />)

      const revisionItem = screen.getByTestId('revision-item-def456a')
      const event = new KeyboardEvent('keydown', { key: ' ', code: 'Space', bubbles: true })
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')

      revisionItem.dispatchEvent(event)

      expect(preventDefaultSpy).toHaveBeenCalled()
    })

    it('ignores other keys when isAuthor is true', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={true} onSelectRevision={mockOnSelect} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      fireEvent.keyDown(revisionItem, { key: 'a', code: 'KeyA' })
      fireEvent.keyDown(revisionItem, { key: 'Tab', code: 'Tab' })
      fireEvent.keyDown(revisionItem, { key: 'Escape', code: 'Escape' })

      expect(mockOnSelect).not.toHaveBeenCalled()
    })
  })

  describe('Authorization - Read-Only Mode', () => {
    it('shows read-only revision items when isAuthor is false', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={false} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      expect(revisionItem).not.toHaveAttribute('role', 'button')
    })

    it('does not call onSelectRevision when revision is clicked and isAuthor is false', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(
        <RevisionTimeline {...defaultProps} isAuthor={false} onSelectRevision={mockOnSelect} />
      )

      const revisionItem = screen.getByTestId('revision-item-789ghi0')
      fireEvent.click(revisionItem)

      expect(mockOnSelect).not.toHaveBeenCalled()
    })

    it('revision items do not have hover styling when isAuthor is false', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} isAuthor={false} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      expect(revisionItem).toHaveAttribute('data-interactive', 'false')
    })

    it('ignores keyboard activation when isAuthor is false', () => {
      const mockOnSelect = vi.fn()
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(
        <RevisionTimeline {...defaultProps} isAuthor={false} onSelectRevision={mockOnSelect} />
      )

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      fireEvent.keyDown(revisionItem, { key: 'Enter', code: 'Enter', charCode: 13 })
      fireEvent.keyDown(revisionItem, { key: ' ', code: 'Space', charCode: 32 })

      expect(mockOnSelect).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA role for timeline container', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const timeline = screen.getByRole('list')
      expect(timeline).toBeInTheDocument()
    })

    it('has proper ARIA labels for revision items', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      expect(revisionItem).toHaveAttribute('aria-label')
    })

    it('has aria-current="true" on current revision', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const currentRevision = screen.getByTestId('revision-item-abc123d')
      expect(currentRevision).toHaveAttribute('aria-current', 'true')
    })

    it('has aria-live region for loading state', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: true,
        isError: false,
        data: undefined,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const loadingRegion = screen.getByTestId('revision-timeline-loading')
      expect(loadingRegion).toHaveAttribute('aria-live', 'polite')
    })

    it('has aria-live region for error state', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: true,
        data: undefined,
        error: new Error('Network error'),
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const errorRegion = screen.getByTestId('revision-timeline-error')
      expect(errorRegion).toHaveAttribute('aria-live', 'assertive')
    })
  })

  describe('Hook Integration', () => {
    it('calls useRevisionHistory with postId and default pagination', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      expect(mockUseRevisionHistory).toHaveBeenCalledWith('test-post', 0, 20)
    })

    it('calls useRevisionHistory with updated skip on load more', async () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: {
          ...mockRevisionsData,
          has_more: true,
        },
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const loadMoreButton = screen.getByTestId('revision-timeline-load-more')
      fireEvent.click(loadMoreButton)

      await waitFor(() => {
        expect(mockUseRevisionHistory).toHaveBeenCalledWith('test-post', 3, 20)
      })
    })
  })

  describe('Responsive Design', () => {
    it('applies responsive CSS classes to timeline container', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const container = screen.getByTestId('revision-timeline-container')
      expect(container).toHaveClass('revision-timeline')
    })

    it('applies mobile-friendly spacing to revision items', () => {
      mockUseRevisionHistory.mockReturnValue({
        isLoading: false,
        isError: false,
        isSuccess: true,
        data: mockRevisionsData,
        error: null,
      } as unknown as UseQueryResult<ListRevisionsResponse, Error>)

      render(<RevisionTimeline {...defaultProps} />)

      const revisionItem = screen.getByTestId('revision-item-abc123d')
      expect(revisionItem).toHaveClass('revision-item')
    })
  })
})
