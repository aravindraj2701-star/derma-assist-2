import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';

// Pages
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import DashboardPage from './pages/DashboardPage';
import DatasetPage from './pages/DatasetPage';
import AnalyzePage from './pages/AnalyzePage';
import ResultPage from './pages/ResultPage';
import HistoryPage from './pages/HistoryPage';
import CaseDetailPage from './pages/CaseDetailPage';
import DiseaseDetailPage from './pages/DiseaseDetailPage';
import ProfilePage from './pages/ProfilePage';
import ModelTrainingConsolePage from './pages/ModelTrainingConsolePage';
import AdminConsolePage from './pages/AdminConsolePage';
import MedicalChatWidget from './components/MedicalChatWidget';

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  // Public unauthenticated page paths where full app navigation bar must never render
  const isPublicAuthPage = ['/', '/login', '/forgot-password', '/reset-password'].includes(location.pathname);
  const showAppNav = isAuthenticated && !isPublicAuthPage;

  return (
    <>
      {showAppNav && <Navbar />}
      <Routes>
        {/* Public Intro Landing Page — authenticated users redirected to dashboard */}
        <Route path="/" element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : <LandingPage />
        } />

        {/* Public Auth & Password Reset Pages */}
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
        } />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Protected Application Routes */}
        <Route path="/dashboard" element={
          <ProtectedRoute><DashboardPage /></ProtectedRoute>
        } />
        <Route path="/dataset" element={
          <ProtectedRoute><DatasetPage /></ProtectedRoute>
        } />
        <Route path="/analyze" element={
          <ProtectedRoute><AnalyzePage /></ProtectedRoute>
        } />
        <Route path="/result" element={
          <ProtectedRoute><ResultPage /></ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute><HistoryPage /></ProtectedRoute>
        } />
        <Route path="/history/:caseId" element={
          <ProtectedRoute><CaseDetailPage /></ProtectedRoute>
        } />
        <Route path="/disease/:diseaseId" element={
          <ProtectedRoute><DiseaseDetailPage /></ProtectedRoute>
        } />
        <Route path="/profile" element={
          <ProtectedRoute><ProfilePage /></ProtectedRoute>
        } />
        {/* Dedicated Admin Account & Security Management Console */}
        <Route path="/admin" element={
          <ProtectedRoute requireAdmin={true}><AdminConsolePage /></ProtectedRoute>
        } />
        {/* Continuous Learning / Model Training Console */}
        <Route path="/admin/training" element={
          <ProtectedRoute><ModelTrainingConsolePage /></ProtectedRoute>
        } />

        {/* Default redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {showAppNav && <MedicalChatWidget />}
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

