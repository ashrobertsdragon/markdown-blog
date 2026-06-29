import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RoleEditModal } from '@/components/admin/RoleEditModal'
import { useUpdateUserRole } from '@/hooks/admin/useUsers'
import { createMockAdminUser, createMockUser } from '../../../fixtures/users.fixtures'

/**
 * RoleEditModal component test suite.
 *
 * Tests a standalone modal that lets admins change a user's role via radio
 * buttons. Covers rendering (email, radio buttons, pre-selection), submit
 * button state (disabled when unchanged, enabled when changed, loading while
 * pending), mutation invocation, onClose callbacks (cancel button, Escape key,
 * backdrop click, mutation success), and ARIA accessibility attributes.
 */

vi.mock('@/hooks/admin/useUsers', () => ({
  useUsers: vi.fn(),
  useUpdateUserRole: vi.fn(),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const baseMockMutation = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
  isIdle: true,
  isSuccess: false,
  reset: vi.fn(),
  mutateAsync: vi.fn(),
  data: undefined,
  failureCount: 0,
  failureReason: null,
  isPaused: false,
  status: 'idle' as const,
  submittedAt: 0,
  variables: undefined,
  context: undefined,
}

describe('RoleEditModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useUpdateUserRole).mockReturnValue(baseMockMutation as never)
  })

  describe('Rendering', () => {
    it('displays the user email inside the modal', () => {
      const user = createMockUser({ email: 'target@example.com' })
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByText('target@example.com')).toBeInTheDocument()
    })

    it('renders a radio button for the authenticated role', () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByRole('radio', { name: /authenticated/i })).toBeInTheDocument()
    })

    it('renders a radio button for the admin role', () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByRole('radio', { name: /admin/i })).toBeInTheDocument()
    })

    it('pre-selects the authenticated radio when user role is authenticated', () => {
      const user = createMockUser({ role: 'authenticated' })
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByRole('radio', { name: /authenticated/i })).toBeChecked()
      expect(screen.getByRole('radio', { name: /admin/i })).not.toBeChecked()
    })

    it('pre-selects the admin radio when user role is admin', () => {
      const user = createMockAdminUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByRole('radio', { name: /admin/i })).toBeChecked()
      expect(screen.getByRole('radio', { name: /authenticated/i })).not.toBeChecked()
    })
  })

  describe('Submit button state', () => {
    it('is disabled when the selected role matches the user current role', () => {
      const user = createMockUser({ role: 'authenticated' })
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByRole('button', { name: /save|submit|update/i })).toBeDisabled()
    })

    it('becomes enabled when a different role is selected', async () => {
      const user = createMockUser({ role: 'authenticated' })
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      await userEvent.click(screen.getByRole('radio', { name: /admin/i }))

      expect(screen.getByRole('button', { name: /save|submit|update/i })).toBeEnabled()
    })

    it('is disabled and shows loading text when mutation isPending is true', () => {
      const user = createMockUser({ role: 'authenticated' })
      const onClose = vi.fn()
      vi.mocked(useUpdateUserRole).mockReturnValue({
        ...baseMockMutation,
        isPending: true,
        isIdle: false,
        status: 'pending',
      } as never)

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      const submitButton = screen.getByRole('button', { name: /saving/i })
      expect(submitButton).toBeDisabled()
    })
  })

  describe('Mutation invocation', () => {
    it('calls mutate with userId and new role when submit is clicked', async () => {
      const mockMutate = vi.fn()
      const user = createMockUser({ id: 7, role: 'authenticated' })
      const onClose = vi.fn()
      vi.mocked(useUpdateUserRole).mockReturnValue({
        ...baseMockMutation,
        mutate: mockMutate,
      } as never)

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      await userEvent.click(screen.getByRole('radio', { name: /admin/i }))
      await userEvent.click(screen.getByRole('button', { name: /save|submit|update/i }))

      expect(mockMutate).toHaveBeenCalledWith(
        { userId: 7, role: 'admin' },
        expect.objectContaining({ onSuccess: expect.any(Function) })
      )
    })

    it('does not call mutate when submit is clicked with role unchanged', async () => {
      const mockMutate = vi.fn()
      const user = createMockUser({ role: 'authenticated' })
      const onClose = vi.fn()
      vi.mocked(useUpdateUserRole).mockReturnValue({
        ...baseMockMutation,
        mutate: mockMutate,
      } as never)

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      const submitButton = screen.getByRole('button', { name: /save|submit|update/i })
      expect(submitButton).toBeDisabled()

      expect(mockMutate).not.toHaveBeenCalled()
    })
  })

  describe('onClose callbacks', () => {
    it('calls onClose when the cancel button is clicked', async () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

      expect(onClose).toHaveBeenCalledOnce()
    })

    it('calls onClose when the Escape key is pressed', async () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      await userEvent.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledOnce()
    })

    it('calls onClose when the dialog close button is clicked', async () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      const closeButton = screen.getByRole('button', { name: /close/i })
      await userEvent.click(closeButton)

      expect(onClose).toHaveBeenCalledOnce()
    })

    it('calls onClose after mutation succeeds via onSuccess callback', async () => {
      const onClose = vi.fn()
      const user = createMockUser({ id: 3, role: 'authenticated' })
      let capturedOnSuccess: (() => void) | undefined

      vi.mocked(useUpdateUserRole).mockImplementation(() => {
        return {
          ...baseMockMutation,
          mutate: vi.fn((_vars, options?: { onSuccess?: () => void }) => {
            capturedOnSuccess = options?.onSuccess
          }),
        } as never
      })

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      await userEvent.click(screen.getByRole('radio', { name: /admin/i }))
      await userEvent.click(screen.getByRole('button', { name: /save|submit|update/i }))

      capturedOnSuccess?.()

      expect(onClose).toHaveBeenCalledOnce()
    })

    it('does not call onClose when the mutation errors', async () => {
      const onClose = vi.fn()
      const user = createMockUser({ id: 3, role: 'authenticated' })

      vi.mocked(useUpdateUserRole).mockImplementation(() => {
        return {
          ...baseMockMutation,
          mutate: vi.fn(
            (_vars, options?: { onSuccess?: () => void; onError?: (err: Error) => void }) => {
              options?.onError?.(new Error('Network error'))
            }
          ),
        } as never
      })

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      await userEvent.click(screen.getByRole('radio', { name: /admin/i }))
      await userEvent.click(screen.getByRole('button', { name: /save|submit|update/i }))

      expect(onClose).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('renders an element with role="dialog"', () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('has aria-labelledby pointing to a heading element about role editing', () => {
      const user = createMockUser()
      const onClose = vi.fn()

      renderWithQueryClient(<RoleEditModal user={user} onClose={onClose} />)

      const dialog = screen.getByRole('dialog')
      const labelledById = dialog.getAttribute('aria-labelledby')
      expect(labelledById).not.toBeNull()

      const titleElement = document.getElementById(labelledById as string)
      expect(titleElement).not.toBeNull()
      expect(titleElement?.textContent).toMatch(/role/i)
    })
  })
})
