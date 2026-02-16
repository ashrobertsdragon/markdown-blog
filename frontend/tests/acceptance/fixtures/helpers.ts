import type { Page } from '@playwright/test'

declare global {
  interface Window {
    Clerk?: {
      loaded: boolean
      user?: unknown
    }
  }
}

/**
 * Wait for Clerk authentication to load by checking for the presence of
 * the Clerk client object in the window.
 */
export async function waitForAuthToLoad(page: Page): Promise<void> {
  await page.waitForFunction(() => window.Clerk !== undefined, { timeout: 5000 })
}
