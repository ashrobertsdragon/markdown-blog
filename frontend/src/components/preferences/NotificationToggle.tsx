import { useId } from 'react'

export interface NotificationToggleProps {
  label: string
  checked: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
}

/**
 * Toggle component for a single notification preference
 *
 * Purely presentational component that renders a labelled checkbox.
 * All async operations and error handling are managed by the parent.
 */
export function NotificationToggle({
  label,
  checked,
  onChange,
  disabled = false,
}: NotificationToggleProps): React.ReactElement {
  const id = useId()

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        disabled={disabled}
      />
    </div>
  )
}
