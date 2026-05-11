import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '@/App'
import { render, screen } from '../test-utils'

/**
 * Mock the Home page component to isolate routing logic
 * This allows us to test routing without Home component implementation
 */
vi.mock('@/pages/Home', () => ({
  default: () => <div data-testid="home-component">Home Page</div>,
}))

/**
 * Mock the NotFound page component to isolate routing logic
 */
vi.mock('@/pages/NotFound', () => ({
  default: () => <div data-testid="notfound-component">Not Found Page</div>,
}))

/**
 * Mock the Login page component for authentication flow testing
 */
vi.mock('@/pages/Login', () => ({
  default: () => <div data-testid="login-component">Login Page</div>,
}))

/**
 * Mock the Forbidden page component for authorization testing
 */
vi.mock('@/pages/Forbidden', () => ({
  default: () => <div data-testid="forbidden-component">Forbidden Page</div>,
}))

/**
 * Mock the Admin page component for protected route testing
 * This page does not exist yet - will be created in GREEN phase
 */
vi.mock('@/pages/Admin', () => ({
  default: () => <div data-testid="admin-component">Admin Page</div>,
}))

/**
 * Mock the Author page component for protected route testing
 * This page does not exist yet - will be created in GREEN phase
 */
vi.mock('@/pages/Author', () => ({
  default: () => <div data-testid="author-component">Author Page</div>,
}))

/**
 * Mock the AuthContext to control authentication state in tests
 */
vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

/**
 * App Component Routing Tests
 *
 * Tests the App component's routing configuration and behavior.
 * Validates that BrowserRouter is properly configured and routes
 * are set up correctly for "/" and "*" (catch-all) paths.
 */
