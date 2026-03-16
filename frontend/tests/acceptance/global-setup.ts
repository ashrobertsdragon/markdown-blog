import { request } from '@playwright/test'

/**
 * Global setup for acceptance tests.
 *
 * Seeds the backend with test data before any acceptance tests run.
 * This ensures tests that navigate directly to seeded routes (e.g.
 * /posts/test-post) have data available without per-test beforeAll hooks.
 */
async function globalSetup() {
  const context = await request.newContext({ baseURL: 'http://localhost:5555' })
  await context.post('/api/test/seed')
  await context.dispose()
}

export default globalSetup
