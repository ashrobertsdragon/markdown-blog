/**
 * E2E tests for the full image upload workflow.
 *
 * Validates: author uploads image via PostEditor → markdown inserted → post
 * published → img tag with /uploads/ src visible on public post page.
 *
 * The image upload API is intercepted to return a synthetic /uploads/ URL so
 * the test does not require UPLOADS_PATH to be configured in the test env.
 */
import { clerk } from '@clerk/testing/playwright'
import { expect, test } from '@playwright/test'
import { waitForAuthToLoad } from '../acceptance/fixtures/helpers'
import { testUserIds } from '../fixtures/test-user-ids'

const BACKEND = 'http://localhost:5555'
const TEST_SLUG = 'publish-me'

/** Minimal valid 1×1 pixel PNG (red pixel). */
const TEST_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADklEQVQI12P4z8BQDwAEgAF/QualIQAAAABJRU5ErkJggg==',
  'base64'
)

test.describe('Image Upload E2E', () => {
  test.beforeEach(async ({ page }) => {
    const seed = await page.request.post(`${BACKEND}/api/test/seed`, {
      data: {
        author_clerk_id: testUserIds.authorClerkId,
        admin_clerk_id: testUserIds.adminClerkId,
        user_clerk_id: testUserIds.userClerkId,
      },
    })
    expect(seed.ok()).toBeTruthy()

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })
    await waitForAuthToLoad(page)
  })

  test('uploads PNG via ImageUploadButton, inserts markdown, img visible in published post', async ({
    page,
  }) => {
    await page.route(`**/api/posts/${TEST_SLUG}/images`, route => {
      if (route.request().method() === 'POST') {
        void route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ url: `/uploads/${TEST_SLUG}/test.png` }),
        })
      } else {
        void route.continue()
      }
    })

    await page.goto(`/edit/${TEST_SLUG}`)
    await expect(page.locator('.w-md-editor')).toBeVisible({ timeout: 15000 })

    const fileInput = page.locator('input[type="file"][accept="image/*"]')
    await fileInput.setInputFiles({
      name: 'test.png',
      mimeType: 'image/png',
      buffer: TEST_PNG,
    })

    const textarea = page.locator('.w-md-editor-text-input')
    await expect(textarea).toContainText('![', { timeout: 5000 })

    const saveRequest = page.waitForRequest(
      r => r.url().includes(`/api/posts/${TEST_SLUG}`) && r.method() === 'PUT',
      { timeout: 10000 }
    )
    await page.getByRole('button', { name: 'Save' }).click()
    await saveRequest

    await page.click('button:has-text("Publish")')
    const dialog = page.locator('[role="alertdialog"]')
    await expect(dialog).toBeVisible()
    await dialog.locator('button:has-text("Publish")').click()

    await page.waitForURL(`**/posts/${TEST_SLUG}`, { timeout: 15000 })

    await expect(page.locator('img[src*="/uploads/"]')).toBeVisible({ timeout: 10000 })
  })
})
