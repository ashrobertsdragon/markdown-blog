import { useState } from 'react'
import { CommentModerateButton } from '@/components/comments/CommentModerateButton'
import { Button } from '@/components/ui/button'
import { useFetchComments } from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'

type FilterState = 'all' | 'pending' | 'deleted'

export interface ModerationPanelProps {
  postSlug: string
  postAuthorId: number
}

/** Derive a human-readable status label from a comment's flags */
function getCommentStatus(comment: CommentResponse): 'pending' | 'deleted' | 'published' {
  if (comment.is_deleted) return 'deleted'
  if (comment.is_pending_moderation) return 'pending'
  return 'published'
}

/**
 * Status badge rendered inside each comment row
 *
 * Colour encodes urgency: yellow for pending review, grey for deleted,
 * green for published — so admins can triage at a glance.
 */
function StatusBadge({ status }: { status: ReturnType<typeof getCommentStatus> }) {
  const styles = {
    pending: 'bg-yellow-100 text-yellow-800 border border-yellow-300',
    deleted: 'bg-gray-100 text-gray-600 border border-gray-300',
    published: 'bg-green-100 text-green-800 border border-green-300',
  }

  const labels = {
    pending: 'Pending',
    deleted: 'Deleted',
    published: 'Published',
  }

  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

/**
 * Generates a CSV blob from an array of comments and triggers a browser download
 *
 * Uses URL.createObjectURL so the admin stays on the page instead of navigating
 * away — the anchor click is programmatic and the element is removed immediately.
 */
function downloadCommentsCSV(comments: CommentResponse[]) {
  const header = 'id,post_id,author_id,text,status,created_at'
  const rows = comments.map(c => {
    const status = getCommentStatus(c)
    const escapedText = `"${c.text.replace(/"/g, '""')}"`
    return `${c.id},${c.post_id},${c.author_id},${escapedText},${status},${c.created_at}`
  })
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'comments.csv'
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

/**
 * Admin panel for moderating all comments on a post
 *
 * Shows every comment regardless of status (unlike the public view which
 * hides deleted and pending items). Filter buttons narrow by status.
 * Deleted rows intentionally omit the CommentModerateButton because
 * approve is nonsensical and the delete action has already been taken.
 */
export function ModerationPanel({ postSlug, postAuthorId: _postAuthorId }: ModerationPanelProps) {
  const [filter, setFilter] = useState<FilterState>('all')
  const { data, isLoading } = useFetchComments(postSlug, { limit: 100 })

  if (isLoading) {
    return <output aria-label="Loading comments">Loading...</output>
  }

  const allComments = data?.comments ?? []

  const filtered = allComments.filter(c => {
    if (filter === 'pending') return c.is_pending_moderation && !c.is_deleted
    if (filter === 'deleted') return c.is_deleted
    return true
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          {filtered.length} of {allComments.length} comments
        </p>
        <Button variant="outline" size="sm" onClick={() => downloadCommentsCSV(allComments)}>
          Export CSV
        </Button>
      </div>

      <div className="flex gap-2">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All
        </Button>
        <Button
          variant={filter === 'pending' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('pending')}
        >
          Pending
        </Button>
        <Button
          variant={filter === 'deleted' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('deleted')}
        >
          Deleted
        </Button>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-gray-500">
            <th className="pb-2 pr-4">Author ID</th>
            <th className="pb-2 pr-4">Text</th>
            <th className="pb-2 pr-4">Date</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(comment => {
            const status = getCommentStatus(comment)
            const truncated =
              comment.text.length > 100 ? `${comment.text.slice(0, 97)}...` : comment.text

            return (
              <tr key={comment.id} data-testid="comment-row" className="border-b">
                <td className="py-2 pr-4">{comment.author_id}</td>
                <td className="py-2 pr-4">{truncated}</td>
                <td className="py-2 pr-4 whitespace-nowrap">
                  {new Date(comment.created_at).toLocaleDateString()}
                </td>
                <td className="py-2 pr-4">
                  <StatusBadge status={status} />
                </td>
                <td className="py-2">
                  {status !== 'deleted' && (
                    <CommentModerateButton commentId={comment.id} postSlug={postSlug} />
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
