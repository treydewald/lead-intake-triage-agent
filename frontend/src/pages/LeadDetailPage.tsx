import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Clock3, History } from 'lucide-react'
import { getLeadDetail, getLeadHistory, type LeadDetail, type TimelineEntry } from '../lib/api'
import { STAGE_ORDER } from '../lib/stageOrder'
import { Card } from '../components/ui/Card'
import { ErrorState, LoadingState } from '../components/ui/States'
import { TimelineRow } from '../components/ui/TimelineRow'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'

const STAGE_STATUS_CLASSES: Record<string, string> = {
  COMPLETED: 'border-emerald-300 bg-emerald-50',
  FAILED: 'border-red-300 bg-red-50',
  NOT_YET_RUN: 'border-slate-200 bg-slate-50',
}

const STAGE_STATUS_LABELS: Record<string, string> = {
  COMPLETED: 'Completed',
  FAILED: 'Failed',
  NOT_YET_RUN: 'Not yet run',
}

const STATUS_BADGE_CLASSES: Record<string, string> = {
  auto_processed: 'bg-emerald-100 text-emerald-800',
  awaiting_review: 'bg-amber-100 text-amber-800',
  rejected: 'bg-slate-200 text-slate-700',
  failed: 'bg-red-100 text-red-800',
  in_progress: 'bg-sky-100 text-sky-800',
}

export function LeadDetailPage() {
  const { leadId } = useParams<{ leadId: string }>()
  const [lead, setLead] = useState<LeadDetail | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [recentActivity, setRecentActivity] = useState<TimelineEntry[] | null>(null)
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
    getLeadDetail(leadId)
      .then((data) => {
        if (!cancelled) setLead(data)
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 404) {
          setNotFound(true)
        } else {
          setError('Failed to load lead detail.')
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
    getLeadHistory(leadId)
      .then((data) => {
        if (!cancelled) setRecentActivity(data.entries)
      })
      .catch(() => {
        if (!cancelled) setRecentActivity(null)
      })
    return () => {
      cancelled = true
    }
  }, [leadId])

  if (loading) {
    return <LoadingState label="Loading lead detail…" />
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

  if (error || !lead) {
    return <ErrorState message={error ?? 'Something went wrong.'} />
  }

  const stagesByKey = new Map(lead.stages.map((s) => [s.stage_key, s]))
  const badgeClass = STATUS_BADGE_CLASSES[lead.status] ?? 'bg-slate-100 text-slate-700'

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 sm:gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            to="/leads"
            className="inline-flex items-center gap-1 text-sm font-medium text-teal-700 hover:underline"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Back to leads
          </Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
            Lead {lead.lead_id.slice(0, 8)}
          </h1>
        </div>
        <span className={`inline-flex w-fit rounded-full px-3 py-1 text-sm font-medium ${badgeClass}`}>
          {lead.status.replace('_', ' ')}
        </span>
      </div>

      {lead.status === 'failed' && lead.failed_stage && (
        <div className="flex items-start gap-2 rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">
              Pipeline failed at {STAGE_ORDER.find((s) => s.key === lead.failed_stage)?.label ?? lead.failed_stage}
            </p>
            {lead.error && <p className="mt-1 text-red-700">{lead.error}</p>}
          </div>
        </div>
      )}

      {lead.status === 'in_progress' && (
        <div className="rounded-xl border border-sky-300 bg-sky-50 p-3 text-sm text-sky-800">
          This lead is still mid-pipeline — later stages have not run yet.
        </div>
      )}

      <div className="grid flex-1 min-h-0 grid-cols-1 gap-4 sm:gap-5 lg:grid-cols-3">
        <div className="flex min-h-0 flex-col gap-2.5 overflow-y-auto sm:gap-3 lg:col-span-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pipeline stages</h2>
          {STAGE_ORDER.map(({ key, label }) => {
            const stage = stagesByKey.get(key)
            const status = stage?.status ?? 'NOT_YET_RUN'
            return (
              <div
                key={key}
                className={`rounded-xl border p-3.5 shadow-sm transition-shadow sm:p-4 ${stage?.decision ? 'hover:shadow-md' : ''} ${STAGE_STATUS_CLASSES[status]}`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-slate-900">{label}</h3>
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-600">
                    {STAGE_STATUS_LABELS[status]}
                  </span>
                </div>
                {stage?.error && <p className="mt-1.5 text-sm text-red-700">{stage.error}</p>}
                {stage?.decision && (
                  <details className="mt-1.5">
                    <summary className="cursor-pointer text-xs font-medium text-slate-500 hover:text-slate-700">
                      View stage output
                    </summary>
                    <pre className="mt-1.5 overflow-x-auto rounded-lg bg-white/70 p-2 text-xs text-slate-700">
                      {JSON.stringify(stage.decision, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )
          })}
        </div>

        <div className="flex min-h-0 flex-col gap-3 sm:gap-4">
          <Card className="flex flex-col gap-3.5 p-5 sm:gap-4 sm:p-6">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Lead summary</h2>
            <dl className="grid grid-cols-2 gap-4 text-sm sm:gap-5">
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
              <div className="col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Updated</dt>
                <dd className="mt-0.5 font-medium text-slate-900">{new Date(lead.updated_at).toLocaleString()}</dd>
              </div>
            </dl>
          </Card>

          <Card className="flex flex-1 min-h-0 flex-col gap-3 overflow-y-auto p-5 sm:gap-3.5 sm:p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                Recent activity
              </div>
            </div>
            {recentActivity && recentActivity.length > 0 ? (
              <div className="flex flex-col gap-2.5">
                {recentActivity
                  .slice(-4)
                  .reverse()
                  .map((entry, index) => (
                    <TimelineRow key={`${entry.run_id}-${entry.kind}-${index}`} entry={entry} />
                  ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No activity recorded yet.</p>
            )}
            <Link
              to={`/leads/${lead.lead_id}/history`}
              className="mt-1 inline-flex w-fit items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-all hover:border-teal-300 hover:text-teal-700 hover:shadow-md active:scale-[0.98]"
            >
              View full history
            </Link>
          </Card>
        </div>
      </div>
    </div>
  )
}
