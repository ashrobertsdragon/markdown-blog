import { useRevisionDetail } from '@/hooks/useRevisions'
import { RevertButton } from './RevertButton'

export interface RevisionDetailProps {
  slug: string
  revisionSha: string
  isAuthor: boolean
  onRevertSuccess?: () => void
}

/**
 * RevisionDetail component for displaying full revision details
 *
 * Shows complete revision metadata including author, timestamp, commit SHA, message,
 * and badges for current/revert status. Displays the HTML content and optionally
 * shows a revert button for authors.
 */
export function RevisionDetail({
  slug,
  revisionSha,
  isAuthor,
  onRevertSuccess,
}: RevisionDetailProps) {
  const { data, isLoading, isError, error } = useRevisionDetail(slug, revisionSha)

  if (isLoading) {
    return (
      <div
        data-testid="revision-detail-loading"
        aria-live="polite"
        className="space-y-6 animate-pulse"
      >
        <div className="space-y-3">
          <div className="h-8 bg-muted rounded w-3/4" />
          <div className="h-4 bg-muted rounded w-full" />
          <div className="h-4 bg-muted rounded w-5/6" />
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded w-full" />
          <div className="h-4 bg-muted rounded w-full" />
          <div className="h-4 bg-muted rounded w-4/5" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div
        data-testid="revision-detail-error"
        aria-live="assertive"
        className="p-6 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-lg"
      >
        <p className="text-destructive font-medium text-lg">Failed to load revision</p>
        <p className="text-destructive mt-2">{error?.message || 'Unknown error occurred'}</p>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <article
      aria-label="Revision Detail"
      data-testid="revision-detail"
      className="revision-detail space-y-6"
    >
      <header className="border-b border-border pb-6">
        <h2 className="text-2xl font-bold text-foreground mb-4">{data.commit_message}</h2>

        <div className="metadata space-y-2">
          <div className="flex items-center gap-4 flex-wrap text-sm">
            <span className="text-foreground">
              <span className="font-medium">Author ID:</span> {data.author_id}
            </span>
            <span className="text-muted-foreground">•</span>
            <span className="text-foreground">
              <span className="font-medium">Date:</span> {new Date(data.timestamp).toLocaleString()}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <code
              data-testid="revision-detail-sha"
              title={data.commit_sha}
              className="text-sm font-mono px-2 py-1 bg-muted rounded text-foreground"
            >
              {data.short_sha}
            </code>

            {data.is_current && (
              <span
                data-testid="revision-detail-current-badge"
                className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300"
              >
                ⭐ Current
              </span>
            )}

            {data.is_revert && (
              <span
                data-testid="revision-detail-revert-badge"
                className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-orange-100 text-orange-800"
              >
                Revert
              </span>
            )}
          </div>
        </div>
      </header>

      <div
        data-testid="revision-detail-content"
        className="content prose prose-slate max-w-none"
        dangerouslySetInnerHTML={{ __html: data.html_content }}
      />

      {isAuthor && (
        <div className="pt-6 border-t border-border">
          <RevertButton
            slug={slug}
            targetSha={data.commit_sha}
            commitMessage={data.commit_message}
            onSuccess={onRevertSuccess || (() => {})}
          />
        </div>
      )}
    </article>
  )
}
