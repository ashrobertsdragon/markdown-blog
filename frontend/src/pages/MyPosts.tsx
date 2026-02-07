import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { useDeleteDraft, useMyPosts } from '@/hooks/usePosts'
import { cn } from '@/lib/utils'
import type { PostFilter } from '@/services/postsApi'

/**
 * MyPosts page component for managing user's blog posts
 *
 * Features:
 * - Filter posts by all/drafts/published status
 * - Paginated list view (20 posts per page)
 * - Actions: Edit, View (published only), Delete
 * - Loading, error, and empty state handling
 * - Delete confirmation dialog
 *
 * @returns User posts management interface
 */
export default function MyPosts() {
  const navigate = useNavigate()

  // State
  const [filter, setFilter] = useState<PostFilter>('all')
  const [page, setPage] = useState(1)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [slugToDelete, setSlugToDelete] = useState<string | null>(null)

  // Hooks
  const { data, isLoading, error } = useMyPosts(filter, page)
  const deleteDraft = useDeleteDraft()

  /**
   * Handle filter button click
   */
  const handleFilterChange = useCallback((newFilter: PostFilter) => {
    setFilter(newFilter)
    setPage(1)
  }, [])

  /**
   * Handle page navigation
   */
  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage)
  }, [])

  /**
   * Open delete confirmation dialog
   */
  const handleDeleteClick = useCallback((slug: string) => {
    setSlugToDelete(slug)
    setDeleteConfirmOpen(true)
  }, [])

  /**
   * Confirm deletion
   */
  const handleDeleteConfirm = useCallback(async () => {
    if (!slugToDelete) return

    try {
      await deleteDraft.mutateAsync(slugToDelete)
    } catch {
      // Error handled by mutation error state
    } finally {
      setDeleteConfirmOpen(false)
      setSlugToDelete(null)
    }
  }, [slugToDelete, deleteDraft])

  /**
   * Format date for display
   */
  const formatDate = useCallback((dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    })
  }, [])

  /**
   * Memoized filter button configuration
   */
  const filterButtons = useMemo(
    () => [
      { label: 'All', value: 'all' as const },
      { label: 'Drafts', value: 'drafts' as const },
      { label: 'Published', value: 'published' as const },
    ],
    []
  )

  // Loading state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-2" aria-live="polite">
          {/* biome-ignore lint/a11y/useSemanticElements: Test expects role="status" on spinner div */}
          <div
            role="status"
            className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
          />
          <span className="text-lg text-muted-foreground">Loading posts...</span>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    const userFriendlyError = error.message?.toLowerCase().includes('network')
      ? 'Network error. Please check your connection and try again.'
      : 'Failed to load posts. Please refresh the page.'

    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Error Loading Posts</AlertTitle>
          <AlertDescription>{userFriendlyError}</AlertDescription>
        </Alert>
      </div>
    )
  }

  // Empty state
  if (!data || data.posts.length === 0) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-50">
        <div className="mx-auto w-full max-w-7xl p-6">
          <h1 className="mb-6 text-3xl font-bold text-gray-800">My Posts</h1>

          {/* Filter Tabs */}
          {/* biome-ignore lint/a11y/useSemanticElements: Using div with role=group for flexbox layout, fieldset would break styling */}
          <div className="mb-6 flex gap-2" role="group" aria-label="Filter posts by status">
            {filterButtons.map(({ label, value }) => (
              <Button
                key={label}
                aria-pressed={filter === value}
                variant={filter === value ? 'default' : 'outline'}
                onClick={() => handleFilterChange(value)}
                className={cn(
                  filter === value && 'bg-primary text-primary-foreground hover:bg-primary/90'
                )}
              >
                {label}
              </Button>
            ))}
          </div>

          <div className="flex min-h-[400px] items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-white p-12">
            {/* biome-ignore lint/a11y/useSemanticElements: role="status" needed for screen reader announcement */}
            <div className="text-center" role="status" aria-live="polite">
              <p className="mb-2 text-lg font-medium text-gray-700">No posts found</p>
              <p className="text-gray-500">Create your first post to get started!</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <div className="mx-auto w-full max-w-7xl p-6">
        {/* Header */}
        <h1 className="mb-6 text-3xl font-bold text-gray-800">My Posts</h1>

        {/* Filter Tabs */}
        {/* biome-ignore lint/a11y/useSemanticElements: Using div with role=group for flexbox layout, fieldset would break styling */}
        <div className="mb-6 flex gap-2" role="group" aria-label="Filter posts by status">
          {filterButtons.map(({ label, value }) => (
            <Button
              key={label}
              aria-pressed={filter === value}
              variant={filter === value ? 'default' : 'outline'}
              onClick={() => handleFilterChange(value)}
              className={cn(
                filter === value && 'bg-primary text-primary-foreground hover:bg-primary/90'
              )}
            >
              {label}
            </Button>
          ))}
        </div>

        {/* Delete Error Alert */}
        {deleteDraft.error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>Failed to delete post. Please try again.</AlertDescription>
          </Alert>
        )}

        {/* Posts Table */}
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Updated
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Slug
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {data.posts.map(post => (
                <tr key={post.slug} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{post.title}</div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <span
                      className={cn(
                        'inline-flex rounded-full px-2 py-1 text-xs font-semibold leading-5',
                        post.published ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      )}
                    >
                      {post.published ? 'Published' : 'Draft'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {formatDate(post.updated_at)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{post.slug}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium">
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/edit/${post.slug}`)}
                        aria-label={`Edit post ${post.title}`}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/posts/${post.slug}`)}
                        disabled={!post.published}
                        aria-label={`View post ${post.title}`}
                      >
                        View
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteClick(post.slug)}
                        disabled={deleteDraft.isPending}
                        aria-label={`Delete post ${post.title}`}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {data.total_pages > 1 && (
          <nav className="mt-6 flex items-center justify-between" aria-label="Pagination">
            <div className="text-sm text-gray-700" aria-live="polite" aria-atomic="true">
              Page {data.page} of {data.total_pages}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                aria-label="Go to previous page"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= data.total_pages}
                aria-label="Go to next page"
              >
                Next
              </Button>
            </div>
          </nav>
        )}

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you sure you want to delete this post?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. The post will be permanently deleted.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setDeleteConfirmOpen(false)}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteConfirm}>Delete</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}
