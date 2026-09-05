import type { HTMLAttributes } from 'react'

export function Card({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}
      {...props}
    />
  )
}

export function SectionLabel({ children }: { children: string }) {
  return <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{children}</h2>
}
