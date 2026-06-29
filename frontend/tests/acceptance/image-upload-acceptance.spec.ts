/**
 * Acceptance tests for the image upload feature (spec: images).
 *
 * ACs 1.1–4.3 exercise the REST API directly (no browser UI). Real Clerk
 * bearer tokens are obtained once in beforeAll by signing in via a headless
 * browser page and extracting the session token from window.Clerk.
 *
 * ACs 5.1–5.4 exercise the PostEditor UI with real Clerk authentication.
 *
 * All tests run against the real Flask backend (FLASK_ENV=TESTING).
 */
import * as http from 'node:http'
import { clerk } from '@clerk/testing/playwright'
import { type APIRequestContext, expect, test } from '@playwright/test'
import { testUserIds } from '../fixtures/test-user-ids'
import { waitForAuthToLoad } from './fixtures/helpers'

/**
 * Send an HTTP GET using the raw path string, bypassing URL normalisation
 * performed by Playwright's request client (which resolves %2E%2E to ..
 * before the request leaves the process).
 */
function rawGet(port: number, path: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const req = http.request({ hostname: 'localhost', port, path, method: 'GET' }, res =>
      resolve(res.statusCode ?? 0)
    )
    req.on('error', reject)
    req.end()
  })
}

const BACKEND = 'http://localhost:5555'
const TEST_SLUG = 'test-post'

/** Minimal valid 1×1 pixel PNG. */
const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADklEQVQI12P4z8BQDwAEgAF/QualIQAAAABJRU5ErkJggg==',
  'base64'
)

/** 6 MB zero-byte buffer to trigger size limit. */
const OVERSIZED = Buffer.alloc(6 * 1024 * 1024)

/** Signs in via a headless browser page and extracts the Clerk session token. */
async function getClerkToken(
  browser: import('@playwright/test').Browser,
  emailAddress: string
): Promise<string> {
  const context = await browser.newContext()
  const page = await context.newPage()
  try {
    await page.goto('/')
    await clerk.signIn({ page, emailAddress })
    const token = await page.evaluate(() =>
      (
        window as unknown as { Clerk?: { session?: { getToken(): Promise<string> } } }
      ).Clerk?.session?.getToken()
    )
    if (!token) throw new Error(`Failed to get Clerk session token for ${emailAddress}`)
    return token
  } finally {
    await context.close()
  }
}

async function postImageRequest(
  request: APIRequestContext,
  slug: string,
  file: Buffer,
  filename: string,
  token: string
) {
  return request.post(`${BACKEND}/api/posts/${slug}/images`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: {
        name: filename,
        mimeType: 'image/png',
        buffer: file,
      },
    },
  })
}

test.describe.configure({ mode: 'serial' })

let authorToken: string
let otherToken: string

