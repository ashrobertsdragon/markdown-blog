import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'

/**
 * Basic authentication test to verify Clerk mocking works
 */
test.describe('Authentication', () => {
  test('should load home page with mocked auth', async ({ page }) => {
    // Mock Clerk authentication
    await mockClerkAuth(page, { role: 'author' })

    // Navigate to home page
    await page.goto('/')

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Check current URL and page content
    const url = page.url()
    const bodyText = await page.textContent('body')

    console.log('Current URL:', url)
    console.log('Page content:', bodyText?.substring(0, 200))

    // Take a screenshot for debugging
    await page.screenshot({ path: 'test-results/auth-test-debug.png' })

    // Verify we're not on the login page
    expect(url).not.toContain('/login')

    // Check if Clerk object exists
    const hasClerk = await page.evaluate(() => window.Clerk !== undefined)
    console.log('window.Clerk exists:', hasClerk)
  })

  test('should navigate to new-post page when authenticated', async ({ page }) => {
    // Mock Clerk authentication
    await mockClerkAuth(page, { role: 'author' })

    // Navigate directly to new-post page
    await page.goto('/new-post')

    // Wait for navigation to complete
    await page.waitForLoadState('networkidle')

    const url = page.url()
    console.log('Final URL after navigation:', url)

    // Take screenshot
    await page.screenshot({ path: 'test-results/new-post-navigation.png' })

    // Should not redirect to login
    expect(url).toContain('/new-post')
  })
})
