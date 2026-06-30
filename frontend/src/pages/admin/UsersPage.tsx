import { useState } from 'react'
import { RoleEditModal } from '@/components/admin/RoleEditModal'
import { UserTable } from '@/components/admin/UserTable'
import type { User } from '@/services/admin/adminApi'

const LIMIT = 50

/**
 * Admin page for managing users — lists all users with pagination and
 * provides an inline role-editing modal driven by UserTable's onEditRole callback.
 */
export default function UsersPage() {
  const [page, setPage] = useState(1)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-foreground mb-6">Users</h1>

      <UserTable page={page} limit={LIMIT} onEditRole={user => setSelectedUser(user)} />

      <nav aria-label="Pagination" className="mt-6 flex items-center gap-4">
        <button
          type="button"
          disabled={page === 1}
          onClick={() => setPage(p => Math.max(1, p - 1))}
          className="px-3 py-1 rounded border border-border text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted/40"
        >
          Previous
        </button>

        <span className="text-sm text-foreground">{page}</span>

        <button
          type="button"
          onClick={() => setPage(p => p + 1)}
          className="px-3 py-1 rounded border border-border text-sm hover:bg-muted/40"
        >
          Next
        </button>
      </nav>

      {selectedUser !== null && (
        <RoleEditModal user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
    </div>
  )
}
