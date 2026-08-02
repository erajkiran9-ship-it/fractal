import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ManagerDashboard from './pages/ManagerDashboard'
import CustomerPortal from './pages/CustomerPortal'
import CollectorDashboard from './pages/CollectorDashboard'
import DisputeDashboard from './pages/DisputeDashboard'
import NotificationInbox from './pages/NotificationInbox'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/manager" replace />} />
        <Route path="/manager" element={<ManagerDashboard />} />
        <Route path="/customer/:customerId" element={<NotificationInbox role="customer" />} />
        <Route path="/customer/:customerId/portal" element={<CustomerPortal />} />
        <Route path="/collector" element={<NotificationInbox role="collector" />} />
        <Route path="/collector/workbench" element={<CollectorDashboard />} />
        <Route path="/disputes" element={<NotificationInbox role="disputes" />} />
        <Route path="/disputes/workbench" element={<DisputeDashboard />} />
        <Route path="/disputes/case/:disputeId" element={<DisputeDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
