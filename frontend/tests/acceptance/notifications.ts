import { expect, test } from '@playwright/test'
import { waitForAuthToLoad } from '../e2e/fixtures/helpers'
import { mockClerkAuth } from '../fixtures/clerk-mock'

/**
 * Acceptance tests for Notifications spec - Frontend UI.
 *
 * These tests verify notification preferences, unsubscribe functionality,
 * and notification UI as specified in notifications/requirements.md.
 */

const VALID_TOKEN = 'a'.repeat(64)

test.describe('Notifications - Frontend UI', () => {
  test('User notification preferences settings', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - User visits notification settings: sees toggles for notification types
     * - Toggles available for reply, mention, new post notifications
     * - User disables notification type: corresponding emails NOT sent
     * - Preference updates: changes effective immediately
     */
    const defaultPrefs = {
      preferences: {
        user_id: 1,
        notify_on_comment_replies: true,
        notify_on_mentions: true,
        notify_on_new_posts: true,
      },
    }

    await page.route('**/api/user/notification-preferences', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(defaultPrefs),
        })
      } else if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            preferences: { ...defaultPrefs.preferences, notify_on_comment_replies: false },
          }),
        })
      } else {
        await route.continue()
      }
    })

    await mockClerkAuth(page, { role: 'authenticated' })
    await page.goto('/settings/notifications')
    await waitForAuthToLoad(page)

    const checkboxes = page.locator('input[type="checkbox"]')
    await expect(checkboxes.first()).toBeVisible()
    await expect(checkboxes).toHaveCount(3)

    await checkboxes.first().click()

    const successMessage = page.locator('[role="alert"]')
    await expect(successMessage).toContainText(/Preferences saved/i)
  })

  test('Unsubscribe from emails via link', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - User clicks unsubscribe link: token verified
     * - Token verified: notification preferences updated to "all disabled"
     * - User sees success message: "You've been unsubscribed"
     * - Token invalid or expired: error message displayed
     */
    await page.route('**/api/unsubscribe**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Successfully unsubscribed from all notifications',
          user_id: 1,
        }),
      })
    })

    await page.goto(`/unsubscribe?user_id=1&token=${VALID_TOKEN}`)

    const successMessage = page.locator('[role="alert"]')
    await expect(successMessage).toContainText(/unsubscribed/i)
  })

  test('Invalid unsubscribe token handling', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Invalid token: error message displayed
     * - Expired token: error message displayed
     * - User can navigate to settings to manage preferences manually
     */
    await page.goto('/unsubscribe?user_id=1&token=invalid_token')

    const errorMessage = page.locator('[role="alert"]')
    await expect(errorMessage).toContainText(/invalid.*token/i)
  })

  test.skip('Notification badge for new notifications', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - User has unread notifications: badge displays count
     * - Clicking notification icon: dropdown shows recent notifications
     * - Clicking notification: navigates to relevant content
     * - Marking as read: badge count decreases
     *
     * Note: This is a future enhancement, not in current spec
     */
    await mockClerkAuth(page, { role: 'authenticated' })
    await page.goto('/')

    const notificationBadge = page.locator('[data-testid="notification-badge"]')
    if (await notificationBadge.isVisible()) {
      await expect(notificationBadge).toContainText(/\d+/)

      await notificationBadge.click()

      const notificationDropdown = page.locator('[data-testid="notification-dropdown"]')
      await expect(notificationDropdown).toBeVisible()
    }
  })

  test.skip('Email preview for notification types', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Settings page shows email preview for each notification type
     * - Preview includes: subject line, excerpt, unsubscribe link
     * - User can toggle between HTML and plain text preview
     *
     * Note: This would be useful for users to understand what emails look like
     */
    await mockClerkAuth(page, { role: 'authenticated' })
    await page.goto('/settings/notifications')

    const previewButton = page.locator('button:has-text("Preview Email")')
    if (await previewButton.isVisible()) {
      await previewButton.click()

      const emailPreview = page.locator('[data-testid="email-preview"]')
      await expect(emailPreview).toBeVisible()

      const subjectLine = emailPreview.locator('[data-testid="subject"]')
      await expect(subjectLine).toBeVisible()
    }
  })
})
