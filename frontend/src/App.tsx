import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'react-hot-toast'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import Layout from '@/components/common/Layout'
import { AuthProvider } from '@/context/AuthContext'
import AdminDashboard from '@/pages/AdminDashboard'
import Author from '@/pages/Author'
import ContentPage from '@/pages/admin/ContentPage'
import SystemPage from '@/pages/admin/SystemPage'
import UserProfilePage from '@/pages/admin/UserProfilePage'
import UsersPage from '@/pages/admin/UsersPage'
import Forbidden from '@/pages/Forbidden'
import Home from '@/pages/Home'
import Login from '@/pages/Login'
import MyPosts from '@/pages/MyPosts'
import NotFound from '@/pages/NotFound'
import NotificationPreferences from '@/pages/NotificationPreferences'
import PostEditor from '@/pages/PostEditor'
import PublicPost from '@/pages/PublicPost'
import RevisionDetailPage from '@/pages/RevisionDetailPage'
import RevisionDiffPage from '@/pages/RevisionDiffPage'
import RevisionHistory from '@/pages/RevisionHistory'
import Unsubscribe from '@/pages/Unsubscribe'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 3,
      refetchOnWindowFocus: false,
    },
  },
})

/**
 * Application routes component
 *
 * Defines all application routes with role-based access control.
 * Routes are organized by access level: public, admin-only, author-only.
 * Exported separately to allow testing with different router types.
 *
 * Route ordering:
 * 1. Public routes (no authentication required)
 * 2. Admin routes (requireRole="admin")
 * 3. Author routes (requireRole="author")
 * 4. Parameterized routes (specific before generic)
 * 5. Catch-all routes (404)
 */
export function AppRoutes() {
  return (
    <Routes>
      {/* Admin routes - own chrome (AdminDashboard + AdminSidebar), no Layout wrapper */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute requireRole="admin">
            <AdminDashboard />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="users" replace />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="users/:userId" element={<UserProfilePage />} />
        <Route path="content" element={<ContentPage />} />
        <Route path="system" element={<SystemPage />} />
      </Route>

      {/* All other routes share the persistent Header via Layout */}
      <Route element={<Layout />}>
        {/* Public routes */}
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forbidden" element={<Forbidden />} />
        <Route path="/unsubscribe" element={<Unsubscribe />} />
        <Route path="/posts/:slug" element={<PublicPost />} />
        <Route
          path="/posts/:slug/revisions"
          element={
            <ProtectedRoute requireRole="authenticated">
              <RevisionHistory />
            </ProtectedRoute>
          }
        />
        <Route
          path="/posts/:slug/revisions/:sha"
          element={
            <ProtectedRoute requireRole="authenticated">
              <RevisionDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/posts/:slug/revisions/:sha/diff/:otherSha"
          element={
            <ProtectedRoute requireRole="authenticated">
              <RevisionDiffPage />
            </ProtectedRoute>
          }
        />

        {/* Authenticated routes */}
        <Route
          path="/settings/notifications"
          element={
            <ProtectedRoute requireRole="authenticated">
              <NotificationPreferences />
            </ProtectedRoute>
          }
        />

        {/* Author routes */}
        <Route
          path="/author"
          element={
            <ProtectedRoute requireRole="author">
              <Author />
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-posts"
          element={
            <ProtectedRoute requireRole="author">
              <MyPosts />
            </ProtectedRoute>
          }
        />
        <Route
          path="/new-post"
          element={
            <ProtectedRoute requireRole="author">
              <PostEditor />
            </ProtectedRoute>
          }
        />
        <Route
          path="/edit/:slug"
          element={
            <ProtectedRoute requireRole="author">
              <PostEditor />
            </ProtectedRoute>
          }
        />

        {/* Catch-all */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

/**
 * Root application component with client-side routing
 *
 * Provides the main routing structure for the blog platform application.
 * Uses React Router's BrowserRouter for client-side navigation without hash symbols.
 * Configured for deployment at root domain (no basename).
 *
 * Server state is managed via React Query (QueryClientProvider) with these defaults:
 * - staleTime: 5 minutes — cached data stays fresh for 5 minutes
 * - gcTime: 10 minutes — unused cache entries are garbage collected after 10 minutes
 * - retry: 3 — failed requests are retried up to 3 times
 * - refetchOnWindowFocus: false — no automatic refetch on tab/window focus
 * React Query devtools are mounted in development mode only (tree-shaken from production builds).
 *
 * Routes:
 * - "/" - Home page displaying system health status
 * - "/login" - Login page for authentication
 * - "/forbidden" - Forbidden page for unauthorized access
 * - "/admin" - Redirects to /admin/users (protected, requires admin role)
 * - "/admin/users" - User management page (protected, requires admin role)
 * - "/admin/users/:userId" - User profile page (protected, requires admin role)
 * - "/admin/content" - Content moderation page (protected, requires admin role)
 * - "/admin/system" - System health page (protected, requires admin role)
 * - "/author" - Author dashboard (protected, requires author role)
 * - "/new-post" - Post editor for creating new posts (protected, requires author role)
 * - "/edit/:slug" - Post editor for editing existing posts (protected, requires author role)
 * - "/my-posts" - Author's post management page (protected, requires author role)
 * - "/posts/:slug" - Public post view page
 * - "*" - 404 Not Found page for unmatched routes
 *
 * @returns Root application component with routing configuration
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
      <div data-testid="toaster">
        <Toaster
          position="bottom-right"
          reverseOrder={false}
          gutter={8}
          toastOptions={{
            duration: 3500,
            style: {
              background: 'var(--card)',
              color: 'var(--card-foreground)',
              border: '1px solid var(--border)',
            },
          }}
        />
      </div>
    </QueryClientProvider>
  )
}
