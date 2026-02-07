import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PreviewPane } from '@/components/post/PreviewPane'

/**
 * Mock react-syntax-highlighter to verify it's called for code blocks
 */
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children, language }: { children: string; language: string }) => (
    <div data-testid={`syntax-highlighter-${language || 'auto'}`}>{children}</div>
  ),
}))

describe('PreviewPane Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty div when markdown is empty', () => {
    const { container } = render(<PreviewPane markdown="" />)
    const preview = container.querySelector('[data-testid="preview-pane"]')
    expect(preview).toBeInTheDocument()
    const markdownDiv = preview?.querySelector('.markdown-preview')
    expect(markdownDiv).toBeEmptyDOMElement()
  })

  it('renders heading markdown correctly with proper hierarchy', () => {
    const markdown = '# Heading 1\n## Heading 2\n### Heading 3'
    const { container } = render(<PreviewPane markdown={markdown} />)

    const h1 = container.querySelector('h1')
    const h2 = container.querySelector('h2')
    const h3 = container.querySelector('h3')

    expect(h1).toBeInTheDocument()
    expect(h1).toHaveTextContent('Heading 1')
    expect(h2).toBeInTheDocument()
    expect(h2).toHaveTextContent('Heading 2')
    expect(h3).toBeInTheDocument()
    expect(h3).toHaveTextContent('Heading 3')
  })

  it('renders paragraph text correctly', () => {
    const markdown = 'This is a paragraph.\n\nThis is another paragraph.'
    const { container } = render(<PreviewPane markdown={markdown} />)

    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs.length).toBeGreaterThanOrEqual(2)
    expect(paragraphs[0]).toHaveTextContent('This is a paragraph.')
  })

  it('renders code blocks with syntax highlighting', () => {
    const markdown = '```typescript\nconst x = 1;\n```'
    render(<PreviewPane markdown={markdown} />)

    // Verify SyntaxHighlighter was called for the code block
    const highlighter = screen.getByTestId('syntax-highlighter-typescript')
    expect(highlighter).toBeInTheDocument()
    expect(highlighter).toHaveTextContent('const x = 1;')
  })

  it('renders links as clickable anchors with proper href', () => {
    const markdown = '[Click me](https://example.com)'
    const { container } = render(<PreviewPane markdown={markdown} />)

    const link = container.querySelector('a')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', 'https://example.com')
    expect(link).toHaveTextContent('Click me')
  })

  it('renders images with alt text and src attribute', () => {
    const markdown = '![Alt text](https://example.com/image.png)'
    const { container } = render(<PreviewPane markdown={markdown} />)

    const img = container.querySelector('img')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', 'https://example.com/image.png')
    expect(img).toHaveAttribute('alt', 'Alt text')
  })

  it('handles invalid/malformed markdown gracefully without crashing', () => {
    const malformedMarkdown =
      '[unclosed link(https://example.com)\n# Missing closing\n```unclosed code'
    expect(() => {
      render(<PreviewPane markdown={malformedMarkdown} />)
    }).not.toThrow()
  })

  it('displays error message when rendering fails', () => {
    const { rerender } = render(<PreviewPane markdown="# Test" />)

    // Re-render with error prop
    rerender(<PreviewPane markdown="# Test" error="Failed to render markdown" />)

    const errorElement = screen.getByTestId('preview-error')
    expect(errorElement).toBeInTheDocument()
    expect(errorElement).toHaveTextContent('Failed to render markdown')
  })

  it('applies custom className to container', () => {
    const { container } = render(<PreviewPane markdown="Test" className="custom-class" />)

    const preview = container.querySelector('[data-testid="preview-pane"]')
    expect(preview).toHaveClass('custom-class')
  })

  it('shows loading state when isLoading is true', () => {
    render(<PreviewPane markdown="# Test" isLoading={true} />)

    const loader = screen.getByTestId('preview-loading')
    expect(loader).toBeInTheDocument()
  })

  it('renders code block without language specified with auto-detection', () => {
    const markdown = '```\ngeneric code\n```'
    render(<PreviewPane markdown={markdown} />)

    // Should fallback to text when no language specified
    const highlighter = screen.getByTestId('syntax-highlighter-text')
    expect(highlighter).toBeInTheDocument()
  })

  it('re-renders when markdown prop changes', () => {
    const { rerender, container } = render(<PreviewPane markdown="# Old" />)

    let h1 = container.querySelector('h1')
    expect(h1).toHaveTextContent('Old')

    rerender(<PreviewPane markdown="# New" />)

    h1 = container.querySelector('h1')
    expect(h1).toHaveTextContent('New')
  })

  it('handles rapid markdown changes without crashing', () => {
    const { rerender } = render(<PreviewPane markdown="# Test 1" />)

    for (let i = 2; i <= 10; i++) {
      expect(() => {
        rerender(<PreviewPane markdown={`# Test ${i}`} />)
      }).not.toThrow()
    }
  })

  it('clears error message when markdown is updated', () => {
    const { rerender } = render(<PreviewPane markdown="# Test" error="Previous error" />)

    expect(screen.getByTestId('preview-error')).toBeInTheDocument()

    rerender(<PreviewPane markdown="# Test" error={null} />)

    expect(screen.queryByTestId('preview-error')).not.toBeInTheDocument()
  })
})
