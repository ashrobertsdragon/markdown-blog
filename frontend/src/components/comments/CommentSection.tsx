import { useFetchComments } from '@/hooks/useComments'
import { CommentForm } from './CommentForm'

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

  return (
    <section>
      <CommentForm postSlug={postSlug} />
      {isLoading && <p>Loading comments...</p>}
      {isError && <p>Failed to load comments.</p>}
      {!isLoading && !isError && data?.comments.length === 0 && <p>No comments yet</p>}
      {data?.comments
        .filter(c => !c.is_pending_moderation)
        .map(c => (
          <div key={c.id}>
            <p>{c.author_id}</p>
            <p>{c.text}</p>
          </div>
        ))}
    </section>
  )
}
