import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { actionReview, getReview, type ReviewAction, type ReviewActionResult, type ReviewQueueItem } from '../lib/api'

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
    return <p className="text-slate-500">Loading…</p>
  }

  if (notFound) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-slate-600">No review item found for run "{runId}".</p>
        <Link to="/reviews" className="w-fit text-teal-700 hover:underline">
          Back to review queue
        </Link>
      </div>
    )
  }

  if (error || !item) {
    return <p className="text-red-600">{error ?? 'Something went wrong.'}</p>
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/reviews" className="text-sm text-teal-700 hover:underline">
          ← Back to review queue
        </Link>
        <h1 className="mt-1 text-xl font-semibold">Review lead {item.lead_id.slice(0, 8)}</h1>
      </div>

      <dl className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-white p-4 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-400">Draft classification</dt>
          <dd>{item.draft_intent_label ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Confidence</dt>
          <dd>{item.confidence_score != null ? item.confidence_score.toFixed(2) : '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Queued</dt>
          <dd>{new Date(item.created_at).toLocaleString()}</dd>
        </div>
      </dl>

      {alreadyActioned && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          This item has already been actioned by someone else — no further action can be taken here.
        </div>
      )}

      {result && !alreadyActioned && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">
          Action submitted. Run status is now <span className="font-medium">{result.status}</span>.
        </div>
      )}

      {!result && !alreadyActioned && (
        <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap gap-3">
            {(['approve', 'reject', 'edit'] as ReviewAction[]).map((action) => (
              <label key={action} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="review-action"
                  value={action}
                  checked={selectedAction === action}
                  onChange={() => setSelectedAction(action)}
                />
                {action[0].toUpperCase() + action.slice(1)}
              </label>
            ))}
          </div>

          {selectedAction === 'edit' && (
            <input
              type="text"
              placeholder="Corrected classification"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              value={correctedLabel}
              onChange={(e) => setCorrectedLabel(e.target.value)}
            />
          )}

          <input
            type="text"
            placeholder="Your name (optional)"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
          />

          {validationError && <p className="text-sm text-red-600">{validationError}</p>}
          {submitError && <p className="text-sm text-red-600">{submitError}</p>}

          <button
            type="button"
            className="w-fit rounded-md bg-teal-700 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            disabled={submitting}
            onClick={handleSubmit}
          >
            {submitting ? 'Submitting…' : 'Submit'}
          </button>
        </div>
      )}
    </div>
  )
}
