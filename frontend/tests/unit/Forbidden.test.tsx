import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import Forbidden from '@/pages/Forbidden'

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('Forbidden', () => {
  it('should render 403 status code', () => {
    renderWithRouter(<Forbidden />)

    const statusCode = screen.getByText('403')
    expect(statusCode).toBeInTheDocument()
    expect(statusCode.tagName).toBe('H1')
  })

  it('should render access denied heading', () => {
    renderWithRouter(<Forbidden />)

    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toBeInTheDocument()
    expect(heading.textContent).toMatch(/(Access Denied|Forbidden)/i)
  })

  it('should render ShadCN Alert component with destructive variant', () => {
    const { container } = renderWithRouter(<Forbidden />)

    const alert = container.querySelector('[role="alert"]')
    expect(alert).toBeInTheDocument()
    expect(alert?.className).toContain('border-destructive')
  })

  it('should render user-friendly error message about permissions', () => {
    renderWithRouter(<Forbidden />)

    const message = screen.getByText(/permission/i)
    expect(message).toBeInTheDocument()
    expect(message.textContent).toMatch(/you (do not have|don't have) (the necessary )?permission/i)
  })

  it('should not contain technical jargon in error message', () => {
    renderWithRouter(<Forbidden />)

    const bodyText = screen.getByRole('alert').textContent || ''

    expect(bodyText.toLowerCase()).not.toContain('http')
    expect(bodyText.toLowerCase()).not.toContain('status code')
    expect(bodyText.toLowerCase()).not.toContain('error code')
    expect(bodyText.toLowerCase()).not.toContain('api')
    expect(bodyText.toLowerCase()).not.toContain('exception')
  })

  it('should render home navigation link with React Router Link', () => {
    renderWithRouter(<Forbidden />)

    const homeLink = screen.getByRole('link')
    expect(homeLink).toBeInTheDocument()
    expect(homeLink).toHaveAttribute('href', '/')
    expect(homeLink.textContent).toMatch(/(go home|return home|back to home)/i)
  })

  it('should use ShadCN Button component for navigation link', () => {
    renderWithRouter(<Forbidden />)

    const homeLink = screen.getByRole('link')
    expect(homeLink.className).toContain('inline-flex')
    expect(homeLink.className).toContain('items-center')
    expect(homeLink.className).toContain('justify-center')
  })

  it('should render Alert with AlertTitle and AlertDescription components', () => {
    const { container } = renderWithRouter(<Forbidden />)

    const alert = container.querySelector('[role="alert"]')
    expect(alert).toBeInTheDocument()

    const title = alert?.querySelector('h5')
    expect(title).toBeInTheDocument()
    expect(title?.className).toContain('font-medium')

    const description = alert?.querySelector('div.text-sm')
    expect(description).toBeInTheDocument()
  })

  it('should display clear and helpful error message', () => {
    renderWithRouter(<Forbidden />)

    const alert = screen.getByRole('alert')
    const message = alert.textContent || ''

    expect(message.length).toBeGreaterThan(20)
    expect(message).toMatch(/(access|permission|allowed|authorized)/i)
  })

  it('should have proper page structure with error code and navigation', () => {
    const { container } = renderWithRouter(<Forbidden />)

    expect(container.querySelector('h1')).toBeInTheDocument()
    expect(container.querySelector('[role="alert"]')).toBeInTheDocument()
    expect(screen.getByRole('link')).toBeInTheDocument()
  })
})
