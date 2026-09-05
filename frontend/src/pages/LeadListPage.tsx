import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Activity, CheckCircle2, ClipboardCheck, Inbox } from 'lucide-react'
import { listLeads, type LeadListItem, type ListLeadsParams } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card } from '../components/ui/Card'
import { Select } from '../components/ui/Select'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'

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
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState<LeadListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [counts, setCounts] = useState<{ awaitingReview: number | null; autoProcessed: number | null }>({
    awaitingReview: null,
    autoProcessed: null,
  })

  const status = searchParams.get('status') ?? ''
  const sourceChannel = searchParams.get('channel') ?? ''
  const sort = (searchParams.get('sort') as ListLeadsParams['sort']) || 'created_desc'
  const page = Number(searchParams.get('page') ?? '1') || 1

  const updateParams = (updates: Record<string, string | undefined>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      for (const [key, value] of Object.entries(updates)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      return next
    })
  }

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

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      listLeads({ status: 'awaiting_review', page_size: 1 }),
      listLeads({ status: 'auto_processed', page_size: 1 }),
    ]).then(([awaiting, auto]) => {
      if (cancelled) return
      setCounts({
        awaitingReview: awaiting.status === 'fulfilled' ? awaiting.value.total : null,
        autoProcessed: auto.status === 'fulfilled' ? auto.value.total : null,
      })
    })
    return () => {
      cancelled = true
    }
  }, [])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <PageHeader title="Leads" description="Every lead that has entered the intake pipeline." />

      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        <StatCard label="Total leads" value={String(total)} icon={Activity} />
        <StatCard
          label="Awaiting review"
          value={counts.awaitingReview != null ? String(counts.awaitingReview) : '—'}
          icon={ClipboardCheck}
          tone={counts.awaitingReview ? 'amber' : 'neutral'}
        />
        <StatCard
          label="Auto-processed"
          value={counts.autoProcessed != null ? String(counts.autoProcessed) : '—'}
          icon={CheckCircle2}
          tone="emerald"
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Select
          label="Filter by status"
          value={status}
          onChange={(e) => updateParams({ status: e.target.value || undefined, page: undefined })}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>

        <Select
          label="Filter by channel"
          value={sourceChannel}
          onChange={(e) => updateParams({ channel: e.target.value || undefined, page: undefined })}
        >
          {SOURCE_CHANNEL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>

        <Select label="Sort by" value={sort} onChange={(e) => updateParams({ sort: e.target.value })}>
          <option value="created_desc">Newest first</option>
          <option value="confidence_desc">Confidence: high to low</option>
          <option value="confidence_asc">Confidence: low to high</option>
        </Select>
      </div>

      {error && <ErrorState message={error} />}

      <div className="flex min-w-0 flex-1 min-h-0 flex-col">
        {loading ? (
          <Card>
            <LoadingState label="Loading leads…" />
          </Card>
        ) : items.length === 0 ? (
          <Card>
            <EmptyState
              icon={Inbox}
              title="No leads found"
              description="Try adjusting the status or channel filters, or check back once new leads arrive."
            />
          </Card>
        ) : (
          <>
            <Card className="hidden min-w-0 flex-1 min-h-0 flex-col overflow-auto sm:flex">
              <table className="w-full min-w-160 text-left text-sm">
                <thead className="sticky top-0 border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Lead</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Source</th>
                    <th className="px-4 py-3 font-medium">Confidence</th>
                    <th className="px-4 py-3 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.lead_id}
                      className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50"
                    >
                      <td className="px-4 py-3.5">
                        <Link
                          to={`/leads/${item.lead_id}`}
                          className="font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-1"
                        >
                          {item.lead_id.slice(0, 8)}
                        </Link>
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-3.5 text-slate-600">{item.source_channel ?? '—'}</td>
                      <td className="px-4 py-3.5">
                        <ConfidenceMeter value={item.confidence_score} />
                      </td>
                      <td className="px-4 py-3.5 text-slate-600">{new Date(item.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <Card className="flex flex-col divide-y divide-slate-100 sm:hidden">
              {items.map((item) => (
                <Link
                  key={item.lead_id}
                  to={`/leads/${item.lead_id}`}
                  className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span className="font-medium text-teal-700">{item.lead_id.slice(0, 8)}</span>
                    <StatusBadge status={item.status} />
                  </div>
                  <ConfidenceMeter value={item.confidence_score} showValue={false} />
                </Link>
              ))}
            </Card>
          </>
        )}
      </div>

      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>
          Page {page} of {totalPages} ({total} total)
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 shadow-sm transition-all hover:bg-slate-50 hover:shadow-md active:scale-[0.98] disabled:opacity-40 disabled:active:scale-100"
            disabled={page <= 1}
            onClick={() => {
              const next = Math.max(1, page - 1)
              updateParams({ page: next === 1 ? undefined : String(next) })
            }}
          >
            Previous
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 shadow-sm transition-all hover:bg-slate-50 hover:shadow-md active:scale-[0.98] disabled:opacity-40 disabled:active:scale-100"
            disabled={page >= totalPages}
            onClick={() => {
              const next = Math.min(totalPages, page + 1)
              updateParams({ page: next === 1 ? undefined : String(next) })
            }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
