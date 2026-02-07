import MarkdownPreview from '@uiw/react-markdown-preview'
import rehypeSanitize from 'rehype-sanitize'
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
 * Markdown preview component with syntax highlighting
 *
 * Renders markdown content as HTML with:
 * - Syntax highlighting for code blocks via rehype-prism-plus (built into @uiw/react-markdown-preview)
 * - XSS protection via rehype-sanitize integration
 * - Support for all common markdown: headings, links, images, code, etc.
 *
 * Uses @uiw/react-markdown-preview which is already included via @uiw/react-md-editor dependency.
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

      {!isLoading && !error && (
        <MarkdownPreview
          source={markdown}
          rehypePlugins={[[rehypeSanitize]]}
          className="markdown-preview bg-transparent"
          wrapperElement={{
            'data-color-mode': 'light',
          }}
        />
      )}
    </div>
  )
}
