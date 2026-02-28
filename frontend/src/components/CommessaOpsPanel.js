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

export default function CommessaOpsPanel({ commessaId, onRefresh }) {
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

    // Form states
    const [rdpForm, setRdpForm] = useState({ fornitore_nome: '', fornitore_id: '', materiali_richiesti: '' });
    const [odaForm, setOdaForm] = useState({ fornitore_nome: '', fornitore_id: '', importo_totale: '', note: '' });
    const [arrivoForm, setArrivoForm] = useState({ ddt_fornitore: '', ordine_id: '', note: '' });
    const [clForm, setClForm] = useState({ tipo: 'verniciatura', fornitore_nome: '', fornitore_id: '' });

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
    const handleCreateRdP = async () => {
        try {
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/richieste`, { method: 'POST', body: rdpForm });
            toast.success('RdP inviata');
            setRdpOpen(false);
            setRdpForm({ fornitore_nome: '', materiali_richiesti: '' });
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
        try {
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/ordini`, {
                method: 'POST', body: { ...odaForm, importo_totale: parseFloat(odaForm.importo_totale) || 0 },
            });
            toast.success('Ordine emesso');
            setOdaOpen(false);
            setOdaForm({ fornitore_nome: '', importo_totale: '', note: '' });
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
                            <span className="font-medium flex-1 truncate">RdP → {r.fornitore_nome}</span>
                            <StatoBadge stato={r.stato} />
                            {r.importo_proposto && <span className="font-mono text-[10px]">{fmtEur(r.importo_proposto)}</span>}
                            {r.stato === 'inviata' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateRdP(r.rdp_id, 'ricevuta')}>Ricevuta</Button>}
                            {r.stato === 'ricevuta' && (
                                <>
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateRdP(r.rdp_id, 'accettata')}>Accetta</Button>
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-red-600" onClick={() => handleUpdateRdP(r.rdp_id, 'rifiutata')}>Rifiuta</Button>
                                </>
                            )}
                        </div>
                    ))}

                    {/* Ordini */}
                    {(approv.ordini || []).map(o => (
                        <div key={o.ordine_id} className="flex items-center gap-2 p-2 bg-blue-50 rounded text-xs" data-testid={`oda-${o.ordine_id}`}>
                            <Truck className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                            <span className="font-medium flex-1 truncate">OdA → {o.fornitore_nome}</span>
                            <span className="font-mono text-[10px]">{fmtEur(o.importo_totale)}</span>
                            <StatoBadge stato={o.stato} />
                            {o.stato === 'inviato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateOrdine(o.ordine_id, 'confermato')}>Confermato</Button>}
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
            {/* RdP Dialog */}
            <Dialog open={rdpOpen} onOpenChange={setRdpOpen}>
                <DialogContent className="max-w-sm"><DialogHeader><DialogTitle>Nuova RdP Fornitore</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label className="text-xs">Fornitore</Label>
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
                        <div><Label className="text-xs">Materiali richiesti</Label><Textarea value={rdpForm.materiali_richiesti} onChange={e => setRdpForm(f => ({ ...f, materiali_richiesti: e.target.value }))} className="mt-1 h-16" data-testid="rdp-materiali" /></div>
                    </div>
                    <DialogFooter><Button size="sm" disabled={!rdpForm.fornitore_nome} onClick={handleCreateRdP} className="bg-[#0055FF] text-white" data-testid="btn-confirm-rdp">Invia RdP</Button></DialogFooter>
                </DialogContent>
            </Dialog>

            {/* OdA Dialog */}
            <Dialog open={odaOpen} onOpenChange={setOdaOpen}>
                <DialogContent className="max-w-sm"><DialogHeader><DialogTitle>Nuovo Ordine Fornitore</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label className="text-xs">Fornitore</Label>
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
                        <div><Label className="text-xs">Importo Totale (EUR)</Label><Input type="number" value={odaForm.importo_totale} onChange={e => setOdaForm(f => ({ ...f, importo_totale: e.target.value }))} className="mt-1" data-testid="oda-importo" /></div>
                        <div><Label className="text-xs">Note</Label><Textarea value={odaForm.note} onChange={e => setOdaForm(f => ({ ...f, note: e.target.value }))} className="mt-1 h-12" /></div>
                    </div>
                    <DialogFooter><Button size="sm" disabled={!odaForm.fornitore_nome} onClick={handleCreateOdA} className="bg-[#0055FF] text-white" data-testid="btn-confirm-oda">Emetti Ordine</Button></DialogFooter>
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
        </div>
    );
}
