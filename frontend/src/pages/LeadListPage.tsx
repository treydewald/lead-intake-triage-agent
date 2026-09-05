import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listLeads, type LeadListItem, type ListLeadsParams } from '../lib/api'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'auto_processed', label: 'Auto-processed' },
  { value: 'awaiting_review', label: 'Awaiting review' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'failed', label: 'Failed' },
  { value: 'in_progress', label: 'In progress' },
]

const SOURCE_CHANNEL_OPTIONS = [
  { value: '', label: 'All channels' },
  { value: 'web_form', label: 'Web form' },
  { value: 'email', label: 'Email' },
  { value: 'callback', label: 'Callback' },
]

const STATUS_BADGE_CLASSES: Record<string, string> = {
  auto_processed: 'bg-emerald-100 text-emerald-800',
  awaiting_review: 'bg-amber-100 text-amber-800',
  rejected: 'bg-slate-200 text-slate-700',
  failed: 'bg-red-100 text-red-800',
  in_progress: 'bg-sky-100 text-sky-800',
}

function StatusBadge({ status }: { status: string }) {
  const classes = STATUS_BADGE_CLASSES[status] ?? 'bg-slate-100 text-slate-700'
  const label = STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>{label}</span>
  )
}

const PAGE_SIZE = 10

export function LeadListPage() {
  const [items, setItems] = useState<LeadListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [sourceChannel, setSourceChannel] = useState('')
  const [sort, setSort] = useState<ListLeadsParams['sort']>('created_desc')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listLeads({
      status: status || undefined,
      source_channel: sourceChannel || undefined,
      sort,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        if (cancelled) return
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load leads.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [status, sourceChannel, sort, page])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Leads</h1>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <select
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm sm:w-auto"
          value={status}
          onChange={(e) => {
            setPage(1)
            setStatus(e.target.value)
          }}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm sm:w-auto"
          value={sourceChannel}
          onChange={(e) => {
            setPage(1)
            setSourceChannel(e.target.value)
          }}
        >
          {SOURCE_CHANNEL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm sm:w-auto"
          value={sort}
          onChange={(e) => setSort(e.target.value as ListLeadsParams['sort'])}
        >
          <option value="created_desc">Newest first</option>
          <option value="confidence_desc">Confidence: high to low</option>
          <option value="confidence_asc">Confidence: low to high</option>
        </select>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">Lead</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5 font-medium">Source</th>
              <th className="px-4 py-2.5 font-medium">Confidence</th>
              <th className="px-4 py-2.5 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                  No leads found.
                </td>
              </tr>
            )}
            {items.map((item) => (
              <tr key={item.lead_id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2.5">
                  <Link to={`/leads/${item.lead_id}`} className="font-medium text-teal-700 hover:underline">
                    {item.lead_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-2.5">
                  <StatusBadge status={item.status} />
                </td>
                <td className="px-4 py-2.5 text-slate-600">{item.source_channel ?? '—'}</td>
                <td className="px-4 py-2.5 text-slate-600">
                  {item.confidence_score != null ? item.confidence_score.toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2.5 text-slate-600">{new Date(item.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>
          Page {page} of {totalPages} ({total} total)
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
