import { format } from 'date-fns'
import type React from 'react'
import { useState } from 'react'
import { useErrorLogs } from '@/hooks/admin/useSystemHealth'
import type { ErrorLogLevel } from '@/services/admin/adminApi'

/**
 * Props for ErrorLogTable.
 *
 * Limit defaults to 50 — callers can reduce it for compact dashboard widgets.
 */
interface ErrorLogTableProps {
  /** Maximum number of log entries to fetch */
  limit?: number
}

/**
 * Returns Tailwind colour classes for a given ErrorLogLevel badge.
 *
 * Class names contain "red", "yellow", "blue", or "gray" for potential
 * colour-based querying in tests and visual distinction in the UI.
 */
function levelColour(level: ErrorLogLevel): string {
  switch (level) {
    case 'error':
      return 'text-red-700 bg-red-100'
    case 'warning':
      return 'text-yellow-700 bg-yellow-100'
    case 'info':
      return 'text-blue-700 bg-blue-100'
    case 'debug':
      return 'text-gray-700 bg-gray-100'
    default:
      return 'text-gray-700 bg-gray-100'
  }
}

/**
 * Formats an ISO timestamp string for display.
 *
 * Uses date-fns `format` to produce "MMM d, yyyy HH:mm:ss" in local time
 * (e.g. "May 29, 2026 09:30:00"). Local time is intentional for log entries —
 * admins typically want to correlate logs with their own timezone. Falls back
 * to the raw string if parsing fails so the table never crashes on a bad value.
 */
function formatTimestamp(timestamp: string): string {
  try {
    return format(new Date(timestamp), 'MMM d, yyyy HH:mm:ss')
  } catch {
    return timestamp
  }
}

const SENSITIVE_KEY_PATTERN = /token|secret|password|key|auth|credential/i

/**
 * Serialises an error context object to indented JSON, redacting values whose
 * key names suggest sensitive data (tokens, passwords, API keys, etc.).
 *
 * This is defense-in-depth: the backend should not populate `context` with
 * secrets, but client-side redaction limits blast radius when it does.
 */
function safeStringify(obj: Record<string, unknown>): string {
  return JSON.stringify(
    obj,
    (k, v) => (k !== '' && SENSITIVE_KEY_PATTERN.test(k) ? '[redacted]' : v),
    2
  )
}

/**
 * Toggles a numeric ID in a Set, returning a new Set.
 */
function toggleId(prev: Set<number>, id: number): Set<number> {
  const next = new Set(prev)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  return next
}

/**
 * ErrorLogTable displays recent application error log entries for the admin
 * dashboard.
 *
 * Renders a table of the last `limit` log entries (default 50), each showing
 * timestamp, log level, message, and an expandable context panel. Context is
 * serialised via `safeStringify` which redacts keys matching sensitive patterns.
 * Shows "No recent errors" when the error list is empty.
 * All user-facing content is rendered as plain text — no dangerouslySetInnerHTML.
 */
export function ErrorLogTable({ limit }: ErrorLogTableProps): React.ReactElement {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const { data, isLoading, isError } = useErrorLogs({ limit })

  if (isLoading) {
    return <output className="hidden" />
  }

  if (isError) {
    return <div>Failed to load error logs</div>
  }

  const errors = data?.errors ?? []

  if (errors.length === 0) {
    return <div>No recent errors</div>
  }

  return (
    <div data-testid="error-log">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Timestamp
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Level
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Message
            </th>
            <th scope="col" className="border-b px-4 py-2 text-left font-semibold">
              Context
            </th>
          </tr>
        </thead>
        <tbody>
          {errors.map(entry => {
            const isExpanded = expandedIds.has(entry.id)
            const hasContext = Object.keys(entry.context).length > 0
            const shortMessage = entry.message.slice(0, 60)
            // align-top prevents cell misalignment when the context panel is expanded
            return (
              <tr key={entry.id} className="border-b hover:bg-gray-50 align-top">
                <td className="px-4 py-2 whitespace-nowrap text-gray-600">
                  {formatTimestamp(entry.timestamp)}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`inline-block text-xs font-semibold px-2 py-0.5 rounded ${levelColour(entry.level)}`}
                  >
                    {entry.level}
                  </span>
                </td>
                <td className="px-4 py-2">{entry.message}</td>
                <td className="px-4 py-2">
                  {hasContext && (
                    <button
                      type="button"
                      aria-label={
                        isExpanded
                          ? `Collapse context for: ${shortMessage}`
                          : `Expand context for: ${shortMessage}`
                      }
                      onClick={() => setExpandedIds(prev => toggleId(prev, entry.id))}
                      className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-700"
                    >
                      {isExpanded ? 'Collapse' : 'Expand'}
                    </button>
                  )}
                  {isExpanded && hasContext && (
                    <figure className="mt-2">
                      <figcaption className="sr-only">Error context details</figcaption>
                      <pre className="text-xs bg-gray-50 rounded p-2 overflow-auto max-w-xs whitespace-pre-wrap">
                        {safeStringify(entry.context)}
                      </pre>
                    </figure>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
