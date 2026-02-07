import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { MarkdownEditor } from '@/components/post/MarkdownEditor'
import { PreviewPane } from '@/components/post/PreviewPane'
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
import { useDraft, usePublishPost, useSaveDraft } from '@/hooks/usePosts'
import { cn } from '@/lib/utils'

/**
 * PostEditor page component for editing blog post drafts
 *
 * Features:
 * - Markdown editing with real-time preview
 * - Auto-save on Ctrl+S/Cmd+S
 * - Save and publish workflows
 * - Loading and error state handling
 *
 * @returns Post editor interface
 */
export default function PostEditor() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()

  // State
  const [content, setContent] = useState('')
  const [showPreview, setShowPreview] = useState(false)
  const [showPublishDialog, setShowPublishDialog] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Refs
  const successAlertRef = useRef<HTMLDivElement>(null)

  // Hooks
  const { data: draft, isLoading, error } = useDraft(slug || '')
  const saveDraft = useSaveDraft()
  const publishPost = usePublishPost()

  // Sync content from draft data
  useEffect(() => {
    if (draft?.content) {
      setContent(draft.content)
    }
  }, [draft])

  // Auto-dismiss save success message and focus alert
  useEffect(() => {
    if (saveSuccess) {
      successAlertRef.current?.focus()
      const timer = setTimeout(() => setSaveSuccess(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [saveSuccess])

  /**
   * Save draft content
   */
  const handleSave = async () => {
    if (!slug) return

    try {
      await saveDraft.mutateAsync({ slug, content })
      setSaveSuccess(true)
    } catch {
      // Error handled by mutation error state
    }
  }

  /**
   * Publish draft to database
   */
  const handlePublish = async () => {
    if (!slug) return

    try {
      await publishPost.mutateAsync(slug)
      setShowPublishDialog(false)
      navigate(`/posts/${slug}`)
    } catch {
      // Error handled by mutation error state
      setShowPublishDialog(false)
    }
  }

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
          <span className="text-lg text-muted-foreground">Loading draft...</span>
        </div>
      </div>
    )
  }

  // Error state - draft not found or fetch failed
  if (error || !draft) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Error Loading Draft</AlertTitle>
          <AlertDescription>
            {error?.message || 'Draft not found. Please check the URL and try again.'}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <div className="mx-auto w-full max-w-7xl p-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">{draft.title}</h1>
            <p className="mt-1 text-sm text-gray-600">
              Last updated: {new Date(draft.updated_at).toLocaleString()}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={() => setShowPreview(!showPreview)}
              className="hidden lg:inline-flex"
              aria-label={showPreview ? 'Hide preview pane' : 'Show preview pane'}
            >
              {showPreview ? 'Hide Preview' : 'Show Preview'}
            </Button>

            <Button
              variant="outline"
              onClick={() => setShowPreview(!showPreview)}
              className="lg:hidden"
              aria-label={showPreview ? 'Hide preview pane' : 'Show preview pane'}
            >
              {showPreview ? 'Edit' : 'Preview'}
            </Button>

            <Button
              variant="secondary"
              onClick={handleSave}
              disabled={saveDraft.isPending}
              className={cn(saveDraft.isPending && 'opacity-50 cursor-not-allowed')}
              aria-label={saveDraft.isPending ? 'Saving draft' : 'Save draft (Ctrl+S)'}
            >
              {saveDraft.isPending ? 'Saving...' : 'Save'}
            </Button>

            <Button
              onClick={() => setShowPublishDialog(true)}
              disabled={publishPost.isPending}
              className={cn(publishPost.isPending && 'opacity-50 cursor-not-allowed')}
              aria-label={publishPost.isPending ? 'Publishing' : 'Publish'}
            >
              {publishPost.isPending ? 'Publishing...' : 'Publish'}
            </Button>
          </div>
        </div>

        {/* Success Message */}
        {saveSuccess && (
          <Alert ref={successAlertRef} tabIndex={-1} className="mb-6 bg-green-50 border-green-200">
            <AlertDescription className="text-green-800">
              Draft saved successfully!
            </AlertDescription>
          </Alert>
        )}

        {/* Save Error */}
        {saveDraft.error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Error Saving Draft</AlertTitle>
            <AlertDescription>{saveDraft.error.message}</AlertDescription>
          </Alert>
        )}

        {/* Publish Error */}
        {publishPost.error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Error Publishing Post</AlertTitle>
            <AlertDescription>{publishPost.error.message}</AlertDescription>
          </Alert>
        )}

        {/* Editor Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Editor Column (always shown on desktop, toggle on mobile) */}
          <div className={cn('lg:col-span-1', showPreview && 'hidden lg:block')}>
            <MarkdownEditor value={content} onChange={setContent} onSave={handleSave} />
          </div>

          {/* Preview Column (only shown when enabled) */}
          {showPreview && (
            <div className="lg:col-span-1">
              <PreviewPane content={content} />
            </div>
          )}
        </div>

        {/* Publish Confirmation Dialog */}
        <AlertDialog open={showPublishDialog} onOpenChange={setShowPublishDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Publish Post</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to publish this post? It will be visible to all readers.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handlePublish}>Publish</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}
