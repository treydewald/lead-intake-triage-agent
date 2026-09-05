import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getLeadDetail, type LeadDetail } from '../lib/api'
import { STAGE_ORDER } from '../lib/stageOrder'

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

export function LeadDetailPage() {
  const { leadId } = useParams<{ leadId: string }>()
  const [lead, setLead] = useState<LeadDetail | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!leadId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setNotFound(false)
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

  if (error || !lead) {
    return <p className="text-red-600">{error ?? 'Something went wrong.'}</p>
  }

  const stagesByKey = new Map(lead.stages.map((s) => [s.stage_key, s]))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/leads" className="text-sm text-teal-700 hover:underline">
            ← Back to leads
          </Link>
          <h1 className="mt-1 text-xl font-semibold">Lead {lead.lead_id.slice(0, 8)}</h1>
        </div>
        <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
          {lead.status.replace('_', ' ')}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-white p-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-slate-400">Source</dt>
          <dd>{lead.source_channel ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Confidence</dt>
          <dd>{lead.confidence_score != null ? lead.confidence_score.toFixed(2) : '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Created</dt>
          <dd>{new Date(lead.created_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Updated</dt>
          <dd>{new Date(lead.updated_at).toLocaleString()}</dd>
        </div>
      </dl>

      {lead.status === 'failed' && lead.failed_stage && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">
          <p className="font-medium">
            Pipeline failed at {STAGE_ORDER.find((s) => s.key === lead.failed_stage)?.label ?? lead.failed_stage}
          </p>
          {lead.error && <p className="mt-1 text-red-700">{lead.error}</p>}
        </div>
      )}

      {lead.status === 'in_progress' && (
        <div className="rounded-lg border border-sky-300 bg-sky-50 p-4 text-sm text-sky-800">
          This lead is still mid-pipeline — later stages have not run yet.
        </div>
      )}

      <div className="flex flex-col gap-3">
        {STAGE_ORDER.map(({ key, label }) => {
          const stage = stagesByKey.get(key)
          const status = stage?.status ?? 'NOT_YET_RUN'
          return (
            <div key={key} className={`rounded-lg border p-4 ${STAGE_STATUS_CLASSES[status]}`}>
              <div className="flex items-center justify-between">
                <h2 className="font-medium">{label}</h2>
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {STAGE_STATUS_LABELS[status]}
                </span>
              </div>
              {stage?.error && <p className="mt-2 text-sm text-red-700">{stage.error}</p>}
              {stage?.decision && (
                <pre className="mt-2 overflow-x-auto rounded bg-white/70 p-2 text-xs text-slate-700">
                  {JSON.stringify(stage.decision, null, 2)}
                </pre>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
