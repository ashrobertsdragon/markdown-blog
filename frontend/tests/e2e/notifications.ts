import { clerk } from '@clerk/testing/playwright'
import { expect, test } from '@playwright/test'
import { testUserIds } from '../fixtures/test-user-ids'
import { waitForAuthToLoad } from './fixtures/helpers'

const BACKEND = 'http://localhost:5555'
const POST_URL = '/posts/pub-1'

/**
 * Post a comment on the current page and wait for the API response.
 * Returns the comment text used so callers can assert against it.
 */
async function postComment(page: import('@playwright/test').Page, text: string): Promise<string> {
  await page.locator('textarea[name="text"]').fill(text)
  const responsePromise = page.waitForResponse(
    response => response.url().includes('/comments') && response.request().method() === 'POST',
    { timeout: 10000 }
  )
  await page.locator('button[type="submit"]').click()
  await responsePromise
  return text
}

/**
 * Poll GET /api/test/notifications until a notification record exists for the
 * given post slug, or the timeout elapses.
 */
async function waitForNotification(
  page: import('@playwright/test').Page,
  postSlug: string,
  timeoutMs = 10000
): Promise<Record<string, unknown>> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const response = await page.request.get(
      `${BACKEND}/api/test/notifications?post_slug=${postSlug}`
    )
    if (response.ok()) {
      const body = (await response.json()) as { notifications: Record<string, unknown>[] }
      if (body.notifications && body.notifications.length > 0) {
        return body.notifications[0]
      }
    }
    await page.waitForTimeout(500)
  }
  throw new Error(`Timed out waiting for notification for post ${postSlug}`)
}

/**
 * Trigger the background notification processing job via the test helper endpoint.
 */
async function processNotifications(page: import('@playwright/test').Page): Promise<void> {
  const response = await page.request.post(`${BACKEND}/api/test/process-notifications`)
  expect(response.ok()).toBeTruthy()
}

