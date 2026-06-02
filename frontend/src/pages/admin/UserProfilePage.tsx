import { Link, useLocation, useParams } from 'react-router-dom'
import { useUserActivity } from '@/hooks/admin/useUsers'
import type { User } from '@/services/admin/adminApi'

const formatDate = (d: string | null): string => (d ? new Date(d).toLocaleDateString() : 'Never')

function isUser(value: unknown): value is User {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.id === 'number' &&
    typeof v.email === 'string' &&
    typeof v.role === 'string' &&
    typeof v.created_at === 'string'
  )
}

/**
 * Admin page displaying a single user's profile and activity summary.
 *
 * Reads the `User` record from React Router location state (passed by the
 * users list page) and fetches live activity data via `useUserActivity`.
 * Renders loading/error states before showing user details, activity counts,
 * recent posts and comments, and navigation links to the content tab.
 */
export default function UserProfilePage() {
  const { userId } = useParams<{ userId: string }>()
  const location = useLocation()
  const user = isUser(location.state?.user) ? location.state.user : undefined

  const numericId = parseInt(userId ?? '', 10)
  const { data: activity, isLoading, isError } = useUserActivity(numericId)

  if (!user) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">User Profile</h1>
        <p className="text-gray-500">User not found</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">User Profile</h1>
        <output className="text-gray-500">Loading activity…</output>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">User Profile</h1>
        <p className="text-red-600">Failed to load activity data</p>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">User Profile</h1>

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">User Details</h2>
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-gray-500">Email</dt>
            <dd className="text-sm text-gray-900">{user.email}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Role</dt>
            <dd className="text-sm text-gray-900">{user.role}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Joined</dt>
            <dd className="text-sm text-gray-900">{formatDate(user.created_at)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Last Login</dt>
            <dd className="text-sm text-gray-900">{formatDate(activity?.last_login ?? null)}</dd>
          </div>
        </dl>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 mb-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-500">Posts</p>
          <p className="text-2xl font-semibold text-gray-900">{activity?.post_count}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-500">Comments</p>
          <p className="text-2xl font-semibold text-gray-900">{activity?.comment_count}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-gray-900">Recent Posts</h2>
          <Link
            to="/admin/content"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            View Posts
          </Link>
        </div>
        {activity?.recent_posts.length === 0 ? (
          <p className="text-sm text-gray-500">No recent posts</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {activity?.recent_posts.map(post => (
              <li key={post.id} className="py-2 text-sm text-gray-900">
                {post.title}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-gray-900">Recent Comments</h2>
          <Link
            to="/admin/content"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            View Comments
          </Link>
        </div>
        {activity?.recent_comments.length === 0 ? (
          <p className="text-sm text-gray-500">No recent comments</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {activity?.recent_comments.map(comment => (
              <li key={comment.id} className="py-2 text-sm text-gray-900">
                {comment.text}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
