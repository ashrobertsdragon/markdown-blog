import { Link, useParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { usePublicPost } from '@/hooks/usePosts'
import { formatDate } from '@/lib/utils'

/**
 * PublicPost page component
 *
 * Displays a published blog post by slug for public viewing.
 * Fetches post data from the public API endpoint (no authentication required).
 * Shows loading state during fetch, displays post content on success,
 * and shows appropriate error messages for 404 or API failures.
 *
 * @returns Public post page with content display
 */
export default function PublicPost() {
  const { slug } = useParams<{ slug: string }>()
  const { data: post, isLoading, isError } = usePublicPost(slug || '')

  if (isLoading) {
    return <LoadingSpinner message="Loading..." className="min-h-screen" />
  }

  if (isError || !post) {
    return (
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <Alert variant="destructive" role="alert">
          <AlertDescription data-testid="error-message">Post not found</AlertDescription>
        </Alert>
        <div className="mt-6">
          <Link to="/" data-testid="back-to-home">
            <Button variant="outline">Back to Home</Button>
          </Link>
        </div>
      </div>
    )
  }

  const formattedDate = formatDate(post.published_at)

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      <article>
        <header className="mb-8">
          <h1 className="mb-4 text-4xl font-bold text-gray-900" data-testid="post-title">
            {post.title}
          </h1>
          <div className="text-sm text-gray-600" data-testid="post-metadata">
            <span data-testid="post-author">By {post.author}</span>
            <span className="mx-2">•</span>
            <time dateTime={post.published_at} data-testid="published-date">
              {formattedDate}
            </time>
          </div>
        </header>

        <div
          className="prose prose-lg max-w-none"
          data-testid="post-content"
          dangerouslySetInnerHTML={{ __html: post.html_content }}
        />

        <div className="mt-8">
          <Link to="/" data-testid="back-to-home">
            <Button variant="outline">Back to Home</Button>
          </Link>
        </div>
      </article>
    </div>
  )
}