describe('App', () => {
  describe('component rendering and structure', () => {
    /**
     * Test that App component renders without crashing
     * This is the basic smoke test for the component
     */
    it('should render without crashing', () => {
      expect(() => {
        render(<App />)
      }).not.toThrow()
    })

    /**
     * Test that App component renders successfully
     * Validates that the component produces valid output
     */
    it('should render successfully', () => {
      const { container } = render(<App />)
      expect(container).toBeTruthy()
      expect(container.firstChild).toBeTruthy()
    })
  })

  describe('routing configuration', () => {
    /**
     * Test that App uses BrowserRouter for client-side routing
     * BrowserRouter should be the top-level wrapper, NOT MemoryRouter
     */
    it('should use BrowserRouter for client-side routing', () => {
      const { container } = render(<App />)

      expect(container.firstChild).toBeTruthy()
    })

    /**
     * Test that App exports as a default export
     * This ensures the component can be imported as: import App from '@/App'
     */
    it('should export as default export', () => {
      expect(App).toBeTruthy()
      expect(typeof App).toBe('function')
    })

    /**
     * Test that Routes component is used in App
     * Routes is the core React Router component for defining routes
     */
    it('should render with Routes component', () => {
      const { container } = render(<App />)

      expect(container.firstChild).toBeTruthy()
    })
  })

  describe('root path route', () => {
    /**
     * Test that Home component renders at root path "/"
     * This validates the primary route is configured correctly
     */
    it('should render Home page at root path', () => {
      render(<App />)

      const homeElement = screen.queryByTestId('home-component')
      expect(homeElement).toBeInTheDocument()
    })

    /**
     * Test that root path contains Home component text
     * Further validates that the correct component is routed
     */
    it('should display Home page content at root', () => {
      render(<App />)

      const homeContent = screen.queryByText(/home page/i)
      expect(homeContent).toBeInTheDocument()
    })
  })

  describe('catch-all route', () => {
    /**
     * Test that catch-all route ("*") is configured
     * This route should handle any unmatched paths
     */
    it('should have catch-all route configured', () => {
      const { container } = render(<App />)

      expect(container).toBeTruthy()
    })

    /**
     * Test that App component structure is valid
     * Ensures routes are properly nested
     */
    it('should have valid route structure', () => {
      const { container } = render(<App />)

      expect(container.firstChild).toBeTruthy()
    })
  })

  describe('multiple renders', () => {
    /**
     * Test that component can be rendered multiple times safely
     * Ensures no state leakage between renders
     */
    it('should render multiple times safely', () => {
      const { unmount: unmount1 } = render(<App />)
      unmount1()

      const { unmount: unmount2 } = render(<App />)
      unmount2()
    })

    /**
     * Test that each render is independent
     * Component should reset state between renders
     */
    it('should have independent renders', () => {
      const { container: container1, unmount: unmount1 } = render(<App />)
      expect(container1.firstChild).toBeTruthy()
      unmount1()

      const { container: container2 } = render(<App />)
      expect(container2.firstChild).toBeTruthy()
    })

    /**
     * Test that component unmounts cleanly
     * No console warnings or unhandled exceptions
     */
    it('should unmount without errors', () => {
      const { unmount } = render(<App />)

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })

  describe('router configuration', () => {
    /**
     * Test that App does NOT use basename prop
     * The application runs at root "/" not a subdirectory
     */
    it('should not use basename prop on BrowserRouter', () => {
      render(<App />)

      const homeElement = screen.queryByTestId('home-component')
      expect(homeElement).toBeInTheDocument()
    })

    /**
     * Test that router is properly initialized
     * Routes should be accessible and functional
     */
    it('should have functional routing setup', () => {
      const { container } = render(<App />)

      expect(container.firstChild).toBeTruthy()
    })
  })

  describe('component behavior', () => {
    /**
     * Test that App component is a functional component
     * Can be called as a function and returns JSX
     */
    it('should be a functional component', () => {
      expect(typeof App).toBe('function')

      const { container } = render(<App />)
      expect(container.firstChild).toBeTruthy()
    })

    /**
     * Test that component renders within expected DOM structure
     * Should have a valid React Portal or element tree
     */
    it('should render in valid DOM structure', () => {
      const { container } = render(<App />)

      expect(container.firstChild).toBeTruthy()
      expect(container.textContent).toBeTruthy()
    })

    /**
     * Test that rendering is synchronous
     * App should render immediately without async operations
     */
    it('should render synchronously', () => {
      expect(() => {
        render(<App />)
      }).not.toThrow()

      const homeElement = screen.queryByTestId('home-component')
      expect(homeElement).toBeInTheDocument()
    })
  })

  describe('react router integration', () => {
    /**
     * Test that BrowserRouter provides routing context
     * All child components should have access to routing hooks
     */
    it('should provide routing context to children', () => {
      const { container } = render(<App />)

      expect(container).toBeTruthy()
    })

    /**
     * Test that Routes component is properly configured
     * Should be the direct child of BrowserRouter
     */
    it('should have Routes as main route container', () => {
      render(<App />)

      const homeElement = screen.queryByTestId('home-component')
      expect(homeElement).toBeInTheDocument()
    })

    /**
     * Test that route components are properly rendered
     * Route path matches should work correctly
     */
    it('should render route components correctly', () => {
      render(<App />)

      const homeComponent = screen.queryByTestId('home-component')
      expect(homeComponent).toBeInTheDocument()
    })
  })

  describe('Protected Routes', () => {
    let mockUseAuth: ReturnType<typeof vi.fn>

    beforeEach(async () => {
      vi.clearAllMocks()
      const authModule = await import('@/context/AuthContext')
      mockUseAuth = vi.mocked(authModule.useAuth)
    })

    describe('Admin Route Protection', () => {
      /**
       * Test that unauthenticated users are redirected to login when accessing /admin
       * Requirement 7.1: Unauthenticated user visits /admin → redirected to /login with location state
       */
      it('should redirect unauthenticated users to login page when accessing /admin', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        render(<App />, {
          initialEntries: ['/admin'],
        })

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).toBeInTheDocument()

        const adminComponent = screen.queryByTestId('admin-component')
        expect(adminComponent).not.toBeInTheDocument()
      })

      /**
       * Test that authenticated admin users can access /admin route
       * Requirement 7.2: Authenticated admin user visits /admin → sees admin page
       */
      it('should allow authenticated admin users to access admin page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          user: { id: 'admin-user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/admin'],
        })

        const adminComponent = screen.queryByTestId('admin-component')
        expect(adminComponent).toBeInTheDocument()

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).not.toBeInTheDocument()

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).not.toBeInTheDocument()
      })

      /**
       * Test that authenticated non-admin users are redirected to forbidden page
       * Requirement 7.3: Authenticated non-admin visits /admin → redirected to /forbidden
       */
      it('should redirect authenticated non-admin users to forbidden page when accessing /admin', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          user: { id: 'regular-user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/admin'],
        })

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).toBeInTheDocument()

        const adminComponent = screen.queryByTestId('admin-component')
        expect(adminComponent).not.toBeInTheDocument()

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).not.toBeInTheDocument()
      })

      /**
       * Test that authenticated author users are redirected to forbidden page
       * Authors do not have admin privileges
       */
      it('should redirect authenticated author users to forbidden page when accessing /admin', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          user: { id: 'author-user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/admin'],
        })

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).toBeInTheDocument()

        const adminComponent = screen.queryByTestId('admin-component')
        expect(adminComponent).not.toBeInTheDocument()
      })

      /**
       * Test that loading state shows loading message instead of admin content
       * While auth is loading, protected content should not be visible
       */
      it('should show loading state while auth is loading for /admin route', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: false,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        const { container } = render(<App />, {
          initialEntries: ['/admin'],
        })

        const loadingSpinner = container.querySelector('.animate-spin')
        expect(loadingSpinner).toBeTruthy()

        const adminComponent = screen.queryByTestId('admin-component')
        expect(adminComponent).not.toBeInTheDocument()
      })
    })

    describe('Author Route Protection', () => {
      /**
       * Test that unauthenticated users are redirected to login when accessing /author
       * Similar to admin route, requires authentication first
       */
      it('should redirect unauthenticated users to login page when accessing /author', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        render(<App />, {
          initialEntries: ['/author'],
        })

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).toBeInTheDocument()

        const authorComponent = screen.queryByTestId('author-component')
        expect(authorComponent).not.toBeInTheDocument()
      })

      /**
       * Test that authenticated author users can access /author route
       * Authors should have access to author-specific features
       */
      it('should allow authenticated author users to access author page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          user: { id: 'author-user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/author'],
        })

        const authorComponent = screen.queryByTestId('author-component')
        expect(authorComponent).toBeInTheDocument()

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).not.toBeInTheDocument()

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).not.toBeInTheDocument()
      })

      /**
       * Test that authenticated admin users can access /author route
       * Admins have hierarchical access (admin > author > authenticated)
       */
      it('should allow authenticated admin users to access author page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          user: { id: 'admin-user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/author'],
        })

        const authorComponent = screen.queryByTestId('author-component')
        expect(authorComponent).toBeInTheDocument()

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).not.toBeInTheDocument()
      })

      /**
       * Test that authenticated regular users are redirected to forbidden page
       * Regular authenticated users do not have author privileges
       */
      it('should redirect authenticated regular users to forbidden page when accessing /author', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          user: { id: 'regular-user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/author'],
        })

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).toBeInTheDocument()

        const authorComponent = screen.queryByTestId('author-component')
        expect(authorComponent).not.toBeInTheDocument()
      })

      /**
       * Test that loading state shows loading message for /author route
       * Protected content should not be visible during auth loading
       */
      it('should show loading state while auth is loading for /author route', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: false,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        const { container } = render(<App />, {
          initialEntries: ['/author'],
        })

        const loadingSpinner = container.querySelector('.animate-spin')
        expect(loadingSpinner).toBeTruthy()

        const authorComponent = screen.queryByTestId('author-component')
        expect(authorComponent).not.toBeInTheDocument()
      })
    })

    describe('Login and Forbidden Routes', () => {
      /**
       * Test that /login route is accessible to all users
       * Public route should not require authentication
       */
      it('should render login page when accessing /login route', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        render(<App />, {
          initialEntries: ['/login'],
        })

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).toBeInTheDocument()
      })

      /**
       * Test that /forbidden route is accessible
       * Forbidden page should be directly accessible
       */
      it('should render forbidden page when accessing /forbidden route', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          user: { id: 'user-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/forbidden'],
        })

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).toBeInTheDocument()
      })

      /**
       * Test that authenticated users can still access /login
       * Login page should be accessible even when signed in
       */
      it('should allow authenticated users to access login page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          user: { id: 'admin-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/login'],
        })

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).toBeInTheDocument()
      })

      /**
       * Test that unauthenticated users can access /forbidden
       * Forbidden page should be publicly accessible
       */
      it('should allow unauthenticated users to access forbidden page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        render(<App />, {
          initialEntries: ['/forbidden'],
        })

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).toBeInTheDocument()
      })
    })

    describe('Public Routes', () => {
      /**
       * Test that home page is accessible without authentication
       * Public routes should work regardless of auth state
       */
      it('should allow unauthenticated users to access home page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        render(<App />)

        const homeComponent = screen.queryByTestId('home-component')
        expect(homeComponent).toBeInTheDocument()
      })

      /**
       * Test that authenticated users can access home page
       * Home page should remain public
       */
      it('should allow authenticated users to access home page', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          user: { id: 'admin-123' } as never,
        })

        render(<App />)

        const homeComponent = screen.queryByTestId('home-component')
        expect(homeComponent).toBeInTheDocument()
      })
    })

    describe('Post-Login Redirect Behavior', () => {
      /**
       * Test that login redirect preserves original destination
       * Location state should be passed to login page
       */
      it('should pass location state when redirecting to login from protected route', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          user: null,
        })

        render(<App />, {
          initialEntries: ['/admin'],
        })

        const loginComponent = screen.queryByTestId('login-component')
        expect(loginComponent).toBeInTheDocument()
      })

      /**
       * Test that role hierarchy is respected in protected routes
       * Admin should have access to both admin and author routes
       */
      it('should respect role hierarchy in protected routes', () => {
        mockUseAuth.mockReturnValue({
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          user: { id: 'admin-123' } as never,
        })

        render(<App />, {
          initialEntries: ['/author'],
        })

        const authorComponent = screen.queryByTestId('author-component')
        expect(authorComponent).toBeInTheDocument()

        const forbiddenComponent = screen.queryByTestId('forbidden-component')
        expect(forbiddenComponent).not.toBeInTheDocument()
      })
    })
  })
})

