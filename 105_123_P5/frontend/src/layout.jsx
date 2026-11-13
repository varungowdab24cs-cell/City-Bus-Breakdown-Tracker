import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Activity, BarChart3, BusFront, ClipboardPlus, Map, Search, Settings2, ShieldAlert, Users } from 'lucide-react'
import { useState } from 'react'
import { MobileMenuButton } from './components'

const links = [
  { to: '/', label: 'Operations overview', icon: Activity },
  { to: '/reports/new', label: 'Submit breakdown', icon: ClipboardPlus },
  { to: '/track', label: 'Track a report', icon: Search },
  { to: '/handlers', label: 'Handler desk', icon: Users },
  { to: '/routing', label: 'Routing control', icon: Map },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export function AppLayout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const current = links.find((link) => link.to === location.pathname) || links[0]
  return <div className="min-h-screen bg-[#07111f] text-slate-100">
    <aside className={`fixed inset-y-0 left-0 z-30 w-72 border-r border-slate-800 bg-[#091525] p-5 transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="flex items-center gap-3 border-b border-slate-800 px-2 pb-6"><div className="flex h-10 w-10 items-center justify-center rounded-none bg-cyan-300 font-black text-slate-950">CB</div><div><p className="font-bold uppercase tracking-[0.16em]">City Bus Ops</p><p className="text-xs uppercase tracking-[0.2em] text-slate-500">Control room</p></div></div>
      <div className="mt-7 rounded-none border-l-2 border-red-500 bg-red-500/5 p-3 text-xs uppercase tracking-wider text-red-300"><span className="mr-2 inline-block h-2 w-2 rounded-full bg-red-400" />API systems operational</div>
      <nav className="mt-8 space-y-1">{links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-3 border-l-2 px-3 py-3 text-sm uppercase tracking-wide transition ${isActive ? 'border-red-500 bg-red-500 font-semibold text-white' : 'border-transparent text-slate-400 hover:border-red-500 hover:bg-slate-800 hover:text-white'}`}><Icon size={17} />{label}</NavLink>)}</nav>
      <div className="absolute bottom-5 left-5 right-5 border-t border-slate-800 pt-4 text-xs text-slate-500"><div className="flex items-center gap-2"><ShieldAlert size={14} />Dispatch priority monitoring enabled</div><div className="mt-3 flex items-center gap-2"><Settings2 size={14} />Phase 5 operations build</div></div>
    </aside>
    {open && <button aria-label="Close navigation" onClick={() => setOpen(false)} className="fixed inset-0 z-20 bg-slate-950/70 lg:hidden" />}
    <div className="lg:pl-72"><header className="sticky top-0 z-10 border-b border-slate-800/80 bg-[#07111f]/90 px-5 py-4 backdrop-blur md:px-8"><div className="flex items-center justify-between"><div className="flex items-center gap-3"><MobileMenuButton open={open} onClick={() => setOpen(!open)} /><div><p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Transit command / 24·7</p><h1 className="text-xl font-bold uppercase tracking-wide">{current.label}</h1></div></div><div className="hidden items-center gap-3 text-xs uppercase tracking-widest text-slate-400 sm:flex"><BusFront size={18} className="text-cyan-300" />Live network · UTC</div></div></header><main className="mx-auto max-w-[1600px] p-5 md:p-8"><Outlet /></main></div>
  </div>
}
