import { readFileSync } from 'node:fs'

const IDS_FILE = 'playwright/.clerk/test-user-ids.json'

interface TestUserIds {
  authorClerkId: string
  adminClerkId: string
  userClerkId: string
}

function loadTestUserIds(): TestUserIds {
  try {
    return JSON.parse(readFileSync(IDS_FILE, 'utf8')) as TestUserIds
  } catch {
    return {
      authorClerkId: 'user_test_author',
      adminClerkId: 'user_test_admin',
      userClerkId: 'user_test_user',
    }
  }
}

export const testUserIds = loadTestUserIds()
