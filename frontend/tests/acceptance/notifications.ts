import { expect, test } from '@playwright/test'
import { waitForAuthToLoad } from '../e2e/fixtures/helpers'
import { mockClerkAuth } from '../fixtures/clerk-mock'

const BACKEND = 'http://localhost:5555'

/**
 * Acceptance tests for Notifications spec - Frontend UI.
 *
 * Tests exercise the real backend (FLASK_ENV=TESTING, SQLite in-memory).
 * Only Clerk network traffic is mocked. Test data is seeded via /api/test/seed.
 */

test.describe.configure({ mode: 'serial' })

test.describe('Notifications - Frontend UI', () => {
  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${BACKEND}/api/test/seed`)
    expect(res.ok()).toBeTruthy()
  })

  test.afterAll(async ({ request }) => {
    await request.delete(`${BACKEND}/api/test/reset`)
  })

  test('User notification preferences settings', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - User visits notification settings: sees toggles for notification types
     * - All 3 toggles enabled by default (reply, mention, new post)
     * - User disables a preference: change persists after page reload
     * - Other preferences remain unaffected
     */
    await mockClerkAuth(page, { role: 'author' })
    await page.goto('/settings/notifications')
    await waitForAuthToLoad(page)

    const replyCheckbox = page.getByLabel('Notify on comment replies')
    await expect(replyCheckbox).toBeVisible({ timeout: 10000 })
    await expect(replyCheckbox).toBeChecked()
    await expect(page.locator('input[type="checkbox"]')).toHaveCount(3)

    await replyCheckbox.uncheck()
    await expect(page.locator('[role="alert"]')).toContainText(/Preferences saved/i, {
      timeout: 10000,
    })

    await page.reload()
    await waitForAuthToLoad(page)
    await expect(page.getByLabel('Notify on comment replies')).not.toBeChecked({ timeout: 10000 })
    await expect(page.getByLabel('Notify on mentions')).toBeChecked()
    await expect(page.getByLabel('Notify on new posts')).toBeChecked()
  })

  test('Unsubscribe from emails via link', async ({ page, request }) => {
    /**
     * Acceptance Criteria:
     * - User navigates to unsubscribe URL with valid HMAC token
     * - Backend verifies token and disables all notification preferences
     * - Success message: "You've been unsubscribed"
     */
    const tokenRes = await request.get(`${BACKEND}/api/test/unsubscribe-token?user_id=1`)
    expect(tokenRes.ok()).toBeTruthy()
    const { user_id, token } = await tokenRes.json()

    await page.goto(`/unsubscribe?user_id=${user_id}&token=${token}`)
    await expect(page.locator('[role="alert"]')).toContainText(/unsubscribed/i, { timeout: 10000 })
  })

  test('Invalid unsubscribe token handling', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Token failing client-side format check: immediate error, no API call
     * - Error message explains the token is invalid
     */
    await page.goto('/unsubscribe?user_id=1&token=invalid_token')
    await expect(page.locator('[role="alert"]')).toContainText(/invalid.*token/i)
  })
})
