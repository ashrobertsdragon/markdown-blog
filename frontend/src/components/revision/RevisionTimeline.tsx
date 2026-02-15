import { useState } from 'react'
import { useRevisionHistory } from '@/hooks/useRevisions'

export interface RevisionTimelineProps {
  postId: string
  currentSha: string
  onSelectRevision: (sha: string) => void
  isAuthor: boolean
}

/**
 * RevisionTimeline component for displaying chronological revision history
 *
 * Displays a paginated list of post revisions with visual indicators for the current
 * revision and revert operations. Only allows selection when user is the author.
 */
export function RevisionTimeline({
  postId,
  currentSha,
  onSelectRevision,
  isAuthor,
}: RevisionTimelineProps) {
  const [skip, setSkip] = useState(0)
  const { data, isLoading, isError, error, refetch } = useRevisionHistory(postId, skip, 20)

  const handleLoadMore = () => {
    if (data?.revisions.length) {
      setSkip(prev => prev + data.revisions.length)
    }
  }

  const handleRevisionClick = (shortSha: string) => {
    if (isAuthor) {
      onSelectRevision(shortSha)
    }
  }

  if (isLoading && !data && skip === 0) {
    return (
      <div
        data-testid="revision-timeline-loading"
        aria-live="polite"
        className="space-y-4 animate-pulse"
      >
        {[1, 2, 3].map(i => (
          <div key={i} className="h-20 bg-gray-200 rounded-lg" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div
        data-testid="revision-timeline-error"
        aria-live="assertive"
        className="p-4 bg-red-50 border border-red-200 rounded-lg"
      >
        <p className="text-red-800 font-medium">Failed to load revisions</p>
        <p className="text-red-600 text-sm mt-1">{error?.message}</p>
        <button
          type="button"
          data-testid="revision-timeline-retry"
          onClick={() => refetch()}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (isLoading && skip > 0) {
    return (
      <div data-testid="revision-timeline-load-more-loading" className="text-center py-2">
        <span className="text-sm text-gray-500">Loading...</span>
      </div>
    )
  }

  if (!data?.revisions.length) {
    return (
      <div
        data-testid="revision-timeline-empty"
        className="p-8 text-center text-gray-500 border border-gray-200 rounded-lg"
      >
        <p>No revisions yet</p>
      </div>
    )
  }

  return (
    <div data-testid="revision-timeline-container" className="revision-timeline space-y-4">
      <ul data-testid="revision-timeline-list" className="space-y-3">
        {data.revisions.map(revision => {
          const isCurrent = revision.short_sha === currentSha
          const isInteractive = isAuthor

          return (
            <li
              key={revision.id}
              data-testid={`revision-item-${revision.short_sha}`}
              data-current={isCurrent}
              data-interactive={isInteractive}
              role={isInteractive ? 'button' : undefined}
              tabIndex={isInteractive ? 0 : undefined}
              onClick={() => handleRevisionClick(revision.short_sha)}
              onKeyDown={e => {
                if (isInteractive && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault()
                  handleRevisionClick(revision.short_sha)
                }
              }}
              aria-label={`Revision ${revision.short_sha} by ${revision.author.name} ${revision.relative_time}${isCurrent ? ' (current)' : ''}`}
              aria-current={isCurrent ? 'true' : 'false'}
              className={`
                revision-item
                p-4 border rounded-lg transition-all
                ${isCurrent ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}
                ${isInteractive ? 'cursor-pointer hover:border-gray-400 hover:shadow-md' : ''}
              `}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <code
                      data-testid={`revision-sha-${revision.short_sha}`}
                      title={revision.commit_sha}
                      className="text-sm font-mono font-medium text-gray-900"
                    >
                      {revision.short_sha}
                    </code>
                    {isCurrent && (
                      <span
                        data-testid={`revision-current-badge-${revision.short_sha}`}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        ⭐ Current
                      </span>
                    )}
                    {revision.is_revert && (
                      <span
                        data-testid={`revision-revert-badge-${revision.short_sha}`}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800"
                      >
                        Revert
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-600 truncate">{revision.commit_message}</p>
                  <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                    <span>{revision.author.name}</span>
                    <span>•</span>
                    <span>{revision.relative_time}</span>
                  </div>
                </div>
              </div>
            </li>
          )
        })}
      </ul>

      {(data.has_more || isLoading) && (
        <div className="pt-2">
          {isLoading && skip > 0 ? (
            <div data-testid="revision-timeline-load-more-loading" className="text-center py-2">
              <span className="text-sm text-gray-500">Loading...</span>
            </div>
          ) : (
            data.has_more && (
              <button
                type="button"
                data-testid="revision-timeline-load-more"
                onClick={handleLoadMore}
                disabled={isLoading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Load More
              </button>
            )
          )}
        </div>
      )}
    </div>
  )
}
