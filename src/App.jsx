import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import { RequireRole } from './context/AuthContext'
import Landing from './pages/Landing'
import Onboarding from './pages/Onboarding'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Upload from './pages/Upload'
import Analysis from './pages/Analysis'
import Vault from './pages/Vault'
import DocumentView from './pages/DocumentView'
import CaseBrief from './pages/CaseBrief'
import CaseBriefView from './pages/CaseBriefView'
import Calculator from './pages/Calculator'
import LegalAid from './pages/LegalAid'
import Emergency from './pages/Emergency'
import LawyerProfile from './pages/LawyerProfile'
import Booking from './pages/Booking'
import Payment from './pages/Payment'
import Community from './pages/Community'
import AskQuestion from './pages/AskQuestion'
import QuestionView from './pages/QuestionView'
import Offline from './pages/Offline'
import WhatsApp from './pages/WhatsApp'
import Settings from './pages/Settings'
import LawyerDashboard from './pages/LawyerDashboard'
import LawyerProfileEdit from './pages/LawyerProfileEdit'
import LawyerConsultations from './pages/LawyerConsultations'
import LawyerPayments from './pages/LawyerPayments'
import AdminDashboard from './pages/AdminDashboard'
import AdminLawyers from './pages/AdminLawyers'
import AdminLawyerApplications from './pages/AdminLawyerApplications'
import AdminUsers from './pages/AdminUsers'
import AdminBookings from './pages/AdminBookings'
import LawyerApply from './pages/LawyerApply'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/lawyer/apply" element={<LawyerApply />} />

        <Route element={<RequireRole role="client"><AppLayout /></RequireRole>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/chat/:id" element={<Chat />} />
          <Route path="/documents" element={<Navigate to="/documents/upload" replace />} />
          <Route path="/documents/upload" element={<Upload />} />
          <Route path="/documents/analysis" element={<Navigate to="/documents/analysis/tenancy" replace />} />
          <Route path="/documents/analysis/:id" element={<Analysis />} />
          <Route path="/vault" element={<Vault />} />
          <Route path="/vault/document/:id" element={<DocumentView />} />
          <Route path="/case-briefs" element={<Navigate to="/case-briefs/new" replace />} />
          <Route path="/case-briefs/new" element={<CaseBrief />} />
          <Route path="/case-briefs/:id" element={<CaseBriefView />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="/legal-aid" element={<LegalAid />} />
          <Route path="/emergency" element={<Emergency />} />
          <Route path="/find-a-lawyer/:id" element={<LawyerProfile />} />
          <Route path="/find-a-lawyer/:id/book" element={<Booking />} />
          <Route path="/find-a-lawyer/:id/pay/:bookingId" element={<Payment />} />
          <Route path="/community" element={<Community />} />
          <Route path="/community/ask" element={<AskQuestion />} />
          <Route path="/community/:id" element={<QuestionView />} />
          <Route path="/offline" element={<Offline />} />
          <Route path="/whatsapp" element={<WhatsApp />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        <Route element={<RequireRole role="lawyer"><AppLayout /></RequireRole>}>
          <Route path="/lawyer" element={<LawyerDashboard />} />
          <Route path="/lawyer/profile" element={<LawyerProfileEdit />} />
          <Route path="/lawyer/consultations" element={<LawyerConsultations />} />
          <Route path="/lawyer/payments" element={<LawyerPayments />} />
        </Route>

        <Route element={<RequireRole role="admin"><AppLayout /></RequireRole>}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/lawyers" element={<AdminLawyers />} />
          <Route path="/admin/lawyers/pending" element={<AdminLawyerApplications />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/bookings" element={<AdminBookings />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
