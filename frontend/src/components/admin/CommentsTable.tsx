import type React from 'react'
import { useState } from 'react'
import ConfirmModal from '@/components/admin/ConfirmModal'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useComments, useDeleteComment } from '@/hooks/admin/useComments'

/**
 * Props for CommentsTable.
 *
 * Pagination defaults to page 1, 50 results per page — callers can pass explicit
 * values when the admin view supports navigation between pages.
 */
interface CommentsTableProps {
  /** 1-indexed page number */
  page?: number
  /** Results per page */
  limit?: number
}

/**
 * Converts an ISO date string to MM/DD/YYYY format using UTC to avoid timezone-dependent
 * display differences across admin users in different regions.
 *
 * Returns 'Never' for null/undefined inputs so the table always has a
 * displayable value rather than an empty cell or crash.
 */
function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  const year = date.getUTCFullYear()
  return `${month}/${day}/${year}`
}

/**
 * CommentsTable — paginated comment moderation table with inline delete flow.
 *
 * Drives the admin comments view: lists all comments across all posts, truncates
 * long content so the table stays scannable, and lets admins delete a comment via
 * a ConfirmModal so accidental clicks do not immediately remove reader contributions.
 * Plain-text rendering (no dangerouslySetInnerHTML) prevents XSS from user content.
 */
export function CommentsTable({ page = 1, limit = 50 }: CommentsTableProps): React.ReactElement {
  const { data, isLoading, isError, error } = useComments({ page, limit })
  const deleteComment = useDeleteComment()
  const [confirmCommentId, setConfirmCommentId] = useState<number | null>(null)

  if (isLoading) {
    return <div className="hidden" aria-hidden="true" data-testid="loading" />
  }

  if (isError) {
    return <div>Error: {error?.message || 'Failed to load comments'}</div>
  }

  const comments = data?.comments || []

  if (comments.length === 0) {
    return <div>No comments found</div>
  }

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Content</TableHead>
            <TableHead scope="col">Author</TableHead>
            <TableHead scope="col">Post</TableHead>
            <TableHead scope="col">Date</TableHead>
            <TableHead scope="col">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {comments.map(comment => (
            <TableRow key={comment.id}>
              <TableCell className="max-w-xs">
                {comment.text.length > 100 ? `${comment.text.slice(0, 100)}...` : comment.text}
              </TableCell>
              <TableCell>{comment.author}</TableCell>
              <TableCell>{comment.post_title}</TableCell>
              <TableCell>{formatDate(comment.created_at)}</TableCell>
              <TableCell>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmCommentId(comment.id)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="mt-4 text-sm text-muted-foreground">
        Page {page} of {data?.total_pages || 0} — {data?.total_count || 0} total comments
      </div>
      {confirmCommentId !== null && (
        <ConfirmModal
          title="Delete comment"
          message="Are you sure you want to delete this comment? This action cannot be undone."
          confirmText="Delete"
          onConfirm={() => {
            deleteComment.mutate({ commentId: confirmCommentId })
            setConfirmCommentId(null)
          }}
          onCancel={() => setConfirmCommentId(null)}
        />
      )}
    </div>
  )
}
