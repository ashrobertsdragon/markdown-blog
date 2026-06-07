import { ErrorLogTable } from '@/components/admin/ErrorLogTable'
import { HealthMetrics } from '@/components/admin/HealthMetrics'

/**
 * Thin composition boundary for the system health section of the admin dashboard.
 *
 * Each child component owns its own query lifecycle (data fetching, 60-second
 * auto-refresh for health, loading spinners, error banners, and empty states),
 * so this page stays free of data-fetching logic. Keeping the page stateless
 * means it remains testable in isolation via mocks and is easy to extend without
 * touching the components' internal query behaviour.
 */
export default function SystemPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">System</h1>
      <div className="space-y-8">
        <HealthMetrics />
        <ErrorLogTable />
      </div>
    </div>
  )
}
