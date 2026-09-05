import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  icon: LucideIcon
  hint?: string
  tone?: 'neutral' | 'amber' | 'emerald' | 'red'
}

const TONE_CLASSES: Record<NonNullable<StatCardProps['tone']>, string> = {
  neutral: 'bg-teal-50 text-teal-700',
  amber: 'bg-amber-50 text-amber-700',
  emerald: 'bg-emerald-50 text-emerald-700',
  red: 'bg-red-50 text-red-700',
}

export function StatCard({ label, value, icon: Icon, hint, tone = 'neutral' }: StatCardProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-2.5 shadow-sm sm:p-4">
      <div
        className={`hidden h-9 w-9 shrink-0 items-center justify-center rounded-lg sm:flex ${TONE_CLASSES[tone]}`}
      >
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase leading-tight text-slate-500 sm:text-xs sm:tracking-wide">
          {label}
        </div>
        <div className="mt-0.5 truncate text-lg font-semibold tracking-tight text-slate-900 sm:text-xl">{value}</div>
        {hint && <div className="mt-0.5 truncate text-xs text-slate-500">{hint}</div>}
      </div>
    </div>
  )
}
