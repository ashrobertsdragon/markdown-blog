import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminDashboard from '@/pages/AdminDashboard'

vi.mock('@/components/admin/AdminSidebar', () => ({
  default: vi.fn(
    ({ isOpen, onClose, onOpen }: { isOpen: boolean; onClose: () => void; onOpen: () => void }) => (
      <div data-testid="admin-sidebar" data-is-open={String(isOpen)}>
        <button type="button" data-testid="hamburger" onClick={onOpen}>
          menu
        </button>
        <button type="button" data-testid="close-btn" onClick={onClose}>
          close
        </button>
      </div>
    )
  ),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, Outlet: vi.fn(() => <div data-testid="outlet-content">outlet</div>) }
})

/**
 * Tests for the AdminDashboard layout component.
 *
 * Covers sidebar integration, Outlet rendering, sidebar open/close state
 * management, and layout structure for desktop and mobile viewports.
 */
describe('AdminDashboard', () => {
  const renderComponent = () =>
    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    )

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders AdminSidebar with isOpen false initially', () => {
    renderComponent()

    const sidebar = screen.getByTestId('admin-sidebar')
    expect(sidebar).toBeInTheDocument()
    expect(sidebar).toHaveAttribute('data-is-open', 'false')
  })

  it('renders Outlet for nested route content', () => {
    renderComponent()

    expect(screen.getByTestId('outlet-content')).toBeInTheDocument()
  })

  it('opens sidebar when onOpen is called', async () => {
    const user = userEvent.setup()
    renderComponent()

    const hamburger = screen.getByTestId('hamburger')
    await user.click(hamburger)

    expect(screen.getByTestId('admin-sidebar')).toHaveAttribute('data-is-open', 'true')
  })

  it('closes sidebar when onClose is called', async () => {
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByTestId('hamburger'))
    expect(screen.getByTestId('admin-sidebar')).toHaveAttribute('data-is-open', 'true')

    await user.click(screen.getByTestId('close-btn'))
    expect(screen.getByTestId('admin-sidebar')).toHaveAttribute('data-is-open', 'false')
  })

  it('renders a main element for page content', () => {
    renderComponent()

    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('applies desktop left-padding class to main element', () => {
    renderComponent()

    const main = screen.getByRole('main')
    expect(main.className).toMatch(/pl-64|md:pl-64/)
  })
})
