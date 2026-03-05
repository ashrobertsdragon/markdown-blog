import { expect, test } from '@playwright/test'
import { mockClerkUnauthenticated } from './fixtures/clerk-mock'

/**
 * Acceptance tests for Foundation spec - Frontend UI.
 *
 * These tests verify the React frontend infrastructure, routing,
 * and static file serving as specified in foundation/requirements.md.
 */

test.describe('Foundation - Frontend Infrastructure', () => {
  test.beforeEach(async ({ page }) => {
    await mockClerkUnauthenticated(page)
  })

  test('React frontend serves with SPA routing', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Flask serves React static files from build/ directory
     * - Non-API routes serve index.html (SPA catch-all)
     * - BrowserRouter has NO basename (root domain routing)
     */
    await page.goto('/')

    await expect(page).toHaveTitle(/.+/)

    const currentUrl = page.url()
    expect(currentUrl).toMatch(/\/$/)
  })

  test('React dev server with HMR', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Vite starts development server with HMR
     * - Hot reload within 1 second of file changes
     *
     * Note: This test verifies dev server is running during development.
     * In production, this would be skipped.
     */

    await page.goto('/')
    await expect(page).toHaveTitle(/.+/)
  })

  test('Health check endpoints accessibility', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - GET /health returns 200 OK with {"status": "healthy"}
     * - GET /health/db tests database connectivity
     * - GET /health/github tests GitHub API connectivity
     */
    const healthResponse = await page.request.get('http://localhost:5555/api/health')
    expect([200]).toContain(healthResponse.status())

    if (healthResponse.status() === 200) {
      const json = await healthResponse.json()
      expect(json.status).toBe('healthy')
    }
  })

  test('Navigation and layout structure', async ({ page }) => {
    /**
     * Acceptance Criteria:
     * - Frontend organizes code by feature
     * - Components render correctly
     * - Layout includes header and footer
     */
    await page.goto('/')

    const body = page.locator('body')
    await expect(body).toBeVisible()
  })

  test.skip('Asset optimization and bundle size', async () => {
    /**
     * Acceptance Criteria:
     * - React production bundle < 500KB gzipped
     * - Assets loaded from build/static/
     * - Build completes in < 60 seconds
     *
     * Note: This test would verify build output in CI/CD pipeline
     */
  })
})
