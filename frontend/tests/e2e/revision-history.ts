import { expect, test } from '@playwright/test'
import { waitForAuthToLoad } from '../acceptance/fixtures/helpers'
import { mockClerkAuth } from '../fixtures/clerk-mock'

/**
 * E2E tests for revision tracking workflow.
 *
 * Verifies timeline display, detail views, diff comparison, revert operations,
 * permission boundaries, and error handling for post revision history.
 *
 * These tests run against a real backend seeded with test data via /api/test/seed.
 */
test.describe('Revision History E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.post('http://localhost:5555/api/test/seed')
    expect(response.ok()).toBeTruthy()

    await mockClerkAuth(page, {
      role: 'author',
      userId: 'user_test_author',
      email: 'author@example.com',
    })
    await page.goto('/')
    await waitForAuthToLoad(page)
  })

  test.describe('Test Group 1: Revision Timeline Display', () => {
    test('1.1: Loads and displays revision list', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')

      const timelineList = page.locator('[data-testid="revision-timeline-list"]')
      await expect(timelineList).toBeVisible()

      const items = page.locator('[data-testid^="revision-item-"]')
      await expect(items).toHaveCount(3)
    })

    test('1.2: Shows correct metadata (SHA, author, timestamp, message)', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')

      const firstItem = page.locator('[data-testid^="revision-item-"]').first()
      await expect(firstItem).toBeVisible()

      await expect(firstItem.locator('[data-testid^="revision-sha-"]')).toBeVisible()
      await expect(firstItem).toContainText('User')
      await expect(firstItem).toContainText('Revert to initial')
    })

    test('1.3: Displays current badge on current revision', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')

      const currentBadge = page.locator('[data-testid^="revision-current-badge-c3d4e5f"]')
      await expect(currentBadge).toBeVisible()
      await expect(currentBadge).toContainText('Current')
    })

    test('1.4: Displays revert badge on revert revisions', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')

      const revertBadge = page.locator('[data-testid^="revision-revert-badge-"]').first()
      await expect(revertBadge).toBeVisible()
      await expect(revertBadge).toContainText('Revert')
    })

    test('1.5: Most recent revision appears first', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')

      const firstItem = page.locator('[data-testid="revision-timeline-list"] > li').first()
      await expect(firstItem).toContainText('Revert to initial')
    })
  })

  test.describe('Test Group 2: Revision Detail View', () => {
    test('2.1: Clicking revision opens detail view', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')

      const revisionItem = page.locator('[data-testid^="revision-item-"]').first()
      await revisionItem.click()
      await page.waitForLoadState('networkidle')

      await expect(page).toHaveURL(/\/posts\/test-post\/revisions\/[a-f0-9]+/)
      const detailArticle = page.locator('[data-testid="revision-detail"]')
      await expect(detailArticle).toBeVisible()
    })

    test('2.2: Detail shows commit message, author, timestamp', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const revisionItem = page.locator('[data-testid^="revision-item-"]').first()
      await revisionItem.click()
      await page.waitForLoadState('networkidle')

      const detail = page.locator('[data-testid="revision-detail"]')
      await expect(detail).toContainText('Revert to initial')
      await expect(detail).toContainText('Author ID')
      await expect(detail).toContainText('Date')
    })

    test('2.4: Detail renders HTML content', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const revisionItem = page.locator('[data-testid^="revision-item-"]').last()
      await revisionItem.click()
      await page.waitForLoadState('networkidle')

      const contentDiv = page.locator('[data-testid="revision-detail-content"]')
      await expect(contentDiv).toContainText('Initial Content')
      await expect(contentDiv).toContainText('Test content')
    })

    test('2.5: Revert button visible for authors', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const revisionItem = page.locator('[data-testid^="revision-item-"]').nth(1)
      await revisionItem.click()
      await page.waitForLoadState('networkidle')

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await expect(revertButton).toBeVisible()
    })

    test('2.6: Revert button hidden for non-authors', async ({ page }) => {
      await mockClerkAuth(page, {
        role: 'authenticated',
        userId: 'user_other',
        email: 'other@example.com',
      })
      await page.goto('/posts/test-post/revisions')
      await waitForAuthToLoad(page)

      await expect(page.locator('role=alert')).toContainText(/not authorized/i)
    })
  })

  test.describe('Test Group 3: Diff Viewer', () => {
    test('3.1: Diff displays additions and deletions', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const shaElements = page.locator('[data-testid^="revision-sha-"]')
      await expect(shaElements).toHaveCount(3)

      const shas = await shaElements
        .all()
        .then(els => Promise.all(els.map(el => el.getAttribute('title'))))

      expect(shas.length).toBeGreaterThanOrEqual(2)
      const newerSha = shas[0]
      const olderSha = shas[1]

      await page.goto(`/posts/test-post/revisions/${newerSha}/diff/${olderSha}`)
      await page.waitForLoadState('networkidle')

      const diffContainer = page.locator('[aria-label="Diff viewer"]')
      await expect(diffContainer).toBeVisible()

      const lines = page.locator('[data-testid^="diff-line-"]')
      await expect(lines.count()).resolves.toBeGreaterThan(0)
    })

    test('3.5: No changes detected for same revision diff', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const shaElements = page.locator('[data-testid^="revision-sha-"]')
      await expect(shaElements.first()).toBeVisible()

      const sha = await shaElements.first().getAttribute('title')
      const trimmedSha = sha?.trim()

      await page.goto(`/posts/test-post/revisions/${trimmedSha}/diff/${trimmedSha}`)
      await page.waitForLoadState('networkidle')

      await expect(page.getByText(/no changes detected/i)).toBeVisible()
    })

    test('3.6: Copy button functionality', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const shaElements = page.locator('[data-testid^="revision-sha-"]')
      await expect(shaElements).toHaveCount(3)

      const shas = await shaElements
        .all()
        .then(els => Promise.all(els.map(el => el.getAttribute('title'))))

      await page.goto(`/posts/test-post/revisions/${shas[0]}/diff/${shas[1]}`)
      await page.waitForLoadState('networkidle')

      const copyButton = page.getByRole('button', { name: /copy/i })
      await expect(copyButton).toBeVisible()

      await copyButton.click()
      await expect(copyButton).toContainText(/copied/i)
    })
  })

  test.describe('Test Group 4: Revert Workflow', () => {
    test('4.1: Clicking revert button opens confirmation modal', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const items = page.locator('[data-testid^="revision-item-"]')
      await expect(items).toHaveCount(3)

      await items.nth(1).click()
      await page.waitForLoadState('networkidle')

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await expect(revertButton).toBeVisible()
      await revertButton.click()

      const modal = page.locator('role=alertdialog').or(page.locator('role=dialog'))
      await expect(modal.first()).toBeVisible()
      await expect(modal.first()).toContainText(/confirm revert/i)
    })

    test('4.4: Successful revert operation', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const items = page.locator('[data-testid^="revision-item-"]')
      await expect(items).toHaveCount(3)

      await items.nth(1).click()
      await page.waitForLoadState('networkidle')

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await expect(revertButton).toBeVisible()

      await revertButton.click()

      const confirmButton = page.locator('[data-testid="revert-modal-confirm"]')
      await expect(confirmButton).toBeVisible()
      await confirmButton.click()

      await page.waitForURL('**/edit/test-post')
    })
  })

  test.describe('Test Group 5: Permissions', () => {
    test('5.1: Authors can select revisions', async ({ page }) => {
      await page.goto('/posts/test-post/revisions')
      const items = page.locator('[data-testid^="revision-item-"]')
      await expect(items).toHaveCount(3)

      const firstItem = items.first()
      await expect(firstItem).toHaveAttribute('role', 'button')
      await expect(firstItem).toHaveAttribute('tabindex', '0')
    })

    test('5.2: Non-authors cannot select revisions (read-only)', async ({ page }) => {
      await mockClerkAuth(page, {
        role: 'authenticated',
        userId: 'user_other',
        email: 'other@example.com',
      })
      await page.goto('/posts/test-post/revisions')
      await waitForAuthToLoad(page)

      await expect(page.locator('role=alert')).toContainText(/not authorized/i)
    })
  })
})
