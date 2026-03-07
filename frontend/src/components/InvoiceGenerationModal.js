/**
 * InvoiceGenerationModal — Progressive Invoicing Wizard.
 * 3 modes: Acconto (%), SAL (select lines or custom amount), Saldo Finale.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Percent, ListChecks, CheckCircle2, ArrowRightLeft, Loader2,
    Receipt, AlertTriangle, FileText,
} from 'lucide-react';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const MODES = [
    { key: 'acconto', label: 'Acconto %', icon: Percent, desc: "Fattura una percentuale dell'imponibile", color: 'bg-amber-500' },
    { key: 'sal', label: 'SAL', icon: ListChecks, desc: 'Seleziona righe o importo personalizzato', color: 'bg-blue-500' },
    { key: 'saldo', label: 'Saldo Finale', icon: CheckCircle2, desc: 'Fattura il residuo (deduce gli acconti)', color: 'bg-emerald-500' },
];

export default function InvoiceGenerationModal({ open, onOpenChange, prevId, onCreated }) {
    const [mode, setMode] = useState(null);
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [creating, setCreating] = useState(false);
    const [prevData, setPrevData] = useState(null);

    // Acconto state
    const [percentage, setPercentage] = useState(30);

    // SAL state
    const [salMode, setSalMode] = useState('lines'); // 'lines' or 'amount'
    const [selectedLines, setSelectedLines] = useState([]);
    const [customAmount, setCustomAmount] = useState('');

    // Load invoicing status when modal opens
    const fetchStatus = useCallback(async () => {
        if (!prevId || !open) return;
        setLoading(true);
        try {
            const [s, p] = await Promise.all([
                apiRequest(`/preventivi/${prevId}/invoicing-status`),
                apiRequest(`/preventivi/${prevId}`),
            ]);
            setStatus(s);
            setPrevData(p);
        } catch (e) {
            toast.error('Errore caricamento stato fatturazione');
        } finally {
            setLoading(false);
        }
    }, [prevId, open]);

    useEffect(() => {
        if (open) {
            setMode(null);
            setPercentage(30);
            setSalMode('lines');
            setSelectedLines([]);
            setCustomAmount('');
            fetchStatus();
        }
    }, [open, fetchStatus]);

    const handleCreate = async () => {
        if (!mode) return;
        setCreating(true);
        try {
            const body = { invoice_type: mode };
            if (mode === 'acconto') {
                body.percentage = parseFloat(percentage) || 0;
            } else if (mode === 'sal') {
                if (salMode === 'lines') {
                    body.selected_lines = selectedLines;
                } else {
                    body.custom_amount = parseFloat(customAmount) || 0;
                }
            }
            const res = await apiRequest(`/preventivi/${prevId}/progressive-invoice`, { method: 'POST', body });
            toast.success(res.message);
            onOpenChange(false);
            if (onCreated) onCreated(res);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setCreating(false);
        }
    };

    const toggleLine = (idx) => {
        setSelectedLines(prev => prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]);
    };

    // Calculated preview amounts
    const totalPrev = status?.total_preventivo || 0;
    const remaining = status?.remaining ?? 0;
    // ?? invece di || per gestire correttamente remaining = 0
    const lines = prevData?.lines || [];

    let previewAmount = 0;
    if (mode === 'acconto') {
        previewAmount = totalPrev * (parseFloat(percentage) || 0) / 100;
    } else if (mode === 'sal') {
        if (salMode === 'lines') {
            previewAmount = selectedLines.reduce((s, idx) => s + (lines[idx] ? parseFloat(lines[idx].line_total || 0) : 0), 0);
        } else {
            previewAmount = parseFloat(customAmount) || 0;
        }
    } else if (mode === 'saldo') {
        previewAmount = remaining;
    }

    const isValid = mode && (
        (mode === 'acconto' && percentage > 0 && percentage <= 100 && previewAmount <= remaining + 0.01) ||
        (mode === 'sal' && ((salMode === 'lines' && selectedLines.length > 0) || (salMode === 'amount' && previewAmount > 0)) && previewAmount <= remaining + 0.01) ||
        (mode === 'saldo' && remaining >= -0.01)
    );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="invoice-generation-modal">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-[#1E293B]">
                        <Receipt className="h-5 w-5 text-[#0055FF]" />
                        Genera Fattura Progressiva
                    </DialogTitle>
                </DialogHeader>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-[#0055FF]" />
                    </div>
                ) : (
                    <div className="space-y-4">
                        {/* Status bar */}
                        {status && (
                            <div className="bg-slate-50 rounded-lg p-3 space-y-2" data-testid="invoicing-status-bar">
                                <div className="flex justify-between text-xs text-slate-500">
                                    <span>Fatturato: {fmtEur(status.total_invoiced)} di {fmtEur(status.total_preventivo)} <span className="text-slate-400">(imponibile)</span></span>
                                    <span className="font-semibold text-[#0055FF]">{status.percentage_invoiced}%</span>
                                </div>
                                <div className="w-full bg-slate-200 rounded-full h-2">
                                    <div
                                        className="bg-[#0055FF] h-2 rounded-full transition-all"
                                        style={{ width: `${Math.min(status.percentage_invoiced, 100)}%` }}
                                        data-testid="progress-bar"
                                    />
                                </div>
                                <div className="flex justify-between text-xs">
                                    <span className="text-slate-400">Residuo: <span className="font-semibold text-[#1E293B]">{fmtEur(status.remaining)}</span></span>
                                </div>
                                {/* Previous invoices */}
                                {status.linked_invoices?.length > 0 && (
                                    <div className="mt-2 space-y-1">
                                        {status.linked_invoices.map((inv, i) => (
                                            <div key={i} className="flex items-center justify-between text-xs bg-white rounded px-2 py-1 border border-slate-100">
                                                <span className="font-mono text-[#0055FF]">{inv.document_number}</span>
                                                <Badge className="text-[9px] bg-slate-100 text-slate-600">{(inv.progressive_type || inv.type) === 'acconto' ? 'Acconto' : (inv.progressive_type || inv.type) === 'sal' ? 'SAL' : 'Saldo'}</Badge>
                                                <span className="font-mono font-medium">{fmtEur(inv.progressive_amount || inv.amount)}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {status?.is_fully_invoiced ? (
                            <div className="text-center py-6 space-y-2" data-testid="fully-invoiced">
                                <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
                                <p className="text-sm font-semibold text-emerald-700">Preventivo completamente fatturato</p>
                            </div>
                        ) : (
                            <>
                                {/* Mode selector */}
                                {!mode ? (
                                    <div className="grid grid-cols-3 gap-2" data-testid="mode-selector">
                                        {MODES.map(m => (
                                            <button
                                                key={m.key}
                                                onClick={() => setMode(m.key)}
                                                data-testid={`mode-${m.key}`}
                                                className="flex flex-col items-center gap-2 p-4 rounded-lg border-2 border-slate-200 hover:border-[#0055FF] hover:bg-blue-50 transition-all text-center"
                                            >
                                                <div className={`w-10 h-10 rounded-full ${m.color} flex items-center justify-center`}>
                                                    <m.icon className="h-5 w-5 text-white" />
                                                </div>
                                                <span className="text-sm font-semibold text-[#1E293B]">{m.label}</span>
                                                <span className="text-[10px] text-slate-400 leading-tight">{m.desc}</span>
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {/* Back button */}
                                        <button
                                            onClick={() => setMode(null)}
                                            className="text-xs text-[#0055FF] hover:underline flex items-center gap-1"
                                            data-testid="btn-back-mode"
                                        >
                                            ← Cambia tipo
                                        </button>

                                        {/* Mode-specific content */}
                                        {mode === 'acconto' && (
                                            <div className="space-y-3" data-testid="acconto-form">
                                                <div>
                                                    <Label className="text-sm font-medium">Percentuale Acconto</Label>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <Input
                                                            type="number"
                                                            min="1"
                                                            max="100"
                                                            step="5"
                                                            value={percentage}
                                                            onChange={e => setPercentage(e.target.value)}
                                                            className="w-24 h-9 font-mono text-right"
                                                            data-testid="input-percentage"
                                                        />
                                                        <span className="text-sm text-slate-500">%</span>
                                                        <span className="text-xs text-slate-400 ml-auto">
                                                            di {fmtEur(totalPrev)} (imponibile)
                                                        </span>
                                                    </div>
                                                    {/* Quick buttons */}
                                                    <div className="flex gap-1.5 mt-2">
                                                        {[20, 30, 40, 50].map(p => (
                                                            <button
                                                                key={p}
                                                                onClick={() => setPercentage(p)}
                                                                className={`px-3 py-1 rounded text-xs font-mono border transition-colors ${parseFloat(percentage) === p ? 'bg-[#0055FF] text-white border-[#0055FF]' : 'bg-white text-slate-600 border-slate-200 hover:border-[#0055FF]'}`}
                                                                data-testid={`quick-pct-${p}`}
                                                            >
                                                                {p}%
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {mode === 'sal' && (
                                            <div className="space-y-3" data-testid="sal-form">
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => setSalMode('lines')}
                                                        className={`flex-1 py-2 text-xs font-medium rounded border transition-colors ${salMode === 'lines' ? 'bg-[#0055FF] text-white border-[#0055FF]' : 'bg-white text-slate-600 border-slate-200'}`}
                                                        data-testid="sal-mode-lines"
                                                    >
                                                        Seleziona Righe
                                                    </button>
                                                    <button
                                                        onClick={() => setSalMode('amount')}
                                                        className={`flex-1 py-2 text-xs font-medium rounded border transition-colors ${salMode === 'amount' ? 'bg-[#0055FF] text-white border-[#0055FF]' : 'bg-white text-slate-600 border-slate-200'}`}
                                                        data-testid="sal-mode-amount"
                                                    >
                                                        Importo Libero
                                                    </button>
                                                </div>
                                                {salMode === 'lines' ? (
                                                    <div className="space-y-1 max-h-48 overflow-y-auto border rounded-lg p-2" data-testid="sal-lines-list">
                                                        {lines.map((ln, idx) => {
                                                            const sel = selectedLines.includes(idx);
                                                            return (
                                                                <button
                                                                    key={idx}
                                                                    onClick={() => toggleLine(idx)}
                                                                    className={`w-full flex items-center gap-2 p-2 rounded text-left transition-colors ${sel ? 'bg-blue-50 border-[#0055FF] border' : 'bg-white border border-slate-100 hover:bg-slate-50'}`}
                                                                    data-testid={`sal-line-${idx}`}
                                                                >
                                                                    <div className={`w-4 h-4 rounded border flex items-center justify-center ${sel ? 'bg-[#0055FF] border-[#0055FF]' : 'border-slate-300'}`}>
                                                                        {sel && <CheckCircle2 className="h-3 w-3 text-white" />}
                                                                    </div>
                                                                    <span className="text-xs text-slate-700 truncate flex-1">{ln.description || `Riga ${idx + 1}`}</span>
                                                                    <span className="text-xs font-mono font-semibold text-[#0055FF]">{fmtEur(ln.line_total)}</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                ) : (
                                                    <div>
                                                        <Label className="text-sm">Importo SAL</Label>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <Input
                                                                type="number"
                                                                min="0.01"
                                                                step="100"
                                                                value={customAmount}
                                                                onChange={e => setCustomAmount(e.target.value)}
                                                                placeholder="Es. 5000"
                                                                className="h-9 font-mono"
                                                                data-testid="input-sal-amount"
                                                            />
                                                            <span className="text-xs text-slate-400">max {fmtEur(remaining)}</span>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {mode === 'saldo' && (
                                            <div className="space-y-3" data-testid="saldo-form">
                                                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm text-emerald-800">
                                                    <p className="font-medium flex items-center gap-1.5">
                                                        <CheckCircle2 className="h-4 w-4" />
                                                        Fattura a saldo
                                                    </p>
                                                    <p className="text-xs mt-1 text-emerald-600">
                                                        Verranno incluse tutte le righe del preventivo con detrazione automatica degli acconti precedenti.
                                                    </p>
                                                </div>
                                                {status?.linked_invoices?.length > 0 && (
                                                    <div className="text-xs text-slate-500 space-y-1">
                                                        <p className="font-medium text-slate-600">Detrazioni automatiche:</p>
                                                        {status.linked_invoices.map((inv, i) => (
                                                            <div key={i} className="flex justify-between pl-3">
                                                                <span>- Ft. {inv.document_number}</span>
                                                                <span className="font-mono text-red-500">-{fmtEur(inv.progressive_amount || inv.amount)}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Preview */}
                                        <Separator />
                                        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg" data-testid="invoice-preview">
                                            <div className="text-xs text-slate-500">
                                                <FileText className="h-3.5 w-3.5 inline mr-1" />
                                                Importo fattura:
                                            </div>
                                            <span className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(previewAmount)}</span>
                                        </div>
                                        {previewAmount > remaining + 0.01 && (
                                            <div className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 p-2 rounded" data-testid="amount-warning">
                                                <AlertTriangle className="h-3.5 w-3.5" />
                                                Importo supera il residuo di {fmtEur(remaining)}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Annulla</Button>
                    {mode && !status?.is_fully_invoiced && (
                        <Button
                            onClick={handleCreate}
                            disabled={creating || !isValid}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                            data-testid="btn-create-invoice"
                        >
                            {creating ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <ArrowRightLeft className="h-4 w-4 mr-1.5" />}
                            {creating ? 'Creazione...' : 'Crea Fattura'}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
