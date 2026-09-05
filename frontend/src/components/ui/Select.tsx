import type { SelectHTMLAttributes } from 'react'
import { ChevronDown } from 'lucide-react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
}

export function Select({ label, className = '', ...props }: SelectProps) {
  return (
    <div className="relative w-full sm:w-auto">
      <select
        aria-label={label}
        className={`w-full appearance-none rounded-lg border border-slate-300 bg-white py-1.5 pl-3 pr-8 text-sm shadow-sm transition-colors hover:border-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600 sm:w-auto ${className}`}
        {...props}
      />
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        aria-hidden="true"
      />
    </div>
  )
}
