/**
 * LinkedDocumentsPanel — Shows invoices/NC linked to a preventivo
 * with +/- indicators and a dialog to link new ones.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { FileText, Plus, X, TrendingUp, TrendingDown, Link2, Unlink, Receipt, Loader2 } from 'lucide-react';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

export default function LinkedDocumentsPanel({ prevId, clientId, onUpdate }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showDialog, setShowDialog] = useState(false);

    const fetchLinked = useCallback(async () => {
        if (!prevId) return;
        setLoading(true);
        try {
            const res = await apiRequest(`/preventivi/${prevId}/linked-documents`);
            setData(res);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [prevId]);

    useEffect(() => { fetchLinked(); }, [fetchLinked]);

    const handleUnlink = async (invoiceId, docNumber) => {
        if (!window.confirm(`Scollegare la fattura ${docNumber}?`)) return;
        try {
            await apiRequest(`/preventivi/${prevId}/unlink-invoice/${invoiceId}`, { method: 'DELETE' });
            toast.success('Collegamento rimosso');
            fetchLinked();
            onUpdate?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleLinked = () => {
        setShowDialog(false);
        fetchLinked();
        onUpdate?.();
    };

    if (!prevId) return null;

    const docs = data?.documents || [];
    const hasDocuments = docs.length > 0;

    return (
        <>
            <Card className="border-gray-200" data-testid="linked-documents-panel">
                <CardHeader className="py-2.5 px-4">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                            <Receipt className="h-3.5 w-3.5 text-slate-400" />
                            Documenti Collegati
                        </CardTitle>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px] text-blue-600"
                            onClick={() => setShowDialog(true)} data-testid="btn-link-invoice">
                            <Plus className="h-3 w-3 mr-0.5" />Collega
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="px-4 pb-3 pt-0">
                    {loading && !data && (
                        <div className="flex items-center justify-center py-3">
                            <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                        </div>
                    )}
                    {!loading && !hasDocuments && (
                        <p className="text-[11px] text-slate-400 py-2 text-center">Nessun documento collegato</p>
                    )}
                    {hasDocuments && (
                        <div className="space-y-1.5">
                            {docs.map(d => (
                                <div key={`${d.invoice_id}-${d.link_type}`}
                                    className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs ${
                                        d.document_type === 'NC'
                                            ? 'bg-red-50 border-red-200'
                                            : 'bg-emerald-50 border-emerald-200'
                                    }`}
                                    data-testid={`linked-doc-${d.invoice_id}`}>
                                    {d.document_type === 'NC'
                                        ? <TrendingDown className="h-3.5 w-3.5 text-red-500 shrink-0" />
                                        : <TrendingUp className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                                    }
                                    <div className="flex-1 min-w-0">
                                        <span className="font-mono font-medium">{d.document_number}</span>
                                        <span className="text-slate-400 ml-1">
                                            {d.document_type === 'NC' ? 'NC' : 'FT'}
                                        </span>
                                    </div>
                                    <span className={`font-mono font-semibold ${
                                        d.document_type === 'NC' ? 'text-red-600' : 'text-emerald-600'
                                    }`}>
                                        {d.document_type === 'NC' ? '-' : '+'}{fmtEur(d.amount)}
                                    </span>
                                    {d.link_type === 'manual' && (
                                        <button onClick={() => handleUnlink(d.invoice_id, d.document_number)}
                                            className="p-0.5 text-slate-400 hover:text-red-500" title="Scollega">
                                            <Unlink className="h-3 w-3" />
                                        </button>
                                    )}
                                </div>
                            ))}
                            {/* Summary */}
                            <div className="border-t pt-2 mt-2 space-y-1">
                                <div className="flex justify-between text-[11px]">
                                    <span className="text-slate-500">Imponibile preventivo</span>
                                    <span className="font-mono font-medium">{fmtEur(data?.imponibile)}</span>
                                </div>
                                <div className="flex justify-between text-[11px]">
                                    <span className="text-emerald-600">Fatturato (+)</span>
                                    <span className="font-mono font-medium text-emerald-600">{fmtEur(data?.total_fatturato)}</span>
                                </div>
                                {data?.total_nc > 0 && (
                                    <div className="flex justify-between text-[11px]">
                                        <span className="text-red-600">Note di Credito (-)</span>
                                        <span className="font-mono font-medium text-red-600">-{fmtEur(data?.total_nc)}</span>
                                    </div>
                                )}
                                <div className="flex justify-between text-xs font-semibold border-t pt-1">
                                    <span>Netto fatturato</span>
                                    <span className={data?.is_complete ? 'text-emerald-600' : 'text-slate-800'}>
                                        {fmtEur(data?.net_invoiced)}
                                    </span>
                                </div>
                                {data?.remaining > 0 && (
                                    <div className="flex justify-between text-[11px]">
                                        <span className="text-amber-600">Residuo da fatturare</span>
                                        <span className="font-mono text-amber-600">{fmtEur(data?.remaining)}</span>
                                    </div>
                                )}
                                {/* Progress bar */}
                                <div className="pt-1">
                                    <div className="w-full bg-slate-200 rounded-full h-2">
                                        <div className={`h-2 rounded-full transition-all ${
                                            data?.is_complete ? 'bg-emerald-500' : data?.percentage > 0 ? 'bg-amber-500' : 'bg-slate-300'
                                        }`} style={{ width: `${Math.min(data?.percentage || 0, 100)}%` }} />
                                    </div>
                                    <p className={`text-[10px] font-semibold mt-0.5 text-center ${
                                        data?.is_complete ? 'text-emerald-600' : 'text-slate-500'
                                    }`}>
                                        {data?.is_complete ? 'Completamente fatturato' : `${data?.percentage || 0}% fatturato`}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {showDialog && (
                <LinkInvoiceDialog
                    open={showDialog}
                    onOpenChange={setShowDialog}
                    prevId={prevId}
                    clientId={clientId}
                    existingDocs={docs}
                    onLinked={handleLinked}
                />
            )}
        </>
    );
}


