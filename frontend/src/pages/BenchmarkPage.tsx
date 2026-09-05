import { useEffect, useState } from 'react'
import { Cpu, Gauge, Repeat, Sparkles } from 'lucide-react'
import {
  getBenchmarkRun,
  listBenchmarkRuns,
  runBenchmark,
  type BenchmarkCase,
  type BenchmarkRun,
  type BenchmarkRunSummary,
} from '../lib/api'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { Card, SectionLabel } from '../components/ui/Card'
import { EmptyState, ErrorState } from '../components/ui/States'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'
import { TrendChart } from '../components/ui/TrendChart'

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
  const [runs, setRuns] = useState<BenchmarkRunSummary[]>([])
  const [latestRun, setLatestRun] = useState<BenchmarkRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [switchingRunId, setSwitchingRunId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listBenchmarkRuns()
      .then((allRuns) => {
        if (cancelled) return
        setRuns(allRuns)
        if (allRuns.length === 0) return
        return getBenchmarkRun(allRuns[0].id).then((run) => {
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
      .then((run) => {
        setLatestRun(run)
        setRuns((prev) => [run, ...prev])
      })
      .catch(() => setError('Benchmark run failed.'))
      .finally(() => setRunning(false))
  }

  const handleSelectRun = (runId: string) => {
    if (runId === latestRun?.id) return
    setSwitchingRunId(runId)
    setError(null)
    getBenchmarkRun(runId)
      .then((run) => setLatestRun(run))
      .catch(() => setError('Failed to load that benchmark run.'))
      .finally(() => setSwitchingRunId(null))
  }

  const misclassifiedAndAmbiguous = latestRun?.cases.filter((c) => c.is_ambiguous || !c.correct) ?? []

  const trendPoints = [...runs]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((run, index) => ({
      label: `#${index + 1}`,
      dateLabel: new Date(run.created_at).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      }),
      accuracy: run.accuracy,
      consistency: run.consistency,
    }))

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <PageHeader
        title="Classification Accuracy Benchmark"
        description="Accuracy and consistency measured against a fixed set of known cases."
        actions={
          <button
            type="button"
            onClick={handleRunBenchmark}
            disabled={running}
            className="inline-flex w-fit items-center gap-1.5 rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-teal-800 hover:shadow-md active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100"
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
                    <tr
                      key={item.case_id}
                      className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50"
                    >
                      <td className="px-4 py-2.5 font-medium text-slate-800">{item.case_id}</td>
                      <td className="px-4 py-2.5">
                        <CaseStatusBadge item={item} />
                      </td>
                      <td className="px-4 py-2.5 text-slate-600">{item.expected_label ?? '—'}</td>
                      <td className="px-4 py-2.5 text-slate-600">{item.predicted_label ?? '—'}</td>
                      <td className="px-4 py-2.5">
                        <ConfidenceMeter value={item.confidence} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {runs.length > 0 && (
            <div className="flex min-w-0 flex-1 min-h-0 flex-col gap-2">
              <SectionLabel>Run History &amp; Trend</SectionLabel>
              <Card className="flex min-w-0 flex-1 min-h-0 flex-col overflow-hidden">
                <div className="p-4 pb-3">
                  <TrendChart points={trendPoints} />
                </div>
                <div className="min-w-0 flex-1 min-h-0 overflow-auto border-t border-slate-200">
                  <table aria-label="Run history" className="w-full min-w-[560px] text-left text-sm">
                    <thead className="sticky top-0 border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-2.5 font-medium">Run</th>
                        <th className="px-4 py-2.5 font-medium">Model</th>
                        <th className="px-4 py-2.5 font-medium">Accuracy</th>
                        <th className="px-4 py-2.5 font-medium">Consistency</th>
                        <th className="px-4 py-2.5 font-medium">Cases × Repeats</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.map((run) => {
                        const isSelected = run.id === latestRun.id
                        return (
                          <tr
                            key={run.id}
                            onClick={() => handleSelectRun(run.id)}
                            aria-current={isSelected ? 'true' : undefined}
                            className={`cursor-pointer border-b border-slate-100 transition-colors last:border-0 ${
                              isSelected ? 'bg-teal-50 hover:bg-teal-50' : 'hover:bg-slate-50'
                            } ${switchingRunId === run.id ? 'opacity-50' : ''}`}
                          >
                            <td className="px-4 py-2.5 font-medium text-slate-800">
                              {new Date(run.created_at).toLocaleString()}
                              {isSelected && <span className="ml-2 text-xs font-normal text-teal-700">Viewing</span>}
                            </td>
                            <td className="px-4 py-2.5 text-slate-600">{run.model_used}</td>
                            <td className="px-4 py-2.5 text-slate-600">{formatPercent(run.accuracy)}</td>
                            <td className="px-4 py-2.5 text-slate-600">{formatPercent(run.consistency)}</td>
                            <td className="px-4 py-2.5 text-slate-600">
                              {run.total_cases} × {run.repeats}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  )
}
