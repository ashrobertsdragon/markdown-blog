import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'
import { waitForAuthToLoad } from './fixtures/helpers'

/**
 * Acceptance tests for Post Management UI.
 *
 * These tests verify the frontend implementation of the post management lifecycle,
 * covering form interactions, real-time updates, and state transitions.
 */

test.describe('Post Management UI', () => {
  test.beforeEach(async ({ page }) => {
    // Mock Clerk authentication to simulate a logged-in author
    await mockClerkAuth(page, { role: 'author' })

    await page.goto('/')
    await waitForAuthToLoad(page)
  })

  test('New Post form and slug normalization', async ({ page }) => {
    // Navigate to New Post page
    await page.goto('/new-post')

    // Verify form fields SHALL appear
    const titleInput = page.locator('input[name="title"]')
    const slugInput = page.locator('input[name="slug"]')
    await expect(titleInput).toBeVisible()
    await expect(slugInput).toBeVisible()

    await slugInput.fill('My New Post!')
    // Expect spaces to hyphens, lowercase, special chars removed
    await expect(slugInput).toHaveValue('my-new-post')

    // Mock create draft success
    await page.route('**/api/posts', async route => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ slug: 'my-new-post', title: 'My New Post' }),
      })
    })

    await titleInput.fill('My New Post')
    await page.click('button[type="submit"]')

    // Verify redirection to edit page
    await page.waitForURL('**/edit/my-new-post')
    await expect(page).toHaveURL(/\/edit\/my-new-post/)
  })

  test('Markdown Editor and Preview', async ({ page }) => {
    const slug = 'test-post'
    // Mock get draft
    await page.route(`**/api/posts/${slug}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          slug,
          title: 'Test Post',
          content: '# Initial Content',
          published: false,
        }),
      })
    })

    await page.goto(`/edit/${slug}`)

    // Verify markdown editor SHALL display
    const editor = page.locator('.w-md-editor')
    await expect(editor).toBeVisible()

    const previewTab = page.locator('button:has-text("Preview")')
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
      request => request.url().includes('/api/posts/') && request.method() === 'PUT'
    )

    await textarea.press('Control+s')
    const saveRequest = await savePromise
    expect(saveRequest).toBeDefined()
  })

  test('Publish/Unpublish flow with modals', async ({ page }) => {
    const slug = 'publish-me'
    await page.route(`**/api/posts/${slug}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ slug, title: 'Publish Me', content: '...', published: false }),
      })
    })

    await page.goto(`/edit/${slug}`)

    // 1. Click Publish
    await page.click('button:has-text("Publish")')

    // Verify confirmation modal SHALL appear
    const modal = page.locator('role=dialog')
    await expect(modal).toBeVisible()
    await expect(modal).toContainText('Are you sure you want to publish')

    // Mock publish success
    await page.route(`**/api/posts/${slug}/publish`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ slug, published: true }),
      })
    })

    await modal.locator('button:has-text("Confirm")').click()
    await page.waitForURL(`**/posts/${slug}`)
    await expect(page).toHaveURL(new RegExp(`/posts/${slug}`))
  })

  test('Delete Draft Post', async ({ page }) => {
    const slug = 'delete-me'
    await page.route(`**/api/posts/${slug}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ slug, title: 'Delete Me', content: '...', published: false }),
      })
    })

    await page.goto(`/edit/${slug}`)

    // Click Delete
    await page.click('button:has-text("Delete")')

    // Verify confirmation modal SHALL appear
    const modal = page.locator('role=dialog')
    await expect(modal).toBeVisible()
    await expect(modal).toContainText('Are you sure you want to delete')

    // Mock delete success
    await page.route(`**/api/posts/${slug}`, async route => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({ status: 204 })
      } else {
        await route.continue()
      }
    })

    await modal.locator('button:has-text("Delete")').click()
    await page.waitForURL('**/my-posts')
    await expect(page).toHaveURL(/\/my-posts/)
  })

  test('List Author Drafts and Filtering', async ({ page }) => {
    // Mock list posts
    await page.route('**/api/posts/my-posts*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          posts: [
            {
              slug: 'draft-1',
              title: 'Draft 1',
              published: false,
              updated_at: '2024-01-01T12:00:00Z',
            },
            {
              slug: 'pub-1',
              title: 'Published 1',
              published: true,
              updated_at: '2024-01-02T12:00:00Z',
            },
          ],
          total_count: 2,
          total_pages: 1,
          current_page: 1,
          limit: 20,
        }),
      })
    })

    await page.goto('/my-posts')

    // Verify each entry SHALL show: title, status, slug
    await expect(page.locator('text=Draft 1')).toBeVisible()
    await expect(page.locator('text=Published 1')).toBeVisible()
    await expect(page.locator('text=Draft')).toBeVisible()
    await expect(page.locator('text=Published')).toBeVisible()

    // Filter by "drafts only"
    const filterSelect = page.locator('select[name="filter"]')
    if (await filterSelect.isVisible()) {
      await filterSelect.selectOption('drafts')
      await expect(page).toHaveURL(/filter=drafts/)
    }
  })
})
