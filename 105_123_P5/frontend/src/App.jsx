import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './layout'
import { AnalyticsDashboard, Dashboard, HandlerDashboard, RoutingDashboard, SubmitReport, TrackReport } from './pages'

function App() {
  return <BrowserRouter><Routes><Route element={<AppLayout />}><Route path="/" element={<Dashboard />} /><Route path="/reports/new" element={<SubmitReport />} /><Route path="/track" element={<TrackReport />} /><Route path="/handlers" element={<HandlerDashboard />} /><Route path="/routing" element={<RoutingDashboard />} /><Route path="/analytics" element={<AnalyticsDashboard />} /><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes></BrowserRouter>
}

export default App
