/**
 * CommessaOpsPanel — Operational panels for a commessa.
 * Approvvigionamento, Produzione, Conto Lavoro, Repository Documenti.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Combobox } from '../components/ui/combobox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import {
    ShoppingCart, Package, Truck, Factory, Paintbrush, FileUp,
    Play, CheckCircle2, Clock, AlertTriangle, Plus, Trash2,
    Download, Eye, Loader2, Sparkles, ChevronDown, ChevronUp, FileText,
    Mail, MailCheck, FileSearch,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const STATO_COLORS = {
    da_fare: 'bg-slate-100 text-slate-600', in_corso: 'bg-blue-100 text-blue-700',
    completato: 'bg-emerald-100 text-emerald-700', inviata: 'bg-blue-100 text-blue-700',
    ricevuta: 'bg-amber-100 text-amber-700', accettata: 'bg-emerald-100 text-emerald-700',
    rifiutata: 'bg-red-100 text-red-700', inviato: 'bg-blue-100 text-blue-700',
    confermato: 'bg-emerald-100 text-emerald-700', consegnato: 'bg-emerald-100 text-emerald-700',
    da_verificare: 'bg-amber-100 text-amber-700', verificato: 'bg-emerald-100 text-emerald-700',
    da_inviare: 'bg-slate-100 text-slate-600', in_lavorazione: 'bg-blue-100 text-blue-700',
    rientrato: 'bg-amber-100 text-amber-700',
};

function StatoBadge({ stato }) {
    return <Badge className={`text-[9px] ${STATO_COLORS[stato] || 'bg-slate-100 text-slate-600'}`}>{(stato || '').replace(/_/g, ' ')}</Badge>;
}

function Section({ title, icon: Icon, count, defaultOpen, children }) {
    const [open, setOpen] = useState(defaultOpen || false);
    return (
        <Card className="border-gray-200">
            <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors rounded-t-lg" data-testid={`section-${title.toLowerCase().replace(/\s/g, '-')}`}>
                <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-[#0055FF]" />
                    <span className="text-sm font-semibold text-[#1E293B]">{title}</span>
                    {count > 0 && <Badge className="bg-[#0055FF]/10 text-[#0055FF] text-[9px]">{count}</Badge>}
                </div>
                {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
            </button>
            {open && <CardContent className="pt-0 pb-3 px-4">{children}</CardContent>}
        </Card>
    );
}

export default function CommessaOpsPanel({ commessaId, commessaNumero, onRefresh }) {
    const [ops, setOps] = useState(null);
    const [docs, setDocs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [fornitori, setFornitori] = useState([]);
    const fileRef = useRef();

    // Dialog states
    const [rdpOpen, setRdpOpen] = useState(false);
    const [odaOpen, setOdaOpen] = useState(false);
    const [arrivoOpen, setArrivoOpen] = useState(false);
    const [clOpen, setClOpen] = useState(false);
    const [uploadType, setUploadType] = useState('altro');
    const [parsing, setParsing] = useState(null); // doc_id being parsed

    // Empty line templates
    const emptyRdpLine = () => ({ id: `l${Date.now()}`, descrizione: '', quantita: 1, unita_misura: 'kg', richiede_cert_31: false });
    const emptyOdaLine = () => ({ id: `l${Date.now()}`, descrizione: '', quantita: 1, unita_misura: 'kg', prezzo_unitario: 0, richiede_cert_31: false });

    // Form states with righe
    const [rdpForm, setRdpForm] = useState({ fornitore_nome: '', fornitore_id: '', righe: [emptyRdpLine()], note: '' });
    const [odaForm, setOdaForm] = useState({ fornitore_nome: '', fornitore_id: '', righe: [emptyOdaLine()], note: '' });
    const [arrivoForm, setArrivoForm] = useState({ ddt_fornitore: '', ordine_id: '', note: '' });
    const [clForm, setClForm] = useState({ tipo: 'verniciatura', fornitore_nome: '', fornitore_id: '' });

    // PDF Preview and Email states (must be before any conditional return)
    const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
    const [pdfPreviewTitle, setPdfPreviewTitle] = useState('');
    const [sendingEmail, setSendingEmail] = useState(null); // Track which item is sending email

    // Load fornitori from anagrafica
    useEffect(() => {
        apiRequest('/clients/?client_type=fornitore&limit=100').then(data => {
            setFornitori((data.clients || []).map(c => ({ id: c.client_id, nome: c.business_name })));
        }).catch(() => {});
    }, []);

    const fetchData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const [o, d] = await Promise.all([
                apiRequest(`/commesse/${commessaId}/ops`),
                apiRequest(`/commesse/${commessaId}/documenti`),
            ]);
            setOps(o);
            setDocs(d.documents || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    if (loading) return <div className="text-center py-6 text-sm text-slate-400">Caricamento dati operativi...</div>;

    const approv = ops?.approvvigionamento || { richieste: [], ordini: [], arrivi: [] };
    const fasi = ops?.fasi_produzione || [];
    const progPct = ops?.produzione_progress?.percentage || 0;
    const cl = ops?.conto_lavoro || [];

    // ── Handlers ──
    
    // RdP line helpers
    const addRdpLine = () => setRdpForm(f => ({ ...f, righe: [...f.righe, emptyRdpLine()] }));
    const removeRdpLine = (idx) => setRdpForm(f => ({ ...f, righe: f.righe.filter((_, i) => i !== idx) }));
    const updateRdpLine = (idx, field, value) => setRdpForm(f => {
        const righe = [...f.righe];
        righe[idx] = { ...righe[idx], [field]: value };
        return { ...f, righe };
    });

    // OdA line helpers
    const addOdaLine = () => setOdaForm(f => ({ ...f, righe: [...f.righe, emptyOdaLine()] }));
    const removeOdaLine = (idx) => setOdaForm(f => ({ ...f, righe: f.righe.filter((_, i) => i !== idx) }));
    const updateOdaLine = (idx, field, value) => setOdaForm(f => {
        const righe = [...f.righe];
        righe[idx] = { ...righe[idx], [field]: value };
        return { ...f, righe };
    });

    // Calculate OdA total
    const odaTotale = odaForm.righe.reduce((sum, r) => sum + (parseFloat(r.quantita) || 0) * (parseFloat(r.prezzo_unitario) || 0), 0);

    const handleCreateRdP = async () => {
        if (rdpForm.righe.filter(r => r.descrizione.trim()).length === 0) {
            toast.error('Inserisci almeno una riga');
            return;
        }
        try {
            const payload = {
                ...rdpForm,
                righe: rdpForm.righe.filter(r => r.descrizione.trim()).map(r => ({
                    descrizione: r.descrizione,
                    quantita: parseFloat(r.quantita) || 1,
                    unita_misura: r.unita_misura,
                    richiede_cert_31: r.richiede_cert_31,
                })),
            };
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/richieste`, { method: 'POST', body: payload });
            toast.success('RdP inviata');
            setRdpOpen(false);
            setRdpForm({ fornitore_nome: '', fornitore_id: '', righe: [emptyRdpLine()], note: '' });
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateRdP = async (rdpId, stato, importo) => {
        const form = new FormData();
        form.append('stato', stato);
        if (importo) form.append('importo', importo);
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}`, {
                method: 'PUT', body: form,
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) throw new Error('Errore');
            toast.success(`RdP → ${stato}`);
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleCreateOdA = async () => {
        if (odaForm.righe.filter(r => r.descrizione.trim()).length === 0) {
            toast.error('Inserisci almeno una riga');
            return;
        }
        try {
            const payload = {
                ...odaForm,
                righe: odaForm.righe.filter(r => r.descrizione.trim()).map(r => ({
                    descrizione: r.descrizione,
                    quantita: parseFloat(r.quantita) || 1,
                    unita_misura: r.unita_misura,
                    prezzo_unitario: parseFloat(r.prezzo_unitario) || 0,
                    richiede_cert_31: r.richiede_cert_31,
                })),
                importo_totale: odaTotale,
            };
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/ordini`, { method: 'POST', body: payload });
            toast.success('Ordine emesso');
            setOdaOpen(false);
            setOdaForm({ fornitore_nome: '', fornitore_id: '', righe: [emptyOdaLine()], note: '' });
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateOrdine = async (ordineId, stato) => {
        const form = new FormData();
        form.append('stato', stato);
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}`, {
                method: 'PUT', body: form,
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) throw new Error('Errore');
            toast.success(`Ordine → ${stato}`);
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleCreateArrivo = async () => {
        try {
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/arrivi`, { method: 'POST', body: arrivoForm });
            toast.success('Arrivo registrato');
            setArrivoOpen(false);
            setArrivoForm({ ddt_fornitore: '', ordine_id: '', note: '' });
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleVerificaArrivo = async (arrivoId) => {
        try {
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/arrivi/${arrivoId}/verifica`, { method: 'PUT' });
            toast.success('Arrivo verificato');
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleInitProduzione = async () => {
        try {
            await apiRequest(`/commesse/${commessaId}/produzione/init`, { method: 'POST' });
            toast.success('Fasi produzione inizializzate');
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateFase = async (tipo, stato) => {
        try {
            await apiRequest(`/commesse/${commessaId}/produzione/${tipo}`, { method: 'PUT', body: { stato } });
            toast.success(`Fase aggiornata`);
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleCreateCL = async () => {
        try {
            await apiRequest(`/commesse/${commessaId}/conto-lavoro`, { method: 'POST', body: clForm });
            toast.success('Conto lavoro creato');
            setClOpen(false);
            setClForm({ tipo: 'verniciatura', fornitore_nome: '' });
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateCL = async (clId, stato) => {
        try {
            await apiRequest(`/commesse/${commessaId}/conto-lavoro/${clId}`, { method: 'PUT', body: { stato } });
            toast.success(`C/L → ${stato}`);
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUploadDoc = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const form = new FormData();
        form.append('file', file);
        form.append('tipo', uploadType);
        form.append('note', '');
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/documenti`, {
                method: 'POST', body: form,
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) throw new Error('Errore upload');
            const data = await res.json();
            toast.success(data.message);
            fetchData(); onRefresh?.();
        } catch (err) { toast.error(err.message); }
        if (fileRef.current) fileRef.current.value = '';
    };

    const handleParseAI = async (docId) => {
        setParsing(docId);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/documenti/${docId}/parse-certificato`, { method: 'POST' });
            const m = res.metadata;
            toast.success(`Colata: ${m?.numero_colata || '?'} — ${m?.qualita_acciaio || '?'} — ${m?.fornitore || '?'}`);
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); } finally { setParsing(null); }
    };

    const handleDownloadDoc = async (docId, nome) => {
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/documenti/${docId}/download`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) throw new Error('Errore download');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = nome; a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    const handleDeleteDoc = async (docId) => {
        try {
            await apiRequest(`/commesse/${commessaId}/documenti/${docId}`, { method: 'DELETE' });
            toast.success('Documento eliminato');
            fetchData();
        } catch (e) { toast.error(e.message); }
    };

    // PDF Preview handlers
    const handlePreviewRdpPdf = async (rdpId) => {
        try {
            const url = `${API}/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/pdf`;
            setPdfPreviewTitle(`Anteprima RdP ${rdpId}`);
            setPdfPreviewUrl(url);
        } catch (e) { toast.error(e.message); }
    };

    const handlePreviewOdaPdf = async (ordineId) => {
        try {
            const url = `${API}/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/pdf`;
            setPdfPreviewTitle(`Anteprima OdA ${ordineId}`);
            setPdfPreviewUrl(url);
        } catch (e) { toast.error(e.message); }
    };

    const handleSendRdpEmail = async (rdpId) => {
        setSendingEmail(rdpId);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/send-email`, { method: 'POST' });
            toast.success(res.message || 'Email inviata');
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); } finally { setSendingEmail(null); }
    };

    const handleSendOdaEmail = async (ordineId) => {
        setSendingEmail(ordineId);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/send-email`, { method: 'POST' });
            toast.success(res.message || 'Email inviata');
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); } finally { setSendingEmail(null); }
    };

    return (
        <div className="space-y-3" data-testid="commessa-ops">
            {/* ── APPROVVIGIONAMENTO ── */}
            <Section title="Approvvigionamento" icon={ShoppingCart} count={(approv.richieste?.length || 0) + (approv.ordini?.length || 0)} defaultOpen>
                <div className="space-y-3">
                    <div className="flex gap-2 flex-wrap">
                        <Button size="sm" variant="outline" onClick={() => setRdpOpen(true)} className="text-xs" data-testid="btn-new-rdp">
                            <Plus className="h-3 w-3 mr-1" /> RdP Fornitore
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setOdaOpen(true)} className="text-xs" data-testid="btn-new-oda">
                            <Plus className="h-3 w-3 mr-1" /> Ordine (OdA)
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setArrivoOpen(true)} className="text-xs" data-testid="btn-new-arrivo">
                            <Package className="h-3 w-3 mr-1" /> Registra Arrivo
                        </Button>
                    </div>

                    {/* Richieste Preventivo */}
                    {(approv.richieste || []).map(r => (
                        <div key={r.rdp_id} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`rdp-${r.rdp_id}`}>
                            <ShoppingCart className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium truncate">RdP → {r.fornitore_nome}</span>
                                    {/* Email status badge */}
                                    {r.email_sent ? (
                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded text-[9px] font-medium" title={`Inviata a ${r.email_sent_to}`}>
                                            <MailCheck className="h-2.5 w-2.5" /> Inviata
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[9px] font-medium">
                                            <Mail className="h-2.5 w-2.5" /> Bozza
                                        </span>
                                    )}
                                </div>
                                {r.righe?.length > 0 && (
                                    <div className="text-[10px] text-slate-500 mt-0.5">
                                        {r.righe.length} righe — {r.righe.filter(x => x.richiede_cert_31).length > 0 && `${r.righe.filter(x => x.richiede_cert_31).length} cert. 3.1`}
                                    </div>
                                )}
                            </div>
                            <StatoBadge stato={r.stato} />
                            {r.importo_proposto && <span className="font-mono text-[10px]">{fmtEur(r.importo_proposto)}</span>}
                            {/* Action buttons */}
                            <div className="flex items-center gap-1">
                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handlePreviewRdpPdf(r.rdp_id)} title="Anteprima PDF">
                                    <FileSearch className="h-3.5 w-3.5 text-blue-600" />
                                </Button>
                                {!r.email_sent && (
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 w-6 p-0"
                                        onClick={() => handleSendRdpEmail(r.rdp_id)}
                                        disabled={sendingEmail === r.rdp_id}
                                        title="Invia Email"
                                    >
                                        {sendingEmail === r.rdp_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5 text-amber-600" />}
                                    </Button>
                                )}
                                {r.stato === 'inviata' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateRdP(r.rdp_id, 'ricevuta')}>Ricevuta</Button>}
                                {r.stato === 'ricevuta' && (
                                    <>
                                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateRdP(r.rdp_id, 'accettata')}>Accetta</Button>
                                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-red-600" onClick={() => handleUpdateRdP(r.rdp_id, 'rifiutata')}>Rifiuta</Button>
                                    </>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Ordini */}
                    {(approv.ordini || []).map(o => (
                        <div key={o.ordine_id} className="flex items-center gap-2 p-2 bg-blue-50 rounded text-xs" data-testid={`oda-${o.ordine_id}`}>
                            <Truck className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium truncate">OdA → {o.fornitore_nome}</span>
                                    {/* Email status badge */}
                                    {o.email_sent ? (
                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded text-[9px] font-medium" title={`Inviata a ${o.email_sent_to}`}>
                                            <MailCheck className="h-2.5 w-2.5" /> Inviata
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[9px] font-medium">
                                            <Mail className="h-2.5 w-2.5" /> Bozza
                                        </span>
                                    )}
                                </div>
                                {o.righe?.length > 0 && (
                                    <div className="text-[10px] text-slate-500 mt-0.5">
                                        {o.righe.length} righe — {o.righe.filter(x => x.richiede_cert_31).length > 0 && `${o.righe.filter(x => x.richiede_cert_31).length} cert. 3.1`}
                                    </div>
                                )}
                            </div>
                            <span className="font-mono text-[10px] font-semibold">{fmtEur(o.importo_totale)}</span>
                            <StatoBadge stato={o.stato} />
                            {/* Action buttons */}
                            <div className="flex items-center gap-1">
                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handlePreviewOdaPdf(o.ordine_id)} title="Anteprima PDF">
                                    <FileSearch className="h-3.5 w-3.5 text-emerald-600" />
                                </Button>
                                {!o.email_sent && (
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 w-6 p-0"
                                        onClick={() => handleSendOdaEmail(o.ordine_id)}
                                        disabled={sendingEmail === o.ordine_id}
                                        title="Invia Email"
                                    >
                                        {sendingEmail === o.ordine_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5 text-amber-600" />}
                                    </Button>
                                )}
                                {o.stato === 'inviato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateOrdine(o.ordine_id, 'confermato')}>Confermato</Button>}
                            </div>
                        </div>
                    ))}

                    {/* Arrivi */}
                    {(approv.arrivi || []).map(a => (
                        <div key={a.arrivo_id} className="flex items-center gap-2 p-2 bg-amber-50 rounded text-xs" data-testid={`arrivo-${a.arrivo_id}`}>
                            <Package className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                            <span className="font-medium flex-1 truncate">Arrivo DDT: {a.ddt_fornitore || '-'}</span>
                            <StatoBadge stato={a.stato} />
                            {a.stato === 'da_verificare' && (
                                <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleVerificaArrivo(a.arrivo_id)}>
                                    <CheckCircle2 className="h-3 w-3 mr-0.5" /> Verifica
                                </Button>
                            )}
                        </div>
                    ))}
                </div>
            </Section>

            {/* ── PRODUZIONE ── */}
            <Section title="Produzione" icon={Factory} count={fasi.length}>
                {fasi.length === 0 ? (
                    <Button size="sm" onClick={handleInitProduzione} className="bg-[#0055FF] text-white text-xs" data-testid="btn-init-prod">
                        <Play className="h-3.5 w-3.5 mr-1.5" /> Inizializza Fasi Produzione
                    </Button>
                ) : (
                    <div className="space-y-1.5">
                        {/* Progress bar */}
                        <div className="flex items-center gap-2 mb-2">
                            <div className="flex-1 bg-slate-200 rounded-full h-2">
                                <div className="bg-[#0055FF] h-2 rounded-full transition-all" style={{ width: `${progPct}%` }} />
                            </div>
                            <span className="text-xs font-mono font-semibold text-[#0055FF]">{progPct}%</span>
                        </div>
                        {fasi.map(f => (
                            <div key={f.tipo} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`fase-${f.tipo}`}>
                                <span className="font-medium flex-1">{f.label || f.tipo}</span>
                                <StatoBadge stato={f.stato} />
                                {f.stato === 'da_fare' && (
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600" onClick={() => handleUpdateFase(f.tipo, 'in_corso')}>
                                        <Play className="h-3 w-3 mr-0.5" /> Avvia
                                    </Button>
                                )}
                                {f.stato === 'in_corso' && (
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateFase(f.tipo, 'completato')}>
                                        <CheckCircle2 className="h-3 w-3 mr-0.5" /> Completa
                                    </Button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </Section>

            {/* ── CONTO LAVORO ── */}
            <Section title="Conto Lavoro" icon={Paintbrush} count={cl.length}>
                <div className="space-y-2">
                    <Button size="sm" variant="outline" onClick={() => setClOpen(true)} className="text-xs" data-testid="btn-new-cl">
                        <Plus className="h-3 w-3 mr-1" /> Nuovo C/L
                    </Button>
                    {cl.map(c => (
                        <div key={c.cl_id} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`cl-${c.cl_id}`}>
                            <Paintbrush className="h-3.5 w-3.5 text-purple-500 shrink-0" />
                            <span className="font-medium flex-1 truncate capitalize">{c.tipo} → {c.fornitore_nome}</span>
                            <StatoBadge stato={c.stato} />
                            {c.stato === 'da_inviare' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600" onClick={() => handleUpdateCL(c.cl_id, 'inviato')}>Invia</Button>}
                            {c.stato === 'inviato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-amber-600" onClick={() => handleUpdateCL(c.cl_id, 'in_lavorazione')}>In Lav.</Button>}
                            {c.stato === 'in_lavorazione' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateCL(c.cl_id, 'rientrato')}>Rientrato</Button>}
                            {c.stato === 'rientrato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateCL(c.cl_id, 'verificato')}>Verifica</Button>}
                        </div>
                    ))}
                </div>
            </Section>

            {/* ── REPOSITORY DOCUMENTI ── */}
            <Section title="Repository Documenti" icon={FileUp} count={docs.length} defaultOpen>
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <Select value={uploadType} onValueChange={setUploadType}>
                            <SelectTrigger className="w-44 h-8 text-xs"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="certificato_31">Certificato 3.1</SelectItem>
                                <SelectItem value="conferma_ordine">Conferma Ordine</SelectItem>
                                <SelectItem value="disegno">Disegno</SelectItem>
                                <SelectItem value="certificato_verniciatura">Cert. Verniciatura</SelectItem>
                                <SelectItem value="certificato_zincatura">Cert. Zincatura</SelectItem>
                                <SelectItem value="ddt_fornitore">DDT Fornitore</SelectItem>
                                <SelectItem value="foto">Foto</SelectItem>
                                <SelectItem value="altro">Altro</SelectItem>
                            </SelectContent>
                        </Select>
                        <input ref={fileRef} type="file" className="hidden" onChange={handleUploadDoc} data-testid="file-input" />
                        <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} className="text-xs" data-testid="btn-upload-doc">
                            <FileUp className="h-3 w-3 mr-1" /> Carica File
                        </Button>
                    </div>
                    {docs.map(d => (
                        <div key={d.doc_id} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`doc-${d.doc_id}`}>
                            <FileUp className="h-3.5 w-3.5 text-[#0055FF] shrink-0" />
                            <div className="flex-1 min-w-0">
                                <span className="font-medium truncate block">{d.nome_file}</span>
                                <span className="text-[10px] text-slate-400">{d.tipo?.replace(/_/g, ' ')} — {(d.size_bytes / 1024).toFixed(0)}KB</span>
                                {d.metadata_estratti?.numero_colata && (
                                    <span className="block text-[10px] text-emerald-600 font-mono mt-0.5">
                                        Colata: {d.metadata_estratti.numero_colata} | {d.metadata_estratti.qualita_acciaio} | {d.metadata_estratti.fornitore}
                                    </span>
                                )}
                            </div>
                            {d.tipo === 'certificato_31' && !d.metadata_estratti && (
                                <Button size="sm" variant="ghost" className="h-7 text-[10px] text-[#0055FF]" disabled={parsing === d.doc_id}
                                    onClick={() => handleParseAI(d.doc_id)} data-testid={`btn-parse-${d.doc_id}`}>
                                    {parsing === d.doc_id ? <Loader2 className="h-3 w-3 animate-spin mr-0.5" /> : <Sparkles className="h-3 w-3 mr-0.5" />}
                                    AI OCR
                                </Button>
                            )}
                            <Button size="sm" variant="ghost" className="h-7 px-1.5" onClick={() => handleDownloadDoc(d.doc_id, d.nome_file)}>
                                <Download className="h-3 w-3" />
                            </Button>
                            <Button size="sm" variant="ghost" className="h-7 px-1.5 text-red-400 hover:text-red-600" onClick={() => handleDeleteDoc(d.doc_id)}>
                                <Trash2 className="h-3 w-3" />
                            </Button>
                        </div>
                    ))}
                </div>
            </Section>

            {/* ── Dialogs ── */}
            {/* RdP Dialog - Full featured with line items */}
            <Dialog open={rdpOpen} onOpenChange={setRdpOpen}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-blue-600" />
                            Nuova Richiesta di Preventivo (RdP)
                        </DialogTitle>
                        {commessaNumero && (
                            <DialogDescription>
                                Riferimento: Commessa <span className="font-semibold">{commessaNumero}</span>
                            </DialogDescription>
                        )}
                    </DialogHeader>
                    <div className="space-y-4">
                        {/* Fornitore selector */}
                        <div>
                            <Label className="text-sm font-medium">Fornitore *</Label>
                            <Combobox
                                options={fornitori.map(f => ({ value: f.id, label: f.nome }))}
                                value={rdpForm.fornitore_id}
                                onValueChange={(val) => {
                                    const f = fornitori.find(x => x.id === val);
                                    setRdpForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                }}
                                placeholder="Seleziona fornitore..."
                                searchPlaceholder="Cerca fornitore..."
                                emptyText="Nessun fornitore trovato"
                                className="mt-1"
                                data-testid="rdp-fornitore"
                            />
                        </div>

                        {/* Line items table */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label className="text-sm font-medium">Materiali Richiesti *</Label>
                                <Button type="button" variant="outline" size="sm" onClick={addRdpLine} data-testid="rdp-add-line">
                                    <Plus className="h-3 w-3 mr-1" /> Aggiungi riga
                                </Button>
                            </div>
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="w-[45%] text-xs">Descrizione</TableHead>
                                            <TableHead className="w-[15%] text-xs text-center">Quantità</TableHead>
                                            <TableHead className="w-[15%] text-xs text-center">U.M.</TableHead>
                                            <TableHead className="w-[15%] text-xs text-center">Cert. 3.1</TableHead>
                                            <TableHead className="w-[10%]"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {rdpForm.righe.map((riga, idx) => (
                                            <TableRow key={riga.id || idx}>
                                                <TableCell className="p-1">
                                                    <Input
                                                        value={riga.descrizione}
                                                        onChange={e => updateRdpLine(idx, 'descrizione', e.target.value)}
                                                        placeholder="es. Travi IPE 100"
                                                        className="h-8 text-sm"
                                                        data-testid={`rdp-desc-${idx}`}
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        type="number"
                                                        value={riga.quantita}
                                                        onChange={e => updateRdpLine(idx, 'quantita', e.target.value)}
                                                        className="h-8 text-sm text-center"
                                                        min="0"
                                                        step="0.01"
                                                        data-testid={`rdp-qty-${idx}`}
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Select value={riga.unita_misura} onValueChange={v => updateRdpLine(idx, 'unita_misura', v)}>
                                                        <SelectTrigger className="h-8 text-xs">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="kg">kg</SelectItem>
                                                            <SelectItem value="pz">pz</SelectItem>
                                                            <SelectItem value="ml">ml</SelectItem>
                                                            <SelectItem value="mq">mq</SelectItem>
                                                            <SelectItem value="t">t</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell className="p-1 text-center">
                                                    <Checkbox
                                                        checked={riga.richiede_cert_31}
                                                        onCheckedChange={v => updateRdpLine(idx, 'richiede_cert_31', v)}
                                                        data-testid={`rdp-cert-${idx}`}
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1 text-center">
                                                    {rdpForm.righe.length > 1 && (
                                                        <Button
                                                            type="button"
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-7 w-7 p-0 text-red-400 hover:text-red-600"
                                                            onClick={() => removeRdpLine(idx)}
                                                        >
                                                            <Trash2 className="h-3.5 w-3.5" />
                                                        </Button>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                                ☑️ Cert. 3.1 = richiedi certificato materiale EN 10204 tipo 3.1
                            </p>
                        </div>

                        {/* Notes */}
                        <div>
                            <Label className="text-sm font-medium">Note aggiuntive</Label>
                            <Textarea
                                value={rdpForm.note}
                                onChange={e => setRdpForm(f => ({ ...f, note: e.target.value }))}
                                className="mt-1 h-16"
                                placeholder="Specifiche particolari, tempi di consegna richiesti, ecc."
                                data-testid="rdp-note"
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setRdpOpen(false)}>Annulla</Button>
                        <Button
                            size="sm"
                            disabled={!rdpForm.fornitore_nome || rdpForm.righe.filter(r => r.descrizione.trim()).length === 0}
                            onClick={handleCreateRdP}
                            className="bg-[#0055FF] text-white"
                            data-testid="btn-confirm-rdp"
                        >
                            <ShoppingCart className="h-4 w-4 mr-1" /> Invia RdP
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* OdA Dialog - Full featured with line items and pricing */}
            <Dialog open={odaOpen} onOpenChange={setOdaOpen}>
                <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Package className="h-5 w-5 text-emerald-600" />
                            Nuovo Ordine di Acquisto (OdA)
                        </DialogTitle>
                        {commessaNumero && (
                            <DialogDescription>
                                Riferimento: Commessa <span className="font-semibold">{commessaNumero}</span>
                            </DialogDescription>
                        )}
                    </DialogHeader>
                    <div className="space-y-4">
                        {/* Fornitore selector */}
                        <div>
                            <Label className="text-sm font-medium">Fornitore *</Label>
                            <Combobox
                                options={fornitori.map(f => ({ value: f.id, label: f.nome }))}
                                value={odaForm.fornitore_id}
                                onValueChange={(val) => {
                                    const f = fornitori.find(x => x.id === val);
                                    setOdaForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                }}
                                placeholder="Seleziona fornitore..."
                                searchPlaceholder="Cerca fornitore..."
                                emptyText="Nessun fornitore trovato"
                                className="mt-1"
                                data-testid="oda-fornitore"
                            />
                        </div>

                        {/* Line items table with pricing */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label className="text-sm font-medium">Righe Ordine *</Label>
                                <Button type="button" variant="outline" size="sm" onClick={addOdaLine} data-testid="oda-add-line">
                                    <Plus className="h-3 w-3 mr-1" /> Aggiungi riga
                                </Button>
                            </div>
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="w-[35%] text-xs">Descrizione</TableHead>
                                            <TableHead className="w-[12%] text-xs text-center">Quantità</TableHead>
                                            <TableHead className="w-[10%] text-xs text-center">U.M.</TableHead>
                                            <TableHead className="w-[15%] text-xs text-right">Prezzo Unit. €</TableHead>
                                            <TableHead className="w-[13%] text-xs text-right">Importo €</TableHead>
                                            <TableHead className="w-[8%] text-xs text-center">3.1</TableHead>
                                            <TableHead className="w-[7%]"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {odaForm.righe.map((riga, idx) => {
                                            const importoRiga = (parseFloat(riga.quantita) || 0) * (parseFloat(riga.prezzo_unitario) || 0);
                                            return (
                                                <TableRow key={riga.id || idx}>
                                                    <TableCell className="p-1">
                                                        <Input
                                                            value={riga.descrizione}
                                                            onChange={e => updateOdaLine(idx, 'descrizione', e.target.value)}
                                                            placeholder="es. Travi IPE 100"
                                                            className="h-8 text-sm"
                                                            data-testid={`oda-desc-${idx}`}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="p-1">
                                                        <Input
                                                            type="number"
                                                            value={riga.quantita}
                                                            onChange={e => updateOdaLine(idx, 'quantita', e.target.value)}
                                                            className="h-8 text-sm text-center"
                                                            min="0"
                                                            step="0.01"
                                                            data-testid={`oda-qty-${idx}`}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="p-1">
                                                        <Select value={riga.unita_misura} onValueChange={v => updateOdaLine(idx, 'unita_misura', v)}>
                                                            <SelectTrigger className="h-8 text-xs">
                                                                <SelectValue />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="kg">kg</SelectItem>
                                                                <SelectItem value="pz">pz</SelectItem>
                                                                <SelectItem value="ml">ml</SelectItem>
                                                                <SelectItem value="mq">mq</SelectItem>
                                                                <SelectItem value="t">t</SelectItem>
                                                            </SelectContent>
                                                        </Select>
                                                    </TableCell>
                                                    <TableCell className="p-1">
                                                        <Input
                                                            type="number"
                                                            value={riga.prezzo_unitario}
                                                            onChange={e => updateOdaLine(idx, 'prezzo_unitario', e.target.value)}
                                                            className="h-8 text-sm text-right"
                                                            min="0"
                                                            step="0.01"
                                                            data-testid={`oda-price-${idx}`}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="p-1 text-right text-sm font-medium text-slate-600">
                                                        {importoRiga.toFixed(2)}
                                                    </TableCell>
                                                    <TableCell className="p-1 text-center">
                                                        <Checkbox
                                                            checked={riga.richiede_cert_31}
                                                            onCheckedChange={v => updateOdaLine(idx, 'richiede_cert_31', v)}
                                                            data-testid={`oda-cert-${idx}`}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="p-1 text-center">
                                                        {odaForm.righe.length > 1 && (
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="sm"
                                                                className="h-7 w-7 p-0 text-red-400 hover:text-red-600"
                                                                onClick={() => removeOdaLine(idx)}
                                                            >
                                                                <Trash2 className="h-3.5 w-3.5" />
                                                            </Button>
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </div>
                            <div className="flex justify-between items-center mt-2 px-2">
                                <p className="text-xs text-muted-foreground">
                                    ☑️ 3.1 = richiedi certificato materiale
                                </p>
                                <div className="text-right">
                                    <span className="text-sm text-slate-500 mr-2">Totale Ordine:</span>
                                    <span className="text-lg font-bold text-emerald-700">{fmtEur(odaTotale)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Notes */}
                        <div>
                            <Label className="text-sm font-medium">Note</Label>
                            <Textarea
                                value={odaForm.note}
                                onChange={e => setOdaForm(f => ({ ...f, note: e.target.value }))}
                                className="mt-1 h-16"
                                placeholder="Condizioni di pagamento, consegna, ecc."
                                data-testid="oda-note"
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setOdaOpen(false)}>Annulla</Button>
                        <Button
                            size="sm"
                            disabled={!odaForm.fornitore_nome || odaForm.righe.filter(r => r.descrizione.trim()).length === 0}
                            onClick={handleCreateOdA}
                            className="bg-emerald-600 text-white hover:bg-emerald-700"
                            data-testid="btn-confirm-oda"
                        >
                            <Package className="h-4 w-4 mr-1" /> Emetti Ordine
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Arrivo Dialog */}
            <Dialog open={arrivoOpen} onOpenChange={setArrivoOpen}>
                <DialogContent className="max-w-sm"><DialogHeader><DialogTitle>Registra Arrivo Materiale</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label className="text-xs">DDT Fornitore</Label><Input value={arrivoForm.ddt_fornitore} onChange={e => setArrivoForm(f => ({ ...f, ddt_fornitore: e.target.value }))} className="mt-1" placeholder="es. DDT-2026/0123" data-testid="arrivo-ddt" /></div>
                        <div><Label className="text-xs">Note</Label><Textarea value={arrivoForm.note} onChange={e => setArrivoForm(f => ({ ...f, note: e.target.value }))} className="mt-1 h-12" /></div>
                    </div>
                    <DialogFooter><Button size="sm" onClick={handleCreateArrivo} className="bg-[#0055FF] text-white" data-testid="btn-confirm-arrivo">Registra</Button></DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Conto Lavoro Dialog */}
            <Dialog open={clOpen} onOpenChange={setClOpen}>
                <DialogContent className="max-w-sm"><DialogHeader><DialogTitle>Nuovo Conto Lavoro</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label className="text-xs">Tipo</Label>
                            <Select value={clForm.tipo} onValueChange={v => setClForm(f => ({ ...f, tipo: v }))}>
                                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="verniciatura">Verniciatura</SelectItem>
                                    <SelectItem value="zincatura">Zincatura a caldo</SelectItem>
                                    <SelectItem value="sabbiatura">Sabbiatura</SelectItem>
                                    <SelectItem value="altro">Altro</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs">Fornitore</Label>
                            <Combobox
                                options={fornitori.map(f => ({ value: f.id, label: f.nome }))}
                                value={clForm.fornitore_id}
                                onValueChange={(val) => {
                                    const f = fornitori.find(x => x.id === val);
                                    setClForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                }}
                                placeholder="Seleziona fornitore..."
                                searchPlaceholder="Cerca fornitore..."
                                emptyText="Nessun fornitore trovato"
                                className="mt-1"
                                data-testid="cl-fornitore"
                            />
                        </div>
                    </div>
                    <DialogFooter><Button size="sm" disabled={!clForm.fornitore_nome} onClick={handleCreateCL} className="bg-[#0055FF] text-white" data-testid="btn-confirm-cl">Crea</Button></DialogFooter>
                </DialogContent>
            </Dialog>

            {/* PDF Preview Dialog */}
            <Dialog open={!!pdfPreviewUrl} onOpenChange={(open) => !open && setPdfPreviewUrl(null)}>
                <DialogContent className="max-w-4xl h-[85vh]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileSearch className="h-5 w-5 text-blue-600" />
                            {pdfPreviewTitle}
                        </DialogTitle>
                        <DialogDescription>
                            Verifica il documento prima di inviarlo via email
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex-1 h-full min-h-0">
                        {pdfPreviewUrl && (
                            <iframe
                                src={`${pdfPreviewUrl}?token=${localStorage.getItem('auth_token')}`}
                                className="w-full h-[calc(85vh-120px)] border rounded"
                                title="PDF Preview"
                            />
                        )}
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" onClick={() => setPdfPreviewUrl(null)}>Chiudi</Button>
                        <Button
                            className="bg-[#0055FF] text-white"
                            onClick={() => {
                                // Extract type and ID from URL
                                if (pdfPreviewUrl?.includes('/richieste/')) {
                                    const rdpId = pdfPreviewUrl.split('/richieste/')[1]?.split('/')[0];
                                    if (rdpId) handleSendRdpEmail(rdpId);
                                } else if (pdfPreviewUrl?.includes('/ordini/')) {
                                    const ordineId = pdfPreviewUrl.split('/ordini/')[1]?.split('/')[0];
                                    if (ordineId) handleSendOdaEmail(ordineId);
                                }
                                setPdfPreviewUrl(null);
                            }}
                        >
                            <Mail className="h-4 w-4 mr-1" /> Invia Email
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
