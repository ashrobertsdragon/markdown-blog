import { clerk } from '@clerk/testing/playwright'
import { expect, test } from '@playwright/test'

/**
 * Basic authentication test to verify Clerk auth works in E2E tests.
 */
test.describe('Authentication', () => {
  test('should load home page with mocked auth', async ({ page }) => {
    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })

    await page.waitForLoadState('networkidle')

    const url = page.url()
    const bodyText = await page.textContent('body')

    console.log('Current URL:', url)
    console.log('Page content:', bodyText?.substring(0, 200))

    await page.screenshot({ path: 'test-results/auth-test-debug.png' })

    expect(url).not.toContain('/login')

    const hasClerk = await page.evaluate(() => window.Clerk !== undefined)
    console.log('window.Clerk exists:', hasClerk)
  })

  test('should navigate to new-post page when authenticated', async ({ page }) => {
    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })

    await page.goto('/new-post')

    await page.waitForLoadState('networkidle')

    const url = page.url()
    console.log('Final URL after navigation:', url)

    await page.screenshot({ path: 'test-results/new-post-navigation.png' })

    expect(url).toContain('/new-post')
  })
})
