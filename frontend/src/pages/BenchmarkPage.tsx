import { useEffect, useState } from 'react'
import { Cpu, Gauge, Repeat, SlidersHorizontal, Sparkles } from 'lucide-react'
import {
  getBenchmarkRun,
  getConfidenceThreshold,
  listBenchmarkRuns,
  runBenchmark,
  type BenchmarkCase,
  type BenchmarkRun,
  type BenchmarkRunSummary,
} from '../lib/api'
import { simulateThreshold } from '../lib/thresholdSimulation'
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
  const [liveThreshold, setLiveThreshold] = useState<number | null>(null)
  const [candidateThreshold, setCandidateThreshold] = useState(0.7)

  useEffect(() => {
    getConfidenceThreshold()
      .then(({ confidence_threshold }) => {
        setLiveThreshold(confidence_threshold)
        setCandidateThreshold(confidence_threshold)
      })
      .catch(() => {
        // Non-critical - the simulator still works with its 0.7 default if this fails.
      })
  }, [])

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

  const candidateSimulation = latestRun ? simulateThreshold(latestRun.cases, candidateThreshold) : null
  const liveSimulation =
    latestRun && liveThreshold !== null ? simulateThreshold(latestRun.cases, liveThreshold) : null

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

          {candidateSimulation && (
            <details className="group rounded-xl border border-slate-200 bg-white shadow-sm">
              <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-slate-700 marker:content-none">
                <SlidersHorizontal className="h-4 w-4 text-teal-700" aria-hidden="true" />
                Threshold Simulator
                <span className="ml-auto text-xs font-normal text-slate-400 group-open:hidden">
                  Click to explore what-if scenarios
                </span>
              </summary>
              <div className="flex flex-col gap-3 border-t border-slate-100 px-4 pb-4 pt-3 sm:gap-4">
                <p className="text-xs text-slate-500">
                  Move the slider to see how many of this run's {candidateSimulation.totalCases} cases
                  would auto-process vs. route to human review at a candidate confidence threshold,
                  compared to the live setting.
                </p>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={candidateThreshold}
                    onChange={(e) => setCandidateThreshold(Number(e.target.value))}
                    aria-label="Candidate confidence threshold"
                    className="h-2 w-full flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 accent-teal-700"
                  />
                  <span className="w-14 shrink-0 text-right text-sm font-semibold text-slate-900">
                    {candidateThreshold.toFixed(2)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:gap-3">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Live threshold {liveThreshold !== null ? `(${liveThreshold.toFixed(2)})` : ''}
                    </p>
                    {liveSimulation ? (
                      <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                        <dt className="text-slate-500">Auto-processed</dt>
                        <dd className="text-right font-medium text-slate-900">{liveSimulation.autoCount}</dd>
                        <dt className="text-slate-500">To review</dt>
                        <dd className="text-right font-medium text-slate-900">{liveSimulation.reviewCount}</dd>
                        <dt className="text-slate-500">Wrong, auto-approved</dt>
                        <dd className="text-right font-medium text-red-700">{liveSimulation.autoIncorrect}</dd>
                      </dl>
                    ) : (
                      <p className="mt-1.5 text-sm text-slate-400">Loading live threshold…</p>
                    )}
                  </div>
                  <div className="rounded-lg border border-teal-200 bg-teal-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-teal-700">
                      Candidate threshold ({candidateThreshold.toFixed(2)})
                    </p>
                    <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                      <dt className="text-teal-800">Auto-processed</dt>
                      <dd className="text-right font-medium text-teal-900">{candidateSimulation.autoCount}</dd>
                      <dt className="text-teal-800">To review</dt>
                      <dd className="text-right font-medium text-teal-900">{candidateSimulation.reviewCount}</dd>
                      <dt className="text-teal-800">Wrong, auto-approved</dt>
                      <dd className="text-right font-medium text-red-700">{candidateSimulation.autoIncorrect}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </details>
          )}

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
