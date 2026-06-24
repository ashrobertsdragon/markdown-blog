import MDEditor from '@uiw/react-md-editor'
import type React from 'react'
import rehypeSanitize from 'rehype-sanitize'
import { cn } from '@/lib/utils'

type MDEditorTextareaProps = React.ComponentProps<typeof MDEditor>['textareaProps']

/**
 * Props for the MarkdownEditor component
 */
interface MarkdownEditorProps {
  value: string
  onChange: (content: string) => void
  onSave?: () => void | Promise<void>
  className?: string
  /** Textarea event handlers forwarded to the underlying MDEditor textarea */
  textareaProps?: MDEditorTextareaProps
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
export function MarkdownEditor({
  value,
  onChange,
  onSave,
  className,
  textareaProps,
}: MarkdownEditorProps) {
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
    <fieldset
      onKeyDown={handleKeyDown}
      data-testid="markdown-editor-container"
      className={cn('w-full border-0 p-0 m-0', className)}
    >
      <MDEditor
        value={value}
        onChange={content => onChange(content ?? '')}
        textareaProps={textareaProps}
        previewOptions={{
          rehypePlugins: [[rehypeSanitize]],
        }}
      />
    </fieldset>
  )
}
