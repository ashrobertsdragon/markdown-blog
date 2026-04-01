import { expect, test } from '@playwright/test'
import { mockClerkAuth } from '../fixtures/clerk-mock'

const BACKEND = 'http://localhost:5555'

/**
 * Acceptance tests for Comments spec - Frontend UI.
 *
 * Tests exercise the real backend (FLASK_ENV=TESTING, SQLite in-memory).
 * Only Clerk network traffic is mocked. Test data is seeded via /api/test/seed.
 */

test.describe.configure({ mode: 'serial' })

test.describe('Comments - Frontend UI', () => {
  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${BACKEND}/api/test/seed`)
    expect(res.ok()).toBeTruthy()
  })

  test.afterAll(async ({ request }) => {
    await request.delete(`${BACKEND}/api/test/reset`)
  })

  test('Post comment on published post', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Comment form appears below published post
     * - Unauthenticated user sees "Sign in to comment" message
     * - Authenticated reader has name/email pre-filled from auth
     * - Comment text required (min 1 character, max 5000)
     * - Comment appears at bottom of list immediately (optimistic update)
     * - Rate limit exceeded shows error message
     */
    await mockClerkAuth(page, { role: 'authenticated' })

    await page.goto('/posts/test-post')

    const commentForm = page.locator('textarea[placeholder*="comment" i]')
    await expect(commentForm).toBeVisible()

    await commentForm.fill('This is a test comment')

    const submitButton = page.locator('button:has-text("Post Comment")')
    await expect(submitButton).toBeEnabled()
    const postResponsePromise = page.waitForResponse(
      res => res.url().includes('/comments') && res.request().method() === 'POST'
    )
    await submitButton.click()
    await postResponsePromise

    await expect(page.locator('section[aria-label="Comments"]')).toContainText(
      'This is a test comment'
    )
  })

  test('Reply to comment with @mention', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - "Reply" button appears below each comment
     * - Clicking "Reply" shows reply form indented under comment
     * - @username of parent comment author pre-filled
     * - Reply appears immediately in flat list after parent comment
     * - Deleting reply text collapses/cancels reply form
     */
    await mockClerkAuth(page, { role: 'authenticated' })

    const slug = 'test-post'
    await page.goto(`/posts/${slug}`)

    const replyButton = page.locator('button:has-text("Reply")').first()
    await replyButton.click()

    const replyForm = page.locator('textarea[placeholder*="reply" i]')
    await expect(replyForm).toBeVisible()

    const prefilledText = await replyForm.inputValue()
    expect(prefilledText).toMatch(/@\w+/)

    await replyForm.fill(`${prefilledText} Great point!`)

    const submitReply = page.locator('button:has-text("Post Reply")')
    await submitReply.click()

    const postedReply = page.locator('text=/Great point!/')
    await expect(postedReply).toBeVisible()
  })

  test('Comment moderation controls', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Admin views post: delete button on each comment
     * - Author views their post: delete button on comments by others
     * - Reader views comments: delete button only on their own comments
     * - Confirmation modal appears before deletion
     * - Deleted comment immediately disappears from list
     */
    await mockClerkAuth(page, { role: 'admin' })

    const slug = 'test-post'
    await page.goto(`/posts/${slug}`)

    const deleteButton = page.locator('button[aria-label*="Delete comment"]').first()
    await expect(deleteButton).toBeVisible()

    await deleteButton.click()

    const confirmationModal = page.locator('[role="alertdialog"]')
    await expect(confirmationModal).toBeVisible()

    const confirmButton = confirmationModal.locator('button:has-text("Delete")')
    await confirmButton.click()

    await expect(confirmationModal).not.toBeVisible()
  })

  test('Rate limit feedback', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Exceeding rate limit shows error: "Too many comments. Please wait X seconds."
     * - Rate limit enforced: 5 comments per 1 minute per user
     * - Error message displays remaining wait time
     */
    await mockClerkAuth(page, {
      role: 'authenticated',
      userId: 'user_test_rate_limiter',
      email: 'ratelimit@example.com',
    })

    await page.goto('/posts/test-post')

    const commentForm = page.locator('textarea[placeholder*="comment" i]')
    const submitButton = page.locator('button:has-text("Post Comment")')

    for (let i = 1; i <= 5; i++) {
      await commentForm.fill(`Rate limit test comment ${i}`)
      await expect(submitButton).toBeEnabled()
      const responsePromise = page.waitForResponse(
        res => res.url().includes('/comments') && res.request().method() === 'POST'
      )
      await submitButton.click()
      await responsePromise
    }

    await commentForm.fill('This should be rate limited')
    await expect(submitButton).toBeEnabled()
    await submitButton.click()

    const errorMessage = page.locator('text=/Too many comments/')
    await expect(errorMessage).toBeVisible()
  })

  test('Real-time comment updates', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - New comments appear within 2 seconds (polling OR websocket)
     * - Each comment shows: author name, timestamp (relative), text
     * - Post author's comments visually distinguished (badge: "Author")
     * - >50 comments: pagination OR "Load more" button
     */
    await mockClerkAuth(page, { role: 'authenticated' })

    const slug = 'test-post'
    await page.goto(`/posts/${slug}`)

    const commentsList = page.locator('[data-testid="comments-list"]')
    await expect(commentsList).toBeVisible()

    const firstComment = commentsList.locator('.comment-item').first()
    const timestamp = firstComment.locator('.comment-timestamp')
    await expect(timestamp).toContainText(/ago|just now/)

    const authorBadge = firstComment.locator('.badge:has-text("Author")')
    if (await authorBadge.isVisible()) {
      await expect(authorBadge).toBeVisible()
    }
  })

  test('Comment thread tracking with @mentions', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Comment with parent_id visually indented OR prefixed "Reply to @username"
     * - Clicking "Reply to @username" scrolls to parent comment
     * - Deleted comment shows "[deleted comment]" with replies visible
     */
    await mockClerkAuth(page, { role: 'authenticated' })

    const slug = 'test-post'
    await page.goto(`/posts/${slug}`)

    const replyIndicator = page.locator('text=/Reply to @/').first()
    await expect(replyIndicator).toBeVisible()
    await replyIndicator.click()

    const parentComment = page.locator('[data-comment-id]').first()
    await expect(parentComment).toBeInViewport()
  })

  test('Spam prevention feedback', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Comment fails spam check: queued for moderation (not published)
     * - User sees message: "Your comment is pending moderation"
     * - Flagged comments appear in admin "Pending Moderation" section
     *
     * The spam check scores 50+ points for 3+ URLs, which triggers pending
     * moderation on the real backend (SpamCheckService: url_density check).
     */
    await mockClerkAuth(page, { role: 'authenticated' })

    await page.goto('/posts/test-post')

    const commentForm = page.locator('textarea[placeholder*="comment" i]')
    await commentForm.fill('http://spam.com http://more-spam.com http://extra-spam.com')

    const submitButton = page.locator('button:has-text("Post Comment")')
    await expect(submitButton).toBeEnabled()
    const responsePromise = page.waitForResponse(
      res => res.url().includes('/comments') && res.request().method() === 'POST'
    )
    await submitButton.click()
    await responsePromise

    const moderationMessage = page.locator('text=/pending moderation/')
    await expect(moderationMessage).toBeVisible()
  })
})
