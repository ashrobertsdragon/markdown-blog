import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import NotificationPreferences from '@/pages/NotificationPreferences'

const mockMutateAsync = vi.fn()

vi.mock('@/hooks/useNotificationPreferences', () => ({
  useNotificationPreferences: vi.fn(),
  useUpdateNotificationPreferences: vi.fn(),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    isLoaded: true,
    getToken: vi.fn(async () => 'mock-token'),
    user: null,
    role: 'authenticated' as const,
  })),
}))

vi.mock('@/components/preferences/NotificationToggle', () => ({
  NotificationToggle: ({
    label,
    checked,
    onChange,
    disabled,
  }: {
    label: string
    checked: boolean
    onChange: (value: boolean) => void
    disabled?: boolean
  }) => (
    <div>
      <label>
        {label}
        <input
          type="checkbox"
          checked={checked}
          onChange={e => onChange(e.target.checked)}
          aria-label={label}
          disabled={disabled}
        />
      </label>
    </div>
  ),
}))

import { useAuth } from '@/hooks/useAuth'
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from '@/hooks/useNotificationPreferences'

/**
 * Test suite for NotificationPreferences page
 *
 * Verifies loading skeleton, toggle rendering with correct values, mutation
 * wiring, success/error alerts with auto-dismiss, and unauthenticated redirect.
 */
describe('NotificationPreferences page', () => {
  const defaultPreferences = {
    user_id: 1,
    notify_on_comment_replies: true,
    notify_on_mentions: false,
    notify_on_new_posts: true,
  }

  const defaultMutation = {
    mutateAsync: mockMutateAsync,
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    isIdle: true,
    isSuccess: false,
    reset: vi.fn(),
    data: undefined,
    failureCount: 0,
    failureReason: null,
    isPaused: false,
    status: 'idle' as const,
    submittedAt: 0,
    variables: undefined,
    context: undefined,
  }

  beforeEach(() => {
    vi.mocked(useNotificationPreferences).mockReturnValue({
      data: defaultPreferences,
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: true,
    } as ReturnType<typeof useNotificationPreferences>)
    vi.mocked(useUpdateNotificationPreferences).mockReturnValue(
      defaultMutation as ReturnType<typeof useUpdateNotificationPreferences>
    )
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <NotificationPreferences />
      </MemoryRouter>
    )

  it('shows a loading skeleton when preferences are loading', () => {
    vi.mocked(useNotificationPreferences).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      isSuccess: false,
    } as ReturnType<typeof useNotificationPreferences>)

    renderPage()

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('renders three toggles after preferences load', () => {
    renderPage()

    expect(screen.getAllByRole('checkbox')).toHaveLength(3)
  })

  it('renders a toggle for comment reply notifications', () => {
    renderPage()

    expect(screen.getByLabelText('Notify on comment replies')).toBeInTheDocument()
  })

  it('renders a toggle for mention notifications', () => {
    renderPage()

    expect(screen.getByLabelText('Notify on mentions')).toBeInTheDocument()
  })

  it('renders a toggle for new post notifications', () => {
    renderPage()

    expect(screen.getByLabelText('Notify on new posts')).toBeInTheDocument()
  })

  it('reflects notify_on_comment_replies preference value as checked', () => {
    renderPage()

    expect(screen.getByLabelText('Notify on comment replies')).toBeChecked()
  })

  it('reflects notify_on_mentions preference value as unchecked', () => {
    renderPage()

    expect(screen.getByLabelText('Notify on mentions')).not.toBeChecked()
  })

  it('reflects notify_on_new_posts preference value as checked', () => {
    renderPage()

    expect(screen.getByLabelText('Notify on new posts')).toBeChecked()
  })

  it('calls mutateAsync with correct args when comment reply toggle changes', async () => {
    mockMutateAsync.mockResolvedValueOnce(undefined)
    renderPage()

    await userEvent.click(screen.getByLabelText('Notify on comment replies'))

    await waitFor(() =>
      expect(mockMutateAsync).toHaveBeenCalledWith({ notify_on_comment_replies: false })
    )
  })

  it('calls mutateAsync with correct args when mention toggle changes', async () => {
    mockMutateAsync.mockResolvedValueOnce(undefined)
    renderPage()

    await userEvent.click(screen.getByLabelText('Notify on mentions'))

    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalledWith({ notify_on_mentions: true }))
  })

  it('calls mutateAsync with correct args when new post toggle changes', async () => {
    mockMutateAsync.mockResolvedValueOnce(undefined)
    renderPage()

    await userEvent.click(screen.getByLabelText('Notify on new posts'))

    await waitFor(() =>
      expect(mockMutateAsync).toHaveBeenCalledWith({ notify_on_new_posts: false })
    )
  })

  it('shows a success alert after a successful mutation', async () => {
    const mockMutation = {
      ...defaultMutation,
      mutateAsync: vi.fn(async () => ({
        user_id: 1,
        notify_on_comment_replies: true,
        notify_on_mentions: true,
        notify_on_new_posts: true,
      })),
    }
    vi.mocked(useUpdateNotificationPreferences).mockReturnValue(
      mockMutation as ReturnType<typeof useUpdateNotificationPreferences>
    )
    renderPage()

    await userEvent.click(screen.getByLabelText('Notify on mentions'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent(/saved/i)
  })

  it('auto-dismisses the success alert after 3 seconds', async () => {
    vi.useFakeTimers()
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mockMutation = {
      ...defaultMutation,
      mutateAsync: vi.fn(async () => ({
        user_id: 1,
        notify_on_comment_replies: true,
        notify_on_mentions: true,
        notify_on_new_posts: true,
      })),
    }
    vi.mocked(useUpdateNotificationPreferences).mockReturnValue(
      mockMutation as ReturnType<typeof useUpdateNotificationPreferences>
    )
    renderPage()

    await user.click(screen.getByLabelText('Notify on mentions'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())

    vi.advanceTimersByTime(3000)

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('shows an error alert when the mutation fails', async () => {
    const mockMutation = {
      ...defaultMutation,
      mutateAsync: vi.fn(async () => {
        throw new Error('Save failed')
      }),
    }
    vi.mocked(useUpdateNotificationPreferences).mockReturnValue(
      mockMutation as ReturnType<typeof useUpdateNotificationPreferences>
    )
    renderPage()

    await userEvent.click(screen.getByLabelText('Notify on mentions'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('Save failed')
  })

  it('shows a message or redirects when user is not authenticated', () => {
    vi.mocked(useAuth).mockReturnValueOnce({
      isSignedIn: false,
      isLoaded: true,
      getToken: vi.fn(async () => null),
      user: null,
      role: 'authenticated' as const,
    })

    renderPage()

    expect(screen.getByText(/please sign in/i)).toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })
})
