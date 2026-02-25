import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface LoadingSpinnerProps {
  message?: string
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

/**
 * LoadingSpinner component
 *
 * Reusable loading indicator with optional message.
 * Displays animated spinner with accessibility attributes.
 *
 * @param message - Optional loading message to display below spinner
 * @param className - Optional additional CSS classes for container
 * @param size - Spinner size: 'sm' (4x4), 'md' (8x8), 'lg' (12x12)
 */
export function LoadingSpinner({ message, className, size = 'md' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  }

  return (
    <output className={cn('flex flex-col items-center justify-center gap-2', className)}>
      <Loader2 className={cn('animate-spin', sizeClasses[size])} aria-hidden="true" />
      {message && <p className="text-lg text-gray-600">{message}</p>}
    </output>
  )
}
