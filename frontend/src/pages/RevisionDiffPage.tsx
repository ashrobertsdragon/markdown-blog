import { ArrowLeft } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { DiffViewer } from '@/components/revision/DiffViewer'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useRevisionDiff } from '@/hooks/useRevisions'

export default function RevisionDiffPage() {
  const {
    slug = '',
    sha = '',
    otherSha = '',
  } = useParams<{
    slug: string
    sha: string
    otherSha: string
  }>()
  const navigate = useNavigate()

  const { data, isLoading, isError, error } = useRevisionDiff(slug, sha, otherSha)

  if (isLoading) {
    return <LoadingSpinner message="Calculating diff..." className="min-h-screen" />
  }

  if (isError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error?.message || 'Failed to load diff.'}</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-muted/40">
      <div className="mx-auto w-full max-w-4xl p-6">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate(`/posts/${slug}/revisions/${sha}`)}
            className="mb-4 -ml-2 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Revision
          </Button>
          <h1 className="text-3xl font-bold text-foreground">Compare Revisions</h1>
          <p className="mt-2 text-muted-foreground">
            Comparing <code className="bg-muted px-1 rounded">{sha.slice(0, 7)}</code> to{' '}
            <code className="bg-muted px-1 rounded font-semibold">{otherSha.slice(0, 7)}</code>
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-1 overflow-hidden">
          <DiffViewer diffLines={sha === otherSha ? [] : (data?.diff_lines ?? [])} />
        </div>
      </div>
    </div>
  )
}
