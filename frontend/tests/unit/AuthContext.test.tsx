import type { UserResource } from '@clerk/shared/types'
import { render, renderHook, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '../../src/context/AuthContext'

vi.mock('@clerk/clerk-react', () => ({
  useUser: vi.fn(),
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-token'),
  })),
}))

import { useUser } from '@clerk/clerk-react'

const mockUseUser = vi.mocked(useUser)

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render children without errors', () => {
      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: true,
        isSignedIn: false,
      })

      render(
        <AuthProvider>
          <div>Test Child</div>
        </AuthProvider>
      )

      expect(screen.getByText('Test Child')).toBeInTheDocument()
    })

    it('should render multiple children correctly', () => {
      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: true,
        isSignedIn: false,
      })

      render(
        <AuthProvider>
          <div>First Child</div>
          <div>Second Child</div>
        </AuthProvider>
      )

      expect(screen.getByText('First Child')).toBeInTheDocument()
      expect(screen.getByText('Second Child')).toBeInTheDocument()
    })
  })

  describe('Context Value Provision', () => {
    it('should provide all five context properties', () => {
      const mockUser = {
        id: 'user_123',
        firstName: 'John',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const TestComponent = () => {
        const context = useAuth()
        return (
          <div>
            <div data-testid="user">{context.user?.id}</div>
            <div data-testid="isLoaded">{String(context.isLoaded)}</div>
            <div data-testid="isSignedIn">{String(context.isSignedIn)}</div>
            <div data-testid="role">{context.role}</div>
            <div data-testid="hasGetToken">{String(typeof context.getToken === 'function')}</div>
          </div>
        )
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('user')).toHaveTextContent('user_123')
      expect(screen.getByTestId('isLoaded')).toHaveTextContent('true')
      expect(screen.getByTestId('isSignedIn')).toHaveTextContent('true')
      expect(screen.getByTestId('role')).toHaveTextContent('author')
      expect(screen.getByTestId('hasGetToken')).toHaveTextContent('true')
    })

    it('should provide getToken function from Clerk', async () => {
      const mockUser = {
        id: 'user_123',
        firstName: 'John',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      expect(result.current.getToken).toBeDefined()
      expect(typeof result.current.getToken).toBe('function')

      const token = await result.current.getToken()
      expect(token).toBe('mock-token')
    })
  })

  describe('Role Extraction', () => {
    it('should default role to "authenticated" when user is null', () => {
      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: true,
        isSignedIn: false,
      })

      const TestComponent = () => {
        const { role } = useAuth()
        return <div data-testid="role">{role}</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('role')).toHaveTextContent('authenticated')
    })

    it('should default role to "authenticated" when publicMetadata is missing', () => {
      const mockUser = {
        id: 'user_123',
        firstName: 'John',
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const TestComponent = () => {
        const { role } = useAuth()
        return <div data-testid="role">{role}</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('role')).toHaveTextContent('authenticated')
    })

    it('should default role to "authenticated" when publicMetadata.role is undefined', () => {
      const mockUser = {
        id: 'user_123',
        firstName: 'John',
        publicMetadata: {},
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const TestComponent = () => {
        const { role } = useAuth()
        return <div data-testid="role">{role}</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('role')).toHaveTextContent('authenticated')
    })

    it('should extract role "author" from user.publicMetadata.role', () => {
      const mockUser = {
        id: 'user_123',
        firstName: 'John',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const TestComponent = () => {
        const { role } = useAuth()
        return <div data-testid="role">{role}</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('role')).toHaveTextContent('author')
    })

    it('should extract role "admin" from user.publicMetadata.role', () => {
      const mockUser = {
        id: 'user_123',
        firstName: 'Admin',
        publicMetadata: { role: 'admin' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const TestComponent = () => {
        const { role } = useAuth()
        return <div data-testid="role">{role}</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('role')).toHaveTextContent('admin')
    })
  })
})

describe('useAuth Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Hook Behavior', () => {
    it('should return context value when used inside AuthProvider', () => {
      const mockUser = {
        id: 'user_456',
        firstName: 'Jane',
        publicMetadata: { role: 'admin' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      expect(result.current.user).toBe(mockUser)
      expect(result.current.isLoaded).toBe(true)
      expect(result.current.isSignedIn).toBe(true)
      expect(result.current.role).toBe('admin')
    })

    it('should throw error when used outside AuthProvider', () => {
      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: true,
        isSignedIn: false,
      })

      expect(() => {
        renderHook(() => useAuth())
      }).toThrow('useAuth must be used within AuthProvider')
    })

    it('should return all required properties from context', () => {
      const mockUser = {
        id: 'user_789',
        firstName: 'Bob',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      expect(result.current).toHaveProperty('user')
      expect(result.current).toHaveProperty('isLoaded')
      expect(result.current).toHaveProperty('isSignedIn')
      expect(result.current).toHaveProperty('role')
      expect(result.current).toHaveProperty('getToken')
    })
  })
})

describe('AuthContext Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Child Component Access', () => {
    it('should allow child components to access auth context', () => {
      const mockUser = {
        id: 'user_integration',
        firstName: 'Integration',
        lastName: 'Test',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const ChildComponent = () => {
        const { user, role, isSignedIn } = useAuth()
        return (
          <div>
            <div data-testid="user-name">
              {user?.firstName} {user?.lastName}
            </div>
            <div data-testid="user-role">{role}</div>
            <div data-testid="signed-in">{isSignedIn ? 'Yes' : 'No'}</div>
          </div>
        )
      }

      render(
        <AuthProvider>
          <ChildComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('user-name')).toHaveTextContent('Integration Test')
      expect(screen.getByTestId('user-role')).toHaveTextContent('author')
      expect(screen.getByTestId('signed-in')).toHaveTextContent('Yes')
    })

    it('should allow nested child components to access auth context', () => {
      const mockUser = {
        id: 'user_nested',
        firstName: 'Nested',
        publicMetadata: { role: 'admin' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const DeepNestedComponent = () => {
        const { role } = useAuth()
        return <div data-testid="deep-role">{role}</div>
      }

      const NestedComponent = () => (
        <div>
          <DeepNestedComponent />
        </div>
      )

      render(
        <AuthProvider>
          <NestedComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('deep-role')).toHaveTextContent('admin')
    })
  })

  describe('Auth State Changes', () => {
    it('should handle loading state correctly', () => {
      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: false,
        isSignedIn: false,
      })

      const TestComponent = () => {
        const { isLoaded, user } = useAuth()
        return (
          <div>
            {!isLoaded && <div data-testid="loading">Loading...</div>}
            {isLoaded && !user && <div data-testid="not-loaded">Not signed in</div>}
          </div>
        )
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('loading')).toBeInTheDocument()
    })

    it('should handle signed in state correctly', () => {
      const mockUser = {
        id: 'user_signed_in',
        firstName: 'SignedIn',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const TestComponent = () => {
        const { isSignedIn, user } = useAuth()
        return (
          <div>{isSignedIn && <div data-testid="signed-in">Welcome, {user?.firstName}!</div>}</div>
        )
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('signed-in')).toHaveTextContent('Welcome, SignedIn!')
    })

    it('should handle signed out state correctly', () => {
      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: true,
        isSignedIn: false,
      })

      const TestComponent = () => {
        const { isSignedIn, isLoaded } = useAuth()
        return (
          <div>{isLoaded && !isSignedIn && <div data-testid="signed-out">Please sign in</div>}</div>
        )
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('signed-out')).toHaveTextContent('Please sign in')
    })

    it('should re-render components when auth state changes', () => {
      const mockUser = {
        id: 'user_rerender',
        firstName: 'ReRender',
        publicMetadata: { role: 'author' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: false,
        isSignedIn: false,
      })

      const TestComponent = () => {
        const { isLoaded, isSignedIn, user } = useAuth()

        if (!isLoaded) {
          return <div data-testid="state">loading</div>
        }

        if (!isSignedIn) {
          return <div data-testid="state">signed-out</div>
        }

        return <div data-testid="state">signed-in-{user?.firstName}</div>
      }

      const { rerender } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('state')).toHaveTextContent('loading')

      mockUseUser.mockReturnValue({
        user: null,
        isLoaded: true,
        isSignedIn: false,
      })

      rerender(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('state')).toHaveTextContent('signed-out')

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      rerender(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByTestId('state')).toHaveTextContent('signed-in-ReRender')
    })
  })

  describe('Multiple Consumers', () => {
    it('should provide same context value to multiple consumers', () => {
      const mockUser = {
        id: 'user_multi',
        firstName: 'Multi',
        publicMetadata: { role: 'admin' },
      } as UserResource

      mockUseUser.mockReturnValue({
        user: mockUser,
        isLoaded: true,
        isSignedIn: true,
      })

      const Consumer1 = () => {
        const { role } = useAuth()
        return <div data-testid="consumer1">{role}</div>
      }

      const Consumer2 = () => {
        const { role } = useAuth()
        return <div data-testid="consumer2">{role}</div>
      }

      render(
        <AuthProvider>
          <Consumer1 />
          <Consumer2 />
        </AuthProvider>
      )

      expect(screen.getByTestId('consumer1')).toHaveTextContent('admin')
      expect(screen.getByTestId('consumer2')).toHaveTextContent('admin')
    })
  })
})