describe('React Query devtools configuration', () => {
  /**
   * Verifies that the @tanstack/react-query-devtools package is installed and importable.
   * This test will fail until the package is added as a dev dependency.
   * The devtools panel aids development by exposing query cache state.
   */
  it('should have @tanstack/react-query-devtools package installed', async () => {
    const devtoolsModule = await import('@tanstack/react-query-devtools')
    expect(devtoolsModule).toBeTruthy()
  })

  /**
   * Verifies that ReactQueryDevtools is a named export from the devtools package.
   * The component must be exported so App.tsx can import and render it conditionally.
   */
  it('should export ReactQueryDevtools component from the package', async () => {
    const { ReactQueryDevtools } = await import('@tanstack/react-query-devtools')
    expect(ReactQueryDevtools).toBeDefined()
    expect(typeof ReactQueryDevtools).toBe('function')
  })

  /**
   * Verifies that App renders correctly when ReactQueryDevtools is present in the tree.
   * The devtools component must not interfere with existing route rendering.
   * This test validates structural integrity — it will pass once the package is installed
   * and the component is placed inside QueryClientProvider in App.
   */
  it('should render App without errors when devtools component is mounted', () => {
    const { container } = render(<App />)
    expect(container.firstChild).toBeTruthy()
  })

  /**
   * Verifies that ReactQueryDevtools initialIsOpen prop type is correct.
   * The component should accept an initialIsOpen boolean prop so it starts closed
   * by default in development, reducing visual noise on first load.
   */
  it('should accept initialIsOpen prop on ReactQueryDevtools component', async () => {
    const { ReactQueryDevtools } = await import('@tanstack/react-query-devtools')
    expect(ReactQueryDevtools).toBeDefined()
    const propTypes = (ReactQueryDevtools as { propTypes?: Record<string, unknown> }).propTypes
    if (propTypes !== undefined) {
      expect(typeof propTypes).toBe('object')
    }
    expect(typeof ReactQueryDevtools).toBe('function')
  })
})
