/**
 * Norma Facile 2.0 - Main App Component
 * Handles routing and auth context.
 */
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';
import LandingPage from './pages/LandingPage';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import ClientsPage from './pages/ClientsPage';
import InvoicesPage from './pages/InvoicesPage';
import InvoiceEditorPage from './pages/InvoiceEditorPage';
import SettingsPage from './pages/SettingsPage';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

/**
 * App Router with session_id detection
 * Detects session_id DURING RENDER (not in useEffect) to prevent race conditions.
 */
function AppRouter() {
    const location = useLocation();

    // Check URL fragment for session_id synchronously during render
    // This prevents race conditions by processing new session_id FIRST
    if (location.hash?.includes('session_id=')) {
        return <AuthCallback />;
    }

    return (
        <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route
                path="/dashboard"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
            {/* Clients */}
            <Route
                path="/clients"
                element={
                    <ProtectedRoute>
                        <ClientsPage />
                    </ProtectedRoute>
                }
            />
            {/* Invoices */}
            <Route
                path="/invoices"
                element={
                    <ProtectedRoute>
                        <InvoicesPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/invoices/new"
                element={
                    <ProtectedRoute>
                        <InvoiceEditorPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/invoices/:invoiceId"
                element={
                    <ProtectedRoute>
                        <InvoiceEditorPage />
                    </ProtectedRoute>
                }
            />
            {/* Settings */}
            <Route
                path="/settings"
                element={
                    <ProtectedRoute>
                        <SettingsPage />
                    </ProtectedRoute>
                }
            />
            {/* Placeholder routes for Phase 2 */}
            <Route
                path="/documents/*"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/chat"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/archive"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
        </Routes>
    );
}

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <AppRouter />
                <Toaster position="top-right" />
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;
