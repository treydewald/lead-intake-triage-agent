import { Link } from 'react-router-dom'

const sections = [
  {
    to: '/leads',
    label: 'Observability',
    description: 'Browse triaged leads, pipeline runs, and per-stage traces.',
  },
  {
    to: '/reviews',
    label: 'Review Queue',
    description: 'Approve or reject leads flagged for human review.',
  },
  {
    to: '/benchmark',
    label: 'Benchmark',
    description: 'Measure classification accuracy and consistency against known cases.',
  },
]

export function HomePage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Lead Intake Triage</h1>
        <p className="mt-1 text-sm text-slate-500">
          Automated lead classification, routing, and review — pick a view to get started.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {sections.map((section) => (
          <Link
            key={section.to}
            to={section.to}
            className="rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-teal-700 hover:bg-teal-50"
          >
            <div className="font-medium text-slate-900">{section.label}</div>
            <div className="mt-1 text-sm text-slate-500">{section.description}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
