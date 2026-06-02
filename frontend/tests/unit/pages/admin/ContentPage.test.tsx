import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/components/admin/PostsTable', () => ({
  PostsTable: vi.fn(() => <div data-testid="posts-table">posts table</div>),
}))

vi.mock('@/components/admin/CommentsTable', () => ({
  CommentsTable: vi.fn(() => <div data-testid="comments-table">comments table</div>),
}))

import ContentPage from '@/pages/admin/ContentPage'

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderComponent = () =>
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <ContentPage />
    </QueryClientProvider>
  )

/**
 * Tests for the ContentPage admin component.
 *
 * Covers heading and tab button render, default active tab state,
 * and tab switching behaviour including aria-selected updates
 * and child table mount/unmount.
 */
describe('ContentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Render', () => {
    it('renders a page heading (h1)', () => {
      renderComponent()

      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    })

    it('renders a "Posts" tab button', () => {
      renderComponent()

      expect(screen.getByRole('tab', { name: /posts/i })).toBeInTheDocument()
    })

    it('renders a "Comments" tab button', () => {
      renderComponent()

      expect(screen.getByRole('tab', { name: /comments/i })).toBeInTheDocument()
    })
  })

  describe('Default state (Posts tab active)', () => {
    it('renders PostsTable by default', () => {
      renderComponent()

      expect(screen.getByTestId('posts-table')).toBeInTheDocument()
    })

    it('does not render CommentsTable by default', () => {
      renderComponent()

      expect(screen.queryByTestId('comments-table')).not.toBeInTheDocument()
    })

    it('"Posts" tab button has aria-selected="true" by default', () => {
      renderComponent()

      expect(screen.getByRole('tab', { name: /posts/i })).toHaveAttribute('aria-selected', 'true')
    })

    it('"Comments" tab button has aria-selected="false" by default', () => {
      renderComponent()

      expect(screen.getByRole('tab', { name: /comments/i })).toHaveAttribute(
        'aria-selected',
        'false'
      )
    })
  })

  describe('Tab switching - Comments', () => {
    it('renders CommentsTable after clicking "Comments" tab', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('tab', { name: /comments/i }))

      expect(screen.getByTestId('comments-table')).toBeInTheDocument()
    })

    it('does not render PostsTable after clicking "Comments" tab', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('tab', { name: /comments/i }))

      expect(screen.queryByTestId('posts-table')).not.toBeInTheDocument()
    })

    it('"Comments" tab button has aria-selected="true" after click', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('tab', { name: /comments/i }))

      expect(screen.getByRole('tab', { name: /comments/i })).toHaveAttribute(
        'aria-selected',
        'true'
      )
    })

    it('"Posts" tab button has aria-selected="false" after clicking "Comments"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('tab', { name: /comments/i }))

      expect(screen.getByRole('tab', { name: /posts/i })).toHaveAttribute('aria-selected', 'false')
    })
  })

  describe('Tab switching - back to Posts', () => {
    it('renders PostsTable after clicking "Posts" tab following "Comments"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('tab', { name: /comments/i }))
      await interaction.click(screen.getByRole('tab', { name: /posts/i }))

      expect(screen.getByTestId('posts-table')).toBeInTheDocument()
    })
  })
})
