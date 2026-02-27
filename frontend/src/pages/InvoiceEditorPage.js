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
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

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
    quantity: 1,
    unit_price: 0,
    discount_percent: 0,
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

    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [clients, setClients] = useState([]);
    
    const [formData, setFormData] = useState({
        document_type: 'FT',
        client_id: '',
        issue_date: new Date().toISOString().split('T')[0],
        due_date: '',
        payment_method: 'bonifico',
        payment_terms: '30gg',
        notes: '',
        internal_notes: '',
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

    // Fetch clients on mount
    useEffect(() => {
        const fetchClients = async () => {
            try {
                const data = await apiRequest('/clients/?limit=100');
                setClients(data.clients);
            } catch (error) {
                toast.error('Errore caricamento clienti');
            }
        };
        fetchClients();
    }, []);

    // Fetch invoice if editing
    useEffect(() => {
        if (!isEditing) return;
        
        const fetchInvoice = async () => {
            try {
                const data = await apiRequest(`/invoices/${invoiceId}`);
                setFormData({
                    document_type: data.document_type,
                    client_id: data.client_id,
                    issue_date: data.issue_date,
                    due_date: data.due_date || '',
                    payment_method: data.payment_method,
                    payment_terms: data.payment_terms,
                    notes: data.notes || '',
                    internal_notes: data.internal_notes || '',
                    tax_settings: data.tax_settings || formData.tax_settings,
                    lines: data.lines.length > 0 ? data.lines : [{ ...emptyLine }],
                });
                setTotals(data.totals);
            } catch (error) {
                toast.error('Documento non trovato');
                navigate('/invoices');
            } finally {
                setLoading(false);
            }
        };
        fetchInvoice();
    }, [invoiceId, isEditing, navigate]);

    // Calculate totals when lines or tax settings change
    useEffect(() => {
        calculateTotals();
    }, [formData.lines, formData.tax_settings]);

    const calculateTotals = () => {
        let subtotal = 0;
        let totalVat = 0;
        const vatBreakdown = {};

        formData.lines.forEach(line => {
            const gross = line.quantity * line.unit_price;
            const discount = gross * (line.discount_percent / 100);
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
            const payload = {
                ...formData,
                lines: formData.lines.filter(l => l.description.trim()),
            };

            if (isEditing) {
                await apiRequest(`/invoices/${invoiceId}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload),
                });
                toast.success('Documento aggiornato');
            } else {
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
            <div className="space-y-6 max-w-6xl">
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

                {/* Document Header */}
                <Card className="border-gray-200">
                    <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                        <CardTitle className="text-lg font-semibold">Intestazione</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-4 gap-4">
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
                                <Select
                                    value={formData.payment_terms}
                                    onValueChange={(v) => updateField('payment_terms', v)}
                                >
                                    <SelectTrigger data-testid="select-payment-terms">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {PAYMENT_TERMS.map(t => (
                                            <SelectItem key={t.value} value={t.value}>
                                                {t.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <div>
                                <Label>Cliente *</Label>
                                <Select
                                    value={formData.client_id || "__none__"}
                                    onValueChange={(v) => updateField('client_id', v === "__none__" ? "" : v)}
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
                                    const gross = line.quantity * line.unit_price;
                                    const discount = gross * (line.discount_percent / 100);
                                    const lineTotal = gross - discount;
                                    
                                    return (
                                        <TableRow key={index} className="hover:bg-slate-50">
                                            <TableCell className="p-1">
                                                <Input
                                                    data-testid={`line-code-${index}`}
                                                    value={line.code}
                                                    onChange={(e) => updateLine(index, 'code', e.target.value)}
                                                    className="h-8 text-sm"
                                                    placeholder="COD"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Textarea
                                                    data-testid={`line-desc-${index}`}
                                                    value={line.description}
                                                    onChange={(e) => updateLine(index, 'description', e.target.value)}
                                                    className="min-h-[32px] h-8 text-sm resize-none"
                                                    placeholder="Descrizione prodotto/servizio"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Input
                                                    type="number"
                                                    data-testid={`line-qty-${index}`}
                                                    value={line.quantity}
                                                    onChange={(e) => updateLine(index, 'quantity', parseFloat(e.target.value) || 0)}
                                                    className="h-8 text-sm text-right"
                                                    min="0"
                                                    step="0.01"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Input
                                                    type="number"
                                                    data-testid={`line-price-${index}`}
                                                    value={line.unit_price}
                                                    onChange={(e) => updateLine(index, 'unit_price', parseFloat(e.target.value) || 0)}
                                                    className="h-8 text-sm text-right"
                                                    min="0"
                                                    step="0.01"
                                                />
                                            </TableCell>
                                            <TableCell className="p-1">
                                                <Input
                                                    type="number"
                                                    data-testid={`line-discount-${index}`}
                                                    value={line.discount_percent}
                                                    onChange={(e) => updateLine(index, 'discount_percent', parseFloat(e.target.value) || 0)}
                                                    className="h-8 text-sm text-right"
                                                    min="0"
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

                {/* Tax Settings & Totals */}
                <div className="grid grid-cols-2 gap-6">
                    {/* Tax Settings */}
                    <Card className="border-gray-200">
                        <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg font-semibold">Impostazioni Fiscali</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Checkbox
                                        id="rivalsa"
                                        checked={formData.tax_settings.apply_rivalsa_inps}
                                        onCheckedChange={(v) => updateTaxSetting('apply_rivalsa_inps', v)}
                                    />
                                    <Label htmlFor="rivalsa" className="text-sm">Rivalsa INPS</Label>
                                </div>
                                {formData.tax_settings.apply_rivalsa_inps && (
                                    <div className="flex items-center gap-2">
                                        <Input
                                            type="number"
                                            value={formData.tax_settings.rivalsa_inps_rate}
                                            onChange={(e) => updateTaxSetting('rivalsa_inps_rate', parseFloat(e.target.value) || 0)}
                                            className="w-20 h-8 text-sm text-right"
                                        />
                                        <span className="text-sm text-slate-500">%</span>
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Checkbox
                                        id="cassa"
                                        checked={formData.tax_settings.apply_cassa}
                                        onCheckedChange={(v) => updateTaxSetting('apply_cassa', v)}
                                    />
                                    <Label htmlFor="cassa" className="text-sm">Cassa Previdenza</Label>
                                </div>
                                {formData.tax_settings.apply_cassa && (
                                    <div className="flex items-center gap-2">
                                        <Input
                                            type="number"
                                            value={formData.tax_settings.cassa_rate}
                                            onChange={(e) => updateTaxSetting('cassa_rate', parseFloat(e.target.value) || 0)}
                                            className="w-20 h-8 text-sm text-right"
                                        />
                                        <span className="text-sm text-slate-500">%</span>
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Checkbox
                                        id="ritenuta"
                                        checked={formData.tax_settings.apply_ritenuta}
                                        onCheckedChange={(v) => updateTaxSetting('apply_ritenuta', v)}
                                    />
                                    <Label htmlFor="ritenuta" className="text-sm">Ritenuta d'Acconto</Label>
                                </div>
                                {formData.tax_settings.apply_ritenuta && (
                                    <div className="flex items-center gap-2">
                                        <Input
                                            type="number"
                                            value={formData.tax_settings.ritenuta_rate}
                                            onChange={(e) => updateTaxSetting('ritenuta_rate', parseFloat(e.target.value) || 0)}
                                            className="w-20 h-8 text-sm text-right"
                                        />
                                        <span className="text-sm text-slate-500">%</span>
                                    </div>
                                )}
                            </div>

                            <Separator />

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
            </div>
        </DashboardLayout>
    );
}
