import { test } from '@playwright/test'
import { mockClerkAuth } from './fixtures/clerk-mock'

test('debug auth and page content', async ({ page }) => {
  await mockClerkAuth(page, { role: 'author' })

  page.on('console', msg => console.log('BROWSER LOG:', msg.text()))
  page.on('request', request => console.log('REQUEST:', request.method(), request.url()))
  page.on('response', response => console.log('RESPONSE:', response.status(), response.url()))

  console.log('Navigating to /my-posts...')
  await page.goto('/my-posts', { waitUntil: 'networkidle' })

  console.log('Current URL:', page.url())

  const hasSpinner = await page.locator('[role="status"]').isVisible()
  console.log('Has Loading Spinner:', hasSpinner)

  const hasMyPostsHeader = await page.locator('h1:has-text("My Posts")').isVisible()
  console.log('Has "My Posts" header:', hasMyPostsHeader)
})
