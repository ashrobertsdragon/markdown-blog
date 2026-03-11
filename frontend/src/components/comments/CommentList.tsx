import type { CommentResponse } from '@/services/commentsApi'
import { CommentItem } from './CommentItem'

export interface CommentListProps {
  comments: CommentResponse[]
  postSlug: string
}

/**
 * Displays a flat list of comments with support for replies and deletion
 *
 * Renders comments in chronological order, with deleted comments shown
 * as placeholders. Reply comments are prefixed with "Reply to @username"
 * to show threading without nesting.
 */
export function CommentList({ comments, postSlug }: CommentListProps) {
  if (comments.length === 0) {
    return <p>No comments yet</p>
  }

  return (
    <section aria-label="Comments">
      {comments.map(comment => (
        <CommentItem key={comment.id} comment={comment} postSlug={postSlug} />
      ))}
    </section>
  )
}
