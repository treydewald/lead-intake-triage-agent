import { useEffect, useState } from 'react'
import { getBenchmarkRun, listBenchmarkRuns, runBenchmark, type BenchmarkCase, type BenchmarkRun } from '../lib/api'

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
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Classification Accuracy Benchmark</h1>
        <button
          type="button"
          onClick={handleRunBenchmark}
          disabled={running}
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {running ? 'Running…' : 'Run Benchmark'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !latestRun && !running && (
        <p className="text-sm text-slate-500">No benchmark runs yet. Click "Run Benchmark" to measure classification accuracy.</p>
      )}

      {latestRun && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Accuracy</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{formatPercent(latestRun.accuracy)}</div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Consistency</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{formatPercent(latestRun.consistency)}</div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Model / Cases</div>
              <div className="mt-1 text-sm text-slate-700">
                {latestRun.model_used} · {latestRun.total_cases} cases · {latestRun.repeats} repeats
              </div>
            </div>
          </div>

          <h2 className="text-sm font-semibold text-slate-700">Failure &amp; Ambiguous Cases</h2>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
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
                {misclassifiedAndAmbiguous.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                      No failures or ambiguous cases in this run.
                    </td>
                  </tr>
                )}
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
          </div>
        </>
      )}
    </div>
  )
}
