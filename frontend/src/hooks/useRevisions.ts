import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  type DiffResponse,
  type ListRevisionsResponse,
  type RevertResponse,
  type RevisionDetail,
  revisionsApi,
} from '@/services/revisionsApi'
import { queryKeys } from './queryKeys'

/**
 * Hook for fetching revision history for a post with pagination
 *
 * @param slug - Post slug identifier
 * @param skip - Number of revisions to skip (offset), defaults to 0
 * @param limit - Maximum number of revisions to return, defaults to 20
 * @returns Query result containing paginated list of revisions
 */
export function useRevisionHistory(
  slug: string,
  skip = 0,
  limit = 20
): UseQueryResult<ListRevisionsResponse, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.revisionHistory(slug, { skip, limit }),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return revisionsApi.listRevisions(slug, skip, limit, token)
    },
    enabled: Boolean(slug),
    retry: false,
  })
}

/**
 * Hook for fetching full details of a specific revision
 *
 * @param slug - Post slug identifier
 * @param sha - Git commit SHA (full or short)
 * @returns Query result containing complete revision data with content
 */
export function useRevisionDetail(
  slug: string,
  sha: string
): UseQueryResult<RevisionDetail, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.revisionDetail(slug, sha),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return revisionsApi.getRevision(slug, sha, token)
    },
    enabled: Boolean(slug && sha),
    retry: false,
  })
}

/**
 * Hook for fetching diff comparison between two revisions
 *
 * @param slug - Post slug identifier
 * @param sha1 - First revision SHA (older)
 * @param sha2 - Second revision SHA (newer)
 * @returns Query result containing diff lines with additions, deletions, and context
 */
export function useRevisionDiff(
  slug: string,
  sha1: string,
  sha2: string
): UseQueryResult<DiffResponse, Error> {
  const auth = useAuth()

  return useQuery({
    queryKey: queryKeys.revisionDiff(slug, sha1, sha2),
    queryFn: async () => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return revisionsApi.getDiff(slug, sha1, sha2, token)
    },
    enabled: Boolean(slug && sha1 && sha2),
    retry: false,
  })
}

/**
 * Hook for reverting a post to a previous revision
 *
 * Creates a new commit that restores the content from the target revision.
 * Invalidates revision history and detail caches on success.
 *
 * @returns Mutation result for revert operation
 */
export function useRevertRevision(): UseMutationResult<
  RevertResponse,
  Error,
  { slug: string; targetSha: string }
> {
  const auth = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ slug, targetSha }: { slug: string; targetSha: string }) => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      return revisionsApi.revertToRevision(slug, targetSha, token)
    },
    onSuccess: (_data, { slug }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.revisionHistory(slug, {}) })
      queryClient.invalidateQueries({ queryKey: ['revisionDetail', slug] })
    },
  })
}
