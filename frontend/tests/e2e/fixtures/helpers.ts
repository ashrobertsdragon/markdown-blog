import { expect, type Page } from '@playwright/test'

export async function waitForApiCall(
  page: Page,
  pattern: string | RegExp,
  timeout = 5000
): Promise<void> {
  await page.waitForResponse(
    response => {
      const url = response.url()
      if (pattern instanceof RegExp) {
        return pattern.test(url)
      }
      return url.includes(pattern)
    },
    { timeout }
  )
}

export async function getAuthToken(page: Page): Promise<string | null> {
  const cookies = await page.context().cookies()
  const authCookie = cookies.find(c => c.name === '__session')

  if (authCookie) {
    return authCookie.value
  }

  const sessionStorage = await page.evaluate(() => {
    return sessionStorage.getItem('auth_token')
  })

  if (sessionStorage) {
    return sessionStorage
  }

  const localStorage = await page.evaluate(() => {
    return localStorage.getItem('auth_token')
  })

  return localStorage
}

export async function verifyAuthHeaderInRequest(page: Page, apiPath: string): Promise<void> {
  let authHeaderFound = false

  page.on('response', response => {
    if (response.url().includes(apiPath)) {
      const request = response.request()
      const authHeader = request.headerValue('authorization')
      if (authHeader?.startsWith('Bearer ')) {
        authHeaderFound = true
      }
    }
  })

  await waitForApiCall(page, apiPath)

  expect(authHeaderFound).toBeTruthy()
}

export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login')
  await page.waitForSelector("input[type='email']", { timeout: 10000 })

  await page.fill("input[type='email']", email)
  await page.fill("input[type='password']", password)

  const submitButton = page.locator("button:has-text('Sign in')")
  await submitButton.click()

  await page.waitForNavigation({ url: /^(?!\/login)/, timeout: 15000 })
}

export async function checkUserCreatedInDatabase(page: Page, clerkUserId: string): Promise<void> {
  const response = await page.request.get('/api/auth/me')
  expect(response.ok()).toBeTruthy()

  const userData = await response.json()
  expect(userData).toHaveProperty('clerk_user_id', clerkUserId)
  expect(userData).toHaveProperty('email')
  expect(userData).toHaveProperty('role')
  expect(userData).toHaveProperty('id')
}

export async function verifyRedirectToLogin(page: Page, protectedPath: string): Promise<void> {
  await page.goto(protectedPath)
  await page.waitForURL('/login', { timeout: 5000 })
  expect(page.url()).toContain('/login')
}

export async function logout(page: Page): Promise<void> {
  const userButton = page.locator("[data-testid='user-button']")

  if (await userButton.isVisible()) {
    await userButton.click()
    const signOutButton = page.locator('text=Sign out')
    await signOutButton.click()
    await page.waitForURL('/', { timeout: 5000 })
  }
}

export async function waitForAuthToLoad(page: Page): Promise<void> {
  await page.waitForFunction(
    () => {
      const spinner = document.querySelector('.animate-spin')
      return !spinner
    },
    { timeout: 10000 }
  )
}

export async function verifyBearerTokenFormat(token: string | null): void {
  expect(token).toBeTruthy()
  expect(token).toMatch(/^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$/)
}

export async function interceptApiRequests(page: Page): Promise<Map<string, boolean>> {
  const apiRequests = new Map<string, boolean>()

  page.on('response', response => {
    const url = response.url()
    if (url.includes('/api/')) {
      const request = response.request()
      const authHeader = request.headerValue('authorization')
      apiRequests.set(url, !!authHeader)
    }
  })

  return apiRequests
}