test.describe('Image Upload Acceptance Tests', () => {
  test.beforeAll(async ({ browser, request }) => {
    const res = await request.post(`${BACKEND}/api/test/seed`, {
      data: {
        author_clerk_id: testUserIds.authorClerkId,
        admin_clerk_id: testUserIds.adminClerkId,
        user_clerk_id: testUserIds.userClerkId,
      },
    })
    expect(res.ok()).toBeTruthy()

    authorToken = await getClerkToken(browser, 'author@example.com')
    otherToken = await getClerkToken(browser, 'user@example.com')
  })

  test.afterAll(async ({ request }) => {
    await request.delete(`${BACKEND}/api/test/reset`)
  })

  // ── Requirement 1: Upload ──────────────────────────────────────────────────

  test('AC 1.1: POST valid PNG → 201 + url body', async ({ request }) => {
    const res = await postImageRequest(request, TEST_SLUG, PNG_1X1, 'photo.png', authorToken)
    expect(res.status()).toBe(201)
    const body = await res.json()
    expect(body).toHaveProperty('url')
    expect(body.url).toContain(`/uploads/${TEST_SLUG}/`)
  })

  test('AC 1.2: POST file > 5 MB → 413', async ({ request }) => {
    const res = await request.post(`${BACKEND}/api/posts/${TEST_SLUG}/images`, {
      headers: { Authorization: `Bearer ${authorToken}` },
      multipart: {
        file: {
          name: 'big.png',
          mimeType: 'image/png',
          buffer: OVERSIZED,
        },
      },
    })
    expect(res.status()).toBe(413)
  })

  test('AC 1.3: POST non-image extension → 400', async ({ request }) => {
    const res = await request.post(`${BACKEND}/api/posts/${TEST_SLUG}/images`, {
      headers: { Authorization: `Bearer ${authorToken}` },
      multipart: {
        file: {
          name: 'script.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from('hello'),
        },
      },
    })
    expect(res.status()).toBe(400)
  })

  test('AC 1.4: POST unauthenticated → 401', async ({ request }) => {
    const res = await request.post(`${BACKEND}/api/posts/${TEST_SLUG}/images`, {
      multipart: {
        file: {
          name: 'photo.png',
          mimeType: 'image/png',
          buffer: PNG_1X1,
        },
      },
    })
    expect(res.status()).toBe(401)
  })

  test('AC 1.5: POST as wrong author → 403', async ({ request }) => {
    const res = await postImageRequest(request, TEST_SLUG, PNG_1X1, 'photo.png', otherToken)
    expect(res.status()).toBe(403)
  })

  // ── Requirement 2: Serve ──────────────────────────────────────────────────

  test('AC 2.1: GET /uploads/{slug}/{file} → correct Content-Type', async ({ request }) => {
    const upload = await postImageRequest(
      request,
      TEST_SLUG,
      PNG_1X1,
      'serve-test.png',
      authorToken
    )
    expect(upload.status()).toBe(201)
    const { url } = await upload.json()

    const res = await request.get(`${BACKEND}${url}`)
    expect(res.status()).toBe(200)
    expect(res.headers()['content-type']).toContain('image/png')
  })

  test('AC 2.2: GET /uploads/%2E%2E/etc/passwd → 403', async () => {
    const status = await rawGet(5555, '/uploads/%2E%2E/etc/passwd')
    expect(status).toBe(403)
  })

  test('AC 2.3: GET valid image → Cache-Control header present', async ({ request }) => {
    const upload = await postImageRequest(
      request,
      TEST_SLUG,
      PNG_1X1,
      'cache-test.png',
      authorToken
    )
    expect(upload.status()).toBe(201)
    const { url } = await upload.json()

    const res = await request.get(`${BACKEND}${url}`)
    expect(res.headers()['cache-control']).toContain('max-age=31536000')
  })

  // ── Requirement 3: List ───────────────────────────────────────────────────

  test('AC 3.1: GET list for draft with uploads → images array', async ({ request }) => {
    await postImageRequest(request, TEST_SLUG, PNG_1X1, 'list-test.png', authorToken)

    const res = await request.get(`${BACKEND}/api/posts/${TEST_SLUG}/images`, {
      headers: { Authorization: `Bearer ${authorToken}` },
    })
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body).toHaveProperty('images')
    expect(Array.isArray(body.images)).toBe(true)
    expect(body.images.length).toBeGreaterThan(0)
  })

  test('AC 3.2: GET list for draft with no uploads → {"images":[]}', async ({ request }) => {
    const slug = 'publish-me'
    const res = await request.get(`${BACKEND}/api/posts/${slug}/images`, {
      headers: { Authorization: `Bearer ${authorToken}` },
    })
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body).toEqual({ images: [] })
  })

  // ── Requirement 4: Delete ─────────────────────────────────────────────────

  test('AC 4.1: DELETE existing image → 204', async ({ request }) => {
    const upload = await postImageRequest(request, TEST_SLUG, PNG_1X1, 'delete-me.png', authorToken)
    expect(upload.status()).toBe(201)
    const { url } = await upload.json()
    const filename = url.split('/').pop()

    const res = await request.delete(`${BACKEND}/api/posts/${TEST_SLUG}/images/${filename}`, {
      headers: { Authorization: `Bearer ${authorToken}` },
    })
    expect(res.status()).toBe(204)
  })

  test('AC 4.2: DELETE non-existent image → 404', async ({ request }) => {
    const res = await request.delete(`${BACKEND}/api/posts/${TEST_SLUG}/images/ghost.png`, {
      headers: { Authorization: `Bearer ${authorToken}` },
    })
    expect(res.status()).toBe(404)
  })

  test('AC 4.3: DELETE wrong author → 403', async ({ request }) => {
    const upload = await postImageRequest(request, TEST_SLUG, PNG_1X1, 'no-delete.png', authorToken)
    expect(upload.status()).toBe(201)
    const { url } = await upload.json()
    const filename = url.split('/').pop()

    const res = await request.delete(`${BACKEND}/api/posts/${TEST_SLUG}/images/${filename}`, {
      headers: { Authorization: `Bearer ${otherToken}` },
    })
    expect(res.status()).toBe(403)
  })

  // ── Requirement 5: PostEditor UI ──────────────────────────────────────────

  test('AC 5.1: Upload via PostEditor inserts "![" at cursor', async ({ page }) => {
    await page.route(`**/api/posts/${TEST_SLUG}/images`, route => {
      if (route.request().method() === 'POST') {
        void route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ url: `/uploads/${TEST_SLUG}/photo.png` }),
        })
      } else {
        void route.continue()
      }
    })

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })
    await waitForAuthToLoad(page)
    await page.goto(`/edit/${TEST_SLUG}`)
    await expect(page.locator('.w-md-editor')).toBeVisible({ timeout: 15000 })

    await page
      .locator('input[type="file"][accept="image/*"]')
      .setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: PNG_1X1 })

    await expect(page.locator('.w-md-editor-text-input')).toContainText('![', { timeout: 5000 })
  })

  test('AC 5.2: Upload in progress → button disabled', async ({ page }) => {
    let resolveUpload!: () => void
    await page.route(`**/api/posts/${TEST_SLUG}/images`, async route => {
      if (route.request().method() === 'POST') {
        await new Promise<void>(resolve => {
          resolveUpload = resolve
        })
        void route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ url: `/uploads/${TEST_SLUG}/photo.png` }),
        })
      } else {
        void route.continue()
      }
    })

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })
    await waitForAuthToLoad(page)
    await page.goto(`/edit/${TEST_SLUG}`)
    await expect(page.locator('.w-md-editor')).toBeVisible({ timeout: 15000 })

    const fileInput = page.locator('input[type="file"][accept="image/*"]')
    await fileInput.setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: PNG_1X1 })

    const uploadButton = page.getByRole('button', { name: /uploading/i })
    await expect(uploadButton).toBeDisabled({ timeout: 5000 })

    resolveUpload()
  })

  test('AC 5.3: Server 500 → error toast, markdown unchanged', async ({ page }) => {
    await page.route(`**/api/posts/${TEST_SLUG}/images`, route => {
      if (route.request().method() === 'POST') {
        void route.fulfill({ status: 500, body: 'Internal Server Error' })
      } else {
        void route.continue()
      }
    })

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })
    await waitForAuthToLoad(page)
    await page.goto(`/edit/${TEST_SLUG}`)
    await expect(page.locator('.w-md-editor')).toBeVisible({ timeout: 15000 })

    await page
      .locator('input[type="file"][accept="image/*"]')
      .setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: PNG_1X1 })

    await expect(page.getByText(/image upload failed/i)).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.w-md-editor-text-input')).not.toContainText('![')
  })

  test('AC 5.4: Upload success → success toast', async ({ page }) => {
    await page.route(`**/api/posts/${TEST_SLUG}/images`, route => {
      if (route.request().method() === 'POST') {
        void route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ url: `/uploads/${TEST_SLUG}/photo.png` }),
        })
      } else {
        void route.continue()
      }
    })

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })
    await waitForAuthToLoad(page)
    await page.goto(`/edit/${TEST_SLUG}`)
    await expect(page.locator('.w-md-editor')).toBeVisible({ timeout: 15000 })

    await page
      .locator('input[type="file"][accept="image/*"]')
      .setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: PNG_1X1 })

    await expect(page.getByText(/image uploaded/i)).toBeVisible({ timeout: 5000 })
  })
})
