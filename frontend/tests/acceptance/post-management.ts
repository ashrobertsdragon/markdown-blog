import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'

const BACKEND = 'http://localhost:5555'

/**
 * Acceptance tests for Post Management UI.
 *
 * Tests exercise the real backend (FLASK_ENV=TESTING, SQLite in-memory).
 * Only Clerk network traffic is mocked. Test data is seeded via /api/test/seed
 * and torn down via /api/test/reset.
 */

test.describe.configure({ mode: 'serial' })

test.describe('Post Management UI', () => {
  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${BACKEND}/api/test/seed`)
    expect(res.ok()).toBeTruthy()
  })

  test.afterAll(async ({ request }) => {
    await request.delete(`${BACKEND}/api/test/reset`)
  })

  test.beforeEach(async ({ page }) => {
    await mockClerkAuth(page, { role: 'author' })
  })

  test.skip('New Post form and slug normalization', async ({ page }) => {
    await page.goto('/new-post')
  })

  test('Markdown Editor and Preview', async ({ page }) => {
    const slug = 'test-post'
    await page.goto(`/edit/${slug}`)

    const editor = page.locator('.w-md-editor')
    await expect(editor).toBeVisible({ timeout: 15000 })

    const previewTab = page.locator('button:has-text("Preview")').first()
    if (await previewTab.isVisible()) {
      await previewTab.click()
      const previewPane = page.locator('.w-md-editor-preview')
      await expect(previewPane).toContainText('Initial Content')
      await expect(previewPane.locator('h1')).toBeVisible()
    }

    const textarea = page.locator('.w-md-editor-text-input')
    await textarea.fill('# Updated Title')

    if (await previewTab.isVisible()) {
      await expect(page.locator('.w-md-editor-preview')).toContainText('Updated Title')
    }

    const savePromise = page.waitForRequest(
      request => request.url().includes('/posts/') && request.method() === 'PUT'
    )

    await textarea.press('Control+s')
    const saveRequest = await savePromise
    expect(saveRequest).toBeDefined()
  })

  test('Publish/Unpublish flow with modals', async ({ page }) => {
    const slug = 'publish-me'
    await page.goto(`/edit/${slug}`)

    await page.click('button:has-text("Publish")')

    const modal = page.locator('role=alertdialog')
    await expect(modal).toBeVisible()
    await expect(modal).toContainText('Are you sure you want to publish')

    await modal.locator('button:has-text("Publish")').click()
    await page.waitForURL(`**/posts/${slug}`)
    await expect(page).toHaveURL(new RegExp(`/posts/${slug}`))
  })

  test('Delete Draft Post', async ({ page }) => {
    await page.goto('/my-posts')

    const draftRow = page.locator('tr', { hasText: 'Delete Me' })
    await draftRow.getByRole('button', { name: /^delete post/i }).click()

    const modal = page.getByRole('alertdialog')
    await expect(modal).toBeVisible()
    await expect(modal).toContainText('Are you sure you want to delete')

    await modal.getByRole('button', { name: /delete/i }).click()
    await expect(modal).not.toBeVisible()

    await expect(page.getByText('Delete Me')).not.toBeVisible()
    await expect(page.getByRole('table')).toBeVisible()
  })

  test('List Author Drafts and Filtering', async ({ page }) => {
    await page.goto('/my-posts')
    await page.waitForLoadState('networkidle')

    await expect(page.locator('text=Draft 1')).toBeVisible()
    await expect(page.locator('text=Published 1')).toBeVisible()

    await expect(page.getByRole('cell', { name: 'Draft', exact: true }).first()).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Published', exact: true }).first()).toBeVisible()

    const draftsButton = page.locator('button:has-text("Drafts")')
    if (await draftsButton.isVisible()) {
      await draftsButton.click()
      await expect(draftsButton).toHaveAttribute('aria-pressed', 'true')
    }
  })
})
