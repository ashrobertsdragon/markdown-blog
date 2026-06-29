import { Link, useLocation, useParams } from 'react-router-dom'
import { useUser, useUserActivity } from '@/hooks/admin/useUsers'
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
  const stateUser = isUser(location.state?.user) ? location.state.user : undefined

  const numericId = parseInt(userId ?? '', 10)
  const isValidId = !Number.isNaN(numericId) && numericId > 0

  const { data: fetchedUser, isLoading: isUserLoading, isError: isUserError } = useUser(numericId)
  const user: User | undefined = stateUser ?? fetchedUser
  const {
    data: activity,
    isLoading: isActivityLoading,
    isError: isActivityError,
  } = useUserActivity(numericId)

  const isLoading = (stateUser ? false : isUserLoading) || isActivityLoading

  if (!isValidId) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-foreground mb-6">User Profile</h1>
        <p className="text-muted-foreground">Invalid user ID</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-foreground mb-6">User Profile</h1>
        <output className="text-muted-foreground">Loading activity…</output>
      </div>
    )
  }

  if ((!stateUser && isUserError) || isActivityError) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-foreground mb-6">User Profile</h1>
        <p className="text-destructive">Failed to load user data</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-foreground mb-6">User Profile</h1>
        <p className="text-muted-foreground">User not found</p>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-foreground mb-6">User Profile</h1>

      <div className="bg-card rounded-lg border border-border p-6 mb-6">
        <h2 className="text-lg font-medium text-foreground mb-4">User Details</h2>
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-muted-foreground">Email</dt>
            <dd className="text-sm text-foreground">{user.email}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-muted-foreground">Role</dt>
            <dd className="text-sm text-foreground">{user.role}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-muted-foreground">Joined</dt>
            <dd className="text-sm text-foreground">{formatDate(user.created_at)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-muted-foreground">Last Login</dt>
            <dd className="text-sm text-foreground">{formatDate(activity?.last_login ?? null)}</dd>
          </div>
        </dl>
      </div>

      <div data-testid="user-activity" className="grid grid-cols-1 gap-4 sm:grid-cols-2 mb-6">
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="text-sm font-medium text-muted-foreground">Posts</p>
          <p className="text-2xl font-semibold text-foreground">{activity?.post_count}</p>
        </div>
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="text-sm font-medium text-muted-foreground">Comments</p>
          <p className="text-2xl font-semibold text-foreground">{activity?.comment_count}</p>
        </div>
      </div>

      <div data-testid="user-posts" className="bg-card rounded-lg border border-border p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-foreground">Recent Posts</h2>
          <Link
            to="/admin/content"
            className="text-sm text-primary hover:text-primary/80 font-medium"
          >
            View Posts
          </Link>
        </div>
        {activity?.recent_posts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No recent posts</p>
        ) : (
          <ul className="divide-y divide-border">
            {activity?.recent_posts.map(post => (
              <li key={post.id} className="py-2 text-sm text-foreground">
                {post.title}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-card rounded-lg border border-border p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-foreground">Recent Comments</h2>
          <Link
            to="/admin/content"
            className="text-sm text-primary hover:text-primary/80 font-medium"
          >
            View Comments
          </Link>
        </div>
        {activity?.recent_comments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No recent comments</p>
        ) : (
          <ul className="divide-y divide-border">
            {activity?.recent_comments.map(comment => (
              <li key={comment.id} className="py-2 text-sm text-foreground">
                {comment.text}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
