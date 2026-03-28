import { useEffect, useId, useState } from 'react'

export interface NotificationToggleProps {
  label: string
  checked: boolean
  onToggle: (value: boolean) => Promise<void>
  disabled?: boolean
}

/**
 * Toggle component for a single notification preference
 *
 * Renders a labelled checkbox that calls onToggle with the new boolean state.
 * Shows a loading indicator while the async onToggle promise is pending and
 * disables the checkbox during that period. Surfaces an error message when
 * onToggle rejects; the message auto-dismisses after 3 seconds.
 */
export function NotificationToggle({
  label,
  checked,
  onToggle,
  disabled = false,
}: NotificationToggleProps): React.ReactElement {
  const id = useId()
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (error === null) return
    const timer = setTimeout(() => setError(null), 3000)
    return () => clearTimeout(timer)
  }, [error])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.checked
    setIsPending(true)
    setError(null)
    onToggle(newValue).then(
      () => {
        setIsPending(false)
      },
      (err: unknown) => {
        setError(err instanceof Error ? err.message : 'An error occurred')
        setIsPending(false)
      }
    )
  }

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={handleChange}
        disabled={disabled || isPending}
      />
      {isPending && <output>Saving...</output>}
      {error !== null && <div role="alert">{error}</div>}
    </div>
  )
}
