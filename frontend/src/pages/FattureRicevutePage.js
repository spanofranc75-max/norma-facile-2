/**
 * Fatture Ricevute - Received Invoices from Suppliers
 * Supports manual entry, XML import, payment tracking, and article extraction.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
    Plus, Search, Upload, MoreHorizontal, Eye, Trash2, CreditCard,
    FileCode, PackagePlus, CheckCircle2, Clock, AlertCircle,
    CircleDollarSign, FileUp,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const STATUS_BADGES = {
    da_registrare: { label: 'Da Registrare', color: 'bg-yellow-100 text-yellow-800' },
    registrata: { label: 'Registrata', color: 'bg-blue-100 text-blue-800' },
    pagata: { label: 'Pagata', color: 'bg-emerald-100 text-emerald-800' },
    contestata: { label: 'Contestata', color: 'bg-red-100 text-red-800' },
};

const PAYMENT_STATUS_ICONS = {
    pagata: { icon: CheckCircle2, color: 'text-emerald-600' },
    parzialmente_pagata: { icon: Clock, color: 'text-amber-600' },
    non_pagata: { icon: AlertCircle, color: 'text-red-500' },
};

const TIPO_DOC = {
    TD01: 'Fattura', TD02: 'Acconto', TD03: 'Acconto', TD04: 'Nota Credito',
    TD05: 'Nota Debito', TD06: 'Parcella', TD24: 'Fattura Differita', TD25: 'Fattura Differita',
};

const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

export default function FattureRicevutePage() {
    const [fatture, setFatture] = useState([]);
    const [total, setTotal] = useState(0);
    const [kpi, setKpi] = useState({ totale_fatture: 0, totale_pagato: 0, da_pagare: 0, count: 0 });
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({ status: '', year: new Date().getFullYear().toString() });
    const [searchQ, setSearchQ] = useState('');

    // Dialogs
    const [detailDialog, setDetailDialog] = useState(false);
    const [selectedFR, setSelectedFR] = useState(null);
    const [paymentDialog, setPaymentDialog] = useState(false);
    const [paymentData, setPaymentData] = useState(null);
    const [paymentForm, setPaymentForm] = useState({ importo: 0, data_pagamento: '', metodo: 'bonifico', note: '' });
    const [savingPayment, setSavingPayment] = useState(false);
    const [extracting, setExtracting] = useState(false);
    const [uploading, setUploading] = useState(false);

    const fileInputRef = useRef(null);

    const fetchFatture = useCallback(async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (filters.status) params.append('status', filters.status);
            if (filters.year) params.append('year', filters.year);
            if (searchQ) params.append('q', searchQ);
            const data = await apiRequest(`/fatture-ricevute/?${params}`);
            setFatture(data.fatture || []);
            setTotal(data.total || 0);
            setKpi(data.kpi || { totale_fatture: 0, totale_pagato: 0, da_pagare: 0, count: 0 });
        } catch {
            toast.error('Errore caricamento fatture ricevute');
        } finally {
            setLoading(false);
        }
    }, [filters, searchQ]);

    useEffect(() => {
        const timer = setTimeout(fetchFatture, 300);
        return () => clearTimeout(timer);
    }, [fetchFatture]);

    const years = Array.from({ length: 5 }, (_, i) => (new Date().getFullYear() - i).toString());

    // XML Upload (single or multiple)
    const handleXmlUpload = async (e) => {
        const files = Array.from(e.target.files || []);
        if (!files.length) return;

        // Single file → use single endpoint, Multiple → batch
        if (files.length === 1) {
            const file = files[0];
            const fname = file.name.toLowerCase();
            if (!fname.endsWith('.xml') && !fname.endsWith('.p7m')) {
                toast.error('Seleziona un file .xml o .xml.p7m (FatturaPA)');
                return;
            }
            setUploading(true);
            try {
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/fatture-ricevute/import-xml`, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData,
                });
                if (!res.ok) {
                    let detail = `Errore ${res.status}`;
                    try { const err = await res.json(); detail = err.detail || detail; } catch {}
                    throw new Error(detail);
                }
                const result = await res.json();
                toast.success(result.message);
                if (!result.fornitore_trovato) {
                    toast.info('Fornitore non trovato in anagrafica — puoi aggiungerlo dalla pagina Fornitori');
                }
                fetchFatture();
            } catch (err) {
                toast.error(err.message);
            } finally {
                setUploading(false);
                if (fileInputRef.current) fileInputRef.current.value = '';
            }
        } else {
            // Multiple files → batch endpoint
            setUploading(true);
            try {
                const formData = new FormData();
                files.forEach(f => formData.append('files', f));
                const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/fatture-ricevute/import-xml-batch`, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData,
                });
                if (!res.ok) {
                    let detail = `Errore ${res.status}`;
                    try { const err = await res.json(); detail = err.detail || detail; } catch {}
                    throw new Error(detail);
                }
                const result = await res.json();
                toast.success(result.message);
                if (result.errors?.length) {
                    result.errors.forEach(e => toast.warning(e));
                }
                fetchFatture();
            } catch (err) {
                toast.error(err.message);
            } finally {
                setUploading(false);
                if (fileInputRef.current) fileInputRef.current.value = '';
            }
        }
    };

    // View detail
    const openDetail = async (fr) => {
        try {
            const data = await apiRequest(`/fatture-ricevute/${fr.fr_id}`);
            setSelectedFR(data);
            setDetailDialog(true);
        } catch {
            toast.error('Errore caricamento dettagli');
        }
    };

    // Delete
    const handleDelete = async (fr) => {
        if (!window.confirm(`Eliminare la fattura ${fr.numero_documento}?`)) return;
        try {
            await apiRequest(`/fatture-ricevute/${fr.fr_id}`, { method: 'DELETE' });
            toast.success('Fattura eliminata');
            fetchFatture();
        } catch {
            toast.error('Errore eliminazione');
        }
    };

    // Extract articles
    const handleExtract = async (fr) => {
        setExtracting(true);
        try {
            const result = await apiRequest(`/fatture-ricevute/${fr.fr_id}/extract-articoli`, { method: 'POST' });
            toast.success(result.message);
        } catch (err) {
            toast.error(err.message || 'Errore estrazione');
        } finally {
            setExtracting(false);
        }
    };

    // Change status
    const handleStatusChange = async (fr, newStatus) => {
        try {
            await apiRequest(`/fatture-ricevute/${fr.fr_id}`, {
                method: 'PUT',
                body: JSON.stringify({ status: newStatus }),
            });
            toast.success('Stato aggiornato');
            fetchFatture();
        } catch {
            toast.error('Errore aggiornamento stato');
        }
    };

    // Payment dialog
    const openPaymentDialog = async (fr) => {
        try {
            const data = await apiRequest(`/fatture-ricevute/${fr.fr_id}/pagamenti`);
            setPaymentData({ ...data, fr_id: fr.fr_id, numero_documento: fr.numero_documento });
            setPaymentForm({ importo: data.residuo || 0, data_pagamento: new Date().toISOString().split('T')[0], metodo: 'bonifico', note: '' });
            setPaymentDialog(true);
        } catch {
            toast.error('Errore caricamento pagamenti');
        }
    };

    const recordPayment = async () => {
        if (!paymentForm.importo || paymentForm.importo <= 0) {
            toast.error('Inserisci un importo valido');
            return;
        }
        setSavingPayment(true);
        try {
            await apiRequest(`/fatture-ricevute/${paymentData.fr_id}/pagamenti`, {
                method: 'POST',
                body: JSON.stringify(paymentForm),
            });
            toast.success('Pagamento registrato');
            const data = await apiRequest(`/fatture-ricevute/${paymentData.fr_id}/pagamenti`);
            setPaymentData({ ...data, fr_id: paymentData.fr_id, numero_documento: paymentData.numero_documento });
            setPaymentForm(f => ({ ...f, importo: data.residuo || 0 }));
            fetchFatture();
        } catch (err) {
            toast.error(err.message);
        } finally {
            setSavingPayment(false);
        }
    };

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">Fatture Ricevute</h1>
                        <p className="text-slate-600">{total} fattur{total !== 1 ? 'e' : 'a'} da fornitori</p>
                    </div>
                    <div className="flex gap-2">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".xml,.p7m"
                            multiple
                            className="hidden"
                            onChange={handleXmlUpload}
                            data-testid="input-xml-upload"
                        />
                        <Button
                            data-testid="btn-import-xml"
                            variant="outline"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                            className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50"
                        >
                            <FileUp className="h-4 w-4 mr-2" />
                            {uploading ? 'Importazione...' : 'Importa XML / P7M'}
                        </Button>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-3 gap-4">
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Totale Fatture</p>
                            <p className="text-2xl font-bold font-mono text-slate-900" data-testid="kpi-fr-total">
                                {formatCurrency(kpi.totale_fatture)}
                            </p>
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3">
                            <p className="text-xs text-emerald-600 uppercase tracking-wide">Pagato</p>
                            <p className="text-2xl font-bold font-mono text-emerald-700" data-testid="kpi-fr-paid">
                                {formatCurrency(kpi.totale_pagato)}
                            </p>
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3">
                            <p className="text-xs text-red-500 uppercase tracking-wide">Da Pagare</p>
                            <p className="text-2xl font-bold font-mono text-red-600" data-testid="kpi-fr-due">
                                {formatCurrency(kpi.da_pagare)}
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Filters */}
                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-4">
                            <div className="relative flex-1 max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input
                                    data-testid="search-fr"
                                    placeholder="Cerca per fornitore o numero..."
                                    value={searchQ}
                                    onChange={(e) => setSearchQ(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                            <Select
                                value={filters.status || '__all__'}
                                onValueChange={(v) => setFilters(f => ({ ...f, status: v === '__all__' ? '' : v }))}
                            >
                                <SelectTrigger data-testid="filter-fr-status" className="w-[180px]">
                                    <SelectValue placeholder="Stato" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">Tutti gli stati</SelectItem>
                                    <SelectItem value="da_registrare">Da Registrare</SelectItem>
                                    <SelectItem value="registrata">Registrata</SelectItem>
                                    <SelectItem value="pagata">Pagata</SelectItem>
                                    <SelectItem value="contestata">Contestata</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select
                                value={filters.year}
                                onValueChange={(v) => setFilters(f => ({ ...f, year: v }))}
                            >
                                <SelectTrigger data-testid="filter-fr-year" className="w-[120px]">
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
                                    <TableHead className="text-white font-semibold">Fornitore</TableHead>
                                    <TableHead className="text-white font-semibold">Tipo</TableHead>
                                    <TableHead className="text-white font-semibold">Numero</TableHead>
                                    <TableHead className="text-white font-semibold">Data</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Totale</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Pagato</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Da Pagare</TableHead>
                                    <TableHead className="text-white font-semibold">Stato</TableHead>
                                    <TableHead className="text-white font-semibold w-[40px]">XML</TableHead>
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
                                ) : fatture.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={10} className="p-0">
                                            <EmptyState
                                                type="fatture_ricevute"
                                                title="Nessuna fattura ricevuta"
                                                description="Importa fatture XML o P7M dalla PEC, oppure registra manualmente. Supporta upload multiplo."
                                                actionLabel="Importa XML / P7M"
                                                onAction={() => fileInputRef.current?.click()}
                                            />
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    fatture.map((fr) => {
                                        const totalAmount = fr.totale_documento || 0;
                                        const paidAmount = fr.totale_pagato || 0;
                                        const dueAmount = totalAmount - paidAmount;
                                        const ps = fr.payment_status || 'non_pagata';
                                        const PsIcon = PAYMENT_STATUS_ICONS[ps]?.icon || AlertCircle;
                                        const psColor = PAYMENT_STATUS_ICONS[ps]?.color || 'text-slate-400';

                                        return (
                                            <TableRow
                                                key={fr.fr_id}
                                                data-testid={`fr-row-${fr.fr_id}`}
                                                className="hover:bg-slate-50 cursor-pointer"
                                                onClick={() => openDetail(fr)}
                                            >
                                                <TableCell className="font-medium max-w-[180px] truncate">
                                                    {fr.fornitore_nome || 'N/A'}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge className="bg-slate-100 text-slate-700">
                                                        {TIPO_DOC[fr.tipo_documento] || fr.tipo_documento}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="font-mono text-sm">{fr.numero_documento}</TableCell>
                                                <TableCell>{fr.data_documento ? formatDateIT(fr.data_documento) : '-'}</TableCell>
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
                                                        <Badge className={STATUS_BADGES[fr.status]?.color || STATUS_BADGES.da_registrare.color}>
                                                            {STATUS_BADGES[fr.status]?.label || fr.status}
                                                        </Badge>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    {fr.has_xml && <FileCode className="h-4 w-4 text-[#0055FF]" title="XML SDI" />}
                                                </TableCell>
                                                <TableCell>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                            <Button variant="ghost" size="sm">
                                                                <MoreHorizontal className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openDetail(fr); }}>
                                                                <Eye className="mr-2 h-4 w-4" />Dettagli
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openPaymentDialog(fr); }}>
                                                                <CreditCard className="mr-2 h-4 w-4" />Gestisci Pagamenti
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleExtract(fr); }} disabled={extracting}>
                                                                <PackagePlus className="mr-2 h-4 w-4" />Estrai Articoli
                                                            </DropdownMenuItem>
                                                            <DropdownMenuSeparator />
                                                            {fr.status === 'da_registrare' && (
                                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleStatusChange(fr, 'registrata'); }}>
                                                                    <CheckCircle2 className="mr-2 h-4 w-4" />Segna come Registrata
                                                                </DropdownMenuItem>
                                                            )}
                                                            <DropdownMenuSeparator />
                                                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDelete(fr); }} className="text-red-600">
                                                                <Trash2 className="mr-2 h-4 w-4" />Elimina
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            {/* Detail Dialog */}
            <Dialog open={detailDialog} onOpenChange={setDetailDialog}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileCode className="h-5 w-5 text-[#0055FF]" />
                            Fattura {selectedFR?.numero_documento} — {selectedFR?.fornitore_nome}
                        </DialogTitle>
                    </DialogHeader>
                    {selectedFR && (
                        <div className="space-y-4">
                            {/* Header info */}
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <p className="text-slate-500">Fornitore</p>
                                    <p className="font-medium">{selectedFR.fornitore_nome}</p>
                                    {selectedFR.fornitore_piva && <p className="text-xs text-slate-500">P.IVA: {selectedFR.fornitore_piva}</p>}
                                </div>
                                <div>
                                    <p className="text-slate-500">Documento</p>
                                    <p className="font-medium">{TIPO_DOC[selectedFR.tipo_documento] || selectedFR.tipo_documento} {selectedFR.numero_documento}</p>
                                    <p className="text-xs text-slate-500">{selectedFR.data_documento ? formatDateIT(selectedFR.data_documento) : '-'}</p>
                                </div>
                            </div>

                            {/* Line items */}
                            <div>
                                <p className="text-sm font-semibold text-slate-700 mb-2">Righe ({selectedFR.linee?.length || 0})</p>
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-100">
                                            <TableHead className="text-xs">Cod.</TableHead>
                                            <TableHead className="text-xs">Descrizione</TableHead>
                                            <TableHead className="text-xs text-right">Q.tà</TableHead>
                                            <TableHead className="text-xs text-right">Prezzo</TableHead>
                                            <TableHead className="text-xs text-right">Importo</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(selectedFR.linee || []).map((l, i) => (
                                            <TableRow key={i} className="text-sm">
                                                <TableCell className="font-mono text-xs text-[#0055FF]">{l.codice_articolo || '-'}</TableCell>
                                                <TableCell className="max-w-[250px] truncate">{l.descrizione}</TableCell>
                                                <TableCell className="text-right">{l.quantita} {l.unita_misura}</TableCell>
                                                <TableCell className="text-right font-mono">{formatCurrency(l.prezzo_unitario)}</TableCell>
                                                <TableCell className="text-right font-mono font-semibold">{formatCurrency(l.importo)}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>

                            {/* Totals */}
                            <div className="flex justify-end">
                                <div className="w-64 space-y-1 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Imponibile</span>
                                        <span className="font-mono">{formatCurrency(selectedFR.imponibile)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">IVA</span>
                                        <span className="font-mono">{formatCurrency(selectedFR.imposta)}</span>
                                    </div>
                                    <div className="flex justify-between pt-1 border-t font-bold">
                                        <span>Totale</span>
                                        <span className="font-mono text-[#0055FF]">{formatCurrency(selectedFR.totale_documento)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="flex gap-2 pt-2 border-t">
                                <Button
                                    data-testid="btn-extract-detail"
                                    variant="outline" size="sm"
                                    onClick={() => { handleExtract(selectedFR); }}
                                    disabled={extracting}
                                >
                                    <PackagePlus className="h-4 w-4 mr-2" />
                                    {extracting ? 'Estrazione...' : 'Estrai in Catalogo'}
                                </Button>
                                <Button
                                    data-testid="btn-payment-detail"
                                    variant="outline" size="sm"
                                    onClick={() => { setDetailDialog(false); openPaymentDialog(selectedFR); }}
                                >
                                    <CreditCard className="h-4 w-4 mr-2" />
                                    Gestisci Pagamenti
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* Payment Dialog */}
            <Dialog open={paymentDialog} onOpenChange={setPaymentDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <CircleDollarSign className="h-5 w-5 text-[#0055FF]" />
                            Pagamenti — {paymentData?.numero_documento}
                        </DialogTitle>
                    </DialogHeader>
                    {paymentData ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-3 gap-3">
                                <div className="bg-slate-50 rounded-lg p-3 text-center">
                                    <p className="text-xs text-slate-500">Totale</p>
                                    <p className="font-mono font-bold">{formatCurrency(paymentData.total_document)}</p>
                                </div>
                                <div className="bg-emerald-50 rounded-lg p-3 text-center">
                                    <p className="text-xs text-emerald-600">Pagato</p>
                                    <p className="font-mono font-bold text-emerald-700">{formatCurrency(paymentData.totale_pagato)}</p>
                                </div>
                                <div className="bg-red-50 rounded-lg p-3 text-center">
                                    <p className="text-xs text-red-500">Residuo</p>
                                    <p className="font-mono font-bold text-red-600">{formatCurrency(paymentData.residuo)}</p>
                                </div>
                            </div>

                            {(paymentData.pagamenti || []).length > 0 && (
                                <div>
                                    <p className="text-sm font-semibold text-slate-700 mb-2">Pagamenti effettuati</p>
                                    <div className="space-y-2 max-h-[150px] overflow-y-auto">
                                        {paymentData.pagamenti.map((p) => (
                                            <div key={p.payment_id} className="flex items-center justify-between bg-slate-50 rounded-md px-3 py-2">
                                                <div>
                                                    <p className="font-mono font-semibold text-emerald-700">{formatCurrency(p.importo)}</p>
                                                    <p className="text-xs text-slate-500">
                                                        {p.data_pagamento ? new Date(p.data_pagamento).toLocaleDateString('it-IT') : '-'}
                                                        {p.metodo ? ` — ${p.metodo}` : ''}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {paymentData.residuo > 0.01 && (
                                <div className="border-t pt-4 space-y-3">
                                    <p className="text-sm font-semibold text-slate-700">Registra pagamento</p>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Label className="text-xs">Importo</Label>
                                            <Input
                                                data-testid="input-fr-payment-amount"
                                                type="number" step="0.01" min="0.01"
                                                value={paymentForm.importo}
                                                onChange={(e) => setPaymentForm(f => ({ ...f, importo: parseFloat(e.target.value) || 0 }))}
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Data</Label>
                                            <Input
                                                data-testid="input-fr-payment-date"
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
                                                <SelectTrigger><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="bonifico">Bonifico</SelectItem>
                                                    <SelectItem value="contanti">Contanti</SelectItem>
                                                    <SelectItem value="carta">Carta</SelectItem>
                                                    <SelectItem value="riba">RiBa</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div>
                                            <Label className="text-xs">Note</Label>
                                            <Input
                                                placeholder="Rif. bonifico..."
                                                value={paymentForm.note}
                                                onChange={(e) => setPaymentForm(f => ({ ...f, note: e.target.value }))}
                                            />
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline" size="sm"
                                            onClick={() => setPaymentForm(f => ({ ...f, importo: paymentData.residuo }))}
                                        >
                                            Saldo Completo
                                        </Button>
                                        <Button
                                            data-testid="btn-fr-record-payment"
                                            onClick={recordPayment}
                                            disabled={savingPayment}
                                            className="bg-emerald-600 text-white hover:bg-emerald-700"
                                        >
                                            {savingPayment ? 'Salvataggio...' : 'Registra Pagamento'}
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {paymentData.residuo <= 0.01 && (
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
        </DashboardLayout>
    );
}
