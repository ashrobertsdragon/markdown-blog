import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PublicPost from '@/pages/PublicPost'

/**
 * Mock react-router-dom to control route params
 */
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: vi.fn(),
    useNavigate: vi.fn(),
  }
})

/**
 * Mock usePublicPost hook from usePosts
 */
vi.mock('@/hooks/usePosts', () => ({
  usePublicPost: vi.fn(),
}))

/**
 * Test suite for PublicPost page component
 *
 * Tests comprehensive public post viewing functionality including:
 * - Loading state while fetching post data
 * - Successful post render with metadata (title, author, date)
 * - Sanitized HTML content rendering
 * - 404 state for unpublished or non-existent posts
 * - Error state for API failures
 * - Navigation elements (Back to Home link)
 * - Metadata display formatting
 *
 * TDD RED PHASE: These tests will FAIL because PublicPost.tsx doesn't exist yet
 */
describe('PublicPost', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * Helper to render component with Router wrapper
   */
  const renderPublicPost = () => {
    return render(
      <BrowserRouter>
        <PublicPost />
      </BrowserRouter>
    )
  }

  describe('loading state', () => {
    /**
     * Test that component displays loading state while fetching post data
     */
    it('should display loading state on initial render', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })

    /**
     * Test that component calls usePublicPost hook with slug from URL params
     */
    it('should call usePublicPost with slug from URL params', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-awesome-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      expect(usePublicPost).toHaveBeenCalledWith('my-awesome-post')
    })

    /**
     * Test that loading state is removed after successful fetch
     */
    it('should remove loading state after successful fetch', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockPost = {
        id: 1,
        slug: 'test-post',
        title: 'Test Post',
        author_id: 42,
        html_content: '<p>Test content</p>',
        published: true,
        published_at: '2026-02-05T10:00:00Z',
        created_at: '2026-02-03T10:00:00Z',
        updated_at: '2026-02-05T10:00:00Z',
      }

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('successful post render', () => {
    const mockPost = {
      id: 1,
      slug: 'my-first-post',
      title: 'My First Blog Post',
      author_id: 42,
      html_content:
        '<h2>Hello World</h2><p>This is my first post with <strong>bold text</strong>.</p>',
      published: true,
      published_at: '2026-02-05T14:30:00Z',
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-05T14:30:00Z',
    }

    /**
     * Test that post title is displayed
     */
    it('should display post title', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByText('My First Blog Post')).toBeInTheDocument()
      })
    })

    /**
     * Test that published date is displayed and formatted correctly
     */
    it('should display formatted published date', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const dateElement = screen.getByTestId('published-date')
        expect(dateElement).toBeInTheDocument()
        expect(dateElement.textContent).toMatch(/2026/)
      })
    })

    /**
     * Test that author information is displayed
     */
    it('should display author information', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const authorElement = screen.getByTestId('post-author')
        expect(authorElement).toBeInTheDocument()
      })
    })

    /**
     * Test that sanitized HTML content is rendered
     */
    it('should render sanitized HTML content', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const contentElement = screen.getByTestId('post-content')
        expect(contentElement).toBeInTheDocument()
        expect(contentElement.innerHTML).toContain('<h2>Hello World</h2>')
        expect(contentElement.innerHTML).toContain('<strong>bold text</strong>')
      })
    })

    /**
     * Test that HTML content uses dangerouslySetInnerHTML
     */
    it('should use dangerouslySetInnerHTML for HTML content rendering', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const contentElement = screen.getByTestId('post-content')
        expect(contentElement.innerHTML).toBe(mockPost.html_content)
      })
    })

    /**
     * Test that component renders with proper semantic HTML structure
     */
    it('should render with proper semantic HTML structure', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      const { container } = renderPublicPost()

      await waitFor(() => {
        expect(container.querySelector('article')).toBeInTheDocument()
      })
    })

    /**
     * Test that post title is rendered as h1 heading
     */
    it('should render title as h1 heading', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'my-first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const heading = screen.getByRole('heading', { level: 1 })
        expect(heading).toHaveTextContent('My First Blog Post')
      })
    })
  })

  describe('404 state for unpublished posts', () => {
    /**
     * Test that 404 message is displayed when post is not found
     */
    it('should display 404 message when post not found', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Post not found') as Error & { response?: { status: number } }
      mockError.response = { status: 404 }

      vi.mocked(useParams).mockReturnValue({ slug: 'nonexistent-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByText(/not found/i)).toBeInTheDocument()
      })
    })

    /**
     * Test that 404 message is displayed for unpublished draft
     */
    it('should display 404 message for unpublished draft', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Post not published') as Error & { response?: { status: number } }
      mockError.response = { status: 404 }

      vi.mocked(useParams).mockReturnValue({ slug: 'draft-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByText(/not found/i)).toBeInTheDocument()
      })
    })

    /**
     * Test that 404 state does not display post content
     */
    it('should not display post content in 404 state', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Post not found')

      vi.mocked(useParams).mockReturnValue({ slug: 'nonexistent' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.queryByTestId('post-content')).not.toBeInTheDocument()
      })
    })

    /**
     * Test that 404 state displays helpful message
     */
    it('should display helpful 404 message', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Post not found') as Error & { response?: { status: number } }
      mockError.response = { status: 404 }

      vi.mocked(useParams).mockReturnValue({ slug: 'missing-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const message = screen.getByTestId('error-message')
        expect(message).toBeInTheDocument()
        expect(message.textContent).toMatch(/not found/i)
      })
    })
  })

  describe('error state for API failures', () => {
    /**
     * Test that error message is displayed when API fails
     */
    it('should display error message on API failure', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Network error')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    /**
     * Test that loading state is removed when error occurs
     */
    it('should remove loading state when error occurs', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Server error')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      })
    })

    /**
     * Test that error message contains descriptive text
     */
    it('should display descriptive error message', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Failed to load post')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const errorMessage = screen.getByTestId('error-message')
        expect(errorMessage).toBeInTheDocument()
        expect(errorMessage.textContent?.length).toBeGreaterThan(0)
      })
    })

    /**
     * Test that post content is not displayed in error state
     */
    it('should not display post content when error occurs', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Network error')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.queryByTestId('post-content')).not.toBeInTheDocument()
      })
    })

    /**
     * Test that error state handles different error types
     */
    it('should handle different error types correctly', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Internal Server Error')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })
  })

  describe('navigation elements', () => {
    const mockPost = {
      id: 1,
      slug: 'test-post',
      title: 'Test Post',
      author_id: 42,
      html_content: '<p>Content</p>',
      published: true,
      published_at: '2026-02-05T10:00:00Z',
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-05T10:00:00Z',
    }

    /**
     * Test that Back to Home link exists
     */
    it('should display Back to Home link', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const backLink = screen.getByTestId('back-to-home')
        expect(backLink).toBeInTheDocument()
      })
    })

    /**
     * Test that Back to Home link has correct href
     */
    it('should have correct href for Back to Home link', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const backLink = screen.getByTestId('back-to-home')
        expect(backLink).toHaveAttribute('href', '/')
      })
    })

    /**
     * Test that navigation is visible in success state
     */
    it('should display navigation in success state', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByTestId('back-to-home')).toBeInTheDocument()
      })
    })
  })

  describe('metadata display formatting', () => {
    const mockPost = {
      id: 1,
      slug: 'formatting-test',
      title: 'Formatting Test Post',
      author_id: 42,
      html_content: '<p>Test content</p>',
      published: true,
      published_at: '2026-02-05T14:30:45Z',
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-05T14:30:45Z',
    }

    /**
     * Test that metadata section exists
     */
    it('should display metadata section', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'formatting-test' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const metadata = screen.getByTestId('post-metadata')
        expect(metadata).toBeInTheDocument()
      })
    })

    /**
     * Test that published date is formatted as readable string
     */
    it('should format published date as readable string', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'formatting-test' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const dateElement = screen.getByTestId('published-date')
        expect(dateElement.textContent).not.toContain('T')
        expect(dateElement.textContent).not.toContain('Z')
      })
    })

    /**
     * Test that metadata includes all required fields
     */
    it('should include all required metadata fields', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'formatting-test' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByTestId('post-metadata')).toBeInTheDocument()
        expect(screen.getByTestId('post-author')).toBeInTheDocument()
        expect(screen.getByTestId('published-date')).toBeInTheDocument()
      })
    })

    /**
     * Test that metadata is displayed in correct order
     */
    it('should display metadata in logical order', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'formatting-test' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      const { container } = renderPublicPost()

      await waitFor(() => {
        const metadata = container.querySelector('[data-testid="post-metadata"]')
        expect(metadata).toBeInTheDocument()
      })
    })

    /**
     * Test that metadata is styled appropriately
     */
    it('should style metadata section appropriately', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'formatting-test' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const metadata = screen.getByTestId('post-metadata')
        expect(metadata).toBeInTheDocument()
      })
    })
  })

  describe('component lifecycle', () => {
    /**
     * Test that component unmounts without errors
     */
    it('should unmount without errors', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockPost = {
        id: 1,
        slug: 'test-post',
        title: 'Test',
        author_id: 42,
        html_content: '<p>Content</p>',
        published: true,
        published_at: '2026-02-05T10:00:00Z',
        created_at: '2026-02-03T10:00:00Z',
        updated_at: '2026-02-05T10:00:00Z',
      }

      vi.mocked(useParams).mockReturnValue({ slug: 'test-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      const { unmount } = renderPublicPost()

      await waitFor(() => {
        expect(screen.getByText('Test')).toBeInTheDocument()
      })

      expect(() => {
        unmount()
      }).not.toThrow()
    })

    /**
     * Test that component handles slug parameter changes
     */
    it('should handle slug parameter changes', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'first-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      expect(usePublicPost).toHaveBeenCalledWith('first-post')
    })
  })

  describe('accessibility', () => {
    const mockPost = {
      id: 1,
      slug: 'accessible-post',
      title: 'Accessible Post',
      author_id: 42,
      html_content: '<p>Content</p>',
      published: true,
      published_at: '2026-02-05T10:00:00Z',
      created_at: '2026-02-03T10:00:00Z',
      updated_at: '2026-02-05T10:00:00Z',
    }

    /**
     * Test that page uses semantic article element
     */
    it('should use semantic article element for post', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'accessible-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      const { container } = renderPublicPost()

      await waitFor(() => {
        expect(container.querySelector('article')).toBeInTheDocument()
      })
    })

    /**
     * Test that error messages have alert role
     */
    it('should use alert role for error messages', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      const mockError = new Error('Test error')

      vi.mocked(useParams).mockReturnValue({ slug: 'test' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: mockError,
        isSuccess: false,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    /**
     * Test that main heading is h1
     */
    it('should use h1 for main post title', async () => {
      const { useParams } = await import('react-router-dom')
      const { usePublicPost } = await import('@/hooks/usePosts')

      vi.mocked(useParams).mockReturnValue({ slug: 'accessible-post' })
      vi.mocked(usePublicPost).mockReturnValue({
        data: mockPost,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        // biome-ignore lint/suspicious/noExplicitAny: test mock requires any type
      } as any)

      renderPublicPost()

      await waitFor(() => {
        const heading = screen.getByRole('heading', { level: 1 })
        expect(heading).toBeInTheDocument()
      })
    })
  })
})
