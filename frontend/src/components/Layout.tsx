import { NavLink, Outlet } from 'react-router-dom'
import { BuildIndicator } from './BuildIndicator'

const navItems = [
  { to: '/leads', label: 'Observability' },
  { to: '/reviews', label: 'Review Queue' },
  { to: '/benchmark', label: 'Benchmark' },
]

export function Layout() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-50 text-slate-900 md:flex-row">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-white px-4 py-6 md:flex">
        <div className="mb-8 text-lg font-semibold">Lead Intake Triage</div>
        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'bg-teal-700 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <header className="flex shrink-0 flex-col gap-1.5 border-b border-slate-200 bg-white px-4 py-2 md:hidden">
        <span className="text-base font-semibold">Lead Intake Triage</span>
        <nav className="flex flex-wrap gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-md px-2.5 py-1 text-xs font-medium ${
                  isActive
                    ? 'bg-teal-700 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="min-w-0 flex-1 overflow-auto p-4 sm:p-6">
        <Outlet />
      </main>
      <BuildIndicator />
    </div>
  )
}
