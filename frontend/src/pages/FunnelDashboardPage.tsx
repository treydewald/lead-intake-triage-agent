import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, ClipboardCheck, Clock3, Users } from 'lucide-react'
import { getFunnelDashboard, type FunnelDashboard } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card, SectionLabel } from '../components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const totalMinutes = Math.floor(seconds / 60)
  if (totalMinutes < 60) {
    const secs = Math.round(seconds % 60)
    return secs > 0 ? `${totalMinutes}m ${secs}s` : `${totalMinutes}m`
  }
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours}h ${String(minutes).padStart(2, '0')}m`
}

export function FunnelDashboardPage() {
  const [dashboard, setDashboard] = useState<FunnelDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getFunnelDashboard()
      .then((data) => {
        if (!cancelled) setDashboard(data)
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load the funnel dashboard.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const awaitingReview = dashboard?.by_status.find((entry) => entry.status === 'awaiting_review')?.count ?? 0

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 sm:gap-4">
      <PageHeader
        title="Lead Funnel & Reviewer Throughput"
        description="Aggregate pipeline performance across every lead — conversion by channel, time-to-resolution, and reviewer throughput."
      />

      {error && <ErrorState message={error} />}
      {loading && !dashboard && !error && <LoadingState label="Loading dashboard…" />}

      {dashboard && dashboard.total_leads === 0 && (
        <EmptyState
          icon={BarChart3}
          title="No leads have entered the pipeline yet"
          description="Once leads start flowing through the pipeline, this dashboard will show conversion, resolution time, and reviewer throughput."
        />
      )}

      {dashboard && dashboard.total_leads > 0 && (
        <>
          <div className="grid grid-cols-3 gap-2 sm:gap-4">
            <StatCard label="Total leads" value={dashboard.total_leads.toLocaleString()} icon={Users} />
            <StatCard
              label="Awaiting review"
              value={String(awaitingReview)}
              icon={ClipboardCheck}
              tone={awaitingReview ? 'amber' : 'neutral'}
            />
            <StatCard
              label="Avg. time to resolution"
              value={formatDuration(dashboard.avg_resolution_seconds)}
              icon={Clock3}
            />
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-3 sm:flex-row sm:gap-4">
            <div className="flex min-h-0 flex-1 flex-col gap-2">
              <SectionLabel>By Source Channel</SectionLabel>
              <Card className="min-h-0 flex-1 overflow-auto">
                <table className="w-full min-w-[380px] text-left text-sm">
                  <thead className="sticky top-0 border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-2.5 font-medium">Channel</th>
                      <th className="px-4 py-2.5 font-medium">Leads</th>
                      <th className="px-4 py-2.5 font-medium">Avg. confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.by_source_channel.map((row) => (
                      <tr
                        key={row.source_channel}
                        className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50"
                      >
                        <td className="px-4 py-2.5 font-medium capitalize">
                          <Link
                            to={`/leads?channel=${encodeURIComponent(row.source_channel)}`}
                            className="text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-1"
                          >
                            {row.source_channel.replace('_', ' ')}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5 text-slate-600">{row.count}</td>
                        <td className="px-4 py-2.5">
                          <ConfidenceMeter value={row.avg_confidence} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>

            <div className="flex min-h-0 flex-1 flex-col gap-2">
              <SectionLabel>Reviewer Throughput</SectionLabel>
              <Card className="min-h-0 flex-1 overflow-auto">
                {dashboard.reviewer_throughput.length === 0 ? (
                  <EmptyState
                    icon={ClipboardCheck}
                    title="No reviews actioned yet"
                    description="Reviewer throughput appears here once someone approves, rejects, or edits a queued review."
                  />
                ) : (
                  <table className="w-full min-w-[380px] text-left text-sm">
                    <thead className="sticky top-0 border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-2.5 font-medium">Reviewer</th>
                        <th className="px-4 py-2.5 font-medium">Actioned</th>
                        <th className="px-4 py-2.5 font-medium">Avg. time to action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.reviewer_throughput.map((row) => (
                        <tr key={row.reviewer_name} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-2.5 font-medium text-slate-800">{row.reviewer_name}</td>
                          <td className="px-4 py-2.5 text-slate-600">{row.actioned_count}</td>
                          <td className="px-4 py-2.5 text-slate-600">{formatDuration(row.avg_resolution_seconds)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
