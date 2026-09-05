import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ListTree } from 'lucide-react'
import { getLeadHistory, type LeadHistory } from '../lib/api'
import { ErrorState, LoadingState } from '../components/ui/States'
import { TimelineRow } from '../components/ui/TimelineRow'

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
    return <LoadingState label="Loading history…" />
  }

  if (notFound) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-slate-600">No lead found with id "{leadId}".</p>
        <Link to="/leads" className="w-fit text-sm font-medium text-teal-700 hover:underline">
          Back to leads
        </Link>
      </div>
    )
  }

  if (error || !history) {
    return <ErrorState message={error ?? 'Something went wrong.'} />
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          to={`/leads/${history.lead_id}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-teal-700 hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Back to lead detail
        </Link>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-slate-900">
          <ListTree className="h-5 w-5 text-teal-700" aria-hidden="true" />
          Full history — {history.lead_id.slice(0, 8)}
        </h1>
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
