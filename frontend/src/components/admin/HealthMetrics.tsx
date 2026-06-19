import type React from 'react'
import { useSystemHealth } from '@/hooks/admin/useSystemHealth'
import type { HealthStatus } from '@/services/admin/adminApi'

/**
 * Converts a raw uptime in seconds to a human-readable string.
 *
 * Omits leading zero components but always emits at least seconds so the
 * display is never blank for an uptime of zero. Clamps negative input to 0.
 */
function formatUptime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const days = Math.floor(s / 86400)
  const hours = Math.floor((s % 86400) / 3600)
  const minutes = Math.floor((s % 3600) / 60)
  const secs = s % 60

  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)
  if (parts.length === 0 || secs > 0) parts.push(`${secs}s`)

  return parts.join(' ')
}

/**
 * Returns Tailwind colour classes for a given HealthStatus.
 *
 * The class names contain "green", "yellow", or "red" so tests can query them
 * with `[class*="green"]` etc.
 */
function statusColour(status: HealthStatus): { badge: string; dot: string } {
  switch (status) {
    case 'healthy':
      return { badge: 'text-green-700 bg-green-100', dot: 'bg-green-500' }
    case 'degraded':
      return { badge: 'text-yellow-700 bg-yellow-100', dot: 'bg-yellow-500' }
    case 'unhealthy':
      return { badge: 'text-red-700 bg-red-100', dot: 'bg-red-500' }
    default:
      return { badge: 'text-gray-700 bg-gray-100', dot: 'bg-gray-400' }
  }
}

/**
 * Returns the capitalised display label for a HealthStatus.
 */
function statusLabel(status: HealthStatus): string {
  switch (status) {
    case 'healthy':
      return 'Healthy'
    case 'degraded':
      return 'Degraded'
    case 'unhealthy':
      return 'Unhealthy'
    default:
      return 'Unknown'
  }
}

interface StatusCardProps {
  title: string
  status: HealthStatus
  testId?: string
}

/**
 * Renders a single health status card with a coloured indicator badge.
 */
function StatusCard({ title, status, testId }: StatusCardProps): React.ReactElement {
  const colours = statusColour(status)
  return (
    <div data-testid={testId} className="rounded-lg border p-4 flex flex-col gap-2">
      <span className="text-sm font-medium text-gray-600">{title}</span>
      <div className="flex items-center gap-2">
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${colours.dot}`} />
        <span className={`text-sm font-semibold px-2 py-0.5 rounded ${colours.badge}`}>
          {statusLabel(status)}
        </span>
      </div>
    </div>
  )
}

/**
 * HealthMetrics displays system health status cards for the admin dashboard.
 *
 * Shows overall status, database, filesystem, and GitHub API health indicators
 * alongside a human-readable uptime counter. Indicator colours reflect the
 * current HealthStatus: green=healthy, yellow=degraded, red=unhealthy.
 */
export function HealthMetrics(): React.ReactElement {
  const { data, isLoading, isError } = useSystemHealth()

  if (isLoading) {
    return <div className="hidden" aria-hidden="true" data-testid="loading" />
  }

  if (isError) {
    return <div>Failed to load system health</div>
  }

  if (!data) {
    return <div className="hidden" aria-hidden="true" data-testid="loading" />
  }

  return (
    <section aria-label="System health" className="space-y-4">
      {/* aria-live so screen readers announce status changes on auto-refresh */}
      <div aria-live="polite" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatusCard title="Overall" status={data.status} testId="api-status" />
        <StatusCard title="Database" status={data.database} testId="database-status" />
        <StatusCard title="Filesystem" status={data.filesystem} />
        <StatusCard title="GitHub" status={data.github_api} />
      </div>
      <div className="rounded-lg border p-4 flex items-center gap-2 text-sm text-gray-700">
        <span className="font-medium">Uptime:</span>
        <span>{formatUptime(data.uptime_seconds)}</span>
      </div>
    </section>
  )
}
