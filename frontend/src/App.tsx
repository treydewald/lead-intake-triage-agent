import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { BenchmarkPage } from './pages/BenchmarkPage'
import { HomePage } from './pages/HomePage'
import { LeadDetailPage } from './pages/LeadDetailPage'
import { LeadListPage } from './pages/LeadListPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="leads" element={<LeadListPage />} />
          <Route path="leads/:leadId" element={<LeadDetailPage />} />
          <Route path="benchmark" element={<BenchmarkPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
