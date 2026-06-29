import { format } from 'date-fns'
import type React from 'react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
      return 'text-red-700 bg-red-100 dark:text-red-300 dark:bg-red-950'
    case 'warning':
      return 'text-yellow-700 bg-yellow-100 dark:text-yellow-300 dark:bg-yellow-950'
    case 'info':
      return 'text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-950'
    default:
      return 'text-muted-foreground bg-muted'
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
    return <div className="hidden" aria-hidden="true" data-testid="loading" />
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
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Timestamp</TableHead>
            <TableHead scope="col">Level</TableHead>
            <TableHead scope="col">Message</TableHead>
            <TableHead scope="col">Context</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {errors.map(entry => {
            const isExpanded = expandedIds.has(entry.id)
            const hasContext = Object.keys(entry.context).length > 0
            const shortMessage = entry.message.slice(0, 60)
            // align-top prevents cell misalignment when the context panel is expanded
            return (
              <TableRow key={entry.id} className="align-top">
                <TableCell className="whitespace-nowrap text-muted-foreground">
                  {formatTimestamp(entry.timestamp)}
                </TableCell>
                <TableCell>
                  <span
                    className={`inline-block text-xs font-semibold px-2 py-0.5 rounded ${levelColour(entry.level)}`}
                  >
                    {entry.level}
                  </span>
                </TableCell>
                <TableCell>{entry.message}</TableCell>
                <TableCell>
                  {hasContext && (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      aria-label={
                        isExpanded
                          ? `Collapse context for: ${shortMessage}`
                          : `Expand context for: ${shortMessage}`
                      }
                      onClick={() => setExpandedIds(prev => toggleId(prev, entry.id))}
                    >
                      {isExpanded ? 'Collapse' : 'Expand'}
                    </Button>
                  )}
                  {isExpanded && hasContext && (
                    <figure className="mt-2">
                      <figcaption className="sr-only">Error context details</figcaption>
                      <pre className="text-xs bg-muted rounded p-2 overflow-auto max-w-xs whitespace-pre-wrap">
                        {safeStringify(entry.context)}
                      </pre>
                    </figure>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
