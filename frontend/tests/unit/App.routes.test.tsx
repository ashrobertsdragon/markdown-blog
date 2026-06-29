import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '@/App'
import type { AuthContextType } from '@/context/AuthContext'

vi.mock('@/components/common/Layout', async () => {
  const { Outlet } = await import('react-router-dom')
  return {
    default: () => <Outlet />,
  }
})

vi.mock('@/pages/AdminDashboard', async () => {
  const { Outlet } = await import('react-router-dom')
  return {
    default: () => (
      <div data-testid="admin-dashboard">
        <Outlet />
      </div>
    ),
  }
})

vi.mock('@/pages/admin/ContentPage', () => ({
  default: () => <div data-testid="content-page">Content Page</div>,
}))

vi.mock('@/pages/admin/SystemPage', () => ({
  default: () => <div data-testid="system-page">System Page</div>,
}))

vi.mock('@/pages/admin/UserProfilePage', () => ({
  default: () => <div data-testid="user-profile-page">User Profile Page</div>,
}))

vi.mock('@/pages/admin/UsersPage', () => ({
  default: () => <div data-testid="users-page">Users Page</div>,
}))

vi.mock('@/pages/Home', () => ({
  default: () => <div data-testid="home-component">Home Page</div>,
}))

vi.mock('@/pages/Login', () => ({
  default: () => <div data-testid="login-component">Login Page</div>,
}))

vi.mock('@/pages/Forbidden', () => ({
  default: () => <div data-testid="forbidden-component">Forbidden Page</div>,
}))

vi.mock('@/pages/NotFound', () => ({
  default: () => <div data-testid="notfound-component">Not Found Page</div>,
}))

vi.mock('@/pages/Admin', () => ({
  default: () => <div data-testid="admin-component">Admin Page</div>,
}))

vi.mock('@/pages/Author', () => ({
  default: () => <div data-testid="author-component">Author Page</div>,
}))

vi.mock('@/pages/PublicPost', () => ({
  default: () => <div data-testid="public-post-component">Public Post Page</div>,
}))

vi.mock('@/pages/PostEditor', () => ({
  default: () => <div data-testid="post-editor-component">Post Editor Page</div>,
}))

vi.mock('@/pages/MyPosts', () => ({
  default: () => <div data-testid="my-posts-component">My Posts Page</div>,
}))

let mockAuthContext: AuthContextType

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => mockAuthContext,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

function renderRoute(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AppRoutes />
    </MemoryRouter>
  )
}

