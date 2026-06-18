import type React from 'react'
import { useState } from 'react'
import ConfirmModal from '@/components/admin/ConfirmModal'
import { usePosts, useUnpublishPost } from '@/hooks/admin/usePosts'

/**
 * Props for PostsTable.
 *
 * Pagination defaults to page 1, 50 results per page — callers can pass explicit
 * values when the admin view supports navigation between pages.
 */
interface PostsTableProps {
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
 * Guards against slugs containing path traversal sequences or non-slug characters.
 *
 * Slugs from the API are expected to be lowercase alphanumeric with hyphens.
 * An invalid slug falls back to '#' to prevent malformed hrefs.
 */
function safeBlogHref(slug: string): string {
  return /^[a-z0-9-]+$/i.test(slug) ? `/blog/${slug}` : '#'
}

/**
 * PostsTable — paginated published-post management table with inline unpublish flow.
 *
 * Drives the admin posts view: lists all published posts, shows a view link
 * to the live post, and lets admins unpublish a post via a ConfirmModal so
 * accidental clicks do not immediately affect production content.
 */
export function PostsTable({ page = 1, limit = 50 }: PostsTableProps): React.ReactElement {
  const { data, isLoading, isError, error } = usePosts({ page, limit })
  const unpublishPost = useUnpublishPost()
  const [confirmPostId, setConfirmPostId] = useState<number | null>(null)

  if (isLoading) {
    return <div className="hidden" />
  }

  if (isError) {
    return <div>Error: {error?.message || 'Failed to load posts'}</div>
  }

  const posts = data?.posts || []

  if (posts.length === 0) {
    return <div>No posts found</div>
  }

  return (
    <div>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Title
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Author
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Published
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {posts.map(post => (
            <tr key={post.id} className="border-b hover:bg-gray-50">
              <td className="px-4 py-2">{post.title}</td>
              <td className="px-4 py-2">{post.author}</td>
              <td className="px-4 py-2">{formatDate(post.published_at)}</td>
              <td className="px-4 py-2 flex gap-2">
                <a
                  href={safeBlogHref(post.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200"
                >
                  View
                </a>
                <button
                  type="button"
                  onClick={() => setConfirmPostId(post.id)}
                  className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                >
                  Unpublish
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 text-sm text-gray-600">
        Page {page} of {data?.total_pages || 0} — {data?.total_count || 0} total posts
      </div>
      {confirmPostId !== null && (
        <ConfirmModal
          title="Unpublish post"
          message="Are you sure you want to unpublish this post? It will no longer be visible to readers."
          confirmText="Unpublish"
          onConfirm={() => {
            unpublishPost.mutate({ postId: confirmPostId })
            setConfirmPostId(null)
          }}
          onCancel={() => setConfirmPostId(null)}
        />
      )}
    </div>
  )
}
