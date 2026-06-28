import '@testing-library/jest-dom'
import { vi } from 'vitest'

/**
 * Mock @clerk/clerk-react globally so unit tests never need a real
 * ClerkProvider in the component tree. AuthProvider → ClerkAuthProvider calls
 * useUser() and useAuth(); without this mock every test that renders via
 * test-utils (which wraps AppRoutes in AuthProvider) throws.
 *
 * Individual test files that need a specific signed-in state can override
 * these stubs with vi.mocked(useUser).mockReturnValue(...) etc.
 */
vi.mock('@clerk/clerk-react', () => ({
  useUser: vi.fn(() => ({ user: null, isLoaded: true, isSignedIn: false })),
  useAuth: vi.fn(() => ({ getToken: vi.fn(async () => null) })),
  ClerkProvider: ({ children }: { children: unknown }) => children,
  UserButton: () => null,
  SignIn: () => null,
  SignUp: () => null,
  useClerk: vi.fn(() => ({ signOut: vi.fn() })),
}))

/**
 * Test environment setup for Vitest
 *
 * Configures the jsdom test environment with necessary DOM elements
 * required by the React application entry point.
 *
 * Exposes `vi` as `jest` on globalThis so that @testing-library/dom's
 * jestFakeTimersAreEnabled() check succeeds when vi.useFakeTimers() is
 * active. Without this, waitFor() uses setInterval for retries which
 * never fires under fake timers, causing test timeouts.
 */

Object.defineProperty(globalThis, 'jest', {
  value: vi,
  writable: true,
  configurable: true,
})

const rootElement = document.createElement('div')
rootElement.id = 'root'
document.body.appendChild(rootElement)

/**
 * jsdom does not implement window.matchMedia, but react-hot-toast uses it
 * to detect the user's color-scheme preference. This stub satisfies the call
 * so Toaster renders without throwing in the test environment.
 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})
