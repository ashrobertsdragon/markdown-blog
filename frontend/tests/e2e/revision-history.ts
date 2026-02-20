import { expect, test } from '@playwright/test'
import type {
  DiffResponse,
  ListRevisionsResponse,
  RevisionDetail,
  RevisionListItem,
} from '@/types/revision'
import { mockClerkAuth } from '../acceptance/fixtures/clerk-mock'
import { waitForAuthToLoad } from '../acceptance/fixtures/helpers'

/**
 * Mock data generators for revision testing
 */
function createMockRevisions(count: number): RevisionListItem[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `rev_${i}`,
    commit_sha: `abc${123 + i}def456789abcdef0123456789abcdef01234567`.slice(0, 40),
    short_sha: `abc${123 + i}d`,
    author: {
      id: 'user_123',
      name: i === 0 ? 'Jane Doe' : 'John Smith',
    },
    timestamp: new Date(Date.now() - i * 86400000).toISOString(),
    relative_time: i === 0 ? '5 minutes ago' : `${i + 1} days ago`,
    commit_message: i === 0 ? 'Initial post draft' : `Update ${i + 1}`,
    is_revert: i === 2,
  }))
}

function createMockRevisionDetail(overrides?: Partial<RevisionDetail>): RevisionDetail {
  return {
    id: 'rev_0',
    commit_sha: 'abc123def456789abcdef0123456789abcdef01',
    short_sha: 'abc123d',
    author: { id: 'user_123', name: 'Jane Doe' },
    timestamp: new Date().toISOString(),
    commit_message: 'Initial post draft',
    markdown_content: '# Hello World\n\nThis is a test post.',
    html_content: '<h1>Hello World</h1><p>This is a test post.</p>',
    is_current: true,
    is_revert: false,
    ...overrides,
  }
}

function createMockDiff(overrides?: Partial<DiffResponse>): DiffResponse {
  return {
    from_revision: {
      sha: 'older789abcdef0123456789abcdef01234567ab',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
    },
    to_revision: {
      sha: 'abc123def456789abcdef0123456789abcdef01',
      timestamp: new Date().toISOString(),
    },
    diff_lines: [
      {
        type: 'context',
        content: '# Hello World',
        lineNumber: 1,
      },
      {
        type: 'deletion',
        content: 'Old content',
        lineNumber: 2,
      },
      {
        type: 'addition',
        content: 'New content',
        lineNumber: 3,
      },
      {
        type: 'context',
        content: 'More text here',
        lineNumber: 4,
      },
    ],
    ...overrides,
  }
}

/**
 * E2E tests for revision tracking workflow.
 *
 * Verifies timeline display, detail views, diff comparison, revert operations,
 * permission boundaries, and error handling for post revision history.
 */
