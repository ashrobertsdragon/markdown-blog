import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { queryKeys } from '@/hooks/queryKeys'
import { useAuth } from '@/hooks/useAuth'
import {
  adminApi,
  type User,
  type UserActivity,
  type UserRole,
  type UsersResponse,
} from '@/services/admin/adminApi'

/**
 * Query hook for fetching a paginated list of all users (admin only).
 *
 * Fetches a JWT token on each request and throws 'Authentication required'
 * before calling the API when the token is unavailable. Results are cached
 * under the `queryKeys.admin.users(page, limit)` key so different pages are
 * stored as independent cache entries.
 *
 * @param options - Pagination parameters
 * @param options.page - 1-indexed page number (default: 1)
 * @param options.limit - Results per page (default: 50)
 * @returns React Query result containing `UsersResponse` on success
 */
export function useUsers({ page = 1, limit = 50 } = {}): UseQueryResult<UsersResponse, Error> {
  const auth = useAuth()

  const safePage = Math.max(1, Math.floor(page))
  const safeLimit = Math.min(100, Math.max(1, Math.floor(limit)))

  return useQuery({
    queryKey: queryKeys.admin.users(safePage, safeLimit),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.getUsers(safePage, safeLimit, token)
    },
    enabled: auth.isLoaded && auth.isSignedIn === true,
  })
}

/**
 * Mutation hook for updating a user's role (admin only).
 *
 * Fetches a JWT token before each mutation and throws 'Authentication required'
 * without calling the API when the token is unavailable. On success, invalidates
 * the `['admin', 'users']` cache so all active user list queries reload fresh
 * data. Cache is NOT invalidated on failure.
 *
 * @returns React Query mutation result for `{ userId: number; role: UserRole }` variables
 */
export function useUpdateUserRole(): UseMutationResult<
  User,
  Error,
  { userId: number; role: UserRole }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, role }: { userId: number; role: UserRole }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.updateUserRole(userId, role, token)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.all() })
    },
  })
}

/**
 * Query hook for fetching a single user record by ID (admin only).
 *
 * Used by UserProfilePage when the user record is not available via router state
 * (e.g. direct URL access or page refresh).
 *
 * @param userId - Numeric user ID to fetch
 * @returns React Query result containing `User` on success
 */
export function useUser(userId: number): UseQueryResult<User, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.admin.user(userId),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.getUser(userId, token)
    },
    enabled: auth.isLoaded && auth.isSignedIn === true && userId > 0,
  })
}

/**
 * Query hook for fetching a user's activity summary (admin only).
 *
 * Fetches post count, comment count, last login, and recent posts/comments
 * for the given user ID. Throws 'Authentication required' before calling
 * the API when no token is available.
 *
 * @param userId - Numeric user ID to fetch activity for
 * @returns React Query result containing `UserActivity` on success
 */
export function useUserActivity(userId: number): UseQueryResult<UserActivity, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.admin.userActivity(userId),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.getUserActivity(userId, token)
    },
    enabled: auth.isLoaded && auth.isSignedIn === true && userId > 0,
  })
}
