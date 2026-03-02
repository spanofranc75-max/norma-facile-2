/**
 * CostControlPage — Purchase Invoice Processing & Cost Assignment.
 * Two-column layout: Inbox (pending invoices) | Detail & Assignment form.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import {
    Receipt, FileInput, ArrowRight, Loader2, CheckCircle2,
    Warehouse, Briefcase, Tag, Truck, Wrench, Search,
    CircleDollarSign, TrendingUp, Building2, Package,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);
const fmtDate = (d) => { if (!d) return '—'; const p = d.split('-'); return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d; };

const CATEGORY_OPTIONS = [
    { value: 'materiali', label: 'Materiale Ferroso', icon: Package },
    { value: 'lavorazioni_esterne', label: 'Lavorazione Esterna', icon: Wrench },
    { value: 'consumabili', label: 'Consumabili', icon: Tag },
    { value: 'trasporti', label: 'Trasporti', icon: Truck },
];

export default function CostControlPage() {
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);
    const [assigning, setAssigning] = useState(false);

    // Assignment form
    const [targetType, setTargetType] = useState('commessa');
    const [targetId, setTargetId] = useState('');
    const [category, setCategory] = useState('materiali');
    const [selectedRows, setSelectedRows] = useState([]);
    const [note, setNote] = useState('');

    // Commesse search
    const [commesseList, setCommesseList] = useState([]);
    const [commessaQuery, setCommessaQuery] = useState('');
    const [searchingCommesse, setSearchingCommesse] = useState(false);

    // Processed entries
    const [processed, setProcessed] = useState([]);
    const [showProcessed, setShowProcessed] = useState(false);

    const fetchInvoices = useCallback(async () => {
        try {
            const data = await apiRequest('/costs/invoices/pending');
            setInvoices(data.invoices || []);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, []);

    const fetchProcessed = useCallback(async () => {
        try {
            const data = await apiRequest('/costs/invoices/processed');
            setProcessed(data.entries || []);
        } catch { /* silent */ }
    }, []);

    useEffect(() => { fetchInvoices(); fetchProcessed(); }, [fetchInvoices, fetchProcessed]);

    const searchCommesse = useCallback(async (q) => {
        setSearchingCommesse(true);
        try {
            const data = await apiRequest(`/costs/commesse-search?q=${encodeURIComponent(q)}`);
            setCommesseList(data.commesse || []);
        } catch { /* silent */ }
        finally { setSearchingCommesse(false); }
    }, []);

    useEffect(() => {
        const t = setTimeout(() => searchCommesse(commessaQuery), 300);
        return () => clearTimeout(t);
    }, [commessaQuery, searchCommesse]);

    const handleSelect = (inv) => {
        setSelected(inv);
        setSelectedRows(inv.linee.map((_, i) => i)); // select all by default
        setTargetType('commessa');
        setTargetId('');
        setCategory('materiali');
        setNote('');
    };

    const toggleRow = (idx) => {
        setSelectedRows(prev =>
            prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
        );
    };

    const selectedAmount = selected
        ? selected.linee.filter((_, i) => selectedRows.includes(i)).reduce((s, l) => s + Math.abs(l.importo || 0), 0)
        : 0;

    const handleAssign = async () => {
        if (!selected) return;
        if (targetType === 'commessa' && !targetId) {
            toast.error('Seleziona una commessa');
            return;
        }
        setAssigning(true);
        try {
            const res = await apiRequest(`/costs/invoices/${selected.invoice_id}/assign`, {
                method: 'POST',
                body: {
                    target_type: targetType,
                    target_id: targetType === 'commessa' ? targetId : null,
                    category,
                    righe_selezionate: selectedRows.length < selected.linee.length ? selectedRows : null,
                    amount: selectedAmount,
                    note,
                },
            });
            toast.success(res.message);
            setSelected(null);
            fetchInvoices();
            fetchProcessed();
        } catch (e) { toast.error(e.message); }
        finally { setAssigning(false); }
    };

    // KPIs
    const totalePending = invoices.reduce((s, inv) => s + (inv.totale || 0), 0);
    const totaleProcessed = processed.reduce((s, e) => s + (e.importo || 0), 0);

    return (
        <DashboardLayout>
            <div className="max-w-7xl mx-auto space-y-4" data-testid="cost-control-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-[#1E293B]" data-testid="page-title">Controllo Costi</h1>
                        <p className="text-xs text-slate-500 mt-0.5">Imputa le fatture passive alle commesse o alle spese generali</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="text-right">
                            <p className="text-[10px] text-slate-400 uppercase tracking-wider">Da processare</p>
                            <p className="text-lg font-bold text-amber-600" data-testid="kpi-pending">{fmtEur(totalePending)}</p>
                        </div>
                        <Separator orientation="vertical" className="h-10" />
                        <div className="text-right">
                            <p className="text-[10px] text-slate-400 uppercase tracking-wider">Imputati</p>
                            <p className="text-lg font-bold text-emerald-600" data-testid="kpi-processed">{fmtEur(totaleProcessed)}</p>
                        </div>
                    </div>
                </div>

                {/* 2-Column Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                    {/* Left: Invoice Inbox */}
                    <div className="lg:col-span-2 space-y-3">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-semibold text-[#1E293B] flex items-center gap-1.5">
                                <FileInput className="h-4 w-4 text-[#0055FF]" />
                                Fatture da Processare ({invoices.length})
                            </h2>
                            <Button variant="ghost" size="sm" className="text-[10px] h-7" onClick={() => setShowProcessed(!showProcessed)} data-testid="toggle-processed">
                                {showProcessed ? 'Mostra Pendenti' : `Storico (${processed.length})`}
                            </Button>
                        </div>

                        {loading ? (
                            <div className="flex items-center justify-center py-12 text-slate-400">
                                <Loader2 className="h-5 w-5 animate-spin mr-2" /> Caricamento...
                            </div>
                        ) : !showProcessed ? (
                            invoices.length === 0 ? (
                                <Card className="border-dashed"><CardContent className="py-8 text-center text-xs text-slate-400">
                                    <Receipt className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                    Nessuna fattura da processare
                                </CardContent></Card>
                            ) : (
                                <div className="space-y-2">
                                    {invoices.map(inv => (
                                        <InvoiceCard
                                            key={inv.invoice_id}
                                            invoice={inv}
                                            isSelected={selected?.invoice_id === inv.invoice_id}
                                            onClick={() => handleSelect(inv)}
                                        />
                                    ))}
                                </div>
                            )
                        ) : (
                            processed.length === 0 ? (
                                <Card className="border-dashed"><CardContent className="py-8 text-center text-xs text-slate-400">
                                    Nessun costo ancora imputato
                                </CardContent></Card>
                            ) : (
                                <div className="space-y-2">
                                    {processed.map(entry => (
                                        <Card key={entry.cost_id} className="border-slate-200 bg-emerald-50/30" data-testid={`processed-${entry.cost_id}`}>
                                            <CardContent className="p-3">
                                                <div className="flex items-start justify-between">
                                                    <div>
                                                        <p className="text-xs font-semibold text-slate-700">{entry.fornitore}</p>
                                                        <p className="text-[10px] text-slate-400">Fatt. {entry.source_invoice_numero}</p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-sm font-bold text-emerald-700">{fmtEur(entry.importo)}</p>
                                                        <Badge className="text-[9px] bg-emerald-100 text-emerald-700">{entry.target_name || entry.target_type}</Badge>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            )
                        )}
                    </div>

                    {/* Right: Assignment Detail */}
                    <div className="lg:col-span-3">
                        {!selected ? (
                            <Card className="border-dashed h-full min-h-[400px]">
                                <CardContent className="h-full flex flex-col items-center justify-center text-slate-400">
                                    <ArrowRight className="h-8 w-8 mb-3 text-slate-300" />
                                    <p className="text-sm font-medium">Seleziona una fattura a sinistra</p>
                                    <p className="text-xs mt-1">per iniziare l'imputazione dei costi</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card className="border-[#0055FF]/30" data-testid="assignment-panel">
                                <CardHeader className="bg-[#1E293B] rounded-t-lg py-3 px-4">
                                    <CardTitle className="text-sm font-semibold text-white flex items-center justify-between">
                                        <span className="flex items-center gap-2">
                                            <Receipt className="h-4 w-4" />
                                            {selected.fornitore} — {selected.numero}
                                        </span>
                                        <span className="text-base font-bold text-amber-300">{fmtEur(selected.totale)}</span>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="p-4 space-y-4">
                                    {/* Invoice date */}
                                    <div className="flex items-center gap-4 text-xs text-slate-500">
                                        <span>Data: <strong>{fmtDate(selected.data)}</strong></span>
                                        {selected.is_mock && <Badge className="text-[9px] bg-amber-100 text-amber-700 border-amber-200">DATI SIMULATI</Badge>}
                                    </div>

                                    {/* Line items with checkboxes */}
                                    <div>
                                        <Label className="text-xs font-semibold text-slate-600 mb-2 block">Seleziona Righe da Imputare</Label>
                                        <div className="border rounded-lg overflow-hidden">
                                            <div className="bg-slate-50 px-3 py-1.5 flex items-center text-[10px] font-semibold text-slate-500 uppercase tracking-wider border-b">
                                                <span className="w-6" />
                                                <span className="flex-1">Descrizione</span>
                                                <span className="w-16 text-right">Qta</span>
                                                <span className="w-20 text-right">Prezzo</span>
                                                <span className="w-20 text-right">Importo</span>
                                            </div>
                                            {selected.linee.map((line, i) => (
                                                <div
                                                    key={i}
                                                    className={`flex items-center px-3 py-2 text-xs border-b last:border-b-0 cursor-pointer transition-colors ${
                                                        selectedRows.includes(i) ? 'bg-blue-50' : 'hover:bg-slate-50'
                                                    }`}
                                                    onClick={() => toggleRow(i)}
                                                    data-testid={`invoice-line-${i}`}
                                                >
                                                    <Checkbox checked={selectedRows.includes(i)} className="mr-2 h-3.5 w-3.5" />
                                                    <span className="flex-1 truncate">{line.descrizione}</span>
                                                    <span className="w-16 text-right text-slate-400">{line.quantita} {line.unita || ''}</span>
                                                    <span className="w-20 text-right text-slate-400">{fmtEur(line.prezzo_unitario)}</span>
                                                    <span className="w-20 text-right font-medium">{fmtEur(line.importo)}</span>
                                                </div>
                                            ))}
                                        </div>
                                        <p className="text-right text-xs mt-1.5 text-slate-500">
                                            Selezionati: <strong className="text-[#0055FF]">{fmtEur(selectedAmount)}</strong>
                                        </p>
                                    </div>

                                    <Separator />

                                    {/* Destination */}
                                    <div className="grid grid-cols-3 gap-2">
                                        {[
                                            { value: 'commessa', label: 'Commessa', icon: Briefcase, desc: 'Costo diretto' },
                                            { value: 'magazzino', label: 'Magazzino', icon: Warehouse, desc: 'Scorta' },
                                            { value: 'generale', label: 'Spese Generali', icon: Building2, desc: 'Costo fisso' },
                                        ].map(opt => (
                                            <button
                                                key={opt.value}
                                                onClick={() => { setTargetType(opt.value); setTargetId(''); }}
                                                className={`p-3 rounded-lg border text-center transition-all ${
                                                    targetType === opt.value
                                                        ? 'border-[#0055FF] bg-blue-50 ring-1 ring-[#0055FF]'
                                                        : 'border-slate-200 hover:border-slate-300'
                                                }`}
                                                data-testid={`target-${opt.value}`}
                                            >
                                                <opt.icon className={`h-5 w-5 mx-auto mb-1 ${targetType === opt.value ? 'text-[#0055FF]' : 'text-slate-400'}`} />
                                                <p className={`text-xs font-semibold ${targetType === opt.value ? 'text-[#0055FF]' : 'text-slate-600'}`}>{opt.label}</p>
                                                <p className="text-[10px] text-slate-400">{opt.desc}</p>
                                            </button>
                                        ))}
                                    </div>

                                    {/* Commessa selector */}
                                    {targetType === 'commessa' && (
                                        <div>
                                            <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">Cerca Commessa</Label>
                                            <div className="relative">
                                                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                                                <Input
                                                    placeholder="Cerca per numero, titolo o cliente..."
                                                    value={commessaQuery}
                                                    onChange={e => setCommessaQuery(e.target.value)}
                                                    className="pl-8 h-9 text-xs"
                                                    data-testid="commessa-search"
                                                />
                                                {searchingCommesse && <Loader2 className="absolute right-2.5 top-2.5 h-3.5 w-3.5 animate-spin text-slate-400" />}
                                            </div>
                                            <div className="mt-2 max-h-36 overflow-y-auto border rounded-lg divide-y">
                                                {commesseList.length === 0 ? (
                                                    <p className="text-xs text-slate-400 text-center py-3">
                                                        {commessaQuery ? 'Nessun risultato' : 'Digita per cercare'}
                                                    </p>
                                                ) : commesseList.map(c => (
                                                    <button
                                                        key={c.commessa_id}
                                                        onClick={() => setTargetId(c.commessa_id)}
                                                        className={`w-full text-left px-3 py-2 transition-colors ${
                                                            targetId === c.commessa_id ? 'bg-blue-50' : 'hover:bg-slate-50'
                                                        }`}
                                                        data-testid={`commessa-opt-${c.commessa_id}`}
                                                    >
                                                        <div className="flex items-center justify-between">
                                                            <div>
                                                                <span className="text-xs font-mono font-bold text-[#0055FF]">{c.numero}</span>
                                                                <span className="text-xs text-slate-500 ml-2">{c.title}</span>
                                                            </div>
                                                            <span className="text-xs font-semibold text-slate-700">{fmtEur(c.value)}</span>
                                                        </div>
                                                        {c.client_name && <p className="text-[10px] text-slate-400">{c.client_name}</p>}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Category */}
                                    <div>
                                        <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">Categoria Costo</Label>
                                        <Select value={category} onValueChange={setCategory}>
                                            <SelectTrigger className="h-9 text-xs" data-testid="category-select">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {CATEGORY_OPTIONS.map(opt => (
                                                    <SelectItem key={opt.value} value={opt.value} className="text-xs">
                                                        {opt.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {/* Note */}
                                    <div>
                                        <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">Nota (opzionale)</Label>
                                        <Textarea
                                            value={note}
                                            onChange={e => setNote(e.target.value)}
                                            placeholder="Es. Materiale per tettoia cliente Rossi..."
                                            className="text-xs h-16"
                                            data-testid="cost-note"
                                        />
                                    </div>

                                    {/* Confirm button */}
                                    <Button
                                        onClick={handleAssign}
                                        disabled={assigning || selectedRows.length === 0}
                                        className="w-full bg-[#0055FF] text-white hover:bg-[#0044CC] h-11"
                                        data-testid="btn-assign-cost"
                                    >
                                        {assigning ? (
                                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                        ) : (
                                            <CircleDollarSign className="h-4 w-4 mr-2" />
                                        )}
                                        Assegna {fmtEur(selectedAmount)} a {
                                            targetType === 'commessa' ? `Commessa ${commesseList.find(c => c.commessa_id === targetId)?.numero || ''}` :
                                            targetType === 'magazzino' ? 'Magazzino' : 'Spese Generali'
                                        }
                                    </Button>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}

function InvoiceCard({ invoice, isSelected, onClick }) {
    return (
        <Card
            className={`cursor-pointer transition-all border ${
                isSelected
                    ? 'border-[#0055FF] ring-1 ring-[#0055FF] bg-blue-50/30'
                    : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'
            }`}
            onClick={onClick}
            data-testid={`invoice-card-${invoice.invoice_id}`}
        >
            <CardContent className="p-3">
                <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                            <p className="text-xs font-semibold text-[#1E293B] truncate">{invoice.fornitore}</p>
                            {invoice.is_mock && (
                                <Badge className="text-[8px] bg-amber-100 text-amber-600 border-amber-200 shrink-0">MOCK</Badge>
                            )}
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">Fatt. {invoice.numero} — {fmtDate(invoice.data)}</p>
                        <div className="mt-1.5 space-y-0.5">
                            {invoice.linee.slice(0, 2).map((l, i) => (
                                <p key={i} className="text-[10px] text-slate-500 truncate">{l.descrizione}</p>
                            ))}
                            {invoice.linee.length > 2 && (
                                <p className="text-[10px] text-slate-400">+{invoice.linee.length - 2} altre righe</p>
                            )}
                        </div>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                        <p className="text-sm font-bold text-[#1E293B]">{fmtEur(invoice.totale)}</p>
                        <p className="text-[10px] text-slate-400">Imp. {fmtEur(invoice.imponibile)}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
