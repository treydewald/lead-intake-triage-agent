import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, CheckCircle2, MessageSquare } from 'lucide-react'
import { actionReview, getReview, type ReviewAction, type ReviewActionResult, type ReviewQueueItem } from '../lib/api'
import { Card } from '../components/ui/Card'
import { ErrorState, LoadingState } from '../components/ui/States'

export function ReviewDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const [item, setItem] = useState<ReviewQueueItem | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [selectedAction, setSelectedAction] = useState<ReviewAction>('approve')
  const [correctedLabel, setCorrectedLabel] = useState('')
  const [reviewerName, setReviewerName] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [alreadyActioned, setAlreadyActioned] = useState(false)
  const [result, setResult] = useState<ReviewActionResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setNotFound(false)
    getReview(runId)
      .then((data) => {
        if (!cancelled) setItem(data)
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 404) {
          setNotFound(true)
        } else {
          setError('Failed to load this review item.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [runId])

  async function handleSubmit() {
    if (!runId) return
    setValidationError(null)
    setSubmitError(null)

    if (selectedAction === 'edit' && !correctedLabel.trim()) {
      setValidationError('Enter a corrected classification before submitting an edit.')
      return
    }

    setSubmitting(true)
    try {
      const data = await actionReview(runId, {
        action: selectedAction,
        corrected_intent_label: selectedAction === 'edit' ? correctedLabel.trim() : undefined,
        reviewer_name: reviewerName.trim() || undefined,
      })
      setResult(data)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        setAlreadyActioned(true)
      } else {
        setSubmitError('Failed to submit this review action.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <LoadingState label="Loading review item…" />
  }

  if (notFound) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-slate-600">No review item found for run "{runId}".</p>
        <Link to="/reviews" className="w-fit text-sm font-medium text-teal-700 hover:underline">
          Back to review queue
        </Link>
      </div>
    )
  }

  if (error || !item) {
    return <ErrorState message={error ?? 'Something went wrong.'} />
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <Link
          to="/reviews"
          className="inline-flex items-center gap-1 text-sm font-medium text-teal-700 hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Back to review queue
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Review lead</h1>
          <Link
            to={`/leads/${item.lead_id}`}
            className="inline-flex items-center gap-1 text-sm font-medium text-teal-700 hover:underline"
          >
            {item.lead_id.slice(0, 8)}
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {alreadyActioned && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          This item has already been actioned by someone else — no further action can be taken here.
        </div>
      )}

      {result && !alreadyActioned && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">
          <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
          Action submitted. Run status is now <span className="font-medium">{result.status}</span>.
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card className="p-5">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
              Lead message
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
              {item.message_body?.trim() ? item.message_body : 'This lead was submitted with no message content.'}
            </p>
          </Card>

          <Card className="p-5">
            <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Draft classification</dt>
                <dd className="mt-0.5 font-medium text-slate-900">{item.draft_intent_label ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Confidence</dt>
                <dd className="mt-0.5 font-medium text-slate-900">
                  {item.confidence_score != null ? item.confidence_score.toFixed(2) : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Queued</dt>
                <dd className="mt-0.5 font-medium text-slate-900">{new Date(item.created_at).toLocaleString()}</dd>
              </div>
            </dl>
          </Card>
        </div>

        {!result && !alreadyActioned && (
          <Card className="flex h-fit flex-col gap-3.5 p-5">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reviewer decision</h2>
            <div className="flex flex-wrap gap-3">
              {(['approve', 'reject', 'edit'] as ReviewAction[]).map((action) => (
                <label key={action} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="radio"
                    name="review-action"
                    value={action}
                    checked={selectedAction === action}
                    onChange={() => setSelectedAction(action)}
                    className="h-4 w-4 accent-teal-700"
                  />
                  {action[0].toUpperCase() + action.slice(1)}
                </label>
              ))}
            </div>

            {selectedAction === 'edit' && (
              <input
                type="text"
                placeholder="Corrected classification"
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm shadow-sm focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
                value={correctedLabel}
                onChange={(e) => setCorrectedLabel(e.target.value)}
              />
            )}

            <input
              type="text"
              placeholder="Your name (optional)"
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm shadow-sm focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
            />

            {validationError && <p className="text-sm text-red-600">{validationError}</p>}
            {submitError && <p className="text-sm text-red-600">{submitError}</p>}

            <button
              type="button"
              className="w-fit rounded-lg bg-teal-700 px-4 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-800 disabled:opacity-50"
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? 'Submitting…' : 'Submit'}
            </button>
          </Card>
        )}
      </div>
    </div>
  )
}
