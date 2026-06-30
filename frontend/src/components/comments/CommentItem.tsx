import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/hooks/useAuth'
import { useDeleteComment } from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'
import { ReplyForm } from './ReplyForm'

export interface CommentItemProps {
  comment: CommentResponse
  postSlug: string
}

/**
 * Renders a single comment or reply with optional author badge, timestamp,
 * and action buttons (Reply, Delete).
 *
 * Deleted comments show "[deleted]" placeholder. Replies show "Reply to @username"
 * prefix to indicate threading in the flat comment list. The delete action is
 * confirmed via an AlertDialog before mutation is triggered.
 */
export function CommentItem({ comment, postSlug }: CommentItemProps) {
  const { isSignedIn } = useAuth()
  const [showReplyForm, setShowReplyForm] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const deleteCommentMutation = useDeleteComment()

  const isPostAuthor = comment.is_post_author
  const canDelete = isSignedIn

  const handleDeleteConfirm = () => {
    deleteCommentMutation.mutate(
      { slug: postSlug, commentId: comment.id },
      { onSuccess: () => setShowDeleteDialog(false) }
    )
  }

  const scrollToParent = () => {
    const parent = document.querySelector(`[data-comment-id="${comment.parent_id}"]`)
    parent?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const formatTimestamp = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`
    if (seconds < 2592000) return `${Math.floor(seconds / 604800)} weeks ago`
    if (seconds < 31536000) return `${Math.floor(seconds / 2592000)} months ago`
    return `${Math.floor(seconds / 31536000)} years ago`
  }

  const authorHandle = `comment${comment.parent_id ?? comment.id}`

  return (
    <>
      <article
        className="comment-item border-b pb-4 mb-4"
        data-testid="comment-item"
        data-comment-id={comment.id}
      >
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold">Comment author</span>
              {isPostAuthor && <Badge variant="secondary">Author</Badge>}
            </div>
            <div className="comment-timestamp text-xs text-muted-foreground mt-1">
              {formatTimestamp(comment.created_at)}
            </div>

            {comment.parent_id && (
              <div className="text-sm text-muted-foreground italic mt-2">
                <button type="button" className="hover:underline" onClick={scrollToParent}>
                  {`Reply to @${String(authorHandle).replace(/^@/, '')}`}
                </button>
              </div>
            )}

            <div className="mt-2">
              {comment.is_deleted ? (
                <p className="text-muted-foreground italic">[deleted]</p>
              ) : (
                <p className="text-foreground">{comment.text}</p>
              )}
            </div>

            <div className="flex gap-2 mt-3">
              {!comment.is_deleted && (
                <button
                  type="button"
                  onClick={() => setShowReplyForm(!showReplyForm)}
                  className="text-sm text-primary hover:underline"
                >
                  Reply
                </button>
              )}
              {canDelete && (
                <button
                  type="button"
                  aria-label="Delete comment"
                  onClick={() => setShowDeleteDialog(true)}
                  disabled={deleteCommentMutation.isPending}
                  className="text-sm text-destructive hover:underline disabled:opacity-50"
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

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete comment</AlertDialogTitle>
            <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleteCommentMutation.isPending}
              className="disabled:opacity-50"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
