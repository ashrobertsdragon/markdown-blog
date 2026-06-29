import type { APIRequestContext } from '@playwright/test'
import { expect } from '@playwright/test'
import { testUserIds } from './test-user-ids'

const BACKEND = 'http://localhost:5555'

/**
 * Seeds the test database with the three standard test users (author, admin,
 * regular user) using the IDs provisioned by global setup.
 *
 * Accepts either `request` (from a beforeAll fixture) or `page.request`
 * (from a page fixture) — both implement `APIRequestContext`.
 */
export async function seedWithTestUsers(request: APIRequestContext): Promise<void> {
  const res = await request.post(`${BACKEND}/api/test/seed`, {
    data: {
      author_clerk_id: testUserIds.authorClerkId,
      admin_clerk_id: testUserIds.adminClerkId,
      user_clerk_id: testUserIds.userClerkId,
    },
  })
  expect(res.ok()).toBeTruthy()
}
