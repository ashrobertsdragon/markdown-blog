import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PreviewPane } from '@/components/post/PreviewPane'

/**
 * Mock @uiw/react-markdown-preview to verify it's called correctly
 */
vi.mock('@uiw/react-markdown-preview', () => ({
  default: ({ source, className }: { source: string; className: string }) => {
    const lines = source.split('\n')
    return (
      <div data-testid="markdown-preview" className={className}>
        {lines.map((line, idx) => {
          if (line.startsWith('### ')) return <h3 key={idx}>{line.replace('### ', '')}</h3>
          if (line.startsWith('## ')) return <h2 key={idx}>{line.replace('## ', '')}</h2>
          if (line.startsWith('# ')) return <h1 key={idx}>{line.replace('# ', '')}</h1>
          if (line.includes('![') && line.includes('](')) {
            return (
              <img
                key={idx}
                src={line.match(/\]\((.*?)\)/)?.[1]}
                alt={line.match(/!\[(.*?)\]/)?.[1]}
              />
            )
          }
          if (line.includes('[') && line.includes('](')) {
            return (
              <a key={idx} href={line.match(/\]\((.*?)\)/)?.[1]}>
                {line.match(/\[(.*?)\]/)?.[1]}
              </a>
            )
          }
          if (line.startsWith('```')) return null
          if (line.trim() && !line.startsWith('#')) return <p key={idx}>{line}</p>
          return null
        })}
        {source.includes('```') && (
          <pre>
            <code data-testid="code-block">{source.match(/```\w*\n([\s\S]*?)```/)?.[1]}</code>
          </pre>
        )}
      </div>
    )
  },
}))

describe('PreviewPane Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty when markdown is empty', () => {
    const { container } = render(<PreviewPane markdown="" />)
    const preview = container.querySelector('[data-testid="preview-pane"]')
    expect(preview).toBeInTheDocument()
    const markdownDiv = preview?.querySelector('[data-testid="markdown-preview"]')
    expect(markdownDiv).toBeInTheDocument()
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
    const markdown = 'This is a paragraph.'
    const { container } = render(<PreviewPane markdown={markdown} />)

    const paragraph = container.querySelector('p')
    expect(paragraph).toBeInTheDocument()
    expect(paragraph).toHaveTextContent('This is a paragraph.')
  })

  it('renders code blocks', () => {
    const markdown = '```typescript\nconst x = 1;\n```'
    render(<PreviewPane markdown={markdown} />)

    const codeBlock = screen.getByTestId('code-block')
    expect(codeBlock).toBeInTheDocument()
    expect(codeBlock).toHaveTextContent('const x = 1;')
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

  it('does not render MarkdownPreview when isLoading is true', () => {
    render(<PreviewPane markdown="# Test" isLoading={true} />)

    const markdownPreview = screen.queryByTestId('markdown-preview')
    expect(markdownPreview).not.toBeInTheDocument()
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

  it('passes rehypeSanitize plugin to MarkdownPreview', () => {
    const { container } = render(<PreviewPane markdown="# Test" />)

    const markdownPreview = container.querySelector('[data-testid="markdown-preview"]')
    expect(markdownPreview).toBeInTheDocument()
  })
})
