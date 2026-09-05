import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardCheck, Gauge, History } from 'lucide-react'
import { listReviews, type ReviewQueueItem } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card } from '../components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'

export function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
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
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Review Queue"
        description="Leads paused for a human decision before they reach CRM."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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

      <Card className="overflow-x-auto">
        {loading ? (
          <LoadingState label="Loading review queue…" />
        ) : items.length === 0 ? (
          <EmptyState
            icon={ClipboardCheck}
            title="No leads awaiting review"
            description="Everything routed automatically — leads land here only when classification confidence is low."
          />
        ) : (
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-medium">Lead</th>
                <th className="px-4 py-2.5 font-medium">Draft classification</th>
                <th className="px-4 py-2.5 font-medium">Confidence</th>
                <th className="px-4 py-2.5 font-medium">Queued</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.run_id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-2.5">
                    <Link
                      to={`/reviews/${item.run_id}`}
                      className="font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-1"
                    >
                      {item.lead_id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{item.draft_intent_label ?? '—'}</td>
                  <td className="px-4 py-2.5 text-slate-600">
                    {item.confidence_score != null ? item.confidence_score.toFixed(2) : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
