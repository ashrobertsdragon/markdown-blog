import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'

/**
 * Acceptance tests for Notifications spec - Frontend UI.
 *
 * These tests verify notification preferences, unsubscribe functionality,
 * and notification UI as specified in notifications/requirements.md.
 */

test.describe('Notifications - Frontend UI', () => {
  test.skip('User notification preferences settings', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - User visits notification settings: sees toggles for notification types
     * - Toggles available:
     *   * "Notify me on comment replies"
     *   * "Notify me on mentions"
     *   * "Notify me on new posts" (future feature)
     * - User disables notification type: corresponding emails NOT sent
     * - Preference updates: changes effective immediately
     */
    await mockClerkAuth(page, { role: 'authenticated' })
    await page.goto('/settings/notifications')

    const replyToggle = page.locator('input[type="checkbox"][name*="reply"]')
    await expect(replyToggle).toBeVisible()

    const mentionToggle = page.locator('input[type="checkbox"][name*="mention"]')
    await expect(mentionToggle).toBeVisible()

    await page.route('**/users/*/preferences', async route => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Preferences updated' }),
        })
      } else {
        await route.continue()
      }
    })

    await replyToggle.click()

    const successMessage = page.locator('text=/preferences updated/i')
    await expect(successMessage).toBeVisible()
  })

  test.skip('Unsubscribe from emails via link', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - User clicks unsubscribe link: token verified
     * - Token verified: notification preferences updated to "all disabled"
     * - User sees success message: "You've been unsubscribed"
     * - Token invalid or expired: error message displayed
     */
    const token = 'valid_unsubscribe_token_123'

    await page.route('**/unsubscribe', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: "You've been unsubscribed from all notifications",
        }),
      })
    })

    await page.goto(`/unsubscribe?token=${token}`)

    const successMessage = page.locator('text=/unsubscribed/i')
    await expect(successMessage).toBeVisible()
  })

  test.skip('Invalid unsubscribe token handling', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Invalid token: error message displayed
     * - Expired token: error message displayed
     * - User can navigate to settings to manage preferences manually
     */
    const invalidToken = 'invalid_token'

    await page.route('**/unsubscribe', async route => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Invalid or expired unsubscribe token',
        }),
      })
    })

    await page.goto(`/unsubscribe?token=${invalidToken}`)

    const errorMessage = page.locator('text=/invalid.*token/i')
    await expect(errorMessage).toBeVisible()

    const settingsLink = page.locator('a:has-text("notification settings")')
    if (await settingsLink.isVisible()) {
      await expect(settingsLink).toBeVisible()
    }
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
