import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HealthMetrics } from '@/components/admin/HealthMetrics'
import { useSystemHealth } from '@/hooks/admin/useSystemHealth'
import {
  createMockDegradedSystemHealth,
  createMockSystemHealth,
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

const mockUseSystemHealthReturn = {
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
 * HealthMetrics component test suite.
 *
 * Tests for system health dashboard cards covering API status, database,
 * filesystem, github_api, and uptime display. Covers healthy/degraded/unhealthy
 * indicator colours, uptime formatting, and loading/error states (req 5.1-5.4).
 */
describe('HealthMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useSystemHealth).mockReturnValue(mockUseSystemHealthReturn as never)
  })

  describe('Status Cards', () => {
    it('should_render_overall_status_card', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth(),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/overall|system status/i)).toBeInTheDocument()
    })

    it('should_render_database_status_card', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth(),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/database/i)).toBeInTheDocument()
    })

    it('should_render_filesystem_status_card', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth(),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/filesystem/i)).toBeInTheDocument()
    })

    it('should_render_github_api_status_card', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth(),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/github/i)).toBeInTheDocument()
    })

    it('should_render_uptime_display', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth({ uptime_seconds: 3661 }),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/uptime/i)).toBeInTheDocument()
    })
  })

  describe('Healthy State', () => {
    it('should_show_healthy_text_for_overall_status', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth({ status: 'healthy' }),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getAllByText(/healthy/i).length).toBeGreaterThan(0)
    })

    it('should_apply_green_indicator_class_when_healthy', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth({ status: 'healthy' }),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      const greenElements = document.querySelectorAll('[class*="green"]')
      expect(greenElements.length).toBeGreaterThan(0)
    })

    it('should_show_all_subsystem_statuses_when_healthy', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth({
          status: 'healthy',
          database: 'healthy',
          filesystem: 'healthy',
          github_api: 'healthy',
        }),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/database/i)).toBeInTheDocument()
      expect(screen.getByText(/filesystem/i)).toBeInTheDocument()
      expect(screen.getByText(/github/i)).toBeInTheDocument()
    })
  })

  describe('Degraded State', () => {
    it('should_show_degraded_text_when_status_is_degraded', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockDegradedSystemHealth('degraded'),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getAllByText(/degraded/i).length).toBeGreaterThan(0)
    })

    it('should_apply_yellow_indicator_class_when_degraded', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockDegradedSystemHealth('degraded'),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      const yellowElements = document.querySelectorAll('[class*="yellow"]')
      expect(yellowElements.length).toBeGreaterThan(0)
    })
  })

  describe('Unhealthy State', () => {
    it('should_show_unhealthy_text_when_status_is_unhealthy', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockDegradedSystemHealth('unhealthy'),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getAllByText(/unhealthy/i).length).toBeGreaterThan(0)
    })

    it('should_apply_red_indicator_class_when_unhealthy', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockDegradedSystemHealth('unhealthy'),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      const redElements = document.querySelectorAll('[class*="red"]')
      expect(redElements.length).toBeGreaterThan(0)
    })
  })

  describe('Uptime Formatting', () => {
    it('should_format_uptime_seconds_as_human_readable', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth({ uptime_seconds: 3661 }),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/1h\s*1m\s*1s|1 hour|3661/i)).toBeInTheDocument()
    })

    it('should_handle_zero_uptime_gracefully', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        data: createMockSystemHealth({ uptime_seconds: 0 }),
        isSuccess: true,
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/uptime/i)).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('should_show_loading_indicator_when_isLoading_is_true', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        isLoading: true,
        isPending: true,
        status: 'pending',
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should_show_error_message_when_isError_is_true', () => {
      vi.mocked(useSystemHealth).mockReturnValue({
        ...mockUseSystemHealthReturn,
        isError: true,
        error: new Error('Failed to load system health'),
        status: 'error',
      } as never)

      renderWithQueryClient(<HealthMetrics />)

      expect(screen.getByText(/error|failed/i)).toBeInTheDocument()
    })
  })
})
