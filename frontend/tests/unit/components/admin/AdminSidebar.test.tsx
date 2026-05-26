import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminSidebar from '@/components/admin/AdminSidebar'

vi.mock('react-router-dom', () => ({
  NavLink: vi.fn(
    ({
      to,
      className,
      children,
      onClick,
    }: {
      to: string
      className?: (({ isActive }: { isActive: boolean }) => string) | string
      children: React.ReactNode
      onClick?: () => void
    }) => {
      const isActive = to === '/admin/users'
      const resolvedClass = typeof className === 'function' ? className({ isActive }) : className
      return (
        <a
          href={to}
          className={resolvedClass}
          onClick={onClick}
          data-testid={`nav-link-${to.replace(/\//g, '-')}`}
          aria-current={isActive ? 'page' : undefined}
        >
          {children}
        </a>
      )
    }
  ),
}))

const createTestClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithProviders = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={createTestClient()}>{ui}</QueryClientProvider>)

const defaultProps = {
  isOpen: false,
  onClose: vi.fn(),
  onOpen: vi.fn(),
}

/**
 * Test suite for AdminSidebar component
 *
 * Covers navigation link rendering, active-link styling via NavLink className
 * callback, mobile hamburger trigger, drawer open/closed state, backdrop
 * visibility and click behaviour, NavLink click dismissal, and Escape key
 * dismissal.
 */
describe('AdminSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Navigation links', () => {
    it('renders 3 navigation links', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      const links = screen.getAllByRole('link')
      expect(links).toHaveLength(3)
    })

    it('renders Users link to /admin/users', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      const link = screen.getByRole('link', { name: /users/i })
      expect(link).toHaveAttribute('href', '/admin/users')
    })

    it('renders Content link to /admin/content', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      const link = screen.getByRole('link', { name: /content/i })
      expect(link).toHaveAttribute('href', '/admin/content')
    })

    it('renders System link to /admin/system', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      const link = screen.getByRole('link', { name: /system/i })
      expect(link).toHaveAttribute('href', '/admin/system')
    })

    it('applies active styling to the active link', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      const usersLink = screen.getByRole('link', { name: /users/i })
      expect(usersLink).toHaveAttribute('aria-current', 'page')
    })

    it('applies inactive styling to non-active links', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      const contentLink = screen.getByRole('link', { name: /content/i })
      const systemLink = screen.getByRole('link', { name: /system/i })

      expect(contentLink).not.toHaveAttribute('aria-current', 'page')
      expect(systemLink).not.toHaveAttribute('aria-current', 'page')
    })
  })

  describe('Mobile hamburger', () => {
    it('renders a hamburger button with aria-label Open navigation', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} />)

      expect(screen.getByRole('button', { name: /open navigation/i })).toBeInTheDocument()
    })

    it('calls onOpen when hamburger button is clicked', async () => {
      const onOpen = vi.fn()
      renderWithProviders(<AdminSidebar {...defaultProps} onOpen={onOpen} />)

      await userEvent.click(screen.getByRole('button', { name: /open navigation/i }))

      expect(onOpen).toHaveBeenCalledOnce()
    })
  })

  describe('Mobile drawer', () => {
    it('sidebar has closed class when isOpen=false', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={false} />)

      const sidebar = screen.getByRole('navigation')
      expect(sidebar.className).toMatch(/translate-x-\[-100%\]|-translate-x-full/)
    })

    it('sidebar does not have closed class when isOpen=true', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={true} />)

      const sidebar = screen.getByRole('navigation')
      expect(sidebar.className).not.toMatch(/translate-x-\[-100%\]|-translate-x-full/)
    })

    it('backdrop is not visible when isOpen=false', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={false} />)

      const backdrop = screen.getByRole('presentation', { hidden: true })
      expect(backdrop).toHaveAttribute('aria-hidden', 'true')
    })

    it('backdrop is visible when isOpen=true', () => {
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={true} />)

      const backdrop = screen.getByRole('presentation')
      expect(backdrop).not.toHaveAttribute('aria-hidden', 'true')
    })

    it('calls onClose when backdrop is clicked', async () => {
      const onClose = vi.fn()
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={true} onClose={onClose} />)

      await userEvent.click(screen.getByRole('presentation'))

      expect(onClose).toHaveBeenCalledOnce()
    })
  })

  describe('Mobile interactions', () => {
    it('calls onClose when a nav link is clicked', async () => {
      const onClose = vi.fn()
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={true} onClose={onClose} />)

      await userEvent.click(screen.getByRole('link', { name: /users/i }))

      expect(onClose).toHaveBeenCalledOnce()
    })

    it('calls onClose when Escape key is pressed', async () => {
      const onClose = vi.fn()
      renderWithProviders(<AdminSidebar {...defaultProps} isOpen={true} onClose={onClose} />)

      await userEvent.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledOnce()
    })
  })
})
