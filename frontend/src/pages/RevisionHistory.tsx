import { useNavigate, useParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { RevisionTimeline } from '@/components/revision/RevisionTimeline'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useAuth } from '@/context/AuthContext'
import { useDraft } from '@/hooks/usePosts'

export default function RevisionHistory() {
  const { slug = '' } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const { role } = useAuth()

  const { data: draft, isLoading, error } = useDraft(slug)

  if (isLoading) {
    return <LoadingSpinner message="Loading post details..." className="min-h-screen" />
  }

  if (error || !draft) {
    const isForbidden =
      (error as { response?: { status?: number } } | null)?.response?.status === 403 ||
      error?.message?.toLowerCase().includes('not authorized') ||
      error?.message?.includes('403')

    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {isForbidden
              ? 'You are not authorized to view revisions for this post.'
              : error?.message || 'Post not found.'}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const handleSelectRevision = (sha: string) => {
    navigate(`/posts/${slug}/revisions/${sha}`)
  }

  return (
    <div className="flex min-h-screen flex-col bg-muted/40">
      <div className="mx-auto w-full max-w-3xl p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Revision History</h1>
          <p className="mt-2 text-muted-foreground">
            Viewing revisions for:{' '}
            <span className="font-semibold text-foreground">{draft.title}</span>
          </p>
        </div>

        <RevisionTimeline
          slug={slug}
          currentSha=""
          onSelectRevision={handleSelectRevision}
          isAuthor={role === 'author' || role === 'admin'}
        />
      </div>
    </div>
  )
}
