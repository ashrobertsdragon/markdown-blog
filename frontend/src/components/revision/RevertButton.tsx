import { useState } from 'react'
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
import { useRevertRevision } from '@/hooks/useRevisions'

interface RevertButtonProps {
  slug: string
  targetSha: string
  commitMessage: string
  onSuccess: () => void
}

export function RevertButton({ slug, targetSha, commitMessage, onSuccess }: RevertButtonProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const { mutate, isPending, isError, error, reset } = useRevertRevision()

  const shortSha = targetSha.slice(0, 7)

  const handleConfirm = () => {
    mutate(
      { slug, targetSha },
      {
        onSuccess: () => {
          setIsDialogOpen(false)
          onSuccess()
        },
      }
    )
  }

  const handleOpenChange = (open: boolean) => {
    setIsDialogOpen(open)
    if (open && isError) {
      reset()
    }
  }

  return (
    <>
      {isError && error && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-destructive bg-destructive/10 p-3"
        >
          <p className="text-sm text-destructive">{error.message}</p>
        </div>
      )}
      <AlertDialog open={isDialogOpen} onOpenChange={handleOpenChange}>
        <AlertDialogTrigger asChild>
          <Button
            variant="destructive"
            disabled={isPending}
            aria-label={`Revert to revision ${shortSha}`}
          >
            {isPending ? 'Reverting...' : 'Revert'}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Revert</AlertDialogTitle>
            <AlertDialogDescription>
              Revert to {shortSha}: {commitMessage}
              <br />
              <br />
              This will overwrite the current draft with the content from this revision. This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={e => {
                e.preventDefault()
                handleConfirm()
              }}
              disabled={isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isPending ? 'Reverting...' : 'Confirm'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
