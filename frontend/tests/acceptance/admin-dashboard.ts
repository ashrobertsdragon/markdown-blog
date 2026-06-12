import { expect, test } from '@playwright/test'
import { mockClerkAuth } from '../fixtures/clerk-mock'

const BACKEND = 'http://localhost:5555'
const ADMIN_AUTH = { role: 'admin' as const, userId: 'user_test_admin', email: 'admin@example.com' }

/**
 * Acceptance tests for Admin Dashboard spec - Frontend UI.
 *
 * Tests run against the real seeded backend. No route mocking — each test
 * calls /api/test/seed before running to guarantee a clean, deterministic
 * dataset. Seeded state: author@example.com (id=1, role=author),
 * admin@example.com (id=2, role=admin), two published posts ("Test Post",
 * "Published 1"), two comments on "test-post".
 */

test.describe('Admin Dashboard - Frontend UI', () => {
  test.beforeEach(async ({ request }) => {
    await request.post(`${BACKEND}/api/test/seed`)
  })

  test.afterAll(async ({ request }) => {
    await request.delete(`${BACKEND}/api/test/reset`)
  })

  test('User management interface', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin/users: all users displayed in table
     * - Table shows: email, role, created_at
     * - Admin clicks "Edit Role": modal appears with role selection
     * - Admin selects new role and confirms: user's role updated
     * - Role update succeeds: modal closes
     */
    await mockClerkAuth(page, ADMIN_AUTH)
    await page.goto('/admin/users')

    const userTable = page.locator('table')
    await expect(userTable).toBeVisible()

    const emailCell = page.locator('td:has-text("author@example.com")')
    await expect(emailCell).toBeVisible()

    const editButton = page.locator('button:has-text("Edit Role")').first()
    await editButton.click()

    const roleModal = page.locator('[role="dialog"]')
    await expect(roleModal).toBeVisible()

    const adminRadio = roleModal.locator('input[type="radio"][value="admin"]')
    await adminRadio.click()

    const confirmButton = roleModal.locator('button:has-text("Save")')
    await confirmButton.click()

    await expect(roleModal).not.toBeVisible()
  })

  test('User profile viewer', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin navigates to /admin/users/:id: profile page displays
     * - Profile shows: email, role, activity counts, recent posts section
     * - View Posts link navigates to content page
     */
    await mockClerkAuth(page, ADMIN_AUTH)
    await page.goto('/admin/users/1')

    const userEmail = page.locator('dd:has-text("author@example.com")')
    await expect(userEmail).toBeVisible()

    const activitySection = page.locator('[data-testid="user-activity"]')
    await expect(activitySection).toBeVisible()

    const postsList = page.locator('[data-testid="user-posts"]')
    await expect(postsList).toBeVisible()

    const viewPostsLink = page.locator('a:has-text("View Posts")')
    await expect(viewPostsLink).toBeVisible()
  })

  test('Content moderation dashboard', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin/content: Posts tab active by default
     * - Posts tab: lists all published posts with title, author, published_at
     * - Admin clicks "Unpublish": confirmation modal appears
     * - Unpublish confirmed: modal closes
     */
    await mockClerkAuth(page, ADMIN_AUTH)
    await page.goto('/admin/content')

    const postTitle = page.locator('text=/Test Post/')
    await expect(postTitle).toBeVisible()

    const unpublishButton = page.locator('button:has-text("Unpublish")').first()
    await unpublishButton.click()

    const confirmModal = page.locator('[role="dialog"]')
    await expect(confirmModal).toBeVisible()

    await confirmModal.locator('button:has-text("Unpublish")').click()
    await expect(confirmModal).not.toBeVisible()
  })

  test('System health dashboard', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin/system: health metrics displayed
     * - Metrics include: API status card, database status card
     * - Error log section shows errors or "No recent errors" message
     */
    await mockClerkAuth(page, ADMIN_AUTH)
    await page.goto('/admin/system')

    const apiStatus = page.locator('[data-testid="api-status"]')
    await expect(apiStatus).toBeVisible()

    const dbStatus = page.locator('[data-testid="database-status"]')
    await expect(dbStatus).toBeVisible()

    const errorLogOrEmpty = page
      .locator('[data-testid="error-log"]')
      .or(page.getByText('No recent errors'))
    await expect(errorLogOrEmpty.first()).toBeVisible()
  })

  test('Admin dashboard navigation', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin: sidebar navigation visible
     * - Sidebar has links: Users, Content, System
     * - Admin clicks a link: navigates to the section
     * - Active section highlighted in sidebar (aria-current="page")
     */
    await mockClerkAuth(page, ADMIN_AUTH)
    await page.goto('/admin')

    const sidebar = page.locator('[data-testid="admin-sidebar"]')
    await expect(sidebar).toBeVisible()

    const usersLink = sidebar.locator('a:has-text("Users")')
    await expect(usersLink).toBeVisible()

    const contentLink = sidebar.locator('a:has-text("Content")')
    await expect(contentLink).toBeVisible()

    const systemLink = sidebar.locator('a:has-text("System")')
    await expect(systemLink).toBeVisible()

    await usersLink.click()
    await page.waitForURL('/admin/users')

    const activeLink = sidebar.locator('a[aria-current="page"]:has-text("Users")')
    await expect(activeLink).toBeVisible()
  })

  test('Admin dashboard responsive layout', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Desktop: sidebar visible
     * - Mobile: sidebar collapses to hamburger menu
     * - Hamburger clicked: sidebar opens (aria-expanded=true)
     * - Content clicked: sidebar closes (aria-expanded=false)
     */
    await mockClerkAuth(page, ADMIN_AUTH)

    await page.setViewportSize({ width: 1280, height: 720 })
    await page.goto('/admin')

    const sidebar = page.locator('[data-testid="admin-sidebar"]')
    await expect(sidebar).toBeVisible()

    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/admin')

    const hamburgerMenu = page.locator('button[aria-label="Open navigation"]')
    await expect(hamburgerMenu).toBeVisible()
    await expect(hamburgerMenu).toHaveAttribute('aria-expanded', 'false')

    await hamburgerMenu.click()
    await expect(hamburgerMenu).toHaveAttribute('aria-expanded', 'true')

    await page.locator('[data-testid="sidebar-backdrop"]').click()
    await expect(hamburgerMenu).toHaveAttribute('aria-expanded', 'false')
  })

  test('Non-admin user access prevention', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Non-admin visits /admin: redirected to /forbidden
     * - Forbidden page shows access denied message and home link
     */
    await mockClerkAuth(page, { role: 'author' })

    await page.goto('/admin')

    const forbiddenMessage = page.locator('h2:has-text("Access Denied")')
    await expect(forbiddenMessage).toBeVisible()

    const homeLink = page.locator('a:has-text("Home")')
    await expect(homeLink).toBeVisible()
  })
})
