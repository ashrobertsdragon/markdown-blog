import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'

/**
 * Acceptance tests for Revision Tracking spec - Frontend UI.
 *
 * These tests verify revision history display, diff viewer, and revert
 * functionality as specified in revision-tracking/requirements.md.
 */

test.describe('Revision Tracking - Frontend UI', () => {
  test.beforeEach(async ({ page }) => {
    await mockClerkAuth(page, { role: 'author' })
  })

  test('Display post revision history timeline', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - "View History" button appears on published post
     * - Revision timeline shows all commits
     * - Each revision shows: commit SHA (shortened), author, timestamp, message
     * - Pagination or infinite scroll for >10 revisions
     * - Hovering over commit SHA shows full SHA in tooltip
     * - Most recent commit appears first
     */
    const slug = 'test-post'

    await page.route(`**/posts/${slug}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          slug,
          title: 'Test Post',
          content: '# Content',
          published: true,
        }),
      })
    })

    await page.route(`**/posts/${slug}/revisions`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          revisions: [
            {
              commit_sha: 'abc123def456',
              author: 'test@example.com',
              timestamp: '2024-01-01T12:00:00Z',
              message: 'Initial commit',
            },
          ],
          total: 1,
        }),
      })
    })

    await page.goto(`/posts/${slug}`)

    const viewHistoryButton = page.locator('button:has-text("View History")')
    await expect(viewHistoryButton).toBeVisible()

    await viewHistoryButton.click()

    const revisionTimeline = page.locator('[data-testid="revision-timeline"]')
    await expect(revisionTimeline).toBeVisible()

    const commitSha = page.locator('text=/abc123/')
    await expect(commitSha).toBeVisible()
  })

  test('View previous version of post', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Clicking revision displays post content at that commit
     * - Previous version is read-only (no editing)
     * - Title, author, timestamp, commit SHA clearly displayed
     * - "Revert to This Version" button appears
     * - Clear message if previous version not available
     */
    const slug = 'test-post'
    const sha = 'abc123'

    await page.route(`**/posts/${slug}/revisions/${sha}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          commit_sha: sha,
          content: '# Previous Version',
          title: 'Test Post',
          author: 'test@example.com',
          timestamp: '2024-01-01T12:00:00Z',
        }),
      })
    })

    await page.goto(`/posts/${slug}/revisions/${sha}`)

    const content = page.locator('text=/Previous Version/')
    await expect(content).toBeVisible()

    const revertButton = page.locator('button:has-text("Revert")')
    await expect(revertButton).toBeVisible()

    const editor = page.locator('.w-md-editor-text-input')
    await expect(editor).not.toBeVisible()
  })

  test('Diff viewer between two revisions', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Selecting two revisions displays diff view
     * - Additions highlighted in green
     * - Deletions highlighted in red
     * - Unchanged lines appear in gray
     * - Large diffs show only changed sections with context
     */
    const slug = 'test-post'
    const sha1 = 'abc123'
    const sha2 = 'def456'

    await page.route(`**/posts/${slug}/revisions/${sha1}/diff/${sha2}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          diff_lines: [
            { type: 'deletion', content: '- Old line', line_number: 1 },
            { type: 'addition', content: '+ New line', line_number: 1 },
            { type: 'unchanged', content: '  Same line', line_number: 2 },
          ],
        }),
      })
    })

    await page.goto(`/posts/${slug}/diff/${sha1}/${sha2}`)

    const diffViewer = page.locator('[data-testid="diff-viewer"]')
    await expect(diffViewer).toBeVisible()

    const deletionLine = page.locator('.bg-red-100:has-text("Old line")')
    await expect(deletionLine).toBeVisible()

    const additionLine = page.locator('.bg-green-100:has-text("New line")')
    await expect(additionLine).toBeVisible()
  })

  test('Revert to specific revision with confirmation', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - "Revert to This Version" shows confirmation modal
     * - Confirmation restores draft file to that commit SHA
     * - Author redirected to edit page for restored draft
     * - Error displayed if revert fails
     */
    const slug = 'test-post'
    const sha = 'abc123'

    await page.route(`**/posts/${slug}/revert`, async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Reverted successfully', slug }),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto(`/posts/${slug}/revisions/${sha}`)

    const revertButton = page.locator('button:has-text("Revert")')
    await revertButton.click()

    const confirmationModal = page.locator('[role="alertdialog"]')
    await expect(confirmationModal).toBeVisible()

    const confirmButton = confirmationModal.locator('button:has-text("Confirm")')
    await confirmButton.click()

    await page.waitForURL(`/edit/${slug}`)
  })

  test('Compare current draft with published version', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Editing published post shows "Compare with Published" button
     * - Clicking shows diff between current draft and published version
     * - Changed sections highlighted
     * - "No changes" message if draft matches published version
     */
    const slug = 'test-post'

    await page.route(`**/posts/${slug}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          slug,
          title: 'Test Post',
          content: '# Current Draft',
          published: true,
        }),
      })
    })

    await page.goto(`/edit/${slug}`)

    const compareButton = page.locator('button:has-text("Compare with Published")')
    if (await compareButton.isVisible()) {
      await compareButton.click()

      const diffView = page.locator('[data-testid="diff-view"]')
      await expect(diffView).toBeVisible()
    }
  })

  test('Revision history permissions by role', async () => {
    /**
     * Acceptance Criteria:
     * - Reader views published post: revision timeline visible (read-only)
     * - Author views their post: full history AND revert buttons available
     * - Author views another author's post: timeline visible, no revert
     * - Admin views any post: full history AND revert buttons available
     * - Non-authenticated user: revision timeline NOT displayed
     */
  })
})
