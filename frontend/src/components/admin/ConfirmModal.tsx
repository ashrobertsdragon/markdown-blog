import { useEffect, useId, useRef } from 'react'
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
 * ConfirmModal renders an accessible confirmation dialog with a title,
 * message, confirm action, and cancel action.
 *
 * Implements ARIA dialog semantics (role, aria-modal, aria-labelledby,
 * aria-describedby), backdrop dismiss, Escape key dismiss, and a manual
 * focus trap that cycles between the cancel and confirm buttons.
 * Focus moves to the cancel button on mount.
 *
 * @param title - Heading displayed at the top of the dialog
 * @param message - Body text describing the action to confirm
 * @param confirmText - Label for the confirm button (default: "Confirm")
 * @param cancelText - Label for the cancel button (default: "Cancel")
 * @param onConfirm - Callback invoked when the confirm button is clicked
 * @param onCancel - Callback invoked when the cancel button is clicked,
 *   the Escape key is pressed, or the backdrop is clicked
 */
export default function ConfirmModal({
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const titleId = useId()
  const descId = useId()
  const cancelRef = useRef<HTMLButtonElement>(null)
  const confirmRef = useRef<HTMLButtonElement>(null)
  const onCancelRef = useRef(onCancel)

  useEffect(() => {
    onCancelRef.current = onCancel
  })

  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onCancelRef.current()
        return
      }

      if (event.key === 'Tab') {
        const cancel = cancelRef.current
        const confirm = confirmRef.current
        if (!cancel || !confirm) return

        if (event.shiftKey) {
          if (document.activeElement === cancel) {
            event.preventDefault()
            confirm.focus()
          }
        } else {
          if (document.activeElement === confirm) {
            event.preventDefault()
            cancel.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <button
        type="button"
        tabIndex={-1}
        aria-label="Close dialog"
        data-testid="confirm-modal-backdrop"
        onClick={onCancel}
        className="absolute inset-0 bg-black/50 cursor-default"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        className={cn(
          'relative z-10 w-full max-w-md rounded-lg bg-white p-6 shadow-xl',
          'flex flex-col gap-4'
        )}
      >
        <h2 id={titleId} className="text-lg font-semibold text-gray-900">
          {title}
        </h2>

        <p id={descId} className="text-sm text-gray-600">
          {message}
        </p>

        <div className="flex justify-end gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium',
              'border border-gray-300 bg-white text-gray-700',
              'hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-400'
            )}
          >
            {cancelText}
          </button>

          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium',
              'bg-red-600 text-white',
              'hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500'
            )}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
