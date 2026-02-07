import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  type ListPostsResponse,
  type PostFilter,
  type PostResponse,
  postsApi,
} from '@/services/postsApi'
import { queryKeys } from './queryKeys'

/**
 * Hook for fetching a single draft by slug
 */
export function useDraft(slug: string): UseQueryResult<PostResponse, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.draft(slug),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.getDraft(slug, token)
    },
    enabled: Boolean(slug),
  })
}

/**
 * Hook for fetching paginated list of user's posts with optional filtering
 */
export function useMyPosts(
  filter?: PostFilter,
  page = 1,
  limit = 20
): UseQueryResult<ListPostsResponse, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.myPosts(
      filter || page !== 1 || limit !== 20 ? { filter, page, limit } : undefined
    ),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.listMyPosts(filter, page, limit, token)
    },
  })
}

/**
 * Hook for creating a new draft post
 */
export function useCreateDraft(): UseMutationResult<
  PostResponse,
  Error,
  { slug: string; title: string }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ slug, title }: { slug: string; title: string }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.createDraft(slug, title, token)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.myPosts() })
    },
  })
}

/**
 * Hook for saving draft content with optimistic updates
 */
export function useSaveDraft(): UseMutationResult<
  PostResponse,
  Error,
  { slug: string; content: string }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ slug, content }: { slug: string; content: string }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.saveDraft(slug, content, token)
    },
    onMutate: async ({ slug, content }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.draft(slug) })

      const previousDraft = queryClient.getQueryData<PostResponse>(queryKeys.draft(slug))

      if (previousDraft) {
        queryClient.setQueryData<PostResponse>(queryKeys.draft(slug), {
          ...previousDraft,
          content: content,
          updated_at: new Date().toISOString(),
        })
      }

      return { previousDraft }
    },
    onError: (_error, { slug }, context) => {
      if (context?.previousDraft) {
        queryClient.setQueryData(queryKeys.draft(slug), context.previousDraft)
      }
    },
    onSuccess: (_data, { slug }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.draft(slug) })
      queryClient.invalidateQueries({ queryKey: queryKeys.myPosts() })
    },
  })
}

/**
 * Hook for publishing a draft post
 */
export function usePublishPost(): UseMutationResult<PostResponse, Error, string> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (slug: string) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.publishPost(slug, token)
    },
    onSuccess: (_data, slug) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.draft(slug) })
      queryClient.invalidateQueries({ queryKey: queryKeys.myPosts() })
    },
  })
}

/**
 * Hook for unpublishing a published post
 */
export function useUnpublishPost(): UseMutationResult<PostResponse, Error, string> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (slug: string) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.unpublishPost(slug, token)
    },
    onSuccess: (_data, slug) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.draft(slug) })
      queryClient.invalidateQueries({ queryKey: queryKeys.myPosts() })
    },
  })
}

/**
 * Hook for deleting a draft post
 */
export function useDeleteDraft(): UseMutationResult<void, Error, string> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (slug: string) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return postsApi.deleteDraft(slug, token)
    },
    onSuccess: (_data, slug) => {
      queryClient.removeQueries({ queryKey: queryKeys.draft(slug) })
      queryClient.invalidateQueries({ queryKey: queryKeys.myPosts() })
    },
  })
}
