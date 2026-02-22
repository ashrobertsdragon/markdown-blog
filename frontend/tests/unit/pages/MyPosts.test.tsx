import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MyPosts from '@/pages/MyPosts'
import type { ListPostsResponse } from '@/services/postsApi'

/**
 * Mock hooks from @/hooks/usePosts
 */
const mockUseMyPosts = vi.fn()
const mockMutateAsync = vi.fn()
const mockUseDeleteDraft = vi.fn()

vi.mock('@/hooks/usePosts', () => ({
  useMyPosts: (filter?: string, page?: number) => mockUseMyPosts(filter, page),
  useDeleteDraft: () => mockUseDeleteDraft(),
}))

/**
 * Mock react-router-dom navigation
 */
const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

/**
 * Test suite for MyPosts page component
 *
 * Tests comprehensive user post management including filtering, pagination,
 * and CRUD operations. Written in TDD RED phase - all tests expected to FAIL
 * until component is implemented.
 *
 * Requirements from spec task 32:
 * - Display author's posts with filters (all/drafts/published)
 * - Pagination (20 posts per page)
 * - Actions: Edit, View (published only), Delete (with confirmation)
 * - Show title, status, last_updated, slug columns
 * - Loading/error/empty states
 */
describe('MyPosts Component', () => {
  let queryClient: QueryClient

  /**
   * Helper to wrap component with required providers
   */
  function renderMyPosts() {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    )

    return render(<MyPosts />, { wrapper })
  }

  const mockPostsResponse: ListPostsResponse = {
    posts: [
      {
        id: 1,
        slug: 'first-post',
        title: 'First Post',
        author_id: 42,
        html_content: '<p>Content 1</p>',
        published: true,
        published_at: '2026-02-01T10:00:00Z',
        created_at: '2026-02-01T09:00:00Z',
        updated_at: '2026-02-01T10:00:00Z',
      },
      {
        id: 2,
        slug: 'draft-post',
        title: 'Draft Post',
        author_id: 42,
        html_content: '',
        published: false,
        published_at: null,
        created_at: '2026-02-02T11:00:00Z',
        updated_at: '2026-02-02T11:30:00Z',
      },
    ],
    total_count: 2,
    total_pages: 1,
    page: 1,
    limit: 20,
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    vi.clearAllMocks()
    mockNavigate.mockReset()

    mockUseDeleteDraft.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      error: null,
    })
  })

  /**
   * RED phase: Test loading state displays spinner
   * Expected to FAIL if loading indicator not shown during isLoading
   */
  it('renders loading state while fetching posts', () => {
    mockUseMyPosts.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText(/loading posts/i)).toBeInTheDocument()
    const loadingContainer = screen.getByRole('status')
    expect(loadingContainer).toBeInTheDocument()

    const spinner = loadingContainer.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  /**
   * RED phase: Test error state when fetch fails
   * Expected to FAIL if error Alert not displayed with error message
   */
  it('renders error state when fetch fails', () => {
    mockUseMyPosts.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to load posts'),
    })

    renderMyPosts()

    expect(screen.getByText(/error loading posts/i)).toBeInTheDocument()
    expect(screen.getByText(/failed to load posts.*please refresh/i)).toBeInTheDocument()
  })

  /**
   * RED phase: Test empty state message when no posts exist
   * Expected to FAIL if empty message not displayed when posts array is empty
   */
  it('renders empty state when no posts exist', () => {
    mockUseMyPosts.mockReturnValue({
      data: {
        posts: [],
        total_count: 0,
        total_pages: 0,
        page: 1,
        limit: 20,
      },
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText(/no posts found/i)).toBeInTheDocument()
    expect(screen.getByText(/create your first post/i)).toBeInTheDocument()
  })

  /**
   * RED phase: Test post table renders with correct columns
   * Expected to FAIL if table headers not present
   */
  it('renders post table with correct column headers', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Last Updated')).toBeInTheDocument()
    expect(screen.getByText('Slug')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
  })

  /**
   * RED phase: Test post data displays in table rows
   * Expected to FAIL if post titles not rendered
   */
  it('displays post titles in table', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText('First Post')).toBeInTheDocument()
    expect(screen.getByText('Draft Post')).toBeInTheDocument()
  })

  /**
   * RED phase: Test published status displays correctly
   * Expected to FAIL if "Published" badge not shown for published posts
   */
  it('displays Published status badge for published posts', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const publishedBadges = screen.getAllByText('Published')
    expect(publishedBadges.length).toBeGreaterThan(0)
  })

  /**
   * RED phase: Test draft status displays correctly
   * Expected to FAIL if "Draft" badge not shown for draft posts
   */
  it('displays Draft status badge for draft posts', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const draftBadges = screen.getAllByText('Draft')
    expect(draftBadges.length).toBeGreaterThan(0)
  })

  /**
   * RED phase: Test last_updated shows formatted date
   * Expected to FAIL if timestamp not formatted and displayed
   */
  it('displays formatted last updated date', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const datePattern = /\d{1,2}\/\d{1,2}\/\d{4}|\w+ \d{1,2}, \d{4}/
    const dates = screen.getAllByText(datePattern)
    expect(dates.length).toBeGreaterThan(0)
  })

  /**
   * RED phase: Test slug displays in table
   * Expected to FAIL if slug column not rendered
   */
  it('displays post slugs in table', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText('first-post')).toBeInTheDocument()
    expect(screen.getByText('draft-post')).toBeInTheDocument()
  })

  /**
   * RED phase: Test filter buttons render correctly
   * Expected to FAIL if All, Drafts, Published filter buttons not present
   */
  it('renders filter buttons (All, Drafts, Published)', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByRole('button', { name: /^all$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /drafts/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /published/i })).toBeInTheDocument()
  })

  /**
   * RED phase: Test filter state changes when button clicked
   * Expected to FAIL if useMyPosts not called with 'drafts' filter
   */
  it('updates filter when Drafts button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const draftsButton = screen.getByRole('button', { name: /drafts/i })
    fireEvent.click(draftsButton)

    expect(mockUseMyPosts).toHaveBeenCalledWith('drafts', 1)
  })

  /**
   * RED phase: Test filter updates to 'published'
   * Expected to FAIL if useMyPosts not called with 'published' filter
   */
  it('updates filter when Published button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const publishedButton = screen.getByRole('button', { name: /published/i })
    fireEvent.click(publishedButton)

    expect(mockUseMyPosts).toHaveBeenCalledWith('published', 1)
  })

  /**
   * RED phase: Test filter resets to undefined when All clicked
   * Expected to FAIL if useMyPosts not called with undefined filter
   */
  it('clears filter when All button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const draftsButton = screen.getByRole('button', { name: /drafts/i })
    fireEvent.click(draftsButton)

    const allButton = screen.getByRole('button', { name: /^all$/i })
    fireEvent.click(allButton)

    expect(mockUseMyPosts).toHaveBeenCalledWith('all', 1)
  })

  /**
   * RED phase: Test pagination controls render when multiple pages
   * Expected to FAIL if pagination not shown when total_pages > 1
   */
  it('renders pagination controls when multiple pages exist', () => {
    mockUseMyPosts.mockReturnValue({
      data: {
        ...mockPostsResponse,
        total_pages: 5,
        total_count: 100,
      },
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText(/page 1 of 5/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
  })

  /**
   * RED phase: Test pagination hidden when only one page
   * Expected to FAIL if pagination controls shown when total_pages <= 1
   */
  it('hides pagination controls when only one page exists', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.queryByText(/page 1 of 1/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument()
  })

  /**
   * RED phase: Test next page navigation
   * Expected to FAIL if useMyPosts not called with page 2
   */
  it('navigates to next page when next button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: {
        ...mockPostsResponse,
        total_pages: 3,
        page: 1,
      },
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    expect(mockUseMyPosts).toHaveBeenCalledWith('all', 2)
  })

  /**
   * RED phase: Test previous page navigation
   * Expected to FAIL if useMyPosts not called with page 1 when on page 2
   */
  it('navigates to previous page when previous button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: {
        ...mockPostsResponse,
        total_pages: 3,
        page: 2,
      },
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const prevButton = screen.getByRole('button', { name: /previous/i })
    fireEvent.click(prevButton)

    expect(mockUseMyPosts).toHaveBeenCalledWith('all', 1)
  })

  /**
   * RED phase: Test page info displays correctly
   * Expected to FAIL if page indicator not showing correct page/total
   */
  it('displays correct page info text', () => {
    mockUseMyPosts.mockReturnValue({
      data: {
        ...mockPostsResponse,
        total_pages: 5,
        page: 3,
      },
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    expect(screen.getByText(/page 3 of 5/i)).toBeInTheDocument()
  })

  /**
   * RED phase: Test Edit button navigates to /edit/:slug
   * Expected to FAIL if navigate not called with correct path
   */
  it('navigates to editor when Edit button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const editButtons = screen.getAllByRole('button', { name: /edit/i })
    fireEvent.click(editButtons[0])

    expect(mockNavigate).toHaveBeenCalledWith('/edit/first-post')
  })

  /**
   * RED phase: Test View button navigates to /posts/:slug for published posts
   * Expected to FAIL if navigate not called for published post
   */
  it('navigates to post view when View button clicked on published post', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const viewButtons = screen.getAllByRole('button', { name: /view/i })
    const publishedPostViewButton = viewButtons.find(btn => !btn.hasAttribute('disabled'))

    if (publishedPostViewButton) {
      fireEvent.click(publishedPostViewButton)
      expect(mockNavigate).toHaveBeenCalledWith('/posts/first-post')
    }
  })

  /**
   * RED phase: Test View button disabled for draft posts
   * Expected to FAIL if View button not disabled for drafts
   */
  it('disables View button for draft posts', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const viewButtons = screen.getAllByRole('button', { name: /view/i })
    const draftViewButton = viewButtons.find(btn => btn.hasAttribute('disabled'))

    expect(draftViewButton).toBeDefined()
    expect(draftViewButton).toBeDisabled()
  })

  /**
   * RED phase: Test Delete button opens confirmation dialog
   * Expected to FAIL if AlertDialog not shown when Delete clicked
   */
  it('opens confirmation dialog when Delete button clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    fireEvent.click(deleteButtons[0])

    expect(screen.getByText(/are you sure you want to delete/i)).toBeInTheDocument()
    expect(screen.getByText(/this action cannot be undone/i)).toBeInTheDocument()
  })

  /**
   * RED phase: Test delete confirmation calls mutation
   * Expected to FAIL if mutateAsync not called when confirm clicked
   */
  it('calls useDeleteDraft when deletion confirmed', async () => {
    mockMutateAsync.mockResolvedValue(undefined)
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    fireEvent.click(deleteButtons[0])

    const confirmButton = await screen.findByRole('button', {
      name: /confirm|delete/i,
      hidden: false,
    })
    fireEvent.click(confirmButton)

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith('first-post')
    })
  })

  /**
   * RED phase: Test cancel button closes delete dialog
   * Expected to FAIL if dialog not closed when cancel clicked
   */
  it('closes delete dialog when cancel clicked', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    fireEvent.click(deleteButtons[0])

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelButton)

    expect(screen.queryByText(/are you sure you want to delete/i)).not.toBeInTheDocument()
  })

  /**
   * RED phase: Test delete error displays alert
   * Expected to FAIL if error Alert not shown when mutation fails
   */
  it('shows error Alert when delete fails', () => {
    const deleteError = new Error('Delete failed: network timeout')

    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    mockUseDeleteDraft.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      error: deleteError,
    })

    renderMyPosts()

    expect(screen.getByText(/failed to delete post.*please try again/i)).toBeInTheDocument()
  })

  /**
   * RED phase: Test active filter button has visual indicator
   * Expected to FAIL if active filter not styled differently
   * Also verifies ARIA state via aria-pressed for accessibility
   */
  it('highlights active filter button', () => {
    mockUseMyPosts.mockReturnValue({
      data: mockPostsResponse,
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const draftsButton = screen.getByRole('button', { name: /drafts/i })
    fireEvent.click(draftsButton)

    expect(draftsButton).toHaveClass(/bg-primary|bg-blue|variant-default/)
    expect(draftsButton).toHaveAttribute('aria-pressed', 'true')
  })

  /**
   * RED phase: Test filter persists across pagination
   * Expected to FAIL if filter not maintained when changing pages
   */
  it('maintains filter when navigating between pages', () => {
    mockUseMyPosts.mockReturnValue({
      data: {
        ...mockPostsResponse,
        total_pages: 3,
        page: 1,
      },
      isLoading: false,
      error: null,
    })

    renderMyPosts()

    const draftsButton = screen.getByRole('button', { name: /drafts/i })
    fireEvent.click(draftsButton)

    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    expect(mockUseMyPosts).toHaveBeenCalledWith('drafts', 2)
  })
})
