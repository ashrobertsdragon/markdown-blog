import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ActivityComment, ActivityPost, UserActivity } from '@/services/admin/adminApi'
import { createMockUser } from '../../../fixtures/users.fixtures'

const mockUseUserActivity = vi.hoisted(() => vi.fn())

vi.mock('@/hooks/admin/useUsers', async importOriginal => {
  const actual = await importOriginal<typeof import('@/hooks/admin/useUsers')>()
  return {
    ...actual,
    useUserActivity: mockUseUserActivity,
  }
})

vi.mock('react-router-dom', async importOriginal => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useParams: vi.fn(() => ({ userId: '42' })),
    useLocation: vi.fn(() => ({ state: { user: createMockUser({ id: 42 }) } })),
  }
})

import UserProfilePage from '@/pages/admin/UserProfilePage'

const createMockActivityPost = (overrides: Partial<ActivityPost> = {}): ActivityPost => ({
  id: 1,
  slug: 'my-post',
  title: 'My Post',
  published: true,
  created_at: '2024-01-10T00:00:00Z',
  ...overrides,
})

const createMockActivityComment = (overrides: Partial<ActivityComment> = {}): ActivityComment => ({
  id: 1,
  post_slug: 'some-post',
  text: 'Great article!',
  created_at: '2024-01-12T00:00:00Z',
  ...overrides,
})

const createMockUserActivity = (overrides: Partial<UserActivity> = {}): UserActivity => ({
  user_id: 42,
  last_login: '2024-01-15T10:00:00Z',
  post_count: 5,
  comment_count: 12,
  recent_posts: [createMockActivityPost()],
  recent_comments: [createMockActivityComment()],
  ...overrides,
})

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithProviders = (ui: React.ReactElement) =>
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )

/**
 * Tests for the UserProfilePage admin component.
 *
 * Covers page heading, loading and error states, user metadata display from
 * location state, activity data from useUserActivity (post/comment counts,
 * last login, recent posts and comments), navigation elements, and graceful
 * handling of missing location state.
 */
describe('UserProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Render', () => {
    it('renders a page heading', () => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity(),
        isLoading: false,
        isError: false,
        error: null,
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    })
  })

  describe('Loading state', () => {
    it('shows a status element while activity is loading', () => {
      mockUseUserActivity.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('does not show activity data while loading', () => {
      mockUseUserActivity.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.queryByText(/post_count|5 posts/i)).not.toBeInTheDocument()
    })
  })

  describe('Error state', () => {
    it('shows an error message when activity fetch fails', () => {
      mockUseUserActivity.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('Failed to load activity'),
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/failed to load activity/i)).toBeInTheDocument()
    })

    it('does not show loading indicator when in error state', () => {
      mockUseUserActivity.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('Network error'),
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })
  })

  describe('User details from location state', () => {
    beforeEach(() => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity(),
        isLoading: false,
        isError: false,
        error: null,
      })
    })

    it('displays the user email', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText('user@example.com')).toBeInTheDocument()
    })

    it('displays the user role', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/authenticated/i)).toBeInTheDocument()
    })

    it('displays admin role when user is an admin', async () => {
      const { useLocation } = await import('react-router-dom')
      vi.mocked(useLocation).mockReturnValue({
        state: { user: createMockUser({ id: 42, role: 'admin' }) },
        pathname: '',
        search: '',
        hash: '',
        key: 'default',
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/admin/i)).toBeInTheDocument()
    })
  })

  describe('Activity data', () => {
    beforeEach(() => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity(),
        isLoading: false,
        isError: false,
        error: null,
      })
    })

    it('displays the post count', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('displays the comment count', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/12/)).toBeInTheDocument()
    })

    it('displays the last login timestamp', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/2024/)).toBeInTheDocument()
    })

    it('shows "Never" when last_login is null', () => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity({ last_login: null }),
        isLoading: false,
        isError: false,
        error: null,
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/never/i)).toBeInTheDocument()
    })
  })

  describe('Recent posts', () => {
    beforeEach(() => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity({
          recent_posts: [
            createMockActivityPost({ id: 1, title: 'First Article' }),
            createMockActivityPost({ id: 2, title: 'Second Article', slug: 'second-article' }),
          ],
        }),
        isLoading: false,
        isError: false,
        error: null,
      })
    })

    it('displays the title of each recent post', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText('First Article')).toBeInTheDocument()
      expect(screen.getByText('Second Article')).toBeInTheDocument()
    })
  })

  describe('Recent comments', () => {
    beforeEach(() => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity({
          recent_comments: [
            createMockActivityComment({ id: 1, text: 'Great article!' }),
            createMockActivityComment({ id: 2, text: 'Very informative post.' }),
          ],
        }),
        isLoading: false,
        isError: false,
        error: null,
      })
    })

    it('displays text of each recent comment', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/great article!/i)).toBeInTheDocument()
      expect(screen.getByText(/very informative post\./i)).toBeInTheDocument()
    })
  })

  describe('Navigation elements', () => {
    beforeEach(() => {
      mockUseUserActivity.mockReturnValue({
        data: createMockUserActivity(),
        isLoading: false,
        isError: false,
        error: null,
      })
    })

    it('renders a "View Posts" navigation element', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByRole('link', { name: /view posts/i })).toBeInTheDocument()
    })

    it('renders a "View Comments" navigation element', () => {
      renderWithProviders(<UserProfilePage />)

      expect(screen.getByRole('link', { name: /view comments/i })).toBeInTheDocument()
    })
  })

  describe('Missing location state', () => {
    it('shows a "not found" message when location state has no user', async () => {
      const { useLocation } = await import('react-router-dom')
      vi.mocked(useLocation).mockReturnValue({
        state: null,
        pathname: '',
        search: '',
        hash: '',
        key: 'default',
      })

      mockUseUserActivity.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: false,
        error: null,
      })

      renderWithProviders(<UserProfilePage />)

      expect(screen.getByText(/not found/i)).toBeInTheDocument()
    })

    it('does not crash when location state is an empty object', async () => {
      const { useLocation } = await import('react-router-dom')
      vi.mocked(useLocation).mockReturnValue({
        state: {},
        pathname: '',
        search: '',
        hash: '',
        key: 'default',
      })

      mockUseUserActivity.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: false,
        error: null,
      })

      expect(() => renderWithProviders(<UserProfilePage />)).not.toThrow()
    })
  })
})
