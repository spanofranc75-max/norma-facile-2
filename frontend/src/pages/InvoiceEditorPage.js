/**
 * Invoice Editor Page - Creazione/Modifica Fattura (Invoicex Style)
 * Dense table layout with clear visual hierarchy.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../components/ui/table';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Plus,
    Trash2,
    Save,
    FileText,
    ArrowLeft,
    Calculator,
    Mail,
    Send,
    CheckCircle2,
    PanelRightOpen,
    Eye,
    Printer,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import ArticleSearch from '../components/ArticleSearch';
import { QuickFillModal } from '../components/QuickFillModal';
import { useConfirm } from '../components/ConfirmProvider';

import { LivePDFPreview } from '../components/LivePDFPreview';
import { AutoExpandTextarea } from '../components/AutoExpandTextarea';
import EmailPreviewDialog from '../components/EmailPreviewDialog';
import SdiPreviewDialog from '../components/SdiPreviewDialog';

const DOC_TYPES = [
    { value: 'FT', label: 'Fattura' },
    { value: 'PRV', label: 'Preventivo' },
    { value: 'DDT', label: 'DDT' },
    { value: 'NC', label: 'Nota di Credito' },
];

const PAYMENT_METHODS = [
    { value: 'bonifico', label: 'Bonifico Bancario' },
    { value: 'contanti', label: 'Contanti' },
    { value: 'carta', label: 'Carta di Credito' },
    { value: 'assegno', label: 'Assegno' },
    { value: 'riba', label: 'RiBa' },
    { value: 'altro', label: 'Altro' },
];

const PAYMENT_TERMS = [
    { value: 'immediato', label: 'Immediato' },
    { value: '30gg', label: '30 giorni' },
    { value: '60gg', label: '60 giorni' },
    { value: '90gg', label: '90 giorni' },
    { value: '30-60gg', label: '30/60 giorni' },
    { value: '30-60-90gg', label: '30/60/90 giorni' },
    { value: 'fine_mese', label: 'Fine mese' },
    { value: 'fm+30', label: 'Fine mese + 30' },
];

const VAT_RATES = [
    { value: '22', label: '22%' },
    { value: '10', label: '10%' },
    { value: '4', label: '4%' },
    { value: '0', label: '0%' },
    { value: 'N4', label: 'Esente (N4)' },
    { value: 'N3', label: 'Non imponibile (N3)' },
];

const emptyLine = {
    code: '',
    description: '',
    quantity: '',
    unit_price: '',
    discount_percent: '',
    vat_rate: '22',
};

const formatCurrency = (value) => {
    return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency: 'EUR',
    }).format(value || 0);
};

export default function InvoiceEditorPage() {
    const navigate = useNavigate();
    const { invoiceId } = useParams();
    const isEditing = !!invoiceId;
    const confirm = useConfirm();

    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [clients, setClients] = useState([]);
    const [quickFillOpen, setQuickFillOpen] = useState(false);
    
    const [formData, setFormData] = useState({
        document_type: 'FT',
        document_number: '',
        client_id: '',
        issue_date: new Date().toISOString().split('T')[0],
        due_date: '',
        payment_method: 'bonifico',
        payment_terms: '30gg',
        notes: '',
        internal_notes: '',
        cup: '',
        cig: '',
        cuc: '',
        tax_settings: {
            apply_rivalsa_inps: false,
            rivalsa_inps_rate: 4,
            apply_cassa: false,
            cassa_type: '',
            cassa_rate: 4,
            apply_ritenuta: false,
            ritenuta_rate: 20,
            ritenuta_base: 'imponibile',
        },
        lines: [{ ...emptyLine }],
    });

    const [totals, setTotals] = useState({
        subtotal: 0,
        vat_breakdown: {},
        total_vat: 0,
        rivalsa_inps: 0,
        cassa: 0,
        ritenuta: 0,
        total_document: 0,
        total_to_pay: 0,
    });

    const [emailPreviewOpen, setEmailPreviewOpen] = useState(false);
    const [sdiPreviewOpen, setSdiPreviewOpen] = useState(false);
    const [paymentTypes, setPaymentTypes] = useState([]);
    const [showLivePreview, setShowLivePreview] = useState(false);

    // Calculate due date from issue_date and payment type
    const calcDueDate = (issueDate, pt) => {
        if (!issueDate || !pt) return '';
        const quote = pt.quote || [];
        if (quote.length === 0) return '';
        // Use the last installment's giorni for the final due date
        const maxGiorni = Math.max(...quote.map(q => q.giorni || 0));
        if (maxGiorni < 0) return issueDate; // "a fine lavori" = same day
        const d = new Date(issueDate);
        d.setDate(d.getDate() + maxGiorni);
        if (pt.fine_mese) {
            // Move to end of month
            d.setMonth(d.getMonth() + 1, 0);
            // Add extra days after end of month (e.g. FM+10)
            if (pt.extra_days) {
                d.setDate(d.getDate() + pt.extra_days);
            }
        }
        return d.toISOString().split('T')[0];
    };

    // Fetch clients and payment types on mount
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [cl, pt] = await Promise.all([
                    apiRequest('/clients/?limit=100&status=active'),
                    apiRequest('/payment-types/').catch(() => ({ items: [] })),
                ]);
                setClients(cl.clients);
                setPaymentTypes(pt.items || []);
            } catch (error) {
                toast.error('Errore caricamento dati');
            }
        };
        fetchData();
    }, []);

    // Reload invoice data from API
    const fetchInvoice = async () => {
        try {
            const data = await apiRequest(`/invoices/${invoiceId}`);
            setFormData({
                document_type: data.document_type,
                document_number: data.document_number || '',
                client_id: data.client_id,
                issue_date: data.issue_date,
                due_date: data.due_date || '',
                payment_method: data.payment_method,
                payment_terms: data.payment_terms,
                notes: data.notes || '',
                internal_notes: data.internal_notes || '',
                cup: data.cup || '',
                cig: data.cig || '',
                cuc: data.cuc || '',
                tax_settings: data.tax_settings || formData.tax_settings,
                lines: data.lines.length > 0 ? data.lines : [{ ...emptyLine }],
                status: data.status || 'bozza',
            });
            setTotals(data.totals);
        } catch (error) {
            toast.error('Documento non trovato');
            navigate('/invoices');
        } finally {
            setLoading(false);
        }
    };

    // Fetch invoice if editing
    useEffect(() => {
        if (!isEditing) return;
        fetchInvoice();
    }, [invoiceId, isEditing]);

    // Calculate totals when lines or tax settings change
    useEffect(() => {
        calculateTotals();
    }, [formData.lines, formData.tax_settings]);

    const calculateTotals = () => {
        let subtotal = 0;
        let totalVat = 0;
        const vatBreakdown = {};

        formData.lines.forEach(line => {
            const qty = parseFloat(line.quantity) || 0;
            const price = parseFloat(line.unit_price) || 0;
            const disc = parseFloat(line.discount_percent) || 0;
            const gross = qty * price;
            const discount = gross * (disc / 100);
            const net = gross - discount;
            
            let vatRate = 0;
            if (!['N3', 'N4'].includes(line.vat_rate)) {
                vatRate = parseFloat(line.vat_rate) || 0;
            }
            const vatAmount = net * (vatRate / 100);

            subtotal += net;
            totalVat += vatAmount;

            if (!vatBreakdown[line.vat_rate]) {
                vatBreakdown[line.vat_rate] = { imponibile: 0, imposta: 0 };
            }
            vatBreakdown[line.vat_rate].imponibile += net;
            vatBreakdown[line.vat_rate].imposta += vatAmount;
        });

        // Additional taxes
        let rivalsaInps = 0;
        let cassa = 0;
        let ritenuta = 0;

        if (formData.tax_settings.apply_rivalsa_inps) {
            rivalsaInps = subtotal * (formData.tax_settings.rivalsa_inps_rate / 100);
        }
        if (formData.tax_settings.apply_cassa) {
            cassa = subtotal * (formData.tax_settings.cassa_rate / 100);
        }

        const totalDocument = subtotal + totalVat + rivalsaInps + cassa;

        if (formData.tax_settings.apply_ritenuta) {
            const base = formData.tax_settings.ritenuta_base === 'imponibile' ? subtotal : totalDocument;
            ritenuta = base * (formData.tax_settings.ritenuta_rate / 100);
        }

        const totalToPay = totalDocument - ritenuta;

        setTotals({
            subtotal: Math.round(subtotal * 100) / 100,
            vat_breakdown: vatBreakdown,
            total_vat: Math.round(totalVat * 100) / 100,
            rivalsa_inps: Math.round(rivalsaInps * 100) / 100,
            cassa: Math.round(cassa * 100) / 100,
            ritenuta: Math.round(ritenuta * 100) / 100,
            total_document: Math.round(totalDocument * 100) / 100,
            total_to_pay: Math.round(totalToPay * 100) / 100,
        });
    };

    const updateField = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const updateTaxSetting = (field, value) => {
        setFormData(prev => ({
            ...prev,
            tax_settings: { ...prev.tax_settings, [field]: value },
        }));
    };

    const updateLine = (index, field, value) => {
        setFormData(prev => {
            const newLines = [...prev.lines];
            newLines[index] = { ...newLines[index], [field]: value };
            return { ...prev, lines: newLines };
        });
    };

    const addLine = () => {
        setFormData(prev => ({
            ...prev,
            lines: [...prev.lines, { ...emptyLine }],
        }));
    };

    const removeLine = (index) => {
        if (formData.lines.length <= 1) return;
        setFormData(prev => ({
            ...prev,
            lines: prev.lines.filter((_, i) => i !== index),
        }));
    };

    const handleQuickFill = (source) => {
        // Map lines from preventivo/DDT into invoice format
        const mappedLines = (source.lines || []).map(line => ({
            code: line.codice_articolo || line.code || '',
            description: line.description || '',
            quantity: parseFloat(line.quantity) || 1,
            unit_price: parseFloat(line.prezzo_netto || line.unit_price) || 0,
            discount_percent: 0,
            vat_rate: line.vat_rate || '22',
        }));

        if (mappedLines.length === 0) {
            toast.error('Nessuna riga trovata nel documento');
            return;
        }

        setFormData(prev => ({
            ...prev,
            client_id: source.client_id || prev.client_id,
            cup: source.cup || prev.cup,
            cig: source.cig || prev.cig,
            cuc: source.cuc || prev.cuc,
            lines: mappedLines,
            notes: prev.notes
                ? `${prev.notes}\nRif. ${source.source_type === 'preventivo' ? 'Preventivo' : 'DDT'} ${source.number}`
                : `Rif. ${source.source_type === 'preventivo' ? 'Preventivo' : 'DDT'} ${source.number}`,
        }));
        toast.success(`${mappedLines.length} righe importate da ${source.number}`);
    };

    const handleSave = async () => {
        if (!formData.client_id) {
            toast.error('Seleziona un cliente');
            return;
        }
        if (formData.lines.every(l => !l.description.trim())) {
            toast.error('Inserisci almeno una riga');
            return;
        }

        try {
            setSaving(true);

            if (isEditing) {
                let payload;
                const isNonDraft = formData.status && formData.status !== 'bozza';
                const isNC = formData.document_type === 'NC';
                if (isNonDraft && !isNC) {
                    // Non-draft FT: only send metadata fields
                    payload = {
                        payment_method: formData.payment_method,
                        payment_terms: formData.payment_terms,
                        due_date: formData.due_date || undefined,
                        notes: formData.notes,
                        internal_notes: formData.internal_notes,
                    };
                } else {
                    // Draft documents OR NC (always editable)
                    payload = {
                        ...formData,
                        lines: formData.lines.filter(l => l.description.trim()),
                    };
                }
                await apiRequest(`/invoices/${invoiceId}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload),
                });
                toast.success('Documento aggiornato');
            } else {
                const payload = {
                    ...formData,
                    lines: formData.lines.filter(l => l.description.trim()),
                };
                const result = await apiRequest('/invoices/', {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });
                toast.success(`Documento ${result.document_number} creato`);
                navigate(`/invoices/${result.invoice_id}`);
            }
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
        }
    };

    // Auto-save then open PDF (preview or print)
    const handleOpenPDF = async (printAfter = false) => {
        if (!isEditing) return;
        try {
            setSaving(true);
            const payload = formData.status && formData.status !== 'bozza'
                ? { payment_method: formData.payment_method, payment_terms: formData.payment_terms, due_date: formData.due_date || undefined, notes: formData.notes, internal_notes: formData.internal_notes }
                : { ...formData, lines: formData.lines.filter(l => l.description.trim()) };
            await apiRequest(`/invoices/${invoiceId}`, { method: 'PUT', body: JSON.stringify(payload) });
            toast.success('Documento salvato');
        } catch (e) {
            toast.error('Errore salvataggio: ' + e.message);
            setSaving(false);
            return;
        }
        setSaving(false);
        const pdfUrl = `${process.env.REACT_APP_BACKEND_URL}/api/invoices/${invoiceId}/pdf`;
        const w = window.open(pdfUrl, '_blank');
        if (printAfter && w) setTimeout(() => w.print(), 1800);
    };

    const selectedClient = clients.find(c => c.client_id === formData.client_id);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 loading-spinner" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className={`flex gap-0 ${showLivePreview ? 'h-[calc(100vh-64px)]' : ''}`}>
                {/* Editor Column */}
                <div className={`${showLivePreview ? 'w-[55%] overflow-y-auto pr-2' : 'w-full'} transition-all duration-300`}>
                <div className={`space-y-6 ${showLivePreview ? '' : 'max-w-6xl'}`}>
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate('/invoices')}
                        >
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Indietro
                        </Button>
                        <div>
                            <h1 className="font-sans text-2xl font-bold text-slate-900">
                                {isEditing ? 'Modifica Documento' : 'Nuovo Documento'}
                            </h1>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {isEditing && <Button variant="outline" onClick={() => handleOpenPDF(false)} disabled={saving} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9 text-xs"><Eye className="h-3.5 w-3.5 mr-1.5" /> Anteprima</Button>}
                        {isEditing && <Button variant="outline" onClick={() => handleOpenPDF(true)} disabled={saving} className="border-purple-500 text-purple-600 hover:bg-purple-50 h-9 text-xs"><Printer className="h-3.5 w-3.5 mr-1.5" /> Stampa</Button>}
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            data-testid="btn-live-preview"
                            onClick={() => setShowLivePreview(v => !v)}
                            className={`text-xs h-9 ${showLivePreview ? 'bg-sky-50 border-sky-400 text-sky-700' : 'border-sky-300 text-sky-600 hover:bg-sky-50'}`}
                        >
                            <PanelRightOpen className="h-3.5 w-3.5 mr-1" />
                            {showLivePreview ? 'Chiudi Anteprima' : 'Anteprima Live'}
                        </Button>
                        {isEditing && (
                            <Button
                                type="button"
                                variant="outline"
                                data-testid="btn-send-email"
                                onClick={() => setEmailPreviewOpen(true)}
                                className="border-violet-400 text-violet-600 hover:bg-violet-50 text-xs h-9"
                            >
                                <Mail className="h-3.5 w-3.5 mr-1" /> Email
                            </Button>
                        )}
                        {isEditing && formData.status === 'bozza' && (formData.document_type === 'FT' || formData.document_type === 'NC') && (
                            <Button
                                type="button"
                                variant="outline"
                                data-testid="btn-emetti"
                                onClick={async () => {
                                    if (!(await confirm('Confermi l\'emissione del documento? Non sara piu modificabile.'))) return;
                                    try {
                                        await apiRequest(`/invoices/${invoiceId}/status`, { method: 'PATCH', body: { status: 'emessa' } });
                                        toast.success('Documento emesso');
                                        setFormData(f => ({ ...f, status: 'emessa' }));
                                    } catch (e) { toast.error((e && e.message) || 'Errore emissione'); }
                                }}
                                className="border-blue-500 text-blue-700 hover:bg-blue-50 text-xs h-9 font-semibold"
                            >
                                <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Emetti
                            </Button>
                        )}
                        {isEditing && formData.status !== 'bozza' && (formData.document_type === 'FT' || formData.document_type === 'NC') && (
                            <Button
                                type="button"
                                variant="outline"
                                data-testid="btn-send-sdi"
                                onClick={() => setSdiPreviewOpen(true)}
                                className="border-amber-400 text-amber-600 hover:bg-amber-50 text-xs h-9"
                            >
                                <Send className="h-3.5 w-3.5 mr-1" /> Invia SDI
                            </Button>
                        )}
                        <Button
                            data-testid="btn-save-invoice"
                        onClick={handleSave}
                        disabled={saving}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Save className="h-4 w-4 mr-2" />
                        {saving ? 'Salvataggio...' : 'Salva'}
                    </Button>
                    </div>
                </div>

                {/* Document Header */}
                <Card className="border-gray-200">
                    <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                        <CardTitle className="text-lg font-semibold">Intestazione</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-5 gap-4">
                            <div>
                                <Label>Tipo Documento</Label>
                                <Select
                                    value={formData.document_type}
                                    onValueChange={(v) => updateField('document_type', v)}
                                    disabled={isEditing}
                                >
                                    <SelectTrigger data-testid="select-doc-type">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {DOC_TYPES.map(t => (
                                            <SelectItem key={t.value} value={t.value}>
                                                {t.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Numero</Label>
                                <Input
                                    data-testid="input-doc-number"
                                    value={formData.document_number || ''}
                                    onChange={(e) => updateField('document_number', e.target.value)}
                                    placeholder={isEditing ? '' : 'Auto'}
                                    className="font-mono"
                                />
                            </div>
                            <div>
                                <Label>Data Emissione</Label>
                                <Input
                                    type="date"
                                    data-testid="input-issue-date"
                                    value={formData.issue_date}
                                    onChange={(e) => updateField('issue_date', e.target.value)}
                                />
                            </div>
                            <div>
                                <Label>Scadenza</Label>
                                <Input
                                    type="date"
                                    data-testid="input-due-date"
                                    value={formData.due_date}
                                    onChange={(e) => updateField('due_date', e.target.value)}
                                />
                            </div>
                            <div>
                                <Label>Termini Pagamento</Label>
                                <select
                                    data-testid="select-payment-terms"
                                    className="w-full border rounded px-2 py-1.5 text-sm bg-white"
                                    value={formData.payment_terms}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        const pt = paymentTypes.find(p => p.label === val);
                                        const dueDate = pt ? calcDueDate(formData.issue_date, pt) : '';
                                        setFormData(f => ({
                                            ...f,
                                            payment_terms: val,
                                            payment_type_id: pt?.payment_type_id || '',
                                            due_date: dueDate || f.due_date,
                                        }));
                                    }}
                                >
                                    <option value="">-- Seleziona --</option>
                                    {paymentTypes.map(pt => (
                                        <option key={pt.payment_type_id} value={pt.label}>
                                            {pt.label}
                                        </option>
                                    ))}
                                    {/* Fallback: show current value if not in list */}
                                    {formData.payment_terms && !paymentTypes.some(pt => pt.label === formData.payment_terms) && (
                                        <option value={formData.payment_terms}>{formData.payment_terms}</option>
                                    )}
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <div>
                                <Label>Cliente *</Label>
                                <Select
                                    value={formData.client_id || "__none__"}
                                    onValueChange={(v) => {
                                        const cid = v === "__none__" ? "" : v;
                                        updateField('client_id', cid);
                                        // Auto-fill payment terms from client profile
                                        if (cid) {
                                            const cl = clients.find(c => c.client_id === cid);
                                            if (cl?.payment_type_label) {
                                                const pt = paymentTypes.find(p => p.payment_type_id === cl.payment_type_id || p.label === cl.payment_type_label);
                                                const dueDate = pt ? calcDueDate(formData.issue_date, pt) : '';
                                                setFormData(f => ({
                                                    ...f,
                                                    client_id: cid,
                                                    payment_terms: cl.payment_type_label,
                                                    payment_type_id: cl.payment_type_id || '',
                                                    due_date: dueDate || f.due_date,
                                                }));
                                            }
                                        }
                                    }}
                                >
                                    <SelectTrigger data-testid="select-client">
                                        <SelectValue placeholder="Seleziona cliente..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="__none__">-- Seleziona cliente --</SelectItem>
                                        {clients.map(c => (
                                            <SelectItem key={c.client_id} value={c.client_id}>
                                                {c.business_name} {c.partita_iva ? `(${c.partita_iva})` : ''}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                {selectedClient && (
                                    <div className="mt-2 p-3 bg-slate-50 rounded-md text-sm text-slate-600">
                                        <p>{selectedClient.address}</p>
                                        <p>{selectedClient.cap} {selectedClient.city} ({selectedClient.province})</p>
                                        {selectedClient.partita_iva && <p>P.IVA: {selectedClient.partita_iva}</p>}
                                        {selectedClient.codice_sdi && <p>SDI: {selectedClient.codice_sdi}</p>}
                                    </div>
                                )}
                            </div>
                            <div>
                                <Label>Metodo Pagamento</Label>
                                <Select
                                    value={formData.payment_method}
                                    onValueChange={(v) => updateField('payment_method', v)}
                                >
                                    <SelectTrigger data-testid="select-payment-method">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {PAYMENT_METHODS.map(m => (
                                            <SelectItem key={m.value} value={m.value}>
                                                {m.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Line Items */}
                <Card className="border-gray-200">
                    <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-lg font-semibold">Righe Documento</CardTitle>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    data-testid="btn-quick-fill"
                                    onClick={() => setQuickFillOpen(true)}
                                    className="border-amber-400 text-amber-600 hover:bg-amber-50"
                                >
                                    <FileText className="h-4 w-4 mr-2" />
                                    Importa da Preventivo/DDT
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    data-testid="btn-add-line"
                                    onClick={addLine}
                                >
                                    <Plus className="h-4 w-4 mr-2" />
                                    Aggiungi Riga
                                </Button>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B] hover:bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold w-[80px]">Cod.</TableHead>
                                    <TableHead className="text-white font-semibold">Descrizione</TableHead>
                                    <TableHead className="text-white font-semibold w-[80px] text-right">Q.tà</TableHead>
                                    <TableHead className="text-white font-semibold w-[100px] text-right">Prezzo</TableHead>
                                    <TableHead className="text-white font-semibold w-[70px] text-right">Sc.%</TableHead>
                                    <TableHead className="text-white font-semibold w-[90px] text-right">IVA</TableHead>
                                    <TableHead className="text-white font-semibold w-[100px] text-right">Importo</TableHead>
                                    <TableHead className="w-[40px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {formData.lines.map((line, index) => {
                                    const gross = (parseFloat(line.quantity) || 0) * (parseFloat(line.unit_price) || 0);
                                    const discount = gross * ((parseFloat(line.discount_percent) || 0) / 100);
                                    const lineTotal = gross - discount;
                                    
                                    return (
                                        <TableRow key={index} className="hover:bg-slate-50">
                                            <TableCell className="p-1">
                                                <ArticleSearch
                                                    value={line.code}
                                                    onChange={(v) => updateLine(index, 'code', v)}
                                                    onSelect={(article) => {
                                                        const updates = { ...formData };
                                                        updates.lines = [...updates.lines];
                                                        updates.lines[index] = {
                                                            ...updates.lines[index],
                                                            code: article.codice,
                                                            description: article.descrizione,
                                                            unit_price: article.prezzo_unitario || 0,
                                                            vat_rate: article.aliquota_iva || '22',
                                                        };
                                                        setFormData(updates);
                                                    }}
                                                    placeholder="COD"
                                                    testId={`line-code-${index}`}
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <AutoExpandTextarea
                                                    data-testid={`line-desc-${index}`}
                                                    value={line.description}
                                                    onChange={(e) => updateLine(index, 'description', e.target.value)}
                                                    className="text-sm"
                                                    placeholder="Descrizione prodotto/servizio"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Input
                                                    type="number"
                                                    data-testid={`line-qty-${index}`}
                                                    value={line.quantity}
                                                    onChange={(e) => updateLine(index, 'quantity', e.target.value)}
                                                    className="h-8 text-sm text-right [&::-webkit-inner-spin-button]:appearance-none"
                                                    step="0.01"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Input
                                                    type="number"
                                                    data-testid={`line-price-${index}`}
                                                    value={line.unit_price}
                                                    onChange={(e) => updateLine(index, 'unit_price', e.target.value)}
                                                    className="h-8 text-sm text-right [&::-webkit-inner-spin-button]:appearance-none"
                                                    step="0.01"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Input
                                                    type="number"
                                                    data-testid={`line-discount-${index}`}
                                                    value={line.discount_percent}
                                                    onChange={(e) => updateLine(index, 'discount_percent', e.target.value)}
                                                    className="h-8 text-sm text-right [&::-webkit-inner-spin-button]:appearance-none"
                                                    max="100"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Select
                                                    value={line.vat_rate}
                                                    onValueChange={(v) => updateLine(index, 'vat_rate', v)}
                                                >
                                                    <SelectTrigger className="h-8 text-sm">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {VAT_RATES.map(r => (
                                                            <SelectItem key={r.value} value={r.value}>
                                                                {r.label}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </TableCell>
                                            <TableCell className="p-1 text-right font-mono font-semibold text-[#0055FF] bg-slate-50">
                                                {formatCurrency(lineTotal)}
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeLine(index)}
                                                    disabled={formData.lines.length <= 1}
                                                    className="h-8 w-8 p-0 text-slate-400 hover:text-red-600"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* Notes, CUP/CIG/CUC & Totals */}
                <div className="grid grid-cols-2 gap-6">
                    {/* Notes & Public Tender Codes */}
                    <Card className="border-gray-200">
                        <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg font-semibold">Note e Riferimenti</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-3 gap-3">
                                <div>
                                    <Label className="text-xs text-slate-500">CUP</Label>
                                    <Input
                                        data-testid="input-cup"
                                        value={formData.cup || ''}
                                        onChange={(e) => updateField('cup', e.target.value.toUpperCase())}
                                        placeholder="Codice CUP"
                                        className="h-8 text-sm font-mono"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs text-slate-500">CIG</Label>
                                    <Input
                                        data-testid="input-cig"
                                        value={formData.cig || ''}
                                        onChange={(e) => updateField('cig', e.target.value.toUpperCase())}
                                        placeholder="Codice CIG"
                                        className="h-8 text-sm font-mono"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs text-slate-500">CUC</Label>
                                    <Input
                                        data-testid="input-cuc"
                                        value={formData.cuc || ''}
                                        onChange={(e) => updateField('cuc', e.target.value.toUpperCase())}
                                        placeholder="Codice CUC"
                                        className="h-8 text-sm font-mono"
                                    />
                                </div>
                            </div>

                            <div>
                                <Label>Note Documento</Label>
                                <Textarea
                                    value={formData.notes}
                                    onChange={(e) => updateField('notes', e.target.value)}
                                    placeholder="Note visibili in fattura..."
                                    rows={3}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Totals */}
                    <Card className="border-gray-200">
                        <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg font-semibold flex items-center gap-2">
                                <Calculator className="h-5 w-5" />
                                Riepilogo
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-600">Imponibile:</span>
                                    <span className="font-mono font-semibold text-[#0055FF]">{formatCurrency(totals.subtotal)}</span>
                                </div>

                                {Object.entries(totals.vat_breakdown).map(([rate, values]) => (
                                    <div key={rate} className="flex justify-between text-sm">
                                        <span className="text-slate-600">
                                            IVA {rate}% su {formatCurrency(values.imponibile)}:
                                        </span>
                                        <span className="font-mono font-semibold text-[#0055FF]">{formatCurrency(values.imposta)}</span>
                                    </div>
                                ))}

                                {totals.rivalsa_inps > 0 && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-600">Rivalsa INPS:</span>
                                        <span className="font-mono font-semibold text-[#0055FF]">{formatCurrency(totals.rivalsa_inps)}</span>
                                    </div>
                                )}

                                {totals.cassa > 0 && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-600">Cassa Previdenza:</span>
                                        <span className="font-mono font-semibold text-[#0055FF]">{formatCurrency(totals.cassa)}</span>
                                    </div>
                                )}

                                <Separator />

                                <div className="flex justify-between font-bold text-lg">
                                    <span>TOTALE DOCUMENTO:</span>
                                    <span className="font-mono text-[#0055FF]">{formatCurrency(totals.total_document)}</span>
                                </div>

                                {totals.ritenuta > 0 && (
                                    <>
                                        <div className="flex justify-between text-sm text-red-600">
                                            <span>Ritenuta d'acconto:</span>
                                            <span>- {formatCurrency(totals.ritenuta)}</span>
                                        </div>
                                        <div className="flex justify-between font-bold text-lg text-[#1E293B] pt-2 border-t">
                                            <span>NETTO A PAGARE:</span>
                                            <span className="font-mono text-[#0055FF]">{formatCurrency(totals.total_to_pay)}</span>
                                        </div>
                                    </>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <QuickFillModal
                    open={quickFillOpen}
                    onOpenChange={setQuickFillOpen}
                    onSelect={handleQuickFill}
                />
            </div>
            </div>
            {/* Live Preview Panel */}
            {showLivePreview && (
                <div className="w-[45%] shrink-0 h-full">
                    <LivePDFPreview
                        formData={formData}
                        totals={totals}
                        onClose={() => setShowLivePreview(false)}
                    />
                </div>
            )}
            </div>
            <EmailPreviewDialog
                open={emailPreviewOpen}
                onOpenChange={setEmailPreviewOpen}
                previewUrl={`/api/invoices/${invoiceId}/preview-email`}
                sendUrl={`/api/invoices/${invoiceId}/send-email`}
            />
            <SdiPreviewDialog
                open={sdiPreviewOpen}
                onOpenChange={setSdiPreviewOpen}
                invoice={{
                    ...formData,
                    invoice_id: invoiceId,
                    numero: formData.document_number,
                    client_name: selectedClient?.business_name || '',
                    totale: totals.total_document || totals.total_to_pay || 0,
                    total: totals.total_document || totals.total_to_pay || 0,
                    imponibile: totals.subtotal || 0,
                    iva: totals.total_vat || 0,
                    vat: totals.total_vat || 0,
                    stato: formData.status || 'bozza',
                    client_piva: selectedClient?.partita_iva || '',
                    client_cf: selectedClient?.codice_fiscale || '',
                    client_sdi_code: selectedClient?.codice_sdi || '',
                    client_pec: selectedClient?.pec || '',
                }}
                onSent={() => { setSdiPreviewOpen(false); fetchInvoice(); }}
            />
        </DashboardLayout>
    );
}
