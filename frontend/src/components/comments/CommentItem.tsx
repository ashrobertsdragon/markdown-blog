import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useDeleteComment } from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'
import { ReplyForm } from './ReplyForm'

export interface CommentItemProps {
  comment: CommentResponse
  postSlug: string
  postAuthorId: number
}

/**
 * Renders a single comment or reply with optional author badge, timestamp,
 * and action buttons (Reply, Delete).
 *
 * Deleted comments show "[deleted]" placeholder. Replies show "Reply to @username"
 * prefix to indicate threading in the flat comment list.
 */
export function CommentItem({ comment, postSlug, postAuthorId }: CommentItemProps) {
  const { user } = useAuth()
  const [showReplyForm, setShowReplyForm] = useState(false)
  const deleteCommentMutation = useDeleteComment()

  const isPostAuthor = comment.author_id === postAuthorId
  const isCommentAuthor = user && Number(user.id) === comment.author_id
  const canDelete = isCommentAuthor

  const handleDelete = () => {
    if (window.confirm('Delete this comment?')) {
      deleteCommentMutation.mutate({ slug: postSlug, commentId: comment.id })
    }
  }

  const formatTimestamp = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`
    return date.toLocaleDateString()
  }

  return (
    <article className="border-b pb-4 mb-4">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">User {comment.author_id}</span>
            {isPostAuthor && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Author</span>
            )}
          </div>
          <div className="text-xs text-gray-500 mt-1">{formatTimestamp(comment.created_at)}</div>

          {comment.parent_id && (
            <div className="text-sm text-gray-600 italic mt-2">
              <span>Reply to comment #{comment.parent_id}</span>
            </div>
          )}

          <div className="mt-2">
            {comment.is_deleted ? (
              <p className="text-gray-500 italic">[deleted]</p>
            ) : (
              <p className="text-gray-800">{comment.text}</p>
            )}
          </div>

          <div className="flex gap-2 mt-3">
            {!comment.is_deleted && (
              <button
                type="button"
                onClick={() => setShowReplyForm(!showReplyForm)}
                className="text-sm text-blue-600 hover:underline"
              >
                Reply
              </button>
            )}
            {canDelete && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteCommentMutation.isPending}
                className="text-sm text-red-600 hover:underline disabled:opacity-50"
              >
                Delete
              </button>
            )}
          </div>

          {showReplyForm && !comment.is_deleted && (
            <div className="mt-4 ml-4 border-l-2 pl-4">
              <ReplyForm
                parentComment={comment}
                postSlug={postSlug}
                onCancel={() => setShowReplyForm(false)}
              />
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
