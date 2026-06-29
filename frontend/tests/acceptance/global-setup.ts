import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { clerkSetup } from '@clerk/testing/playwright'
import dotenv from 'dotenv'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
dotenv.config({ path: resolve(__dirname, '../../../../.env'), override: false })

/**
 * Ensures a Clerk test user exists for the given email, returning their Clerk user ID.
 * Creates the user if they don't already exist. Updates publicMetadata.role on each run
 * to keep it in sync with the expected role.
 */
async function getOrCreateClerkUser(email: string, role: string): Promise<string> {
  const secretKey = process.env.CLERK_SECRET_KEY
  if (!secretKey) throw new Error('CLERK_SECRET_KEY is required for E2E tests')

  const headers = { Authorization: `Bearer ${secretKey}`, 'Content-Type': 'application/json' }

  const listRes = await fetch(
    `https://api.clerk.com/v1/users?email_address=${encodeURIComponent(email)}`,
    { headers }
  )
  if (!listRes.ok) throw new Error(`Clerk list users failed: ${listRes.status}`)
  const list = (await listRes.json()) as Array<{ id: string }>

  if (list.length > 0) {
    const userId = list[0].id
    await fetch(`https://api.clerk.com/v1/users/${userId}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ public_metadata: { role } }),
    })
    return userId
  }

  const createRes = await fetch('https://api.clerk.com/v1/users', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      email_address: [email],
      public_metadata: { role },
      skip_password_checks: true,
      skip_password_requirement: true,
    }),
  })
  if (!createRes.ok) {
    const body = await createRes.text()
    throw new Error(`Clerk create user failed for ${email}: ${createRes.status} ${body}`)
  }
  const created = (await createRes.json()) as { id: string }
  return created.id
}

export default async function globalSetup() {
  await clerkSetup()

  const authorClerkId = await getOrCreateClerkUser('author@example.com', 'author')
  const adminClerkId = await getOrCreateClerkUser('admin@example.com', 'admin')
  const userClerkId = await getOrCreateClerkUser('user@example.com', 'authenticated')

  mkdirSync('playwright/.clerk', { recursive: true })
  writeFileSync(
    'playwright/.clerk/test-user-ids.json',
    JSON.stringify({ authorClerkId, adminClerkId, userClerkId })
  )
}
