import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Clock3, ListTree } from 'lucide-react'
import { getLeadDetail, getLeadHistory, type LeadDetail, type LeadHistory } from '../lib/api'
import { Card, SectionLabel } from '../components/ui/Card'
import { ErrorState, LoadingState } from '../components/ui/States'
import { TimelineRow } from '../components/ui/TimelineRow'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'

const STATUS_BADGE_CLASSES: Record<string, string> = {
  auto_processed: 'bg-emerald-100 text-emerald-800',
  awaiting_review: 'bg-amber-100 text-amber-800',
  rejected: 'bg-slate-200 text-slate-700',
  failed: 'bg-red-100 text-red-800',
  in_progress: 'bg-sky-100 text-sky-800',
}

export function LeadHistoryPage() {
  const { leadId } = useParams<{ leadId: string }>()
  const [history, setHistory] = useState<LeadHistory | null>(null)
  const [lead, setLead] = useState<LeadDetail | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [prevLeadId, setPrevLeadId] = useState(leadId)

  if (leadId !== prevLeadId) {
    setPrevLeadId(leadId)
    setLoading(true)
    setError(null)
    setNotFound(false)
  }

  useEffect(() => {
    if (!leadId) return
    let cancelled = false
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

  useEffect(() => {
    if (!leadId) return
    let cancelled = false
    getLeadDetail(leadId)
      .then((data) => {
        if (!cancelled) setLead(data)
      })
      .catch(() => {
        if (!cancelled) setLead(null)
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
    <div className="flex h-full min-h-0 flex-col gap-5 sm:gap-6">
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

      <div className="grid flex-1 min-h-0 grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="flex min-h-0 flex-col gap-2 lg:col-span-2">
          <SectionLabel>Timeline</SectionLabel>
          <Card className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
            {history.entries.length === 0 ? (
              <p className="text-slate-500">No history recorded for this lead yet.</p>
            ) : (
              history.entries.map((entry, index) => (
                <TimelineRow key={`${entry.run_id}-${entry.kind}-${index}`} entry={entry} />
              ))
            )}
          </Card>
        </div>

        {lead && (
          <Card className="flex flex-col gap-4 p-6">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Lead summary</h2>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div className="col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</dt>
                <dd className="mt-1">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[lead.status] ?? 'bg-slate-100 text-slate-700'}`}
                  >
                    {lead.status.replace('_', ' ')}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Source</dt>
                <dd className="mt-0.5 font-medium text-slate-900">{lead.source_channel ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Confidence</dt>
                <dd className="mt-1">
                  <ConfidenceMeter value={lead.confidence_score} />
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                  <Clock3 className="h-3 w-3" aria-hidden="true" />
                  Created
                </dt>
                <dd className="mt-0.5 font-medium text-slate-900">{new Date(lead.created_at).toLocaleString()}</dd>
              </div>
            </dl>
            <Link
              to={`/leads/${lead.lead_id}`}
              className="inline-flex w-fit items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-all hover:border-teal-300 hover:text-teal-700 hover:shadow-md active:scale-[0.98]"
            >
              View lead detail
            </Link>
          </Card>
        )}
      </div>
    </div>
  )
}
