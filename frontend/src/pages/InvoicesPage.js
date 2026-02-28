/**
 * Invoices List Page - Lista Fatture con Tracciamento Pagamenti
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import {
    Plus, MoreHorizontal, Download, RefreshCw, Trash2, Eye, FileCode,
    Copy, CreditCard, CircleDollarSign, CheckCircle2, Clock, AlertCircle,
    Mail, Send,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { PDFPreviewModal } from '../components/PDFPreviewModal';
import EmptyState from '../components/EmptyState';
import EmailPreviewDialog from '../components/EmailPreviewDialog';

const DOC_TYPES = {
    FT: { label: 'Fattura', color: 'bg-blue-100 text-blue-800' },
    PRV: { label: 'Preventivo', color: 'bg-purple-100 text-purple-800' },
    DDT: { label: 'DDT', color: 'bg-orange-100 text-orange-800' },
    NC: { label: 'Nota Credito', color: 'bg-red-100 text-red-800' },
};

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-slate-100 text-slate-800' },
    emessa: { label: 'Emessa', color: 'bg-blue-100 text-blue-800' },
    inviata_sdi: { label: 'Inviata SDI', color: 'bg-yellow-100 text-yellow-800' },
    accettata: { label: 'Accettata', color: 'bg-green-100 text-green-800' },
    rifiutata: { label: 'Rifiutata', color: 'bg-red-100 text-red-800' },
    pagata: { label: 'Pagata', color: 'bg-emerald-100 text-emerald-800' },
    scaduta: { label: 'Scaduta', color: 'bg-orange-100 text-orange-800' },
    annullata: { label: 'Annullata', color: 'bg-gray-100 text-gray-500' },
};

const PAYMENT_STATUS_ICONS = {
    pagata: { icon: CheckCircle2, color: 'text-emerald-600', label: 'Pagata' },
    parzialmente_pagata: { icon: Clock, color: 'text-amber-600', label: 'Parziale' },
    non_pagata: { icon: AlertCircle, color: 'text-red-500', label: 'Non pagata' },
};

const formatCurrency = (value) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(value || 0);

export default function InvoicesPage() {
    const navigate = useNavigate();
    const [invoices, setInvoices] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        document_type: '',
        status: '',
        year: new Date().getFullYear().toString(),
    });

    // Payment dialog state
    const [paymentDialog, setPaymentDialog] = useState(false);
    const [paymentInvoice, setPaymentInvoice] = useState(null);
    const [scadenzeData, setScadenzeData] = useState(null);
    const [paymentForm, setPaymentForm] = useState({
        importo: 0,
        data_pagamento: new Date().toISOString().split('T')[0],
        metodo: 'bonifico',
        note: '',
    });
    const [savingPayment, setSavingPayment] = useState(false);
    
    // PDF Preview state
    const [pdfPreview, setPdfPreview] = useState({ open: false, url: '', title: '' });

    const fetchInvoices = useCallback(async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (filters.document_type) params.append('document_type', filters.document_type);
            if (filters.status) params.append('status', filters.status);
            if (filters.year) params.append('year', filters.year);
            const data = await apiRequest(`/invoices/?${params}`);
            setInvoices(data.invoices);
            setTotal(data.total);
        } catch {
            toast.error('Errore nel caricamento documenti');
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetchInvoices();
    }, [fetchInvoices]);

    const handleDownloadPDF = async (invoice) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/invoices/${invoice.invoice_id}/pdf`,
                { credentials: 'include' }
            );
            if (!response.ok) throw new Error('Errore download');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${invoice.document_number}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch {
            toast.error('Errore nel download del PDF');
        }
    };

    const handleDownloadXML = async (invoice) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/invoices/${invoice.invoice_id}/xml`,
                { credentials: 'include' }
            );
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Errore download');
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${invoice.document_number}.xml`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('XML scaricato');
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleConvert = async (invoice, targetType) => {
        try {
            await apiRequest('/invoices/convert', {
                method: 'POST',
                body: JSON.stringify({ target_type: targetType, source_ids: [invoice.invoice_id] }),
            });
            toast.success(`Documento convertito in ${DOC_TYPES[targetType]?.label}`);
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleDuplicate = async (invoice) => {
        try {
            const result = await apiRequest(`/invoices/${invoice.invoice_id}/duplicate`, {
                method: 'POST',
            });
            toast.success(`Documento duplicato: ${result.document_number}`);
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleSendEmail = async (invoice) => {
        try {
            const result = await apiRequest(`/invoices/${invoice.invoice_id}/send-email`, { method: 'POST' });
            toast.success(result.message);
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleSendSDI = async (invoice) => {
        if (!window.confirm('Confermi l\'invio al Sistema di Interscambio (SDI)?')) return;
        try {
            const result = await apiRequest(`/invoices/${invoice.invoice_id}/send-sdi`, { method: 'POST' });
            toast.success(result.message);
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };


    const handleDelete = async (invoice) => {
        if (!window.confirm('Sei sicuro di voler eliminare questo documento?')) return;
        try {
            await apiRequest(`/invoices/${invoice.invoice_id}`, { method: 'DELETE' });
            toast.success('Documento eliminato');
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };

    // Payment tracking
    const openPaymentDialog = async (invoice) => {
        setPaymentInvoice(invoice);
        setPaymentDialog(true);
        try {
            const data = await apiRequest(`/invoices/${invoice.invoice_id}/scadenze`);
            setScadenzeData(data);
            setPaymentForm(f => ({
                ...f,
                importo: data.residuo || 0,
                data_pagamento: new Date().toISOString().split('T')[0],
            }));
        } catch {
            toast.error('Errore caricamento scadenze');
        }
    };

    const recordPayment = async () => {
        if (!paymentForm.importo || paymentForm.importo <= 0) {
            toast.error('Inserisci un importo valido');
            return;
        }
        setSavingPayment(true);
        try {
            await apiRequest(`/invoices/${paymentInvoice.invoice_id}/scadenze/pagamento`, {
                method: 'POST',
                body: JSON.stringify(paymentForm),
            });
            toast.success('Pagamento registrato');
            // Refresh
            const data = await apiRequest(`/invoices/${paymentInvoice.invoice_id}/scadenze`);
            setScadenzeData(data);
            setPaymentForm(f => ({ ...f, importo: data.residuo || 0 }));
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSavingPayment(false);
        }
    };

    const deletePayment = async (paymentId) => {
        try {
            await apiRequest(`/invoices/${paymentInvoice.invoice_id}/scadenze/pagamento/${paymentId}`, {
                method: 'DELETE',
            });
            toast.success('Pagamento eliminato');
            const data = await apiRequest(`/invoices/${paymentInvoice.invoice_id}/scadenze`);
            setScadenzeData(data);
            fetchInvoices();
        } catch {
            toast.error('Errore eliminazione pagamento');
        }
    };

    const years = Array.from({ length: 5 }, (_, i) =>
        (new Date().getFullYear() - i).toString()
    );

    // Totals
    const totalDoc = invoices.reduce((s, i) => s + (i.totals?.total_document || 0), 0);
    const totalPaid = invoices.reduce((s, i) => s + (i.totale_pagato || 0), 0);
    const totalDue = totalDoc - totalPaid;

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">Fatturazione</h1>
                        <p className="text-slate-600">{total} document{total !== 1 ? 'i' : 'o'}</p>
                    </div>
                    <Button
                        data-testid="btn-new-invoice"
                        onClick={() => navigate('/invoices/new')}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Nuovo Documento
                    </Button>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-3 gap-4">
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Totale Fatturato</p>
                            <p className="text-2xl font-bold font-mono text-slate-900" data-testid="kpi-total">
                                {formatCurrency(totalDoc)}
                            </p>
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3">
                            <p className="text-xs text-emerald-600 uppercase tracking-wide">Incassato</p>
                            <p className="text-2xl font-bold font-mono text-emerald-700" data-testid="kpi-paid">
                                {formatCurrency(totalPaid)}
                            </p>
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3">
                            <p className="text-xs text-red-500 uppercase tracking-wide">Da Incassare</p>
                            <p className="text-2xl font-bold font-mono text-red-600" data-testid="kpi-due">
                                {formatCurrency(totalDue)}
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Filters */}
                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-4">
                            <Select
                                value={filters.document_type || "all"}
                                onValueChange={(v) => setFilters(f => ({ ...f, document_type: v === "all" ? "" : v }))}
                            >
                                <SelectTrigger data-testid="filter-type" className="w-[180px]">
                                    <SelectValue placeholder="Tipo documento" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti i tipi</SelectItem>
                                    <SelectItem value="FT">Fattura</SelectItem>
                                    <SelectItem value="PRV">Preventivo</SelectItem>
                                    <SelectItem value="DDT">DDT</SelectItem>
                                    <SelectItem value="NC">Nota di Credito</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select
                                value={filters.status || "all"}
                                onValueChange={(v) => setFilters(f => ({ ...f, status: v === "all" ? "" : v }))}
                            >
                                <SelectTrigger data-testid="filter-status" className="w-[180px]">
                                    <SelectValue placeholder="Stato" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti gli stati</SelectItem>
                                    <SelectItem value="bozza">Bozza</SelectItem>
                                    <SelectItem value="emessa">Emessa</SelectItem>
                                    <SelectItem value="inviata_sdi">Inviata SDI</SelectItem>
                                    <SelectItem value="pagata">Pagata</SelectItem>
                                    <SelectItem value="scaduta">Scaduta</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select
                                value={filters.year}
                                onValueChange={(v) => setFilters(f => ({ ...f, year: v }))}
                            >
                                <SelectTrigger data-testid="filter-year" className="w-[120px]">
                                    <SelectValue placeholder="Anno" />
                                </SelectTrigger>
                                <SelectContent>
                                    {years.map(y => (
                                        <SelectItem key={y} value={y}>{y}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Numero</TableHead>
                                    <TableHead className="text-white font-semibold">Tipo</TableHead>
                                    <TableHead className="text-white font-semibold">Cliente</TableHead>
                                    <TableHead className="text-white font-semibold">Data</TableHead>
                                    <TableHead className="text-white font-semibold">Scadenza</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Totale</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Pagato</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Da Pagare</TableHead>
                                    <TableHead className="text-white font-semibold">Stato</TableHead>
                                    <TableHead className="w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={10} className="text-center py-8">
                                            <div className="w-6 h-6 loading-spinner mx-auto" />
                                        </TableCell>
                                    </TableRow>
                                ) : invoices.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={10} className="p-0">
                                            <EmptyState
                                                type="invoices"
                                                title="Nessun documento trovato"
                                                description="Crea la tua prima fattura per iniziare."
                                                actionLabel="Crea la prima Fattura"
                                                onAction={() => navigate('/invoices/new')}
                                            />
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    invoices.map((inv) => {
                                        const totalAmount = inv.totals?.total_document || 0;
                                        const paidAmount = inv.totale_pagato || 0;
                                        const dueAmount = totalAmount - paidAmount;
                                        const ps = inv.payment_status || (paidAmount >= totalAmount && totalAmount > 0 ? 'pagata' : paidAmount > 0 ? 'parzialmente_pagata' : 'non_pagata');
                                        const PsIcon = PAYMENT_STATUS_ICONS[ps]?.icon || AlertCircle;
                                        const psColor = PAYMENT_STATUS_ICONS[ps]?.color || 'text-slate-400';

                                        return (
                                            <TableRow
                                                key={inv.invoice_id}
                                                data-testid={`invoice-row-${inv.invoice_id}`}
                                                className="hover:bg-slate-50 cursor-pointer"
                                                onClick={() => navigate(`/invoices/${inv.invoice_id}`)}
                                            >
                                                <TableCell className="font-mono font-medium">
                                                    {inv.document_number}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge className={DOC_TYPES[inv.document_type]?.color}>
                                                        {DOC_TYPES[inv.document_type]?.label}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>{inv.client_name}</TableCell>
                                                <TableCell>{formatDateIT(inv.issue_date)}</TableCell>
                                                <TableCell>{inv.due_date ? formatDateIT(inv.due_date) : '-'}</TableCell>
                                                <TableCell className="text-right font-mono font-semibold text-[#0055FF]">
                                                    {formatCurrency(totalAmount)}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-emerald-700">
                                                    {paidAmount > 0 ? formatCurrency(paidAmount) : '-'}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-red-600">
                                                    {dueAmount > 0.01 ? formatCurrency(dueAmount) : '-'}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex items-center gap-1.5">
                                                        <PsIcon className={`h-4 w-4 ${psColor}`} />
                                                        <Badge className={STATUS_BADGES[inv.status]?.color}>
                                                            {STATUS_BADGES[inv.status]?.label}
                                                        </Badge>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                            <Button variant="ghost" size="sm">
                                                                <MoreHorizontal className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/invoices/${inv.invoice_id}`); }}>
                                                                <Eye className="mr-2 h-4 w-4" />Visualizza
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDuplicate(inv); }}>
                                                                <Copy className="mr-2 h-4 w-4" />Duplica
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDownloadPDF(inv); }}>
                                                                <Download className="mr-2 h-4 w-4" />Scarica PDF
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); setPdfPreview({ open: true, url: `/invoices/${inv.invoice_id}/pdf`, title: `Anteprima ${inv.document_number}` }); }}>
                                                                <Eye className="mr-2 h-4 w-4" />Anteprima PDF
                                                            </DropdownMenuItem>
                                                            {(inv.document_type === 'FT' || inv.document_type === 'NC') && (
                                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDownloadXML(inv); }}>
                                                                    <FileCode className="mr-2 h-4 w-4" />Esporta XML
                                                                </DropdownMenuItem>
                                                            )}
                                                            <DropdownMenuSeparator />
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleSendEmail(inv); }} data-testid="btn-send-email">
                                                                <Mail className="mr-2 h-4 w-4" />Invia via Email
                                                            </DropdownMenuItem>
                                                            {(inv.document_type === 'FT' || inv.document_type === 'NC') && inv.status !== 'bozza' && (
                                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleSendSDI(inv); }} data-testid="btn-send-sdi">
                                                                    <Send className="mr-2 h-4 w-4" />Invia a SDI
                                                                </DropdownMenuItem>
                                                            )}
                                                            <DropdownMenuSeparator />
                                                            {inv.document_type === 'FT' && inv.status !== 'bozza' && (
                                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openPaymentDialog(inv); }}>
                                                                    <CreditCard className="mr-2 h-4 w-4" />Gestisci Pagamenti
                                                                </DropdownMenuItem>
                                                            )}
                                                            {inv.document_type === 'PRV' && (
                                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleConvert(inv, 'FT'); }}>
                                                                    <RefreshCw className="mr-2 h-4 w-4" />Converti in Fattura
                                                                </DropdownMenuItem>
                                                            )}
                                                            {inv.document_type === 'DDT' && (
                                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleConvert(inv, 'FT'); }}>
                                                                    <RefreshCw className="mr-2 h-4 w-4" />Converti in Fattura
                                                                </DropdownMenuItem>
                                                            )}
                                                            {inv.status === 'bozza' && (
                                                                <>
                                                                    <DropdownMenuSeparator />
                                                                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDelete(inv); }} className="text-red-600">
                                                                        <Trash2 className="mr-2 h-4 w-4" />Elimina
                                                                    </DropdownMenuItem>
                                                                </>
                                                            )}
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>

                        {/* Footer totals */}
                        {invoices.length > 0 && (
                            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t text-sm">
                                <span className="text-slate-600">
                                    {invoices.length} document{invoices.length !== 1 ? 'i' : 'o'} visualizzat{invoices.length !== 1 ? 'i' : 'o'}
                                </span>
                                <div className="flex gap-6">
                                    <span>Totale: <strong className="font-mono">{formatCurrency(totalDoc)}</strong></span>
                                    <span>Pagato: <strong className="font-mono text-emerald-700">{formatCurrency(totalPaid)}</strong></span>
                                    <span>Residuo: <strong className="font-mono text-red-600">{formatCurrency(totalDue)}</strong></span>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Payment/Scadenze Dialog */}
            <Dialog open={paymentDialog} onOpenChange={setPaymentDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <CircleDollarSign className="h-5 w-5 text-[#0055FF]" />
                            Scadenze — {paymentInvoice?.document_number}
                        </DialogTitle>
                    </DialogHeader>

                    {scadenzeData ? (
                        <div className="space-y-4">
                            {/* Summary */}
                            <div className="grid grid-cols-3 gap-3">
                                <div className="bg-slate-50 rounded-lg p-3 text-center">
                                    <p className="text-xs text-slate-500">Totale</p>
                                    <p className="font-mono font-bold">{formatCurrency(scadenzeData.total_document)}</p>
                                </div>
                                <div className="bg-emerald-50 rounded-lg p-3 text-center">
                                    <p className="text-xs text-emerald-600">Pagato</p>
                                    <p className="font-mono font-bold text-emerald-700">{formatCurrency(scadenzeData.totale_pagato)}</p>
                                </div>
                                <div className="bg-red-50 rounded-lg p-3 text-center">
                                    <p className="text-xs text-red-500">Residuo</p>
                                    <p className="font-mono font-bold text-red-600">{formatCurrency(scadenzeData.residuo)}</p>
                                </div>
                            </div>

                            {/* Payment history */}
                            {(scadenzeData.pagamenti || []).length > 0 && (
                                <div>
                                    <p className="text-sm font-semibold text-slate-700 mb-2">Pagamenti effettuati</p>
                                    <div className="space-y-2 max-h-[180px] overflow-y-auto">
                                        {scadenzeData.pagamenti.map((p) => (
                                            <div key={p.payment_id} className="flex items-center justify-between bg-slate-50 rounded-md px-3 py-2">
                                                <div>
                                                    <p className="font-mono font-semibold text-emerald-700">{formatCurrency(p.importo)}</p>
                                                    <p className="text-xs text-slate-500">
                                                        {p.data_pagamento ? new Date(p.data_pagamento).toLocaleDateString('it-IT') : '-'}
                                                        {p.metodo ? ` — ${p.metodo}` : ''}
                                                        {p.note ? ` — ${p.note}` : ''}
                                                    </p>
                                                </div>
                                                <Button
                                                    variant="ghost" size="sm"
                                                    onClick={() => deletePayment(p.payment_id)}
                                                    data-testid={`btn-delete-payment-${p.payment_id}`}
                                                >
                                                    <Trash2 className="h-3.5 w-3.5 text-red-400" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Add payment form */}
                            {scadenzeData.residuo > 0.01 && (
                                <div className="border-t pt-4 space-y-3">
                                    <p className="text-sm font-semibold text-slate-700">Registra pagamento</p>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Label className="text-xs">Importo</Label>
                                            <Input
                                                data-testid="input-payment-amount"
                                                type="number" step="0.01" min="0.01"
                                                max={scadenzeData.residuo}
                                                value={paymentForm.importo}
                                                onChange={(e) => setPaymentForm(f => ({ ...f, importo: parseFloat(e.target.value) || 0 }))}
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Data</Label>
                                            <Input
                                                data-testid="input-payment-date"
                                                type="date"
                                                value={paymentForm.data_pagamento}
                                                onChange={(e) => setPaymentForm(f => ({ ...f, data_pagamento: e.target.value }))}
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Label className="text-xs">Metodo</Label>
                                            <Select
                                                value={paymentForm.metodo || 'bonifico'}
                                                onValueChange={(v) => setPaymentForm(f => ({ ...f, metodo: v }))}
                                            >
                                                <SelectTrigger data-testid="select-payment-method">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="bonifico">Bonifico</SelectItem>
                                                    <SelectItem value="contanti">Contanti</SelectItem>
                                                    <SelectItem value="carta">Carta</SelectItem>
                                                    <SelectItem value="assegno">Assegno</SelectItem>
                                                    <SelectItem value="riba">RiBa</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div>
                                            <Label className="text-xs">Note</Label>
                                            <Input
                                                data-testid="input-payment-note"
                                                placeholder="Rif. bonifico..."
                                                value={paymentForm.note}
                                                onChange={(e) => setPaymentForm(f => ({ ...f, note: e.target.value }))}
                                            />
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            data-testid="btn-pay-full"
                                            variant="outline" size="sm"
                                            onClick={() => setPaymentForm(f => ({ ...f, importo: scadenzeData.residuo }))}
                                        >
                                            Saldo Completo
                                        </Button>
                                        <Button
                                            data-testid="btn-record-payment"
                                            onClick={recordPayment}
                                            disabled={savingPayment}
                                            className="bg-emerald-600 text-white hover:bg-emerald-700"
                                        >
                                            {savingPayment ? 'Salvataggio...' : 'Registra Pagamento'}
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {scadenzeData.residuo <= 0.01 && (
                                <div className="flex items-center gap-2 p-3 bg-emerald-50 rounded-lg">
                                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                    <p className="text-sm text-emerald-800 font-medium">Fattura completamente saldata</p>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="flex justify-center py-8">
                            <div className="w-6 h-6 loading-spinner" />
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            <PDFPreviewModal
                open={pdfPreview.open}
                onClose={() => setPdfPreview({ open: false, url: '', title: '' })}
                pdfUrl={pdfPreview.url}
                title={pdfPreview.title}
            />
        </DashboardLayout>
    );
}
