import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { DiffLine } from '../../../types/revision'
import { DiffViewer } from '../DiffViewer'

describe('DiffViewer', () => {
  const mockDiffLines: DiffLine[] = [
    { type: 'context', content: 'unchanged line', lineNumber: 1 },
    { type: 'deletion', content: 'removed line', lineNumber: 2 },
    { type: 'addition', content: 'added line', lineNumber: 3 },
  ]

  it('renders diff lines with correct content', () => {
    render(<DiffViewer diffLines={mockDiffLines} />)

    expect(screen.getByText('unchanged line')).toBeInTheDocument()
    expect(screen.getByText('removed line')).toBeInTheDocument()
    expect(screen.getByText('added line')).toBeInTheDocument()
  })

  it('renders addition lines with green background and plus prefix', () => {
    render(<DiffViewer diffLines={[{ type: 'addition', content: 'new content', lineNumber: 1 }]} />)

    const line = screen.getByTestId('diff-line-addition-1')
    expect(line).toHaveClass('bg-green-50')
    expect(within(line).getByText('+')).toBeInTheDocument()
  })

  it('renders deletion lines with red background and minus prefix', () => {
    render(<DiffViewer diffLines={[{ type: 'deletion', content: 'old content', lineNumber: 1 }]} />)

    const line = screen.getByTestId('diff-line-deletion-1')
    expect(line).toHaveClass('bg-red-50')
    expect(within(line).getByText('-')).toBeInTheDocument()
  })

  it('renders context lines with gray background and no prefix', () => {
    render(<DiffViewer diffLines={[{ type: 'context', content: 'same content', lineNumber: 1 }]} />)

    const line = screen.getByTestId('diff-line-context-1')
    expect(line).toHaveClass('bg-gray-50')
    expect(within(line).queryByText('+')).not.toBeInTheDocument()
    expect(within(line).queryByText('-')).not.toBeInTheDocument()
  })

  it('displays line numbers correctly', () => {
    render(<DiffViewer diffLines={mockDiffLines} />)

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('handles diff lines without line numbers', () => {
    const linesWithoutNumbers: DiffLine[] = [{ type: 'context', content: 'no number' }]

    render(<DiffViewer diffLines={linesWithoutNumbers} />)

    expect(screen.getByText('no number')).toBeInTheDocument()
  })

  it('shows loading spinner when isLoading is true', () => {
    render(<DiffViewer diffLines={[]} isLoading={true} />)

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('hides diff content when loading', () => {
    render(<DiffViewer diffLines={mockDiffLines} isLoading={true} />)

    expect(screen.queryByText('unchanged line')).not.toBeInTheDocument()
  })

  it('shows error message when error prop is provided', () => {
    const errorMessage = 'Failed to load diff'
    render(<DiffViewer diffLines={[]} error={errorMessage} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(errorMessage)).toBeInTheDocument()
  })

  it('hides diff content when error is present', () => {
    render(<DiffViewer diffLines={mockDiffLines} error="Error occurred" />)

    expect(screen.queryByText('unchanged line')).not.toBeInTheDocument()
  })

  it('shows "No changes" message when diffLines is empty', () => {
    render(<DiffViewer diffLines={[]} />)

    expect(screen.getByText(/no changes/i)).toBeInTheDocument()
  })

  it('does not show "No changes" when loading', () => {
    render(<DiffViewer diffLines={[]} isLoading={true} />)

    expect(screen.queryByText(/no changes/i)).not.toBeInTheDocument()
  })

  it('does not show "No changes" when error is present', () => {
    render(<DiffViewer diffLines={[]} error="Error" />)

    expect(screen.queryByText(/no changes/i)).not.toBeInTheDocument()
  })

  it('handles large diffs with more than 100 lines', () => {
    const largeDiff: DiffLine[] = Array.from({ length: 150 }, (_, i) => ({
      type: 'context' as const,
      content: `line ${i + 1}`,
      lineNumber: i + 1,
    }))

    render(<DiffViewer diffLines={largeDiff} />)

    expect(screen.getByText('line 1')).toBeInTheDocument()
    expect(screen.getByText('line 150')).toBeInTheDocument()
  })

  it('renders copy to clipboard button', () => {
    render(<DiffViewer diffLines={mockDiffLines} />)

    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
  })

  it('copies diff content to clipboard when copy button is clicked', async () => {
    const user = userEvent.setup()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })

    render(<DiffViewer diffLines={mockDiffLines} />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('unchanged line')
    )
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('- removed line')
    )
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('+ added line')
    )
  })

  it('shows success feedback after successful copy', async () => {
    const user = userEvent.setup()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })

    render(<DiffViewer diffLines={mockDiffLines} />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)

    expect(screen.getByText(/copied/i)).toBeInTheDocument()
  })

  it('shows error feedback when copy fails', async () => {
    const user = userEvent.setup()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockRejectedValue(new Error('Copy failed')),
      },
    })

    render(<DiffViewer diffLines={mockDiffLines} />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)

    expect(screen.getByText(/failed to copy/i)).toBeInTheDocument()
  })

  it('has proper aria-label for diff viewer container', () => {
    render(<DiffViewer diffLines={mockDiffLines} />)

    expect(screen.getByRole('region', { name: /diff viewer/i })).toBeInTheDocument()
  })

  it('renders additions with green background', () => {
    render(<DiffViewer diffLines={[{ type: 'addition', content: 'new', lineNumber: 1 }]} />)

    const line = screen.getByTestId('diff-line-addition-1')
    expect(line).toHaveClass('bg-green-50')
  })

  it('renders deletions with red background', () => {
    render(<DiffViewer diffLines={[{ type: 'deletion', content: 'old', lineNumber: 1 }]} />)

    const line = screen.getByTestId('diff-line-deletion-1')
    expect(line).toHaveClass('bg-red-50')
  })

  it('renders context lines with gray background', () => {
    render(<DiffViewer diffLines={[{ type: 'context', content: 'same', lineNumber: 1 }]} />)

    const line = screen.getByTestId('diff-line-context-1')
    expect(line).toHaveClass('bg-gray-50')
  })

  it('preserves whitespace in diff content', () => {
    const diffWithWhitespace: DiffLine[] = [
      { type: 'context', content: '    indented line', lineNumber: 1 },
    ]

    render(<DiffViewer diffLines={diffWithWhitespace} />)

    const line = screen.getByTestId('diff-line-context-1')
    expect(line).toHaveClass('whitespace-pre')
  })

  it('renders multiple consecutive additions', () => {
    const additions: DiffLine[] = [
      { type: 'addition', content: 'line 1', lineNumber: 1 },
      { type: 'addition', content: 'line 2', lineNumber: 2 },
      { type: 'addition', content: 'line 3', lineNumber: 3 },
    ]

    render(<DiffViewer diffLines={additions} />)

    expect(screen.getAllByText(/^\+/)).toHaveLength(3)
  })

  it('renders multiple consecutive deletions', () => {
    const deletions: DiffLine[] = [
      { type: 'deletion', content: 'line 1', lineNumber: 1 },
      { type: 'deletion', content: 'line 2', lineNumber: 2 },
    ]

    render(<DiffViewer diffLines={deletions} />)

    expect(screen.getAllByText(/^-/)).toHaveLength(2)
  })

  it('handles mixed line types in sequence', () => {
    const mixedLines: DiffLine[] = [
      { type: 'context', content: 'same', lineNumber: 1 },
      { type: 'deletion', content: 'old', lineNumber: 2 },
      { type: 'addition', content: 'new', lineNumber: 3 },
      { type: 'context', content: 'same again', lineNumber: 4 },
    ]

    render(<DiffViewer diffLines={mixedLines} />)

    expect(screen.getByTestId('diff-line-context-1')).toBeInTheDocument()
    expect(screen.getByTestId('diff-line-deletion-2')).toBeInTheDocument()
    expect(screen.getByTestId('diff-line-addition-3')).toBeInTheDocument()
    expect(screen.getByTestId('diff-line-context-4')).toBeInTheDocument()
  })

  it('escapes HTML in diff content', () => {
    const diffWithHTML: DiffLine[] = [
      { type: 'context', content: '<script>alert("xss")</script>', lineNumber: 1 },
    ]

    render(<DiffViewer diffLines={diffWithHTML} />)

    expect(screen.getByText('<script>alert("xss")</script>')).toBeInTheDocument()
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })

  it('handles empty string content in diff lines', () => {
    const emptyContentLine: DiffLine[] = [{ type: 'context', content: '', lineNumber: 1 }]

    render(<DiffViewer diffLines={emptyContentLine} />)

    expect(screen.getByTestId('diff-line-context-1')).toBeInTheDocument()
  })

  it('applies monospace font to diff content', () => {
    render(<DiffViewer diffLines={mockDiffLines} />)

    const container = screen.getByRole('region', { name: /diff viewer/i })
    expect(container).toHaveClass('font-mono')
  })
})