test.describe.fixme('Revision History E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await mockClerkAuth(page, { role: 'author', userId: 'user_123' })

    
    await page.route('**/api/**', async route => {
      
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })

    await page.goto('/')
    await waitForAuthToLoad(page)
  })

  test.describe('Test Group 1: Revision Timeline Display', () => {
    test('1.1: Loads and displays revision list', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(3)

      await page.route(`**/api/posts/*/revisions*`, async route => {
        const response: ListRevisionsResponse = {
          revisions: mockRevisions,
          total_count: 3,
          has_more: false,
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(response),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const timelineList = page.locator('[data-testid="revision-timeline-list"]')
      await expect(timelineList).toBeVisible()

      for (const revision of mockRevisions) {
        const item = page.locator(`[data-testid="revision-item-${revision.short_sha}"]`)
        await expect(item).toBeVisible()
      }
    })

    test('1.2: Shows correct metadata (SHA, author, timestamp, message)', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(1)
      const revision = mockRevisions[0]

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 1,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const shaElement = page.locator(`[data-testid="revision-sha-${revision.short_sha}"]`)
      await expect(shaElement).toContainText(revision.short_sha)
      await expect(shaElement).toHaveAttribute('title', revision.commit_sha)

      const item = page.locator(`[data-testid="revision-item-${revision.short_sha}"]`)
      await expect(item).toContainText(revision.author.name)
      await expect(item).toContainText(revision.relative_time)
      await expect(item).toContainText(revision.commit_message)
    })

    test('1.3: Displays current badge on current revision', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(3)

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 3,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const currentBadge = page.locator(
        `[data-testid="revision-current-badge-${mockRevisions[0].short_sha}"]`
      )
      await expect(currentBadge).toBeVisible()
      await expect(currentBadge).toContainText('Current')

      const otherBadge = page.locator(
        `[data-testid="revision-current-badge-${mockRevisions[1].short_sha}"]`
      )
      await expect(otherBadge).not.toBeVisible()
    })

    test('1.4: Displays revert badge on revert revisions', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(3)

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 3,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const revertBadge = page.locator(
        `[data-testid="revision-revert-badge-${mockRevisions[2].short_sha}"]`
      )
      await expect(revertBadge).toBeVisible()
      await expect(revertBadge).toContainText('Revert')

      const nonRevertBadge = page.locator(
        `[data-testid="revision-revert-badge-${mockRevisions[0].short_sha}"]`
      )
      await expect(nonRevertBadge).not.toBeVisible()
    })

    test('1.5: Most recent revision appears first', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(3)

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 3,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const firstItem = page.locator('[data-testid="revision-timeline-list"] > li').first()
      await expect(firstItem).toContainText(mockRevisions[0].short_sha)
    })

    test('1.6: Pagination with Load More button', async ({ page }) => {
      const _slug = 'test-post'
      const firstBatch = createMockRevisions(3)
      const secondBatch = createMockRevisions(2).map((r, i) => ({
        ...r,
        short_sha: `xyz${999 + i}e`,
        commit_sha: `xyz${999 + i}e456789abcdef0123456789abcdef01234567`.slice(0, 40),
      }))

      await page.route(`**/api/posts/*/revisions*`, async route => {
        const url = new URL(route.request().url())
        const skip = parseInt(url.searchParams.get('skip') || '0', 10)

        let revisions: RevisionListItem[]
        let hasMore: boolean

        if (skip === 0) {
          revisions = firstBatch
          hasMore = true
        } else {
          revisions = secondBatch
          hasMore = false
        }

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions,
            total_count: 5,
            has_more: hasMore,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const loadMoreButton = page.locator('[data-testid="revision-timeline-load-more"]')
      await expect(loadMoreButton).toBeVisible()

      await loadMoreButton.click()

      for (const revision of secondBatch) {
        const item = page.locator(`[data-testid="revision-item-${revision.short_sha}"]`)
        await expect(item).toBeVisible()
      }
    })
  })

  test.describe('Test Group 2: Revision Detail View', () => {
    test('2.1: Clicking revision opens detail view', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(1)
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 1,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.route(`**/api/posts/*/revisions/${mockRevisions[0].short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const revisionItem = page.locator(
        `[data-testid="revision-item-${mockRevisions[0].short_sha}"]`
      )
      await revisionItem.click()

      const detailArticle = page.locator('[data-testid="revision-detail"]')
      await expect(detailArticle).toBeVisible()
    })

    test('2.2: Detail shows commit message, author, timestamp', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const detail = page.locator('[data-testid="revision-detail"]')
      await expect(detail).toContainText(mockDetail.commit_message)
      await expect(detail).toContainText(mockDetail.author.name)

      const detailText = await detail.textContent()
      expect(detailText).toContain('Author')
      expect(detailText).toContain('Date')
    })

    test('2.3: Detail shows SHA with full SHA in title attribute', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const shaElement = page.locator('[data-testid="revision-detail-sha"]')
      await expect(shaElement).toContainText(mockDetail.short_sha)
      await expect(shaElement).toHaveAttribute('title', mockDetail.commit_sha)
    })

    test('2.4: Detail renders HTML content', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const contentDiv = page.locator('[data-testid="revision-detail-content"]')
      await expect(contentDiv).toContainText('Hello World')
      await expect(contentDiv).toContainText('This is a test post')
    })

    test('2.5: Revert button visible for authors', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await expect(revertButton).toBeVisible()
    })

    test('2.6: Revert button hidden for non-authors', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await mockClerkAuth(page, { role: 'authenticated', userId: 'user_456' })

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)
      await waitForAuthToLoad(page)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await expect(revertButton).not.toBeVisible()
    })
  })

  test.describe('Test Group 3: Diff Viewer', () => {
    test('3.1: Diff displays additions in green (bg-green-50)', async ({ page }) => {
      const _slug = 'test-post'
      const mockDiff = createMockDiff()

      await page.route(`**/api/posts/*/revisions/*/diff/**`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDiff),
        })
      })

      await page.goto(`/posts/test-post/revisions/abc123d/diff/older789`)

      const additionLine = page.locator('[data-testid="diff-line-addition-3"]')
      await expect(additionLine).toHaveClass(/bg-green-50/)
    })

    test('3.2: Diff displays deletions in red (bg-red-50)', async ({ page }) => {
      const _slug = 'test-post'
      const mockDiff = createMockDiff()

      await page.route(`**/api/posts/*/revisions/*/diff/**`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDiff),
        })
      })

      await page.goto(`/posts/test-post/revisions/abc123d/diff/older789`)

      const deletionLine = page.locator('[data-testid="diff-line-deletion-2"]')
      await expect(deletionLine).toHaveClass(/bg-red-50/)
    })

    test('3.3: Diff displays context in gray (bg-gray-50)', async ({ page }) => {
      const _slug = 'test-post'
      const mockDiff = createMockDiff()

      await page.route(`**/api/posts/*/revisions/*/diff/**`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDiff),
        })
      })

      await page.goto(`/posts/test-post/revisions/abc123d/diff/older789`)

      const contextLine = page.locator('[data-testid="diff-line-context-1"]')
      await expect(contextLine).toHaveClass(/bg-gray-50/)
    })

    test('3.4: Line numbers display correctly', async ({ page }) => {
      const _slug = 'test-post'
      const mockDiff = createMockDiff()

      await page.route(`**/api/posts/*/revisions/*/diff/**`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDiff),
        })
      })

      await page.goto(`/posts/test-post/revisions/abc123d/diff/older789`)

      for (const line of mockDiff.diff_lines) {
        if (line.lineNumber !== undefined) {
          const diffLine = page.locator(`[data-testid="diff-line-${line.type}-${line.lineNumber}"]`)
          await expect(diffLine).toBeVisible()
        }
      }
    })

    test('3.5: No changes detected for empty diff', async ({ page }) => {
      const _slug = 'test-post'
      const emptyDiff = createMockDiff({
        diff_lines: [],
      })

      await page.route(`**/api/posts/*/revisions/*/diff/**`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(emptyDiff),
        })
      })

      await page.goto(`/posts/test-post/revisions/abc123d/diff/abc123d`)

      await expect(page.getByText('No changes detected')).toBeVisible()
    })

    test('3.6: Copy button functionality', async ({ page }) => {
      const _slug = 'test-post'
      const mockDiff = createMockDiff()

      await page.route(`**/api/posts/*/revisions/*/diff/**`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDiff),
        })
      })

      await page.goto(`/posts/test-post/revisions/abc123d/diff/older789`)

      const copyButton = page.getByRole('button', { name: /Copy/ })

      await copyButton.click()
      await expect(copyButton).toContainText('Copied!')

      const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
      expect(clipboardText).toContain(mockDiff.diff_lines[0].content)
    })
  })

  test.describe('Test Group 4: Revert Workflow', () => {
    test('4.1: Clicking revert button opens confirmation modal', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const modal = page.getByRole('dialog')
      await expect(modal).toBeVisible()
    })

    test('4.2: Modal shows revision SHA and commit message', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail({
        short_sha: 'abc123d',
        commit_message: 'Important update',
      })

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const modal = page.getByRole('dialog')
      await expect(modal).toContainText('abc123d')
      await expect(modal).toContainText('Important update')
    })

    test('4.3: Modal shows warning text', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const modal = page.getByRole('dialog')
      await expect(modal).toContainText('overwrite the current draft')
      await expect(modal).toContainText('cannot be undone')
    })

    test('4.4: Successful revert operation', async ({ page }) => {
      const slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.route(`**/api/posts/*/revert`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Revert successful',
            new_commit_sha: 'new789abcdef0123456789abcdef0123456789ab',
            redirect_url: `/edit/${slug}`,
          }),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const confirmButton = page.getByRole('dialog').locator('button:has-text("Confirm")')
      await confirmButton.click()

      await page.waitForURL(`**/edit/${slug}`)
    })

    test('4.5: Revert creates new commit', async ({ page }) => {
      const slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      let revertCalled = false
      await page.route(`**/api/posts/*/revert`, async route => {
        revertCalled = true
        const body = JSON.parse(route.request().postData() || '{}')
        expect(body.target_sha).toBe(mockDetail.commit_sha)

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Revert successful',
            new_commit_sha: 'newsha123456789abcdef0123456789abcdef01',
            redirect_url: `/edit/${slug}`,
          }),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const confirmButton = page.getByRole('dialog').locator('button:has-text("Confirm")')
      await confirmButton.click()

      await page.waitForFunction(() => revertCalled)
    })

    test('4.6: Error handling for failed revert (403 Forbidden)', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.route(`**/api/posts/*/revert`, async route => {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'You do not have permission to revert this post',
          }),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const confirmButton = page.getByRole('dialog').locator('button:has-text("Confirm")')
      await confirmButton.click()

      await expect(page.getByRole('alert')).toBeVisible()
    })

    test('4.7: Reverting... state during operation', async ({ page }) => {
      const slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      let revertStarted = false
      await page.route(`**/api/posts/*/revert`, async route => {
        revertStarted = true
        await new Promise(resolve => setTimeout(resolve, 500))
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Revert successful',
            new_commit_sha: 'newsha123456789abcdef0123456789abcdef01',
            redirect_url: `/edit/${slug}`,
          }),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await revertButton.click()

      const confirmButton = page.getByRole('dialog').locator('button:has-text("Confirm")')
      await confirmButton.click()

      await page.waitForFunction(() => revertStarted)
      const revertingButton = page.locator('button:has-text("Reverting...")')
      await expect(revertingButton).toBeVisible()
    })
  })

  test.describe('Test Group 5: Permissions', () => {
    test('5.1: Authors can select revisions', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(2)

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 2,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const revisionItem = page.locator(
        `[data-testid="revision-item-${mockRevisions[1].short_sha}"]`
      )
      await expect(revisionItem).toHaveAttribute('role', 'button')
      await expect(revisionItem).toHaveAttribute('tabindex', '0')
    })

    test('5.2: Non-authors cannot select revisions (read-only)', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(2)

      await mockClerkAuth(page, { role: 'authenticated', userId: 'user_456' })

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 2,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)
      await waitForAuthToLoad(page)

      const revisionItem = page.locator(
        `[data-testid="revision-item-${mockRevisions[1].short_sha}"]`
      )
      await expect(revisionItem).not.toHaveAttribute('role', 'button')
      await expect(revisionItem).not.toHaveAttribute('tabindex', '0')
    })

    test('5.3: Admins can revert posts', async ({ page }) => {
      const _slug = 'test-post'
      const mockDetail = createMockRevisionDetail()

      await mockClerkAuth(page, { role: 'admin', userId: 'user_admin' })

      await page.route(`**/api/posts/*/revisions/${mockDetail.short_sha}*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDetail),
        })
      })

      await page.goto(`/posts/test-post/revisions/${mockDetail.short_sha}`)
      await waitForAuthToLoad(page)

      const revertButton = page.locator('[data-testid="revision-detail-revert-button"]')
      await expect(revertButton).toBeVisible()
    })

    test('5.4: Revision timeline visible to all authenticated users', async ({ page }) => {
      const _slug = 'test-post'
      const mockRevisions = createMockRevisions(2)

      await mockClerkAuth(page, { role: 'authenticated', userId: 'user_reader' })

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: mockRevisions,
            total_count: 2,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)
      await waitForAuthToLoad(page)

      const timelineList = page.locator('[data-testid="revision-timeline-list"]')
      await expect(timelineList).toBeVisible()

      for (const revision of mockRevisions) {
        const item = page.locator(`[data-testid="revision-item-${revision.short_sha}"]`)
        await expect(item).toBeVisible()
      }
    })
  })

  test.describe('Test Group 6: Error Handling & Edge Cases', () => {
    test('6.1: Empty revision history shows "No revisions yet"', async ({ page }) => {
      const slug = 'empty-post'

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: [],
            total_count: 0,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/${slug}/revisions`)

      const emptyState = page.locator('[data-testid="revision-timeline-empty"]')
      await expect(emptyState).toBeVisible()
      await expect(emptyState).toContainText('No revisions yet')
    })

    test('6.2: API error shows error message and retry button', async ({ page }) => {
      const _slug = 'test-post'

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Internal server error',
          }),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const errorState = page.locator('[data-testid="revision-timeline-error"]')
      await expect(errorState).toBeVisible()

      const retryButton = page.locator('[data-testid="revision-timeline-retry"]')
      await expect(retryButton).toBeVisible()
    })

    test('6.3: Loading states display skeletons', async ({ page }) => {
      const _slug = 'test-post'

      await page.route(`**/api/posts/*/revisions*`, async route => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            revisions: createMockRevisions(1),
            total_count: 1,
            has_more: false,
          } as ListRevisionsResponse),
        })
      })

      await page.goto(`/posts/test-post/revisions`)

      const loadingSkeleton = page.locator('[data-testid="revision-timeline-loading"]')
      await expect(loadingSkeleton).toBeVisible()
    })

    test('6.4: Retry button refetches data', async ({ page }) => {
      const _slug = 'test-post'
      let callCount = 0

      await page.route(`**/api/posts/*/revisions*`, async route => {
        callCount++
        if (callCount === 1) {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({
              detail: 'Server error',
            }),
          })
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              revisions: createMockRevisions(1),
              total_count: 1,
              has_more: false,
            } as ListRevisionsResponse),
          })
        }
      })

      await page.goto(`/posts/test-post/revisions`)

      const errorState = page.locator('[data-testid="revision-timeline-error"]')
      await expect(errorState).toBeVisible()

      const retryButton = page.locator('[data-testid="revision-timeline-retry"]')
      await retryButton.click()

      const timelineList = page.locator('[data-testid="revision-timeline-list"]')
      await expect(timelineList).toBeVisible()
    })
  })
})
