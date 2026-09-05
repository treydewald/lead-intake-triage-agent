import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getLeadHistory, type LeadHistory, type TimelineEntry } from '../lib/api'

const REVIEW_ACTION_LABELS: Record<string, string> = {
  approve: 'Approved',
  reject: 'Rejected',
  edit: 'Edited',
}

function TimelineRow({ entry }: { entry: TimelineEntry }) {
  const isReviewAction = entry.kind === 'review_action'
  return (
    <div
      className={`rounded-lg border p-3 ${
        isReviewAction ? 'border-teal-300 bg-teal-50' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h2 className="font-medium">
          {isReviewAction
            ? (REVIEW_ACTION_LABELS[entry.reviewer_action ?? ''] ?? entry.reviewer_action)
            : entry.stage_label}
        </h2>
        <span className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString()}</span>
      </div>
      {!isReviewAction && (
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{entry.status}</span>
      )}
      {!isReviewAction && entry.error && <p className="mt-2 text-sm text-red-700">{entry.error}</p>}
      {isReviewAction && (
        <p className="mt-1 text-sm text-teal-800">
          by {entry.reviewer_name ?? 'Reviewer'}
          {entry.corrected_intent_label && <> — corrected to "{entry.corrected_intent_label}"</>}
        </p>
      )}
    </div>
  )
}

export function LeadHistoryPage() {
  const { leadId } = useParams<{ leadId: string }>()
  const [history, setHistory] = useState<LeadHistory | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!leadId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setNotFound(false)
    getLeadHistory(leadId)
      .then((data) => {
        if (!cancelled) setHistory(data)
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 404) {
          setNotFound(true)
        } else {
          setError('Failed to load lead history.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [leadId])

  if (loading) {
    return <p className="text-slate-500">Loading…</p>
  }

  if (notFound) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-slate-600">No lead found with id "{leadId}".</p>
        <Link to="/leads" className="w-fit text-teal-700 hover:underline">
          Back to leads
        </Link>
      </div>
    )
  }

  if (error || !history) {
    return <p className="text-red-600">{error ?? 'Something went wrong.'}</p>
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to={`/leads/${history.lead_id}`} className="text-sm text-teal-700 hover:underline">
          ← Back to lead detail
        </Link>
        <h1 className="mt-1 text-xl font-semibold">Full history — {history.lead_id.slice(0, 8)}</h1>
      </div>

      {history.entries.length === 0 ? (
        <p className="text-slate-500">No history recorded for this lead yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {history.entries.map((entry, index) => (
            <TimelineRow key={`${entry.run_id}-${entry.kind}-${index}`} entry={entry} />
          ))}
        </div>
      )}
    </div>
  )
}
