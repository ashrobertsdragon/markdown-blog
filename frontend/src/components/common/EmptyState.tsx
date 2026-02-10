import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  title: string
  message?: string
  action?: {
    label: string
    onClick: () => void
  }
  icon?: ReactNode
  className?: string
}

/**
 * EmptyState component
 *
 * Reusable empty state display for lists and collections.
 * Shows title, optional message, and optional call-to-action button.
 *
 * @param title - Main heading for empty state
 * @param message - Optional descriptive message
 * @param action - Optional action button with label and onClick handler
 * @param icon - Optional icon element to display above title
 * @param className - Optional additional CSS classes for container
 */
export function EmptyState({ title, message, action, icon, className }: EmptyStateProps) {
  return (
    <div
      className={cn('flex flex-col items-center justify-center gap-4 py-12 text-center', className)}
    >
      {icon && <div className="text-gray-400">{icon}</div>}
      <div>
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        {message && <p className="mt-2 text-sm text-gray-600">{message}</p>}
      </div>
      {action && (
        <Button onClick={action.onClick} variant="default">
          {action.label}
        </Button>
      )}
    </div>
  )
}
