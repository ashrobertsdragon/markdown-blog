import type React from 'react'
import { useState } from 'react'
import ConfirmModal from '@/components/admin/ConfirmModal'
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
    return <div role="status" className="hidden" />
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
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Content
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Author
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Post
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Date
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {comments.map(comment => (
            <tr key={comment.id} className="border-b hover:bg-gray-50">
              <td className="px-4 py-2 max-w-xs">
                {comment.text.length > 100 ? `${comment.text.slice(0, 100)}...` : comment.text}
              </td>
              <td className="px-4 py-2">{comment.author}</td>
              <td className="px-4 py-2">{comment.post_title}</td>
              <td className="px-4 py-2">{formatDate(comment.created_at)}</td>
              <td className="px-4 py-2">
                <button
                  type="button"
                  onClick={() => setConfirmCommentId(comment.id)}
                  className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 text-sm text-gray-600">
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
