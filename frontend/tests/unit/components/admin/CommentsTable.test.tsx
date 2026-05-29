import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CommentsTable } from '@/components/admin/CommentsTable'
import { useComments, useDeleteComment } from '@/hooks/admin/useComments'
import {
  createMockAdminComment,
  createMockCommentsResponse,
  createMockLongTextAdminComment,
  createMockPaginatedCommentsResponse,
} from '../../../fixtures/adminContent.fixtures'

vi.mock('@/hooks/admin/useComments', () => ({
  useComments: vi.fn(),
  useDeleteComment: vi.fn(),
}))

vi.mock('@/components/admin/ConfirmModal', () => ({
  default: vi.fn(({ onConfirm, onCancel, title, message }) => (
    <div data-testid="confirm-modal">
      <p>{title}</p>
      <p>{message}</p>
      <button type="button" onClick={onConfirm}>
        Confirm
      </button>
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
    </div>
  )),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const mockDeleteMutation = {
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
}

const mockUseCommentsReturn = {
  data: undefined,
  isLoading: false,
  isError: false,
  error: null,
  isFetching: false,
  isRefetching: false,
  isSuccess: false,
  isStale: false,
  isPending: false,
  status: 'pending' as const,
  fetchStatus: 'idle' as const,
  errorUpdateCount: 0,
  failureCount: 0,
  failureReason: null,
  errorUpdatedAt: 0,
  isFetchedAfterMount: false,
  isPreviousData: false,
}

/**
 * CommentsTable component test suite.
 *
 * Tests for paginated comment moderation table with delete capability.
 * Covers table structure, data display, content truncation, delete flow with
 * ConfirmModal, loading/error/empty states, pagination display, and accessibility.
 */
describe('CommentsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useComments).mockReturnValue(mockUseCommentsReturn as never)
    vi.mocked(useDeleteComment).mockReturnValue(mockDeleteMutation as never)
  })

  describe('Table Structure', () => {
    it('should_render_table_element_with_role_table', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    it('should_render_content_column_header', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('columnheader', { name: /content/i })).toBeInTheDocument()
    })

    it('should_render_author_column_header', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('columnheader', { name: /author/i })).toBeInTheDocument()
    })

    it('should_render_post_column_header', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('columnheader', { name: /post/i })).toBeInTheDocument()
    })

    it('should_render_date_column_header', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('columnheader', { name: /date/i })).toBeInTheDocument()
    })

    it('should_render_actions_column_header', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('columnheader', { name: /actions/i })).toBeInTheDocument()
    })

    it('should_render_one_data_row_per_comment', () => {
      const comments = [
        createMockAdminComment({ id: 1 }),
        createMockAdminComment({ id: 2 }),
        createMockAdminComment({ id: 3 }),
      ]

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse(comments, 3, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getAllByRole('row')).toHaveLength(4) // 1 header + 3 data rows
    })
  })

  describe('Data Display', () => {
    it('should_display_comment_text_in_table', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse(
          [createMockAdminComment({ text: 'This is a short comment.' })],
          1,
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText(/This is a short comment\./)).toBeInTheDocument()
    })

    it('should_display_author_name_in_table', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ author: 'Jane Smith' })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText('Jane Smith')).toBeInTheDocument()
    })

    it('should_display_post_title_in_table', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse(
          [createMockAdminComment({ post_title: 'My Interesting Article' })],
          1,
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText('My Interesting Article')).toBeInTheDocument()
    })

    it('should_format_created_at_as_MM_DD_YYYY', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse(
          [createMockAdminComment({ created_at: '2026-03-22T14:00:00Z' })],
          1,
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText(/03\/22\/2026/)).toBeInTheDocument()
    })

    it('should_display_data_for_multiple_comments', () => {
      const comments = [
        createMockAdminComment({ id: 1, author: 'Alice', post_title: 'Post Alpha' }),
        createMockAdminComment({ id: 2, author: 'Bob', post_title: 'Post Beta' }),
      ]

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse(comments, 2, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText('Alice')).toBeInTheDocument()
      expect(screen.getByText('Bob')).toBeInTheDocument()
      expect(screen.getByText('Post Alpha')).toBeInTheDocument()
      expect(screen.getByText('Post Beta')).toBeInTheDocument()
    })
  })

  describe('Content Truncation', () => {
    it('should_display_truncated_text_for_comments_longer_than_100_chars', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockLongTextAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const longText =
        'This is a very long comment that exceeds the one hundred character limit set for display truncation in the admin comments table view.'
      expect(screen.queryByText(longText)).not.toBeInTheDocument()
    })

    it('should_display_first_100_chars_of_long_comment', () => {
      const longText =
        'This is a very long comment that exceeds the one hundred character limit set for display truncation in the admin comments table view.'
      const expectedStart = longText.slice(0, 100)

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ text: longText })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const cell = screen.getByText(new RegExp(expectedStart.slice(0, 40)))
      expect(cell).toBeInTheDocument()
    })

    it('should_display_full_text_for_comments_at_or_under_100_chars', () => {
      const exactText = 'A'.repeat(100)

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ text: exactText })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText(exactText)).toBeInTheDocument()
    })
  })

  describe('Delete Flow', () => {
    it('should_not_show_confirm_modal_on_initial_render', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.queryByTestId('confirm-modal')).not.toBeInTheDocument()
    })

    it('should_show_confirm_modal_when_delete_button_clicked', async () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await userEvent.click(deleteButton)

      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()
    })

    it('should_hide_confirm_modal_when_cancel_clicked', async () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      await userEvent.click(screen.getByRole('button', { name: /delete/i }))
      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()

      await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
      expect(screen.queryByTestId('confirm-modal')).not.toBeInTheDocument()
    })

    it('should_call_mutate_with_commentId_when_confirm_clicked', async () => {
      const mutate = vi.fn()
      vi.mocked(useDeleteComment).mockReturnValue({
        ...mockDeleteMutation,
        mutate,
      } as never)

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ id: 99 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      await userEvent.click(screen.getByRole('button', { name: /delete/i }))
      await userEvent.click(screen.getByRole('button', { name: /confirm/i }))

      expect(mutate).toHaveBeenCalledWith({ commentId: 99 })
    })

    it('should_pass_correct_commentId_when_multiple_comments_shown', async () => {
      const mutate = vi.fn()
      vi.mocked(useDeleteComment).mockReturnValue({
        ...mockDeleteMutation,
        mutate,
      } as never)

      const comments = [
        createMockAdminComment({ id: 11, author: 'User A' }),
        createMockAdminComment({ id: 22, author: 'User B' }),
      ]

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse(comments, 2, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      await userEvent.click(deleteButtons[1])
      await userEvent.click(screen.getByRole('button', { name: /confirm/i }))

      expect(mutate).toHaveBeenCalledWith({ commentId: 22 })
    })

    it('should_not_call_mutate_when_cancel_clicked', async () => {
      const mutate = vi.fn()
      vi.mocked(useDeleteComment).mockReturnValue({
        ...mockDeleteMutation,
        mutate,
      } as never)

      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      await userEvent.click(screen.getByRole('button', { name: /delete/i }))
      await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

      expect(mutate).not.toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('should_render_status_element_when_loading', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        isLoading: true,
        isPending: true,
        status: 'pending',
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument()
    })

    it('should_show_loading_indicator_when_fetching', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        isLoading: true,
        isFetching: true,
        isPending: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const loadingIndicator = screen.queryByText(/loading/i) || screen.queryByRole('status')
      expect(loadingIndicator).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should_display_error_text_when_fetch_fails', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        isError: true,
        error: new Error('Failed to load comments'),
        status: 'error',
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText(/error|failed/i)).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('should_display_no_comments_message_when_comments_array_is_empty', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([], 0, 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getByText(/no comments/i)).toBeInTheDocument()
    })

    it('should_not_render_data_rows_in_empty_state', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([], 0, 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const rows = screen.queryAllByRole('row')
      expect(rows.length).toBeLessThanOrEqual(1)
    })
  })

  describe('Pagination Display', () => {
    it('should_display_current_page_number', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockPaginatedCommentsResponse(3, 2, 3, 9),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable page={2} limit={3} />)

      expect(screen.getByText(/page.*2/i)).toBeInTheDocument()
    })

    it('should_display_total_pages', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockPaginatedCommentsResponse(3, 1, 3, 12),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable page={1} limit={3} />)

      expect(screen.getByText(/of\s+4/i)).toBeInTheDocument()
    })

    it('should_display_total_comment_count_in_pagination_info', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockPaginatedCommentsResponse(3, 1, 3, 15),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable page={1} limit={3} />)

      expect(screen.getByText(/15\s+total|15.*comments/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should_have_column_headers_with_scope_col', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const headers = screen.getAllByRole('columnheader')
      for (const header of headers) {
        expect(header).toHaveAttribute('scope', 'col')
      }
    })

    it('should_have_semantic_button_element_for_delete', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      expect(deleteButton.tagName).toBe('BUTTON')
    })

    it('should_support_keyboard_activation_of_delete_button', async () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      deleteButton.focus()
      expect(deleteButton).toHaveFocus()

      await userEvent.keyboard('{Enter}')

      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()
    })

    it('should_have_correct_number_of_column_headers', () => {
      vi.mocked(useComments).mockReturnValue({
        ...mockUseCommentsReturn,
        data: createMockCommentsResponse([createMockAdminComment()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<CommentsTable />)

      expect(screen.getAllByRole('columnheader')).toHaveLength(5) // content, author, post, date, actions
    })
  })
})
