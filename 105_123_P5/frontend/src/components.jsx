import { AlertTriangle, Loader2, Menu, X } from 'lucide-react'

export function LoadingState({ label = 'Loading live operations data...' }) {
  return <div className="flex items-center gap-3 border border-slate-800 bg-slate-900 p-6 text-sm uppercase tracking-wide text-slate-400"><Loader2 className="animate-spin text-cyan-300" size={18} />{label}</div>
}

export function ErrorState({ message, onRetry }) {
  return <div className="flex items-center justify-between gap-4 border-l-2 border-red-500 bg-red-950/30 p-5 text-rose-200"><span className="flex items-center gap-3"><AlertTriangle size={18} />{message}</span>{onRetry && <button onClick={onRetry} className="border border-rose-700 px-3 py-2 text-sm uppercase tracking-wide">Retry</button>}</div>
}

export function EmptyState({ title = 'No records yet', description = 'Live data will appear here when reports arrive.' }) {
  return <div className="border border-dashed border-slate-700 p-10 text-center"><p className="font-semibold uppercase tracking-wide text-slate-200">{title}</p><p className="mt-2 text-sm text-slate-500">{description}</p></div>
}

export function StatusBadge({ status }) {
  const styles = { Assigned: 'bg-cyan-400/10 text-cyan-300', Pending: 'bg-amber-400/10 text-amber-300', 'In Progress': 'bg-violet-400/10 text-violet-300', Resolved: 'bg-emerald-400/10 text-emerald-300', Rejected: 'bg-rose-400/10 text-rose-300', waiting: 'bg-amber-400/10 text-amber-300', correction_queue: 'bg-rose-400/10 text-rose-300' }
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status] || 'bg-slate-700 text-slate-300'}`}>{status}</span>
}

export function PriorityBadge({ priority }) {
  const styles = { Critical: 'text-rose-300 bg-rose-400/10', High: 'text-orange-300 bg-orange-400/10', Normal: 'text-slate-300 bg-slate-700' }
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${styles[priority] || styles.Normal}`}>{priority || '—'}</span>
}

export function StatCard({ label, value, icon: Icon, tone = 'cyan' }) {
  const colors = { cyan: 'bg-cyan-400/10 text-cyan-300', amber: 'bg-amber-400/10 text-amber-300', violet: 'bg-violet-400/10 text-violet-300', emerald: 'bg-emerald-400/10 text-emerald-300', rose: 'bg-rose-400/10 text-rose-300' }
  return <div className="border border-slate-800 bg-slate-900 p-5"><div className="flex items-center justify-between"><span className="text-xs uppercase tracking-[0.15em] text-slate-400">{label}</span><span className={`rounded-none p-2 ${colors[tone]}`}><Icon size={18} /></span></div><p className="mt-5 text-4xl font-black text-white">{value ?? '—'}</p></div>
}

export function Field({ label, children, hint }) {
  return <label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">{label}</span>{children}{hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}</label>
}

export function MobileMenuButton({ open, onClick }) {
  return <button aria-label="Toggle navigation" onClick={onClick} className="rounded-lg border border-slate-700 p-2 lg:hidden">{open ? <X size={20} /> : <Menu size={20} />}</button>
}
