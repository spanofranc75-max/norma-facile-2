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
import RilieviPage from './pages/RilieviPage';
import RilievoEditorPage from './pages/RilievoEditorPage';
import DistintePage from './pages/DistintePage';
import DistintaEditorPage from './pages/DistintaEditorPage';
import CertificazioniPage from './pages/CertificazioniPage';
import CertificazioneWizardPage from './pages/CertificazioneWizardPage';
import SicurezzaPage from './pages/SicurezzaPage';
import PosWizardPage from './pages/PosWizardPage';
import CatalogoPage from './pages/CatalogoPage';
import PreventiviPage from './pages/PreventiviPage';
import PreventivoEditorPage from './pages/PreventivoEditorPage';
import FascicoloCantierePage from './pages/FascicoloCantierePage';
import PaymentTypesPage from './pages/PaymentTypesPage';
import DDTListPage from './pages/DDTListPage';
import DDTEditorPage from './pages/DDTEditorPage';
import FornitoriPage from './pages/FornitoriPage';
import PeriziaListPage from './pages/PeriziaListPage';
import PeriziaEditorPage from './pages/PeriziaEditorPage';
import ArchivioSinistriPage from './pages/ArchivioSinistriPage';
import ArticoliPage from './pages/ArticoliPage';
import FattureRicevutePage from './pages/FattureRicevutePage';
import ScadenziarioPage from './pages/ScadenziarioPage';
import CostControlPage from './pages/CostControlPage';
import DisclaimerPage from './pages/legal/DisclaimerPage';
import TermsPage from './pages/legal/TermsPage';
import PrivacyPage from './pages/legal/PrivacyPage';
import CoreEnginePage from './pages/CoreEnginePage';
import ValidazioneFotoPage from './pages/ValidazioneFotoPage';
import PlanningPage from './pages/PlanningPage';
import CommessaHubPage from './pages/CommessaHubPage';
import EBITDAPage from './pages/EBITDAPage';
import TracciabilitaPage from './pages/TracciabilitaPage';
import FPCProjectPage from './pages/FPCProjectPage';
import ReportCAMPage from './pages/ReportCAMPage';
import ArchivioCertificatiPage from './pages/ArchivioCertificatiPage';
import QualitySystemPage from './pages/QualitySystemPage';
import InstrumentsPage from './pages/InstrumentsPage';
import WeldersPage from './pages/WeldersPage';
import WPSPage from './pages/WPSPage';
import AuditPage from './pages/AuditPage';
import QualityHubPage from './pages/QualityHubPage';
import NotificationsPage from './pages/NotificationsPage';
import SettingsPage from './pages/SettingsPage';
import ProtectedRoute from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';
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
            {/* Rilievi */}
            <Route
                path="/rilievi"
                element={
                    <ProtectedRoute>
                        <RilieviPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/rilievi/new"
                element={
                    <ProtectedRoute>
                        <RilievoEditorPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/rilievi/:rilievoId"
                element={
                    <ProtectedRoute>
                        <RilievoEditorPage />
                    </ProtectedRoute>
                }
            />
            {/* Distinte */}
            <Route
                path="/distinte"
                element={
                    <ProtectedRoute>
                        <DistintePage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/distinte/new"
                element={
                    <ProtectedRoute>
                        <DistintaEditorPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/distinte/:distintaId"
                element={
                    <ProtectedRoute>
                        <DistintaEditorPage />
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
            {/* Certificazioni CE */}
            <Route path="/certificazioni" element={<ProtectedRoute><CertificazioniPage /></ProtectedRoute>} />
            <Route path="/certificazioni/new" element={<ProtectedRoute><CertificazioneWizardPage /></ProtectedRoute>} />
            <Route path="/certificazioni/:certId" element={<ProtectedRoute><CertificazioneWizardPage /></ProtectedRoute>} />
            {/* Sicurezza Cantieri */}
            <Route path="/sicurezza" element={<ProtectedRoute><SicurezzaPage /></ProtectedRoute>} />
            <Route path="/sicurezza/new" element={<ProtectedRoute><PosWizardPage /></ProtectedRoute>} />
            <Route path="/sicurezza/:posId" element={<ProtectedRoute><PosWizardPage /></ProtectedRoute>} />
            {/* Catalogo Profili */}
            <Route path="/catalogo" element={<ProtectedRoute><CatalogoPage /></ProtectedRoute>} />
            {/* Fascicolo Cantiere */}
            <Route path="/fascicolo/:clientId" element={<ProtectedRoute><FascicoloCantierePage /></ProtectedRoute>} />
            {/* Tipi Pagamento */}
            <Route path="/impostazioni/pagamenti" element={<ProtectedRoute><PaymentTypesPage /></ProtectedRoute>} />
            {/* Preventivi */}
            <Route path="/preventivi" element={<ProtectedRoute><PreventiviPage /></ProtectedRoute>} />
            <Route path="/preventivi/new" element={<ProtectedRoute><PreventivoEditorPage /></ProtectedRoute>} />
            <Route path="/preventivi/:prevId" element={<ProtectedRoute><PreventivoEditorPage /></ProtectedRoute>} />
            {/* DDT */}
            <Route path="/ddt" element={<ProtectedRoute><DDTListPage /></ProtectedRoute>} />
            <Route path="/ddt/new" element={<ProtectedRoute><DDTEditorPage /></ProtectedRoute>} />
            <Route path="/ddt/:ddtId" element={<ProtectedRoute><DDTEditorPage /></ProtectedRoute>} />
            {/* Fornitori */}
            <Route path="/fornitori" element={<ProtectedRoute><FornitoriPage /></ProtectedRoute>} />
            {/* Perizie Sinistro */}
            <Route path="/perizie" element={<ProtectedRoute><PeriziaListPage /></ProtectedRoute>} />
            <Route path="/perizie/new" element={<ProtectedRoute><PeriziaEditorPage /></ProtectedRoute>} />
            <Route path="/perizie/:periziaId" element={<ProtectedRoute><PeriziaEditorPage /></ProtectedRoute>} />
            {/* Archivio Sinistri */}
            <Route path="/archivio-sinistri" element={<ProtectedRoute><ArchivioSinistriPage /></ProtectedRoute>} />
            {/* Catalogo Articoli */}
            <Route path="/articoli" element={<ProtectedRoute><ArticoliPage /></ProtectedRoute>} />
            {/* Fatture Ricevute */}
            <Route path="/fatture-ricevute" element={<ProtectedRoute><FattureRicevutePage /></ProtectedRoute>} />
            <Route path="/scadenziario" element={<ProtectedRoute><ScadenziarioPage /></ProtectedRoute>} />
            <Route path="/controllo-costi" element={<ProtectedRoute><CostControlPage /></ProtectedRoute>} />
            <Route path="/legal/disclaimer" element={<DisclaimerPage />} />
            <Route path="/legal/terms" element={<TermsPage />} />
            <Route path="/legal/privacy" element={<PrivacyPage />} />
            {/* Core Engine */}
            <Route path="/core-engine" element={<ProtectedRoute><CoreEnginePage /></ProtectedRoute>} />

            <Route path="/validazione-foto" element={<ProtectedRoute><ValidazioneFotoPage /></ProtectedRoute>} />

            <Route path="/planning" element={<ProtectedRoute><PlanningPage /></ProtectedRoute>} />
            <Route path="/commesse/:commessaId" element={<ProtectedRoute><CommessaHubPage /></ProtectedRoute>} />
            <Route path="/ebitda" element={<ProtectedRoute><EBITDAPage /></ProtectedRoute>} />
            {/* Tracciabilità EN 1090 */}
            <Route path="/tracciabilita" element={<ProtectedRoute><TracciabilitaPage /></ProtectedRoute>} />
            <Route path="/tracciabilita/progetto/:projectId" element={<ProtectedRoute><FPCProjectPage /></ProtectedRoute>} />
            {/* Report CAM */}
            <Route path="/report-cam" element={<ProtectedRoute><ReportCAMPage /></ProtectedRoute>} />
            <Route path="/archivio-certificati" element={<ProtectedRoute><ArchivioCertificatiPage /></ProtectedRoute>} />
            <Route path="/sistema-qualita" element={<ProtectedRoute><QualitySystemPage /></ProtectedRoute>} />
            <Route path="/strumenti" element={<ProtectedRoute><InstrumentsPage /></ProtectedRoute>} />
            <Route path="/saldatori" element={<ProtectedRoute><WeldersPage /></ProtectedRoute>} />
            <Route path="/wps" element={<ProtectedRoute><WPSPage /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
            <Route path="/quality-hub" element={<ProtectedRoute><QualityHubPage /></ProtectedRoute>} />
            <Route path="/notifiche" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
        </Routes>
    );
}

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <ErrorBoundary>
                    <AppRouter />
                </ErrorBoundary>
                <Toaster position="top-right" />
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;
