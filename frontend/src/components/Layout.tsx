import { Activity, ClipboardCheck, Gauge } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { BuildIndicator } from './BuildIndicator'

const navItems = [
  { to: '/leads', label: 'Observability', icon: Activity },
  { to: '/reviews', label: 'Review Queue', icon: ClipboardCheck },
  { to: '/benchmark', label: 'Benchmark', icon: Gauge },
]

export function Layout() {
  const location = useLocation()

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-50 text-slate-900 md:flex-row">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white px-4 py-6 md:flex">
        <div className="mb-8 flex items-center gap-2 px-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700 text-sm font-bold text-white">
            LT
          </div>
          <span className="text-sm font-semibold tracking-tight text-slate-900">Lead Intake Triage</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-1 ${
                  isActive
                    ? 'bg-teal-700 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <header className="flex shrink-0 flex-col gap-1.5 border-b border-slate-200 bg-white px-4 py-2 md:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-teal-700 text-[11px] font-bold text-white">
            LT
          </div>
          <span className="text-sm font-semibold tracking-tight">Lead Intake Triage</span>
        </div>
        <nav className="flex flex-wrap gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium ${
                  isActive
                    ? 'bg-teal-700 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="min-w-0 flex-1 overflow-auto p-4 sm:p-6">
        <div key={location.pathname} className="page-transition h-full">
          <Outlet />
        </div>
      </main>
      <BuildIndicator />
    </div>
  )
}
