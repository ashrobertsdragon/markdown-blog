import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import NotFound from '@/pages/NotFound'

describe('NotFound', () => {
  it('should render 404 message', () => {
    render(
      <BrowserRouter>
        <NotFound />
      </BrowserRouter>
    )

    expect(screen.getByText(/404/i)).toBeInTheDocument()
    expect(screen.getByText(/not found/i)).toBeInTheDocument()
  })

  it('should display a link to the home page', () => {
    render(
      <BrowserRouter>
        <NotFound />
      </BrowserRouter>
    )

    const homeLink = screen.getByRole('link', { name: /home/i })
    expect(homeLink).toBeInTheDocument()
    expect(homeLink).toHaveAttribute('href', '/')
  })

  it('should render with proper styling', () => {
    const { container } = render(
      <BrowserRouter>
        <NotFound />
      </BrowserRouter>
    )

    // Check that container has some content
    expect(container.firstChild).toBeTruthy()
  })
})