function LinkInvoiceDialog({ open, onOpenChange, prevId, clientId, existingDocs, onLinked }) {
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(false);
    const [linking, setLinking] = useState(null);
    const [customAmount, setCustomAmount] = useState({});

    useEffect(() => {
        if (!open) return;
        setLoading(true);
        apiRequest(`/invoices/?limit=100${clientId ? `&client_id=${clientId}` : ''}`)
            .then(res => {
                const existingIds = new Set((existingDocs || []).map(d => d.invoice_id));
                const available = (res.invoices || []).filter(inv =>
                    !existingIds.has(inv.invoice_id) &&
                    ['FT', 'NC'].includes(inv.document_type) &&
                    inv.status !== 'annullata'
                );
                setInvoices(available);
            })
            .catch(e => console.error(e))
            .finally(() => setLoading(false));
    }, [open, clientId, existingDocs]);

    const handleLink = async (inv) => {
        setLinking(inv.invoice_id);
        try {
            const amount = customAmount[inv.invoice_id];
            const body = { invoice_id: inv.invoice_id };
            if (amount && parseFloat(amount) > 0) body.amount = parseFloat(amount);
            await apiRequest(`/preventivi/${prevId}/link-invoice`, {
                method: 'POST',
                body: JSON.stringify(body),
            });
            toast.success(`${inv.document_type === 'NC' ? 'NC' : 'Fattura'} ${inv.document_number} collegata`);
            onLinked?.();
        } catch (e) { toast.error(e.message); }
        finally { setLinking(null); }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg max-h-[80vh] flex flex-col" data-testid="link-invoice-dialog">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-base">
                        <Link2 className="h-4 w-4 text-blue-600" />
                        Collega Fattura / NC
                    </DialogTitle>
                    <DialogDescription>
                        Seleziona una fattura o nota di credito da collegare a questo preventivo
                    </DialogDescription>
                </DialogHeader>
                <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
                    {loading && (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                        </div>
                    )}
                    {!loading && invoices.length === 0 && (
                        <p className="text-sm text-slate-400 text-center py-8">
                            Nessuna fattura disponibile per il collegamento
                        </p>
                    )}
                    {invoices.map(inv => {
                        const isNC = inv.document_type === 'NC';
                        const total = inv.totals?.subtotal || inv.totals?.total_document || 0;
                        return (
                            <div key={inv.invoice_id}
                                className={`border rounded-lg p-3 ${isNC ? 'border-red-200 bg-red-50/50' : 'border-slate-200 bg-white'}`}
                                data-testid={`linkable-inv-${inv.invoice_id}`}>
                                <div className="flex items-center gap-2">
                                    {isNC
                                        ? <TrendingDown className="h-4 w-4 text-red-500 shrink-0" />
                                        : <FileText className="h-4 w-4 text-blue-500 shrink-0" />
                                    }
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono font-semibold text-sm">{inv.document_number}</span>
                                            <Badge className={`text-[9px] ${isNC ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                                                {inv.document_type}
                                            </Badge>
                                            <Badge className="text-[9px] bg-slate-100 text-slate-600">
                                                {inv.status}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-slate-500 truncate">{inv.client_name}</p>
                                    </div>
                                    <span className="font-mono font-semibold text-sm shrink-0">{fmtEur(total)}</span>
                                </div>
                                <div className="flex items-center gap-2 mt-2">
                                    <div className="flex-1">
                                        <Label className="text-[10px] text-slate-400">Importo da collegare (vuoto = intero)</Label>
                                        <Input
                                            type="number"
                                            step="0.01"
                                            placeholder={total.toFixed(2)}
                                            value={customAmount[inv.invoice_id] || ''}
                                            onChange={e => setCustomAmount(prev => ({ ...prev, [inv.invoice_id]: e.target.value }))}
                                            className="h-7 text-xs"
                                            data-testid={`link-amount-${inv.invoice_id}`}
                                        />
                                    </div>
                                    <Button size="sm" className="h-7 mt-3.5 bg-[#0055FF] text-white text-xs"
                                        disabled={linking === inv.invoice_id}
                                        onClick={() => handleLink(inv)}
                                        data-testid={`btn-link-${inv.invoice_id}`}>
                                        {linking === inv.invoice_id
                                            ? <Loader2 className="h-3 w-3 animate-spin" />
                                            : <><Link2 className="h-3 w-3 mr-1" />Collega</>
                                        }
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </DialogContent>
        </Dialog>
    );
}
