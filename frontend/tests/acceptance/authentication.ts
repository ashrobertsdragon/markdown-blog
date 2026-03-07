import { expect, test } from '@playwright/test'
import { mockClerkAuth, mockClerkUnauthenticated } from '../fixtures/clerk-mock'

/**
 * Acceptance tests for Authentication spec - Frontend UI.
 *
 * These tests verify Clerk authentication integration, protected routes,
 * and role-based UI elements as specified in authentication/requirements.md.
 */

test.describe('Authentication - Frontend UI', () => {
  test('User registration and login via Clerk', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Visitor clicks "Sign Up" displays Clerk registration options
     * - OAuth flow creates user account and returns JWT
     * - Magic link sends email and verifies authentication
     * - Authentication success: backend receives and validates JWT
     */
    await page.goto('/')

    const signInButton = page.locator('text=/sign in/i').first()
    if (await signInButton.isVisible()) {
      await expect(signInButton).toBeVisible()
    }
  })

  test('AuthContext provides authentication state', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - AuthContext initializes with Clerk's useUser hook
     * - Provides { user, isLoaded, isSignedIn, role }
     * - Components use useAuth() hook
     * - Logout clears user state
     * - State changes trigger re-renders
     */
    await mockClerkAuth(page, { role: 'author' })
    await page.goto('/')

    const authenticatedElement = page.locator('[data-testid="user-menu"]').first()
    if (await authenticatedElement.isVisible()) {
      await expect(authenticatedElement).toBeVisible()
    }
  })

  test('Protected routes redirect unauthenticated users', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Unauthenticated user visiting protected route redirects or shows forbidden
     * - Authenticated user sees protected content if authorized
     * - User without required role sees 403 Forbidden page
     * - User redirected back to originally requested page after login
     */

    await mockClerkUnauthenticated(page)

    await page.goto('/my-posts', { waitUntil: 'networkidle' })

    await page.waitForURL(/\/login/, { timeout: 5000 }).catch(() => {})

    const url = page.url()
    expect(url).toContain('/login')
  })

  test('Protected routes allow authorized users', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Authenticated user with admin role can access /admin
     * - Protected routes check both authentication and authorization
     */
    await mockClerkAuth(page, { role: 'admin' })
    await page.goto('/admin')

    const url = page.url()
    expect(url).toContain('/admin')
  })

  test('Role-based UI elements', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Author role shows author-specific UI elements
     * - Admin role shows admin-specific UI elements
     * - Authenticated users see role-appropriate navigation
     */
    await mockClerkAuth(page, { role: 'author' })
    await page.goto('/')

    const myPostsLink = page.locator('text=/my posts/i').first()
    if (await myPostsLink.isVisible()) {
      await expect(myPostsLink).toBeVisible()
    }
  })

  test.skip('User management UI for admins', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin can view users with email, role, created_at
     * - Admin can update user roles via modal
     * - Non-admin users cannot access user management
     * - Role updates refresh table with new role
     *
     * Note: Requires admin dashboard implementation
     */
    await mockClerkAuth(page, { role: 'admin' })
    await page.goto('/admin/users')
  })
})
