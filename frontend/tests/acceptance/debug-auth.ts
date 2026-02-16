import { expect, test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'
import { waitForAuthToLoad } from './fixtures/helpers'

/**
 * Debug test to verify Clerk mock authentication is working
 */
test.describe('Debug Auth Mock', () => {
  test('verify mock auth sets up correctly', async ({ page }) => {
    // Set up mock auth
    await mockClerkAuth(page, { role: 'author' })

    // Navigate to home page
    await page.goto('/')
    await waitForAuthToLoad(page)

    // Check window.__CLERK_TEST_MOCK__ is set
    const hasMock = await page.evaluate(() => {
      return window.__CLERK_TEST_MOCK__ !== undefined
    })
    expect(hasMock).toBe(true)

    // Check the mock data
    const mockData = await page.evaluate(() => {
      return window.__CLERK_TEST_MOCK__
    })
    expect(mockData).toBeTruthy()
    expect(mockData?.publicMetadata?.role).toBe('author')

    // Check current URL (should not be redirected to /login)
    expect(page.url()).not.toContain('/login')
  })

  test('verify protected route access with mock', async ({ page }) => {
    // Set up mock auth
    await mockClerkAuth(page, { role: 'author' })

    // Navigate directly to a protected route
    await page.goto('/my-posts')
    await waitForAuthToLoad(page)

    // Should not be redirected to login
    await page.waitForLoadState('networkidle')
    const currentUrl = page.url()
    console.log('Current URL:', currentUrl)

    expect(currentUrl).toContain('/my-posts')
    expect(currentUrl).not.toContain('/login')

    // Check if page content loaded
    const pageContent = await page.textContent('body')
    console.log('Page has content:', pageContent && pageContent.length > 0)
  })
})
