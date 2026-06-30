import type React from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Email</TableHead>
            <TableHead scope="col">Role</TableHead>
            <TableHead scope="col">Created</TableHead>
            <TableHead scope="col">Last Login</TableHead>
            <TableHead scope="col">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map(user => (
            <TableRow key={user.id}>
              <TableCell>
                {user.display_name && <div className="font-medium">{user.display_name}</div>}
                <div className="text-muted-foreground">{user.email}</div>
              </TableCell>
              <TableCell>
                <Badge variant={user.role === 'admin' ? 'destructive' : 'secondary'}>
                  {user.role}
                </Badge>
              </TableCell>
              <TableCell>{formatDate(user.created_at)}</TableCell>
              <TableCell>{formatDate(user.last_login)}</TableCell>
              <TableCell>
                <Button type="button" size="sm" onClick={() => onEditRole(user)}>
                  Edit Role
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="mt-4 text-sm text-muted-foreground">
        Page {page} of {data?.total_pages || 0} — {data?.total_count || 0} total users
      </div>
    </div>
  )
}
