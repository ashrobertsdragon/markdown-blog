import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { NotificationToggle } from '@/components/preferences/NotificationToggle'

/**
 * Test suite for NotificationToggle component
 *
 * Verifies rendering, interaction, disabled prop, and accessible label association.
 * Component is presentational only — async logic and error handling are in parent.
 */
describe('NotificationToggle', () => {
  it('renders the label text', () => {
    render(
      <NotificationToggle label="Notify on comment replies" checked={false} onChange={vi.fn()} />
    )

    expect(screen.getByText('Notify on comment replies')).toBeInTheDocument()
  })

  it('renders a checkbox with the correct initial checked state when true', () => {
    render(<NotificationToggle label="Notify on mentions" checked={true} onChange={vi.fn()} />)

    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('renders a checkbox with the correct initial checked state when false', () => {
    render(<NotificationToggle label="Notify on mentions" checked={false} onChange={vi.fn()} />)

    expect(screen.getByRole('checkbox')).not.toBeChecked()
  })

  it('calls onChange with true when an unchecked box is clicked', async () => {
    const onChange = vi.fn()

    render(<NotificationToggle label="Notify on new posts" checked={false} onChange={onChange} />)

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('calls onChange with false when a checked box is clicked', async () => {
    const onChange = vi.fn()

    render(<NotificationToggle label="Notify on new posts" checked={true} onChange={onChange} />)

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onChange).toHaveBeenCalledWith(false)
  })

  it('renders the checkbox as disabled when the disabled prop is set', () => {
    render(
      <NotificationToggle
        label="Notify on new posts"
        checked={false}
        onChange={vi.fn()}
        disabled={true}
      />
    )

    expect(screen.getByRole('checkbox')).toBeDisabled()
  })

  it('does not call onChange when the disabled prop is set', async () => {
    const onChange = vi.fn()

    render(
      <NotificationToggle
        label="Notify on new posts"
        checked={false}
        onChange={onChange}
        disabled={true}
      />
    )

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onChange).not.toHaveBeenCalled()
  })

  it('associates the checkbox with its label for accessibility', () => {
    render(
      <NotificationToggle label="Notify on comment replies" checked={false} onChange={vi.fn()} />
    )

    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toHaveAccessibleName('Notify on comment replies')
  })
})
