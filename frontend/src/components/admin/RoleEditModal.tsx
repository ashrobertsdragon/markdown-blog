import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { useUpdateUserRole } from '@/hooks/admin/useUsers'
import type { User, UserRole } from '@/services/admin/adminApi'

export interface RoleEditModalProps {
  user: User
  onClose: () => void
}

/**
 * RoleEditModal renders a modal dialog for changing a user's role.
 *
 * Built on the ShadCN Dialog primitive (Radix), which supplies modal
 * semantics, focus trapping, and Escape/backdrop dismiss. Two radios
 * (authenticated / admin) pre-select the user's current role; the save button
 * stays disabled until the selection changes. Submits via the useUpdateUserRole
 * mutation and closes on success, cancel, Escape, or backdrop click.
 *
 * @param props.user - The user whose role is being edited
 * @param props.onClose - Callback fired when the modal should be dismissed
 */
export function RoleEditModal({ user, onClose }: RoleEditModalProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole>(user.role)
  const { mutate, isPending } = useUpdateUserRole()

  const isDirty = selectedRole !== user.role
  const isSubmitDisabled = !isDirty || isPending

  const handleSubmit = () => {
    if (!isDirty) return
    mutate({ userId: user.id, role: selectedRole }, { onSuccess: () => onClose() })
  }

  return (
    <Dialog open onOpenChange={open => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Role</DialogTitle>
          <DialogDescription>{user.email}</DialogDescription>
        </DialogHeader>

        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">Select role</legend>

          <Label className="flex cursor-pointer items-center gap-2 text-sm font-normal">
            <input
              type="radio"
              name="role"
              value="authenticated"
              checked={selectedRole === 'authenticated'}
              onChange={() => setSelectedRole('authenticated')}
              className="accent-primary"
            />
            Authenticated
          </Label>

          <Label className="flex cursor-pointer items-center gap-2 text-sm font-normal">
            <input
              type="radio"
              name="role"
              value="admin"
              checked={selectedRole === 'admin'}
              onChange={() => setSelectedRole('admin')}
              className="accent-primary"
            />
            Admin
          </Label>
        </fieldset>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" disabled={isSubmitDisabled} onClick={handleSubmit}>
            {isPending ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
