import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UserTable } from '@/components/admin/UserTable'
import { useUsers } from '@/hooks/admin/useUsers'
import {
  createMockAdminUser,
  createMockAuthenticatedUser,
  createMockMixedRolesResponse,
  createMockNewUser,
  createMockPaginatedUsersResponse,
  createMockUser,
  createMockUsersResponse,
} from '../../../fixtures/users.fixtures'

/**
 * UserTable component test suite
 *
 * Tests for paginated user management table with role editing capability.
 * Covers table structure, data display, user interactions, loading/error/empty
 * states, pagination display, and accessibility attributes.
 */

vi.mock('@/hooks/admin/useUsers', () => ({
  useUsers: vi.fn(),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const mockUseUsersReturn = {
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

describe('UserTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useUsers).mockReturnValue(mockUseUsersReturn as never)
  })

  describe('Rendering - Table Structure', () => {
    it('should_render_table_element_with_proper_role', () => {
      const mockCallback = vi.fn()
      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([createMockUser()]),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    it('should_render_table_headers_with_correct_text', () => {
      const mockCallback = vi.fn()
      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([createMockUser()]),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByRole('columnheader', { name: /email/i })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: /role/i })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: /created/i })).toBeInTheDocument()
    })

    it('should_render_user_rows_as_table_rows', () => {
      const mockCallback = vi.fn()
      const users = [
        createMockUser({ id: 1, email: 'user1@test.com' }),
        createMockUser({ id: 2, email: 'user2@test.com' }),
        createMockUser({ id: 3, email: 'user3@test.com' }),
      ]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getAllByRole('row')).toHaveLength(4) // 1 header + 3 data rows
    })
  })

  describe('Data Display - Email Column', () => {
    it('should_display_email_for_each_user', () => {
      const mockCallback = vi.fn()
      const users = [
        createMockUser({ email: 'alice@example.com' }),
        createMockUser({ email: 'bob@example.com' }),
      ]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText('alice@example.com')).toBeInTheDocument()
      expect(screen.getByText('bob@example.com')).toBeInTheDocument()
    })

    it('should_display_display_name_in_email_column', () => {
      const mockCallback = vi.fn()
      const users = [createMockUser({ display_name: 'Alice Johnson', email: 'alice@example.com' })]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    })
  })

  describe('Data Display - Role Badge', () => {
    it('should_display_admin_role_badge_for_admin_users', () => {
      const mockCallback = vi.fn()
      const users = [createMockAdminUser()]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/admin/i)).toBeInTheDocument()
    })

    it('should_display_authenticated_role_badge_for_non_admin_users', () => {
      const mockCallback = vi.fn()
      const users = [createMockAuthenticatedUser({ display_name: 'Regular User' })]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/authenticated/i)).toBeInTheDocument()
    })

    it('should_apply_red_styling_to_admin_role_badge', () => {
      const mockCallback = vi.fn()
      const users = [createMockAdminUser()]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const adminBadge = screen.getByText(/admin/i)
      expect(adminBadge).toHaveClass(/red|danger|bg-red/i)
    })

    it('should_apply_gray_styling_to_authenticated_role_badge', () => {
      const mockCallback = vi.fn()
      const users = [createMockAuthenticatedUser({ display_name: 'Regular User' })]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const authBadge = screen.getByText(/authenticated/i)
      expect(authBadge).toHaveClass(/gray|slate|bg-gray|bg-slate/i)
    })
  })

  describe('Data Display - Created Date', () => {
    it('should_format_created_at_as_MM_DD_YYYY', () => {
      const mockCallback = vi.fn()
      const users = [createMockUser({ created_at: '2026-05-15T10:30:00Z' })]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/05\/15\/2026/)).toBeInTheDocument()
    })

    it('should_display_created_date_for_all_users', () => {
      const mockCallback = vi.fn()
      const users = [
        createMockUser({ created_at: '2026-01-10T08:00:00Z' }),
        createMockUser({ created_at: '2026-02-20T09:00:00Z' }),
      ]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/01\/10\/2026/)).toBeInTheDocument()
      expect(screen.getByText(/02\/20\/2026/)).toBeInTheDocument()
    })
  })

  describe('User Interaction - Edit Role Button', () => {
    it('should_render_edit_role_button_for_each_user', () => {
      const mockCallback = vi.fn()
      const users = [
        createMockUser({ id: 1, email: 'user1@test.com' }),
        createMockUser({ id: 2, email: 'user2@test.com' }),
      ]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButtons = screen.getAllByRole('button', { name: /edit role/i })
      expect(editButtons).toHaveLength(2)
    })

    it('should_call_onEditRole_callback_when_edit_button_clicked', async () => {
      const mockCallback = vi.fn()
      const user = createMockUser({ id: 5, email: 'test@example.com' })

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([user]),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButton = screen.getByRole('button', { name: /edit role/i })
      await userEvent.click(editButton)

      expect(mockCallback).toHaveBeenCalled()
    })

    it('should_pass_complete_user_object_to_onEditRole_callback', async () => {
      const mockCallback = vi.fn()
      const user = createMockUser({
        id: 42,
        clerk_id: 'user_abc123',
        email: 'alice@example.com',
        display_name: 'Alice',
        role: 'authenticated',
      })

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([user]),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButton = screen.getByRole('button', { name: /edit role/i })
      await userEvent.click(editButton)

      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 42,
          email: 'alice@example.com',
          display_name: 'Alice',
          role: 'authenticated',
        })
      )
    })

    it('should_call_onEditRole_with_correct_user_when_multiple_edit_buttons_clicked', async () => {
      const mockCallback = vi.fn()
      const users = [
        createMockUser({ id: 1, email: 'user1@test.com', display_name: 'User One' }),
        createMockUser({ id: 2, email: 'user2@test.com', display_name: 'User Two' }),
      ]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButtons = screen.getAllByRole('button', { name: /edit role/i })
      await userEvent.click(editButtons[1]) // Click second user's button

      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 2,
          email: 'user2@test.com',
          display_name: 'User Two',
        })
      )
    })

    it('should_make_edit_buttons_keyboard_accessible', async () => {
      const mockCallback = vi.fn()
      const user = createMockUser()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([user]),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButton = screen.getByRole('button', { name: /edit role/i })
      editButton.focus()

      expect(editButton).toHaveFocus()

      await userEvent.keyboard('{Enter}')

      expect(mockCallback).toHaveBeenCalled()
    })
  })

  describe('State Management - Loading State', () => {
    it('should_display_loading_spinner_when_data_is_loading', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        isLoading: true,
        isPending: true,
        status: 'pending',
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByTestId('loading')).toBeInTheDocument()
    })

    it('should_display_loading_message_or_skeleton_when_fetching', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        isLoading: true,
        isFetching: true,
        isPending: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const loadingIndicator =
        screen.queryByText(/loading|skeleton/i) || screen.queryByTestId('loading')
      expect(loadingIndicator).toBeInTheDocument()
    })
  })

  describe('State Management - Error State', () => {
    it('should_display_error_message_when_data_fetch_fails', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        isError: true,
        error: new Error('Failed to fetch users'),
        status: 'error',
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/error|failed/i)).toBeInTheDocument()
    })

    it('should_display_specific_error_message_text', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        isError: true,
        error: new Error('Network request failed'),
        status: 'error',
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/network|failed/i)).toBeInTheDocument()
    })
  })

  describe('State Management - Empty State', () => {
    it('should_display_empty_message_when_users_array_is_empty', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([], 0, 0, 1, 50),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/no users|empty/i)).toBeInTheDocument()
    })

    it('should_not_render_table_rows_in_empty_state', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse([], 0, 0, 1, 50),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const rows = screen.queryAllByRole('row')
      // Should only have header row, no data rows
      expect(rows.length).toBeLessThanOrEqual(1)
    })
  })

  describe('Pagination Display', () => {
    it('should_display_current_page_number', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockPaginatedUsersResponse(3, 2, 3, 10),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={2} limit={3} />)

      expect(screen.getByText(/page.*2/i)).toBeInTheDocument()
    })

    it('should_display_total_pages', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockPaginatedUsersResponse(3, 1, 3, 10),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={3} />)

      // Should show something like "Page 1 of 4"
      expect(screen.getByText(/of\s+4/i)).toBeInTheDocument()
    })

    it('should_display_user_count_in_pagination_info', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockPaginatedUsersResponse(3, 1, 3, 15),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={3} />)

      expect(screen.getByText(/15\s+total|15.*users/i)).toBeInTheDocument()
    })

    it('should_display_pagination_info_on_last_page', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockPaginatedUsersResponse(1, 4, 3, 10),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={4} limit={3} />)

      expect(screen.getByText(/page.*4/i)).toBeInTheDocument()
    })
  })

  describe('Mixed User Roles Display', () => {
    it('should_display_both_admin_and_authenticated_role_badges', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockMixedRolesResponse(1, 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/admin/i)).toBeInTheDocument()
      expect(screen.getByText(/authenticated/i)).toBeInTheDocument()
    })

    it('should_display_multiple_admin_users_correctly', () => {
      const mockCallback = vi.fn()

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockMixedRolesResponse(3, 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const adminBadges = screen.getAllByText(/admin/i)
      expect(adminBadges).toHaveLength(3)
    })
  })

  describe('Last Login Display', () => {
    it('should_display_last_login_when_user_has_logged_in', () => {
      const mockCallback = vi.fn()
      const users = [createMockUser({ last_login: '2026-05-20T15:30:00Z' })]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/05\/20\/2026/)).toBeInTheDocument()
    })

    it('should_display_never_when_user_has_not_logged_in', () => {
      const mockCallback = vi.fn()
      const users = [createMockNewUser()]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByText(/never/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should_have_proper_table_aria_structure', () => {
      const mockCallback = vi.fn()
      const users = [createMockUser()]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      expect(screen.getByRole('table')).toBeInTheDocument()
      expect(screen.getAllByRole('columnheader')).toHaveLength(5) // email, role, created, last login, actions
    })

    it('should_have_semantic_button_elements_for_edit_role', () => {
      const mockCallback = vi.fn()
      const users = [createMockUser()]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButton = screen.getByRole('button', { name: /edit role/i })
      expect(editButton.tagName).toBe('BUTTON')
    })

    it('should_support_keyboard_navigation_in_table', async () => {
      const mockCallback = vi.fn()
      const users = [
        createMockUser({ id: 1, email: 'user1@test.com' }),
        createMockUser({ id: 2, email: 'user2@test.com' }),
      ]

      vi.mocked(useUsers).mockReturnValue({
        ...mockUseUsersReturn,
        data: createMockUsersResponse(users),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<UserTable onEditRole={mockCallback} page={1} limit={50} />)

      const editButtons = screen.getAllByRole('button', { name: /edit role/i })

      editButtons[0].focus()
      expect(editButtons[0]).toHaveFocus()

      await userEvent.keyboard('{Tab}')
      expect(editButtons[1]).toHaveFocus()
    })
  })
})
