import { format } from 'date-fns'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { type PublicPostResponse, postsApi } from '@/services/postsApi'

export default function Home() {
  const [loading, setLoading] = useState<boolean>(true)
  const [posts, setPosts] = useState<PublicPostResponse[]>([])
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const data = await postsApi.listPublicPosts(1, 20)
        setPosts(data.posts)
        setError(null)
      } catch (err) {
        console.error('Failed to load posts:', err)
        setError(err instanceof Error ? err : new Error('Failed to load posts'))
      } finally {
        setLoading(false)
      }
    }

    fetchPosts()
  }, [])

  if (loading) {
    return <LoadingSpinner message="Loading posts..." className="min-h-screen" />
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Connection Error</AlertTitle>
          <AlertDescription>Unable to load posts. Please try again later.</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="mb-24 text-center">
          <h1 className="mb-6 text-5xl font-extrabold tracking-tight text-foreground sm:text-7xl">
            Ashlynn's Blog
          </h1>
          <p className="mx-auto max-w-2xl text-xl font-light leading-relaxed text-muted-foreground">
            Thoughts, tutorials, and insights on software engineering, architecture, and building
            elegant web experiences.
          </p>
        </div>

        {posts.length === 0 ? (
          <div className="rounded-2xl border border-border py-16 text-center">
            <h3 className="text-2xl font-medium text-foreground">No posts yet</h3>
            <p className="mt-2 text-muted-foreground">Check back soon for new content!</p>
          </div>
        ) : (
          <div className="grid gap-8 md:grid-cols-2">
            {posts.map(post => (
              <Link key={post.slug} to={`/posts/${post.slug}`} className="group block h-full">
                <Card className="flex h-full flex-col overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                  <CardHeader className="pb-4">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
                        {post.published_at
                          ? format(new Date(post.published_at), 'MMMM d, yyyy')
                          : 'Recently'}
                      </span>
                    </div>
                    <CardTitle className="line-clamp-2 text-2xl font-bold leading-tight transition-colors group-hover:text-primary">
                      {post.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-grow">
                    <p className="line-clamp-3 text-[15px] font-light leading-relaxed text-muted-foreground">
                      {(() => {
                        const rawHtml = post.html_content ?? ''
                        const plainText = rawHtml.replace(/<[^>]+>/g, '').trim()
                        const limit = 150
                        if (plainText.length <= limit) return plainText
                        return `${plainText.substring(0, limit).trimEnd()}...`
                      })()}
                    </p>
                  </CardContent>
                  <CardFooter className="flex items-center pb-6 pt-0 text-sm font-semibold tracking-wide text-primary">
                    Read article
                    <span className="ml-2 inline-block transition-transform duration-300 group-hover:translate-x-1">
                      →
                    </span>
                  </CardFooter>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
