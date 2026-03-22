/**
 * Norma Facile 2.0 - Main App Component
 * Handles routing and auth context.
 */
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
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
import SopralluoghiPage from './pages/SopralluoghiPage';
import SopralluogoWizardPage from './pages/SopralluogoWizardPage';
import ArchivioSinistriPage from './pages/ArchivioSinistriPage';
import ArticoliPage from './pages/ArticoliPage';
import FattureRicevutePage from './pages/FattureRicevutePage';
import ScadenziarioPage from './pages/ScadenziarioPage';
import MovimentiBancariPage from './pages/MovimentiBancariPage';
import CostControlPage from './pages/CostControlPage';
import MarginAnalysisPage from './pages/MarginAnalysisPage';
import FinancialSettingsPage from './pages/FinancialSettingsPage';
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
import MatriceScadenzePage from './pages/MatriceScadenzePage';
import VerbalePosaPage from './pages/VerbalePosaPage';
import WPSPage from './pages/WPSPage';
import AuditPage from './pages/AuditPage';
import QualityHubPage from './pages/QualityHubPage';
import NotificationsPage from './pages/NotificationsPage';
import SettingsPage from './pages/SettingsPage';
import ActivityLogPage from './pages/ActivityLogPage';
import OfficinaPage from './pages/OfficinaPage';
import AttrezzaturePage from './pages/AttrezzaturePage';
import ScadenziarioManutenzioniPage from './pages/ScadenziarioManutenzioniPage';
import VerbaliITTPage from './pages/VerbaliITTPage';
import ExecutiveDashboardPage from './pages/ExecutiveDashboardPage';
import ArchivioStoricoPage from './pages/ArchivioStoricoPage';
import IstruttoriaPage from './pages/IstruttoriaPage';
import ValidationPage from './pages/ValidationPage';
import PreventivatoreWizard from './pages/PreventivatoreWizard';
import ManualePage from './pages/ManualePage';
import KPIDashboard from './pages/KPIDashboard';
import ConfrontoPreventivi from './pages/ConfrontoPreventivi';
import AnalisiAIPage from './pages/AnalisiAIPage';
import ProtectedRoute from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';
import './App.css';

/**
 * App Router with session_id detection
 * Detects session_id DURING RENDER (not in useEffect) to prevent race conditions.
 */
function AppRouter() {
    const location = useLocation();

    // Check URL fragment for session_id (Emergent Auth) synchronously during render
    if (location.hash?.includes('session_id=')) {
        return <AuthCallback />;
    }

    // Check URL params for code (Google OAuth) synchronously during render
    if (location.search?.includes('code=')) {
        return <AuthCallback />;
    }

    return (
        <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            {/* Officina: NO ProtectedRoute — uses PIN auth */}
            <Route path="/officina/:commessaId" element={<OfficinaPage />} />
            <Route path="/officina/:commessaId/:voceId" element={<OfficinaPage />} />
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
            {/* Sopralluoghi & Messa a Norma AI */}
            <Route path="/sopralluoghi" element={<ProtectedRoute><SopralluoghiPage /></ProtectedRoute>} />
            <Route path="/sopralluoghi/new" element={<ProtectedRoute><SopralluogoWizardPage /></ProtectedRoute>} />
            <Route path="/sopralluoghi/:sopralluogoId" element={<ProtectedRoute><SopralluogoWizardPage /></ProtectedRoute>} />
            {/* Archivio Sinistri */}
            <Route path="/archivio-sinistri" element={<ProtectedRoute><ArchivioSinistriPage /></ProtectedRoute>} />
            {/* Catalogo Articoli */}
            <Route path="/articoli" element={<ProtectedRoute><ArticoliPage /></ProtectedRoute>} />
            {/* Fatture Ricevute */}
            <Route path="/fatture-ricevute" element={<ProtectedRoute><FattureRicevutePage /></ProtectedRoute>} />
            <Route path="/scadenziario" element={<ProtectedRoute><ScadenziarioPage /></ProtectedRoute>} />
            <Route path="/movimenti-bancari" element={<ProtectedRoute><MovimentiBancariPage /></ProtectedRoute>} />
            <Route path="/controllo-costi" element={<ProtectedRoute><CostControlPage /></ProtectedRoute>} />
            <Route path="/analisi-margini" element={<ProtectedRoute><MarginAnalysisPage /></ProtectedRoute>} />
            <Route path="/configurazione-finanziaria" element={<ProtectedRoute><FinancialSettingsPage /></ProtectedRoute>} />
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
            <Route path="/saldatori" element={<Navigate to="/operai" replace />} />
            <Route path="/operai" element={<ProtectedRoute><WeldersPage /></ProtectedRoute>} />
            <Route path="/operai/matrice" element={<ProtectedRoute><MatriceScadenzePage /></ProtectedRoute>} />
            <Route path="/verbale-posa/:commessaId" element={<ProtectedRoute><VerbalePosaPage /></ProtectedRoute>} />
            <Route path="/wps" element={<ProtectedRoute><WPSPage /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
            <Route path="/quality-hub" element={<ProtectedRoute><QualityHubPage /></ProtectedRoute>} />
            <Route path="/notifiche" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
            <Route path="/registro-attivita" element={<ProtectedRoute><ActivityLogPage /></ProtectedRoute>} />
            <Route path="/attrezzature" element={<ProtectedRoute><AttrezzaturePage /></ProtectedRoute>} />
            <Route path="/manutenzioni" element={<ProtectedRoute><ScadenziarioManutenzioniPage /></ProtectedRoute>} />
            <Route path="/verbali-itt" element={<ProtectedRoute><VerbaliITTPage /></ProtectedRoute>} />
            <Route path="/executive" element={<ProtectedRoute><ExecutiveDashboardPage /></ProtectedRoute>} />
            <Route path="/archivio-storico" element={<ProtectedRoute><ArchivioStoricoPage /></ProtectedRoute>} />
            <Route path="/istruttoria/:preventivoId" element={<ProtectedRoute><IstruttoriaPage /></ProtectedRoute>} />
            <Route path="/validazione-p1" element={<ProtectedRoute><ValidationPage /></ProtectedRoute>} />
            <Route path="/preventivatore" element={<ProtectedRoute><PreventivatoreWizard /></ProtectedRoute>} />
            <Route path="/manuale" element={<ProtectedRoute><ManualePage /></ProtectedRoute>} />
            <Route path="/kpi" element={<ProtectedRoute><KPIDashboard /></ProtectedRoute>} />
            <Route path="/confronto" element={<ProtectedRoute><ConfrontoPreventivi /></ProtectedRoute>} />
            <Route path="/analisi-ai/:prevId" element={<ProtectedRoute><AnalisiAIPage /></ProtectedRoute>} />
            <Route path="/fpc" element={<Navigate to="/tracciabilita" replace />} />
        </Routes>
    );
}

import { ConfirmProvider } from './components/ConfirmProvider';

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <ConfirmProvider>
                    <ErrorBoundary>
                        <AppRouter />
                    </ErrorBoundary>
                </ConfirmProvider>
                <Toaster position="top-right" />
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;
