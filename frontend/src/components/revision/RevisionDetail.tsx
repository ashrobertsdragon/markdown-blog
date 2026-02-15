import { useRevisionDetail } from '@/hooks/useRevisions'

export interface RevisionDetailProps {
  postId: string
  revisionSha: string
  isAuthor: boolean
  onRevertClick?: () => void
}

/**
 * RevisionDetail component for displaying full revision details
 *
 * Shows complete revision metadata including author, timestamp, commit SHA, message,
 * and badges for current/revert status. Displays the HTML content and optionally
 * shows a revert button for authors.
 */
export function RevisionDetail({
  postId,
  revisionSha,
  isAuthor,
  onRevertClick,
}: RevisionDetailProps) {
  const { data, isLoading, isError, error } = useRevisionDetail(postId, revisionSha)

  if (isLoading) {
    return (
      <div
        data-testid="revision-detail-loading"
        aria-live="polite"
        className="space-y-6 animate-pulse"
      >
        <div className="space-y-3">
          <div className="h-8 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-4/5" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div
        data-testid="revision-detail-error"
        aria-live="assertive"
        className="p-6 bg-red-50 border border-red-200 rounded-lg"
      >
        <p className="text-red-800 font-medium text-lg">Failed to load revision</p>
        <p className="text-red-600 mt-2">{error?.message || 'Unknown error occurred'}</p>
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
      <header className="border-b border-gray-200 pb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">{data.commit_message}</h2>

        <div className="metadata space-y-2">
          <div className="flex items-center gap-4 flex-wrap text-sm">
            <span className="text-gray-700">
              <span className="font-medium">Author:</span> {data.author.name}
            </span>
            <span className="text-gray-400">•</span>
            <span className="text-gray-700">
              <span className="font-medium">Date:</span> {new Date(data.timestamp).toLocaleString()}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <code
              data-testid="revision-detail-sha"
              title={data.commit_sha}
              className="text-sm font-mono px-2 py-1 bg-gray-100 rounded text-gray-800"
            >
              {data.short_sha}
            </code>

            {data.is_current && (
              <span
                data-testid="revision-detail-current-badge"
                className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800"
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

      {isAuthor && onRevertClick && (
        <div className="pt-6 border-t border-gray-200">
          <button
            type="button"
            data-testid="revision-detail-revert-button"
            onClick={onRevertClick}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Revert to This Version
          </button>
        </div>
      )}
    </article>
  )
}