describe('App Routes - Protected Author Routes', () => {
  describe('/new-post route', () => {
    describe('when user is not authenticated', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: null,
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should redirect unauthenticated user to /login', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.getByTestId('login-component')).toBeInTheDocument()
        })
      })

      it('should not render PostEditor component for unauthenticated user', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.queryByTestId('post-editor-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is authenticated but not author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'user-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should redirect authenticated non-author to /forbidden', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        })
      })

      it('should not render PostEditor component for non-author', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.queryByTestId('post-editor-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'author-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PostEditor component for author', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.getByTestId('post-editor-component')).toBeInTheDocument()
        })
      })

      it('should not redirect author user', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
          expect(screen.queryByTestId('forbidden-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is admin', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'admin-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PostEditor component for admin (hierarchical access)', async () => {
        renderRoute('/new-post')

        await waitFor(() => {
          expect(screen.getByTestId('post-editor-component')).toBeInTheDocument()
        })
      })
    })
  })

  describe('/edit/:slug route', () => {
    const testSlug = 'test-post-slug'

    describe('when user is not authenticated', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: null,
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should redirect unauthenticated user to /login', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('login-component')).toBeInTheDocument()
        })
      })

      it('should not render PostEditor component for unauthenticated user', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.queryByTestId('post-editor-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is authenticated but not author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'user-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should redirect authenticated non-author to /forbidden', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        })
      })

      it('should not render PostEditor component for non-author', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.queryByTestId('post-editor-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'author-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PostEditor component for author', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('post-editor-component')).toBeInTheDocument()
        })
      })

      it('should not redirect author user', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
          expect(screen.queryByTestId('forbidden-component')).not.toBeInTheDocument()
        })
      })

      it('should handle different slug values correctly', async () => {
        const slugs = ['my-first-post', 'another-post', 'test-123']

        for (const slug of slugs) {
          const { unmount } = renderRoute(`/edit/${slug}`)

          await waitFor(() => {
            expect(screen.getByTestId('post-editor-component')).toBeInTheDocument()
          })

          unmount()
        }
      })
    })

    describe('when user is admin', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'admin-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PostEditor component for admin (hierarchical access)', async () => {
        renderRoute(`/edit/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('post-editor-component')).toBeInTheDocument()
        })
      })
    })
  })

  describe('/my-posts route', () => {
    describe('when user is not authenticated', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: null,
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should redirect unauthenticated user to /login', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.getByTestId('login-component')).toBeInTheDocument()
        })
      })

      it('should not render MyPosts component for unauthenticated user', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.queryByTestId('my-posts-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is authenticated but not author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'user-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should redirect authenticated non-author to /forbidden', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        })
      })

      it('should not render MyPosts component for non-author', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.queryByTestId('my-posts-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'author-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render MyPosts component for author', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.getByTestId('my-posts-component')).toBeInTheDocument()
        })
      })

      it('should not redirect author user', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
          expect(screen.queryByTestId('forbidden-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is admin', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'admin-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render MyPosts component for admin (hierarchical access)', async () => {
        renderRoute('/my-posts')

        await waitFor(() => {
          expect(screen.getByTestId('my-posts-component')).toBeInTheDocument()
        })
      })
    })
  })
})

describe('App Routes - Public Routes', () => {
  describe('/posts/:slug route', () => {
    const testSlug = 'my-blog-post'

    describe('when user is not authenticated', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: null,
          isLoaded: true,
          isSignedIn: false,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PublicPost component without authentication', async () => {
        renderRoute(`/posts/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('public-post-component')).toBeInTheDocument()
        })
      })

      it('should not redirect unauthenticated user', async () => {
        renderRoute(`/posts/${testSlug}`)

        await waitFor(() => {
          expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
          expect(screen.queryByTestId('forbidden-component')).not.toBeInTheDocument()
        })
      })

      it('should handle various slug formats', async () => {
        const slugs = ['simple-post', 'post-with-123-numbers', 'multiple-dashes-here']

        for (const slug of slugs) {
          const { unmount } = renderRoute(`/posts/${slug}`)

          await waitFor(() => {
            expect(screen.getByTestId('public-post-component')).toBeInTheDocument()
          })

          unmount()
        }
      })
    })

    describe('when user is authenticated', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'user-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'authenticated',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PublicPost component for authenticated user', async () => {
        renderRoute(`/posts/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('public-post-component')).toBeInTheDocument()
        })
      })

      it('should not redirect authenticated user', async () => {
        renderRoute(`/posts/${testSlug}`)

        await waitFor(() => {
          expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
          expect(screen.queryByTestId('forbidden-component')).not.toBeInTheDocument()
        })
      })
    })

    describe('when user is author', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'author-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'author',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PublicPost component for author', async () => {
        renderRoute(`/posts/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('public-post-component')).toBeInTheDocument()
        })
      })
    })

    describe('when user is admin', () => {
      beforeEach(() => {
        mockAuthContext = {
          user: { id: 'admin-1' },
          isLoaded: true,
          isSignedIn: true,
          role: 'admin',
          getToken: vi.fn(),
        } as unknown as AuthContextType
      })

      it('should render PublicPost component for admin', async () => {
        renderRoute(`/posts/${testSlug}`)

        await waitFor(() => {
          expect(screen.getByTestId('public-post-component')).toBeInTheDocument()
        })
      })
    })
  })
})

