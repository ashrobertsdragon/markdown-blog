import type { User, UsersResponse } from '@/services/admin/adminApi'

/**
 * Factory function to create a mock User with sensible defaults
 *
 * @param overrides - Partial user fields to override defaults
 * @returns User object
 */
export function createMockUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    clerk_id: 'user_clerk_1234567890',
    email: 'user@example.com',
    display_name: 'John Doe',
    role: 'authenticated',
    created_at: '2026-02-01T10:00:00Z',
    last_login: '2026-05-20T15:30:00Z',
    ...overrides,
  }
}

/**
 * Factory function to create a mock admin user
 *
 * @param overrides - Partial user fields to override defaults
 * @returns User object with role="admin"
 */
export function createMockAdminUser(overrides: Partial<User> = {}): User {
  return createMockUser({
    id: 100,
    clerk_id: 'user_clerk_admin123',
    email: 'alice@example.com',
    display_name: 'Alice Manager',
    role: 'admin',
    ...overrides,
  })
}

/**
 * Factory function to create a mock authenticated user (non-admin)
 *
 * @param overrides - Partial user fields to override defaults
 * @returns User object with role="authenticated"
 */
export function createMockAuthenticatedUser(overrides: Partial<User> = {}): User {
  return createMockUser({
    role: 'authenticated',
    ...overrides,
  })
}

/**
 * Factory function to create a mock user with no login history
 *
 * @param overrides - Partial user fields to override defaults
 * @returns User object with last_login=null
 */
export function createMockNewUser(overrides: Partial<User> = {}): User {
  return createMockUser({
    last_login: null,
    created_at: '2026-05-26T08:00:00Z',
    ...overrides,
  })
}

/**
 * Factory function to create a UsersResponse with paginated data
 *
 * @param users - Array of users to include, or undefined for default array
 * @param total - Total user count across all pages
 * @param totalPages - Total number of pages
 * @param page - Current page number (1-indexed)
 * @param limit - Results per page
 * @returns UsersResponse object
 */
export function createMockUsersResponse(
  users?: User[],
  total: number = 10,
  totalPages: number = 1,
  page: number = 1,
  limit: number = 50
): UsersResponse {
  return {
    users: users ?? [],
    total_count: total,
    total_pages: totalPages,
    page,
    limit,
  }
}

/**
 * Factory function to create a UsersResponse with multiple pages
 *
 * @param userCount - Number of users to create for this page
 * @param page - Current page number
 * @param pageSize - Results per page
 * @param totalCount - Total users across all pages
 * @returns UsersResponse object with pagination metadata
 */
export function createMockPaginatedUsersResponse(
  userCount: number = 3,
  page: number = 1,
  pageSize: number = 3,
  totalCount: number = 10
): UsersResponse {
  const users = Array.from({ length: userCount }, (_, i) =>
    createMockUser({
      id: (page - 1) * pageSize + i + 1,
      email: `user${(page - 1) * pageSize + i + 1}@example.com`,
      display_name: `User ${(page - 1) * pageSize + i + 1}`,
    })
  )

  const totalPages = Math.ceil(totalCount / pageSize)

  return createMockUsersResponse(users, totalCount, totalPages, page, pageSize)
}

/**
 * Factory function to create a UsersResponse with mixed admin and authenticated users
 *
 * @param adminCount - Number of admin users to include
 * @param userCount - Number of authenticated users to include
 * @returns UsersResponse object with mixed roles
 */
export function createMockMixedRolesResponse(
  adminCount: number = 2,
  userCount: number = 3
): UsersResponse {
  const admins = Array.from({ length: adminCount }, (_, i) =>
    createMockAdminUser({
      id: i + 1,
      email: `manager${i + 1}@example.com`,
      display_name: `Manager ${i + 1}`,
    })
  )

  const users = Array.from({ length: userCount }, (_, i) =>
    createMockAuthenticatedUser({
      id: adminCount + i + 1,
      email: `user${i + 1}@example.com`,
      display_name: `User ${i + 1}`,
    })
  )

  return createMockUsersResponse([...admins, ...users], adminCount + userCount, 1, 1, 50)
}
