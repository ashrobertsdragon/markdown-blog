import { useAuth } from '@/hooks/useAuth'
import { useCommentStream } from '@/hooks/useCommentStream'
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
 * submission form. Admins fetch with auth so soft-deleted comments appear
 * as [deleted] placeholders. Non-admin readers see only published comments.
 *
 * Wires in `useCommentStream` to keep the React Query cache fresh via SSE,
 * falling back to REST polling when the streaming endpoint is unavailable.
 */
export function CommentSection({ postSlug }: CommentSectionProps) {
  const { role } = useAuth()
  const isAdmin = role === 'admin'
  const { data, isLoading, isError } = useFetchComments(postSlug, { asAdmin: isAdmin })
  const { isConnected, isStreaming } = useCommentStream(postSlug, {
    fallbackToPoll: true,
  })

  const visibleComments = isAdmin
    ? (data?.comments ?? [])
    : (data?.comments.filter(c => !c.is_pending_moderation) ?? [])

  const showLive = isConnected && isStreaming
  const showPolling = isConnected && !isStreaming

  return (
    <section>
      <CommentForm postSlug={postSlug} />
      {isConnected && (
        <span
          aria-live="polite"
          className={
            showLive
              ? 'text-xs text-green-600 dark:text-green-400'
              : 'text-xs text-muted-foreground'
          }
        >
          {showLive ? '● Live' : showPolling ? '↻ Updating' : null}
        </span>
      )}
      {isLoading && <p>Loading comments...</p>}
      {isError && <p>Failed to load comments.</p>}
      {!isLoading && !isError && <CommentList comments={visibleComments} postSlug={postSlug} />}
    </section>
  )
}
