import { Menu } from 'lucide-react'
import { useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface AdminSidebarProps {
  isOpen: boolean
  onClose: () => void
  onOpen: () => void
}

interface NavItem {
  to: string
  label: string
}

const navLinks: NavItem[] = [
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/content', label: 'Content' },
  { to: '/admin/system', label: 'System' },
]

/**
 * AdminSidebar renders a responsive navigation drawer for the admin panel.
 *
 * @param isOpen - Whether the mobile drawer is currently open
 * @param onClose - Callback invoked when the drawer should close (backdrop click, nav link click, Escape key)
 * @param onOpen - Callback invoked when the hamburger button is clicked to open the drawer
 */
export default function AdminSidebar({ isOpen, onClose, onOpen }: AdminSidebarProps) {
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  return (
    <>
      <button
        type="button"
        aria-label="Open navigation"
        aria-expanded={isOpen}
        aria-controls="admin-sidebar"
        onClick={onOpen}
        className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-md bg-white border border-gray-200 shadow-sm"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div
        role="presentation"
        aria-hidden={!isOpen}
        data-testid="sidebar-backdrop"
        onClick={onClose}
        style={!isOpen ? { opacity: 0, pointerEvents: 'none' } : undefined}
        className="fixed inset-0 bg-black/50 z-30 md:hidden"
      />

      <nav
        id="admin-sidebar"
        data-testid="admin-sidebar"
        aria-label="Admin"
        className={cn(
          'fixed top-0 left-0 h-screen w-64 flex flex-col bg-white border-r border-gray-200 z-40',
          'transition-transform duration-300',
          'md:translate-x-0',
          !isOpen && '-translate-x-full'
        )}
      >
        <ul className="flex flex-col gap-1 p-4">
          {navLinks.map(({ to, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'block px-4 py-2 rounded-md text-sm font-medium',
                    isActive ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-100'
                  )
                }
              >
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}
