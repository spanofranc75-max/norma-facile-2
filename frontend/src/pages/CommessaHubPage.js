/**
 * CommessaHubPage — Central hub for a single commessa.
 * Shows lifecycle state, events timeline, linked modules, and actions.
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest, formatDateIT, downloadPdfBlob } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { toast } from 'sonner';
import {
    ArrowLeft, FileText, Receipt, Truck, Shield, Award,
    Ruler, Package, Play, Pause, CheckCircle2, XCircle,
    Clock, User, ChevronRight, Plus, Link2,
    AlertTriangle, Loader2, BookOpen, CalendarDays, TrendingUp,
    CircleDollarSign, Tag, Wrench as WrenchIcon, QrCode, Hammer,
} from 'lucide-react';
import CommessaOpsPanel from '../components/CommessaOpsPanel';
import VociLavoroSection from '../components/VociLavoroSection';
import { DisabledTooltip } from '../components/DisabledTooltip';
import CommessaComplianceBanner from '../components/CommessaComplianceBanner';
import RiesameTecnicoSection from '../components/RiesameTecnicoSection';
import RegistroSaldaturaSection from '../components/RegistroSaldaturaSection';
import TracciabilitaMaterialiSection from '../components/TracciabilitaMaterialiSection';
import ControlloFinaleSection from '../components/ControlloFinaleSection';
import ReportIspezioniSection from '../components/ReportIspezioniSection';
import RamiNormativiSection from '../components/RamiNormativiSection';
import ObbrighiCommessaSection from '../components/ObbrighiCommessaSection';
import VerificaCommittenzaSection from '../components/VerificaCommittenzaSection';
import CommessaActionsMenu from '../components/CommessaActionsMenu';
import NextStepCard from '../components/NextStepCard';

const API = process.env.REACT_APP_BACKEND_URL;
const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const STATO_STYLES = {
    richiesta:          { label: 'Richiesta',          bg: 'bg-violet-100', text: 'text-violet-800', dot: 'bg-violet-500' },
    bozza:              { label: 'Bozza',              bg: 'bg-slate-100',  text: 'text-slate-700',  dot: 'bg-slate-400' },
    rilievo_completato: { label: 'Rilievo Completato', bg: 'bg-amber-100',  text: 'text-amber-800',  dot: 'bg-amber-500' },
    firmato:            { label: 'Firmato',            bg: 'bg-blue-100',   text: 'text-blue-800',   dot: 'bg-blue-500' },
    in_produzione:      { label: 'In Produzione',      bg: 'bg-orange-100', text: 'text-orange-800', dot: 'bg-orange-500' },
    fatturato:          { label: 'Fatturato',          bg: 'bg-emerald-100',text: 'text-emerald-800',dot: 'bg-emerald-500' },
    chiuso:             { label: 'Chiuso',             bg: 'bg-slate-200',  text: 'text-slate-700',  dot: 'bg-slate-600' },
    sospesa:            { label: 'Sospesa',            bg: 'bg-red-100',    text: 'text-red-800',    dot: 'bg-red-500' },
};

const LIFECYCLE_ORDER = ['richiesta', 'bozza', 'rilievo_completato', 'firmato', 'in_produzione', 'fatturato', 'chiuso'];

const NORMATIVA_CONFIG = {
    EN_1090: {
        label: 'Commessa EN 1090 — Strutture metalliche',
        bg: 'bg-blue-50 border-blue-300',
        text: 'text-blue-800',
        icon: Shield,
        checklist: [
            { key: 'piano_qc', label: 'Piano di Controllo Qualita' },
            { key: 'wps_wpqr', label: 'WPS/WPQR (Procedure di saldatura)' },
            { key: 'certificati_31', label: 'Certificati materiali (3.1)' },
            { key: 'dop', label: 'Dichiarazione di Prestazione (DoP)' },
        ],
    },
    EN_13241: {
        label: 'Commessa EN 13241 — Chiusure industriali',
        bg: 'bg-amber-50 border-amber-300',
        text: 'text-amber-800',
        icon: Award,
        checklist: [
            { key: 'scheda_tecnica', label: 'Scheda tecnica prodotto' },
            { key: 'test_carichi', label: 'Test carichi / resistenza vento' },
            { key: 'dop_13241', label: 'Dichiarazione di Prestazione (DoP)' },
            { key: 'marcatura_ce', label: 'Marcatura CE' },
        ],
    },
    GENERICA: {
        label: 'Commessa Generica — Senza marcatura CE',
        bg: 'bg-slate-50 border-slate-300',
        text: 'text-slate-700',
        icon: Hammer,
        checklist: [
            { key: 'ore_registrate', label: 'Ore lavorate registrate' },
            { key: 'materiali_tracciati', label: 'Materiali utilizzati' },
            { key: 'riepilogo_costi', label: 'Riepilogo costi' },
        ],
    },
};

// Events the user can trigger manually from the hub
const AVAILABLE_EVENTS = {
    richiesta:          [{ tipo: 'RILIEVO_COMPLETATO', label: 'Rilievo Completato', icon: Ruler }, { tipo: 'PREVENTIVO_ACCETTATO', label: 'Preventivo Accettato', icon: CheckCircle2 }],
    bozza:              [{ tipo: 'RILIEVO_COMPLETATO', label: 'Rilievo Completato', icon: Ruler }, { tipo: 'PREVENTIVO_ACCETTATO', label: 'Preventivo Accettato', icon: CheckCircle2 }],
    rilievo_completato: [{ tipo: 'FIRMA_CLIENTE', label: 'Firma Cliente', icon: FileText }, { tipo: 'PREVENTIVO_ACCETTATO', label: 'Preventivo Accettato', icon: CheckCircle2 }],
    firmato:            [{ tipo: 'AVVIO_PRODUZIONE', label: 'Avvia Produzione', icon: Play }],
    in_produzione:      [{ tipo: 'FATTURA_EMESSA', label: 'Fattura Emessa', icon: Receipt }, { tipo: 'CHIUSURA_COMMESSA', label: 'Chiudi Commessa', icon: CheckCircle2 }],
    fatturato:          [{ tipo: 'CHIUSURA_COMMESSA', label: 'Chiudi Commessa', icon: CheckCircle2 }],
    chiuso:             [],
    sospesa:            [{ tipo: 'RIATTIVAZIONE', label: 'Riattiva', icon: Play }],
};

// Can always suspend (if not already)
const SUSPEND_STATES = ['bozza', 'richiesta', 'rilievo_completato', 'firmato', 'in_produzione'];

// Can close directly without certification
const CHIUSURA_DIRETTA_STATES = ['richiesta', 'bozza', 'rilievo_completato', 'firmato', 'in_produzione', 'fatturato'];

function formatEventDate(d) {
    if (!d) return '-';
    try {
        const dt = new Date(d);
        return dt.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' }) +
               ' ' + dt.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    } catch { return d; }
}

export default function CommessaHubPage() {
    const { commessaId } = useParams();
    const navigate = useNavigate();
    const [hub, setHub] = useState(null);
    const [loading, setLoading] = useState(true);
    const [emitting, setEmitting] = useState(false);
    const [linkOpen, setLinkOpen] = useState(false);
    const [linkType, setLinkType] = useState('preventivo');
    const [linkId, setLinkId] = useState('');
    const [availableModules, setAvailableModules] = useState([]);
    const [loadingModules, setLoadingModules] = useState(false);
    const [eventNote, setEventNote] = useState('');
    const [confirmEvent, setConfirmEvent] = useState(null);
    const [costAnalysis, setCostAnalysis] = useState(null);
    const [qrOpen, setQrOpen] = useState(false);
    const [closeSimpleOpen, setCloseSimpleOpen] = useState(false);
    const [closeSimpleNote, setCloseSimpleNote] = useState('');
    const [closingSimple, setClosingSimple] = useState(false);
    const [checklistStato, setChecklistStato] = useState({});
    const [vociLavoro, setVociLavoro] = useState([]);
    const [camAlert, setCamAlert] = useState(null);

    const fetchHub = useCallback(async () => {
        try {
            const data = await apiRequest(`/commesse/${commessaId}/hub`);
            setHub(data);
            setChecklistStato(data?.commessa?.checklist_stato || {});
        } catch (e) {
            toast.error('Errore caricamento commessa');
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchHub(); }, [fetchHub]);

    // Fetch CAM alert status
    useEffect(() => {
        if (!commessaId) return;
        apiRequest(`/cam/alert/${commessaId}`).then(setCamAlert).catch(() => {});
    }, [commessaId]);

    const handleChecklistToggle = async (itemKey, currentChecked) => {
        const newVal = !currentChecked;
        // Aggiornamento ottimistico
        setChecklistStato(prev => ({
            ...prev,
            [itemKey]: { ...prev[itemKey], checked: newVal },
        }));
        try {
            await apiRequest(`/commesse/${commessaId}/checklist/${itemKey}`, {
                method: 'PATCH',
                body: JSON.stringify({ checked: newVal }),
            });
        } catch (e) {
            // Ripristina stato precedente
            setChecklistStato(prev => ({
                ...prev,
                [itemKey]: { ...prev[itemKey], checked: currentChecked },
            }));
            toast.error(e.message);
        }
    };

    // Fetch cost analysis
    useEffect(() => {
        if (!commessaId) return;
        (async () => {
            try {
                const data = await apiRequest(`/costs/commessa/${commessaId}/margin-full`);
                setCostAnalysis(data);
            } catch { /* silent — no costs yet */ }
        })();
    }, [commessaId]);

    const handleEmitEvent = async (tipo) => {
        setEmitting(true);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/eventi`, {
                method: 'POST',
                body: { tipo, note: eventNote || '' },
            });
            toast.success(res.message);
            setConfirmEvent(null);
            setEventNote('');
            fetchHub();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setEmitting(false);
        }
    };

    const handleLinkModule = async () => {
        try {
            await apiRequest(`/commesse/${commessaId}/link-module`, {
                method: 'POST',
                body: { tipo: linkType, module_id: linkId },
            });
            toast.success('Modulo collegato');
            setLinkOpen(false);
            setLinkId('');
            setAvailableModules([]);
            fetchHub();
        } catch (e) {
            toast.error(e.message);
        }
    };

    const fetchAvailableModules = async (tipo) => {
        setLoadingModules(true);
        setLinkId('');
        try {
            const data = await apiRequest(`/commesse/${commessaId}/available-modules?tipo=${tipo}`);
            setAvailableModules(data.modules || []);
        } catch {
            setAvailableModules([]);
        } finally {
            setLoadingModules(false);
        }
    };

    const handleDownloadDossier = async () => {
        try {
            await downloadPdfBlob(`/commesse/${commessaId}/dossier`, `Dossier_${hub?.commessa?.numero || commessaId}.pdf`);
            toast.success('Dossier generato');
        } catch (e) { toast.error(e.message); }
    };

    const handleDownloadPacco = async () => {
        try {
            toast.info('Generazione Pacco Documenti in corso...');
            await downloadPdfBlob(`/commesse/${commessaId}/pacco-documenti`, `Pacco_Documenti_${hub?.commessa?.numero || commessaId}.pdf`);
            toast.success('Pacco Documenti generato');
        } catch (e) { toast.error(e.message); }
    };

    const handleDownloadTemplate111 = async () => {
        try {
            toast.info('Generazione Template Processo 111...');
            await downloadPdfBlob(`/template-111/pdf/${commessaId}`, `Richiesta_Qualifica_111_${hub?.commessa?.numero || commessaId}.pdf`);
            toast.success('Template generato');
        } catch (e) { toast.error(e.message); }
    };

    const [generatingDopAuto, setGeneratingDopAuto] = useState(false);
    const handleDopAutomatica = async () => {
        setGeneratingDopAuto(true);
        try {
            const res = await apiRequest(`/fascicolo-tecnico/${commessaId}/dop-automatica`, { method: 'POST' });
            toast.success(res.message);
            // Now download the PDF
            const dopId = res.dop?.dop_id;
            if (dopId) {
                await downloadPdfBlob(
                    `/fascicolo-tecnico/${commessaId}/dop-frazionata/${dopId}/pdf`,
                    `DoP_Auto_${hub?.commessa?.numero || commessaId}.pdf`
                );
            }
        } catch (e) { toast.error(e.message); }
        finally { setGeneratingDopAuto(false); }
    };

    const handleEtichettaCE1090 = async () => {
        try {
            toast.info('Generazione Etichetta CE EN 1090...');
            await downloadPdfBlob(
                `/fascicolo-tecnico/${commessaId}/etichetta-ce-1090/pdf`,
                `Etichetta_CE_1090_${hub?.commessa?.numero || commessaId}.pdf`
            );
            toast.success('Etichetta CE generata');
        } catch (e) { toast.error(e.message); }
    };

    const handleRintracciabilitaPdf = async () => {
        try {
            toast.info('Generazione Scheda Rintracciabilita...');
            await downloadPdfBlob(
                `/fascicolo-tecnico/${commessaId}/rintracciabilita-totale/pdf`,
                `Rintracciabilita_${hub?.commessa?.numero || commessaId}.pdf`
            );
            toast.success('Scheda Rintracciabilita generata');
        } catch (e) { toast.error(e.message); }
    };

    const handleCamDichiarazionePdf = async () => {
        try {
            toast.info('Generazione Dichiarazione CAM PNRR...');
            await downloadPdfBlob(
                `/cam/dichiarazione-pdf/${commessaId}`,
                `Dichiarazione_CAM_${hub?.commessa?.numero || commessaId}.pdf`
            );
            toast.success('Dichiarazione CAM generata');
        } catch (e) { toast.error(e.message); }
    };

    const handlePaccoRina = async () => {
        try {
            toast.info('Generazione Pacco RINA in corso (potrebbe richiedere qualche secondo)...');
            const API = process.env.REACT_APP_BACKEND_URL;
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}/pacco-rina`, {
                credentials: 'include',
            });
            if (!res.ok) throw new Error('Errore generazione Pacco RINA');
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Pacco_RINA_${hub?.commessa?.numero?.replace(/\//g, '-') || commessaId}.zip`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('Pacco RINA scaricato');
        } catch (e) { toast.error(e.message); }
    };

    const handleCloseSimple = async () => {
        setClosingSimple(true);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/complete-simple`, {
                method: 'POST',
                body: { note: closeSimpleNote || '' },
            });
            toast.success(res.message);
            setCloseSimpleOpen(false);
            setCloseSimpleNote('');
            fetchHub();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setClosingSimple(false);
        }
    };

    if (loading) return (
        <DashboardLayout title="Commessa">
            <div className="flex items-center justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#0055FF]" /></div>
        </DashboardLayout>
    );

    if (!hub) return (
        <DashboardLayout title="Commessa">
            <div className="text-center py-24 text-slate-500">Commessa non trovata</div>
        </DashboardLayout>
    );

    const c = hub.commessa;
    const moduli = c.moduli || {};
    const dettaglio = hub.moduli_dettaglio || {};
    const stato = c.stato || 'bozza';
    const statoStyle = STATO_STYLES[stato] || STATO_STYLES.bozza;
    const eventi = (c.eventi || []).slice().reverse(); // newest first
    const availableEvents = AVAILABLE_EVENTS[stato] || [];
    const canSuspend = SUSPEND_STATES.includes(stato);
    const canCloseDirect = CHIUSURA_DIRETTA_STATES.includes(stato);
    const fattSummary = hub.fatturazione_summary;

    return (
        <DashboardLayout title={`Commessa ${c.numero || ''}`}>
            <div className="max-w-5xl mx-auto space-y-4" data-testid="commessa-hub">
                {/* ══ HEADER: Back + Actions ══ */}
                <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                    <Button variant="ghost" size="sm" onClick={() => navigate('/planning')} data-testid="btn-back" className="text-xs sm:text-sm">
                        <ArrowLeft className="h-4 w-4 mr-1" /> <span className="hidden sm:inline">Planning</span>
                    </Button>
                    <div className="flex-1" />
                    <div className="flex gap-1.5 sm:gap-2">
                        <Button variant="outline" size="sm" onClick={() => { setLinkOpen(true); fetchAvailableModules(linkType); }} data-testid="btn-link-module" className="text-xs px-2 sm:px-3">
                            <Link2 className="h-3.5 w-3.5 sm:mr-1.5" /> <span className="hidden sm:inline">Collega Modulo</span>
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => setQrOpen(true)} data-testid="btn-qr-code" className="text-xs px-2 sm:px-3">
                            <QrCode className="h-3.5 w-3.5 sm:mr-1.5" /> <span className="hidden sm:inline">QR Code</span>
                        </Button>
                        <CommessaActionsMenu
                            commessaId={commessaId} commessaNumero={c.numero} normativaTipo={c.normativa_tipo}
                            onDownloadDossier={handleDownloadDossier} onDownloadPacco={handleDownloadPacco}
                            onDownloadTemplate111={handleDownloadTemplate111} onDopAutomatica={handleDopAutomatica}
                            onEtichettaCE={handleEtichettaCE1090} onRintracciabilita={handleRintracciabilitaPdf}
                            onCamDichiarazione={handleCamDichiarazionePdf} onPaccoRina={handlePaccoRina}
                            generatingDopAuto={generatingDopAuto}
                        />
                    </div>
                </div>

                {/* ══ 1. COMMESSA INFO — Always visible, always first ══ */}
                <Card className="border-gray-200" data-testid="commessa-info">
                    <CardContent className="p-3 sm:p-5">
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                            <div>
                                <p className="font-mono text-xs text-slate-400">{c.numero}</p>
                                <h1 className="text-lg sm:text-xl font-bold text-[#1E293B] mt-1">{c.title}</h1>
                                <p className="text-sm text-slate-500 mt-1">{c.client_name || 'Nessun cliente'}</p>
                                {c.riferimento && <p className="text-xs text-slate-400 mt-0.5">Rif: {c.riferimento}</p>}
                                {(c.classe_exc || c.tipologia_chiusura) && (
                                    <div className="flex items-center gap-2 mt-1.5">
                                        {c.classe_exc && <Badge className="bg-blue-100 text-blue-800 text-[10px]" data-testid="badge-exc">{c.classe_exc}</Badge>}
                                        {c.tipologia_chiusura && <Badge className="bg-slate-100 text-slate-700 text-[10px]" data-testid="badge-chiusura">{c.tipologia_chiusura.replace(/_/g, ' ')}</Badge>}
                                    </div>
                                )}
                            </div>
                            <div className="flex sm:flex-col items-center sm:items-end gap-2 sm:gap-1.5 sm:text-right">
                                <Badge className={`${statoStyle.bg} ${statoStyle.text} text-xs px-2.5`} data-testid="stato-badge">
                                    <span className={`w-1.5 h-1.5 rounded-full ${statoStyle.dot} inline-block mr-1.5`} />
                                    {statoStyle.label}
                                </Badge>
                                <p className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(c.value)}</p>
                                {c.deadline && <p className="text-xs text-slate-400 flex items-center gap-1"><CalendarDays className="h-3 w-3" /> {c.deadline}</p>}
                            </div>
                        </div>
                        {c.cantiere?.indirizzo && (
                            <div className="mt-3 p-2.5 bg-slate-50 rounded-lg text-xs text-slate-600">
                                <span className="font-semibold">Cantiere:</span> {c.cantiere.indirizzo}{c.cantiere.citta ? `, ${c.cantiere.citta}` : ''}{c.cantiere.contesto ? ` (${c.cantiere.contesto})` : ''}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* ══ 2. NEXT STEP — "Cosa devo fare adesso?" ══ */}
                <NextStepCard
                    stato={stato}
                    onEmitEvent={(ev) => setConfirmEvent(ev)}
                    emitting={emitting}
                />

                {/* ══ 3. LIFECYCLE BAR ══ */}
                <Card className="border-gray-200" data-testid="lifecycle-bar">
                    <CardContent className="py-3 px-5">
                        <div className="flex items-center gap-0">
                            {LIFECYCLE_ORDER.map((s, i) => {
                                const st = STATO_STYLES[s];
                                const isActive = stato === s;
                                const isPast = LIFECYCLE_ORDER.indexOf(stato) > i || stato === 'chiuso';
                                const isSuspended = stato === 'sospesa';
                                return (
                                    <div key={s} className="flex items-center flex-1">
                                        <div className="flex flex-col items-center flex-1">
                                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold transition-colors
                                                ${isActive ? `${st.dot} text-white ring-2 ring-offset-1 ring-${st.dot.replace('bg-', '')}` :
                                                  isPast && !isSuspended ? 'bg-emerald-500 text-white' :
                                                  'bg-slate-200 text-slate-400'}`}>
                                                {isPast && !isActive && !isSuspended ? <CheckCircle2 className="h-3.5 w-3.5" /> : (i + 1)}
                                            </div>
                                            <span className={`text-[9px] mt-1 text-center leading-tight ${isActive ? 'font-bold text-[#1E293B]' : 'text-slate-400'}`}>
                                                {st.label}
                                            </span>
                                        </div>
                                        {i < LIFECYCLE_ORDER.length - 1 && (
                                            <div className={`h-0.5 flex-1 ${isPast && !isSuspended ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                        {stato === 'sospesa' && (
                            <div className="mt-2 flex items-center gap-1.5 text-xs text-red-600 bg-red-50 p-2 rounded">
                                <Pause className="h-3.5 w-3.5" /> Commessa sospesa — stato precedente: {STATO_STYLES[c.stato_precedente]?.label || c.stato_precedente}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* ══ ALERTS (CAM + Compliance) — Only when relevant ══ */}
                {camAlert && camAlert.level !== 'info' && (
                    <div data-testid="cam-alert-banner" className={`rounded-lg border-2 p-3 flex items-start gap-3 ${
                        camAlert.level === 'success' ? 'bg-emerald-50 border-emerald-400' :
                        camAlert.level === 'danger' ? 'bg-red-50 border-red-400' :
                        'bg-amber-50 border-amber-400'
                    }`}>
                        <div className={`mt-0.5 ${
                            camAlert.level === 'success' ? 'text-emerald-600' :
                            camAlert.level === 'danger' ? 'text-red-600' : 'text-amber-600'
                        }`}>
                            {camAlert.level === 'success' ? <CheckCircle2 className="h-5 w-5" /> :
                             camAlert.level === 'danger' ? <XCircle className="h-5 w-5" /> :
                             <AlertTriangle className="h-5 w-5" />}
                        </div>
                        <div className="flex-1">
                            <p className={`text-sm font-bold ${
                                camAlert.level === 'success' ? 'text-emerald-800' :
                                camAlert.level === 'danger' ? 'text-red-800' : 'text-amber-800'
                            }`}>
                                CAM DM 256/2022 — {camAlert.message}
                            </p>
                            {camAlert.suggerimenti?.length > 0 && (
                                <ul className="mt-1 text-xs text-slate-600 list-disc list-inside space-y-0.5">
                                    {camAlert.suggerimenti.map((s, i) => <li key={i}>{s}</li>)}
                                </ul>
                            )}
                            {camAlert.percentuale_riciclato != null && (
                                <div className="mt-2 flex gap-3 text-xs">
                                    <span className="font-mono font-bold">{camAlert.percentuale_riciclato?.toFixed(1)}% riciclato</span>
                                    <span className="text-slate-400">|</span>
                                    <span>Soglia: {camAlert.soglia_minima}%</span>
                                    <span className="text-slate-400">|</span>
                                    <span>{camAlert.n_materiali} materiali, {camAlert.n_non_conformi} NC</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}
                <CommessaComplianceBanner commessaId={commessaId} />

                {/* ══ MAIN CONTENT: 2-column layout ══ */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Left: Core content */}
                    <div className="lg:col-span-2 space-y-4">

                        {/* ══ OBBLIGHI + COMMITTENZA ══ */}
                        <ObbrighiCommessaSection commessaId={commessaId} />

                        <Card className="border-gray-200">
                            <CardHeader className="pb-2"><CardTitle className="text-sm">Verifica Committenza</CardTitle></CardHeader>
                            <CardContent>
                                <VerificaCommittenzaSection commessaId={commessaId} />
                            </CardContent>
                        </Card>

                        {/* ══ NORMATIVA CHECKLIST ══ */}
                        {c.normativa_tipo && NORMATIVA_CONFIG[c.normativa_tipo] && (() => {
                            const nc = NORMATIVA_CONFIG[c.normativa_tipo];
                            const NIcon = nc.icon;
                            const completed = nc.checklist.filter(item => checklistStato[item.key]?.checked).length;
                            const total = nc.checklist.length;
                            const allDone = completed === total;
                            return (
                                <Card className={`border ${nc.bg}`} data-testid="normativa-banner">
                                    <CardContent className="py-3 px-5">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <NIcon className={`h-4 w-4 ${nc.text}`} />
                                                <span className={`font-semibold text-sm ${nc.text}`}>{nc.label}</span>
                                                {allDone && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                                            </div>
                                            <span className={`text-xs font-mono ${allDone ? 'text-emerald-600 font-semibold' : 'text-slate-500'}`} data-testid="checklist-progress">{completed} / {total} completati</span>
                                        </div>
                                        <div className="grid grid-cols-2 gap-1.5">
                                            {nc.checklist.map((item) => {
                                                const isChecked = !!checklistStato[item.key]?.checked;
                                                return (
                                                    <label key={item.key} className={`flex items-center gap-2 text-xs cursor-pointer rounded p-1 transition-colors ${isChecked ? 'text-emerald-700 bg-emerald-50/50' : 'text-slate-600 hover:bg-white/50'}`}>
                                                        <input type="checkbox" className="rounded border-slate-300" checked={isChecked} onChange={() => handleChecklistToggle(item.key, isChecked)} data-testid={`checklist-${item.key}`} />
                                                        <span className={isChecked ? 'line-through opacity-70' : ''}>{item.label}</span>
                                                    </label>
                                                );
                                            })}
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })()}

                        {/* ══ LINKED MODULES ══ */}
                        <Card className="border-gray-200" data-testid="linked-modules">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <BookOpen className="h-3.5 w-3.5" /> Moduli Collegati
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-3 space-y-2">
                                <ModuleCard icon={Ruler} label="Rilievo" linked={!!moduli.rilievo_id} detail={dettaglio.rilievo ? (dettaglio.rilievo.title || dettaglio.rilievo.rilievo_id) : null} onClick={() => moduli.rilievo_id && navigate(`/rilievi/${moduli.rilievo_id}`)} />
                                <ModuleCard icon={Package} label="Distinta" linked={!!moduli.distinta_id} detail={dettaglio.distinta ? (dettaglio.distinta.name || dettaglio.distinta.distinta_id) : null} onClick={() => moduli.distinta_id && navigate(`/distinte/${moduli.distinta_id}`)} />
                                <ModuleCard icon={FileText} label="Preventivo" linked={!!moduli.preventivo_id} detail={dettaglio.preventivo ? `${dettaglio.preventivo.number} — ${fmtEur(dettaglio.preventivo.totals?.total)}` : null} onClick={() => moduli.preventivo_id && navigate(`/preventivi/${moduli.preventivo_id}`)} />
                                <ModuleCard icon={Receipt} label={`Fatture (${moduli.fatture_ids?.length || 0})`} linked={(moduli.fatture_ids?.length || 0) > 0} detail={dettaglio.fatture?.map(f => f.document_number).join(', ')} onClick={() => (moduli.fatture_ids?.length > 0) && navigate('/invoices')} />
                                <ModuleCard icon={Truck} label={`DDT (${moduli.ddt_ids?.length || 0})`} linked={(moduli.ddt_ids?.length || 0) > 0} detail={dettaglio.ddt?.map(d => d.document_number).join(', ')} onClick={() => (moduli.ddt_ids?.length > 0) && navigate('/ddt')} />
                                <ModuleCard icon={Shield} label="Progetto FPC" linked={!!moduli.fpc_project_id} detail={dettaglio.fpc_project ? `${dettaglio.fpc_project.fpc_data?.execution_class || ''} — ${dettaglio.fpc_project.status}` : null} onClick={() => moduli.fpc_project_id && navigate(`/tracciabilita/progetto/${moduli.fpc_project_id}`)} />
                                <ModuleCard icon={Award} label="Certificazione CE" linked={!!moduli.certificazione_id} detail={dettaglio.certificazione ? dettaglio.certificazione.product_type : null} onClick={() => moduli.certificazione_id && navigate(`/certificazioni/${moduli.certificazione_id}`)} />
                            </CardContent>
                        </Card>

                        {/* ══ FINANCIALS: Invoicing + Cost (collapsible) ══ */}
                        {(fattSummary || (costAnalysis && (costAnalysis.costo_totale > 0 || costAnalysis.ricavo > 0))) && (
                            <Accordion type="single" collapsible defaultValue="financials">
                                <AccordionItem value="financials" className="border rounded-lg">
                                    <AccordionTrigger className="px-4 py-2.5 text-xs font-semibold text-slate-600 hover:no-underline" data-testid="accordion-financials">
                                        <span className="flex items-center gap-2"><CircleDollarSign className="h-3.5 w-3.5" /> Dati Economici</span>
                                    </AccordionTrigger>
                                    <AccordionContent className="px-4 pb-3 space-y-3">
                                        {fattSummary && (
                                            <div data-testid="invoicing-summary">
                                                <p className="text-[10px] font-semibold text-slate-400 uppercase mb-1.5">Fatturazione</p>
                                                <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                                                    <span>Fatturato: {fmtEur(fattSummary.total_invoiced)} di {fmtEur(fattSummary.total_preventivo)}</span>
                                                    <span className="font-semibold text-[#0055FF]">{fattSummary.percentage}%</span>
                                                </div>
                                                <div className="w-full bg-slate-200 rounded-full h-2">
                                                    <div className={`h-2 rounded-full transition-all ${fattSummary.percentage >= 100 ? 'bg-emerald-500' : 'bg-[#0055FF]'}`}
                                                         style={{ width: `${Math.min(fattSummary.percentage, 100)}%` }} />
                                                </div>
                                                <p className="text-xs text-slate-400 mt-1">Residuo: {fmtEur(fattSummary.remaining)}</p>
                                            </div>
                                        )}
                                        {costAnalysis && (costAnalysis.costo_totale > 0 || costAnalysis.ricavo > 0) && (
                                            <div data-testid="cost-analysis">
                                                <p className="text-[10px] font-semibold text-slate-400 uppercase mb-1.5">Analisi Margine</p>
                                                <div className="grid grid-cols-3 gap-2 sm:gap-3">
                                                    <div className="text-center p-1.5 sm:p-2 bg-blue-50 rounded-lg">
                                                        <p className="text-[9px] sm:text-[10px] text-slate-500">Ricavo</p>
                                                        <p className="text-xs sm:text-sm font-bold text-[#0055FF]">{fmtEur(costAnalysis.ricavo)}</p>
                                                    </div>
                                                    <div className="text-center p-1.5 sm:p-2 bg-red-50 rounded-lg">
                                                        <p className="text-[9px] sm:text-[10px] text-slate-500">Costi</p>
                                                        <p className="text-xs sm:text-sm font-bold text-red-600">{fmtEur(costAnalysis.costo_totale)}</p>
                                                    </div>
                                                    <div className={`text-center p-1.5 sm:p-2 rounded-lg ${costAnalysis.margine >= 0 ? 'bg-emerald-50' : 'bg-red-50'}`}>
                                                        <p className="text-[9px] sm:text-[10px] text-slate-500">Margine</p>
                                                        <p className={`text-xs sm:text-sm font-bold ${costAnalysis.margine >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                            {fmtEur(costAnalysis.margine)} <span className="text-[9px] sm:text-[10px] font-normal">({costAnalysis.margine_pct}%)</span>
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="space-y-1 text-xs mt-2">
                                                    {costAnalysis.costo_materiali_totale > 0 && <CostRow icon={Tag} color="text-blue-500" label="Materiali" value={costAnalysis.costo_materiali_totale} />}
                                                    {costAnalysis.costi_fatture_imputate > 0 && <CostRow icon={Tag} color="text-violet-500" label="Fatt. Imputate" value={costAnalysis.costi_fatture_imputate} />}
                                                    {costAnalysis.costi_oda > 0 && <CostRow icon={Tag} color="text-indigo-500" label="Ordini (OdA)" value={costAnalysis.costi_oda} />}
                                                    {costAnalysis.costi_esterni > 0 && <CostRow icon={WrenchIcon} color="text-amber-500" label="Lav. Esterne" value={costAnalysis.costi_esterni} />}
                                                    {costAnalysis.costo_personale > 0 && <CostRow icon={TrendingUp} color="text-slate-400" label={`Manodopera (${costAnalysis.ore_lavorate}h)`} value={costAnalysis.costo_personale} />}
                                                </div>
                                            </div>
                                        )}
                                    </AccordionContent>
                                </AccordionItem>
                            </Accordion>
                        )}

                        {/* ══ VOCI LAVORO ══ */}
                        <Card className="border-gray-200">
                            <CardContent className="p-4">
                                <VociLavoroSection commessaId={commessaId} onVociChange={setVociLavoro} />
                            </CardContent>
                        </Card>

                        {/* ══ TECHNICAL SECTIONS (EN 1090 — collapsible) ══ */}
                        <Accordion type="multiple" defaultValue={['rami-normativi']}>
                            <AccordionItem value="rami-normativi" className="border rounded-lg mb-3">
                                <AccordionTrigger className="px-4 py-2.5 text-xs font-semibold text-slate-600 hover:no-underline" data-testid="accordion-rami">
                                    <span className="flex items-center gap-2"><Shield className="h-3.5 w-3.5 text-blue-600" /> Rami Normativi ed Emissioni</span>
                                </AccordionTrigger>
                                <AccordionContent className="px-1 pb-1">
                                    <RamiNormativiSection commessaId={commessaId} />
                                </AccordionContent>
                            </AccordionItem>

                            <AccordionItem value="quality-sections" className="border rounded-lg mb-3">
                                <AccordionTrigger className="px-4 py-2.5 text-xs font-semibold text-slate-600 hover:no-underline" data-testid="accordion-quality">
                                    <span className="flex items-center gap-2"><Award className="h-3.5 w-3.5 text-amber-600" /> Qualita e Conformita</span>
                                </AccordionTrigger>
                                <AccordionContent className="space-y-3 px-1 pb-1">
                                    <RiesameTecnicoSection commessaId={commessaId} />
                                    <RegistroSaldaturaSection commessaId={commessaId} />
                                    <TracciabilitaMaterialiSection commessaId={commessaId} />
                                    <ReportIspezioniSection commessaId={commessaId} />
                                    <ControlloFinaleSection commessaId={commessaId} />
                                </AccordionContent>
                            </AccordionItem>
                        </Accordion>

                        {/* ══ OPS PANEL ══ */}
                        <CommessaOpsPanel commessaId={commessaId} commessaNumero={c?.numero} normativaTipo={c?.normativa_tipo} vociLavoro={vociLavoro} onRefresh={fetchHub} />
                    </div>

                    {/* Right: Actions + Timeline */}
                    <div className="space-y-4">
                        {/* Quick Actions */}
                        {(canSuspend || canCloseDirect) && (
                            <Card className="border-gray-200" data-testid="action-buttons">
                                <CardHeader className="py-2 px-4"><CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Azioni Rapide</CardTitle></CardHeader>
                                <CardContent className="px-4 pb-3 flex flex-wrap gap-2">
                                    {canCloseDirect && (
                                        <Button size="sm" variant="outline" onClick={() => setCloseSimpleOpen(true)}
                                            className="text-xs border-emerald-500 text-emerald-700 hover:bg-emerald-50 w-full justify-start"
                                            data-testid="action-CHIUSURA_DIRETTA">
                                            <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" /> Chiudi senza certificazione
                                        </Button>
                                    )}
                                    {canSuspend && (
                                        <Button size="sm" variant="outline"
                                            onClick={() => setConfirmEvent({ tipo: 'SOSPENSIONE', label: 'Sospendi Commessa', icon: Pause })}
                                            className="text-xs border-red-400 text-red-600 hover:bg-red-50 w-full justify-start"
                                            data-testid="action-SOSPENSIONE">
                                            <Pause className="h-3.5 w-3.5 mr-1.5" /> Sospendi
                                        </Button>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Timeline */}
                        <Card className="border-gray-200" data-testid="events-timeline">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <Clock className="h-3.5 w-3.5" /> Timeline ({eventi.length})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0 max-h-[500px] overflow-y-auto">
                                {eventi.length === 0 ? (
                                    <p className="text-xs text-slate-400 p-4 text-center">Nessun evento</p>
                                ) : (
                                    <div className="divide-y divide-slate-100">
                                        {eventi.map((ev, i) => (
                                            <div key={i} className="px-4 py-2.5 hover:bg-slate-50 transition-colors" data-testid={`event-${i}`}>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] font-mono font-bold text-[#0055FF]">{ev.tipo}</span>
                                                </div>
                                                {ev.note && <p className="text-xs text-slate-600 mt-0.5">{ev.note}</p>}
                                                <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                                                    <User className="h-2.5 w-2.5" /> {ev.operatore_nome || '-'}
                                                    <span>{formatEventDate(ev.data)}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Confirm Event Dialog */}
                <Dialog open={!!confirmEvent} onOpenChange={() => setConfirmEvent(null)}>
                    <DialogContent className="max-w-sm" data-testid="confirm-event-dialog">
                        <DialogHeader>
                            <DialogTitle className="text-[#1E293B]">
                                {confirmEvent?.label}
                            </DialogTitle>
                        </DialogHeader>
                        <p className="text-sm text-slate-500">
                            Vuoi emettere l'evento <strong>{confirmEvent?.tipo}</strong>? Questa azione avanzera' lo stato della commessa.
                        </p>
                        <div className="mt-2">
                            <Label className="text-xs">Nota (opzionale)</Label>
                            <Textarea
                                value={eventNote}
                                onChange={e => setEventNote(e.target.value)}
                                placeholder="Aggiungi una nota..."
                                className="mt-1 text-sm h-16"
                                data-testid="event-note"
                            />
                        </div>
                        <DialogFooter>
                            <Button variant="outline" size="sm" onClick={() => setConfirmEvent(null)}>Annulla</Button>
                            <Button size="sm" disabled={emitting}
                                className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                onClick={() => handleEmitEvent(confirmEvent.tipo)}
                                data-testid="btn-confirm-event"
                            >
                                {emitting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : null}
                                Conferma
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Link Module Dialog */}
                <Dialog open={linkOpen} onOpenChange={setLinkOpen}>
                    <DialogContent className="max-w-sm" data-testid="link-module-dialog">
                        <DialogHeader><DialogTitle>Collega Modulo</DialogTitle></DialogHeader>
                        <div className="space-y-3">
                            <div>
                                <Label className="text-xs">Tipo Modulo</Label>
                                <select
                                    value={linkType}
                                    onChange={(e) => {
                                        const tipo = e.target.value;
                                        setLinkType(tipo);
                                        fetchAvailableModules(tipo);
                                    }}
                                    className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                    data-testid="select-link-type"
                                >
                                    <option value="preventivo">Preventivo</option>
                                    <option value="fattura">Fattura</option>
                                    <option value="ddt">DDT</option>
                                    <option value="rilievo">Rilievo</option>
                                    <option value="distinta">Distinta</option>
                                    <option value="fpc_project">Progetto FPC</option>
                                    <option value="certificazione">Certificazione CE</option>
                                </select>
                            </div>
                            <div>
                                <Label className="text-xs">Seleziona Documento</Label>
                                {loadingModules ? (
                                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500 h-9">
                                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Caricamento...
                                    </div>
                                ) : availableModules.length > 0 ? (
                                    <select
                                        value={linkId}
                                        onChange={(e) => setLinkId(e.target.value)}
                                        className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                        data-testid="select-link-id"
                                    >
                                        <option value="">Seleziona...</option>
                                        {availableModules.map(m => (
                                            <option key={m.id} value={m.id}>{m.label}{m.status ? ` [${m.status}]` : ''}</option>
                                        ))}
                                    </select>
                                ) : (
                                    <p className="mt-1 text-xs text-slate-400">Nessun documento disponibile per questo tipo</p>
                                )}
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" size="sm" onClick={() => setLinkOpen(false)}>Annulla</Button>
                            <DisabledTooltip show={!linkId} reason="Seleziona un documento da collegare">
                            <Button size="sm" disabled={!linkId} onClick={handleLinkModule}
                                className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                data-testid="btn-confirm-link"
                            >
                                <Link2 className="h-3.5 w-3.5 mr-1.5" /> Collega
                            </Button>
                            </DisabledTooltip>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* QR Code Dialog — with Officina links */}
                <Dialog open={qrOpen} onOpenChange={setQrOpen}>
                    <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                <QrCode className="h-5 w-5 text-[#0055FF]" />
                                QR Code Officina
                            </DialogTitle>
                        </DialogHeader>
                        <div className="flex flex-col gap-3 py-3">
                            <p className="text-xs text-slate-500 text-center">Genera QR per l'accesso operai (Vista Officina blindata)</p>
                            {/* Main commessa officina link */}
                            <QrLinkCard
                                label={`Commessa ${c.numero}`}
                                subtitle={c.title}
                                color="bg-blue-50 border-blue-200"
                                url={`${window.location.origin}/officina/${commessaId}`}
                                testId="qr-principale"
                            />
                            {/* Links per voce */}
                            {vociLavoro.length > 0 && vociLavoro.map(v => (
                                <QrLinkCard
                                    key={v.voce_id}
                                    label={v.descrizione}
                                    subtitle={v.normativa_tipo === 'EN_1090' ? 'Strutturale' : v.normativa_tipo === 'EN_13241' ? 'Cancello' : 'Generica'}
                                    color={v.normativa_tipo === 'EN_1090' ? 'bg-blue-50 border-blue-200' : v.normativa_tipo === 'EN_13241' ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-200'}
                                    url={`${window.location.origin}/officina/${commessaId}/${v.voce_id}`}
                                    testId={`qr-voce-${v.voce_id}`}
                                />
                            ))}
                            <Separator />
                            <p className="text-[10px] text-slate-400 text-center">L'operaio accede con il PIN a 4 cifre impostato nelle impostazioni</p>
                        </div>
                    </DialogContent>
                </Dialog>
                {/* Close Simple Confirmation Dialog */}
                <Dialog open={closeSimpleOpen} onOpenChange={setCloseSimpleOpen}>
                    <DialogContent className="max-w-sm" data-testid="close-simple-dialog">
                        <DialogHeader>
                            <DialogTitle className="text-[#1E293B] flex items-center gap-2">
                                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                Chiudi senza certificazione
                            </DialogTitle>
                        </DialogHeader>
                        <p className="text-sm text-slate-500">
                            La commessa verra' chiusa direttamente saltando i passaggi di produzione e certificazione.
                            Questa azione e' indicata per lavori semplici che non richiedono certificazione.
                        </p>
                        <div className="mt-2">
                            <Label className="text-xs">Nota (opzionale)</Label>
                            <Textarea
                                value={closeSimpleNote}
                                onChange={e => setCloseSimpleNote(e.target.value)}
                                placeholder="Es: Lavoro di manutenzione completato..."
                                className="mt-1 text-sm h-16"
                                data-testid="close-simple-note"
                            />
                        </div>
                        <DialogFooter>
                            <Button variant="outline" size="sm" onClick={() => setCloseSimpleOpen(false)}>Annulla</Button>
                            <Button size="sm" disabled={closingSimple}
                                className="bg-emerald-600 text-white hover:bg-emerald-700"
                                onClick={handleCloseSimple}
                                data-testid="btn-confirm-close-simple"
                            >
                                {closingSimple ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />}
                                Chiudi Commessa
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </DashboardLayout>
    );
}

function ModuleCard({ icon: Icon, label, linked, detail, onClick }) {
    return (
        <button
            onClick={onClick}
            disabled={!linked}
            className={`w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-all border ${
                linked
                    ? 'border-slate-200 hover:border-[#0055FF] hover:bg-blue-50 cursor-pointer'
                    : 'border-dashed border-slate-200 bg-slate-50 cursor-default opacity-60'
            }`}
            data-testid={`module-${label.toLowerCase().split(' ')[0].replace('(', '')}`}
        >
            <div className={`w-8 h-8 rounded flex items-center justify-center ${linked ? 'bg-[#0055FF]/10 text-[#0055FF]' : 'bg-slate-100 text-slate-400'}`}>
                <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
                <span className={`text-xs font-semibold ${linked ? 'text-[#1E293B]' : 'text-slate-400'}`}>{label}</span>
                {detail && <p className="text-[10px] text-slate-500 truncate">{detail}</p>}
                {!linked && <p className="text-[10px] text-slate-400">Non collegato</p>}
            </div>
            {linked && <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
        </button>
    );
}

function QrLinkCard({ label, subtitle, color, url, testId }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(url).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };
    return (
        <div className={`p-3 rounded-lg border ${color} flex items-center gap-3`} data-testid={testId}>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">{label}</p>
                <p className="text-[10px] text-slate-500">{subtitle}</p>
                <p className="text-[9px] text-slate-400 truncate mt-0.5 font-mono">{url}</p>
            </div>
            <button
                onClick={handleCopy}
                className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${copied ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}`}
                data-testid={`${testId}-copy`}
            >
                {copied ? 'Copiato' : 'Copia'}
            </button>
        </div>
    );
}
