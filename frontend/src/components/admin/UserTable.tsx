import type React from 'react'
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
export function UserTable(props: UserTableProps): React.ReactElement {
  // TODO: Implement UserTable component
  // Props are destructured in the implementation
  void props
  return <div>UserTable component not yet implemented</div>
}
