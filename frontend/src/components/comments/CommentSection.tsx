import { useFetchComments } from '@/hooks/useComments'
import { CommentForm } from './CommentForm'
import { CommentList } from './CommentList'

/**
 * Props for the CommentSection component
 */
export interface CommentSectionProps {
  postSlug: string
}

/**
 * Full comment section for a post page
 *
 * Composes the comment list with loading/error states and the comment
 * submission form. Filters out comments pending moderation so they are
 * not visible to non-admin readers.
 */
export function CommentSection({ postSlug }: CommentSectionProps) {
  const { data, isLoading, isError } = useFetchComments(postSlug)

  const visibleComments = data?.comments.filter(c => !c.is_pending_moderation) ?? []

  return (
    <section>
      <CommentForm postSlug={postSlug} />
      {isLoading && <p>Loading comments...</p>}
      {isError && <p>Failed to load comments.</p>}
      {!isLoading && !isError && <CommentList comments={visibleComments} postSlug={postSlug} />}
    </section>
  )
}
