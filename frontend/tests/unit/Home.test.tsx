import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Home from '@/pages/Home'
import { postsApi } from '@/services/postsApi'

vi.mock('@/services/postsApi', () => ({
  postsApi: {
    listPublicPosts: vi.fn(),
  },
}))

describe('Home', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderWithRouter = (ui: React.ReactElement) => {
    return render(<BrowserRouter>{ui}</BrowserRouter>)
  }

  it('displays loading state initially', async () => {
    vi.mocked(postsApi.listPublicPosts).mockImplementation(() => new Promise(() => {}))
    renderWithRouter(<Home />)
    expect(screen.getByText(/loading posts/i)).toBeInTheDocument()
  })

  it('displays posts on successful fetch', async () => {
    const mockPosts = {
      posts: [
        {
          id: 1,
          slug: 'test-post',
          title: 'Test Post',
          html_content: '<p>Content</p>',
          author: { id: 1, username: 'author', display_name: 'Author', role: 'author' },
          published_at: '2026-06-18T10:00:00Z',
        },
      ],
      total_count: 1,
      total_pages: 1,
      page: 1,
      limit: 20,
    }
    vi.mocked(postsApi.listPublicPosts).mockResolvedValue(mockPosts as never)

    renderWithRouter(<Home />)

    await waitFor(() => {
      expect(screen.queryByText(/loading posts/i)).not.toBeInTheDocument()
    })

    expect(screen.getByText('Test Post')).toBeInTheDocument()
  })

  it('displays error message on fetch failure', async () => {
    vi.mocked(postsApi.listPublicPosts).mockRejectedValue(new Error('API error'))

    renderWithRouter(<Home />)

    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument()
      expect(screen.getByText(/API error/)).toBeInTheDocument()
    })
  })

  it('displays empty state when no posts are available', async () => {
    const mockEmpty = { posts: [], total_count: 0, total_pages: 0, page: 1, limit: 20 }
    vi.mocked(postsApi.listPublicPosts).mockResolvedValue(mockEmpty as never)

    renderWithRouter(<Home />)

    await waitFor(() => {
      expect(screen.getByText(/No posts yet/i)).toBeInTheDocument()
    })
  })
})
