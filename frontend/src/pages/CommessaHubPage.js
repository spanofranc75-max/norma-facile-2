/**
 * CommessaHubPage — Central hub for a single commessa.
 * Shows lifecycle state, events timeline, linked modules, and actions.
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
    ArrowLeft, FileText, Receipt, Truck, Shield, Award,
    Ruler, Package, Play, Pause, CheckCircle2, XCircle,
    Clock, User, ChevronRight, Download, Plus, Link2,
    AlertTriangle, Loader2, BookOpen, CalendarDays, TrendingUp,
    CircleDollarSign, Tag, Wrench as WrenchIcon,
} from 'lucide-react';
import CommessaOpsPanel from '../components/CommessaOpsPanel';
import { DisabledTooltip } from '../components/DisabledTooltip';

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

    const fetchHub = useCallback(async () => {
        try {
            const data = await apiRequest(`/commesse/${commessaId}/hub`);
            setHub(data);
        } catch (e) {
            toast.error('Errore caricamento commessa');
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchHub(); }, [fetchHub]);

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
            const res = await fetch(`${API}/api/commesse/${commessaId}/dossier`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) throw new Error('Errore generazione dossier');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Dossier_${hub?.commessa?.numero || commessaId}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Dossier generato');
        } catch (e) {
            toast.error(e.message);
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
    const fattSummary = hub.fatturazione_summary;

    return (
        <DashboardLayout title={`Commessa ${c.numero || ''}`}>
            <div className="max-w-5xl mx-auto space-y-4" data-testid="commessa-hub">
                {/* Header */}
                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="sm" onClick={() => navigate('/planning')} data-testid="btn-back">
                        <ArrowLeft className="h-4 w-4 mr-1" /> Planning
                    </Button>
                    <div className="flex-1" />
                    <Button variant="outline" size="sm" onClick={() => { setLinkOpen(true); fetchAvailableModules(linkType); }} data-testid="btn-link-module">
                        <Link2 className="h-3.5 w-3.5 mr-1.5" /> Collega Modulo
                    </Button>
                    <Button size="sm" onClick={handleDownloadDossier} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-dossier">
                        <Download className="h-3.5 w-3.5 mr-1.5" /> Dossier PDF
                    </Button>
                </div>

                {/* Commessa Info Card */}
                <Card className="border-gray-200" data-testid="commessa-info">
                    <CardContent className="p-5">
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="font-mono text-xs text-slate-400">{c.numero}</p>
                                <h1 className="text-xl font-bold text-[#1E293B] mt-1">{c.title}</h1>
                                <p className="text-sm text-slate-500 mt-1">{c.client_name || 'Nessun cliente'}</p>
                                {c.riferimento && <p className="text-xs text-slate-400 mt-0.5">Rif: {c.riferimento}</p>}
                                {(c.classe_exc || c.tipologia_chiusura) && (
                                    <div className="flex items-center gap-2 mt-1.5">
                                        {c.classe_exc && <Badge className="bg-blue-100 text-blue-800 text-[10px]" data-testid="badge-exc">{c.classe_exc}</Badge>}
                                        {c.tipologia_chiusura && <Badge className="bg-slate-100 text-slate-700 text-[10px]" data-testid="badge-chiusura">{c.tipologia_chiusura.replace(/_/g, ' ')}</Badge>}
                                    </div>
                                )}
                            </div>
                            <div className="text-right space-y-1.5">
                                <Badge className={`${statoStyle.bg} ${statoStyle.text} text-xs px-2.5`} data-testid="stato-badge">
                                    <span className={`w-1.5 h-1.5 rounded-full ${statoStyle.dot} inline-block mr-1.5`} />
                                    {statoStyle.label}
                                </Badge>
                                <p className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(c.value)}</p>
                                {c.deadline && <p className="text-xs text-slate-400 flex items-center gap-1 justify-end"><CalendarDays className="h-3 w-3" /> {c.deadline}</p>}
                            </div>
                        </div>

                        {/* Cantiere */}
                        {c.cantiere?.indirizzo && (
                            <div className="mt-3 p-2.5 bg-slate-50 rounded-lg text-xs text-slate-600">
                                <span className="font-semibold">Cantiere:</span> {c.cantiere.indirizzo}{c.cantiere.citta ? `, ${c.cantiere.citta}` : ''}{c.cantiere.contesto ? ` (${c.cantiere.contesto})` : ''}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Lifecycle State Machine Bar */}
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

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Left: Modules + Invoicing */}
                    <div className="lg:col-span-2 space-y-4">

                        {/* Action Buttons */}
                        {(availableEvents.length > 0 || canSuspend) && (
                            <Card className="border-gray-200" data-testid="action-buttons">
                                <CardHeader className="py-2 px-4"><CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Azioni Disponibili</CardTitle></CardHeader>
                                <CardContent className="px-4 pb-3 flex flex-wrap gap-2">
                                    {availableEvents.map(ev => (
                                        <Button key={ev.tipo} size="sm" variant="outline"
                                            onClick={() => setConfirmEvent(ev)}
                                            className="text-xs border-[#0055FF] text-[#0055FF] hover:bg-blue-50"
                                            data-testid={`action-${ev.tipo}`}
                                        >
                                            <ev.icon className="h-3.5 w-3.5 mr-1.5" /> {ev.label}
                                        </Button>
                                    ))}
                                    {canSuspend && (
                                        <Button size="sm" variant="outline"
                                            onClick={() => setConfirmEvent({ tipo: 'SOSPENSIONE', label: 'Sospendi Commessa', icon: Pause })}
                                            className="text-xs border-red-400 text-red-600 hover:bg-red-50"
                                            data-testid="action-SOSPENSIONE"
                                        >
                                            <Pause className="h-3.5 w-3.5 mr-1.5" /> Sospendi
                                        </Button>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Linked Modules */}
                        <Card className="border-gray-200" data-testid="linked-modules">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <BookOpen className="h-3.5 w-3.5" /> Moduli Collegati
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-3 space-y-2">
                                <ModuleCard
                                    icon={Ruler} label="Rilievo" linked={!!moduli.rilievo_id}
                                    detail={dettaglio.rilievo ? (dettaglio.rilievo.title || dettaglio.rilievo.rilievo_id) : null}
                                    onClick={() => moduli.rilievo_id && navigate(`/rilievi/${moduli.rilievo_id}`)}
                                />
                                <ModuleCard
                                    icon={Package} label="Distinta" linked={!!moduli.distinta_id}
                                    detail={dettaglio.distinta ? (dettaglio.distinta.name || dettaglio.distinta.distinta_id) : null}
                                    onClick={() => moduli.distinta_id && navigate(`/distinte/${moduli.distinta_id}`)}
                                />
                                <ModuleCard
                                    icon={FileText} label="Preventivo" linked={!!moduli.preventivo_id}
                                    detail={dettaglio.preventivo ? `${dettaglio.preventivo.number} — ${fmtEur(dettaglio.preventivo.totals?.total)}` : null}
                                    onClick={() => moduli.preventivo_id && navigate(`/preventivi/${moduli.preventivo_id}`)}
                                />
                                <ModuleCard
                                    icon={Receipt} label={`Fatture (${moduli.fatture_ids?.length || 0})`}
                                    linked={(moduli.fatture_ids?.length || 0) > 0}
                                    detail={dettaglio.fatture?.map(f => f.document_number).join(', ')}
                                    onClick={() => (moduli.fatture_ids?.length > 0) && navigate('/invoices')}
                                />
                                <ModuleCard
                                    icon={Truck} label={`DDT (${moduli.ddt_ids?.length || 0})`}
                                    linked={(moduli.ddt_ids?.length || 0) > 0}
                                    detail={dettaglio.ddt?.map(d => d.document_number).join(', ')}
                                    onClick={() => (moduli.ddt_ids?.length > 0) && navigate('/ddt')}
                                />
                                <ModuleCard
                                    icon={Shield} label="Progetto FPC" linked={!!moduli.fpc_project_id}
                                    detail={dettaglio.fpc_project ? `${dettaglio.fpc_project.fpc_data?.execution_class || ''} — ${dettaglio.fpc_project.status}` : null}
                                    onClick={() => moduli.fpc_project_id && navigate(`/tracciabilita/progetto/${moduli.fpc_project_id}`)}
                                />
                                <ModuleCard
                                    icon={Award} label="Certificazione CE" linked={!!moduli.certificazione_id}
                                    detail={dettaglio.certificazione ? dettaglio.certificazione.product_type : null}
                                    onClick={() => moduli.certificazione_id && navigate(`/certificazioni/${moduli.certificazione_id}`)}
                                />
                            </CardContent>
                        </Card>

                        {/* Invoicing Summary */}
                        {fattSummary && (
                            <Card className="border-gray-200" data-testid="invoicing-summary">
                                <CardHeader className="py-2 px-4"><CardTitle className="text-xs font-semibold text-slate-500">Stato Fatturazione</CardTitle></CardHeader>
                                <CardContent className="px-4 pb-3">
                                    <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                                        <span>Fatturato: {fmtEur(fattSummary.total_invoiced)} di {fmtEur(fattSummary.total_preventivo)}</span>
                                        <span className="font-semibold text-[#0055FF]">{fattSummary.percentage}%</span>
                                    </div>
                                    <div className="w-full bg-slate-200 rounded-full h-2">
                                        <div className={`h-2 rounded-full transition-all ${fattSummary.percentage >= 100 ? 'bg-emerald-500' : 'bg-[#0055FF]'}`}
                                             style={{ width: `${Math.min(fattSummary.percentage, 100)}%` }} />
                                    </div>
                                    <p className="text-xs text-slate-400 mt-1">Residuo: {fmtEur(fattSummary.remaining)}</p>
                                </CardContent>
                            </Card>
                        )}

                        {/* Operational Panels: Approvvigionamento, Produzione, C/L, Repository */}
                        <CommessaOpsPanel commessaId={commessaId} commessaNumero={c?.numero} onRefresh={fetchHub} />
                    </div>

                    {/* Right: Timeline */}
                    <div>
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
