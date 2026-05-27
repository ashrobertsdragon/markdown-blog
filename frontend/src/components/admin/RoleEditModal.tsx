import { useEffect, useId, useRef, useState } from 'react'
import { useUpdateUserRole } from '@/hooks/admin/useUsers'
import { cn } from '@/lib/utils'
import type { User, UserRole } from '@/services/admin/adminApi'

export interface RoleEditModalProps {
  user: User
  onClose: () => void
}

/**
 * RoleEditModal renders an accessible modal dialog for changing a user's role.
 *
 * Displays the target user's email, two radio buttons (authenticated / admin)
 * pre-selected to the user's current role, a submit button that is disabled
 * until the selection changes, and a cancel button. Submits via the
 * useUpdateUserRole mutation and calls onClose on success, cancel, Escape, or
 * backdrop click.
 *
 * @param props.user - The user whose role is being edited
 * @param props.onClose - Callback fired when the modal should be dismissed
 */
export function RoleEditModal({ user, onClose }: RoleEditModalProps) {
  const titleId = useId()
  const descId = useId()
  const [selectedRole, setSelectedRole] = useState<UserRole>(user.role)
  const { mutate, isPending } = useUpdateUserRole()
  const onCloseRef = useRef(onClose)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const saveRef = useRef<HTMLButtonElement>(null)
  const authenticatedRadioRef = useRef<HTMLInputElement>(null)
  const adminRadioRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    onCloseRef.current = onClose
  })

  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onCloseRef.current()
        return
      }

      if (event.key === 'Tab') {
        const focusables = [
          authenticatedRadioRef.current,
          adminRadioRef.current,
          cancelRef.current,
          saveRef.current,
        ].filter((el): el is HTMLInputElement | HTMLButtonElement => el !== null)

        if (focusables.length === 0) return

        const first = focusables[0] as HTMLInputElement | HTMLButtonElement
        const last = focusables[focusables.length - 1] as HTMLInputElement | HTMLButtonElement

        if (event.shiftKey) {
          if (document.activeElement === first) {
            event.preventDefault()
            last.focus()
          }
        } else {
          if (document.activeElement === last) {
            event.preventDefault()
            first.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const isDirty = selectedRole !== user.role
  const isSubmitDisabled = !isDirty || isPending

  const handleSubmit = () => {
    if (!isDirty) return
    mutate({ userId: user.id, role: selectedRole }, { onSuccess: () => onCloseRef.current() })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <button
        type="button"
        tabIndex={-1}
        aria-label="Close dialog"
        data-testid="role-edit-modal-backdrop"
        onClick={onClose}
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
          Edit Role
        </h2>

        <p id={descId} className="text-sm text-gray-600">
          {user.email}
        </p>

        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">Select role</legend>

          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input
              ref={authenticatedRadioRef}
              type="radio"
              name="role"
              value="authenticated"
              checked={selectedRole === 'authenticated'}
              onChange={() => setSelectedRole('authenticated')}
              className="accent-blue-600"
            />
            Authenticated
          </label>

          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input
              ref={adminRadioRef}
              type="radio"
              name="role"
              value="admin"
              checked={selectedRole === 'admin'}
              onChange={() => setSelectedRole('admin')}
              className="accent-blue-600"
            />
            Admin
          </label>
        </fieldset>

        <div className="flex justify-end gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onClose}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium',
              'border border-gray-300 bg-white text-gray-700',
              'hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-400'
            )}
          >
            Cancel
          </button>

          <button
            ref={saveRef}
            type="button"
            disabled={isSubmitDisabled}
            onClick={handleSubmit}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium',
              'bg-blue-600 text-white',
              'hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
