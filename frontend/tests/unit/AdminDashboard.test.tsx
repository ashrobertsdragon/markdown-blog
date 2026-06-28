import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import AdminDashboard from '@/pages/AdminDashboard'

vi.mock('@/components/admin/AdminSidebar', () => ({
  default: () => <div data-testid="admin-sidebar" />,
}))

describe('AdminDashboard', () => {
  const renderComponent = () =>
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </MemoryRouter>
    )

  it('should apply mobile top offset to clear the hamburger button', () => {
    const { container } = renderComponent()
    const main = container.querySelector('main')
    expect(main).toBeInTheDocument()
    expect(main?.className).toContain('pt-16')
  })

  it('should remove top offset on desktop breakpoint where hamburger is hidden', () => {
    const { container } = renderComponent()
    const main = container.querySelector('main')
    expect(main?.className).toContain('md:pt-0')
  })

  it('should apply desktop left padding for the fixed sidebar width', () => {
    const { container } = renderComponent()
    const main = container.querySelector('main')
    expect(main?.className).toContain('md:pl-64')
  })
})
