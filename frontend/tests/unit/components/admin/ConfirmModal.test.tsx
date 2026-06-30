import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ConfirmModal from '@/components/admin/ConfirmModal'

const defaultProps = {
  title: 'Delete post',
  message: 'Are you sure you want to delete this post? This action cannot be undone.',
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
}

/**
 * Test suite for ConfirmModal component.
 *
 * ConfirmModal is built on the ShadCN AlertDialog primitive (Radix), so these
 * tests cover the behavioural contract — alertdialog semantics, title/message
 * rendering, confirm/cancel button defaults and custom text, the confirm and
 * cancel callbacks, and Escape-to-cancel. Focus trapping and overlay handling
 * are owned by Radix and are not re-asserted here.
 */
describe('ConfirmModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders an alertdialog element', () => {
      render(<ConfirmModal {...defaultProps} />)

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    it('displays the title prop', () => {
      render(<ConfirmModal {...defaultProps} />)

      expect(screen.getByText('Delete post')).toBeInTheDocument()
    })

    it('displays the message prop', () => {
      render(<ConfirmModal {...defaultProps} />)

      expect(
        screen.getByText('Are you sure you want to delete this post? This action cannot be undone.')
      ).toBeInTheDocument()
    })

    it('links aria-labelledby to the title element', () => {
      render(<ConfirmModal {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      const labelledById = dialog.getAttribute('aria-labelledby')
      expect(labelledById).not.toBeNull()
      const titleElement = document.getElementById(labelledById as string)
      expect(titleElement?.textContent).toBe('Delete post')
    })

    it('links aria-describedby to the message element', () => {
      render(<ConfirmModal {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      const describedById = dialog.getAttribute('aria-describedby')
      expect(describedById).not.toBeNull()
      const messageElement = document.getElementById(describedById as string)
      expect(messageElement?.textContent).toBe(
        'Are you sure you want to delete this post? This action cannot be undone.'
      )
    })

    it('renders a confirm button with default text "Confirm"', () => {
      render(<ConfirmModal {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument()
    })

    it('renders a cancel button with default text "Cancel"', () => {
      render(<ConfirmModal {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('renders confirm button with custom confirmText', () => {
      render(<ConfirmModal {...defaultProps} confirmText="Yes, delete" />)

      expect(screen.getByRole('button', { name: 'Yes, delete' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Confirm' })).not.toBeInTheDocument()
    })

    it('renders cancel button with custom cancelText', () => {
      render(<ConfirmModal {...defaultProps} cancelText="No, keep it" />)

      expect(screen.getByRole('button', { name: 'No, keep it' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
    })
  })

  describe('Button interactions', () => {
    it('calls onConfirm when the confirm button is clicked', async () => {
      const onConfirm = vi.fn()
      render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />)

      await userEvent.click(screen.getByRole('button', { name: 'Confirm' }))

      expect(onConfirm).toHaveBeenCalledOnce()
    })

    it('calls onCancel when the cancel button is clicked', async () => {
      const onCancel = vi.fn()
      render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)

      await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))

      expect(onCancel).toHaveBeenCalledOnce()
    })

    it('does not call onConfirm when the cancel button is clicked', async () => {
      const onConfirm = vi.fn()
      render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />)

      await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))

      expect(onConfirm).not.toHaveBeenCalled()
    })
  })

  describe('Keyboard interactions', () => {
    it('calls onCancel when Escape key is pressed', async () => {
      const onCancel = vi.fn()
      render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)

      await userEvent.keyboard('{Escape}')

      expect(onCancel).toHaveBeenCalledOnce()
    })

    it('does not call onConfirm when Escape key is pressed', async () => {
      const onConfirm = vi.fn()
      render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />)

      await userEvent.keyboard('{Escape}')

      expect(onConfirm).not.toHaveBeenCalled()
    })
  })
})
