import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '@/services/admin/adminApi'
import { createMockUser } from '../../../fixtures/users.fixtures'

let capturedOnEditRole: ((user: User) => void) | undefined

vi.mock('@/components/admin/UserTable', () => ({
  UserTable: vi.fn((props: { onEditRole: (user: User) => void; page?: number; limit?: number }) => {
    capturedOnEditRole = props.onEditRole
    return (
      <div
        data-testid="user-table"
        data-page={String(props.page ?? 1)}
        data-limit={String(props.limit ?? 50)}
      >
        user table
      </div>
    )
  }),
}))

vi.mock('@/components/admin/RoleEditModal', () => ({
  RoleEditModal: vi.fn((props: { user: User; onClose: () => void }) => (
    <div role="dialog" data-testid="role-edit-modal" data-user-id={String(props.user.id)}>
      role edit modal
      <button type="button" onClick={props.onClose}>
        close
      </button>
    </div>
  )),
}))

import UsersPage from '@/pages/admin/UsersPage'

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderComponent = () => {
  capturedOnEditRole = undefined
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <UsersPage />
    </QueryClientProvider>
  )
}

/**
 * Tests for the UsersPage admin component.
 *
 * Covers heading render, UserTable prop forwarding, RoleEditModal open/close
 * lifecycle driven by onEditRole, pagination state and button behaviour, and
 * pagination landmark accessibility.
 */
describe('UsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Render', () => {
    it('renders a heading with text matching /users/i', () => {
      renderComponent()

      expect(screen.getByRole('heading', { name: /users/i })).toBeInTheDocument()
    })

    it('renders UserTable with data-page="1" and data-limit="50" on initial mount', () => {
      renderComponent()

      const table = screen.getByTestId('user-table')
      expect(table).toBeInTheDocument()
      expect(table).toHaveAttribute('data-page', '1')
      expect(table).toHaveAttribute('data-limit', '50')
    })
  })

  describe('Modal lifecycle', () => {
    it('does NOT render RoleEditModal on initial mount', () => {
      renderComponent()

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders RoleEditModal with the user id when onEditRole is called', async () => {
      renderComponent()

      const user = createMockUser({ id: 42 })
      capturedOnEditRole?.(user)

      expect(await screen.findByRole('dialog')).toBeInTheDocument()
      expect(screen.getByTestId('role-edit-modal')).toHaveAttribute('data-user-id', '42')
    })

    it('removes RoleEditModal when its close button is clicked', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      const user = createMockUser({ id: 7 })
      capturedOnEditRole?.(user)

      expect(await screen.findByRole('dialog')).toBeInTheDocument()

      await interaction.click(screen.getByRole('button', { name: /close/i }))

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    it('renders a "Previous" button', () => {
      renderComponent()

      expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument()
    })

    it('renders a "Next" button', () => {
      renderComponent()

      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
    })

    it('renders current page number "1" initially', () => {
      renderComponent()

      expect(screen.getByText('1')).toBeInTheDocument()
    })

    it('"Previous" button is disabled on page 1', () => {
      renderComponent()

      expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled()
    })

    it('clicking "Next" updates UserTable data-page to "2"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('button', { name: /next/i }))

      expect(screen.getByTestId('user-table')).toHaveAttribute('data-page', '2')
    })

    it('clicking "Next" twice updates UserTable data-page to "3"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('button', { name: /next/i }))
      await interaction.click(screen.getByRole('button', { name: /next/i }))

      expect(screen.getByTestId('user-table')).toHaveAttribute('data-page', '3')
    })

    it('clicking "Next" then "Previous" keeps UserTable data-page at "1"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('button', { name: /next/i }))
      await interaction.click(screen.getByRole('button', { name: /previous/i }))

      expect(screen.getByTestId('user-table')).toHaveAttribute('data-page', '1')
    })

    it('"Previous" button becomes enabled after clicking "Next"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('button', { name: /next/i }))

      expect(screen.getByRole('button', { name: /previous/i })).toBeEnabled()
    })

    it('clicking "Previous" on page 1 does not go below page 1', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      // Previous is disabled on page 1, so clicking it should be a no-op
      await interaction.click(screen.getByRole('button', { name: /previous/i }))
      await interaction.click(screen.getByRole('button', { name: /previous/i }))

      expect(screen.getByTestId('user-table')).toHaveAttribute('data-page', '1')
    })

    it('displayed page number updates after clicking "Next"', async () => {
      const interaction = userEvent.setup()
      renderComponent()

      await interaction.click(screen.getByRole('button', { name: /next/i }))

      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('pagination nav has an accessible label (aria-label)', () => {
      renderComponent()

      expect(screen.getByRole('navigation', { name: /.+/ })).toBeInTheDocument()
    })
  })
})
