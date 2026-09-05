import type { TimelineEntry } from '../../lib/api'

const REVIEW_ACTION_LABELS: Record<string, string> = {
  approve: 'Approved',
  reject: 'Rejected',
  edit: 'Edited',
}

export function TimelineRow({ entry }: { entry: TimelineEntry }) {
  const isReviewAction = entry.kind === 'review_action'
  return (
    <div
      className={`rounded-xl border p-4 shadow-sm transition-shadow hover:shadow-md ${
        isReviewAction ? 'border-teal-300 bg-teal-50' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 className="font-medium">
          {isReviewAction
            ? (REVIEW_ACTION_LABELS[entry.reviewer_action ?? ''] ?? entry.reviewer_action)
            : entry.stage_label}
        </h3>
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
