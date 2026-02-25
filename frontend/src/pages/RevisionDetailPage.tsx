import { ArrowLeft } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { RevisionDetail } from '@/components/revision/RevisionDetail'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { useDraft } from '@/hooks/usePosts'

export default function RevisionDetailPage() {
  const { slug = '', sha = '' } = useParams<{ slug: string; sha: string }>()
  const navigate = useNavigate()

  const { role } = useAuth()
  const { data: draft, isLoading, error } = useDraft(slug)

  if (isLoading) {
    return <LoadingSpinner message="Loading post details..." className="min-h-screen" />
  }

  if (error || !draft) {
    const isForbidden =
      (error as Error & { response?: { status: number } })?.response?.status === 403 ||
      error?.message?.includes('403')

    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {isForbidden
              ? 'You are not authorized to view this revision.'
              : error?.message || 'Post not found.'}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <div className="mx-auto w-full max-w-4xl p-6">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate(`/posts/${slug}/revisions`)}
            className="mb-4 -ml-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to History
          </Button>
          <h1 className="text-3xl font-bold text-gray-800">Revision Detail</h1>
          <p className="mt-2 text-gray-600">
            Post: <span className="font-semibold text-gray-900">{draft.title}</span>
          </p>
        </div>

        <RevisionDetail
          slug={slug}
          revisionSha={sha}
          isAuthor={role === 'author' || role === 'admin'}
          onRevertSuccess={() => navigate(`/edit/${slug}`)}
        />
      </div>
    </div>
  )
}
