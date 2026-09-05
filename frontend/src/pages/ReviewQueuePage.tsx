import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardCheck, Gauge, History } from 'lucide-react'
import { listLeads, listReviews, type LeadListItem, type ReviewQueueItem } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card, SectionLabel } from '../components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'

const STATUS_BADGE_CLASSES: Record<string, string> = {
  auto_processed: 'bg-emerald-100 text-emerald-800',
  awaiting_review: 'bg-amber-100 text-amber-800',
  rejected: 'bg-slate-200 text-slate-700',
  failed: 'bg-red-100 text-red-800',
  in_progress: 'bg-sky-100 text-sky-800',
}

export function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [recentlyResolved, setRecentlyResolved] = useState<LeadListItem[] | null>(null)

  useEffect(() => {
    let cancelled = false
    listReviews()
      .then((data) => {
        if (!cancelled) setItems(data)
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load the review queue.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    listLeads({ sort: 'created_desc', page_size: 20 })
      .then((data) => {
        if (!cancelled) setRecentlyResolved(data.items.filter((i) => i.status !== 'awaiting_review').slice(0, 8))
      })
      .catch(() => {
        if (!cancelled) setRecentlyResolved([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const withConfidence = items.filter((i) => i.confidence_score != null)
  const avgConfidence =
    withConfidence.length > 0
      ? withConfidence.reduce((sum, i) => sum + (i.confidence_score ?? 0), 0) / withConfidence.length
      : null
  const oldestQueued =
    items.length > 0
      ? items.reduce((oldest, i) => (i.created_at < oldest ? i.created_at : oldest), items[0].created_at)
      : null

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 sm:gap-5">
      <PageHeader
        title="Review Queue"
        description="Leads paused for a human decision before they reach CRM."
      />

      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        <StatCard
          label="Pending reviews"
          value={String(items.length)}
          icon={ClipboardCheck}
          tone={items.length > 0 ? 'amber' : 'neutral'}
        />
        <StatCard
          label="Avg. draft confidence"
          value={avgConfidence != null ? avgConfidence.toFixed(2) : '—'}
          icon={Gauge}
        />
        <StatCard
          label="Oldest queued"
          value={oldestQueued ? new Date(oldestQueued).toLocaleDateString() : '—'}
          hint={oldestQueued ? new Date(oldestQueued).toLocaleTimeString() : undefined}
          icon={History}
        />
      </div>

      {error && <ErrorState message={error} />}

      {loading ? (
        <Card>
          <LoadingState label="Loading review queue…" />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={ClipboardCheck}
            title="No leads awaiting review"
            description="Everything routed automatically — leads land here only when classification confidence is low."
          />
        </Card>
      ) : (
        <>
          <Card className="hidden overflow-x-auto sm:block">
            <table className="w-full min-w-140 text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Lead</th>
                  <th className="px-4 py-3 font-medium">Draft classification</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Queued</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.run_id}
                    className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3.5">
                      <Link
                        to={`/reviews/${item.run_id}`}
                        className="font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-1"
                      >
                        {item.lead_id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-4 py-3.5 text-slate-600">{item.draft_intent_label ?? '—'}</td>
                    <td className="px-4 py-3.5 text-slate-600">
                      {item.confidence_score != null ? item.confidence_score.toFixed(2) : '—'}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600">{new Date(item.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card className="flex flex-col divide-y divide-slate-100 sm:hidden">
            {items.map((item) => (
              <Link
                key={item.run_id}
                to={`/reviews/${item.run_id}`}
                className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
              >
                <div className="min-w-0">
                  <div className="font-medium text-teal-700">{item.lead_id.slice(0, 8)}</div>
                  <div className="truncate text-xs text-slate-500">{item.draft_intent_label ?? '—'}</div>
                </div>
                <span className="shrink-0 text-xs text-slate-500">
                  {item.confidence_score != null ? item.confidence_score.toFixed(2) : '—'}
                </span>
              </Link>
            ))}
          </Card>
        </>
      )}

      {recentlyResolved && recentlyResolved.length > 0 && (
        <div className="flex flex-1 min-h-0 flex-col gap-2">
          <SectionLabel>Recently processed</SectionLabel>
          <Card className="flex flex-1 min-h-0 flex-col divide-y divide-slate-100 overflow-y-auto">
            {recentlyResolved.map((lead) => (
              <Link
                key={lead.lead_id}
                to={`/leads/${lead.lead_id}`}
                className="flex shrink-0 items-center justify-between gap-3 px-4 py-3 text-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="font-medium text-teal-700">{lead.lead_id.slice(0, 8)}</span>
                  <span
                    className={`inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[lead.status] ?? 'bg-slate-100 text-slate-700'}`}
                  >
                    {lead.status.replace('_', ' ')}
                  </span>
                </div>
                <span className="shrink-0 text-xs text-slate-500">{new Date(lead.created_at).toLocaleDateString()}</span>
              </Link>
            ))}
          </Card>
        </div>
      )}
    </div>
  )
}