describe('App Routes - Loading States', () => {
  describe('when auth is not loaded', () => {
    beforeEach(() => {
      mockAuthContext = {
        user: null,
        isLoaded: false,
        isSignedIn: false,
        role: 'authenticated',
        getToken: vi.fn(),
      } as unknown as AuthContextType
    })

    it('should show loading spinner for protected /new-post route', () => {
      renderRoute('/new-post')

      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('should show loading spinner for protected /edit/:slug route', () => {
      renderRoute('/edit/test-slug')

      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('should show loading spinner for protected /my-posts route', () => {
      renderRoute('/my-posts')

      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('should not show loading spinner for public /posts/:slug route', () => {
      renderRoute('/posts/test-slug')

      expect(screen.queryByRole('status')).not.toBeInTheDocument()
      expect(screen.getByTestId('public-post-component')).toBeInTheDocument()
    })
  })
})

describe('App Routes - Admin Nested Routes', () => {
  describe('when user is not authenticated', () => {
    beforeEach(() => {
      mockAuthContext = {
        user: null,
        isLoaded: true,
        isSignedIn: false,
        role: 'authenticated',
        getToken: vi.fn(),
      } as unknown as AuthContextType
    })

    it('should redirect unauthenticated user to /login for /admin/users', async () => {
      renderRoute('/admin/users')

      await waitFor(() => {
        expect(screen.getByTestId('login-component')).toBeInTheDocument()
        expect(screen.queryByTestId('users-page')).not.toBeInTheDocument()
      })
    })

    it('should redirect unauthenticated user to /login for /admin/content', async () => {
      renderRoute('/admin/content')

      await waitFor(() => {
        expect(screen.getByTestId('login-component')).toBeInTheDocument()
        expect(screen.queryByTestId('content-page')).not.toBeInTheDocument()
      })
    })

    it('should redirect unauthenticated user to /login for /admin/system', async () => {
      renderRoute('/admin/system')

      await waitFor(() => {
        expect(screen.getByTestId('login-component')).toBeInTheDocument()
        expect(screen.queryByTestId('system-page')).not.toBeInTheDocument()
      })
    })
  })

  describe('when user is authenticated but not admin', () => {
    beforeEach(() => {
      mockAuthContext = {
        user: { id: 'user-1' },
        isLoaded: true,
        isSignedIn: true,
        role: 'authenticated',
        getToken: vi.fn(),
      } as unknown as AuthContextType
    })

    it('should redirect non-admin to /forbidden for /admin/users', async () => {
      renderRoute('/admin/users')

      await waitFor(() => {
        expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        expect(screen.queryByTestId('users-page')).not.toBeInTheDocument()
      })
    })

    it('should redirect non-admin to /forbidden for /admin/content', async () => {
      renderRoute('/admin/content')

      await waitFor(() => {
        expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        expect(screen.queryByTestId('content-page')).not.toBeInTheDocument()
      })
    })

    it('should redirect non-admin to /forbidden for /admin/system', async () => {
      renderRoute('/admin/system')

      await waitFor(() => {
        expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        expect(screen.queryByTestId('system-page')).not.toBeInTheDocument()
      })
    })
  })

  describe('when user is author (not admin)', () => {
    beforeEach(() => {
      mockAuthContext = {
        user: { id: 'author-1' },
        isLoaded: true,
        isSignedIn: true,
        role: 'author',
        getToken: vi.fn(),
      } as unknown as AuthContextType
    })

    it('should redirect author to /forbidden for /admin/users', async () => {
      renderRoute('/admin/users')

      await waitFor(() => {
        expect(screen.getByTestId('forbidden-component')).toBeInTheDocument()
        expect(screen.queryByTestId('users-page')).not.toBeInTheDocument()
      })
    })
  })

  describe('when user is admin', () => {
    beforeEach(() => {
      mockAuthContext = {
        user: { id: 'admin-1' },
        isLoaded: true,
        isSignedIn: true,
        role: 'admin',
        getToken: vi.fn(),
      } as unknown as AuthContextType
    })

    it('should render UsersPage at /admin/users', async () => {
      renderRoute('/admin/users')

      await waitFor(() => {
        expect(screen.getByTestId('users-page')).toBeInTheDocument()
        expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
        expect(screen.queryByTestId('forbidden-component')).not.toBeInTheDocument()
      })
    })

    it('should render ContentPage at /admin/content', async () => {
      renderRoute('/admin/content')

      await waitFor(() => {
        expect(screen.getByTestId('content-page')).toBeInTheDocument()
        expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
      })
    })

    it('should render SystemPage at /admin/system', async () => {
      renderRoute('/admin/system')

      await waitFor(() => {
        expect(screen.getByTestId('system-page')).toBeInTheDocument()
        expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
      })
    })

    it('should render UserProfilePage at /admin/users/:userId', async () => {
      renderRoute('/admin/users/42')

      await waitFor(() => {
        expect(screen.getByTestId('user-profile-page')).toBeInTheDocument()
        expect(screen.queryByTestId('login-component')).not.toBeInTheDocument()
      })
    })

    it('should redirect /admin to /admin/users', async () => {
      renderRoute('/admin')

      await waitFor(() => {
        expect(screen.getByTestId('users-page')).toBeInTheDocument()
      })
    })
  })

  describe('when auth is loading', () => {
    beforeEach(() => {
      mockAuthContext = {
        user: null,
        isLoaded: false,
        isSignedIn: false,
        role: 'authenticated',
        getToken: vi.fn(),
      } as unknown as AuthContextType
    })

    it('should show loading spinner for /admin/users while auth loads', () => {
      renderRoute('/admin/users')

      expect(screen.getByRole('status')).toBeInTheDocument()
      expect(screen.queryByTestId('users-page')).not.toBeInTheDocument()
    })
  })
})
