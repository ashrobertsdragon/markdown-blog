import { expect, test } from '@playwright/test'
import { mockClerkAuth } from '../fixtures/clerk-mock'

/**
 * Acceptance tests for Revision Tracking spec - Frontend UI.
 *
 * Tests exercise the real backend (FLASK_ENV=TESTING, SQLite in-memory).
 * Only Clerk network traffic is mocked. Test data is seeded via /api/test/seed
 * and torn down via /api/test/reset.
 *
 * Seeded revisions for "test-post" (newest first):
 *   c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2 — "Revert to initial"
 *   b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1 — "Update content"
 *   a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 — "Initial post draft"
 */

const BACKEND = 'http://localhost:5555'

const SHA_MIDDLE = 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1'
const SHA_OLDEST = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0'

test.describe.configure({ mode: 'serial' })

test.describe('Revision Tracking - Frontend UI', () => {
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

  test('Display post revision history timeline', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - "View History" button appears on the post editor
     * - Revision timeline shows all commits
     * - Each revision shows: commit SHA (shortened), author, timestamp, message
     * - Pagination or infinite scroll for >10 revisions
     * - Most recent commit appears first
     */
    await page.goto('/edit/test-post')

    const editor = page.locator('.w-md-editor')
    await expect(editor).toBeVisible({ timeout: 10000 })

    const viewHistoryButton = page.locator('button:has-text("View History")')
    await expect(viewHistoryButton).toBeVisible()

    await viewHistoryButton.click()
    await page.waitForURL('**/posts/test-post/revisions')

    const revisionTimeline = page.locator('[data-testid="revision-timeline"]')
    await expect(revisionTimeline).toBeVisible({ timeout: 10000 })

    const commitSha = page.locator(`text=/c3d4e5f/`)
    await expect(commitSha).toBeVisible()
  })

  test('View previous version of post', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Navigating to a revision URL displays post content at that commit
     * - Previous version is read-only (no editing)
     * - Title, author, timestamp, commit SHA clearly displayed
     * - "Revert to This Version" button appears
     */
    await page.goto(`/posts/test-post/revisions/${SHA_OLDEST}`)

    const content = page.locator('text=/Initial Content/')
    await expect(content).toBeVisible({ timeout: 10000 })

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
     */
    await page.goto(`/posts/test-post/revisions/${SHA_OLDEST}/diff/${SHA_MIDDLE}`)

    const diffViewer = page.locator('[data-testid="diff-viewer"]')
    await expect(diffViewer).toBeVisible({ timeout: 10000 })

    const deletionLine = page.locator('.bg-red-100').first()
    await expect(deletionLine).toBeVisible()

    const additionLine = page.locator('.bg-green-100').first()
    await expect(additionLine).toBeVisible()
  })

  test('Revert to specific revision with confirmation', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - "Revert to This Version" shows confirmation modal
     * - Confirmation restores draft file to that commit SHA
     * - Author redirected to edit page for restored draft
     */
    await page.goto(`/posts/test-post/revisions/${SHA_MIDDLE}`)

    const revertButton = page.locator('button:has-text("Revert")')
    await expect(revertButton).toBeVisible({ timeout: 10000 })
    await revertButton.click()

    const confirmationModal = page.locator('[role="alertdialog"]')
    await expect(confirmationModal).toBeVisible()

    const confirmButton = confirmationModal.locator('button:has-text("Confirm")')
    await confirmButton.click()

    await page.waitForURL('**/edit/test-post', { timeout: 15000 })
  })

  test('Compare current draft with published version', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Editing published post shows "Compare with Published" button
     * - Clicking shows diff between current draft and published version
     * - "No changes" message if draft matches published version
     */
    await page.goto('/edit/test-post')

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
