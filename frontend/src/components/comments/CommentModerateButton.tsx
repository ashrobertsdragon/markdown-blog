import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { useAdminDeleteComment, useApproveComment } from '@/hooks/useComments'

export interface CommentModerateButtonProps {
  commentId: number
  postSlug: string
  onModerated?: () => void
}

/**
 * Inline moderation controls for a single comment in the admin panel
 *
 * Approve fires immediately — no confirmation — to minimise friction during
 * bulk moderation sessions. Delete requires an AlertDialog confirmation
 * because it is irreversible and destructive.
 */
export function CommentModerateButton({ commentId, onModerated }: CommentModerateButtonProps) {
  const approveMutation = useApproveComment()
  const deleteMutation = useAdminDeleteComment()

  const isPending = approveMutation.isPending || deleteMutation.isPending

  const handleApprove = () => {
    if (onModerated) {
      approveMutation.mutate({ commentId }, { onSuccess: onModerated })
    } else {
      approveMutation.mutate({ commentId })
    }
  }

  const handleDelete = () => {
    if (onModerated) {
      deleteMutation.mutate({ commentId }, { onSuccess: onModerated })
    } else {
      deleteMutation.mutate({ commentId })
    }
  }

  return (
    <div className="flex gap-2">
      <Button
        variant="outline"
        size="sm"
        disabled={isPending}
        onClick={handleApprove}
        className="border-green-500 text-green-700 hover:bg-green-50"
      >
        Approve
      </Button>

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="destructive" size="sm" disabled={isPending}>
            Delete
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete comment?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The comment will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Confirm</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
