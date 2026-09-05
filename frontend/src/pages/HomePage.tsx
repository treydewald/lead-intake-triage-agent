import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, ArrowRight, ClipboardCheck, Gauge, History } from 'lucide-react'
import { listBenchmarkRuns, listLeads, listReviews, type LeadListItem } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card, SectionLabel } from '../components/ui/Card'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'

const STATUS_BADGE_CLASSES: Record<string, string> = {
  auto_processed: 'bg-emerald-100 text-emerald-800',
  awaiting_review: 'bg-amber-100 text-amber-800',
  rejected: 'bg-slate-200 text-slate-700',
  failed: 'bg-red-100 text-red-800',
  in_progress: 'bg-sky-100 text-sky-800',
}

const sections = [
  {
    to: '/leads',
    label: 'Observability',
    description: 'Browse triaged leads, pipeline runs, and per-stage traces.',
    icon: Activity,
  },
  {
    to: '/reviews',
    label: 'Review Queue',
    description: 'Approve or reject leads flagged for human review.',
    icon: ClipboardCheck,
  },
  {
    to: '/benchmark',
    label: 'Benchmark',
    description: 'Measure classification accuracy and consistency against known cases.',
    icon: Gauge,
  },
]

interface Snapshot {
  totalLeads: number | null
  pendingReviews: number | null
  latestAccuracy: number | null
}

export function HomePage() {
  const [snapshot, setSnapshot] = useState<Snapshot>({
    totalLeads: null,
    pendingReviews: null,
    latestAccuracy: null,
  })
  const [recentLeads, setRecentLeads] = useState<LeadListItem[] | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([listLeads({ page_size: 1 }), listReviews(), listBenchmarkRuns()]).then(
      ([leadsResult, reviewsResult, benchmarkResult]) => {
        if (cancelled) return
        setSnapshot({
          totalLeads: leadsResult.status === 'fulfilled' ? leadsResult.value.total : null,
          pendingReviews: reviewsResult.status === 'fulfilled' ? reviewsResult.value.length : null,
          latestAccuracy:
            benchmarkResult.status === 'fulfilled' && benchmarkResult.value.length > 0
              ? benchmarkResult.value[0].accuracy
              : null,
        })
      },
    )
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    listLeads({ sort: 'created_desc', page_size: 10 })
      .then((data) => {
        if (!cancelled) setRecentLeads(data.items)
      })
      .catch(() => {
        if (!cancelled) setRecentLeads([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 sm:gap-6">
      <PageHeader
        eyebrow="Lead Intake Triage Agent"
        title="Automated classification, routing, and review"
        description="A multi-stage pipeline that triages inbound leads with a local LLM, writes qualified leads to CRM, and routes ambiguous ones to a human. Pick a view below to get started."
      />

      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        <StatCard
          label="Total leads"
          value={snapshot.totalLeads != null ? snapshot.totalLeads.toLocaleString() : '—'}
          icon={Activity}
        />
        <StatCard
          label="Awaiting review"
          value={snapshot.pendingReviews != null ? String(snapshot.pendingReviews) : '—'}
          icon={ClipboardCheck}
          tone={snapshot.pendingReviews ? 'amber' : 'neutral'}
        />
        <StatCard
          label="Latest benchmark accuracy"
          value={snapshot.latestAccuracy != null ? `${(snapshot.latestAccuracy * 100).toFixed(1)}%` : '—'}
          icon={Gauge}
          tone="emerald"
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
        {sections.map((section) => (
          <Link
            key={section.to}
            to={section.to}
            className="group flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 sm:flex-col sm:items-stretch sm:gap-3 sm:p-5"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              <section.icon className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 font-semibold text-slate-900">
                {section.label}
                <ArrowRight
                  className="h-3.5 w-3.5 text-teal-700 opacity-0 transition-opacity group-hover:opacity-100"
                  aria-hidden="true"
                />
              </div>
              <div className="mt-1 hidden text-sm text-slate-500 sm:block">{section.description}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="flex flex-1 min-h-0 flex-col gap-2">
        <SectionLabel>Recent leads</SectionLabel>
        <Card className="flex flex-1 min-h-0 flex-col divide-y divide-slate-100 overflow-y-auto">
          {recentLeads === null ? (
            <p className="p-4 text-sm text-slate-500">Loading…</p>
          ) : recentLeads.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No leads have entered the pipeline yet.</p>
          ) : (
            recentLeads.map((lead) => (
              <Link
                key={lead.lead_id}
                to={`/leads/${lead.lead_id}`}
                className="flex shrink-0 items-center justify-between gap-3 px-4 py-3 text-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="font-medium text-teal-700">{lead.lead_id.slice(0, 8)}</span>
                  <span
                    className={`inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[lead.status] ?? 'bg-slate-100 text-slate-700'}`}
                  >
                    {lead.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <ConfidenceMeter value={lead.confidence_score} showValue={false} className="hidden sm:flex" />
                  <span className="text-xs text-slate-500">{new Date(lead.created_at).toLocaleDateString()}</span>
                </div>
              </Link>
            ))
          )}
        </Card>
        {recentLeads && recentLeads.length > 0 && (
          <Link
            to="/leads"
            className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-teal-700 hover:underline"
          >
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            View all leads
          </Link>
        )}
      </div>
    </div>
  )
}
