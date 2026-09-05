import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listReviews, type ReviewQueueItem } from '../lib/api'

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

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Review Queue</h1>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
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
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  No leads awaiting review.
                </td>
              </tr>
            )}
            {items.map((item) => (
              <tr key={item.run_id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2.5">
                  <Link to={`/reviews/${item.run_id}`} className="font-medium text-teal-700 hover:underline">
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
      </div>
    </div>
  )
}
