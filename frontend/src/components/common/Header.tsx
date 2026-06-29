import { UserButton } from '@clerk/clerk-react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

/**
 * Persistent top navigation bar rendered on all non-admin pages.
 *
 * Role-conditional links: My Posts and New Post appear for authors and admins;
 * Admin appears only for admins. The Clerk UserButton handles profile and sign-out
 * natively; unauthenticated users see a plain Sign in link instead.
 */
export default function Header() {
  const { isSignedIn, role } = useAuth()

  const isAuthorOrAbove = isSignedIn && (role === 'author' || role === 'admin')
  const isAdmin = isSignedIn && role === 'admin'

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? 'text-foreground font-medium transition-colors'
      : 'text-muted-foreground hover:text-foreground transition-colors'

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="font-semibold text-foreground">
          AshlynnAntrobus.dev
        </Link>

        <nav className="flex flex-1 items-center gap-4 text-sm">
          {isAuthorOrAbove && (
            <>
              <NavLink to="/my-posts" className={navLinkClass}>
                My Posts
              </NavLink>
              <NavLink to="/new-post" className={navLinkClass}>
                New Post
              </NavLink>
            </>
          )}
          {isAdmin && (
            <NavLink to="/admin" className={navLinkClass}>
              Admin
            </NavLink>
          )}
        </nav>

        <div>
          {isSignedIn ? (
            <UserButton afterSignOutUrl="/" />
          ) : (
            <Link
              to="/login"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
