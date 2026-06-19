import type React from 'react'
import { useUsers } from '@/hooks/admin/useUsers'
import type { User } from '@/services/admin/adminApi'

interface UserTableProps {
  /**
   * Callback invoked when user clicks "Edit Role" button for a user
   */
  onEditRole: (user: User) => void

  /**
   * Current page number (1-indexed)
   */
  page?: number

  /**
   * Results per page
   */
  limit?: number
}

/**
 * UserTable component - paginated table displaying all users with role management
 */
export function UserTable({
  onEditRole,
  page = 1,
  limit = 50,
}: UserTableProps): React.ReactElement {
  const { data, isLoading, isError, error } = useUsers({ page, limit })

  if (isLoading) {
    return <div className="hidden" aria-hidden="true" data-testid="loading" />
  }

  if (isError) {
    return <div>Error: {error?.message || 'Failed to load users'}</div>
  }

  const users = data?.users || []

  if (users.length === 0) {
    return <div>No users found</div>
  }

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Never'
    const date = new Date(dateString)
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const year = date.getFullYear()
    return `${month}/${day}/${year}`
  }

  const getRoleBadgeClasses = (role: string): string => {
    if (role === 'admin') {
      return 'bg-red-100 text-red-800 px-2 py-1 rounded text-xs font-medium'
    }
    return 'bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-medium'
  }

  return (
    <div>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Email
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Role
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Created
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Last Login
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.id} className="border-b hover:bg-gray-50">
              <td className="px-4 py-2">
                {user.display_name && <div className="font-medium">{user.display_name}</div>}
                <div className="text-gray-600">{user.email}</div>
              </td>
              <td className="px-4 py-2">
                <span className={getRoleBadgeClasses(user.role)}>{user.role}</span>
              </td>
              <td className="px-4 py-2">{formatDate(user.created_at)}</td>
              <td className="px-4 py-2">{formatDate(user.last_login)}</td>
              <td className="px-4 py-2">
                <button
                  type="button"
                  onClick={() => onEditRole(user)}
                  className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  Edit Role
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 text-sm text-gray-600">
        Page {page} of {data?.total_pages || 0} — {data?.total_count || 0} total users
      </div>
    </div>
  )
}
