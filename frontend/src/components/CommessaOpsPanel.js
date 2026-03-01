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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import {
    ShoppingCart, Package, Truck, Factory, Paintbrush, FileUp,
    Play, CheckCircle2, Clock, AlertTriangle, Plus, Trash2,
    Download, Eye, Loader2, Sparkles, ChevronDown, ChevronUp, FileText,
    Mail, MailCheck, FileSearch, Leaf, RefreshCw,
    Maximize2, Minimize2,
} from 'lucide-react';
import EmailPreviewDialog from './EmailPreviewDialog';
import { DisabledTooltip } from './DisabledTooltip';
import FascicoloTecnicoSection from './FascicoloTecnicoSection';

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
    const [materialBatches, setMaterialBatches] = useState([]);
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
    const [arrivoForm, setArrivoForm] = useState({ 
        ddt_fornitore: '', 
        data_ddt: '', 
        fornitore_nome: '', 
        fornitore_id: '',
        materiali: [{ descrizione: '', quantita: 1, unita_misura: 'kg', ordine_id: '', richiede_cert_31: false }],
        note: '' 
    });
    const emptyClLine = () => ({ id: `l${Date.now()}`, descrizione: '', quantita: 1, unita: 'pz', peso_kg: 0 });
    const [clForm, setClForm] = useState({ tipo: 'verniciatura', fornitore_nome: '', fornitore_id: '', ral: '', righe: [emptyClLine()], note: '', causale_trasporto: 'Conto Lavorazione' });

    // PDF Preview and Email states (must be before any conditional return)
    const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
    const [pdfPreviewTitle, setPdfPreviewTitle] = useState('');
    const [sendingEmail, setSendingEmail] = useState(null); // Track which item is sending email

    // Email Preview Dialog state
    const [emailPreview, setEmailPreview] = useState({ open: false, previewUrl: '', sendUrl: '' });
    const [pdfExpanded, setPdfExpanded] = useState(false);

    // Certificate linking states
    const [certLinkOpen, setCertLinkOpen] = useState(false);
    const [selectedArrivo, setSelectedArrivo] = useState(null);
    const [linkingCert, setLinkingCert] = useState(null); // { arrivo_id, mat_idx }
    const certFileRef = useRef();

    // CAM states
    const [camLotti, setCamLotti] = useState([]);
    const [camCalcolo, setCamCalcolo] = useState(null);
    const [camLoading, setCamLoading] = useState(false);
    const [camLottoOpen, setCamLottoOpen] = useState(false);
    const [camLottoForm, setCamLottoForm] = useState({
        descrizione: '', fornitore: '', numero_colata: '', peso_kg: 0, qualita_acciaio: '',
        percentuale_riciclato: 75, metodo_produttivo: 'forno_elettrico_non_legato',
        tipo_certificazione: 'dichiarazione_produttore', numero_certificazione: '',
        ente_certificatore: '', uso_strutturale: true, commessa_id: commessaId,
    });
    const [editingCamLotto, setEditingCamLotto] = useState(null);

    // Load fornitori from anagrafica
    useEffect(() => {
        apiRequest('/clients/?client_type=fornitore&limit=100').then(data => {
            setFornitori((data.clients || []).map(c => ({ id: c.client_id, nome: c.business_name })));
        }).catch(() => {});
    }, []);

    const fetchData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const [o, d, batches] = await Promise.all([
                apiRequest(`/commesse/${commessaId}/ops`),
                apiRequest(`/commesse/${commessaId}/documenti`),
                apiRequest(`/fpc/batches?commessa_id=${commessaId}`).catch(() => ({ batches: [] })),
            ]);
            setOps(o);
            setDocs(d.documents || []);
            setMaterialBatches(batches.batches || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // CAM data fetch
    const fetchCamData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const [lottiRes, calcoloRes] = await Promise.all([
                apiRequest(`/cam/lotti?commessa_id=${commessaId}`).catch(() => ({ lotti: [] })),
                apiRequest(`/cam/calcolo/${commessaId}`).catch(() => null),
            ]);
            setCamLotti(lottiRes.lotti || []);
            setCamCalcolo(calcoloRes);
        } catch (e) { console.error('CAM fetch error', e); }
    }, [commessaId]);

    useEffect(() => { fetchCamData(); }, [fetchCamData]);

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

    // Create OdA pre-filled from accepted RdP
    const handleCreateOdaFromRdp = (rdp) => {
        // Pre-fill OdA with RdP data - just need to add prices
        const righeFromRdp = (rdp.righe || []).map(r => ({
            id: `l${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            descrizione: r.descrizione,
            quantita: r.quantita || 1,
            unita_misura: r.unita_misura || 'kg',
            prezzo_unitario: 0, // User will fill this
            richiede_cert_31: r.richiede_cert_31 || false,
        }));
        
        setOdaForm({
            fornitore_nome: rdp.fornitore_nome,
            fornitore_id: rdp.fornitore_id || '',
            righe: righeFromRdp.length > 0 ? righeFromRdp : [emptyOdaLine()],
            note: `Rif. RdP: ${rdp.rdp_id}`,
            riferimento_rdp_id: rdp.rdp_id,
        });
        setOdaOpen(true);
        toast.info('OdA pre-compilato dalla RdP - aggiungi i prezzi e invia!');
    };

    const handleCreateArrivo = async () => {
        if (!arrivoForm.ddt_fornitore.trim()) {
            toast.error('Inserisci il numero DDT fornitore');
            return;
        }
        if (arrivoForm.materiali.filter(m => m.descrizione.trim()).length === 0) {
            toast.error('Inserisci almeno un materiale');
            return;
        }
        try {
            const payload = {
                ...arrivoForm,
                materiali: arrivoForm.materiali.filter(m => m.descrizione.trim()).map(m => ({
                    descrizione: m.descrizione,
                    quantita: parseFloat(m.quantita) || 1,
                    unita_misura: m.unita_misura,
                    ordine_id: m.ordine_id || '',
                    richiede_cert_31: m.richiede_cert_31,
                })),
            };
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/arrivi`, { method: 'POST', body: payload });
            toast.success('Arrivo registrato');
            setArrivoOpen(false);
            setArrivoForm({ 
                ddt_fornitore: '', 
                data_ddt: '', 
                fornitore_nome: '', 
                fornitore_id: '',
                materiali: [{ descrizione: '', quantita: 1, unita_misura: 'kg', ordine_id: '', richiede_cert_31: false }],
                note: '' 
            });
            fetchData(); onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    // Arrivo materiali helpers
    const emptyArrivoMat = () => ({ id: `m${Date.now()}`, descrizione: '', quantita: 1, unita_misura: 'kg', ordine_id: '', richiede_cert_31: false });
    const addArrivoMat = () => setArrivoForm(f => ({ ...f, materiali: [...f.materiali, emptyArrivoMat()] }));
    const removeArrivoMat = (idx) => setArrivoForm(f => ({ ...f, materiali: f.materiali.filter((_, i) => i !== idx) }));
    const updateArrivoMat = (idx, field, value) => setArrivoForm(f => {
        const materiali = [...f.materiali];
        materiali[idx] = { ...materiali[idx], [field]: value };
        return { ...f, materiali };
    });

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
        if (clForm.righe.filter(r => r.descrizione.trim()).length === 0) {
            toast.error('Inserisci almeno una riga materiale'); return;
        }
        try {
            await apiRequest(`/commesse/${commessaId}/conto-lavoro`, {
                method: 'POST',
                body: {
                    tipo: clForm.tipo, fornitore_nome: clForm.fornitore_nome, fornitore_id: clForm.fornitore_id,
                    ral: clForm.ral, note: clForm.note, causale_trasporto: clForm.causale_trasporto,
                    righe: clForm.righe.filter(r => r.descrizione.trim()).map(r => ({ descrizione: r.descrizione, quantita: parseFloat(r.quantita) || 0, unita: r.unita, peso_kg: parseFloat(r.peso_kg) || 0 })),
                },
            });
            toast.success('Conto lavoro creato');
            setClOpen(false);
            setClForm({ tipo: 'verniciatura', fornitore_nome: '', fornitore_id: '', ral: '', righe: [emptyClLine()], note: '', causale_trasporto: 'Conto Lavorazione' });
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

    const handlePreviewClPdf = async (clId) => {
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/conto-lavoro/${clId}/preview-pdf`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) throw new Error('Errore generazione PDF');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            setPdfPreviewUrl(url);
            setPdfPreviewTitle('DDT Conto Lavoro');
        } catch (e) { toast.error(e.message); }
    };

    const handleSendClEmail = async (clId) => {
        setEmailPreview({
            open: true,
            previewUrl: `/api/commesse/${commessaId}/conto-lavoro/${clId}/preview-email`,
            sendUrl: `/api/commesse/${commessaId}/conto-lavoro/${clId}/send-email`,
        });
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
            const matches = res.risultati_match || [];
            const nProfili = res.profili_trovati || 0;
            
            // Show results per profile type
            const corrente = matches.filter(r => r.tipo === 'commessa_corrente');
            const altre = matches.filter(r => r.tipo === 'altra_commessa');
            const archivio = matches.filter(r => r.tipo === 'archivio');
            
            if (corrente.length > 0) {
                toast.success(`${corrente.map(p => p.dimensioni || p.qualita_acciaio).join(', ')} → assegnato a questa commessa (+ CAM e tracciabilità auto)`, { duration: 6000 });
            }
            if (altre.length > 0) {
                toast.info(`${altre.map(p => `${p.dimensioni || p.qualita_acciaio} → ${p.commessa_numero || p.commessa_id}`).join(' | ')} — certificato copiato automaticamente`, { duration: 8000 });
            }
            if (archivio.length > 0) {
                toast.warning(`${archivio.map(p => p.dimensioni || p.qualita_acciaio).join(', ')} → archiviato (nessun ordine/richiesta trovato)`, { duration: 6000 });
            }
            if (nProfili === 0) {
                toast.info(`Fornitore: ${m?.fornitore || '?'} — nessun profilo specifico trovato`, { duration: 4000 });
            }
            
            fetchData(); fetchCamData(); onRefresh?.();
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
        setEmailPreview({
            open: true,
            previewUrl: `/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/preview-email`,
            sendUrl: `/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/send-email`,
        });
    };

    const handleSendOdaEmail = async (ordineId) => {
        setEmailPreview({
            open: true,
            previewUrl: `/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/preview-email`,
            sendUrl: `/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/send-email`,
        });
    };

    // Open certificate linking dialog for an arrival
    const handleOpenCertLink = (arrivo) => {
        setSelectedArrivo(arrivo);
        setCertLinkOpen(true);
    };

    // Handle certificate file upload and AI OCR parsing
    const handleCertificateUpload = async (arrivoId, matIdx, file) => {
        if (!file) return;
        setLinkingCert({ arrivo_id: arrivoId, mat_idx: matIdx });
        
        try {
            // First upload the certificate to the repository
            const formData = new FormData();
            formData.append('file', file);
            formData.append('tipo', 'certificato_31');
            
            const uploadRes = await fetch(`${API}/api/commesse/${commessaId}/documenti`, {
                method: 'POST',
                body: formData,
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            
            if (!uploadRes.ok) throw new Error('Errore upload certificato');
            const uploadData = await uploadRes.json();
            const docId = uploadData.doc_id;
            
            toast.info('Analisi AI del certificato in corso...');
            
            // Parse the certificate with AI OCR
            const parseRes = await apiRequest(`/commesse/${commessaId}/documenti/${docId}/parse-certificate`, { method: 'POST' });
            
            // Link the certificate to the material with extracted data
            const linkForm = new FormData();
            linkForm.append('certificato_doc_id', docId);
            if (parseRes.extracted?.numero_colata) linkForm.append('numero_colata', parseRes.extracted.numero_colata);
            if (parseRes.extracted?.qualita_materiale) linkForm.append('qualita_materiale', parseRes.extracted.qualita_materiale);
            if (parseRes.extracted?.fornitore) linkForm.append('fornitore_materiale', parseRes.extracted.fornitore);
            
            await fetch(`${API}/api/commesse/${commessaId}/approvvigionamento/arrivi/${arrivoId}/materiale/${matIdx}/certificato`, {
                method: 'PUT',
                body: linkForm,
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            
            toast.success(`Certificato collegato! Colata: ${parseRes.extracted?.numero_colata || 'N/D'}`);
            fetchData();
            onRefresh?.();
            
            // Update local state
            if (selectedArrivo) {
                const updatedMateriali = [...selectedArrivo.materiali];
                updatedMateriali[matIdx] = {
                    ...updatedMateriali[matIdx],
                    certificato_doc_id: docId,
                    numero_colata: parseRes.extracted?.numero_colata || '',
                    qualita_materiale: parseRes.extracted?.qualita_materiale || '',
                };
                setSelectedArrivo({ ...selectedArrivo, materiali: updatedMateriali });
            }
        } catch (e) {
            toast.error(e.message || 'Errore collegamento certificato');
        } finally {
            setLinkingCert(null);
        }
    };

    // ── CAM Handlers ──
    const handleCreateCamLotto = async () => {
        if (!camLottoForm.descrizione.trim()) { toast.error('Inserisci una descrizione'); return; }
        try {
            const payload = { ...camLottoForm, peso_kg: parseFloat(camLottoForm.peso_kg) || 0, percentuale_riciclato: parseFloat(camLottoForm.percentuale_riciclato) || 0, commessa_id: commessaId };
            if (editingCamLotto) {
                await apiRequest(`/cam/lotti/${editingCamLotto}`, { method: 'PUT', body: payload });
                toast.success('Lotto CAM aggiornato');
            } else {
                await apiRequest('/cam/lotti', { method: 'POST', body: payload });
                toast.success('Lotto CAM creato');
            }
            setCamLottoOpen(false);
            setEditingCamLotto(null);
            setCamLottoForm({ descrizione: '', fornitore: '', numero_colata: '', peso_kg: 0, qualita_acciaio: '', percentuale_riciclato: 75, metodo_produttivo: 'forno_elettrico_non_legato', tipo_certificazione: 'dichiarazione_produttore', numero_certificazione: '', ente_certificatore: '', uso_strutturale: true, commessa_id: commessaId });
            fetchCamData();
        } catch (e) { toast.error(e.message); }
    };

    const handleCalcolaCAM = async () => {
        setCamLoading(true);
        try {
            const result = await apiRequest(`/cam/calcola/${commessaId}`, { method: 'POST' });
            setCamCalcolo(result);
            toast.success('Calcolo CAM aggiornato');
        } catch (e) { toast.error(e.message); }
        finally { setCamLoading(false); }
    };

    const handleDownloadCamPdf = async () => {
        try {
            const res = await fetch(`${API}/api/cam/dichiarazione-pdf/${commessaId}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Errore generazione PDF'); }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Dichiarazione_CAM_${commessaNumero || commessaId}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Dichiarazione CAM generata');
        } catch (e) { toast.error(e.message); }
    };

    const handleDownloadGreenCert = async () => {
        try {
            const res = await fetch(`${API}/api/cam/green-certificate/${commessaId}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Errore'); }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Green_Certificate_${commessaNumero || commessaId}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Green Certificate generato');
        } catch (e) { toast.error(e.message); }
    };

    const handleImportCamFromCert = async (docId) => {
        setCamLoading(true);
        try {
            await apiRequest(`/cam/import-da-certificato/${docId}?commessa_id=${commessaId}&peso_kg=0`, { method: 'POST' });
            toast.success('Dati CAM importati dal certificato');
            fetchCamData();
        } catch (e) { toast.error(e.message); }
        finally { setCamLoading(false); }
    };

    const openEditCamLotto = (lotto) => {
        setCamLottoForm({
            descrizione: lotto.descrizione || '', fornitore: lotto.fornitore || '', numero_colata: lotto.numero_colata || '',
            peso_kg: lotto.peso_kg || 0, qualita_acciaio: lotto.qualita_acciaio || '',
            percentuale_riciclato: lotto.percentuale_riciclato || 0, metodo_produttivo: lotto.metodo_produttivo || 'forno_elettrico_non_legato',
            tipo_certificazione: lotto.tipo_certificazione || 'dichiarazione_produttore', numero_certificazione: lotto.numero_certificazione || '',
            ente_certificatore: lotto.ente_certificatore || '', uso_strutturale: lotto.uso_strutturale !== false, commessa_id: commessaId,
        });
        setEditingCamLotto(lotto.lotto_id);
        setCamLottoOpen(true);
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
                                {r.stato === 'accettata' && (
                                    <Button 
                                        size="sm" 
                                        variant="ghost" 
                                        className="h-6 text-[10px] text-blue-600 font-medium"
                                        onClick={() => handleCreateOdaFromRdp(r)}
                                        title="Crea Ordine da questa RdP"
                                    >
                                        <Package className="h-3 w-3 mr-0.5" /> Crea OdA
                                    </Button>
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
                        <div key={a.arrivo_id} className="p-2 bg-amber-50 rounded text-xs space-y-1.5" data-testid={`arrivo-${a.arrivo_id}`}>
                            <div className="flex items-center gap-2">
                                <Package className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium">DDT: {a.ddt_fornitore || '-'}</span>
                                        {a.fornitore_nome && <span className="text-slate-500">({a.fornitore_nome})</span>}
                                    </div>
                                    {a.materiali?.length > 0 && (
                                        <div className="text-[10px] text-slate-500">
                                            {a.materiali.length} materiali — {a.materiali.filter(m => m.certificato_doc_id || m.numero_colata).length} con certificato
                                        </div>
                                    )}
                                </div>
                                <StatoBadge stato={a.stato} />
                                <div className="flex items-center gap-1">
                                    {a.materiali?.some(m => m.richiede_cert_31 && !m.certificato_doc_id) && (
                                        <Button 
                                            size="sm" 
                                            variant="ghost" 
                                            className="h-6 text-[10px] text-purple-600"
                                            onClick={() => handleOpenCertLink(a)}
                                            title="Collega certificati ai materiali"
                                        >
                                            <Sparkles className="h-3 w-3 mr-0.5" /> Certificati
                                        </Button>
                                    )}
                                    {a.stato === 'da_verificare' && (
                                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleVerificaArrivo(a.arrivo_id)}>
                                            <CheckCircle2 className="h-3 w-3 mr-0.5" /> Verifica
                                        </Button>
                                    )}
                                </div>
                            </div>
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
                        <div key={c.cl_id} className="p-2.5 bg-slate-50 rounded border text-xs space-y-1.5" data-testid={`cl-${c.cl_id}`}>
                            <div className="flex items-center gap-2">
                                <Paintbrush className="h-3.5 w-3.5 text-purple-500 shrink-0" />
                                <span className="font-semibold flex-1 truncate capitalize">{c.tipo} → {c.fornitore_nome}</span>
                                <StatoBadge stato={c.stato} />
                                {c.stato_email === 'inviata' && <Badge className="bg-green-100 text-green-700 text-[8px]"><MailCheck className="h-2.5 w-2.5 mr-0.5" />Email</Badge>}
                            </div>
                            {c.ral && <div className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded inline-block">RAL: {c.ral}</div>}
                            {(c.righe || []).length > 0 && <div className="text-[10px] text-slate-500">{c.righe.length} materiali — {c.righe.reduce((sum, r) => sum + (parseFloat(r.peso_kg) || 0), 0).toFixed(1)} kg</div>}
                            <div className="flex items-center gap-1 flex-wrap pt-1">
                                {/* Status transition buttons */}
                                {c.stato === 'da_inviare' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600" onClick={() => handleUpdateCL(c.cl_id, 'inviato')}>Invia</Button>}
                                {c.stato === 'inviato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-amber-600" onClick={() => handleUpdateCL(c.cl_id, 'in_lavorazione')}>In Lav.</Button>}
                                {c.stato === 'in_lavorazione' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateCL(c.cl_id, 'rientrato')}>Rientrato</Button>}
                                {c.stato === 'rientrato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateCL(c.cl_id, 'verificato')}>Verifica</Button>}
                                <div className="h-4 w-px bg-slate-200 mx-0.5" />
                                {/* PDF Preview */}
                                <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600" onClick={() => handlePreviewClPdf(c.cl_id)} data-testid={`cl-preview-${c.cl_id}`}>
                                    <Eye className="h-3 w-3 mr-0.5" /> PDF
                                </Button>
                                {/* Send Email */}
                                <Button size="sm" variant="ghost" className="h-6 text-[10px] text-purple-600" disabled={sendingEmail === c.cl_id} onClick={() => handleSendClEmail(c.cl_id)} data-testid={`cl-email-${c.cl_id}`}>
                                    {sendingEmail === c.cl_id ? <Loader2 className="h-3 w-3 animate-spin mr-0.5" /> : <Mail className="h-3 w-3 mr-0.5" />}
                                    Email
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            </Section>

            {/* ── TRACCIABILITÀ MATERIALI (EN 1090) ── */}
            <Section title="Tracciabilità Materiali" icon={FileText} count={materialBatches.length + docs.filter(d => d.metadata_estratti?.numero_colata).length}>
                {/* Download Scheda Rintracciabilità button */}
                {materialBatches.length > 0 && (
                    <div className="flex justify-end mb-2">
                        <Button
                            size="sm"
                            variant="outline"
                            data-testid="btn-scheda-rintracciabilita"
                            className="text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                            onClick={async () => {
                                try {
                                    const res = await fetch(`${API}/api/commesse/${commessaId}/scheda-rintracciabilita-pdf`, {
                                        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
                                    });
                                    if (!res.ok) throw new Error('Errore generazione PDF');
                                    const blob = await res.blob();
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a'); a.href = url; a.download = `Scheda_Rintracciabilita_${commessaId}.pdf`; a.click();
                                    URL.revokeObjectURL(url);
                                    toast.success('Scheda Rintracciabilità scaricata');
                                } catch (e) { toast.error(e.message); }
                            }}
                        >
                            <Download className="h-3.5 w-3.5 mr-1" />
                            Scheda Rintracciabilità PDF
                        </Button>
                    </div>
                )}
                <div className="space-y-2">
                    {/* From material_batches collection */}
                    {materialBatches.map(b => (
                        <div key={b.batch_id} className="p-2 bg-emerald-50 rounded border border-emerald-200 text-xs" data-testid={`batch-${b.batch_id}`}>
                            <div className="flex items-center gap-2 mb-1">
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                                <span className="font-semibold text-emerald-800">{b.dimensions || b.material_type || 'Materiale'}</span>
                                <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">EN 1090</Badge>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
                                <div>
                                    <span className="text-slate-500 block">N. Colata</span>
                                    <span className="font-mono font-bold text-emerald-700">{b.heat_number || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Qualità</span>
                                    <span className="font-mono">{b.material_type || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Fornitore</span>
                                    <span className="font-mono">{b.supplier_name || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Profilo</span>
                                    <span className="font-mono">{b.dimensions || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">N. Certificato</span>
                                    <span className="font-mono">{b.numero_certificato || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">DDT N.</span>
                                    <span className="font-mono">{b.ddt_numero || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Posizione</span>
                                    <span className="font-mono">{b.posizione || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">N. Pezzi</span>
                                    <span className="font-mono">{b.n_pezzi || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Acciaieria</span>
                                    <input
                                        defaultValue={b.acciaieria || ''}
                                        placeholder="es. AFV Beltrame"
                                        className="font-mono text-[10px] w-full border border-slate-200 rounded px-1 h-5 bg-white focus:border-emerald-400 focus:outline-none"
                                        data-testid={`acciaieria-${b.batch_id}`}
                                        onBlur={async (e) => {
                                            const val = e.target.value.trim();
                                            if (val === (b.acciaieria || '')) return;
                                            try {
                                                await fetch(`${API}/api/commesse/${commessaId}/material-batches/${b.batch_id}`, {
                                                    method: 'PATCH',
                                                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
                                                    body: JSON.stringify({ acciaieria: val })
                                                });
                                                toast.success('Acciaieria salvata');
                                                loadData();
                                            } catch { toast.error('Errore salvataggio'); }
                                        }}
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                    
                    {/* From documents with extracted metadata */}
                    {docs.filter(d => d.metadata_estratti?.numero_colata).map(d => (
                        <div key={d.doc_id} className="p-2 bg-blue-50 rounded border border-blue-200 text-xs" data-testid={`traced-${d.doc_id}`}>
                            <div className="flex items-center gap-2 mb-1">
                                <Sparkles className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                                <span className="font-semibold text-blue-800">{d.nome_file}</span>
                                <Badge className="bg-blue-100 text-blue-700 text-[9px]">AI OCR</Badge>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
                                <div>
                                    <span className="text-slate-500 block">N. Colata</span>
                                    <span className="font-mono font-bold text-blue-700">{d.metadata_estratti.numero_colata}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Qualità</span>
                                    <span className="font-mono">{d.metadata_estratti.qualita_acciaio || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Fornitore</span>
                                    <span className="font-mono">{d.metadata_estratti.fornitore || '-'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block">Normativa</span>
                                    <span className="font-mono">{d.metadata_estratti.normativa_riferimento || d.metadata_estratti.normativa || '-'}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                    
                    {materialBatches.length === 0 && docs.filter(d => d.metadata_estratti?.numero_colata).length === 0 && (
                        <div className="text-center py-4 text-slate-400 text-xs">
                            <FileText className="h-6 w-6 mx-auto mb-1 opacity-50" />
                            <p>Nessun materiale tracciato</p>
                            <p className="text-[10px] mt-1">Carica un certificato 3.1 e clicca "Analizza AI" per estrarre i dati</p>
                        </div>
                    )}
                </div>
            </Section>

            {/* ── CAM - CRITERI AMBIENTALI MINIMI ── */}
            <Section title="CAM - Criteri Ambientali Minimi" icon={Leaf} count={camLotti.length}>
                <div className="space-y-3">
                    {/* Summary Card */}
                    {camCalcolo && camCalcolo.righe?.length > 0 && (
                        <div className={`p-3 rounded-lg border-2 ${camCalcolo.conforme_cam ? 'bg-emerald-50 border-emerald-400' : 'bg-red-50 border-red-400'}`} data-testid="cam-summary">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    {camCalcolo.conforme_cam ? (
                                        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                    ) : (
                                        <AlertTriangle className="h-5 w-5 text-red-600" />
                                    )}
                                    <span className={`text-sm font-bold ${camCalcolo.conforme_cam ? 'text-emerald-800' : 'text-red-800'}`}>
                                        {camCalcolo.conforme_cam ? 'CONFORME CAM' : 'NON CONFORME CAM'}
                                    </span>
                                </div>
                                <Badge className={camCalcolo.conforme_cam ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>
                                    DM 256/2022
                                </Badge>
                            </div>
                            <div className="grid grid-cols-4 gap-2 text-center">
                                <div className="bg-white/60 rounded p-1.5">
                                    <p className="text-[10px] text-slate-500">Peso Totale</p>
                                    <p className="text-xs font-bold text-slate-800">{(camCalcolo.peso_totale_kg || 0).toLocaleString('it-IT')} kg</p>
                                </div>
                                <div className="bg-white/60 rounded p-1.5">
                                    <p className="text-[10px] text-slate-500">Peso Riciclato</p>
                                    <p className="text-xs font-bold text-slate-800">{(camCalcolo.peso_riciclato_kg || 0).toLocaleString('it-IT')} kg</p>
                                </div>
                                <div className="bg-white/60 rounded p-1.5">
                                    <p className="text-[10px] text-slate-500">% Riciclato</p>
                                    <p className={`text-sm font-bold ${camCalcolo.conforme_cam ? 'text-emerald-700' : 'text-red-700'}`}>
                                        {(camCalcolo.percentuale_riciclato_totale || 0).toFixed(1)}%
                                    </p>
                                </div>
                                <div className="bg-white/60 rounded p-1.5">
                                    <p className="text-[10px] text-slate-500">Soglia Min.</p>
                                    <p className="text-xs font-bold text-slate-600">{camCalcolo.soglia_minima_richiesta || 0}%</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex gap-2 flex-wrap">
                        <Button size="sm" variant="outline" onClick={() => { setEditingCamLotto(null); setCamLottoForm({ descrizione: '', fornitore: '', numero_colata: '', peso_kg: 0, qualita_acciaio: '', percentuale_riciclato: 75, metodo_produttivo: 'forno_elettrico_non_legato', tipo_certificazione: 'dichiarazione_produttore', numero_certificazione: '', ente_certificatore: '', uso_strutturale: true, commessa_id: commessaId }); setCamLottoOpen(true); }} className="text-xs" data-testid="btn-new-cam-lotto">
                            <Plus className="h-3 w-3 mr-1" /> Aggiungi Materiale
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleCalcolaCAM} disabled={camLoading} className="text-xs" data-testid="btn-calcola-cam">
                            <RefreshCw className={`h-3 w-3 mr-1 ${camLoading ? 'animate-spin' : ''}`} /> Ricalcola
                        </Button>
                        {camLotti.length > 0 && (
                            <Button size="sm" onClick={handleDownloadCamPdf} className="text-xs bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-cam-pdf">
                                <Download className="h-3 w-3 mr-1" /> Dichiarazione CAM PDF
                            </Button>
                        )}
                        {camLotti.length > 0 && (
                            <Button size="sm" variant="outline" onClick={handleDownloadGreenCert} className="text-xs border-green-500 text-green-700 hover:bg-green-50" data-testid="btn-green-certificate">
                                <Leaf className="h-3 w-3 mr-1" /> Green Certificate
                            </Button>
                        )}
                    </div>

                    {/* Import from AI-analyzed certificates */}
                    {docs.filter(d => d.metadata_estratti?.numero_colata && !camLotti.find(l => l.numero_colata === d.metadata_estratti.numero_colata)).length > 0 && (
                        <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs" data-testid="cam-import-certs">
                            <p className="font-semibold text-amber-800 mb-1.5 flex items-center gap-1">
                                <Sparkles className="h-3.5 w-3.5" /> Certificati analizzati importabili
                            </p>
                            <div className="space-y-1">
                                {docs.filter(d => d.metadata_estratti?.numero_colata && !camLotti.find(l => l.numero_colata === d.metadata_estratti.numero_colata)).map(d => (
                                    <div key={d.doc_id} className="flex items-center justify-between bg-white rounded p-1.5 border border-amber-100">
                                        <span className="text-slate-700 truncate flex-1">
                                            {d.nome_file} — <span className="font-mono">{d.metadata_estratti.numero_colata}</span>
                                            {d.metadata_estratti.percentuale_riciclato != null && (
                                                <Badge className="ml-1 bg-emerald-50 text-emerald-700 text-[9px]">{d.metadata_estratti.percentuale_riciclato}% ric.</Badge>
                                            )}
                                        </span>
                                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-amber-700" onClick={() => handleImportCamFromCert(d.doc_id)} disabled={camLoading} data-testid={`btn-import-cam-${d.doc_id}`}>
                                            <Plus className="h-3 w-3 mr-0.5" /> Importa
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Material list */}
                    {camLotti.map(lotto => (
                        <div key={lotto.lotto_id} className={`p-2 rounded border text-xs cursor-pointer hover:shadow-sm transition-shadow ${lotto.conforme_cam ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}
                             onClick={() => openEditCamLotto(lotto)} data-testid={`cam-lotto-${lotto.lotto_id}`}>
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                    {lotto.conforme_cam ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                                    <span className="font-semibold text-slate-800">{lotto.descrizione}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <Badge className={`text-[9px] ${lotto.conforme_cam ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                                        {lotto.percentuale_riciclato}% ric. (soglia {lotto.soglia_minima_cam}%)
                                    </Badge>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-[10px]">
                                <div><span className="text-slate-500 block">Fornitore</span><span className="font-mono">{lotto.fornitore || '-'}</span></div>
                                <div><span className="text-slate-500 block">Colata</span><span className="font-mono">{lotto.numero_colata || '-'}</span></div>
                                <div><span className="text-slate-500 block">Peso</span><span className="font-mono">{lotto.peso_kg} kg</span></div>
                                <div><span className="text-slate-500 block">Metodo</span><span className="font-mono">{(lotto.metodo_produttivo || '').replace(/_/g, ' ')}</span></div>
                                <div><span className="text-slate-500 block">Cert.</span><span className="font-mono">{(lotto.tipo_certificazione || '').replace(/_/g, ' ')}</span></div>
                            </div>
                        </div>
                    ))}

                    {camLotti.length === 0 && (
                        <div className="text-center py-4 text-slate-400 text-xs" data-testid="cam-empty">
                            <Leaf className="h-6 w-6 mx-auto mb-1 opacity-50" />
                            <p>Nessun materiale CAM registrato</p>
                            <p className="text-[10px] mt-1">Aggiungi materiali o importa dai certificati analizzati con AI</p>
                        </div>
                    )}
                </div>
            </Section>

            {/* ── FASCICOLO TECNICO EN 1090 ── */}
            <Section title="Fascicolo Tecnico EN 1090" icon={FileText} count={6}>
                <FascicoloTecnicoSection commessaId={commessaId} />
            </Section>

            {/* ── REPOSITORY DOCUMENTI ── */}
            <Section title="Repository Documenti" icon={FileUp} count={docs.length} defaultOpen>
                <div className="space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                        <select
                            value={uploadType}
                            onChange={(e) => setUploadType(e.target.value)}
                            className="w-44 h-8 text-xs rounded-md border border-input bg-transparent px-2 py-1 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                            data-testid="select-upload-type"
                        >
                            <option value="certificato_31">Certificato 3.1</option>
                            <option value="conferma_ordine">Conferma Ordine</option>
                            <option value="disegno">Disegno</option>
                            <option value="certificato_verniciatura">Cert. Verniciatura</option>
                            <option value="certificato_zincatura">Cert. Zincatura</option>
                            <option value="ddt_fornitore">DDT Fornitore</option>
                            <option value="foto">Foto</option>
                            <option value="altro">Altro</option>
                        </select>
                        <input ref={fileRef} type="file" className="hidden" onChange={handleUploadDoc} data-testid="file-input" />
                        <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} className="text-xs" data-testid="btn-upload-doc">
                            <FileUp className="h-3 w-3 mr-1" /> Carica File
                        </Button>
                        {docs.length > 3 && (
                            <select
                                data-testid="filter-doc-type"
                                className="h-8 text-xs rounded-md border border-input bg-transparent px-2 py-1 ml-auto"
                                onChange={(e) => {
                                    const v = e.target.value;
                                    document.querySelectorAll('[data-doc-type]').forEach(el => {
                                        el.style.display = (!v || el.dataset.docType === v) ? '' : 'none';
                                    });
                                }}
                            >
                                <option value="">Tutti i tipi</option>
                                {[...new Set(docs.map(d => d.tipo))].map(t => (
                                    <option key={t} value={t}>{(t || 'altro').replace(/_/g, ' ')}</option>
                                ))}
                            </select>
                        )}
                    </div>
                    {docs.map(d => (
                        <div key={d.doc_id} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`doc-${d.doc_id}`}>
                            <FileUp className="h-3.5 w-3.5 text-[#0055FF] shrink-0" />
                            <div className="flex-1 min-w-0">
                                <span className="font-medium truncate block">{d.nome_file}</span>
                                <span className="text-[10px] text-slate-400">{d.tipo?.replace(/_/g, ' ')} — {(d.size_bytes / 1024).toFixed(0)}KB</span>
                                {d.metadata_estratti?.numero_colata && (
                                    <div className="mt-1 p-1.5 bg-emerald-50 rounded border border-emerald-200">
                                        <span className="block text-[10px] text-emerald-700 font-semibold">Dati Estratti con AI</span>
                                        <div className="grid grid-cols-3 gap-x-2 text-[10px] mt-1">
                                            <div><span className="text-slate-500">Colata:</span> <span className="font-mono font-semibold">{d.metadata_estratti.numero_colata}</span></div>
                                            <div><span className="text-slate-500">Qualità:</span> <span className="font-mono">{d.metadata_estratti.qualita_acciaio || '-'}</span></div>
                                            <div><span className="text-slate-500">Fornitore:</span> <span className="font-mono">{d.metadata_estratti.fornitore || '-'}</span></div>
                                        </div>
                                        {d.metadata_estratti.percentuale_riciclato != null && (
                                            <div className="mt-1 p-1 bg-emerald-100 rounded flex items-center gap-2 text-[10px]">
                                                <Leaf className="h-3 w-3 text-emerald-600" />
                                                <span className="font-semibold text-emerald-800">CAM: {d.metadata_estratti.percentuale_riciclato}% riciclato</span>
                                                {d.metadata_estratti.metodo_produttivo && <span className="text-emerald-600">({(d.metadata_estratti.metodo_produttivo || '').replace(/_/g, ' ')})</span>}
                                                {d.metadata_estratti.certificazione_ambientale && <span className="text-emerald-500">[{d.metadata_estratti.certificazione_ambientale}]</span>}
                                            </div>
                                        )}
                                        {d.metadata_estratti.normativa_riferimento && (
                                            <div className="text-[10px] mt-0.5"><span className="text-slate-500">Normativa:</span> <span className="font-mono">{d.metadata_estratti.normativa_riferimento}</span></div>
                                        )}
                                    </div>
                                )}
                                {/* Multi-profile results */}
                                {d.metadata_estratti?.profili?.length > 0 && (
                                    <div className="mt-1 p-1.5 bg-blue-50 rounded border border-blue-200">
                                        <span className="block text-[10px] text-blue-700 font-semibold">{d.metadata_estratti.profili.length} profili nel certificato</span>
                                        {d.metadata_estratti.profili.map((p, idx) => (
                                            <div key={idx} className="flex items-center gap-2 text-[10px] mt-0.5 py-0.5 border-b border-blue-100 last:border-0">
                                                <span className="font-mono font-semibold text-blue-800">{p.dimensioni || '?'}</span>
                                                <span className="text-slate-500">colata: {p.numero_colata || '?'}</span>
                                                <span className="text-slate-500">{p.qualita_acciaio || ''}</span>
                                                {p.peso_kg && <span className="text-slate-400">{p.peso_kg} kg</span>}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            {/* AI OCR button - show for PDFs that haven't been analyzed yet OR allow re-analysis */}
                            {(d.nome_file?.toLowerCase().endsWith('.pdf') || d.content_type?.includes('pdf') || d.content_type?.includes('image')) && (
                                <Button size="sm" variant="ghost" className={`h-7 text-[10px] border ${d.metadata_estratti?.numero_colata ? 'text-emerald-600 border-emerald-200' : 'text-purple-600 border-purple-200'}`} disabled={parsing === d.doc_id}
                                    onClick={() => handleParseAI(d.doc_id)} data-testid={`btn-parse-${d.doc_id}`}>
                                    {parsing === d.doc_id ? <Loader2 className="h-3 w-3 animate-spin mr-0.5" /> : <Sparkles className="h-3 w-3 mr-0.5" />}
                                    {d.metadata_estratti?.numero_colata ? 'Ri-analizza' : 'Analizza AI'}
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
                            <select
                                value={rdpForm.fornitore_id}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    const f = fornitori.find(x => x.id === val);
                                    setRdpForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                }}
                                className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                data-testid="rdp-fornitore"
                            >
                                <option value="">Seleziona fornitore...</option>
                                {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                            </select>
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
                            <select
                                value={odaForm.fornitore_id}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    const f = fornitori.find(x => x.id === val);
                                    setOdaForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                }}
                                className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                data-testid="oda-fornitore"
                            >
                                <option value="">Seleziona fornitore...</option>
                                {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                            </select>
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

            {/* Arrivo Dialog - Enhanced with material tracking */}
            <Dialog open={arrivoOpen} onOpenChange={setArrivoOpen}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Package className="h-5 w-5 text-amber-600" />
                            Registra Arrivo Materiale
                        </DialogTitle>
                        {commessaNumero && (
                            <DialogDescription>
                                Commessa <span className="font-semibold">{commessaNumero}</span>
                            </DialogDescription>
                        )}
                    </DialogHeader>
                    <div className="space-y-4">
                        {/* DDT Info */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-sm font-medium">N. DDT Fornitore *</Label>
                                <Input 
                                    value={arrivoForm.ddt_fornitore} 
                                    onChange={e => setArrivoForm(f => ({ ...f, ddt_fornitore: e.target.value }))} 
                                    className="mt-1" 
                                    placeholder="es. DDT-2026/0123" 
                                    data-testid="arrivo-ddt" 
                                />
                            </div>
                            <div>
                                <Label className="text-sm font-medium">Data DDT</Label>
                                <Input 
                                    type="date"
                                    value={arrivoForm.data_ddt} 
                                    onChange={e => setArrivoForm(f => ({ ...f, data_ddt: e.target.value }))} 
                                    className="mt-1" 
                                />
                            </div>
                        </div>

                        {/* Fornitore */}
                        <div>
                            <Label className="text-sm font-medium">Fornitore</Label>
                            <select
                                value={arrivoForm.fornitore_id}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    const f = fornitori.find(x => x.id === val);
                                    setArrivoForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                }}
                                className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                data-testid="arrivo-fornitore"
                            >
                                <option value="">Seleziona fornitore...</option>
                                {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                            </select>
                        </div>

                        {/* Materiali table */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label className="text-sm font-medium">Materiali Ricevuti *</Label>
                                <Button type="button" variant="outline" size="sm" onClick={addArrivoMat}>
                                    <Plus className="h-3 w-3 mr-1" /> Aggiungi
                                </Button>
                            </div>
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-amber-50">
                                            <TableHead className="w-[40%] text-xs">Descrizione</TableHead>
                                            <TableHead className="w-[15%] text-xs text-center">Q.tà</TableHead>
                                            <TableHead className="w-[12%] text-xs text-center">U.M.</TableHead>
                                            <TableHead className="w-[20%] text-xs">Rif. Ordine</TableHead>
                                            <TableHead className="w-[8%] text-xs text-center">3.1</TableHead>
                                            <TableHead className="w-[5%]"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {arrivoForm.materiali.map((mat, idx) => (
                                            <TableRow key={mat.id || idx}>
                                                <TableCell className="p-1">
                                                    <Input
                                                        value={mat.descrizione}
                                                        onChange={e => updateArrivoMat(idx, 'descrizione', e.target.value)}
                                                        placeholder="es. Trave IPE 200"
                                                        className="h-8 text-sm"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        type="number"
                                                        value={mat.quantita}
                                                        onChange={e => updateArrivoMat(idx, 'quantita', e.target.value)}
                                                        className="h-8 text-sm text-center"
                                                        min="0"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Select value={mat.unita_misura} onValueChange={v => updateArrivoMat(idx, 'unita_misura', v)}>
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
                                                    <Select value={mat.ordine_id || ''} onValueChange={v => updateArrivoMat(idx, 'ordine_id', v)}>
                                                        <SelectTrigger className="h-8 text-xs">
                                                            <SelectValue placeholder="N/D" />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="">Nessuno</SelectItem>
                                                            {(approv?.ordini || []).map(o => (
                                                                <SelectItem key={o.ordine_id} value={o.ordine_id}>
                                                                    {o.ordine_id.slice(-6)} - {o.fornitore_nome}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell className="p-1 text-center">
                                                    <Checkbox
                                                        checked={mat.richiede_cert_31}
                                                        onCheckedChange={v => updateArrivoMat(idx, 'richiede_cert_31', v)}
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1 text-center">
                                                    {arrivoForm.materiali.length > 1 && (
                                                        <Button
                                                            type="button"
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-7 w-7 p-0 text-red-400 hover:text-red-600"
                                                            onClick={() => removeArrivoMat(idx)}
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
                                ☑️ 3.1 = richiede certificato materiale. Collegherai i certificati dopo la registrazione.
                            </p>
                        </div>

                        {/* Note */}
                        <div>
                            <Label className="text-sm font-medium">Note</Label>
                            <Textarea 
                                value={arrivoForm.note} 
                                onChange={e => setArrivoForm(f => ({ ...f, note: e.target.value }))} 
                                className="mt-1 h-16" 
                                placeholder="Note aggiuntive..."
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setArrivoOpen(false)}>Annulla</Button>
                        <Button 
                            size="sm" 
                            disabled={!arrivoForm.ddt_fornitore.trim() || arrivoForm.materiali.filter(m => m.descrizione.trim()).length === 0}
                            onClick={handleCreateArrivo} 
                            className="bg-amber-600 text-white hover:bg-amber-700" 
                            data-testid="btn-confirm-arrivo"
                        >
                            <Package className="h-4 w-4 mr-1" /> Registra Arrivo
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Conto Lavoro Dialog */}
            <Dialog open={clOpen} onOpenChange={setClOpen}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader><DialogTitle>Nuovo Conto Lavoro (DDT)</DialogTitle><DialogDescription>Compila i dati per la lavorazione esterna</DialogDescription></DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Tipo Lavorazione</Label>
                                <select value={clForm.tipo} onChange={e => setClForm(f => ({ ...f, tipo: e.target.value }))}
                                    className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                    data-testid="cl-tipo">
                                    <option value="verniciatura">Verniciatura</option>
                                    <option value="zincatura">Zincatura a caldo</option>
                                    <option value="sabbiatura">Sabbiatura</option>
                                    <option value="altro">Altro</option>
                                </select>
                            </div>
                            <div>
                                <Label className="text-xs">Fornitore</Label>
                                <select
                                    value={clForm.fornitore_id}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        const f = fornitori.find(x => x.id === val);
                                        setClForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' }));
                                    }}
                                    className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                    data-testid="cl-fornitore"
                                >
                                    <option value="">Seleziona fornitore...</option>
                                    {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                                </select>
                            </div>
                        </div>
                        {clForm.tipo === 'verniciatura' && (
                            <div><Label className="text-xs">Colore RAL</Label>
                                <Input placeholder="es. RAL 9005, RAL 7016..." value={clForm.ral} onChange={e => setClForm(f => ({ ...f, ral: e.target.value }))} className="mt-1 text-sm" data-testid="cl-ral" />
                            </div>
                        )}
                        <div><Label className="text-xs">Causale Trasporto</Label>
                            <Input value={clForm.causale_trasporto} onChange={e => setClForm(f => ({ ...f, causale_trasporto: e.target.value }))} className="mt-1 text-sm" data-testid="cl-causale" />
                        </div>

                        {/* Righe materiali */}
                        <div>
                            <Label className="text-xs font-semibold">Materiali da inviare</Label>
                            <div className="mt-1 border rounded-md overflow-hidden">
                                <table className="w-full text-xs">
                                    <thead><tr className="bg-slate-100 text-left">
                                        <th className="p-2 w-[40%]">Descrizione</th>
                                        <th className="p-2 w-[14%]">Qtà</th>
                                        <th className="p-2 w-[14%]">U.M.</th>
                                        <th className="p-2 w-[18%]">Peso (kg)</th>
                                        <th className="p-2 w-[14%]"></th>
                                    </tr></thead>
                                    <tbody>
                                        {(clForm.righe || []).map((riga, idx) => (
                                            <tr key={riga.id || idx} className="border-t">
                                                <td className="p-1"><Input placeholder="es. IPE 200 L=3000mm" value={riga.descrizione} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], descrizione: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 text-xs" data-testid={`cl-riga-desc-${idx}`} /></td>
                                                <td className="p-1"><Input type="number" value={riga.quantita} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], quantita: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 text-xs" /></td>
                                                <td className="p-1">
                                                    <select value={riga.unita} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], unita: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 w-full text-xs rounded border border-input px-1">
                                                        <option value="pz">pz</option><option value="kg">kg</option><option value="m">m</option><option value="mq">mq</option>
                                                    </select>
                                                </td>
                                                <td className="p-1"><Input type="number" step="0.1" value={riga.peso_kg} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], peso_kg: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 text-xs" /></td>
                                                <td className="p-1 text-center">
                                                    {clForm.righe.length > 1 && <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-500" onClick={() => { const nR = clForm.righe.filter((_, i) => i !== idx); setClForm(f => ({ ...f, righe: nR })); }}><Trash2 className="h-3 w-3" /></Button>}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                <Button variant="ghost" size="sm" className="w-full h-7 text-xs text-blue-600 rounded-none border-t" onClick={() => setClForm(f => ({ ...f, righe: [...f.righe, emptyClLine()] }))} data-testid="cl-add-riga">
                                    <Plus className="h-3 w-3 mr-1" /> Aggiungi riga
                                </Button>
                            </div>
                        </div>

                        <div><Label className="text-xs">Note</Label>
                            <Textarea placeholder="Note aggiuntive..." value={clForm.note} onChange={e => setClForm(f => ({ ...f, note: e.target.value }))} className="mt-1 text-sm" rows={2} data-testid="cl-note" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setClOpen(false)}>Annulla</Button>
                        <DisabledTooltip show={!clForm.fornitore_nome || clForm.righe.filter(r => r.descrizione.trim()).length === 0} reason="Seleziona un fornitore e compila almeno una riga materiale">
                        <Button size="sm" disabled={!clForm.fornitore_nome || clForm.righe.filter(r => r.descrizione.trim()).length === 0} onClick={handleCreateCL} className="bg-[#0055FF] text-white" data-testid="btn-confirm-cl">Crea DDT Conto Lavoro</Button>
                        </DisabledTooltip>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* PDF Preview Dialog */}
            <Dialog open={!!pdfPreviewUrl} onOpenChange={(open) => { if (!open) { setPdfPreviewUrl(null); setPdfExpanded(false); } }}>
                <DialogContent className={`${pdfExpanded ? 'max-w-[95vw] w-[95vw] h-[95vh]' : 'max-w-4xl h-[85vh]'} flex flex-col transition-all duration-200`}>
                    <DialogHeader>
                        <div className="flex items-center justify-between">
                            <DialogTitle className="flex items-center gap-2">
                                <FileSearch className="h-5 w-5 text-blue-600" />
                                {pdfPreviewTitle}
                            </DialogTitle>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 text-slate-500 hover:text-slate-800"
                                onClick={() => setPdfExpanded(!pdfExpanded)}
                                data-testid="pdf-toggle-expand"
                            >
                                {pdfExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                            </Button>
                        </div>
                        <DialogDescription>Verifica il documento prima di inviarlo via email</DialogDescription>
                    </DialogHeader>
                    <div className="flex-1 h-full min-h-0">
                        {pdfPreviewUrl && (
                            <iframe
                                src={pdfPreviewUrl.startsWith('blob:') ? pdfPreviewUrl : `${pdfPreviewUrl}?token=${localStorage.getItem('auth_token')}`}
                                className={`w-full ${pdfExpanded ? 'h-[calc(95vh-140px)]' : 'h-[calc(85vh-140px)]'} border rounded`}
                                title="PDF Preview"
                            />
                        )}
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" onClick={() => { setPdfPreviewUrl(null); setPdfExpanded(false); }}>Chiudi</Button>
                        <Button
                            className="bg-[#0055FF] text-white"
                            onClick={() => {
                                if (pdfPreviewUrl?.includes('/richieste/')) {
                                    const rdpId = pdfPreviewUrl.split('/richieste/')[1]?.split('/')[0];
                                    if (rdpId) handleSendRdpEmail(rdpId);
                                } else if (pdfPreviewUrl?.includes('/ordini/')) {
                                    const ordineId = pdfPreviewUrl.split('/ordini/')[1]?.split('/')[0];
                                    if (ordineId) handleSendOdaEmail(ordineId);
                                }
                                setPdfPreviewUrl(null);
                                setPdfExpanded(false);
                            }}
                        >
                            <Mail className="h-4 w-4 mr-1" /> Invia Email
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Certificate Linking Dialog */}
            <Dialog open={certLinkOpen} onOpenChange={setCertLinkOpen}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-purple-600" />
                            Collega Certificati ai Materiali
                        </DialogTitle>
                        <DialogDescription>
                            {selectedArrivo && `DDT: ${selectedArrivo.ddt_fornitore} — Carica i certificati 3.1 e il sistema li analizzerà automaticamente`}
                        </DialogDescription>
                    </DialogHeader>
                    
                    {selectedArrivo && (
                        <div className="space-y-3">
                            <input
                                ref={certFileRef}
                                type="file"
                                accept=".pdf,image/*"
                                className="hidden"
                                onChange={(e) => {
                                    if (certFileRef.current?.dataset?.matIdx && e.target.files?.[0]) {
                                        handleCertificateUpload(
                                            selectedArrivo.arrivo_id,
                                            parseInt(certFileRef.current.dataset.matIdx),
                                            e.target.files[0]
                                        );
                                        e.target.value = '';
                                    }
                                }}
                            />
                            
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-purple-50">
                                            <TableHead className="w-[40%] text-xs">Materiale</TableHead>
                                            <TableHead className="w-[15%] text-xs text-center">Q.tà</TableHead>
                                            <TableHead className="w-[20%] text-xs">Colata</TableHead>
                                            <TableHead className="w-[25%] text-xs">Azioni</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(selectedArrivo.materiali || []).map((mat, idx) => (
                                            <TableRow key={idx} className={mat.richiede_cert_31 ? '' : 'opacity-50'}>
                                                <TableCell className="text-sm">
                                                    <div>
                                                        {mat.descrizione}
                                                        {mat.richiede_cert_31 && (
                                                            <Badge variant="outline" className="ml-1 text-[9px] bg-amber-50 border-amber-300">3.1</Badge>
                                                        )}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-center text-sm">
                                                    {mat.quantita} {mat.unita_misura}
                                                </TableCell>
                                                <TableCell>
                                                    {mat.numero_colata ? (
                                                        <div className="text-sm">
                                                            <span className="font-mono font-medium text-emerald-700">{mat.numero_colata}</span>
                                                            {mat.qualita_materiale && (
                                                                <span className="text-xs text-slate-500 ml-1">({mat.qualita_materiale})</span>
                                                            )}
                                                        </div>
                                                    ) : mat.richiede_cert_31 ? (
                                                        <span className="text-xs text-red-500">Non collegato</span>
                                                    ) : (
                                                        <span className="text-xs text-slate-400">-</span>
                                                    )}
                                                </TableCell>
                                                <TableCell>
                                                    {mat.richiede_cert_31 && (
                                                        mat.certificato_doc_id ? (
                                                            <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">
                                                                <CheckCircle2 className="h-3 w-3 mr-0.5" /> Collegato
                                                            </Badge>
                                                        ) : (
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                className="h-7 text-xs text-purple-600 border-purple-300"
                                                                disabled={linkingCert?.mat_idx === idx}
                                                                onClick={() => {
                                                                    if (certFileRef.current) {
                                                                        certFileRef.current.dataset.matIdx = idx;
                                                                        certFileRef.current.click();
                                                                    }
                                                                }}
                                                            >
                                                                {linkingCert?.mat_idx === idx ? (
                                                                    <><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Analisi...</>
                                                                ) : (
                                                                    <><FileUp className="h-3 w-3 mr-1" /> Carica Cert.</>
                                                                )}
                                                            </Button>
                                                        )
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            
                            <div className="text-xs text-slate-500 bg-slate-50 p-2 rounded">
                                <strong>AI OCR:</strong> Caricando un certificato 3.1, il sistema estrarrà automaticamente
                                numero colata, qualità del materiale e fornitore. I dati saranno collegati alla tracciabilità EN 1090.
                            </div>
                        </div>
                    )}
                    
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCertLinkOpen(false)}>Chiudi</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* CAM Lotto Dialog */}
            <Dialog open={camLottoOpen} onOpenChange={(open) => { setCamLottoOpen(open); if (!open) setEditingCamLotto(null); }}>
                <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="cam-lotto-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Leaf className="h-5 w-5 text-emerald-600" />
                            {editingCamLotto ? 'Modifica Lotto CAM' : 'Nuovo Lotto Materiale CAM'}
                        </DialogTitle>
                        <DialogDescription>Inserisci i dati del materiale per il calcolo CAM</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Descrizione *</Label>
                                <Input value={camLottoForm.descrizione} onChange={e => setCamLottoForm(f => ({ ...f, descrizione: e.target.value }))} placeholder="es. IPE 200, HEB 160" className="mt-1 h-8 text-sm" data-testid="cam-descrizione" />
                            </div>
                            <div>
                                <Label className="text-xs">Qualità acciaio</Label>
                                <Input value={camLottoForm.qualita_acciaio} onChange={e => setCamLottoForm(f => ({ ...f, qualita_acciaio: e.target.value }))} placeholder="es. S275JR" className="mt-1 h-8 text-sm" data-testid="cam-qualita" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Fornitore</Label>
                                <Input value={camLottoForm.fornitore} onChange={e => setCamLottoForm(f => ({ ...f, fornitore: e.target.value }))} placeholder="Acciaieria" className="mt-1 h-8 text-sm" data-testid="cam-fornitore" />
                            </div>
                            <div>
                                <Label className="text-xs">N. Colata</Label>
                                <Input value={camLottoForm.numero_colata} onChange={e => setCamLottoForm(f => ({ ...f, numero_colata: e.target.value }))} placeholder="Heat number" className="mt-1 h-8 text-sm" data-testid="cam-colata" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Peso (kg) *</Label>
                                <Input type="number" value={camLottoForm.peso_kg} onChange={e => setCamLottoForm(f => ({ ...f, peso_kg: e.target.value }))} className="mt-1 h-8 text-sm" data-testid="cam-peso" />
                            </div>
                            <div>
                                <Label className="text-xs">% Riciclato *</Label>
                                <Input type="number" min="0" max="100" value={camLottoForm.percentuale_riciclato} onChange={e => setCamLottoForm(f => ({ ...f, percentuale_riciclato: e.target.value }))} className="mt-1 h-8 text-sm" data-testid="cam-perc-riciclato" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Metodo produttivo</Label>
                                <Select value={camLottoForm.metodo_produttivo} onValueChange={v => setCamLottoForm(f => ({ ...f, metodo_produttivo: v }))}>
                                    <SelectTrigger className="mt-1 h-8 text-xs" data-testid="cam-metodo"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="forno_elettrico_non_legato">Forno Elettrico (non legato) - soglia 75%</SelectItem>
                                        <SelectItem value="forno_elettrico_legato">Forno Elettrico (legato) - soglia 60%</SelectItem>
                                        <SelectItem value="ciclo_integrale">Ciclo Integrale (altoforno) - soglia 12%</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-xs">Certificazione</Label>
                                <Select value={camLottoForm.tipo_certificazione} onValueChange={v => setCamLottoForm(f => ({ ...f, tipo_certificazione: v }))}>
                                    <SelectTrigger className="mt-1 h-8 text-xs" data-testid="cam-certificazione"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="epd">EPD (ISO 14025, EN 15804)</SelectItem>
                                        <SelectItem value="remade_in_italy">ReMade in Italy</SelectItem>
                                        <SelectItem value="dichiarazione_produttore">Dichiarazione Produttore</SelectItem>
                                        <SelectItem value="altra_accreditata">Altra certificazione</SelectItem>
                                        <SelectItem value="nessuna">Nessuna</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">N. Certificazione</Label>
                                <Input value={camLottoForm.numero_certificazione} onChange={e => setCamLottoForm(f => ({ ...f, numero_certificazione: e.target.value }))} className="mt-1 h-8 text-sm" data-testid="cam-num-cert" />
                            </div>
                            <div>
                                <Label className="text-xs">Ente certificatore</Label>
                                <Input value={camLottoForm.ente_certificatore} onChange={e => setCamLottoForm(f => ({ ...f, ente_certificatore: e.target.value }))} placeholder="es. ICMQ, Bureau Veritas" className="mt-1 h-8 text-sm" data-testid="cam-ente" />
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Checkbox checked={camLottoForm.uso_strutturale} onCheckedChange={v => setCamLottoForm(f => ({ ...f, uso_strutturale: v }))} id="cam-strutturale" data-testid="cam-strutturale" />
                            <Label htmlFor="cam-strutturale" className="text-xs">Uso strutturale (soglie più restrittive)</Label>
                        </div>
                        <div className="p-2 bg-slate-50 rounded text-[10px] text-slate-500">
                            <strong>Soglie CAM (DM 256/2022):</strong> Forno el. non legato ≥ 75% | Forno el. legato ≥ 60% | Ciclo integrale ≥ 12%
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setCamLottoOpen(false)}>Annulla</Button>
                        <Button size="sm" onClick={handleCreateCamLotto} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-save-cam-lotto">
                            {editingCamLotto ? 'Aggiorna' : 'Crea Lotto'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Email Preview Dialog */}
            <EmailPreviewDialog
                open={emailPreview.open}
                onOpenChange={(open) => setEmailPreview(prev => ({ ...prev, open }))}
                previewUrl={emailPreview.previewUrl}
                sendUrl={emailPreview.sendUrl}
                onSent={() => { fetchData(); onRefresh?.(); }}
            />
        </div>
    );
}
