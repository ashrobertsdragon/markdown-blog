import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorLogTable } from '@/components/admin/ErrorLogTable'
import { useErrorLogs } from '@/hooks/admin/useSystemHealth'
import {
  createMockErrorLogEntry,
  createMockErrorLogEntryAtLevel,
  createMockErrorLogsResponse,
} from '../../../fixtures/adminContent.fixtures'

vi.mock('@/hooks/admin/useSystemHealth', () => ({
  useSystemHealth: vi.fn(),
  useErrorLogs: vi.fn(),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    getToken: vi.fn(async () => 'mock-token'),
    isLoaded: true,
    user: null,
    role: 'admin',
  })),
}))

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderWithQueryClient = (component: React.ReactElement) =>
  render(<QueryClientProvider client={createTestQueryClient()}>{component}</QueryClientProvider>)

const mockUseErrorLogsReturn = {
  data: undefined,
  isLoading: false,
  isError: false,
  error: null,
  isFetching: false,
  isRefetching: false,
  isSuccess: false,
  isStale: false,
  isPending: false,
  status: 'pending' as const,
  fetchStatus: 'idle' as const,
  errorUpdateCount: 0,
  failureCount: 0,
  failureReason: null,
  errorUpdatedAt: 0,
  isFetchedAfterMount: false,
  isPreviousData: false,
}

/**
 * ErrorLogTable component test suite.
 *
 * Tests for the admin error log table covering empty state, per-row data
 * display, timestamp formatting, log level labels, context expand/collapse
 * interaction, and loading/error states (req 5.5-5.7).
 */
describe('ErrorLogTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useErrorLogs).mockReturnValue(mockUseErrorLogsReturn as never)
  })

  describe('Empty State', () => {
    it('should_show_no_recent_errors_message_when_errors_array_is_empty', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse([], 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText(/no recent errors/i)).toBeInTheDocument()
    })

    it('should_not_render_table_when_errors_array_is_empty', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse([], 0),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.queryByRole('table')).not.toBeInTheDocument()
    })
  })

  describe('Data Display', () => {
    it('should_render_one_row_per_error_entry', () => {
      const errors = [
        createMockErrorLogEntry({ id: 1 }),
        createMockErrorLogEntry({ id: 2 }),
        createMockErrorLogEntry({ id: 3 }),
      ]

      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(errors, 3),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getAllByRole('row')).toHaveLength(4) // 1 header + 3 data rows
    })

    it('should_display_error_message_in_row', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(
          [createMockErrorLogEntry({ message: 'Database connection timeout' })],
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText('Database connection timeout')).toBeInTheDocument()
    })

    it('should_display_formatted_timestamp_not_raw_iso_string', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(
          [createMockErrorLogEntry({ timestamp: '2026-05-29T09:30:00Z' })],
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.queryByText('2026-05-29T09:30:00Z')).not.toBeInTheDocument()
      expect(
        screen.getByText(/May 29|05\/29\/2026|2026-05-29 09:30|May 29, 2026/i)
      ).toBeInTheDocument()
    })

    it('should_display_error_level_label', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse([createMockErrorLogEntryAtLevel('error', { id: 1 })], 1),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText(/error/i)).toBeInTheDocument()
    })

    it('should_display_warning_level_label', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(
          [createMockErrorLogEntryAtLevel('warning', { id: 1, message: 'Low disk space' })],
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText(/warning/i)).toBeInTheDocument()
    })

    it('should_display_context_data_in_row', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(
          [createMockErrorLogEntry({ context: { file: 'app.py', line: 42 } })],
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText(/app\.py|line.*42|context/i)).toBeInTheDocument()
    })

    it('should_display_multiple_entries_with_distinct_messages', () => {
      const errors = [
        createMockErrorLogEntry({ id: 1, message: 'First error message' }),
        createMockErrorLogEntry({ id: 2, message: 'Second error message' }),
      ]

      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(errors, 2),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText('First error message')).toBeInTheDocument()
      expect(screen.getByText('Second error message')).toBeInTheDocument()
    })
  })

  describe('Expand/Collapse Context', () => {
    it('should_show_expand_button_for_each_row', () => {
      const errors = [createMockErrorLogEntry({ id: 1 }), createMockErrorLogEntry({ id: 2 })]

      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(errors, 2),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getAllByRole('button', { name: /expand|details|show/i })).toHaveLength(2)
    })

    it('should_show_context_details_after_clicking_expand_button', async () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(
          [createMockErrorLogEntry({ id: 1, context: { stack: 'Traceback at line 42' } })],
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      const expandButton = screen.getByRole('button', { name: /expand|details|show/i })
      await userEvent.click(expandButton)

      expect(screen.getByText(/Traceback at line 42|stack/i)).toBeInTheDocument()
    })

    it('should_hide_context_details_after_clicking_expand_button_again', async () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse(
          [createMockErrorLogEntry({ id: 1, context: { stack: 'Traceback at line 42' } })],
          1
        ),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      const expandButton = screen.getByRole('button', { name: /expand|details|show/i })
      await userEvent.click(expandButton)
      expect(screen.getByText(/Traceback at line 42|stack/i)).toBeInTheDocument()

      await userEvent.click(expandButton)
      expect(screen.queryByText(/Traceback at line 42/)).not.toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('should_show_loading_indicator_when_isLoading_is_true', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        isLoading: true,
        isPending: true,
        status: 'pending',
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByTestId('loading')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should_show_error_message_when_isError_is_true', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        isError: true,
        error: new Error('Failed to load error logs'),
        status: 'error',
      } as never)

      renderWithQueryClient(<ErrorLogTable />)

      expect(screen.getByText(/error|failed/i)).toBeInTheDocument()
    })
  })

  describe('Limit Prop', () => {
    it('should_render_without_errors_when_limit_prop_is_provided', () => {
      vi.mocked(useErrorLogs).mockReturnValue({
        ...mockUseErrorLogsReturn,
        data: createMockErrorLogsResponse([], 0, 25),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<ErrorLogTable limit={25} />)

      expect(screen.getByText(/no recent errors/i)).toBeInTheDocument()
    })
  })
})
