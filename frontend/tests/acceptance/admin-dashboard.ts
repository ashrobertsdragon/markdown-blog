import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'

/**
 * Acceptance tests for Admin Dashboard spec - Frontend UI.
 *
 * These tests verify admin user management, content moderation UI,
 * and system health monitoring as specified in admin-dashboard/requirements.md.
 */

test.describe('Admin Dashboard - Frontend UI', () => {
  test.skip('User management interface', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin/users: all users displayed in table
     * - Table shows: email, role, created_at
     * - Admin clicks "Edit Role": modal appears with role selection
     * - Admin selects new role and confirms: user's role updated
     * - Role update succeeds: table refreshes with updated role
     * - Table has >50 users: pagination implemented with next/prev buttons
     */
    await mockClerkAuth(page, { role: 'admin' })

    await page.route('**/users', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          users: [
            {
              id: 1,
              email: 'user1@example.com',
              role: 'authenticated',
              created_at: '2024-01-01T12:00:00Z',
            },
            {
              id: 2,
              email: 'user2@example.com',
              role: 'author',
              created_at: '2024-01-02T12:00:00Z',
            },
          ],
          total: 2,
        }),
      })
    })

    await page.goto('/admin/users')

    const userTable = page.locator('table')
    await expect(userTable).toBeVisible()

    const emailCell = page.locator('td:has-text("user1@example.com")')
    await expect(emailCell).toBeVisible()

    const editButton = page.locator('button:has-text("Edit Role")').first()
    await editButton.click()

    const roleModal = page.locator('[role="dialog"]')
    await expect(roleModal).toBeVisible()

    const roleSelect = roleModal.locator('select[name="role"]')
    await roleSelect.selectOption('author')

    await page.route('**/users/*/role', async route => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Role updated successfully' }),
        })
      } else {
        await route.continue()
      }
    })

    const confirmButton = roleModal.locator('button:has-text("Save")')
    await confirmButton.click()

    await expect(roleModal).not.toBeVisible()

    const updatedRole = page.locator('td:has-text("author")')
    await expect(updatedRole).toBeVisible()
  })

  test.skip('User profile viewer', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin clicks user's email: profile page displays
     * - Profile shows: email, role, created_at, recent activity
     * - Recent activity includes: last login, posts authored, comments posted
     * - Admin clicks "View Posts": all posts by user listed
     * - Admin clicks "View Comments": all comments by user listed
     */
    await mockClerkAuth(page, { role: 'admin' })

    const userId = 1
    await page.route(`**/users/${userId}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: userId,
          email: 'user@example.com',
          role: 'author',
          created_at: '2024-01-01T12:00:00Z',
          activity: {
            last_login: '2024-02-15T10:00:00Z',
            posts_authored: 5,
            comments_posted: 12,
          },
        }),
      })
    })

    await page.goto(`/admin/users/${userId}`)

    const profileHeader = page.locator('h1:has-text("user@example.com")')
    await expect(profileHeader).toBeVisible()

    const activitySection = page.locator('[data-testid="user-activity"]')
    await expect(activitySection).toBeVisible()
    await expect(activitySection).toContainText('5')
    await expect(activitySection).toContainText('12')

    const viewPostsButton = page.locator('button:has-text("View Posts")')
    await viewPostsButton.click()

    const postsList = page.locator('[data-testid="user-posts"]')
    await expect(postsList).toBeVisible()
  })

  test.skip('Content moderation dashboard', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin/content: tabs display "Published Posts" and "Recent Comments"
     * - "Published Posts" tab: lists all published posts with title, author, published_at
     * - Admin clicks "View Post": public post view opens in new tab
     * - Admin clicks "Unpublish Post": confirmation modal appears
     * - Unpublish confirmed: post removed from public view
     * - "Recent Comments" tab: lists recent comments with content, author, post title
     * - Admin clicks "Delete Comment": confirmation modal appears
     * - Deletion confirmed: comment removed
     */
    await mockClerkAuth(page, { role: 'admin' })

    await page.route('**/admin/posts', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          posts: [
            {
              slug: 'test-post',
              title: 'Test Post',
              author: 'author@example.com',
              published_at: '2024-01-15T12:00:00Z',
            },
          ],
        }),
      })
    })

    await page.goto('/admin/content')

    const publishedPostsTab = page.locator('button:has-text("Published Posts")')
    await publishedPostsTab.click()

    const postTitle = page.locator('text=/Test Post/')
    await expect(postTitle).toBeVisible()

    const unpublishButton = page.locator('button:has-text("Unpublish")').first()
    await unpublishButton.click()

    const confirmModal = page.locator('[role="alertdialog"]')
    await expect(confirmModal).toBeVisible()

    await page.route('**/admin/posts/*/unpublish', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Post unpublished' }),
        })
      } else {
        await route.continue()
      }
    })

    const confirmButton = confirmModal.locator('button:has-text("Confirm")')
    await confirmButton.click()

    await expect(confirmModal).not.toBeVisible()
  })

  test.skip('System health dashboard', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin/system: health metrics displayed
     * - Metrics include: API status, database status, uptime
     * - Health check returns 200: status shows "Healthy" with green indicator
     * - Health check returns 503: status shows "Degraded" with yellow indicator
     * - Health check fails: status shows "Unhealthy" with red indicator
     * - Admin clicks "Recent Errors": displays last 50 application errors
     * - Error log shows: timestamp, error message, stack trace, endpoint
     */
    await mockClerkAuth(page, { role: 'admin' })

    await page.route('**/admin/system/health', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          api: { status: 'healthy', uptime: 3600 },
          database: { status: 'healthy', latency: 5 },
          github: { status: 'healthy', rate_limit_remaining: 4500 },
        }),
      })
    })

    await page.goto('/admin/system')

    const apiStatus = page.locator('[data-testid="api-status"]')
    await expect(apiStatus).toContainText('Healthy')
    await expect(apiStatus.locator('.bg-green-500')).toBeVisible()

    const dbStatus = page.locator('[data-testid="database-status"]')
    await expect(dbStatus).toContainText('Healthy')

    const recentErrorsButton = page.locator('button:has-text("Recent Errors")')
    await recentErrorsButton.click()

    const errorLog = page.locator('[data-testid="error-log"]')
    if (await errorLog.isVisible()) {
      await expect(errorLog).toBeVisible()
    } else {
      const noErrorsMessage = page.locator('text=/No recent errors/')
      await expect(noErrorsMessage).toBeVisible()
    }
  })

  test.skip('Admin dashboard navigation', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin visits /admin: dashboard layout displays with sidebar navigation
     * - Sidebar includes links: Dashboard, Users, Content, System Health
     * - Admin clicks sidebar link: corresponding section displayed
     * - Admin not logged in: redirected to /login
     * - Logged-in user not admin: redirected to /forbidden
     * - Admin navigates: active section highlighted in sidebar
     */
    await mockClerkAuth(page, { role: 'admin' })
    await page.goto('/admin')

    const sidebar = page.locator('[data-testid="admin-sidebar"]')
    await expect(sidebar).toBeVisible()

    const dashboardLink = sidebar.locator('a:has-text("Dashboard")')
    await expect(dashboardLink).toBeVisible()

    const usersLink = sidebar.locator('a:has-text("Users")')
    await expect(usersLink).toBeVisible()

    const contentLink = sidebar.locator('a:has-text("Content")')
    await expect(contentLink).toBeVisible()

    const systemLink = sidebar.locator('a:has-text("System Health")')
    await expect(systemLink).toBeVisible()

    await usersLink.click()
    await page.waitForURL('/admin/users')

    const activeLink = sidebar.locator('a.active:has-text("Users")')
    await expect(activeLink).toBeVisible()
  })

  test.skip('Admin dashboard responsive layout', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Dashboard renders on desktop: sidebar visible, content area occupies remaining space
     * - Dashboard renders on mobile: sidebar collapses to hamburger menu
     * - Hamburger menu clicked: sidebar slides in from left
     * - Content clicked on mobile: sidebar closes automatically
     * - Components accessible: proper ARIA labels, keyboard navigation
     */
    await mockClerkAuth(page, { role: 'admin' })

    // Test desktop layout
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.goto('/admin')

    const sidebar = page.locator('[data-testid="admin-sidebar"]')
    await expect(sidebar).toBeVisible()

    // Test mobile layout
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/admin')

    const hamburgerMenu = page.locator('button[aria-label*="menu" i]')
    await expect(hamburgerMenu).toBeVisible()

    await hamburgerMenu.click()
    await expect(sidebar).toBeVisible()

    const mainContent = page.locator('main')
    await mainContent.click()
    await expect(sidebar).not.toBeVisible()
  })

  test.skip('Non-admin user access prevention', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Non-admin requests admin endpoints: 403 Forbidden returned
     * - Non-admin visits /admin: redirected to /forbidden
     * - Forbidden page shows clear message and link to home
     */
    await mockClerkAuth(page, { role: 'author' })

    await page.goto('/admin')

    const forbiddenMessage = page.locator('text=/forbidden|unauthorized|access denied/i')
    await expect(forbiddenMessage).toBeVisible()

    const homeLink = page.locator('a:has-text("Home")')
    await expect(homeLink).toBeVisible()
  })
})
