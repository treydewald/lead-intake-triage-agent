interface ConfidenceMeterProps {
  value: number | null
  className?: string
  showValue?: boolean
}

/**
 * The project's signature visual element: a confidence "spectrum" gauge (red -> amber -> emerald)
 * with a marker at the actual score, used everywhere a classification confidence is shown so the
 * app's core value — an AI confidence judgment — reads as one consistent visual language rather
 * than a plain number repeated across pages.
 */
export function ConfidenceMeter({ value, className = '', showValue = true }: ConfidenceMeterProps) {
  if (value == null) {
    return <span className={`text-sm text-slate-400 ${className}`}>—</span>
  }

  const pct = Math.max(0, Math.min(100, Math.round(value * 100)))

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className="relative h-1.5 w-16 shrink-0 rounded-full"
        style={{ background: 'linear-gradient(to right, #f87171, #fbbf24, #10b981)' }}
      >
        <div
          className="absolute top-1/2 h-3 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-slate-900 ring-2 ring-white"
          style={{ left: `${pct}%` }}
          aria-hidden="true"
        />
      </div>
      {showValue && <span className="text-sm font-medium tabular-nums text-slate-700">{pct}%</span>}
    </div>
  )
}
