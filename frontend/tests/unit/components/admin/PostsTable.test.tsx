import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PostsTable } from '@/components/admin/PostsTable'
import { usePosts, useUnpublishPost } from '@/hooks/admin/usePosts'
import {
  createMockAdminPost,
  createMockPaginatedPostsResponse,
  createMockPostsResponse,
} from '../../../fixtures/adminContent.fixtures'

vi.mock('@/hooks/admin/usePosts', () => ({
  usePosts: vi.fn(),
  useUnpublishPost: vi.fn(),
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

const mockUnpublishMutation = {
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

const mockUsePostsReturn = {
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
 * PostsTable component test suite.
 *
 * Tests for paginated published-post management table with unpublish capability.
 * Covers table structure, data display, view links, unpublish flow with
 * ConfirmModal, loading/error/empty states, and pagination display.
 */
describe('PostsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usePosts).mockReturnValue(mockUsePostsReturn as never)
    vi.mocked(useUnpublishPost).mockReturnValue(mockUnpublishMutation as never)
  })

  describe('Table Structure', () => {
    it('should_render_table_element_with_role_table', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    it('should_render_title_column_header', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByRole('columnheader', { name: /title/i })).toBeInTheDocument()
    })

    it('should_render_author_column_header', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByRole('columnheader', { name: /author/i })).toBeInTheDocument()
    })

    it('should_render_published_date_column_header', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByRole('columnheader', { name: /published/i })).toBeInTheDocument()
    })

    it('should_render_actions_column_header', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByRole('columnheader', { name: /actions/i })).toBeInTheDocument()
    })

    it('should_render_one_data_row_per_post', () => {
      const posts = [
        createMockAdminPost({ id: 1, title: 'Post One' }),
        createMockAdminPost({ id: 2, title: 'Post Two' }),
        createMockAdminPost({ id: 3, title: 'Post Three' }),
      ]

      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse(posts, 3, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getAllByRole('row')).toHaveLength(4) // 1 header + 3 data rows
    })
  })

  describe('Data Display', () => {
    it('should_display_post_title_in_table', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ title: 'My Awesome Article' })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByText('My Awesome Article')).toBeInTheDocument()
    })

    it('should_display_author_name_in_table', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ author: 'Jane Doe' })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByText('Jane Doe')).toBeInTheDocument()
    })

    it('should_format_published_at_as_MM_DD_YYYY', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse(
          [createMockAdminPost({ published_at: '2026-05-15T10:30:00Z' })],
          1,
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByText(/05\/15\/2026/)).toBeInTheDocument()
    })

    it('should_display_data_for_multiple_posts', () => {
      const posts = [
        createMockAdminPost({ id: 1, title: 'First Post', author: 'Alice' }),
        createMockAdminPost({ id: 2, title: 'Second Post', author: 'Bob' }),
      ]

      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse(posts, 2, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByText('First Post')).toBeInTheDocument()
      expect(screen.getByText('Second Post')).toBeInTheDocument()
      expect(screen.getByText('Alice')).toBeInTheDocument()
      expect(screen.getByText('Bob')).toBeInTheDocument()
    })
  })

  describe('View Post Link', () => {
    it('should_render_view_link_for_each_post', () => {
      const posts = [
        createMockAdminPost({ id: 1, slug: 'post-one' }),
        createMockAdminPost({ id: 2, slug: 'post-two' }),
      ]

      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse(posts, 2, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getAllByRole('link', { name: /view/i })).toHaveLength(2)
    })

    it('should_set_href_to_posts_slug_path', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ slug: 'my-first-post' })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      const viewLink = screen.getByRole('link', { name: /view/i })
      expect(viewLink).toHaveAttribute('href', '/blog/my-first-post')
    })

    it('should_open_view_link_in_new_tab', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      const viewLink = screen.getByRole('link', { name: /view/i })
      expect(viewLink).toHaveAttribute('target', '_blank')
    })

    it('should_have_noopener_noreferrer_rel_on_view_link', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost()], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      const viewLink = screen.getByRole('link', { name: /view/i })
      expect(viewLink).toHaveAttribute('rel', 'noopener noreferrer')
    })
  })

  describe('Unpublish Flow', () => {
    it('should_show_confirm_modal_when_unpublish_button_clicked', async () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ id: 1, title: 'My Post' })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.queryByTestId('confirm-modal')).not.toBeInTheDocument()

      const unpublishButton = screen.getByRole('button', { name: /unpublish/i })
      await userEvent.click(unpublishButton)

      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()
    })

    it('should_hide_confirm_modal_when_cancel_clicked', async () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      await userEvent.click(screen.getByRole('button', { name: /unpublish/i }))
      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()

      await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
      expect(screen.queryByTestId('confirm-modal')).not.toBeInTheDocument()
    })

    it('should_call_mutate_with_postId_when_confirm_clicked', async () => {
      const mutate = vi.fn()
      vi.mocked(useUnpublishPost).mockReturnValue({
        ...mockUnpublishMutation,
        mutate,
      } as never)

      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ id: 7 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      await userEvent.click(screen.getByRole('button', { name: /unpublish/i }))
      await userEvent.click(screen.getByRole('button', { name: /confirm/i }))

      expect(mutate).toHaveBeenCalledWith({ postId: 7 })
    })

    it('should_pass_correct_postId_when_multiple_posts_shown', async () => {
      const mutate = vi.fn()
      vi.mocked(useUnpublishPost).mockReturnValue({
        ...mockUnpublishMutation,
        mutate,
      } as never)

      const posts = [
        createMockAdminPost({ id: 10, title: 'First Post' }),
        createMockAdminPost({ id: 20, title: 'Second Post' }),
      ]

      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse(posts, 2, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      const unpublishButtons = screen.getAllByRole('button', { name: /unpublish/i })
      await userEvent.click(unpublishButtons[1])
      await userEvent.click(screen.getByRole('button', { name: /confirm/i }))

      expect(mutate).toHaveBeenCalledWith({ postId: 20 })
    })

    it('should_not_call_mutate_when_cancel_clicked', async () => {
      const mutate = vi.fn()
      vi.mocked(useUnpublishPost).mockReturnValue({
        ...mockUnpublishMutation,
        mutate,
      } as never)

      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([createMockAdminPost({ id: 1 })], 1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      await userEvent.click(screen.getByRole('button', { name: /unpublish/i }))
      await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

      expect(mutate).not.toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('should_render_status_element_when_loading', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        isLoading: true,
        isPending: true,
        status: 'pending',
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByTestId('loading')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should_display_error_text_when_fetch_fails', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        isError: true,
        error: new Error('Failed to load posts'),
        status: 'error',
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByText(/error|failed/i)).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('should_display_no_posts_message_when_posts_array_is_empty', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([], 0, 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      expect(screen.getByText(/no posts/i)).toBeInTheDocument()
    })

    it('should_not_render_data_rows_in_empty_state', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPostsResponse([], 0, 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable />)

      const rows = screen.queryAllByRole('row')
      expect(rows.length).toBeLessThanOrEqual(1)
    })
  })

  describe('Pagination Display', () => {
    it('should_display_current_page_number', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPaginatedPostsResponse(3, 2, 3, 9),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable page={2} limit={3} />)

      expect(screen.getByText(/page.*2/i)).toBeInTheDocument()
    })

    it('should_display_total_pages', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPaginatedPostsResponse(3, 1, 3, 12),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable page={1} limit={3} />)

      expect(screen.getByText(/of\s+4/i)).toBeInTheDocument()
    })

    it('should_display_total_post_count_in_pagination_info', () => {
      vi.mocked(usePosts).mockReturnValue({
        ...mockUsePostsReturn,
        data: createMockPaginatedPostsResponse(3, 1, 3, 15),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<PostsTable page={1} limit={3} />)

      expect(screen.getByText(/15\s+total|15.*posts/i)).toBeInTheDocument()
    })
  })
})
