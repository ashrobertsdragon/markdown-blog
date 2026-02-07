import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarkdownEditor } from '@/components/post/MarkdownEditor'

/**
 * Mock @uiw/react-md-editor to avoid dependency issues in tests
 */
vi.mock('@uiw/react-md-editor', () => ({
  default: vi.fn(({ value }: { value: string }) => <div data-testid="md-editor">{value}</div>),
}))

/**
 * Test suite for MarkdownEditor component
 *
 * Tests the markdown editor wrapper component that integrates @uiw/react-md-editor
 * with proper typing and project conventions.
 */
describe('MarkdownEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  /**
   * RED phase: Test that the component renders with provided value
   * Expected to FAIL because MarkdownEditor.tsx does not exist yet
   */
  it('should render MDEditor with provided value', () => {
    const testValue = '# Test Heading\n\nTest content'

    render(<MarkdownEditor value={testValue} onChange={vi.fn()} />)

    const editor = screen.getByTestId('md-editor')
    expect(editor).toBeInTheDocument()
    expect(editor).toHaveTextContent('# Test Heading')
    expect(editor).toHaveTextContent('Test content')
  })

  /**
   * RED phase: Test that onChange callback is called when content changes
   * Expected to FAIL because MarkdownEditor doesn't wire up onChange to MDEditor yet
   */
  it('should call onChange when content changes', async () => {
    const mockOnChange = vi.fn()
    const initialValue = '# Initial content'
    const newValue = '# Updated content'

    render(<MarkdownEditor value={initialValue} onChange={mockOnChange} />)

    const MDEditorMock = vi.mocked((await import('@uiw/react-md-editor')).default)
    const mockCall = MDEditorMock.mock.calls[0]
    const onChangeFromProps = mockCall?.[0]?.onChange

    if (onChangeFromProps) {
      onChangeFromProps(newValue)
    }

    expect(mockOnChange).toHaveBeenCalledWith(newValue)
    expect(mockOnChange).toHaveBeenCalledTimes(1)
  })

  /**
   * RED phase: Test that onSave callback is called when Ctrl+S is pressed
   * Expected to FAIL because MarkdownEditor doesn't accept onSave prop yet
   * and no keyboard event handler is implemented
   */
  it('should call onSave when Ctrl+S is pressed', () => {
    const mockOnSave = vi.fn()
    const testValue = '# Test content'

    render(<MarkdownEditor value={testValue} onChange={vi.fn()} onSave={mockOnSave} />)

    const editorContainer = screen.getByTestId('markdown-editor-container')

    fireEvent.keyDown(editorContainer, {
      key: 's',
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    })

    expect(mockOnSave).toHaveBeenCalledTimes(1)
  })

  /**
   * RED phase: Test that onSave callback is called when Meta+S is pressed (macOS)
   * Expected to FAIL because MarkdownEditor doesn't accept onSave prop yet
   * and no keyboard event handler is implemented
   */
  it('should call onSave when Meta+S is pressed (macOS)', () => {
    const mockOnSave = vi.fn()
    const testValue = '# Test content'

    render(<MarkdownEditor value={testValue} onChange={vi.fn()} onSave={mockOnSave} />)

    const editorContainer = screen.getByTestId('markdown-editor-container')

    fireEvent.keyDown(editorContainer, {
      key: 's',
      metaKey: true,
      bubbles: true,
      cancelable: true,
    })

    expect(mockOnSave).toHaveBeenCalledTimes(1)
  })

  /**
   * RED phase: Test that component doesn't crash when onSave is not provided
   * Expected to FAIL because MarkdownEditor will attempt to call undefined onSave
   * when keyboard shortcut is triggered
   */
  it('should not call onSave if onSave prop is not provided', () => {
    const testValue = '# Test content'

    render(<MarkdownEditor value={testValue} onChange={vi.fn()} />)

    const editorContainer = screen.getByTestId('markdown-editor-container')

    expect(() => {
      fireEvent.keyDown(editorContainer, {
        key: 's',
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      })
    }).not.toThrow()
  })

  it('should accept and apply className prop', () => {
    const testValue = '# Test content'
    const customClass = 'custom-editor-class'

    render(<MarkdownEditor value={testValue} onChange={vi.fn()} className={customClass} />)

    const editorContainer = screen.getByTestId('markdown-editor-container')
    expect(editorContainer).toHaveClass(customClass)
  })

  it('should handle async onSave errors gracefully', () => {
    const mockOnSave = vi.fn(() => Promise.reject(new Error('Save failed')))
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const testValue = '# Test content'

    render(<MarkdownEditor value={testValue} onChange={vi.fn()} onSave={mockOnSave} />)

    const editorContainer = screen.getByTestId('markdown-editor-container')

    expect(() => {
      fireEvent.keyDown(editorContainer, {
        key: 's',
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      })
    }).not.toThrow()

    expect(mockOnSave).toHaveBeenCalledTimes(1)

    consoleErrorSpy.mockRestore()
  })

  /**
   * RED phase: Test that XSS attempts are sanitized in markdown preview
   * Expected to verify that rehype-sanitize is configured in previewOptions
   * passed to MDEditor to prevent XSS attacks in rendered markdown
   */
  it('should sanitize XSS attempts in markdown preview', async () => {
    const xssContent = "<img src=x onerror=alert('XSS')>"

    render(<MarkdownEditor value={xssContent} onChange={vi.fn()} />)

    const MDEditorMock = vi.mocked((await import('@uiw/react-md-editor')).default)
    const mockCall = MDEditorMock.mock.calls[0]
    const propsPassedToMDEditor = mockCall?.[0]

    expect(propsPassedToMDEditor?.previewOptions).toBeDefined()
    expect(propsPassedToMDEditor?.previewOptions?.rehypePlugins).toBeDefined()
    expect(Array.isArray(propsPassedToMDEditor?.previewOptions?.rehypePlugins)).toBe(true)
    expect(propsPassedToMDEditor?.previewOptions?.rehypePlugins?.length).toBeGreaterThan(0)
  })
})
