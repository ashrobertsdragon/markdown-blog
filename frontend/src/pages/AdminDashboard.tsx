import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import AdminSidebar from '@/components/admin/AdminSidebar'

/**
 * Single ownership point for sidebar open/close state across all admin routes.
 *
 * Keeping this state here rather than inside AdminSidebar lets any nested
 * route trigger sidebar close (e.g., after a nav-link click) without prop
 * drilling through unrelated subtrees. The Outlet renders whatever admin
 * sub-route is active inside the stable shell.
 */
export default function AdminDashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      <AdminSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onOpen={() => setSidebarOpen(true)}
      />
      <main className="pt-16 md:pt-0 md:pl-64">
        <Outlet />
      </main>
    </div>
  )
}
