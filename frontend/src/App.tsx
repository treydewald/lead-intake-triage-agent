import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { BenchmarkPage } from './pages/BenchmarkPage'
import { FunnelDashboardPage } from './pages/FunnelDashboardPage'
import { HomePage } from './pages/HomePage'
import { LeadDetailPage } from './pages/LeadDetailPage'
import { LeadHistoryPage } from './pages/LeadHistoryPage'
import { LeadListPage } from './pages/LeadListPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ReviewDetailPage } from './pages/ReviewDetailPage'
import { ReviewQueuePage } from './pages/ReviewQueuePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="leads" element={<LeadListPage />} />
          <Route path="leads/:leadId" element={<LeadDetailPage />} />
          <Route path="leads/:leadId/history" element={<LeadHistoryPage />} />
          <Route path="reviews" element={<ReviewQueuePage />} />
          <Route path="reviews/:runId" element={<ReviewDetailPage />} />
          <Route path="benchmark" element={<BenchmarkPage />} />
          <Route path="analytics" element={<FunnelDashboardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
