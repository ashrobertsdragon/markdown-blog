import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Layout from '@/components/common/Layout'

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
  useAuth: vi.fn(() => ({
    isSignedIn: false,
    isLoaded: true,
    role: 'authenticated',
    user: null,
    getToken: async () => null,
  })),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('Layout', () => {
  it('should render the header', () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<div>Page content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByRole('banner')).toBeInTheDocument()
  })

  it('should render outlet content inside main', () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<div data-testid="page-content">Page content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    const main = screen.getByRole('main')
    expect(main).toBeInTheDocument()
    expect(main).toContainElement(screen.getByTestId('page-content'))
  })

  it('should render header above main content', () => {
    const { container } = render(
      <MemoryRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<div>Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    const children = Array.from(container.children)
    const headerIndex = children.findIndex(el => el.tagName === 'HEADER')
    const mainIndex = children.findIndex(el => el.tagName === 'MAIN')
    expect(headerIndex).toBeLessThan(mainIndex)
  })
})
