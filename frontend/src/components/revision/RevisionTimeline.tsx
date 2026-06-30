import { useState } from 'react'
import { useRevisionHistory } from '@/hooks/useRevisions'
import type { RevisionListItem } from '@/services/revisionsApi'

export interface RevisionTimelineProps {
  slug: string
  currentSha: string
  onSelectRevision: (sha: string) => void
  isAuthor: boolean
}

type ViewState = 'initialLoading' | 'error' | 'empty' | 'list'

interface RevisionItemProps {
  revision: RevisionListItem
  isCurrent: boolean
  isInteractive: boolean
  onSelect: (sha: string) => void
}

/**
 * Individual revision item component with interactive behavior
 */
function RevisionItem({ revision, isCurrent, isInteractive, onSelect }: RevisionItemProps) {
  const handleActivate = () => {
    if (isInteractive) {
      onSelect(revision.short_sha)
    }
  }

  const handleKeyDown: React.KeyboardEventHandler<HTMLLIElement> = e => {
    if (!isInteractive) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleActivate()
    }
  }

  return (
    <li
      key={revision.id}
      data-testid={`revision-item-${revision.short_sha}`}
      data-current={isCurrent}
      data-interactive={isInteractive}
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onClick={handleActivate}
      onKeyDown={handleKeyDown}
      aria-label={`Revision ${revision.short_sha} by User ${revision.author_id} ${revision.relative_time}${isCurrent ? ' (current)' : ''}`}
      aria-current={isCurrent ? 'true' : 'false'}
      className={`
        revision-item
        p-4 border rounded-lg transition-all
        ${isCurrent ? 'border-primary bg-accent' : 'border-border bg-card'}
        ${isInteractive ? 'cursor-pointer hover:border-muted-foreground/50 hover:shadow-md' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <code
              data-testid={`revision-sha-${revision.short_sha}`}
              title={revision.commit_sha}
              className="text-sm font-mono font-medium text-foreground"
            >
              {revision.short_sha}
            </code>
            {isCurrent && (
              <span
                data-testid={`revision-current-badge-${revision.short_sha}`}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300"
              >
                ⭐ Current
              </span>
            )}
            {revision.is_revert && (
              <span
                data-testid={`revision-revert-badge-${revision.short_sha}`}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 dark:bg-yellow-950 text-yellow-800 dark:text-yellow-300"
              >
                Revert
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground truncate">{revision.commit_message}</p>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
            <span>User {revision.author_id}</span>
            <span>•</span>
            <span>{revision.relative_time}</span>
          </div>
        </div>
      </div>
    </li>
  )
}

/**
 * Loading skeleton for initial data fetch
 */
function InitialLoadingSkeleton() {
  return (
    <div
      data-testid="revision-timeline-loading"
      aria-live="polite"
      className="space-y-4 animate-pulse"
    >
      {[1, 2, 3].map(i => (
        <div key={i} className="h-20 bg-muted rounded-lg" />
      ))}
    </div>
  )
}

/**
 * Error state with retry button
 */
function ErrorState({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  return (
    <div
      role="alert"
      data-testid="revision-timeline-error"
      aria-live="assertive"
      className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-lg"
    >
      <p className="text-destructive font-medium">Failed to load revisions</p>
      <p className="text-destructive text-sm mt-1">
        {(error as { response?: { data?: { error?: string } } } | null)?.response?.data?.error ??
          error?.message}
      </p>
      <button
        type="button"
        data-testid="revision-timeline-retry"
        onClick={onRetry}
        className="mt-3 px-4 py-2 bg-destructive text-white rounded hover:bg-destructive/90 transition-colors"
      >
        Retry
      </button>
    </div>
  )
}

/**
 * Empty state when no revisions exist
 */
function EmptyState() {
  return (
    <div
      data-testid="revision-timeline-empty"
      className="p-8 text-center text-muted-foreground border border-border rounded-lg"
    >
      <p>No revisions yet</p>
    </div>
  )
}

/**
 * Main revision list content with pagination
 */
function RevisionTimelineContent({
  data,
  isAuthor,
  currentSha,
  isLoading,
  skip,
  onLoadMore,
  onSelectRevision,
}: {
  data: NonNullable<ReturnType<typeof useRevisionHistory>['data']>
  isAuthor: boolean
  currentSha: string
  isLoading: boolean
  skip: number
  onLoadMore: () => void
  onSelectRevision: (sha: string) => void
}) {
  const showFooter = data.has_more || (isLoading && skip > 0)

  return (
    <div data-testid="revision-timeline" className="revision-timeline space-y-4">
      <ul data-testid="revision-timeline-list" className="space-y-3">
        {data.revisions.map((revision, index) => (
          <RevisionItem
            key={revision.id}
            revision={revision}
            isCurrent={currentSha ? revision.short_sha === currentSha : index === 0 && skip === 0}
            isInteractive={isAuthor}
            onSelect={onSelectRevision}
          />
        ))}
      </ul>

      {showFooter && (
        <div className="pt-2">
          {isLoading && skip > 0 ? (
            <div data-testid="revision-timeline-load-more-loading" className="text-center py-2">
              <span className="text-sm text-muted-foreground">Loading...</span>
            </div>
          ) : (
            data.has_more && (
              <button
                type="button"
                data-testid="revision-timeline-load-more"
                onClick={onLoadMore}
                disabled={isLoading}
                className="w-full px-4 py-2 border border-border rounded-lg text-sm font-medium text-foreground bg-card hover:bg-muted/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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

/**
 * RevisionTimeline component for displaying chronological revision history
 *
 * Displays a paginated list of post revisions with visual indicators for the current
 * revision and revert operations. Only allows selection when user is the author.
 */
export function RevisionTimeline({
  slug,
  currentSha,
  onSelectRevision,
  isAuthor,
}: RevisionTimelineProps) {
  const [skip, setSkip] = useState(0)
  const { data, isLoading, isError, error, refetch } = useRevisionHistory(slug, skip, 20)

  const handleLoadMore = () => {
    if (data?.revisions.length) {
      setSkip(prev => prev + data.revisions.length)
    }
  }

  if (isLoading && skip > 0 && !data) {
    return (
      <div data-testid="revision-timeline-load-more-loading" className="text-center py-2">
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    )
  }

  const hasRevisions = !!data?.revisions?.length
  let viewState: ViewState

  if (isLoading && !data && skip === 0) {
    viewState = 'initialLoading'
  } else if (isError) {
    viewState = 'error'
  } else if (!hasRevisions) {
    viewState = 'empty'
  } else {
    viewState = 'list'
  }

  return (
    <>
      {viewState === 'initialLoading' && <InitialLoadingSkeleton />}

      {viewState === 'error' && <ErrorState error={error} onRetry={refetch} />}

      {viewState === 'empty' && <EmptyState />}

      {viewState === 'list' && data && (
        <RevisionTimelineContent
          data={data}
          isAuthor={isAuthor}
          currentSha={currentSha}
          isLoading={isLoading}
          skip={skip}
          onLoadMore={handleLoadMore}
          onSelectRevision={onSelectRevision}
        />
      )}
    </>
  )
}
