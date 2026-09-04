function formatBuildTime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function BuildIndicator() {
  return (
    <div className="pointer-events-none fixed bottom-2 right-3 z-50 select-none text-[11px] text-slate-400 dark:text-slate-600">
      Updated: {formatBuildTime(__BUILD_TIME__)}
    </div>
  )
}
