interface TrendPoint {
  label: string
  dateLabel: string
  accuracy: number
  consistency: number
}

interface TrendChartProps {
  points: TrendPoint[]
}

const WIDTH = 600
const HEIGHT = 200
const PAD_LEFT = 36
const PAD_RIGHT = 12
const PAD_TOP = 12
const PAD_BOTTOM = 10
const MIN_SPAN = 0.08

export function TrendChart({ points }: TrendChartProps) {
  if (points.length < 2) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
        Run the benchmark at least twice to see an accuracy/consistency trend.
      </div>
    )
  }

  const values = points.flatMap((p) => [p.accuracy, p.consistency])
  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  // Scale the y-axis to where the data actually lives, not a fixed 0-100% range — accuracy and
  // consistency both tend to cluster in a narrow high band, and a fixed axis squashes every real
  // run into a flat line pinned to the top with a large empty void beneath it.
  const span = Math.max(rawMax - rawMin, MIN_SPAN)
  const domainMax = Math.min(1, rawMax + span * 0.25)
  const domainMin = Math.max(0, domainMax - span * 1.5)

  const innerW = WIDTH - PAD_LEFT - PAD_RIGHT
  const innerH = HEIGHT - PAD_TOP - PAD_BOTTOM
  const stepX = points.length > 1 ? innerW / (points.length - 1) : 0
  const xFor = (i: number) => PAD_LEFT + stepX * i
  const yFor = (v: number) => PAD_TOP + innerH * (1 - (v - domainMin) / (domainMax - domainMin))

  const linePath = (key: 'accuracy' | 'consistency') =>
    points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i).toFixed(1)} ${yFor(p[key]).toFixed(1)}`).join(' ')

  const gridSteps = 4
  const gridValues = Array.from({ length: gridSteps + 1 }, (_, i) => domainMin + ((domainMax - domainMin) * i) / gridSteps)

  return (
    <div className="flex flex-col gap-2">
      {/* The axis percentage labels are plain HTML, not SVG <text>, on purpose: the chart's SVG
          uses preserveAspectRatio="none" so it can fill a wide-but-short container without
          letterboxing, but that non-uniform x/y scaling badly distorts any <text> glyph drawn
          inside the same viewBox (verified via a cropped/enlarged screenshot — the digits render
          as illegible squashed shapes, not just small text). Positioning real HTML text in an
          overlay column, sized as a percentage of the same box, keeps it perfectly legible and
          still aligned to each gridline's vertical position. */}
      <div className="relative h-20 w-full">
        <div
          className="pointer-events-none absolute inset-y-0 left-0"
          style={{ width: `${(PAD_LEFT / WIDTH) * 100}%` }}
        >
          {gridValues.map((g) => (
            <span
              key={g}
              className="absolute right-1.5 -translate-y-1/2 text-[11px] font-medium text-slate-600"
              style={{ top: `${(yFor(g) / HEIGHT) * 100}%` }}
            >
              {Math.round(g * 100)}%
            </span>
          ))}
        </div>
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-full w-full"
          role="img"
          aria-label="Accuracy and consistency trend across benchmark runs"
          preserveAspectRatio="none"
        >
          {gridValues.map((g) => (
            <line
              key={g}
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={yFor(g)}
              y2={yFor(g)}
              stroke="#e2e8f0"
              strokeWidth={1}
            />
          ))}
          <path
            d={linePath('consistency')}
            fill="none"
            stroke="#f59e0b"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="6 5"
            className="chart-line"
          />
          <path
            d={linePath('accuracy')}
            fill="none"
            stroke="#0f766e"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="chart-line"
          />
          {points.map((p, i) => (
            <g key={p.label}>
              <circle cx={xFor(i)} cy={yFor(p.consistency)} r={3.5} fill="#f59e0b" />
              <circle cx={xFor(i)} cy={yFor(p.accuracy)} r={3.5} fill="#0f766e">
                <title>
                  {p.dateLabel}: accuracy {(p.accuracy * 100).toFixed(1)}%, consistency{' '}
                  {(p.consistency * 100).toFixed(1)}%
                </title>
              </circle>
            </g>
          ))}
        </svg>
      </div>
      <div className="flex items-center justify-between pl-9 text-xs">
        <span className="text-slate-500">
          {points[0].dateLabel} – {points[points.length - 1].dateLabel}
        </span>
        <div className="flex items-center gap-3 font-medium text-slate-600">
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-4 rounded-full bg-teal-700" aria-hidden="true" />
            Accuracy
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="h-0.5 w-4 rounded-full bg-amber-500"
              style={{ backgroundImage: 'repeating-linear-gradient(to right, #f59e0b 0 3px, transparent 3px 6px)' }}
              aria-hidden="true"
            />
            Consistency
          </span>
        </div>
      </div>
    </div>
  )
}
