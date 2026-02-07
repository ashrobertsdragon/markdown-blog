import MDEditor from '@uiw/react-md-editor'
import rehypeSanitize from 'rehype-sanitize'
import { cn } from '@/lib/utils'

/**
 * Props for the MarkdownEditor component
 */
interface MarkdownEditorProps {
  /** The markdown content to display in the editor */
  value: string
  /** Callback function invoked when the content changes */
  onChange: (content: string) => void
  /** Optional callback function invoked when Ctrl+S or Cmd+S is pressed */
  onSave?: () => void | Promise<void>
  /** Optional CSS class name to apply to the container */
  className?: string
}

/**
 * Markdown editor component using @uiw/react-md-editor
 *
 * Provides a controlled markdown editing interface with live preview.
 * Supports Ctrl+S (Cmd+S on Mac) keyboard shortcut for saving.
 * Includes XSS prevention via rehype-sanitize plugin.
 *
 * @param props - Component props
 * @returns React component
 */
export function MarkdownEditor({ value, onChange, onSave, className }: MarkdownEditorProps) {
  const handleKeyDown = async (event: React.KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
      event.preventDefault()
      if (onSave) {
        try {
          await onSave()
        } catch (error) {
          console.error('Error saving draft:', error)
        }
      }
    }
  }

  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: keyboard shortcut handler for Ctrl+S
    <div
      onKeyDown={handleKeyDown}
      data-testid="markdown-editor-container"
      className={cn('w-full', className)}
    >
      <MDEditor
        value={value}
        onChange={content => onChange(content ?? '')}
        previewOptions={{
          rehypePlugins: [[rehypeSanitize]],
        }}
      />
    </div>
  )
}
