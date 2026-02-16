import type { Page } from '@playwright/test'

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
      session?: {
        id: string
        status: string
      }
    }
  }
}

/**
 * Mock Clerk authentication for E2E tests.
 *
 * This injects a mock Clerk object to simulate an authenticated user
 * without requiring real Clerk credentials or network access to Clerk servers.
 */
export async function mockClerkAuth(
  page: Page,
  options: {
    userId?: string
    email?: string
    role?: 'author' | 'admin' | 'authenticated'
  } = {}
): Promise<void> {
  const { userId = 'user_test123', email = 'author@example.com', role = 'author' } = options

  // Inject mock user data that AuthProvider will detect
  await page.addInitScript(
    ({ userId, email, role }) => {
      // Set test mock that AuthProvider will use instead of Clerk hooks
      window.__CLERK_TEST_MOCK__ = {
        id: userId,
        emailAddresses: [{ emailAddress: email }],
        publicMetadata: { role },
        firstName: 'Test',
        lastName: 'User',
        fullName: 'Test User',
      }

      // Also set window.Clerk for compatibility with waitForAuthToLoad helper
      window.Clerk = {
        loaded: true,
        user: window.__CLERK_TEST_MOCK__,
        load: async () => Promise.resolve(),
        session: {
          id: 'sess_test123',
          status: 'active',
        },
      }
    },
    { userId, email, role }
  )

  // Block all Clerk network requests to prevent loading real Clerk SDK
  await page.route('**/*.clerk.accounts.dev/**', async route => {
    await route.abort()
  })

  await page.route('**/clerk.*.js', async route => {
    await route.abort()
  })

  await page.route('**/clerk-js/**', async route => {
    await route.abort()
  })

  // Mock our backend's /api/auth/me endpoint
  await page.route('**/api/auth/me', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 10,
        clerk_user_id: userId,
        email,
        role,
      }),
    })
  })
}
