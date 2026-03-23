/**
 * SdiPreviewDialog — Mandatory preview before sending invoice to SDI/FattureInCloud.
 * Shows: client, invoice number, amounts, validation, mandatory confirm.
 */
import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { FileText, Send, Loader2, AlertTriangle, ShieldCheck, CheckCircle2, XCircle, Building2, Hash, Euro } from 'lucide-react';
import { apiRequest } from '../lib/utils';

export default function SdiPreviewDialog({ open, onOpenChange, invoice, onSent }) {
    const [sending, setSending] = useState(false);
    const [confirmed, setConfirmed] = useState(false);
    const [validation, setValidation] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (open && invoice) {
            setConfirmed(false);
            setSending(false);
            validateInvoice();
        }
    }, [open, invoice?.invoice_id]);

    const validateInvoice = async () => {
        if (!invoice) return;
        setLoading(true);
        const checks = [];

        // Client data
        if (invoice.client_name) checks.push({ ok: true, label: 'Cliente', value: invoice.client_name });
        else checks.push({ ok: false, label: 'Cliente', value: 'Mancante' });

        // Invoice number
        if (invoice.numero) checks.push({ ok: true, label: 'Numero fattura', value: invoice.numero });
        else checks.push({ ok: false, label: 'Numero fattura', value: 'Non assegnato' });

        // Amounts
        const total = invoice.totale || invoice.total || 0;
        if (total > 0) checks.push({ ok: true, label: 'Totale', value: `${total.toFixed(2)} EUR` });
        else checks.push({ ok: false, label: 'Totale', value: 'Importo zero o mancante' });

        // VAT
        const iva = invoice.iva || invoice.vat || 0;
        checks.push({ ok: true, label: 'IVA', value: `${iva.toFixed(2)} EUR` });

        // Status
        const stato = invoice.stato || invoice.status || '';
        if (['bozza', 'draft', 'emessa'].includes(stato)) {
            checks.push({ ok: true, label: 'Stato', value: stato });
        } else if (['inviata_sdi', 'accettata', 'pagata'].includes(stato)) {
            checks.push({ ok: false, label: 'Stato', value: `Gia ${stato} — possibile duplicato` });
        }

        // Required fields
        if (invoice.client_piva || invoice.client_cf) checks.push({ ok: true, label: 'P.IVA / CF', value: invoice.client_piva || invoice.client_cf });
        else checks.push({ ok: false, label: 'P.IVA / CF', value: 'Mancante — richiesto per SDI' });

        if (invoice.client_sdi_code || invoice.client_pec) checks.push({ ok: true, label: 'Codice SDI / PEC', value: invoice.client_sdi_code || invoice.client_pec });
        else checks.push({ ok: false, label: 'Codice SDI / PEC', value: 'Mancante — richiesto per recapito' });

        setValidation(checks);
        setLoading(false);
    };

    const hasBlockers = validation?.some(c => !c.ok) || false;

    const handleSend = async () => {
        if (!invoice?.invoice_id || !confirmed) return;
        setSending(true);
        try {
            const result = await apiRequest(`/invoices/${invoice.invoice_id}/send-sdi`, { method: 'POST' });
            toast.success(result.message || 'Fattura inviata a SDI');
            onSent?.();
            onOpenChange(false);
        } catch (e) {
            toast.error(e.message || 'Errore invio SDI');
        } finally {
            setSending(false);
        }
    };

    const fmtAmount = (v) => {
        const n = Number(v) || 0;
        return n.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg" data-testid="sdi-preview-dialog">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-blue-600" />
                        Invio SDI — Anteprima obbligatoria
                    </DialogTitle>
                    <DialogDescription>Verifica i dati prima dell'invio a FattureInCloud / SDI</DialogDescription>
                </DialogHeader>

                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                        <span className="ml-2 text-sm text-slate-500">Validazione in corso...</span>
                    </div>
                ) : invoice && (
                    <div className="space-y-4">
                        {/* Invoice summary */}
                        <div className="bg-slate-50 rounded-lg p-4 border space-y-2">
                            <div className="flex items-center gap-2">
                                <Building2 className="h-4 w-4 text-slate-400" />
                                <span className="text-sm font-semibold text-slate-800">{invoice.client_name || 'Cliente non specificato'}</span>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-slate-600">
                                <span className="flex items-center gap-1"><Hash className="h-3 w-3" />{invoice.numero || '—'}</span>
                                <span className="flex items-center gap-1"><Euro className="h-3 w-3" />Imponibile: {fmtAmount(invoice.imponibile || invoice.subtotal)}</span>
                                <span className="flex items-center gap-1">IVA: {fmtAmount(invoice.iva || invoice.vat)}</span>
                            </div>
                            <div className="text-right">
                                <span className="text-lg font-bold text-slate-900">{fmtAmount(invoice.totale || invoice.total)} EUR</span>
                            </div>
                        </div>

                        {/* Validation checks */}
                        <div className="space-y-1.5" data-testid="sdi-validation-checks">
                            {validation?.map((check, i) => (
                                <div key={i} className={`flex items-center gap-2 text-xs p-2 rounded ${check.ok ? 'text-slate-600 bg-white border border-slate-100' : 'text-red-700 bg-red-50 border border-red-200'}`}>
                                    {check.ok ?
                                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" /> :
                                        <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
                                    }
                                    <span className="font-medium w-28 shrink-0">{check.label}</span>
                                    <span className="truncate">{check.value}</span>
                                </div>
                            ))}
                        </div>

                        {/* Blocker warning */}
                        {hasBlockers && (
                            <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 p-3 rounded border border-amber-200" data-testid="sdi-warn-blockers">
                                <AlertTriangle className="h-4 w-4 shrink-0" />
                                <span>Ci sono dati mancanti. L'invio potrebbe essere rifiutato dal sistema SDI. Procedi solo se sei sicuro.</span>
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter className="flex-col items-stretch gap-2 sm:flex-col">
                    <div className="flex items-center gap-2 py-1" data-testid="sdi-confirm-section">
                        <Checkbox id="sdi-confirm" checked={confirmed} onCheckedChange={setConfirmed} data-testid="sdi-confirm-checkbox" />
                        <label htmlFor="sdi-confirm" className="text-xs text-slate-600 cursor-pointer select-none">
                            Ho verificato i dati e confermo l'invio a SDI
                        </label>
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>Annulla</Button>
                        <Button size="sm" className="bg-[#0055FF] text-white"
                            disabled={sending || !confirmed} onClick={handleSend}
                            data-testid="sdi-preview-send-btn">
                            {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <ShieldCheck className="h-4 w-4 mr-1" />}
                            {sending ? 'Invio in corso...' : 'Conferma e Invia a SDI'}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
