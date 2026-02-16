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
      }
    },
    { userId, email, role }
  )

  // Mock Clerk's API endpoints to return authenticated session
  await page.route('**/*.clerk.accounts.dev/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        response: {
          sessions: [
            {
              id: 'sess_test123',
              status: 'active',
              user: {
                id: userId,
                email_addresses: [{ email_address: email }],
                public_metadata: { role },
              },
            },
          ],
          client: {
            sessions: ['sess_test123'],
            sign_in: null,
            sign_up: null,
          },
        },
      }),
    })
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
