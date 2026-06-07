import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/components/admin/HealthMetrics', () => ({
  HealthMetrics: vi.fn(() => <div data-testid="health-metrics">health metrics</div>),
}))

vi.mock('@/components/admin/ErrorLogTable', () => ({
  ErrorLogTable: vi.fn(() => <div data-testid="error-log-table">error log table</div>),
}))

import SystemPage from '@/pages/admin/SystemPage'

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

const renderComponent = () =>
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <SystemPage />
    </QueryClientProvider>
  )

/**
 * Tests for the SystemPage admin component.
 *
 * Covers page-level rendering requirements 5.1-5.7: the presence of an h1
 * heading with "System" in its text, and the composition of HealthMetrics
 * and ErrorLogTable child components, each rendered exactly once.
 */
describe('SystemPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Render', () => {
    it('renders a "System" h1 heading', () => {
      renderComponent()

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/system/i)
    })
  })

  describe('HealthMetrics section', () => {
    it('renders exactly one HealthMetrics component', () => {
      renderComponent()

      expect(screen.getByTestId('health-metrics')).toBeInTheDocument()
    })
  })

  describe('ErrorLogTable section', () => {
    it('renders exactly one ErrorLogTable component', () => {
      renderComponent()

      expect(screen.getByTestId('error-log-table')).toBeInTheDocument()
    })
  })
})
