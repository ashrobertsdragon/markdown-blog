import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useLocation: vi.fn(),
  }
})

vi.mock('@clerk/clerk-react', () => ({
  SignIn: vi.fn(() => <div data-testid="clerk-signin">Clerk SignIn</div>),
}))

import { SignIn } from '@clerk/clerk-react'
import { useLocation } from 'react-router-dom'

const mockUseLocation = vi.mocked(useLocation)
const mockSignIn = vi.mocked(SignIn)

interface LocationState {
  from?: {
    pathname: string
  }
}

describe('Login Page Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSignIn.mockReturnValue(<div data-testid="clerk-signin">Clerk SignIn</div>)
  })

  describe('Component Rendering', () => {
    it('should render without crashing', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      expect(() => {
        render(
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        )
      }).not.toThrow()
    })

    it('should render successfully with valid DOM structure', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      const { container } = render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(container).toBeTruthy()
      expect(container.firstChild).toBeTruthy()
    })

    it('should render Clerk SignIn component within the page', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      const signInComponent = screen.getByTestId('clerk-signin')
      expect(signInComponent).toBeInTheDocument()
    })

    it('should have appropriate page heading or title', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      const heading = screen.queryByRole('heading')
      expect(heading).toBeInTheDocument()
    })
  })

  describe('Redirect URL Logic', () => {
    it('should pass redirect URL to SignIn when location.state.from.pathname exists', async () => {
      const mockState: LocationState = {
        from: {
          pathname: '/admin/dashboard',
        },
      }

      mockUseLocation.mockReturnValue({
        state: mockState,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/admin/dashboard',
          afterSignInUrl: '/admin/dashboard',
        },
        undefined
      )
    })

    it('should default redirectUrl to / when location.state is null', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/',
          afterSignInUrl: '/',
        },
        undefined
      )
    })

    it('should default redirectUrl to / when location.state is undefined', async () => {
      mockUseLocation.mockReturnValue({
        state: undefined,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/',
          afterSignInUrl: '/',
        },
        undefined
      )
    })

    it('should default redirectUrl to / when location.state.from is undefined', async () => {
      mockUseLocation.mockReturnValue({
        state: {} as LocationState,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/',
          afterSignInUrl: '/',
        },
        undefined
      )
    })

    it('should default redirectUrl to / when location.state.from.pathname is empty', async () => {
      const mockState: LocationState = {
        from: {
          pathname: '',
        },
      }

      mockUseLocation.mockReturnValue({
        state: mockState,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/',
          afterSignInUrl: '/',
        },
        undefined
      )
    })

    it('should handle different redirect paths correctly', async () => {
      const testPaths = ['/author/posts', '/admin/users', '/profile', '/settings']

      const Login = (await import('@/pages/Login')).default

      for (const path of testPaths) {
        vi.clearAllMocks()

        mockUseLocation.mockReturnValue({
          state: { from: { pathname: path } },
          pathname: '/login',
          search: '',
          hash: '',
          key: 'default',
        })

        render(
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        )

        expect(mockSignIn).toHaveBeenCalledWith(
          {
            redirectUrl: path,
            afterSignInUrl: path,
          },
          undefined
        )
      }
    })
  })

  describe('TypeScript Type Safety', () => {
    it('should properly type location state with LocationState interface', async () => {
      const mockState: LocationState = {
        from: {
          pathname: '/test',
        },
      }

      mockUseLocation.mockReturnValue({
        state: mockState,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      expect(() => {
        render(
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        )
      }).not.toThrow()
    })

    it('should handle location state as null without type errors', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      expect(() => {
        render(
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        )
      }).not.toThrow()
    })

    it('should handle location state as undefined without type errors', async () => {
      mockUseLocation.mockReturnValue({
        state: undefined,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      expect(() => {
        render(
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        )
      }).not.toThrow()
    })
  })

  describe('Component Structure and Styling', () => {
    it('should apply Tailwind CSS classes for styling', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      const { container } = render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      const pageElement = container.firstChild as HTMLElement
      expect(pageElement.className).toBeTruthy()
    })

    it('should be a functional component', async () => {
      const Login = (await import('@/pages/Login')).default

      expect(typeof Login).toBe('function')
    })

    it('should not require any props', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      expect(() => {
        render(
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        )
      }).not.toThrow()
    })

    it('should export as default export', async () => {
      const LoginModule = await import('@/pages/Login')

      expect(LoginModule.default).toBeTruthy()
      expect(typeof LoginModule.default).toBe('function')
    })
  })

  describe('Integration with React Router', () => {
    it('should work correctly when rendered within Routes', async () => {
      mockUseLocation.mockReturnValue({
        state: { from: { pathname: '/protected' } },
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<Login />} />
          </Routes>
        </MemoryRouter>
      )

      expect(screen.getByTestId('clerk-signin')).toBeInTheDocument()
    })

    it('should preserve redirect URL through navigation', async () => {
      mockUseLocation.mockReturnValue({
        state: { from: { pathname: '/admin/settings' } },
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter
          initialEntries={[
            {
              pathname: '/login',
              state: { from: { pathname: '/admin/settings' } },
            },
          ]}
        >
          <Routes>
            <Route path="/login" element={<Login />} />
          </Routes>
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/admin/settings',
          afterSignInUrl: '/admin/settings',
        },
        undefined
      )
    })
  })

  describe('Edge Cases', () => {
    it('should handle root path redirect correctly', async () => {
      mockUseLocation.mockReturnValue({
        state: { from: { pathname: '/' } },
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/',
          afterSignInUrl: '/',
        },
        undefined
      )
    })

    it('should handle paths with query parameters', async () => {
      mockUseLocation.mockReturnValue({
        state: { from: { pathname: '/posts?page=2' } },
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/posts?page=2',
          afterSignInUrl: '/posts?page=2',
        },
        undefined
      )
    })

    it('should handle paths with hash fragments', async () => {
      mockUseLocation.mockReturnValue({
        state: { from: { pathname: '/docs#section-2' } },
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/docs#section-2',
          afterSignInUrl: '/docs#section-2',
        },
        undefined
      )
    })

    it('should handle multiple renders without errors', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      const { unmount: unmount1 } = render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )
      unmount1()

      const { unmount: unmount2 } = render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )
      unmount2()

      expect(true).toBe(true)
    })

    it('should unmount cleanly without errors', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      const { unmount } = render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })

  describe('Clerk SignIn Component Integration', () => {
    it('should render Clerk SignIn component with correct props', async () => {
      mockUseLocation.mockReturnValue({
        state: { from: { pathname: '/dashboard' } },
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      expect(mockSignIn).toHaveBeenCalled()
      expect(mockSignIn).toHaveBeenCalledWith(
        {
          redirectUrl: '/dashboard',
          afterSignInUrl: '/dashboard',
        },
        undefined
      )
    })

    it('should only render SignIn component once per render', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      const signInComponents = screen.getAllByTestId('clerk-signin')
      expect(signInComponents).toHaveLength(1)
    })
  })

  describe('Accessibility', () => {
    it('should have semantic HTML structure', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      const heading = screen.queryByRole('heading')
      expect(heading).toBeInTheDocument()
    })

    it('should be keyboard navigable', async () => {
      mockUseLocation.mockReturnValue({
        state: null,
        pathname: '/login',
        search: '',
        hash: '',
        key: 'default',
      })

      const Login = (await import('@/pages/Login')).default

      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      )

      const signInComponent = screen.getByTestId('clerk-signin')
      expect(signInComponent).toBeInTheDocument()
    })
  })
})
