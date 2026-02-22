import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Home from '@/pages/Home'
import type { HealthResponse } from '@/services/healthService'

/**
 * Mock the healthService module before importing Home component
 * This ensures all calls to healthService.checkHealth() are intercepted
 */
vi.mock('@/services/healthService', () => ({
  healthService: {
    checkHealth: vi.fn(),
  },
}))

describe('Home', () => {
  beforeEach(() => {
    /**
     * Clear all mocks before each test to ensure isolation
     */
    vi.clearAllMocks()
  })

  describe('initial render and loading state', () => {
    /**
     * Test that component displays loading state while fetching health status
     */
    it('should display loading state on initial render', async () => {
      const { healthService } = await import('@/services/healthService')
      vi.mocked(healthService.checkHealth).mockImplementation(() => new Promise(() => {}))

      render(<Home />)

      expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })

    /**
     * Test that component calls healthService.checkHealth() on mount
     */
    it('should call healthService.checkHealth on component mount', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      await waitFor(() => {
        expect(healthService.checkHealth).toHaveBeenCalledTimes(1)
      })
    })

    /**
     * Test that loading state is removed after successful fetch
     */
    it('should remove loading state after successful fetch', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('successful health status display', () => {
    /**
     * Test that health status is displayed when fetch succeeds
     */
    it('should display health status data on successful fetch', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      await waitFor(() => {
        expect(screen.getByText(/healthy/i)).toBeInTheDocument()
      })
    })

    /**
     * Test that component renders content container after data is loaded
     */
    it('should render content after health data is loaded', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      const { container } = render(<Home />)

      await waitFor(() => {
        expect(container.firstChild).toBeTruthy()
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      })
    })

    /**
     * Test that different status values are displayed correctly
     */
    it('should display different status values correctly', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'degraded' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      await waitFor(() => {
        expect(screen.getByText(/degraded/i)).toBeInTheDocument()
      })
    })
  })

  describe('error handling', () => {
    /**
     * Test that error message is displayed when fetch fails
     */
    it('should display error message when fetch fails', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockError = new Error('Network error')
      vi.mocked(healthService.checkHealth).mockRejectedValue(mockError)

      render(<Home />)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
        expect(screen.getByText('Connection Error')).toBeInTheDocument()
      })
    })

    /**
     * Test that loading state is removed when error occurs
     */
    it('should remove loading state when error occurs', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockError = new Error('Network error')
      vi.mocked(healthService.checkHealth).mockRejectedValue(mockError)

      render(<Home />)

      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      })
    })

    /**
     * Test that error message contains descriptive text for API failures
     */
    it('should display descriptive error message for API failures', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockError = new Error('Failed to connect to server')
      vi.mocked(healthService.checkHealth).mockRejectedValue(mockError)

      render(<Home />)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
        expect(screen.getByText(/unable to load health status/i)).toBeInTheDocument()
      })
    })

    /**
     * Test that error state is not showing success content
     */
    it('should not display health status data when error occurs', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockError = new Error('Network error')
      vi.mocked(healthService.checkHealth).mockRejectedValue(mockError)

      render(<Home />)

      await waitFor(() => {
        expect(screen.queryByText(/healthy/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('component lifecycle and cleanup', () => {
    /**
     * Test that component effect runs only once on mount
     */
    it('should call healthService.checkHealth only once on mount', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      await waitFor(() => {
        expect(healthService.checkHealth).toHaveBeenCalledTimes(1)
      })
    })

    /**
     * Test that component properly unmounts without errors
     */
    it('should unmount without errors', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      const { unmount } = render(<Home />)

      await waitFor(() => {
        expect(healthService.checkHealth).toHaveBeenCalled()
      })

      expect(() => {
        unmount()
      }).not.toThrow()
    })

    /**
     * Test that component handles rapid mount/unmount cycles
     */
    it('should handle rapid mount and unmount without errors', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      const { unmount: unmount1 } = render(<Home />)
      unmount1()

      const { unmount: unmount2 } = render(<Home />)
      unmount2()

      await waitFor(() => {
        expect(healthService.checkHealth).toHaveBeenCalled()
      })
    })
  })

  describe('state management', () => {
    /**
     * Test that component transitions from loading to success state
     */
    it('should transition from loading to success state', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      expect(screen.getByText(/loading/i)).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
        expect(screen.getByText(/healthy/i)).toBeInTheDocument()
      })
    })

    /**
     * Test that component transitions from loading to error state
     */
    it('should transition from loading to error state', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockError = new Error('Network error')
      vi.mocked(healthService.checkHealth).mockRejectedValue(mockError)

      render(<Home />)

      expect(screen.getByText(/loading/i)).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })
  })

  describe('accessibility and rendering', () => {
    /**
     * Test that component renders with proper HTML structure
     */
    it('should render with proper HTML structure', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      const { container } = render(<Home />)

      await waitFor(() => {
        expect(container.querySelector('div')).toBeInTheDocument()
      })
    })

    /**
     * Test that page title or heading is rendered
     */
    it('should render page heading or title', async () => {
      const { healthService } = await import('@/services/healthService')
      const mockHealthResponse: HealthResponse = { status: 'healthy' }
      vi.mocked(healthService.checkHealth).mockResolvedValue(mockHealthResponse)

      render(<Home />)

      await waitFor(() => {
        const heading = screen.queryByRole('heading')
        const title = screen.queryByText(/home/i)
        expect(heading || title).toBeTruthy()
      })
    })
  })
})
