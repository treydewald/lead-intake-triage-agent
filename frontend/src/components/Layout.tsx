import { NavLink, Outlet } from 'react-router-dom'
import { BuildIndicator } from './BuildIndicator'

const navItems = [
  { to: '/', label: 'Observability' },
  { to: '/review', label: 'Review Queue' },
]

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white px-4 py-6">
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
      <main className="min-w-0 flex-1 overflow-auto p-6">
        <Outlet />
      </main>
      <BuildIndicator />
    </div>
  )
}
