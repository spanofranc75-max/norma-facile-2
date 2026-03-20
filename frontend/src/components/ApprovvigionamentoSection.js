/**
 * ApprovvigionamentoSection — RdP, OdA, Arrivi, Prelievo da Magazzino, Certificati
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { useState, useRef } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import EmailPreviewDialog from './EmailPreviewDialog';
import { toast } from 'sonner';
import {
    ShoppingCart, Package, Truck, Plus, Trash2, FileText,
    Mail, MailCheck, FileSearch, Loader2, Sparkles, FileUp,
    CheckCircle2, Maximize2, Minimize2,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

function StatoBadge({ stato }) {
    const STATO_COLORS = {
        da_fare: 'bg-slate-100 text-slate-600', in_corso: 'bg-blue-100 text-blue-700',
        completato: 'bg-emerald-100 text-emerald-700', inviata: 'bg-blue-100 text-blue-700',
        ricevuta: 'bg-amber-100 text-amber-700', accettata: 'bg-emerald-100 text-emerald-700',
        rifiutata: 'bg-red-100 text-red-700', inviato: 'bg-blue-100 text-blue-700',
        confermato: 'bg-emerald-100 text-emerald-700', consegnato: 'bg-emerald-100 text-emerald-700',
        da_verificare: 'bg-amber-100 text-amber-700', verificato: 'bg-emerald-100 text-emerald-700',
    };
    return <Badge className={`text-[9px] ${STATO_COLORS[stato] || 'bg-slate-100 text-slate-600'}`}>{(stato || '').replace(/_/g, ' ')}</Badge>;
}

export default function ApprovvigionamentoSection({ commessaId, commessaNumero, approv, fornitori, onRefresh }) {
    const certFileRef = useRef();

    // Dialog states
    const [rdpOpen, setRdpOpen] = useState(false);
    const [odaOpen, setOdaOpen] = useState(false);
    const [arrivoOpen, setArrivoOpen] = useState(false);
    const [prelievoOpen, setPrelievoOpen] = useState(false);
    const [certLinkOpen, setCertLinkOpen] = useState(false);
    const [selectedArrivo, setSelectedArrivo] = useState(null);
    const [linkingCert, setLinkingCert] = useState(null);
    const [sendingEmail, setSendingEmail] = useState(null);

    // PDF Preview
    const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
    const [pdfPreviewTitle, setPdfPreviewTitle] = useState('');
    const [pdfExpanded, setPdfExpanded] = useState(false);
    // Email Preview
    const [emailPreview, setEmailPreview] = useState({ open: false, previewUrl: '', sendUrl: '' });

    // Prelievo state
    const [articoliCatalogo, setArticoliCatalogo] = useState([]);
    const [prelievoForm, setPrelievoForm] = useState({ articolo_id: '', quantita: 1, note: '' });
    const [prelievoLoading, setPrelievoLoading] = useState(false);

    // ── Line templates ──
    const emptyRdpLine = () => ({ id: `l${Date.now()}`, descrizione: '', quantita: 1, unita_misura: 'kg', richiede_cert_31: false });
    const emptyOdaLine = () => ({ id: `l${Date.now()}`, descrizione: '', quantita: 1, unita_misura: 'kg', prezzo_unitario: 0, richiede_cert_31: false });
    const emptyArrivoMat = () => ({ id: `m${Date.now()}`, descrizione: '', quantita: 1, unita_misura: 'kg', ordine_id: '', richiede_cert_31: false, prezzo_unitario: 0, quantita_utilizzata: '' });

    // Form states
    const [rdpForm, setRdpForm] = useState({ fornitore_nome: '', fornitore_id: '', righe: [emptyRdpLine()], note: '' });
    const [odaForm, setOdaForm] = useState({ fornitore_nome: '', fornitore_id: '', righe: [emptyOdaLine()], note: '' });
    const [arrivoForm, setArrivoForm] = useState({ ddt_fornitore: '', data_ddt: '', fornitore_nome: '', fornitore_id: '', materiali: [emptyArrivoMat()], note: '' });

    // RdP line helpers
    const addRdpLine = () => setRdpForm(f => ({ ...f, righe: [...f.righe, emptyRdpLine()] }));
    const removeRdpLine = (idx) => setRdpForm(f => ({ ...f, righe: f.righe.filter((_, i) => i !== idx) }));
    const updateRdpLine = (idx, field, value) => setRdpForm(f => { const righe = [...f.righe]; righe[idx] = { ...righe[idx], [field]: value }; return { ...f, righe }; });

    // OdA line helpers
    const addOdaLine = () => setOdaForm(f => ({ ...f, righe: [...f.righe, emptyOdaLine()] }));
    const removeOdaLine = (idx) => setOdaForm(f => ({ ...f, righe: f.righe.filter((_, i) => i !== idx) }));
    const updateOdaLine = (idx, field, value) => setOdaForm(f => { const righe = [...f.righe]; righe[idx] = { ...righe[idx], [field]: value }; return { ...f, righe }; });
    const odaTotale = odaForm.righe.reduce((sum, r) => sum + (parseFloat(r.quantita) || 0) * (parseFloat(r.prezzo_unitario) || 0), 0);

    // Arrivo line helpers
    const addArrivoMat = () => setArrivoForm(f => ({ ...f, materiali: [...f.materiali, emptyArrivoMat()] }));
    const removeArrivoMat = (idx) => setArrivoForm(f => ({ ...f, materiali: f.materiali.filter((_, i) => i !== idx) }));
    const updateArrivoMat = (idx, field, value) => setArrivoForm(f => { const materiali = [...f.materiali]; materiali[idx] = { ...materiali[idx], [field]: value }; return { ...f, materiali }; });

    // ── Handlers ──
    const handleCreateRdP = async () => {
        if (rdpForm.righe.filter(r => r.descrizione.trim()).length === 0) { toast.error('Inserisci almeno una riga'); return; }
        try {
            const payload = { ...rdpForm, righe: rdpForm.righe.filter(r => r.descrizione.trim()).map(r => ({ descrizione: r.descrizione, quantita: parseFloat(r.quantita) || 1, unita_misura: r.unita_misura, richiede_cert_31: r.richiede_cert_31 })) };
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/richieste`, { method: 'POST', body: payload });
            toast.success('RdP inviata');
            setRdpOpen(false);
            setRdpForm({ fornitore_nome: '', fornitore_id: '', righe: [emptyRdpLine()], note: '' });
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateRdP = async (rdpId, stato, importo) => {
        const form = new FormData();
        form.append('stato', stato);
        if (importo) form.append('importo', importo);
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}`, { method: 'PUT', body: form, credentials: 'include' });
            if (!res.ok) throw new Error('Errore');
            toast.success(`RdP → ${stato}`);
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleCreateOdA = async () => {
        if (odaForm.righe.filter(r => r.descrizione.trim()).length === 0) { toast.error('Inserisci almeno una riga'); return; }
        try {
            const payload = { ...odaForm, righe: odaForm.righe.filter(r => r.descrizione.trim()).map(r => ({ descrizione: r.descrizione, quantita: parseFloat(r.quantita) || 1, unita_misura: r.unita_misura, prezzo_unitario: parseFloat(r.prezzo_unitario) || 0, richiede_cert_31: r.richiede_cert_31 })), importo_totale: odaTotale };
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/ordini`, { method: 'POST', body: payload });
            toast.success('Ordine emesso');
            setOdaOpen(false);
            setOdaForm({ fornitore_nome: '', fornitore_id: '', righe: [emptyOdaLine()], note: '' });
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateOrdine = async (ordineId, stato) => {
        const form = new FormData();
        form.append('stato', stato);
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}`, { method: 'PUT', body: form, credentials: 'include' });
            if (!res.ok) throw new Error('Errore');
            toast.success(`Ordine → ${stato}`);
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleCreateOdaFromRdp = (rdp) => {
        const righeFromRdp = (rdp.righe || []).map(r => ({ id: `l${Date.now()}_${Math.random().toString(36).slice(2, 6)}`, descrizione: r.descrizione, quantita: r.quantita || 1, unita_misura: r.unita_misura || 'kg', prezzo_unitario: 0, richiede_cert_31: r.richiede_cert_31 || false }));
        setOdaForm({ fornitore_nome: rdp.fornitore_nome, fornitore_id: rdp.fornitore_id || '', righe: righeFromRdp.length > 0 ? righeFromRdp : [emptyOdaLine()], note: `Rif. RdP: ${rdp.rdp_id}`, riferimento_rdp_id: rdp.rdp_id });
        setOdaOpen(true);
        toast.info('OdA pre-compilato dalla RdP - aggiungi i prezzi e invia!');
    };

    const handleCreateArrivo = async () => {
        if (!arrivoForm.ddt_fornitore.trim()) { toast.error('Inserisci il numero DDT fornitore'); return; }
        if (arrivoForm.materiali.filter(m => m.descrizione.trim()).length === 0) { toast.error('Inserisci almeno un materiale'); return; }
        try {
            const payload = {
                ...arrivoForm,
                materiali: arrivoForm.materiali.filter(m => m.descrizione.trim()).map(m => {
                    const mapped = { descrizione: m.descrizione, quantita: parseFloat(m.quantita) || 1, unita_misura: m.unita_misura, ordine_id: m.ordine_id || '', richiede_cert_31: m.richiede_cert_31 };
                    if (m.prezzo_unitario && parseFloat(m.prezzo_unitario) > 0) mapped.prezzo_unitario = parseFloat(m.prezzo_unitario);
                    const qtyUsed = parseFloat(m.quantita_utilizzata);
                    if (!isNaN(qtyUsed) && qtyUsed >= 0 && qtyUsed < mapped.quantita) mapped.quantita_utilizzata = qtyUsed;
                    return mapped;
                }),
            };
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/arrivi`, { method: 'POST', body: payload });
            toast.success('Arrivo registrato');
            setArrivoOpen(false);
            setArrivoForm({ ddt_fornitore: '', data_ddt: '', fornitore_nome: '', fornitore_id: '', materiali: [emptyArrivoMat()], note: '' });
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleVerificaArrivo = async (arrivoId) => {
        try {
            await apiRequest(`/commesse/${commessaId}/approvvigionamento/arrivi/${arrivoId}/verifica`, { method: 'PUT' });
            toast.success('Arrivo verificato');
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const openPrelievoDialog = async () => {
        try {
            const data = await apiRequest('/articoli');
            const withStock = (data.articoli || data || []).filter(a => (a.giacenza || 0) > 0);
            setArticoliCatalogo(withStock);
            setPrelievoForm({ articolo_id: '', quantita: 1, note: '' });
            setPrelievoOpen(true);
        } catch (e) { toast.error('Errore caricamento articoli: ' + e.message); }
    };

    const handlePrelievo = async () => {
        if (!prelievoForm.articolo_id) { toast.error('Seleziona un articolo'); return; }
        if (!prelievoForm.quantita || parseFloat(prelievoForm.quantita) <= 0) { toast.error('Quantità non valida'); return; }
        setPrelievoLoading(true);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/preleva-da-magazzino`, { method: 'POST', body: { articolo_id: prelievoForm.articolo_id, quantita: parseFloat(prelievoForm.quantita), note: prelievoForm.note || '' } });
            toast.success(res.message || 'Prelievo registrato');
            setPrelievoOpen(false);
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
        finally { setPrelievoLoading(false); }
    };

    // PDF/Email handlers
    const handlePreviewRdpPdf = (rdpId) => { setPdfPreviewTitle(`Anteprima RdP ${rdpId}`); setPdfPreviewUrl(`${API}/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/pdf`); };
    const handlePreviewOdaPdf = (ordineId) => { setPdfPreviewTitle(`Anteprima OdA ${ordineId}`); setPdfPreviewUrl(`${API}/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/pdf`); };
    const handleSendRdpEmail = (rdpId) => { setEmailPreview({ open: true, previewUrl: `/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/preview-email`, sendUrl: `/api/commesse/${commessaId}/approvvigionamento/richieste/${rdpId}/send-email` }); };
    const handleSendOdaEmail = (ordineId) => { setEmailPreview({ open: true, previewUrl: `/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/preview-email`, sendUrl: `/api/commesse/${commessaId}/approvvigionamento/ordini/${ordineId}/send-email` }); };

    // Certificate linking
    const handleOpenCertLink = (arrivo) => { setSelectedArrivo(arrivo); setCertLinkOpen(true); };
    const handleCertificateUpload = async (arrivoId, matIdx, file) => {
        if (!file) return;
        setLinkingCert({ arrivo_id: arrivoId, mat_idx: matIdx });
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('tipo', 'certificato_31');
            const uploadRes = await fetch(`${API}/api/commesse/${commessaId}/documenti`, { method: 'POST', body: formData, credentials: 'include' });
            if (!uploadRes.ok) throw new Error('Errore upload certificato');
            const uploadData = await uploadRes.json();
            const docId = uploadData.doc_id;
            toast.info('Analisi AI del certificato in corso...');
            const parseRes = await apiRequest(`/commesse/${commessaId}/documenti/${docId}/parse-certificato`, { method: 'POST' });
            const linkForm = new FormData();
            linkForm.append('certificato_doc_id', docId);
            if (parseRes.extracted?.numero_colata) linkForm.append('numero_colata', parseRes.extracted.numero_colata);
            if (parseRes.extracted?.qualita_materiale) linkForm.append('qualita_materiale', parseRes.extracted.qualita_materiale);
            if (parseRes.extracted?.fornitore) linkForm.append('fornitore_materiale', parseRes.extracted.fornitore);
            await fetch(`${API}/api/commesse/${commessaId}/approvvigionamento/arrivi/${arrivoId}/materiale/${matIdx}/certificato`, { method: 'PUT', body: linkForm, credentials: 'include' });
            toast.success(`Certificato collegato! Colata: ${parseRes.extracted?.numero_colata || 'N/D'}`);
            onRefresh?.();
            if (selectedArrivo) {
                const updatedMateriali = [...selectedArrivo.materiali];
                updatedMateriali[matIdx] = { ...updatedMateriali[matIdx], certificato_doc_id: docId, numero_colata: parseRes.extracted?.numero_colata || '', qualita_materiale: parseRes.extracted?.qualita_materiale || '' };
                setSelectedArrivo({ ...selectedArrivo, materiali: updatedMateriali });
            }
        } catch (e) { toast.error(e.message || 'Errore collegamento certificato'); }
        finally { setLinkingCert(null); }
    };

    return (
        <>
            <div className="space-y-3" data-testid="approvvigionamento-section">
                <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="outline" onClick={() => setRdpOpen(true)} className="text-xs" data-testid="btn-new-rdp"><Plus className="h-3 w-3 mr-1" /> RdP Fornitore</Button>
                    <Button size="sm" variant="outline" onClick={() => setOdaOpen(true)} className="text-xs" data-testid="btn-new-oda"><Plus className="h-3 w-3 mr-1" /> Ordine (OdA)</Button>
                    <Button size="sm" variant="outline" onClick={() => setArrivoOpen(true)} className="text-xs" data-testid="btn-new-arrivo"><Package className="h-3 w-3 mr-1" /> Registra Arrivo</Button>
                    <Button size="sm" variant="outline" onClick={openPrelievoDialog} className="text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50" data-testid="btn-preleva-magazzino"><Truck className="h-3 w-3 mr-1" /> Preleva da Magazzino</Button>
                </div>

                {/* Richieste Preventivo */}
                {(approv.richieste || []).map(r => (
                    <div key={r.rdp_id} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`rdp-${r.rdp_id}`}>
                        <ShoppingCart className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="font-medium truncate">RdP &rarr; {r.fornitore_nome}</span>
                                {r.email_sent ? (
                                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded text-[9px] font-medium" title={`Inviata a ${r.email_sent_to}`}><MailCheck className="h-2.5 w-2.5" /> Inviata</span>
                                ) : (
                                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[9px] font-medium"><Mail className="h-2.5 w-2.5" /> Bozza</span>
                                )}
                            </div>
                            {r.righe?.length > 0 && <div className="text-[10px] text-slate-500 mt-0.5">{r.righe.length} righe — {r.righe.filter(x => x.richiede_cert_31).length > 0 && `${r.righe.filter(x => x.richiede_cert_31).length} cert. 3.1`}</div>}
                        </div>
                        <StatoBadge stato={r.stato} />
                        {r.importo_proposto && <span className="font-mono text-[10px]">{fmtEur(r.importo_proposto)}</span>}
                        <div className="flex items-center gap-1">
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handlePreviewRdpPdf(r.rdp_id)} title="Anteprima PDF"><FileSearch className="h-3.5 w-3.5 text-blue-600" /></Button>
                            {!r.email_sent && <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handleSendRdpEmail(r.rdp_id)} disabled={sendingEmail === r.rdp_id} title="Invia Email">{sendingEmail === r.rdp_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5 text-amber-600" />}</Button>}
                            {r.stato === 'inviata' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateRdP(r.rdp_id, 'ricevuta')}>Ricevuta</Button>}
                            {r.stato === 'ricevuta' && (<><Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleUpdateRdP(r.rdp_id, 'accettata')}>Accetta</Button><Button size="sm" variant="ghost" className="h-6 text-[10px] text-red-600" onClick={() => handleUpdateRdP(r.rdp_id, 'rifiutata')}>Rifiuta</Button></>)}
                            {r.stato === 'accettata' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600 font-medium" onClick={() => handleCreateOdaFromRdp(r)} title="Crea Ordine da questa RdP"><Package className="h-3 w-3 mr-0.5" /> Crea OdA</Button>}
                        </div>
                    </div>
                ))}

                {/* Ordini */}
                {(approv.ordini || []).map(o => (
                    <div key={o.ordine_id} className="flex items-center gap-2 p-2 bg-blue-50 rounded text-xs" data-testid={`oda-${o.ordine_id}`}>
                        <Truck className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="font-medium truncate">OdA &rarr; {o.fornitore_nome}</span>
                                {o.email_sent ? (
                                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded text-[9px] font-medium" title={`Inviata a ${o.email_sent_to}`}><MailCheck className="h-2.5 w-2.5" /> Inviata</span>
                                ) : (
                                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[9px] font-medium"><Mail className="h-2.5 w-2.5" /> Bozza</span>
                                )}
                            </div>
                            {o.righe?.length > 0 && <div className="text-[10px] text-slate-500 mt-0.5">{o.righe.length} righe — {o.righe.filter(x => x.richiede_cert_31).length > 0 && `${o.righe.filter(x => x.richiede_cert_31).length} cert. 3.1`}</div>}
                        </div>
                        <span className="font-mono text-[10px] font-semibold">{fmtEur(o.importo_totale)}</span>
                        <StatoBadge stato={o.stato} />
                        <div className="flex items-center gap-1">
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handlePreviewOdaPdf(o.ordine_id)} title="Anteprima PDF"><FileSearch className="h-3.5 w-3.5 text-emerald-600" /></Button>
                            {!o.email_sent && <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handleSendOdaEmail(o.ordine_id)} disabled={sendingEmail === o.ordine_id} title="Invia Email">{sendingEmail === o.ordine_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5 text-amber-600" />}</Button>}
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
                                {a.materiali?.length > 0 && <div className="text-[10px] text-slate-500">{a.materiali.length} materiali — {a.materiali.filter(m => m.certificato_doc_id || m.numero_colata).length} con certificato</div>}
                            </div>
                            <StatoBadge stato={a.stato} />
                            <div className="flex items-center gap-1">
                                {a.materiali?.some(m => m.richiede_cert_31 && !m.certificato_doc_id) && (
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-purple-600" onClick={() => handleOpenCertLink(a)} title="Collega certificati ai materiali"><Sparkles className="h-3 w-3 mr-0.5" /> Certificati</Button>
                                )}
                                {a.stato === 'da_verificare' && (
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-600" onClick={() => handleVerificaArrivo(a.arrivo_id)}><CheckCircle2 className="h-3 w-3 mr-0.5" /> Verifica</Button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* ── RdP Dialog ── */}
            <Dialog open={rdpOpen} onOpenChange={setRdpOpen}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><FileText className="h-5 w-5 text-blue-600" /> Nuova Richiesta di Preventivo (RdP)</DialogTitle>
                        {commessaNumero && <DialogDescription>Riferimento: Commessa <span className="font-semibold">{commessaNumero}</span></DialogDescription>}
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <Label className="text-sm font-medium">Fornitore *</Label>
                            <select value={rdpForm.fornitore_id} onChange={(e) => { const val = e.target.value; const f = fornitori.find(x => x.id === val); setRdpForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' })); }} className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="rdp-fornitore">
                                <option value="">Seleziona fornitore...</option>
                                {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                            </select>
                        </div>
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label className="text-sm font-medium">Materiali Richiesti *</Label>
                                <Button type="button" variant="outline" size="sm" onClick={addRdpLine} data-testid="rdp-add-line"><Plus className="h-3 w-3 mr-1" /> Aggiungi riga</Button>
                            </div>
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader><TableRow className="bg-slate-50"><TableHead className="w-[45%] text-xs">Descrizione</TableHead><TableHead className="w-[15%] text-xs text-center">Quantità</TableHead><TableHead className="w-[15%] text-xs text-center">U.M.</TableHead><TableHead className="w-[15%] text-xs text-center">Cert. 3.1</TableHead><TableHead className="w-[10%]"></TableHead></TableRow></TableHeader>
                                    <TableBody>
                                        {rdpForm.righe.map((riga, idx) => (
                                            <TableRow key={riga.id || idx}>
                                                <TableCell className="p-1.5"><Input value={riga.descrizione} onChange={e => updateRdpLine(idx, 'descrizione', e.target.value)} placeholder="es. IPE 200 S275JR" className="h-9 text-sm" data-testid={`rdp-line-desc-${idx}`} /></TableCell>
                                                <TableCell className="p-1.5"><Input type="number" value={riga.quantita} onChange={e => updateRdpLine(idx, 'quantita', e.target.value)} className="h-9 text-sm text-center" min="0" /></TableCell>
                                                <TableCell className="p-1.5"><Select value={riga.unita_misura} onValueChange={v => updateRdpLine(idx, 'unita_misura', v)}><SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="kg">kg</SelectItem><SelectItem value="pz">pz</SelectItem><SelectItem value="ml">ml</SelectItem><SelectItem value="mq">mq</SelectItem><SelectItem value="t">t</SelectItem></SelectContent></Select></TableCell>
                                                <TableCell className="p-1 text-center"><Checkbox checked={riga.richiede_cert_31} onCheckedChange={v => updateRdpLine(idx, 'richiede_cert_31', v)} /></TableCell>
                                                <TableCell className="p-1 text-center">{rdpForm.righe.length > 1 && <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400 hover:text-red-600" onClick={() => removeRdpLine(idx)}><Trash2 className="h-3.5 w-3.5" /></Button>}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        </div>
                        <div><Label className="text-sm font-medium">Note</Label><Textarea value={rdpForm.note} onChange={e => setRdpForm(f => ({ ...f, note: e.target.value }))} className="mt-1 h-16" placeholder="Note aggiuntive..." /></div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setRdpOpen(false)}>Annulla</Button>
                        <Button size="sm" disabled={rdpForm.righe.filter(r => r.descrizione.trim()).length === 0} onClick={handleCreateRdP} className="bg-[#0055FF] text-white" data-testid="btn-confirm-rdp"><ShoppingCart className="h-4 w-4 mr-1" /> Invia RdP</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── OdA Dialog ── */}
            <Dialog open={odaOpen} onOpenChange={setOdaOpen}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><Truck className="h-5 w-5 text-emerald-600" /> Nuovo Ordine di Acquisto (OdA)</DialogTitle>
                        {commessaNumero && <DialogDescription>Riferimento: Commessa <span className="font-semibold">{commessaNumero}</span></DialogDescription>}
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <Label className="text-sm font-medium">Fornitore *</Label>
                            <select value={odaForm.fornitore_id} onChange={(e) => { const val = e.target.value; const f = fornitori.find(x => x.id === val); setOdaForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' })); }} className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="oda-fornitore">
                                <option value="">Seleziona fornitore...</option>
                                {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                            </select>
                        </div>
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label className="text-sm font-medium">Materiali *</Label>
                                <Button type="button" variant="outline" size="sm" onClick={addOdaLine} data-testid="oda-add-line"><Plus className="h-3 w-3 mr-1" /> Aggiungi riga</Button>
                            </div>
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader><TableRow className="bg-blue-50"><TableHead className="w-[30%] text-xs">Descrizione</TableHead><TableHead className="w-[12%] text-xs text-center">Q.tà</TableHead><TableHead className="w-[10%] text-xs text-center">U.M.</TableHead><TableHead className="w-[15%] text-xs text-center">€/unità</TableHead><TableHead className="w-[15%] text-xs text-center">Totale</TableHead><TableHead className="w-[8%] text-xs text-center">3.1</TableHead><TableHead className="w-[10%]"></TableHead></TableRow></TableHeader>
                                    <TableBody>
                                        {odaForm.righe.map((riga, idx) => (
                                            <TableRow key={riga.id || idx}>
                                                <TableCell className="p-1.5"><Input value={riga.descrizione} onChange={e => updateOdaLine(idx, 'descrizione', e.target.value)} placeholder="es. IPE 200 S275JR" className="h-9 text-sm" data-testid={`oda-line-desc-${idx}`} /></TableCell>
                                                <TableCell className="p-1.5"><Input type="number" value={riga.quantita} onChange={e => updateOdaLine(idx, 'quantita', e.target.value)} className="h-9 text-sm text-center" min="0" /></TableCell>
                                                <TableCell className="p-1.5"><Select value={riga.unita_misura} onValueChange={v => updateOdaLine(idx, 'unita_misura', v)}><SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="kg">kg</SelectItem><SelectItem value="pz">pz</SelectItem><SelectItem value="ml">ml</SelectItem><SelectItem value="mq">mq</SelectItem><SelectItem value="t">t</SelectItem></SelectContent></Select></TableCell>
                                                <TableCell className="p-1.5"><Input type="number" step="0.01" value={riga.prezzo_unitario} onChange={e => updateOdaLine(idx, 'prezzo_unitario', e.target.value)} className="h-9 text-sm text-center" min="0" /></TableCell>
                                                <TableCell className="p-1.5 text-center text-xs font-mono">{fmtEur((parseFloat(riga.quantita) || 0) * (parseFloat(riga.prezzo_unitario) || 0))}</TableCell>
                                                <TableCell className="p-1 text-center"><Checkbox checked={riga.richiede_cert_31} onCheckedChange={v => updateOdaLine(idx, 'richiede_cert_31', v)} /></TableCell>
                                                <TableCell className="p-1 text-center">{odaForm.righe.length > 1 && <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400 hover:text-red-600" onClick={() => removeOdaLine(idx)}><Trash2 className="h-3.5 w-3.5" /></Button>}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <div className="text-right mt-1"><span className="text-xs font-semibold">Totale: {fmtEur(odaTotale)}</span></div>
                        </div>
                        <div><Label className="text-sm font-medium">Note</Label><Textarea value={odaForm.note} onChange={e => setOdaForm(f => ({ ...f, note: e.target.value }))} className="mt-1 h-16" placeholder="Note aggiuntive..." /></div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setOdaOpen(false)}>Annulla</Button>
                        <Button size="sm" disabled={odaForm.righe.filter(r => r.descrizione.trim()).length === 0} onClick={handleCreateOdA} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-confirm-oda"><Truck className="h-4 w-4 mr-1" /> Emetti Ordine</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Arrivo Dialog ── */}
            <Dialog open={arrivoOpen} onOpenChange={setArrivoOpen}>
                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><Package className="h-5 w-5 text-amber-600" /> Registra Arrivo Materiale</DialogTitle>
                        {commessaNumero && <DialogDescription>Commessa <span className="font-semibold">{commessaNumero}</span></DialogDescription>}
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-sm font-medium">N° DDT Fornitore *</Label><Input value={arrivoForm.ddt_fornitore} onChange={e => setArrivoForm(f => ({ ...f, ddt_fornitore: e.target.value }))} className="mt-1" data-testid="arrivo-ddt" /></div>
                            <div><Label className="text-sm font-medium">Data DDT</Label><Input type="date" value={arrivoForm.data_ddt} onChange={e => setArrivoForm(f => ({ ...f, data_ddt: e.target.value }))} className="mt-1" data-testid="arrivo-data" /></div>
                        </div>
                        <div>
                            <Label className="text-sm font-medium">Fornitore</Label>
                            <select value={arrivoForm.fornitore_id} onChange={(e) => { const val = e.target.value; const f = fornitori.find(x => x.id === val); setArrivoForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' })); }} className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="arrivo-fornitore">
                                <option value="">Seleziona fornitore...</option>
                                {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                            </select>
                        </div>
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label className="text-sm font-medium">Materiali Ricevuti *</Label>
                                <Button type="button" variant="outline" size="sm" onClick={addArrivoMat}><Plus className="h-3 w-3 mr-1" /> Aggiungi</Button>
                            </div>
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader><TableRow className="bg-amber-50"><TableHead className="w-[25%] text-xs">Descrizione</TableHead><TableHead className="w-[8%] text-xs text-center">Q.tà</TableHead><TableHead className="w-[7%] text-xs text-center">U.M.</TableHead><TableHead className="w-[10%] text-xs text-center">€/unità</TableHead><TableHead className="w-[10%] text-xs text-center" title="Lascia vuoto se usi tutto.">Q.tà Usata</TableHead><TableHead className="w-[28%] text-xs">Rif. Ordine</TableHead><TableHead className="w-[5%] text-xs text-center">3.1</TableHead><TableHead className="w-[4%]"></TableHead></TableRow></TableHeader>
                                    <TableBody>
                                        {arrivoForm.materiali.map((mat, idx) => (
                                            <TableRow key={mat.id || idx}>
                                                <TableCell className="p-1.5"><Input value={mat.descrizione} onChange={e => updateArrivoMat(idx, 'descrizione', e.target.value)} className="h-9 text-sm" /></TableCell>
                                                <TableCell className="p-1.5"><Input type="number" value={mat.quantita} onChange={e => updateArrivoMat(idx, 'quantita', e.target.value)} className="h-9 text-sm text-center" min="0" /></TableCell>
                                                <TableCell className="p-1.5"><Select value={mat.unita_misura} onValueChange={v => updateArrivoMat(idx, 'unita_misura', v)}><SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="kg">kg</SelectItem><SelectItem value="pz">pz</SelectItem><SelectItem value="ml">ml</SelectItem><SelectItem value="mq">mq</SelectItem><SelectItem value="t">t</SelectItem></SelectContent></Select></TableCell>
                                                <TableCell className="p-1.5"><Input type="number" value={mat.prezzo_unitario || ''} onChange={e => updateArrivoMat(idx, 'prezzo_unitario', e.target.value)} className="h-9 text-sm text-center" min="0" step="0.01" data-testid={`arrivo-mat-${idx}-prezzo`} /></TableCell>
                                                <TableCell className="p-1.5"><Input type="number" value={mat.quantita_utilizzata} onChange={e => updateArrivoMat(idx, 'quantita_utilizzata', e.target.value)} className="h-9 text-sm text-center" min="0" step="0.01" title="Lascia vuoto se usi tutto." data-testid={`arrivo-mat-${idx}-qty-usata`} /></TableCell>
                                                <TableCell className="p-1.5"><Select value={mat.ordine_id || '__none__'} onValueChange={v => updateArrivoMat(idx, 'ordine_id', v === '__none__' ? '' : v)}><SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="__none__">Nessuno</SelectItem>{(approv?.ordini || []).map(o => (<SelectItem key={o.ordine_id} value={o.ordine_id}>{o.ordine_id.slice(-6)} - {o.fornitore_nome}</SelectItem>))}</SelectContent></Select></TableCell>
                                                <TableCell className="p-1 text-center"><Checkbox checked={mat.richiede_cert_31} onCheckedChange={v => updateArrivoMat(idx, 'richiede_cert_31', v)} /></TableCell>
                                                <TableCell className="p-1 text-center">{arrivoForm.materiali.length > 1 && <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400 hover:text-red-600" onClick={() => removeArrivoMat(idx)}><Trash2 className="h-3.5 w-3.5" /></Button>}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        </div>
                        <div><Label className="text-sm font-medium">Note</Label><Textarea value={arrivoForm.note} onChange={e => setArrivoForm(f => ({ ...f, note: e.target.value }))} className="mt-1 h-16" placeholder="Note aggiuntive..." /></div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setArrivoOpen(false)}>Annulla</Button>
                        <Button size="sm" disabled={!arrivoForm.ddt_fornitore.trim() || arrivoForm.materiali.filter(m => m.descrizione.trim()).length === 0} onClick={handleCreateArrivo} className="bg-amber-600 text-white hover:bg-amber-700" data-testid="btn-confirm-arrivo"><Package className="h-4 w-4 mr-1" /> Registra Arrivo</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Prelievo Dialog ── */}
            <Dialog open={prelievoOpen} onOpenChange={setPrelievoOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><Truck className="h-5 w-5 text-emerald-600" /> Preleva da Magazzino</DialogTitle>
                        <DialogDescription>Seleziona un articolo dal magazzino e la quantità da assegnare alla commessa <span className="font-semibold">{commessaNumero}</span>.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <Label className="text-sm font-medium">Articolo *</Label>
                            <select value={prelievoForm.articolo_id} onChange={e => setPrelievoForm(f => ({ ...f, articolo_id: e.target.value }))} className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="prelievo-articolo-select">
                                <option value="">Seleziona articolo...</option>
                                {articoliCatalogo.map(a => (<option key={a.articolo_id} value={a.articolo_id}>{a.codice} — {a.descrizione} (Disp: {a.giacenza} {a.unita_misura})</option>))}
                            </select>
                        </div>
                        {prelievoForm.articolo_id && (() => {
                            const art = articoliCatalogo.find(a => a.articolo_id === prelievoForm.articolo_id);
                            return art ? (
                                <div className="bg-emerald-50 p-3 rounded-md text-xs space-y-1 border border-emerald-200">
                                    <div className="flex justify-between"><span className="text-slate-600">Descrizione:</span><span className="font-medium">{art.descrizione}</span></div>
                                    <div className="flex justify-between"><span className="text-slate-600">Giacenza attuale:</span><span className="font-bold text-emerald-700">{art.giacenza} {art.unita_misura}</span></div>
                                    <div className="flex justify-between"><span className="text-slate-600">Prezzo unitario:</span><span className="font-medium">{fmtEur(art.prezzo_unitario)}</span></div>
                                    {prelievoForm.quantita > 0 && <div className="flex justify-between border-t border-emerald-200 pt-1 mt-1"><span className="text-slate-600">Costo totale prelievo:</span><span className="font-bold text-emerald-800">{fmtEur(art.prezzo_unitario * parseFloat(prelievoForm.quantita || 0))}</span></div>}
                                </div>
                            ) : null;
                        })()}
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-sm font-medium">Quantità *</Label><Input type="number" value={prelievoForm.quantita} onChange={e => setPrelievoForm(f => ({ ...f, quantita: e.target.value }))} className="mt-1" min="0.01" step="0.01" data-testid="prelievo-quantita" /></div>
                            <div><Label className="text-sm font-medium">Note</Label><Input value={prelievoForm.note} onChange={e => setPrelievoForm(f => ({ ...f, note: e.target.value }))} className="mt-1" placeholder="Opzionale..." data-testid="prelievo-note" /></div>
                        </div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setPrelievoOpen(false)}>Annulla</Button>
                        <Button size="sm" disabled={!prelievoForm.articolo_id || prelievoLoading} onClick={handlePrelievo} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-confirm-prelievo">{prelievoLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Truck className="h-4 w-4 mr-1" />} Conferma Prelievo</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Certificate Linking Dialog ── */}
            <Dialog open={certLinkOpen} onOpenChange={setCertLinkOpen}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-purple-600" /> Collega Certificati ai Materiali</DialogTitle>
                        <DialogDescription>{selectedArrivo && `DDT: ${selectedArrivo.ddt_fornitore} — Carica i certificati 3.1 e il sistema li analizzerà automaticamente`}</DialogDescription>
                    </DialogHeader>
                    {selectedArrivo && (
                        <div className="space-y-3">
                            <input ref={certFileRef} type="file" accept=".pdf,image/*" className="hidden" onChange={(e) => { if (certFileRef.current?.dataset?.matIdx && e.target.files?.[0]) { handleCertificateUpload(selectedArrivo.arrivo_id, parseInt(certFileRef.current.dataset.matIdx), e.target.files[0]); e.target.value = ''; } }} />
                            <div className="border rounded-md overflow-hidden">
                                <Table>
                                    <TableHeader><TableRow className="bg-purple-50"><TableHead className="w-[40%] text-xs">Materiale</TableHead><TableHead className="w-[15%] text-xs text-center">Q.tà</TableHead><TableHead className="w-[20%] text-xs">Colata</TableHead><TableHead className="w-[25%] text-xs">Azioni</TableHead></TableRow></TableHeader>
                                    <TableBody>
                                        {(selectedArrivo.materiali || []).map((mat, idx) => (
                                            <TableRow key={idx} className={mat.richiede_cert_31 ? '' : 'opacity-50'}>
                                                <TableCell className="text-sm"><div>{mat.descrizione}{mat.richiede_cert_31 && <Badge variant="outline" className="ml-1 text-[9px] bg-amber-50 border-amber-300">3.1</Badge>}</div></TableCell>
                                                <TableCell className="text-center text-sm">{mat.quantita} {mat.unita_misura}</TableCell>
                                                <TableCell>{mat.numero_colata ? <div className="text-sm"><span className="font-mono font-medium text-emerald-700">{mat.numero_colata}</span>{mat.qualita_materiale && <span className="text-xs text-slate-500 ml-1">({mat.qualita_materiale})</span>}</div> : mat.richiede_cert_31 ? <span className="text-xs text-red-500">Non collegato</span> : <span className="text-xs text-slate-400">-</span>}</TableCell>
                                                <TableCell>{mat.richiede_cert_31 && (mat.certificato_doc_id ? <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-3 w-3 mr-0.5" /> Collegato</Badge> : <Button size="sm" variant="outline" className="h-7 text-xs text-purple-600 border-purple-300" disabled={linkingCert?.mat_idx === idx} onClick={() => { if (certFileRef.current) { certFileRef.current.dataset.matIdx = idx; certFileRef.current.click(); } }}>{linkingCert?.mat_idx === idx ? <><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Analisi...</> : <><FileUp className="h-3 w-3 mr-1" /> Carica Cert.</>}</Button>)}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <div className="text-xs text-slate-500 bg-slate-50 p-2 rounded"><strong>AI OCR:</strong> Caricando un certificato 3.1, il sistema estrarrà automaticamente numero colata, qualità del materiale e fornitore.</div>
                        </div>
                    )}
                    <DialogFooter><Button variant="outline" onClick={() => setCertLinkOpen(false)}>Chiudi</Button></DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── PDF Preview Dialog ── */}
            <Dialog open={!!pdfPreviewUrl} onOpenChange={(open) => { if (!open) { setPdfPreviewUrl(null); setPdfExpanded(false); } }}>
                <DialogContent className={`${pdfExpanded ? 'max-w-[95vw] w-[95vw] h-[95vh]' : 'max-w-4xl h-[85vh]'} flex flex-col transition-all duration-200`}>
                    <DialogHeader>
                        <div className="flex items-center justify-between">
                            <DialogTitle className="flex items-center gap-2"><FileSearch className="h-5 w-5 text-blue-600" />{pdfPreviewTitle}</DialogTitle>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-slate-500 hover:text-slate-800" onClick={() => setPdfExpanded(!pdfExpanded)} data-testid="pdf-toggle-expand">{pdfExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}</Button>
                        </div>
                        <DialogDescription>Verifica il documento prima di inviarlo via email</DialogDescription>
                    </DialogHeader>
                    <div className="flex-1 h-full min-h-0">{pdfPreviewUrl && <iframe src={pdfPreviewUrl} className={`w-full ${pdfExpanded ? 'h-[calc(95vh-140px)]' : 'h-[calc(85vh-140px)]'} border rounded`} title="PDF Preview" />}</div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" onClick={() => { setPdfPreviewUrl(null); setPdfExpanded(false); }}>Chiudi</Button>
                        <Button className="bg-[#0055FF] text-white" onClick={() => {
                            if (pdfPreviewUrl?.includes('/richieste/')) { const rdpId = pdfPreviewUrl.split('/richieste/')[1]?.split('/')[0]; if (rdpId) handleSendRdpEmail(rdpId); }
                            else if (pdfPreviewUrl?.includes('/ordini/')) { const ordineId = pdfPreviewUrl.split('/ordini/')[1]?.split('/')[0]; if (ordineId) handleSendOdaEmail(ordineId); }
                            setPdfPreviewUrl(null); setPdfExpanded(false);
                        }}><Mail className="h-4 w-4 mr-1" /> Invia Email</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Email Preview Dialog ── */}
            <EmailPreviewDialog open={emailPreview.open} onOpenChange={(open) => setEmailPreview(prev => ({ ...prev, open }))} previewUrl={emailPreview.previewUrl} sendUrl={emailPreview.sendUrl} onSent={() => { onRefresh?.(); }} />
        </>
    );
}