test.describe('Notifications E2E', () => {
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ page }) => {
    const seedResponse = await page.request.post(`${BACKEND}/api/test/seed`, {
      data: {
        author_clerk_id: testUserIds.authorClerkId,
        admin_clerk_id: testUserIds.adminClerkId,
        user_clerk_id: testUserIds.userClerkId,
      },
    })
    expect(seedResponse.ok()).toBeTruthy()

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'user@example.com' })
    await waitForAuthToLoad(page)
  })

  test.afterEach(async ({ page }) => {
    await page.request.delete(`${BACKEND}/api/test/reset`)
  })

  test.describe('Test Group 1: Comment triggers email notification', () => {
    /**
     * Requirements: Req 1 (Notification Queue), Req 3 (Resend Integration),
     * Req 4 (Background Job), Req 9 (Event Triggers)
     */

    test('1.1: Posting a comment creates a pending notification record', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      const commentText = 'Notification E2E test comment'
      await postComment(page, commentText)

      await expect(page.locator('section[aria-label="Comments"]')).toContainText(commentText)

      const listResponse = await page.request.get(
        `${BACKEND}/api/test/notifications?post_slug=pub-1`
      )
      expect(listResponse.ok()).toBeTruthy()

      const body = (await listResponse.json()) as { notifications: Record<string, unknown>[] }
      expect(body.notifications).toBeDefined()
      expect(body.notifications.length).toBeGreaterThan(0)

      const notification = body.notifications[0]
      expect(notification.status).toBe('pending')
      expect(notification.event_type).toMatch(/comment/i)
    })

    test('1.2: Background job processes notification and marks it sent', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await postComment(page, 'Comment for background job test')

      await processNotifications(page)

      const notification = await waitForNotification(page, 'pub-1')
      expect(notification.status).toBe('sent')
      expect(notification.resend_email_id).toBeTruthy()
      expect(typeof notification.resend_email_id).toBe('string')
    })

    test('1.3: Notification record stores correct recipient and event metadata', async ({
      page,
    }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await postComment(page, 'Metadata verification comment')

      const listResponse = await page.request.get(
        `${BACKEND}/api/test/notifications?post_slug=pub-1`
      )
      expect(listResponse.ok()).toBeTruthy()

      const body = (await listResponse.json()) as { notifications: Record<string, unknown>[] }
      expect(body.notifications.length).toBeGreaterThan(0)

      const notification = body.notifications[0]
      expect(notification.post_id).toBeDefined()
      expect(notification.comment_id).toBeDefined()
      expect(notification.recipient_id).toBeDefined()
      expect(notification.created_at).toBeDefined()
    })
  })

  test.describe('Test Group 2: Unsubscribe workflow', () => {
    /**
     * Requirements: Req 7 (Unsubscribe Functionality)
     */

    test('2.1: Valid unsubscribe token shows success message', async ({ page }) => {
      const tokenResponse = await page.request.get(
        `${BACKEND}/api/test/unsubscribe-token?user_id=1`
      )
      expect(tokenResponse.ok()).toBeTruthy()

      const tokenBody = (await tokenResponse.json()) as { user_id: number; token: string }
      const { user_id, token } = tokenBody

      await page.goto(`/unsubscribe?user_id=${user_id}&token=${token}`)

      const successMessage = page.locator('text=/unsubscribed/i')
      await expect(successMessage).toBeVisible({ timeout: 10000 })
    })

    test('2.2: After unsubscribe, all notification preferences are disabled', async ({ page }) => {
      const tokenResponse = await page.request.get(
        `${BACKEND}/api/test/unsubscribe-token?user_id=1`
      )
      expect(tokenResponse.ok()).toBeTruthy()

      const tokenBody = (await tokenResponse.json()) as { user_id: number; token: string }
      const { user_id, token } = tokenBody

      await page.goto(`/unsubscribe?user_id=${user_id}&token=${token}`)
      await expect(page.locator('text=/unsubscribed/i')).toBeVisible({ timeout: 10000 })

      const prefsResponse = await page.request.get(
        `${BACKEND}/api/test/user-preferences?clerk_user_id=${testUserIds.authorClerkId}`
      )
      expect(prefsResponse.ok()).toBeTruthy()

      const prefs = (await prefsResponse.json()) as {
        notify_on_comment_replies: boolean
        notify_on_mentions: boolean
        notify_on_new_posts: boolean
      }

      expect(prefs.notify_on_comment_replies).toBe(false)
      expect(prefs.notify_on_mentions).toBe(false)
      expect(prefs.notify_on_new_posts).toBe(false)
    })

    test('2.3: Invalid unsubscribe token shows error message', async ({ page }) => {
      const invalidToken = 'a'.repeat(64)
      await page.goto(`/unsubscribe?user_id=1&token=${invalidToken}`)

      const errorMessage = page.locator('[role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 10000 })
      await expect(errorMessage).toContainText(/invalid|expired|error/i)
    })

    test('2.4: Missing token parameter shows validation error', async ({ page }) => {
      await page.goto('/unsubscribe?user_id=1')

      const errorMessage = page.locator('[role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 5000 })
      await expect(errorMessage).toContainText(/token/i)
    })

    test('2.5: Missing user_id parameter shows validation error', async ({ page }) => {
      const validToken = 'b'.repeat(64)
      await page.goto(`/unsubscribe?token=${validToken}`)

      const errorMessage = page.locator('[role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 5000 })
      await expect(errorMessage).toContainText(/user_id/i)
    })
  })

  test.describe('Test Group 3: Preference changes prevent emails', () => {
    /**
     * Requirements: Req 6 (User Preferences), Req 9 (Event Triggers)
     */

    test('3.1: Notification preferences page renders toggles for authenticated user', async ({
      page,
    }) => {
      await clerk.signOut({ page })
      await page.goto('/')
      await clerk.signIn({ page, emailAddress: 'author@example.com' })
      await page.goto('/settings/notifications')
      await waitForAuthToLoad(page)

      const replyToggle = page.locator('input[type="checkbox"]').first()
      await expect(replyToggle).toBeVisible({ timeout: 10000 })

      await expect(page.locator('text=/notify.*repl/i')).toBeVisible()
      await expect(page.locator('text=/notify.*mention/i')).toBeVisible()
    })

    test('3.2: Toggling a preference saves immediately and shows success feedback', async ({
      page,
    }) => {
      await clerk.signOut({ page })
      await page.goto('/')
      await clerk.signIn({ page, emailAddress: 'author@example.com' })
      await page.goto('/settings/notifications')
      await waitForAuthToLoad(page)

      await expect(page.locator('input[type="checkbox"]').first()).toBeVisible({ timeout: 10000 })

      const prefsResponsePromise = page.waitForResponse(
        response =>
          response.url().includes('/notification-preferences') &&
          response.request().method() === 'PUT',
        { timeout: 10000 }
      )

      await page.locator('input[type="checkbox"]').first().click()
      const prefsResponse = await prefsResponsePromise

      expect(prefsResponse.status()).toBe(200)
      await expect(page.locator('[role="alert"]')).toContainText(/saved|updated|preferences/i)
    })

    test('3.3: Disabling comment reply preference prevents notification creation on new comment', async ({
      page,
    }) => {
      const disableResponse = await page.request.put(`${BACKEND}/api/test/user-preferences`, {
        data: {
          clerk_user_id: testUserIds.authorClerkId,
          notify_on_comment_replies: false,
          notify_on_mentions: false,
          notify_on_new_posts: false,
        },
      })
      expect(disableResponse.ok()).toBeTruthy()

      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await postComment(page, 'Comment when preferences disabled')

      await page.waitForTimeout(1000)

      const listResponse = await page.request.get(
        `${BACKEND}/api/test/notifications?post_slug=pub-1`
      )
      expect(listResponse.ok()).toBeTruthy()

      const body = (await listResponse.json()) as { notifications: Record<string, unknown>[] }
      expect(body.notifications).toHaveLength(0)
    })

    test('3.4: Re-enabling a preference allows notifications to be created again', async ({
      page,
    }) => {
      const disableResponse = await page.request.put(`${BACKEND}/api/test/user-preferences`, {
        data: {
          clerk_user_id: testUserIds.authorClerkId,
          notify_on_comment_replies: false,
          notify_on_mentions: false,
          notify_on_new_posts: false,
        },
      })
      expect(disableResponse.ok()).toBeTruthy()

      const enableResponse = await page.request.put(`${BACKEND}/api/test/user-preferences`, {
        data: {
          clerk_user_id: testUserIds.authorClerkId,
          notify_on_comment_replies: true,
          notify_on_mentions: false,
          notify_on_new_posts: false,
        },
      })
      expect(enableResponse.ok()).toBeTruthy()

      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await postComment(page, 'Comment after re-enabling preferences')

      const listResponse = await page.request.get(
        `${BACKEND}/api/test/notifications?post_slug=pub-1`
      )
      expect(listResponse.ok()).toBeTruthy()

      const body = (await listResponse.json()) as { notifications: Record<string, unknown>[] }
      expect(body.notifications.length).toBeGreaterThan(0)
      expect(body.notifications[0].status).toBe('pending')
    })

    test('3.5: Unauthenticated users cannot access notification preferences', async ({ page }) => {
      await clerk.signOut({ page })
      await page.goto('/settings/notifications')
      await waitForAuthToLoad(page)

      const redirectedToLogin = page.url().includes('/login')
      const signInPrompt = page.getByRole('heading', { name: /sign in/i })

      const hasAccessControl = redirectedToLogin || (await signInPrompt.isVisible())
      expect(hasAccessControl).toBe(true)
    })
  })

  test.describe('Test Group 4: Notification deduplication', () => {
    /**
     * Requirement: Req 10 (Notification Deduplication)
     */

    test('4.1: Same comment event does not create duplicate notifications', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await postComment(page, 'Deduplication test comment')

      await page.request.post(`${BACKEND}/api/test/seed`)

      const listResponse = await page.request.get(
        `${BACKEND}/api/test/notifications?post_slug=pub-1`
      )
      expect(listResponse.ok()).toBeTruthy()

      const body = (await listResponse.json()) as { notifications: Record<string, unknown>[] }
      expect(body.notifications.length).toBeLessThanOrEqual(1)
    })
  })
})
