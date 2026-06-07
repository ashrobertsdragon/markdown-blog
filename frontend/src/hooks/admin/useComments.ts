import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { queryKeys } from '@/hooks/queryKeys'
import { useAuth } from '@/hooks/useAuth'
import { adminApi, type CommentsResponse } from '@/services/admin/adminApi'

/**
 * Query hook for fetching a paginated list of all comments (admin only).
 *
 * Fetches a JWT token on each request and throws 'Authentication required'
 * before calling the API when the token is unavailable. Results are cached
 * under the `queryKeys.admin.comments(page, limit)` key so different pages are
 * stored as independent cache entries.
 *
 * @param options - Pagination parameters
 * @param options.page - 1-indexed page number (default: 1)
 * @param options.limit - Results per page (default: 50)
 * @returns React Query result containing `CommentsResponse` on success
 */
export function useComments({
  page = 1,
  limit = 50,
} = {}): UseQueryResult<CommentsResponse, Error> {
  const auth = useAuth()

  const safePage = Math.max(1, Math.floor(page))
  const safeLimit = Math.min(100, Math.max(1, Math.floor(limit)))

  return useQuery({
    queryKey: queryKeys.admin.comments(safePage, safeLimit),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.getComments(safePage, safeLimit, token)
    },
    enabled: auth.isLoaded && auth.isSignedIn === true,
  })
}

/**
 * Mutation hook for deleting a comment by ID (admin only).
 *
 * Fetches a JWT token before each mutation and throws 'Authentication required'
 * without calling the API when the token is unavailable. On success, invalidates
 * the entire `['admin']` cache namespace so all active admin list queries reload
 * fresh data. Cache is NOT invalidated on failure.
 *
 * @returns React Query mutation result for `{ commentId: number }` variables
 */
export function useDeleteComment(): UseMutationResult<void, Error, { commentId: number }> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ commentId }: { commentId: number }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return adminApi.deleteComment(commentId, token)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.all() })
    },
  })
}
