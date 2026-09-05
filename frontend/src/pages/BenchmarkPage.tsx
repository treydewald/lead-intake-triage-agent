import { useEffect, useState } from 'react'
import { Cpu, Gauge, Repeat, Sparkles } from 'lucide-react'
import { getBenchmarkRun, listBenchmarkRuns, runBenchmark, type BenchmarkCase, type BenchmarkRun } from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card, SectionLabel } from '../components/ui/Card'
import { EmptyState, ErrorState } from '../components/ui/States'

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function CaseStatusBadge({ item }: { item: BenchmarkCase }) {
  if (item.is_ambiguous) {
    return <span className="inline-flex rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-700">Ambiguous</span>
  }
  if (item.correct) {
    return <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">Correct</span>
  }
  return <span className="inline-flex rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">Misclassified</span>
}

export function BenchmarkPage() {
  const [latestRun, setLatestRun] = useState<BenchmarkRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listBenchmarkRuns()
      .then((runs) => {
        if (cancelled || runs.length === 0) return
        return getBenchmarkRun(runs[0].id).then((run) => {
          if (!cancelled) setLatestRun(run)
        })
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load benchmark runs.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleRunBenchmark = () => {
    setRunning(true)
    setError(null)
    runBenchmark()
      .then((run) => setLatestRun(run))
      .catch(() => setError('Benchmark run failed.'))
      .finally(() => setRunning(false))
  }

  const misclassifiedAndAmbiguous = latestRun?.cases.filter((c) => c.is_ambiguous || !c.correct) ?? []

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Classification Accuracy Benchmark"
        description="Accuracy and consistency measured against a fixed set of known cases."
        actions={
          <button
            type="button"
            onClick={handleRunBenchmark}
            disabled={running}
            className="inline-flex w-fit items-center gap-1.5 rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-800 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {running ? 'Running…' : 'Run Benchmark'}
          </button>
        }
      />

      {error && <ErrorState message={error} />}

      {!loading && !latestRun && !running && (
        <EmptyState
          icon={Gauge}
          title="No benchmark runs yet"
          description='Click "Run Benchmark" to measure classification accuracy against the known-case dataset.'
        />
      )}

      {latestRun && (
        <>
          <div className="grid grid-cols-3 gap-2 sm:gap-4">
            <StatCard label="Accuracy" value={formatPercent(latestRun.accuracy)} icon={Gauge} tone="emerald" />
            <StatCard label="Consistency" value={formatPercent(latestRun.consistency)} icon={Repeat} />
            <StatCard
              label="Model"
              value={latestRun.model_used}
              hint={`${latestRun.total_cases} cases · ${latestRun.repeats} repeats`}
              icon={Cpu}
            />
          </div>

          <SectionLabel>Failure &amp; Ambiguous Cases</SectionLabel>
          <Card className="overflow-x-auto">
            {misclassifiedAndAmbiguous.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                title="No failures or ambiguous cases in this run"
                description="Every known case was classified correctly and consistently."
              />
            ) : (
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Case</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                    <th className="px-4 py-2.5 font-medium">Expected</th>
                    <th className="px-4 py-2.5 font-medium">Predicted</th>
                    <th className="px-4 py-2.5 font-medium">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {misclassifiedAndAmbiguous.map((item) => (
                    <tr key={item.case_id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-800">{item.case_id}</td>
                      <td className="px-4 py-2.5">
                        <CaseStatusBadge item={item} />
                      </td>
                      <td className="px-4 py-2.5 text-slate-600">{item.expected_label ?? '—'}</td>
                      <td className="px-4 py-2.5 text-slate-600">{item.predicted_label ?? '—'}</td>
                      <td className="px-4 py-2.5 text-slate-600">
                        {item.confidence != null ? item.confidence.toFixed(2) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
