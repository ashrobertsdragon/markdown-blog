import { expect, test } from '@playwright/test'
import { waitForAuthToLoad } from '../acceptance/fixtures/helpers'
import { mockClerkAuth, mockClerkUnauthenticated } from '../fixtures/clerk-mock'
import { waitForApiCall } from './fixtures/helpers'

const POST_URL = '/posts/pub-1'

/**
 * Seeds a comment by filling and submitting the comment form via the UI.
 *
 * Waits for the API call to complete and then verifies the comment text
 * appears in the comments section before resolving.
 */
async function seedCommentViaUi(page: import('@playwright/test').Page, text: string) {
  await page.locator('textarea[name="text"]').fill(text)
  await page.locator('button[type="submit"]').click()
  await waitForApiCall(page, '/comments', 5000)
  await expect(page.locator('section[aria-label="Comments"]')).toContainText(text)
}

test.describe('Comments E2E Tests', () => {
  // beforeEach reseeds the database and resets rate limiter counters.
  // Rate limiting is user-scoped, so user_test_commenter starts fresh each test.
  test.beforeEach(async ({ page }) => {
    const response = await page.request.post('http://localhost:5555/api/test/seed')
    expect(response.ok()).toBeTruthy()

    await mockClerkAuth(page, {
      role: 'authenticated',
      userId: 'user_test_commenter',
      email: 'commenter@example.com',
    })
    await page.goto('/')
    await waitForAuthToLoad(page)
  })

  test.describe('Test Group 1: Post Comment', () => {
    test('1.1: Comment form appears on published post for authenticated user', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()
      await expect(page.locator('button[type="submit"]')).toBeVisible()
      await expect(page.getByText('Sign in to comment')).not.toBeVisible()
    })

    test('1.2: Unauthenticated user sees sign-in prompt instead of form', async ({ page }) => {
      await mockClerkUnauthenticated(page)
      await page.goto(POST_URL)
      await waitForAuthToLoad(page)

      await expect(page.getByText('Sign in to comment')).toBeVisible()
      await expect(page.locator('textarea[name="text"]')).not.toBeVisible()
    })

    test('1.3: Authenticated user can submit a comment', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      const commentText = 'This is a test comment'
      await page.locator('textarea[name="text"]').fill(commentText)

      const commentsResponsePromise = page.waitForResponse(
        response => response.url().includes('/comments') && response.request().method() === 'POST'
      )
      await page.locator('button[type="submit"]').click()
      await commentsResponsePromise

      await expect(page.locator(`section[aria-label="Comments"]`)).toContainText(commentText)
    })

    test('1.4: Comment form validates minimum length', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      const submitButton = page.locator('button[type="submit"]')
      await expect(submitButton).toBeDisabled()

      await page.locator('textarea[name="text"]').fill('Hello')
      await expect(submitButton).toBeEnabled()
    })

    test('1.5: Comment form shows character count', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await page.locator('textarea[name="text"]').fill('Hello world')

      await expect(page.locator('text=/11\\s*\\/\\s*5000/')).toBeVisible()
    })
  })

  test.describe('Test Group 2: Reply to Comment', () => {
    test('2.1: Reply button appears on each comment', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Seed comment for reply button test')

      await expect(page.locator('button:has-text("Reply")').first()).toBeVisible()
    })

    test('2.2: Clicking Reply opens inline reply form', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Seed comment for reply form test')

      await page.locator('button:has-text("Reply")').first().click()

      await expect(page.locator('[data-testid="reply-form"]')).toBeVisible()
    })

    test('2.3: Reply form pre-fills with @mention of parent author', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Seed comment for mention test')

      await page.locator('button:has-text("Reply")').first().click()

      const replyTextarea = page.locator('textarea[name="reply-text"]')
      await expect(replyTextarea).toBeVisible()

      const prefillValue = await replyTextarea.inputValue()
      expect(prefillValue).toMatch(/^@\w+/)
    })

    test('2.4: Reply can be submitted and appears in comment list', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Parent comment for reply submission test')

      await page.locator('button:has-text("Reply")').first().click()

      const replyTextarea = page.locator('textarea[name="reply-text"]')
      await replyTextarea.fill('This is a reply response')

      const replyResponsePromise = page.waitForResponse(
        response => response.url().includes('/reply') && response.request().method() === 'POST'
      )
      await page.locator('[data-testid="reply-form"] button[type="submit"]').click()
      await replyResponsePromise

      await expect(page.locator('section[aria-label="Comments"]')).toContainText(
        'This is a reply response'
      )
    })

    test('2.5: Cancel button closes reply form without submitting', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Seed comment for cancel test')

      await page.locator('button:has-text("Reply")').first().click()
      await expect(page.locator('[data-testid="reply-form"]')).toBeVisible()

      await page.locator('[data-testid="reply-form"] button:has-text("Cancel")').click()

      await expect(page.locator('[data-testid="reply-form"]')).not.toBeVisible()
    })
  })

  test.describe('Test Group 3: Rate Limiting', () => {
    test.setTimeout(60000)

    test('3.1: User can post up to 5 comments successfully', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      for (let i = 1; i <= 5; i++) {
        const textarea = page.locator('textarea[name="text"]')
        await textarea.fill(`Rate limit test comment ${i}`)

        const submitResponsePromise = page.waitForResponse(
          response => response.url().includes('/comments') && response.request().method() === 'POST'
        )
        await page.locator('button[type="submit"]').click()
        const submitResponse = await submitResponsePromise

        expect(submitResponse.status()).toBe(201)
        await expect(page.locator('[role="alert"]')).not.toBeVisible()
      }

      const commentSection = page.locator('section[aria-label="Comments"]')
      for (let i = 1; i <= 5; i++) {
        await expect(commentSection).toContainText(`Rate limit test comment ${i}`)
      }
    })

    test('3.2: 6th comment triggers rate limit error', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      for (let i = 1; i <= 5; i++) {
        const textarea = page.locator('textarea[name="text"]')
        await textarea.fill(`Comment number ${i}`)
        const responsePromise = page.waitForResponse(
          response => response.url().includes('/comments') && response.request().method() === 'POST'
        )
        await page.locator('button[type="submit"]').click()
        await responsePromise
      }

      await page.locator('textarea[name="text"]').fill('This should be rate limited')
      const rateLimitResponsePromise = page.waitForResponse(
        response => response.url().includes('/comments') && response.request().method() === 'POST'
      )
      await page.locator('button[type="submit"]').click()
      const rateLimitResponse = await rateLimitResponsePromise

      expect(rateLimitResponse.status()).toBe(429)
      await expect(page.locator('[role="alert"]')).toBeVisible()
      await expect(page.locator('[role="alert"]')).toContainText(/wait|rate/i)
    })

    test('3.3: Rate limit error displays wait time', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      for (let i = 1; i <= 5; i++) {
        await seedCommentViaUi(page, `Flood comment ${i}`)
      }

      await page.locator('textarea[name="text"]').fill('Trigger rate limit for wait time')
      const rateLimitResponsePromise = page.waitForResponse(
        response => response.url().includes('/comments') && response.request().method() === 'POST'
      )
      await page.locator('button[type="submit"]').click()
      await rateLimitResponsePromise

      const errorAlert = page.locator('[role="alert"]')
      await expect(errorAlert).toBeVisible()

      const errorText = await errorAlert.textContent()
      expect(errorText).toMatch(/\d+/)
    })

    test('3.4: Reply endpoint is also rate limited after flooding replies', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Base comment for reply rate limit test')

      for (let i = 1; i <= 4; i++) {
        await page.locator('button:has-text("Reply")').first().click()
        const replyForm = page.locator('[data-testid="reply-form"]')
        await expect(replyForm).toBeVisible()
        const replyTextarea = replyForm.locator('textarea[name="reply-text"]')
        const replyText = `Rate limit reply ${i}`
        await replyTextarea.fill(replyText)
        const replyResponsePromise = page.waitForResponse(
          response => response.url().includes('/reply') && response.request().method() === 'POST'
        )
        await replyForm.locator('button[type="submit"]').click()
        const replyResponse = await replyResponsePromise
        expect(replyResponse.status()).toBe(201)
        await expect(page.locator('section[aria-label="Comments"]')).toContainText(replyText)
      }

      await page.locator('button:has-text("Reply")').first().click()
      const replyForm = page.locator('[data-testid="reply-form"]')
      await expect(replyForm).toBeVisible()
      const replyTextarea = replyForm.locator('textarea[name="reply-text"]')
      await replyTextarea.fill('This reply should be rate limited')
      const rateLimitResponsePromise = page.waitForResponse(
        response => response.url().includes('/reply') && response.request().method() === 'POST'
      )
      await replyForm.locator('button[type="submit"]').click()
      const rateLimitResponse = await rateLimitResponsePromise

      expect(rateLimitResponse.status()).toBe(429)
      const errorAlert = page.locator('[role="alert"]')
      await expect(errorAlert).toBeVisible()
      await expect(errorAlert).toContainText(/wait|rate/i)
      await expect(errorAlert).toContainText(/\d+/)
    })
  })

  test.describe('Test Group 4: Comment Moderation', () => {
    test('4.1: Comment author can see delete button on own comment', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'My own comment to delete')

      const commentsSection = page.locator('section[aria-label="Comments"]')
      await expect(commentsSection.locator('button:has-text("Delete")').first()).toBeVisible()
    })

    test('4.2: Admin can delete a comment (soft delete)', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Comment that admin will delete')

      await mockClerkAuth(page, {
        role: 'admin',
        userId: 'user_test_admin',
        email: 'admin@example.com',
      })
      await page.reload()
      await waitForAuthToLoad(page)
      await expect(page.locator('section[aria-label="Comments"]')).toBeVisible()

      await page.locator('button[aria-label="Delete comment"]').first().click()

      const confirmDialog = page.locator('[role="alertdialog"]')
      await expect(confirmDialog).toBeVisible()

      const deleteResponsePromise = page.waitForResponse(
        response =>
          response.url().includes('/comments/') && response.request().method() === 'DELETE'
      )
      await confirmDialog.locator('button:has-text("Delete")').click()
      await deleteResponsePromise

      await expect(confirmDialog).not.toBeVisible()

      await expect(
        page.locator('section[aria-label="Comments"]').locator('text=[deleted]')
      ).toBeVisible()
    })

    test('4.4: Non-admin users do not see [deleted] placeholder after soft delete', async ({
      page,
    }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Comment to be soft deleted by admin')

      await mockClerkAuth(page, {
        role: 'admin',
        userId: 'user_test_admin',
        email: 'admin@example.com',
      })
      await page.reload()
      await waitForAuthToLoad(page)

      await expect(page.locator('[role="alertdialog"]')).not.toBeVisible()

      await page.locator('button[aria-label="Delete comment"]').first().click()

      const confirmDialog = page.locator('[role="alertdialog"]')
      await expect(confirmDialog).toBeVisible()

      const deleteResponsePromise = page.waitForResponse(
        response =>
          response.url().includes('/comments/') && response.request().method() === 'DELETE'
      )
      await confirmDialog.locator('button:has-text("Delete")').click()
      await deleteResponsePromise

      await expect(confirmDialog).not.toBeVisible()

      await mockClerkUnauthenticated(page)
      await page.reload()
      await waitForAuthToLoad(page)

      await expect(page.locator('text=[deleted]')).not.toBeVisible()
    })

    test('4.3: Unauthenticated users cannot see delete button', async ({ page }) => {
      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      await seedCommentViaUi(page, 'Comment visible to anonymous users')

      await mockClerkUnauthenticated(page)
      await page.reload()
      await waitForAuthToLoad(page)
      await expect(page.locator('section[aria-label="Comments"]')).toBeVisible()

      await expect(page.locator('button:has-text("Delete")')).not.toBeVisible()
    })
  })

  test.describe('Test Group 5: Author Badge', () => {
    test('5.1: Post author comments show Author badge', async ({ page }) => {
      await mockClerkAuth(page, {
        role: 'author',
        userId: 'user_test_author',
        email: 'author@example.com',
      })
      await page.goto('/')
      await waitForAuthToLoad(page)

      await page.goto(POST_URL)
      await expect(page.locator('textarea[name="text"]')).toBeVisible()

      const textarea = page.locator('textarea[name="text"]')
      await textarea.fill('Author posting on their own post')
      const responsePromise = page.waitForResponse(
        response => response.url().includes('/comments') && response.request().method() === 'POST'
      )
      await page.locator('button[type="submit"]').click()
      await responsePromise

      await expect(
        page.locator('section[aria-label="Comments"]').locator('text=Author').first()
      ).toBeVisible()
    })
  })
})
