import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Header from '@/components/common/Header'
import { AuthProvider } from '@/context/AuthContext'

vi.mock('@clerk/clerk-react', () => ({
  UserButton: () => (
    <button type="button" data-testid="clerk-user-button">
      Account
    </button>
  ),
  useAuth: vi.fn(),
  useUser: vi.fn(() => ({ user: null, isLoaded: true, isSignedIn: false })),
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const renderHeader = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <Header />
      </AuthProvider>
    </MemoryRouter>
  )

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('site identity', () => {
    it('should render the site name as a link to home', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: false,
        isLoaded: true,
        role: 'authenticated',
        user: null,
        getToken: async () => null,
      })

      renderHeader()

      const siteLink = screen.getByRole('link', { name: /blog platform/i })
      expect(siteLink).toBeInTheDocument()
      expect(siteLink).toHaveAttribute('href', '/')
    })

    it('should always show the Home nav link', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: false,
        isLoaded: true,
        role: 'authenticated',
        user: null,
        getToken: async () => null,
      })

      renderHeader()

      expect(screen.getByRole('link', { name: /^home$/i })).toBeInTheDocument()
    })
  })

  describe('unauthenticated state', () => {
    it('should show sign in link when not signed in', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: false,
        isLoaded: true,
        role: 'authenticated',
        user: null,
        getToken: async () => null,
      })

      renderHeader()

      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
      expect(screen.queryByTestId('clerk-user-button')).not.toBeInTheDocument()
    })

    it('should not show author links when not signed in', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: false,
        isLoaded: true,
        role: 'authenticated',
        user: null,
        getToken: async () => null,
      })

      renderHeader()

      expect(screen.queryByRole('link', { name: /my posts/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /new post/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /^admin$/i })).not.toBeInTheDocument()
    })
  })

  describe('author role', () => {
    it('should show My Posts and New Post for authors', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: true,
        isLoaded: true,
        role: 'author',
        user: { id: 'user-1' } as never,
        getToken: async () => 'token',
      })

      renderHeader()

      expect(screen.getByRole('link', { name: /my posts/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /new post/i })).toBeInTheDocument()
    })

    it('should not show Admin link for authors', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: true,
        isLoaded: true,
        role: 'author',
        user: { id: 'user-1' } as never,
        getToken: async () => 'token',
      })

      renderHeader()

      expect(screen.queryByRole('link', { name: /^admin$/i })).not.toBeInTheDocument()
    })

    it('should show user button instead of sign in link for authors', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: true,
        isLoaded: true,
        role: 'author',
        user: { id: 'user-1' } as never,
        getToken: async () => 'token',
      })

      renderHeader()

      expect(screen.getByTestId('clerk-user-button')).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /sign in/i })).not.toBeInTheDocument()
    })
  })

  describe('admin role', () => {
    it('should show My Posts, New Post, and Admin for admins', async () => {
      const { useAuth } = await import('@/context/AuthContext')
      vi.mocked(useAuth).mockReturnValue({
        isSignedIn: true,
        isLoaded: true,
        role: 'admin',
        user: { id: 'admin-1' } as never,
        getToken: async () => 'token',
      })

      renderHeader()

      expect(screen.getByRole('link', { name: /my posts/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /new post/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /^admin$/i })).toBeInTheDocument()
    })
  })
})
