import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  type CommentResponse,
  commentsApi,
  type ListCommentsResponse,
} from '@/services/commentsApi'

/**
 * Query hook for fetching paginated comments on a post
 *
 * Disabled when slug is empty to prevent spurious requests.
 *
 * @param slug - Post slug identifier
 * @param options - Optional pagination parameters
 */
export function useFetchComments(
  slug: string,
  options: { skip?: number; limit?: number } = {}
): UseQueryResult<ListCommentsResponse, Error> {
  const { skip = 0, limit = 50 } = options

  return useQuery({
    queryKey: ['comments', slug, { skip, limit }],
    queryFn: () => commentsApi.listComments(slug, skip, limit),
    enabled: Boolean(slug),
  })
}

/**
 * Mutation hook for posting a top-level comment
 *
 * Throws when getToken returns null rather than silently sending an
 * unauthenticated request. Invalidates the comments cache on success.
 */
export function usePostComment(): UseMutationResult<
  CommentResponse,
  Error,
  { slug: string; text: string }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ slug, text }: { slug: string; text: string }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return commentsApi.postComment(slug, text, token)
    },
    onSuccess: (_data, { slug }) => {
      queryClient.invalidateQueries({ queryKey: ['comments', slug, {}] })
    },
  })
}

/**
 * Mutation hook for deleting a comment by id
 *
 * Invalidates the comments cache for the relevant post on success.
 */
export function useDeleteComment(): UseMutationResult<
  void,
  Error,
  { slug: string; commentId: number }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ slug, commentId }: { slug: string; commentId: number }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return commentsApi.deleteComment(slug, commentId, token)
    },
    onSuccess: (_data, { slug }) => {
      queryClient.invalidateQueries({ queryKey: ['comments', slug] })
    },
  })
}

/**
 * Mutation hook for posting a reply to an existing comment
 *
 * Handles rate-limit errors propagated from the API layer.
 * Invalidates the comments cache for the relevant post on success.
 */
export function useReplyToComment(): UseMutationResult<
  CommentResponse,
  Error,
  { slug: string; parentId: number; text: string }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      slug,
      parentId,
      text,
    }: {
      slug: string
      parentId: number
      text: string
    }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return commentsApi.replyToComment(slug, parentId, text, token)
    },
    onSuccess: (_data, { slug }) => {
      queryClient.invalidateQueries({ queryKey: ['comments', slug] })
    },
  })
}
