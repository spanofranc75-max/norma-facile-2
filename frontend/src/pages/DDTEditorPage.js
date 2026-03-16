/**
 * DDT Editor — Documento di Trasporto (Vendita / Conto Lavoro / Rientro).
 * Invoicex-style with sidebar tabs and Quick Fill from client.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Separator } from '../components/ui/separator';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import {
    Plus, Trash2, Save, ArrowLeft, FileDown, Truck,
    MapPin, CreditCard, StickyNote, Package, Weight, ArrowRightLeft, Mail, Printer,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { PDFPreviewButton } from '../components/PDFPreviewModal';
import { AutoExpandTextarea } from '../components/AutoExpandTextarea';
import EmailPreviewDialog from '../components/EmailPreviewDialog';
import { useConfirm } from '../components/ConfirmProvider';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const emptyLine = () => ({
    line_id: `ln_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    codice_articolo: '', description: '', unit: 'pz', quantity: 0,
    qta_fatturata: 0, unit_price: 0, sconto_1: 0, sconto_2: 0, vat_rate: '22', notes: '',
});

const CAUSALI = ['Vendita', 'Conto Lavoro', 'Reso Conto Lavoro', 'Conto Visione', 'Riparazione', 'Omaggio', 'Trasferimento'];
const ASPETTI = ['Scatola', 'Busta', 'Pallet', 'Sfuso', 'Collo', 'Cassa', 'Altro'];
const PORTI = ['Franco', 'Assegnato', 'Porto Affrancato'];
const MEZZI = ['Mittente', 'Destinatario', 'Vettore'];

const TYPE_OPTIONS = [
    { value: 'vendita', label: 'DDT Vendita', causale: 'Vendita' },
    { value: 'conto_lavoro', label: 'DDT Conto Lavoro', causale: 'Conto Lavoro' },
    { value: 'rientro_conto_lavoro', label: 'DDT Rientro C/Lavoro', causale: 'Reso Conto Lavoro' },
];

const SIDEBAR_TABS = [
    { key: 'trasporto', label: 'Trasporto', icon: Truck },
    { key: 'destinazione', label: 'Destin.', icon: MapPin },
    { key: 'pagamento', label: 'Pagam.', icon: CreditCard },
    { key: 'note', label: 'Note', icon: StickyNote },
];

export default function DDTEditorPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const { ddtId } = useParams();
    const isNew = !ddtId || ddtId === 'new';

    const [form, setForm] = useState({
        ddt_type: 'vendita', client_id: '', subject: '',
        destinazione: { ragione_sociale: '', indirizzo: '', cap: '', localita: '', provincia: '', telefono: '', cellulare: '', paese: 'IT' },
        causale_trasporto: 'Vendita', aspetto_beni: '', vettore: '', mezzo_trasporto: 'Mittente', porto: 'Franco',
        data_ora_trasporto: '', num_colli: 0, peso_lordo_kg: 0, peso_netto_kg: 0,
        payment_type_id: '', payment_type_label: '', stampa_prezzi: true,
        riferimento: '', acconto: 0, sconto_globale: 0, notes: '',
        lines: [emptyLine()],
    });
    const [clients, setClients] = useState([]);
    const [paymentTypes, setPaymentTypes] = useState([]);
    const [saving, setSaving] = useState(false);
    const [converting, setConverting] = useState(false);
    const [sidebarTab, setSidebarTab] = useState('trasporto');
    const [emailPreviewOpen, setEmailPreviewOpen] = useState(false);
    const [ddtInfo, setDdtInfo] = useState({ number: null, status: 'non_fatturato', converted_to: null, commessa_id: null, commessa_numero: null });

    useEffect(() => {
        Promise.all([
            apiRequest('/clients/').catch(() => ({ clients: [] })),
            apiRequest('/payment-types/').catch(() => ({ items: [] })),
        ]).then(([cl, pt]) => {
            setClients(cl.clients || []);
            setPaymentTypes(pt.items || []);
        });
    }, []);

    useEffect(() => {
        if (isNew) return;
        apiRequest(`/ddt/${ddtId}`).then(data => {
            setForm({
                ddt_type: data.ddt_type || 'vendita',
                client_id: data.client_id || '',
                subject: data.subject || '',
                destinazione: data.destinazione || { ragione_sociale: '', indirizzo: '', cap: '', localita: '', provincia: '', telefono: '', cellulare: '', paese: 'IT' },
                causale_trasporto: data.causale_trasporto || 'Vendita',
                aspetto_beni: data.aspetto_beni || '',
                vettore: data.vettore || '',
                mezzo_trasporto: data.mezzo_trasporto || 'Mittente',
                porto: data.porto || 'Franco',
                data_ora_trasporto: data.data_ora_trasporto || '',
                num_colli: data.num_colli || 0,
                peso_lordo_kg: data.peso_lordo_kg || 0,
                peso_netto_kg: data.peso_netto_kg || 0,
                payment_type_id: data.payment_type_id || '',
                payment_type_label: data.payment_type_label || '',
                stampa_prezzi: data.stampa_prezzi !== false,
                riferimento: data.riferimento || '',
                acconto: data.acconto || 0,
                sconto_globale: data.sconto_globale || 0,
                notes: data.notes || '',
                lines: data.lines?.length ? data.lines : [emptyLine()],
            });
            setDdtInfo({ number: data.number, status: data.status || 'non_fatturato', converted_to: data.converted_to || null, commessa_id: data.commessa_id || null, commessa_numero: data.commessa_numero || null });
        }).catch(() => toast.error('DDT non trovato'));
    }, [ddtId, isNew]);

    // Quick Fill from client
    const handleClientChange = useCallback((clientId) => {
        setForm(f => ({ ...f, client_id: clientId }));
        if (!clientId) return;
        const client = clients.find(c => c.client_id === clientId);
        if (!client) return;
        setForm(f => ({
            ...f,
            client_id: clientId,
            destinazione: {
                ragione_sociale: client.business_name || '',
                indirizzo: client.address || '',
                cap: client.cap || '',
                localita: client.city || '',
                provincia: client.province || '',
                telefono: client.phone || '',
                cellulare: client.cellulare || '',
                paese: client.country || 'IT',
            },
            payment_type_id: f.payment_type_id || client.payment_type_id || '',
            payment_type_label: f.payment_type_label || client.payment_type_label || '',
        }));
        toast.success(`Dati di ${client.business_name} importati`);
    }, [clients]);

    const handleTypeChange = (t) => {
        const opt = TYPE_OPTIONS.find(o => o.value === t);
        setForm(f => ({ ...f, ddt_type: t, causale_trasporto: opt?.causale || f.causale_trasporto }));
    };

    const updateLine = (idx, key, val) => setForm(f => {
        const lines = [...f.lines];
        lines[idx] = { ...lines[idx], [key]: val };
        return { ...f, lines };
    });
    const addLine = () => setForm(f => ({ ...f, lines: [...f.lines, emptyLine()] }));
    const removeLine = (idx) => setForm(f => ({ ...f, lines: f.lines.filter((_, i) => i !== idx) }));
    const updateDest = (key, val) => setForm(f => ({ ...f, destinazione: { ...f.destinazione, [key]: val } }));

    // Calculations
    const lineNet = (l) => {
        const p = parseFloat(l.unit_price) || 0;
        return p * (1 - (parseFloat(l.sconto_1) || 0) / 100) * (1 - (parseFloat(l.sconto_2) || 0) / 100);
    };
    const lineTotal = (l) => (parseFloat(l.quantity) || 0) * lineNet(l);
    const subtotal = form.lines.reduce((s, l) => s + lineTotal(l), 0);
    const scontoVal = subtotal * (parseFloat(form.sconto_globale) || 0) / 100;
    const imponibile = subtotal - scontoVal;
    const totalVat = form.lines.reduce((s, l) => {
        const base = lineTotal(l) * (1 - (parseFloat(form.sconto_globale) || 0) / 100);
        return s + base * (parseFloat(l.vat_rate) || 0) / 100;
    }, 0);
    const totale = imponibile + totalVat;
    const daPagare = totale - (parseFloat(form.acconto) || 0);

    const handleSave = async () => {
        setSaving(true);
        try {
            const payload = {
                ...form,
                client_id: form.client_id || null,
                lines: form.lines.map(l => ({
                    ...l, quantity: parseFloat(l.quantity) || 0, unit_price: parseFloat(l.unit_price) || 0,
                    sconto_1: parseFloat(l.sconto_1) || 0, sconto_2: parseFloat(l.sconto_2) || 0,
                    qta_fatturata: parseFloat(l.qta_fatturata) || 0,
                })),
                num_colli: parseInt(form.num_colli) || 0,
                peso_lordo_kg: parseFloat(form.peso_lordo_kg) || 0,
                peso_netto_kg: parseFloat(form.peso_netto_kg) || 0,
                acconto: parseFloat(form.acconto) || 0,
                sconto_globale: parseFloat(form.sconto_globale) || 0,
            };
            if (isNew) {
                const res = await apiRequest('/ddt/', { method: 'POST', body: payload });
                toast.success('DDT creato');
                navigate(`/ddt/${res.ddt_id}`, { replace: true });
            } else {
                await apiRequest(`/ddt/${ddtId}`, { method: 'PUT', body: payload });
                toast.success('DDT salvato');
            }
        } catch (e) { toast.error(e.message); } finally { setSaving(false); }
    };

    const handleDownloadPdf = () => {
        if (isNew) return;
        downloadPdfBlob(`/ddt/${ddtId}/pdf`, `DDT_${ddtInfo.number || ddtId}.pdf`).catch(e => toast.error(e.message));
    };

    const handleConvertToInvoice = async () => {
        if (!(await confirm('Convertire questo DDT in Fattura? Le righe, il cliente e i totali verranno importati automaticamente.'))) return;
        setConverting(true);
        try {
            const res = await apiRequest(`/ddt/${ddtId}/convert-to-invoice`, { method: 'POST' });
            toast.success(res.message || 'DDT convertito in Fattura');
            navigate(`/invoices/${res.invoice_id}`);
        } catch (e) { toast.error(e.message); } finally { setConverting(false); }
    };

    const handlePaymentTypeChange = (ptId) => {
        const pt = paymentTypes.find(p => p.payment_type_id === ptId);
        setForm(f => ({
            ...f,
            payment_type_id: ptId === '__none__' ? '' : ptId,
            payment_type_label: pt ? `${pt.codice} - ${pt.descrizione}` : '',
        }));
    };

    const STATUS_LABELS = { non_fatturato: 'Non Fatturato', parzialmente_fatturato: 'Parz. Fatturato', fatturato: 'Fatturato' };
    const TYPE_COLORS = { vendita: 'bg-blue-100 text-blue-800', conto_lavoro: 'bg-amber-100 text-amber-800', rientro_conto_lavoro: 'bg-emerald-100 text-emerald-800' };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="ddt-editor">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate('/ddt')}><ArrowLeft className="h-4 w-4" /></Button>
                        <div>
                            <h1 className="font-sans text-xl font-bold text-[#1E293B]">{isNew ? 'Nuovo DDT' : 'Modifica DDT'}</h1>
                            <div className="flex items-center gap-2 mt-0.5">
                                {ddtInfo.number && <span className="text-xs font-mono text-[#0055FF]">{ddtInfo.number}</span>}
                                <Badge className={`${TYPE_COLORS[form.ddt_type]} text-[10px]`}>{TYPE_OPTIONS.find(t => t.value === form.ddt_type)?.label}</Badge>
                                {!isNew && <Badge className="bg-slate-100 text-slate-700 text-[10px]">{STATUS_LABELS[ddtInfo.status]}</Badge>}
                                {ddtInfo.commessa_id && (
                                    <button
                                        data-testid="ddt-editor-commessa-link"
                                        className="inline-flex items-center gap-1 text-[10px] font-medium text-[#0055FF] bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5 hover:bg-blue-100 transition-colors"
                                        onClick={() => navigate(`/commesse/${ddtInfo.commessa_id}`)}
                                    >
                                        Commessa {ddtInfo.commessa_numero || ''}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {!isNew && <Button data-testid="btn-download-pdf" variant="outline" onClick={handleDownloadPdf} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50 h-9 text-xs"><FileDown className="h-3.5 w-3.5 mr-1.5" /> PDF</Button>}
                        {!isNew && <Button variant="outline" onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/ddt/${ddtId}/pdf?token=${localStorage.getItem('session_token')}`, '_blank')} className="border-purple-500 text-purple-600 hover:bg-purple-50 h-9 text-xs"><Printer className="h-3.5 w-3.5 mr-1.5" /> Stampa</Button>}
                        {!isNew && <PDFPreviewButton pdfUrl={`/ddt/${ddtId}/pdf`} title={`Anteprima DDT ${ddtInfo.number || ''}`} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9" />}
                        {!isNew && (
                            <Button
                                type="button"
                                variant="outline"
                                data-testid="btn-send-email-ddt"
                                onClick={() => setEmailPreviewOpen(true)}
                                className="border-violet-400 text-violet-600 hover:bg-violet-50 h-9 text-xs"
                            >
                                <Mail className="h-3.5 w-3.5 mr-1" /> Email
                            </Button>
                        )}
                        {!isNew && ddtInfo.status !== 'fatturato' && !ddtInfo.converted_to && (
                            <Button data-testid="btn-convert-invoice" variant="outline" onClick={handleConvertToInvoice} disabled={converting} className="border-amber-500 text-amber-600 hover:bg-amber-50 h-9 text-xs">
                                <ArrowRightLeft className="h-3.5 w-3.5 mr-1.5" /> {converting ? 'Conversione...' : 'Converti in Fattura'}
                            </Button>
                        )}
                        {!isNew && ddtInfo.status === 'fatturato' && ddtInfo.converted_to && (
                            <Button data-testid="btn-go-to-invoice" variant="outline" onClick={() => navigate(`/invoices/${ddtInfo.converted_to}`)} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9 text-xs">
                                <ArrowRightLeft className="h-3.5 w-3.5 mr-1.5" /> Vai alla Fattura
                            </Button>
                        )}
                        <Button data-testid="btn-save-ddt" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC] h-9 text-xs"><Save className="h-3.5 w-3.5 mr-1.5" /> {saving ? 'Salvataggio...' : 'Salva'}</Button>
                    </div>
                </div>

                {/* Main Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
                    {/* ── Left Sidebar ── */}
                    <div className="space-y-3">
                        <Card className="border-gray-200">
                            <CardContent className="p-4 space-y-3">
                                <div>
                                    <Label className="text-xs">Tipo DDT</Label>
                                    <Select value={form.ddt_type} onValueChange={handleTypeChange}>
                                        <SelectTrigger data-testid="select-ddt-type" className="h-9"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {TYPE_OPTIONS.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Cliente / Fornitore</Label>
                                    <Select value={form.client_id || '__none__'} onValueChange={v => handleClientChange(v === '__none__' ? '' : v)}>
                                        <SelectTrigger data-testid="select-client" className="h-9"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                            {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Oggetto</Label>
                                    <Input data-testid="input-subject" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="Consegna materiale..." className="h-9 text-sm" />
                                </div>
                                <div>
                                    <Label className="text-xs">Riferimento</Label>
                                    <Input value={form.riferimento} onChange={e => setForm(f => ({ ...f, riferimento: e.target.value }))} placeholder="Rif. ordine..." className="h-8 text-xs" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-gray-200">
                            <div className="flex border-b border-slate-200">
                                {SIDEBAR_TABS.map(t => (
                                    <button key={t.key} onClick={() => setSidebarTab(t.key)} className={`flex-1 py-2 text-[10px] font-medium text-center border-b-2 transition-colors ${sidebarTab === t.key ? 'border-[#0055FF] text-[#0055FF]' : 'border-transparent text-slate-500'}`}>
                                        <t.icon className="h-3.5 w-3.5 mx-auto mb-0.5" />{t.label}
                                    </button>
                                ))}
                            </div>
                            <CardContent className="p-3 space-y-2.5">
                                {sidebarTab === 'trasporto' && (
                                    <div className="space-y-2.5">
                                        <div><Label className="text-xs">Causale Trasporto</Label>
                                            <Select value={form.causale_trasporto} onValueChange={v => setForm(f => ({ ...f, causale_trasporto: v }))}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                <SelectContent>{CAUSALI.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div><Label className="text-xs">Aspetto Beni</Label>
                                            <Select value={form.aspetto_beni || '__none__'} onValueChange={v => setForm(f => ({ ...f, aspetto_beni: v === '__none__' ? '' : v }))}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                                <SelectContent><SelectItem value="__none__">--</SelectItem>{ASPETTI.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div><Label className="text-xs">Porto</Label>
                                                <Select value={form.porto} onValueChange={v => setForm(f => ({ ...f, porto: v }))}>
                                                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                    <SelectContent>{PORTI.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                                                </Select>
                                            </div>
                                            <div><Label className="text-xs">Mezzo</Label>
                                                <Select value={form.mezzo_trasporto} onValueChange={v => setForm(f => ({ ...f, mezzo_trasporto: v }))}>
                                                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                    <SelectContent>{MEZZI.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                                                </Select>
                                            </div>
                                        </div>
                                        <div><Label className="text-xs">Vettore</Label><Input value={form.vettore} onChange={e => setForm(f => ({ ...f, vettore: e.target.value }))} className="h-8 text-xs" /></div>
                                        <div><Label className="text-xs">Data/Ora Trasporto</Label><Input value={form.data_ora_trasporto} onChange={e => setForm(f => ({ ...f, data_ora_trasporto: e.target.value }))} className="h-8 text-xs" placeholder="27/02/2026 16:00" /></div>
                                        <Separator />
                                        <div className="grid grid-cols-3 gap-2">
                                            <div><Label className="text-xs">Colli</Label><Input type="number" value={form.num_colli} onChange={e => setForm(f => ({ ...f, num_colli: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                            <div><Label className="text-xs">P. Lordo</Label><Input type="number" step="0.1" value={form.peso_lordo_kg} onChange={e => setForm(f => ({ ...f, peso_lordo_kg: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                            <div><Label className="text-xs">P. Netto</Label><Input type="number" step="0.1" value={form.peso_netto_kg} onChange={e => setForm(f => ({ ...f, peso_netto_kg: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                        </div>
                                    </div>
                                )}
                                {sidebarTab === 'destinazione' && (
                                    <div className="space-y-2">
                                        <div><Label className="text-xs">Ragione Sociale</Label><Input value={form.destinazione.ragione_sociale} onChange={e => updateDest('ragione_sociale', e.target.value)} className="h-8 text-xs" /></div>
                                        <div><Label className="text-xs">Indirizzo</Label><Input value={form.destinazione.indirizzo} onChange={e => updateDest('indirizzo', e.target.value)} className="h-8 text-xs" /></div>
                                        <div className="grid grid-cols-3 gap-2">
                                            <div><Label className="text-xs">CAP</Label><Input value={form.destinazione.cap} onChange={e => updateDest('cap', e.target.value)} className="h-8 text-xs" maxLength={5} /></div>
                                            <div><Label className="text-xs">Località</Label><Input value={form.destinazione.localita} onChange={e => updateDest('localita', e.target.value)} className="h-8 text-xs" /></div>
                                            <div><Label className="text-xs">Prov.</Label><Input value={form.destinazione.provincia} onChange={e => updateDest('provincia', e.target.value.toUpperCase())} className="h-8 text-xs" maxLength={2} /></div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div><Label className="text-xs">Telefono</Label><Input value={form.destinazione.telefono} onChange={e => updateDest('telefono', e.target.value)} className="h-8 text-xs" /></div>
                                            <div><Label className="text-xs">Cellulare</Label><Input value={form.destinazione.cellulare} onChange={e => updateDest('cellulare', e.target.value)} className="h-8 text-xs" /></div>
                                        </div>
                                    </div>
                                )}
                                {sidebarTab === 'pagamento' && (
                                    <div className="space-y-2.5">
                                        <div><Label className="text-xs">Condizioni Pagamento</Label>
                                            <Select value={form.payment_type_id || '__none__'} onValueChange={handlePaymentTypeChange}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                                <SelectContent><SelectItem value="__none__">-- Nessuno --</SelectItem>{paymentTypes.map(pt => <SelectItem key={pt.payment_type_id} value={pt.payment_type_id}><span className="font-mono text-[10px] mr-1">{pt.codice}</span> {pt.descrizione}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div><Label className="text-xs">Sconto Globale %</Label><Input type="number" step="0.1" value={form.sconto_globale} onChange={e => setForm(f => ({ ...f, sconto_globale: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                            <div><Label className="text-xs">Acconto</Label><Input type="number" step="0.01" value={form.acconto} onChange={e => setForm(f => ({ ...f, acconto: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                        </div>
                                        <label className="flex items-center gap-2 text-xs cursor-pointer">
                                            <Checkbox checked={form.stampa_prezzi} onCheckedChange={v => setForm(f => ({ ...f, stampa_prezzi: v }))} />
                                            <span>Stampa prezzi in PDF</span>
                                        </label>
                                    </div>
                                )}
                                {sidebarTab === 'note' && (
                                    <div><Label className="text-xs">Note</Label><Textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={6} className="text-xs" /></div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* ── Right Content ── */}
                    <div className="space-y-4">
                        {/* Lines Table */}
                        <Card className="border-gray-200">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg flex flex-row items-center justify-between">
                                <CardTitle className="text-xs font-semibold text-white">Dettaglio Righe</CardTitle>
                                <Button data-testid="btn-add-line" size="sm" variant="ghost" onClick={addLine} className="text-white hover:text-blue-200 h-7 text-xs"><Plus className="h-3 w-3 mr-1" /> Aggiungi</Button>
                            </CardHeader>
                            <CardContent className="p-0 overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="w-7 text-[10px]">#</TableHead>
                                            <TableHead className="w-20 text-[10px]">Codice</TableHead>
                                            <TableHead className="min-w-[160px] text-[10px]">Descrizione</TableHead>
                                            <TableHead className="w-14 text-[10px]">UdM</TableHead>
                                            <TableHead className="w-16 text-right text-[10px]">Q.tà</TableHead>
                                            <TableHead className="w-20 text-right text-[10px]">Prezzo</TableHead>
                                            <TableHead className="w-14 text-right text-[10px]">Sc.1%</TableHead>
                                            <TableHead className="w-14 text-right text-[10px]">Sc.2%</TableHead>
                                            <TableHead className="w-20 text-right text-[10px]">Totale</TableHead>
                                            <TableHead className="w-14 text-[10px]">IVA</TableHead>
                                            <TableHead className="w-8"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {form.lines.map((l, i) => (
                                            <TableRow key={l.line_id} data-testid={`line-${i}`}>
                                                <TableCell className="text-[10px] text-slate-400 font-mono">{i + 1}</TableCell>
                                                <TableCell><Input value={l.codice_articolo} onChange={e => updateLine(i, 'codice_articolo', e.target.value)} className="h-7 text-xs font-mono" /></TableCell>
                                                <TableCell><AutoExpandTextarea value={l.description} onChange={e => updateLine(i, 'description', e.target.value)} className="text-xs" /></TableCell>
                                                <TableCell>
                                                    <Select value={l.unit} onValueChange={v => updateLine(i, 'unit', v)}>
                                                        <SelectTrigger className="h-7 text-[10px] w-14"><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            {['pz', 'm', 'mq', 'kg', 'h', 'corpo'].map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell><Input type="number" value={l.quantity} onChange={e => updateLine(i, 'quantity', e.target.value)} className="h-7 text-xs text-right font-mono" /></TableCell>
                                                <TableCell><Input type="number" step="0.01" value={l.unit_price} onChange={e => updateLine(i, 'unit_price', e.target.value)} className="h-7 text-xs text-right font-mono text-red-600 font-semibold" /></TableCell>
                                                <TableCell><Input type="number" step="0.1" value={l.sconto_1} onChange={e => updateLine(i, 'sconto_1', e.target.value)} className="h-7 text-[10px] text-right font-mono w-14" /></TableCell>
                                                <TableCell><Input type="number" step="0.1" value={l.sconto_2} onChange={e => updateLine(i, 'sconto_2', e.target.value)} className="h-7 text-[10px] text-right font-mono w-14" /></TableCell>
                                                <TableCell className="text-right font-mono text-xs font-semibold text-[#0055FF]">{fmtEur(lineTotal(l))}</TableCell>
                                                <TableCell>
                                                    <Select value={l.vat_rate} onValueChange={v => updateLine(i, 'vat_rate', v)}>
                                                        <SelectTrigger className="h-7 text-[10px] w-14"><SelectValue /></SelectTrigger>
                                                        <SelectContent>{['22', '10', '4', '0'].map(r => <SelectItem key={r} value={r}>{r}%</SelectItem>)}</SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell>{form.lines.length > 1 && <button onClick={() => removeLine(i)} className="p-1 text-slate-400 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* Totals */}
                        <Card className="border-gray-200" data-testid="totals-card">
                            <CardContent className="p-4">
                                <div className="flex justify-end">
                                    <div className="w-64 space-y-1.5">
                                        <TotalRow label="Totale senza IVA" value={fmtEur(subtotal)} />
                                        {parseFloat(form.sconto_globale) > 0 && <TotalRow label={`Sconto ${form.sconto_globale}%`} value={`-${fmtEur(scontoVal)}`} className="text-red-500" />}
                                        <TotalRow label="Imponibile" value={fmtEur(imponibile)} />
                                        <TotalRow label="Totale IVA" value={fmtEur(totalVat)} />
                                        <Separator />
                                        <div className="flex justify-between items-center pt-1">
                                            <span className="text-sm font-bold text-[#1E293B]">TOTALE</span>
                                            <span className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(totale)}</span>
                                        </div>
                                        {parseFloat(form.acconto) > 0 && <TotalRow label="Acconto" value={`-${fmtEur(form.acconto)}`} className="text-amber-600" />}
                                        {parseFloat(form.acconto) > 0 && (
                                            <div className="flex justify-between items-center bg-slate-50 -mx-4 px-4 py-2 rounded-b-lg">
                                                <span className="text-sm font-bold text-[#1E293B]">DA PAGARE</span>
                                                <span className="font-mono text-lg font-bold text-emerald-600">{fmtEur(daPagare)}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
            <EmailPreviewDialog
                open={emailPreviewOpen}
                onOpenChange={setEmailPreviewOpen}
                previewUrl={`/api/ddt/${ddtId}/preview-email`}
                sendUrl={`/api/ddt/${ddtId}/send-email`}
            />
        </DashboardLayout>
    );
}

function TotalRow({ label, value, className = '' }) {
    return (
        <div className="flex justify-between text-xs">
            <span className="text-slate-500">{label}</span>
            <span className={`font-mono font-medium ${className}`}>{value}</span>
        </div>
    );
}
