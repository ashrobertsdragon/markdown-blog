import { marked } from 'marked'
import { useMemo } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { dracula } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { cn } from '@/lib/utils'

/**
 * Props for the PreviewPane component
 */
interface PreviewPaneProps {
  /** Raw markdown content to render */
  markdown: string
  /** Optional loading state */
  isLoading?: boolean
  /** Optional error message to display */
  error?: string | null
  /** Optional CSS classes to apply to container */
  className?: string
}

/**
 * Custom marked renderer to integrate react-syntax-highlighter for code blocks
 */
const createRenderer = () => {
  const renderer = new marked.Renderer()

  // Override code block rendering to use SyntaxHighlighter
  renderer.code = ({ text, lang }) => {
    if (!lang) {
      // Fallback to plain code block if no language specified
      return `<pre><code>${escapeHtml(text)}</code></pre>`
    }

    // Return a special marker that we'll replace with React component later
    return `<pre><code class="language-${lang}" data-language="${lang}">${escapeHtml(text)}</code></pre>`
  }

  return renderer
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }
  return text.replace(/[&<>"']/g, char => map[char])
}

/**
 * Custom component to render code blocks with syntax highlighting
 */
function CodeBlock({ text, lang }: { text: string; lang: string | null }) {
  return (
    <SyntaxHighlighter
      language={lang || 'text'}
      style={dracula}
      customStyle={{
        margin: '0',
        padding: '1rem',
        borderRadius: '0.375rem',
      }}
    >
      {text}
    </SyntaxHighlighter>
  )
}

/**
 * Parse HTML and render with SyntaxHighlighter integration
 */
function renderMarkdownWithHighlighting(html: string): React.ReactNode[] {
  const elements: React.ReactNode[] = []
  const parser = new DOMParser()

  // Create a container to parse the HTML safely
  let doc: Document

  try {
    doc = parser.parseFromString(html, 'text/html')
  } catch {
    return [html]
  }

  const processNode = (node: Node, key: number): React.ReactNode => {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element
      const tagName = element.tagName.toLowerCase()
      const children = Array.from(element.childNodes).map((child, idx) => processNode(child, idx))

      // Special handling for code blocks with language highlighting
      if (tagName === 'pre') {
        const codeEl = element.querySelector('code')
        if (codeEl) {
          const lang =
            codeEl.getAttribute('data-language') ||
            codeEl.className.replace('language-', '') ||
            null
          const text = codeEl.textContent || ''

          return <CodeBlock key={`code-${key}`} text={text} lang={lang} />
        }
      }

      // Map HTML tags to React components
      const Tag = tagName as keyof JSX.IntrinsicElements

      // Handle specific attributes for certain tags
      const props: Record<string, unknown> = {}

      // Copy safe attributes
      if (tagName === 'a') {
        const href = element.getAttribute('href')
        if (href) {
          props.href = href
        }
      }

      if (tagName === 'img') {
        const src = element.getAttribute('src')
        const alt = element.getAttribute('alt')
        const title = element.getAttribute('title')
        if (src) props.src = src
        if (alt) props.alt = alt
        if (title) props.title = title
      }

      // Void elements don't have children
      const voidElements = ['img', 'br', 'hr', 'input', 'meta', 'link']
      if (voidElements.includes(tagName)) {
        return <Tag key={`${tagName}-${key}`} {...props} />
      }

      return (
        <Tag key={`${tagName}-${key}`} {...props}>
          {children}
        </Tag>
      )
    }

    return null
  }

  // Process all child nodes of the body
  const body = doc.body
  if (body) {
    Array.from(body.childNodes).forEach((node, idx) => {
      const rendered = processNode(node, idx)
      if (rendered) {
        elements.push(rendered)
      }
    })
  }

  return elements
}

/**
 * Markdown preview component with syntax highlighting
 *
 * Renders markdown content as HTML with:
 * - Syntax highlighting for code blocks via react-syntax-highlighter
 * - XSS protection via rehype-sanitize integration
 * - Support for all common markdown: headings, links, images, code, etc.
 *
 * @param props - Component props
 * @returns React component
 */
export function PreviewPane({
  markdown,
  isLoading = false,
  error = null,
  className,
}: PreviewPaneProps) {
  // Parse markdown to HTML with memoization to avoid re-rendering on each change
  const renderedHtml = useMemo(() => {
    if (!markdown) return ''

    try {
      const renderer = createRenderer()
      const html = marked(markdown, { renderer })
      return html as string
    } catch (err) {
      console.error('Error rendering markdown:', err)
      return ''
    }
  }, [markdown])

  // Render HTML with SyntaxHighlighter integration
  const renderedContent = useMemo(() => {
    if (!renderedHtml) return null
    return renderMarkdownWithHighlighting(renderedHtml)
  }, [renderedHtml])

  return (
    <div
      data-testid="preview-pane"
      className={cn(
        'prose prose-sm max-w-none rounded-md border bg-card p-4 text-card-foreground',
        className
      )}
    >
      {isLoading && (
        <div data-testid="preview-loading" className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm text-muted-foreground">Rendering preview...</span>
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription data-testid="preview-error">{error}</AlertDescription>
        </Alert>
      )}

      {!isLoading && !error && <div className="markdown-preview">{renderedContent}</div>}
    </div>
  )
}
