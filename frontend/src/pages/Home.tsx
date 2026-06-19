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
    return (
      <LoadingSpinner message="Loading posts..." className="min-h-screen bg-slate-950 text-white" />
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-4 text-white">
        <Alert variant="destructive" className="max-w-md bg-red-950 border-red-900 text-red-200">
          <AlertTitle>Connection Error</AlertTitle>
          <AlertDescription>Unable to load posts. Please try again later.</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 selection:bg-purple-500/30">
      {/* Decorative gradient blob background */}
      <div className="pointer-events-none fixed inset-0 flex justify-center overflow-hidden">
        <div className="absolute -top-[20rem] h-[40rem] w-[80rem] rounded-full bg-gradient-to-b from-blue-900/20 to-purple-900/10 blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="text-center mb-24">
          <h1 className="text-5xl font-extrabold tracking-tight text-white sm:text-7xl mb-6 bg-clip-text text-transparent bg-gradient-to-br from-blue-400 via-purple-400 to-pink-400">
            Ashlynn's Blog
          </h1>
          <p className="mx-auto max-w-2xl text-xl text-slate-400 leading-relaxed font-light">
            Thoughts, tutorials, and insights on software engineering, architecture, and building
            elegant web experiences.
          </p>
        </div>

        {posts.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800">
            <h3 className="text-2xl font-medium text-slate-300">No posts yet</h3>
            <p className="mt-2 text-slate-500">Check back soon for new content!</p>
          </div>
        ) : (
          <div className="grid gap-8 md:grid-cols-2">
            {posts.map(post => (
              <Link key={post.slug} to={`/posts/${post.slug}`} className="group block h-full">
                <Card className="h-full flex flex-col bg-slate-900/80 backdrop-blur border-slate-800 transition-all duration-300 hover:shadow-2xl hover:shadow-purple-900/20 hover:border-purple-500/30 hover:-translate-y-2 overflow-hidden">
                  <CardHeader className="pb-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-blue-400/90 tracking-wide uppercase">
                        {post.published_at
                          ? format(new Date(post.published_at), 'MMMM d, yyyy')
                          : 'Recently'}
                      </span>
                    </div>
                    <CardTitle className="text-2xl font-bold text-slate-100 group-hover:text-purple-300 transition-colors line-clamp-2 leading-tight">
                      {post.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-grow">
                    <p className="text-slate-400/90 line-clamp-3 leading-relaxed font-light text-[15px]">
                      {(() => {
                        const rawHtml = post.html_content ?? ''
                        const plainText = rawHtml.replace(/<[^>]+>/g, '').trim()
                        const limit = 150
                        if (plainText.length <= limit) return plainText
                        return `${plainText.substring(0, limit).trimEnd()}...`
                      })()}
                    </p>
                  </CardContent>
                  <CardFooter className="pt-0 pb-6 text-sm font-semibold text-purple-400 flex items-center tracking-wide">
                    Read article
                    <span className="ml-2 inline-block transition-transform duration-300 group-hover:translate-x-2">
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
