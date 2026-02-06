import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AuthProvider } from '@/context/AuthContext'
import Admin from '@/pages/Admin'
import Author from '@/pages/Author'
import Forbidden from '@/pages/Forbidden'
import Home from '@/pages/Home'
import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'

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
 * Exported separately to allow testing with different router types
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/forbidden" element={<Forbidden />} />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requireRole="admin">
            <Admin />
          </ProtectedRoute>
        }
      />
      <Route
        path="/author"
        element={
          <ProtectedRoute requireRole="author">
            <Author />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFound />} />
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
 * Routes:
 * - "/" - Home page displaying system health status
 * - "/login" - Login page for authentication
 * - "/forbidden" - Forbidden page for unauthorized access
 * - "/admin" - Admin dashboard (protected, requires admin role)
 * - "/author" - Author dashboard (protected, requires author role)
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
    </QueryClientProvider>
  )
}
