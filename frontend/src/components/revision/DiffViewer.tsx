import { useState } from 'react'
import type { DiffLine } from '../../types/revision'

interface DiffViewerProps {
  diffLines: DiffLine[]
  isLoading?: boolean
  error?: string | null
}

export function DiffViewer({ diffLines, isLoading, error }: DiffViewerProps) {
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)

  const handleCopy = async () => {
    const diffText = diffLines
      .map(line => {
        const prefix = line.type === 'addition' ? '+ ' : line.type === 'deletion' ? '- ' : '  '
        return `${prefix}${line.content}`
      })
      .join('\n')

    try {
      await navigator.clipboard.writeText(diffText)
      setCopyFeedback('Copied!')
      setTimeout(() => setCopyFeedback(null), 2000)
    } catch {
      setCopyFeedback('Failed to copy')
      setTimeout(() => setCopyFeedback(null), 2000)
    }
  }

  if (isLoading) {
    return (
      <output className="flex items-center justify-center p-8">
        <div className="text-gray-600">Loading diff...</div>
      </output>
    )
  }

  if (error) {
    return (
      <div role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-red-700">
        {error}
      </div>
    )
  }

  if (diffLines.length === 0) {
    return <div className="p-8 text-center text-gray-500">No changes detected</div>
  }

  return (
    <section data-testid="diff-viewer" aria-label="Diff viewer" className="font-mono text-sm">
      <div className="space-y-0 border border-gray-200 bg-white">
        {diffLines.map((line, index) => {
          const displayNumber = line.line_number_new ?? line.line_number_old ?? index + 1
          const bgColor =
            line.type === 'addition'
              ? 'bg-green-100'
              : line.type === 'deletion'
                ? 'bg-red-100'
                : 'bg-gray-50'
          const prefix = line.type === 'addition' ? '+' : line.type === 'deletion' ? '-' : ' '

          return (
            <div
              key={`${line.type}-${displayNumber}-${index}`}
              data-testid={`diff-line-${line.type}-${displayNumber}`}
              className={`${bgColor} flex whitespace-pre`}
            >
              <span className="w-12 select-none bg-gray-100 px-2 py-1 text-right text-gray-500">
                {displayNumber}
              </span>
              <span className="px-2 py-1">
                <span className="select-none">{prefix}</span>
                {line.content}
              </span>
            </div>
          )
        })}
      </div>
      <button
        type="button"
        onClick={handleCopy}
        aria-label="Copy diff to clipboard"
        className="mt-4 rounded bg-gray-100 px-4 py-2 text-sm hover:bg-gray-200"
      >
        {copyFeedback || 'Copy'}
      </button>
    </section>
  )
}
