import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NotificationToggle } from '@/components/preferences/NotificationToggle'

/**
 * Test suite for NotificationToggle component
 *
 * Verifies rendering, interaction, loading state, error handling with
 * auto-dismiss, disabled prop, and accessible label association.
 */
describe('NotificationToggle', () => {
  const createWrapper = () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )
    return wrapper
  }

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('renders the label text', () => {
    render(
      <NotificationToggle
        label="Notify on comment replies"
        checked={false}
        onToggle={vi.fn(async () => {})}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText('Notify on comment replies')).toBeInTheDocument()
  })

  it('renders a checkbox with the correct initial checked state when true', () => {
    render(
      <NotificationToggle
        label="Notify on mentions"
        checked={true}
        onToggle={vi.fn(async () => {})}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('renders a checkbox with the correct initial checked state when false', () => {
    render(
      <NotificationToggle
        label="Notify on mentions"
        checked={false}
        onToggle={vi.fn(async () => {})}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByRole('checkbox')).not.toBeChecked()
  })

  it('calls onToggle with true when an unchecked box is clicked', async () => {
    const onToggle = vi.fn(async () => {})

    render(<NotificationToggle label="Notify on new posts" checked={false} onToggle={onToggle} />, {
      wrapper: createWrapper(),
    })

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onToggle).toHaveBeenCalledWith(true)
  })

  it('calls onToggle with false when a checked box is clicked', async () => {
    const onToggle = vi.fn(async () => {})

    render(<NotificationToggle label="Notify on new posts" checked={true} onToggle={onToggle} />, {
      wrapper: createWrapper(),
    })

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onToggle).toHaveBeenCalledWith(false)
  })

  it('disables the checkbox while onToggle is pending', async () => {
    let resolveToggle!: () => void
    const onToggle = vi.fn(
      () =>
        new Promise<void>(resolve => {
          resolveToggle = resolve
        })
    )

    render(<NotificationToggle label="Notify on new posts" checked={false} onToggle={onToggle} />, {
      wrapper: createWrapper(),
    })

    await userEvent.click(screen.getByRole('checkbox'))

    expect(screen.getByRole('checkbox')).toBeDisabled()

    resolveToggle()
  })

  it('shows a loading spinner while onToggle is pending', async () => {
    let resolveToggle!: () => void
    const onToggle = vi.fn(
      () =>
        new Promise<void>(resolve => {
          resolveToggle = resolve
        })
    )

    render(<NotificationToggle label="Notify on new posts" checked={false} onToggle={onToggle} />, {
      wrapper: createWrapper(),
    })

    await userEvent.click(screen.getByRole('checkbox'))

    expect(screen.getByRole('status')).toBeInTheDocument()

    resolveToggle()
  })

  it('shows an error message when onToggle rejects', async () => {
    const onToggle = vi.fn(async () => {
      throw new Error('Update failed')
    })

    render(<NotificationToggle label="Notify on new posts" checked={false} onToggle={onToggle} />, {
      wrapper: createWrapper(),
    })

    await userEvent.click(screen.getByRole('checkbox'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('Update failed')
  })

  it('auto-dismisses the error message after 3 seconds', async () => {
    vi.useFakeTimers()
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const onToggle = vi.fn(async () => {
      throw new Error('Update failed')
    })

    render(<NotificationToggle label="Notify on new posts" checked={false} onToggle={onToggle} />, {
      wrapper: createWrapper(),
    })

    await user.click(screen.getByRole('checkbox'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())

    vi.advanceTimersByTime(3000)

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('does not call onToggle when the disabled prop is set', async () => {
    const onToggle = vi.fn(async () => {})

    render(
      <NotificationToggle
        label="Notify on new posts"
        checked={false}
        onToggle={onToggle}
        disabled={true}
      />,
      { wrapper: createWrapper() }
    )

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onToggle).not.toHaveBeenCalled()
  })

  it('renders the checkbox as disabled when the disabled prop is set', () => {
    render(
      <NotificationToggle
        label="Notify on new posts"
        checked={false}
        onToggle={vi.fn(async () => {})}
        disabled={true}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByRole('checkbox')).toBeDisabled()
  })

  it('associates the checkbox with its label for accessibility', () => {
    render(
      <NotificationToggle
        label="Notify on comment replies"
        checked={false}
        onToggle={vi.fn(async () => {})}
      />,
      { wrapper: createWrapper() }
    )

    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toHaveAccessibleName('Notify on comment replies')
  })
})
