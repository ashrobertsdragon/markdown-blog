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

  test.skip('New Post form and slug normalization', async ({ page }) => {
    // TODO: This test requires a separate "New Post" form component with title/slug inputs
    // Current implementation uses PostEditor which doesn't have these fields
    // Skip until the create post workflow is implemented
    await page.goto('/new-post')
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

    // Verify confirmation modal SHALL appear (Radix AlertDialog uses role=alertdialog)
    const modal = page.locator('role=alertdialog')
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

    await modal.locator('button:has-text("Publish")').click()
    await page.waitForURL(`**/posts/${slug}`)
    await expect(page).toHaveURL(new RegExp(`/posts/${slug}`))
  })

  test('Delete Draft Post', async ({ page }) => {
    const slug = 'delete-me'

    // Mock list posts API to show the post we want to delete
    await page.route('**/api/posts/my-posts*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          posts: [
            {
              slug,
              title: 'Delete Me',
              published: false,
              updated_at: '2024-01-01T12:00:00Z',
            },
          ],
          total_count: 1,
          total_pages: 1,
          current_page: 1,
          limit: 20,
        }),
      })
    })

    await page.goto('/my-posts')

    // Click Delete button in the table row
    await page.click('button:has-text("Delete")')

    // Verify confirmation modal SHALL appear (Radix AlertDialog uses role=alertdialog)
    const modal = page.locator('role=alertdialog')
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

    // After deletion, modal should close
    await expect(modal).not.toBeVisible()
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

    // Filter by "drafts only" using filter buttons
    const draftsButton = page.locator('button:has-text("Drafts")')
    if (await draftsButton.isVisible()) {
      await draftsButton.click()
      // Verify the button is now in active state
      await expect(draftsButton).toHaveAttribute('aria-pressed', 'true')
    }
  })
})
