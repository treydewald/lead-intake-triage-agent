import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, ArrowRight, ClipboardCheck, Gauge } from 'lucide-react'
import { listBenchmarkRuns, listLeads, listReviews } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'

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

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Lead Intake Triage Agent"
        title="Automated classification, routing, and review"
        description="A multi-stage pipeline that triages inbound leads with a local LLM, writes qualified leads to CRM, and routes ambiguous ones to a human. Pick a view below to get started."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {sections.map((section) => (
          <Link
            key={section.to}
            to={section.to}
            className="group flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              <section.icon className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-slate-900">
                {section.label}
                <ArrowRight
                  className="h-3.5 w-3.5 text-teal-700 opacity-0 transition-opacity group-hover:opacity-100"
                  aria-hidden="true"
                />
              </div>
              <div className="mt-1 text-sm text-slate-500">{section.description}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
