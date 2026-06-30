import { useRef } from 'react'
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
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface ConfirmModalProps {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
}

/**
 * ConfirmModal renders a destructive-action confirmation dialog.
 *
 * Built on the ShadCN AlertDialog primitive (Radix), which provides modal
 * semantics, focus management, Escape/backdrop dismiss, and a focus trap for
 * free. The component is always open while mounted; callers conditionally
 * render it and respond via onConfirm / onCancel.
 *
 * @param title - Heading displayed at the top of the dialog
 * @param message - Body text describing the action to confirm
 * @param confirmText - Label for the confirm button (default: "Confirm")
 * @param cancelText - Label for the cancel button (default: "Cancel")
 * @param onConfirm - Callback invoked when the confirm button is clicked
 * @param onCancel - Callback invoked when the dialog is dismissed or cancelled
 */
export default function ConfirmModal({
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  // Closing via the action button, the cancel button, or Escape all flow
  // through onOpenChange. This ref lets the confirm path suppress the cancel
  // callback so a confirm click does not also fire onCancel.
  const confirmedRef = useRef(false)

  return (
    <AlertDialog
      open
      onOpenChange={open => {
        if (open) return
        if (confirmedRef.current) {
          confirmedRef.current = false
          return
        }
        onCancel()
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{message}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{cancelText}</AlertDialogCancel>
          <AlertDialogAction
            onClick={() => {
              confirmedRef.current = true
              onConfirm()
            }}
            className={cn(buttonVariants({ variant: 'destructive' }))}
          >
            {confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
