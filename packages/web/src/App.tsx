import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { CompanyDashboard } from './pages/CompanyDashboard'
import { DemoPage } from './pages/DemoPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DemoPage />} />
        <Route path="/company" element={<CompanyDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
