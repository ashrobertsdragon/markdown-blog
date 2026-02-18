import type { Page } from '@playwright/test'
import { makeTestJwt } from '../../fixtures/test-jwt'

declare global {
  interface Window {
    __CLERK_TEST_MOCK__?: {
      id: string
      emailAddresses: Array<{ emailAddress: string }>
      publicMetadata: { role: string }
      firstName: string
      lastName: string
      fullName: string
    }
    Clerk?: {
      loaded: boolean
      user?: unknown
      load?: () => Promise<void>
      addListener?: (callback: unknown) => void
      session?: {
        id: string
        status: string
        getToken: () => Promise<string>
      }
    }
  }
}

/**
 * Mock Clerk for unauthenticated state.
 *
 * Simulates a visitor who is not signed in, without connecting to Clerk servers.
 */
export async function mockClerkUnauthenticated(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.__CLERK_TEST_MOCK__ = undefined
    window.Clerk = {
      loaded: true,
      user: undefined,
      load: async () => Promise.resolve(),
      addListener: () => {},
      session: undefined,
    }
  })

  await page.route('**/*.clerk.accounts.dev/**', route => route.abort())
  await page.route('**/clerk.*.js', route => route.abort())
  await page.route('**/clerk-js/**', route => route.abort())
}

/**
 * Mock Clerk authentication for acceptance tests.
 *
 * Blocks real Clerk network traffic and injects a signed RS256 JWT that the
 * Flask backend verifies via the local JWKS server (port 5557). No backend
 * routes are mocked — tests exercise the real API.
 */
export async function mockClerkAuth(
  page: Page,
  options: {
    userId?: string
    email?: string
    role?: 'author' | 'admin' | 'authenticated'
  } = {}
): Promise<void> {
  const { userId = 'user_test_author', email = 'author@example.com', role = 'author' } = options

  const token = await makeTestJwt(userId, email)

  await page.addInitScript(
    ({ userId, email, role, token }) => {
      window.__CLERK_TEST_MOCK__ = {
        id: userId,
        emailAddresses: [{ emailAddress: email }],
        publicMetadata: { role },
        firstName: 'Test',
        lastName: 'User',
        fullName: 'Test User',
      }

      window.Clerk = {
        loaded: true,
        user: window.__CLERK_TEST_MOCK__,
        load: async () => Promise.resolve(),
        addListener: () => {},
        session: {
          id: 'sess_test123',
          status: 'active',
          getToken: async () => token,
        },
      }
    },
    { userId, email, role, token }
  )

  await page.route('**/*.clerk.accounts.dev/**', route => route.abort())
  await page.route('**/clerk.*.js', route => route.abort())
  await page.route('**/clerk-js/**', route => route.abort())
}
