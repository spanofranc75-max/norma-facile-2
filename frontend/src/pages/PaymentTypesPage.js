/**
 * Tipi Pagamento — Stile Invoicex con quote, simulazione scadenze e codice FE.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import { Plus, Pencil, Trash2, CreditCard, Wand2, Calculator, X } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const TIPO_OPTIONS = [
    { value: 'BON', label: 'Bonifico', color: 'bg-blue-100 text-blue-800' },
    { value: 'RIB', label: 'Ri.Ba', color: 'bg-amber-100 text-amber-800' },
    { value: 'CON', label: 'Contanti', color: 'bg-emerald-100 text-emerald-800' },
    { value: 'ELE', label: 'Elettronico', color: 'bg-violet-100 text-violet-800' },
];

const CODICE_FE_OPTIONS = [
    { value: '', label: '— Nessuno —' },
    { value: 'MP01', label: 'MP01 - Contanti' },
    { value: 'MP02', label: 'MP02 - Assegno' },
    { value: 'MP03', label: 'MP03 - Assegno circolare' },
    { value: 'MP05', label: 'MP05 - Bonifico' },
    { value: 'MP06', label: 'MP06 - Vaglia cambiario' },
    { value: 'MP08', label: 'MP08 - Carta di pagamento' },
    { value: 'MP09', label: 'MP09 - RID' },
    { value: 'MP10', label: 'MP10 - RID utenze' },
    { value: 'MP11', label: 'MP11 - RID veloce' },
    { value: 'MP12', label: 'MP12 - RIBA' },
    { value: 'MP13', label: 'MP13 - MAV' },
    { value: 'MP14', label: 'MP14 - Quietanza erario' },
    { value: 'MP16', label: 'MP16 - Domiciliazione bancaria' },
    { value: 'MP17', label: 'MP17 - Domiciliazione postale' },
    { value: 'MP18', label: 'MP18 - Bollettino c/c postale' },
    { value: 'MP19', label: 'MP19 - SEPA Direct Debit' },
    { value: 'MP20', label: 'MP20 - SEPA DD CORE' },
    { value: 'MP21', label: 'MP21 - SEPA DD B2B' },
    { value: 'MP22', label: 'MP22 - Trattenuta su somme' },
    { value: 'MP23', label: 'MP23 - PagoPA' },
];

const QUICK_DAYS = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360];
const QUICK_LABELS = { 0: 'Imm.', 30: '30', 60: '60', 90: '90', 120: '120', 150: '150', 180: '180', 210: '210', 240: '240', 270: '270', 300: '300', 330: '330', 360: '360' };

const emptyForm = {
    codice: '', tipo: 'BON', descrizione: '', codice_fe: '',
    quote: [], divisione_automatica: true,
    immediato: false, gg_30: false, gg_60: false, gg_90: false,
    gg_120: false, gg_150: false, gg_180: false, gg_210: false,
    gg_240: false, gg_270: false, gg_300: false, gg_330: false,
    gg_360: false,
    fine_mese: false, richiedi_giorno_scadenza: false, giorno_scadenza: null,
    iva_30gg: false,
    note_documento: '', spese_incasso: 0, banca_necessaria: false,
};

function formatDateIT(d) {
    if (!d) return '';
    const parts = d.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return d;
}

function fmtEur(v) {
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);
}

export default function PaymentTypesPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyForm);
    const [customDays, setCustomDays] = useState('');
    const [simResult, setSimResult] = useState(null);
    const [simDate, setSimDate] = useState(new Date().toISOString().slice(0, 10));
    const [simImporto, setSimImporto] = useState(10000);

    const fetchItems = useCallback(async () => {
        try {
            const data = await apiRequest('/payment-types/');
            setItems(data.items || []);
        } catch (e) {
            toast.error('Errore nel caricamento');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchItems(); }, [fetchItems]);

    const handleSeedDefaults = async () => {
        try {
            const res = await apiRequest('/payment-types/seed-defaults', { method: 'POST' });
            toast.success(res.message);
            fetchItems();
        } catch (e) { toast.error(e.message); }
    };

    const openCreate = () => {
        setForm(emptyForm);
        setEditing(null);
        setSimResult(null);
        setCustomDays('');
        setDialogOpen(true);
    };
    const openEdit = (item) => {
        setForm({ ...emptyForm, ...item });
        setEditing(item.payment_type_id);
        setSimResult(null);
        setCustomDays('');
        setDialogOpen(true);
    };

    const handleSave = async () => {
        if (!form.codice || !form.descrizione) {
            toast.error('Codice e Descrizione obbligatori');
            return;
        }
        if (form.quote.length === 0) {
            toast.error('Aggiungi almeno una scadenza');
            return;
        }
        try {
            if (editing) {
                await apiRequest(`/payment-types/${editing}`, { method: 'PUT', body: form });
                toast.success('Tipo pagamento aggiornato');
            } else {
                await apiRequest('/payment-types/', { method: 'POST', body: form });
                toast.success('Tipo pagamento creato');
            }
            setDialogOpen(false);
            fetchItems();
        } catch (e) { toast.error(e.message); }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Eliminare questo tipo pagamento?')) return;
        try {
            await apiRequest(`/payment-types/${id}`, { method: 'DELETE' });
            toast.success('Eliminato');
            fetchItems();
        } catch (e) { toast.error(e.message); }
    };

    const setField = (key, val) => setForm(f => ({ ...f, [key]: val }));
    const getTipoBadge = (tipo) => TIPO_OPTIONS.find(t => t.value === tipo) || TIPO_OPTIONS[0];

    // Toggle a quick-day checkbox and update quote list
    const toggleDay = (days) => {
        setForm(f => {
            const exists = f.quote.some(q => q.giorni === days);
            let newQuote;
            if (exists) {
                newQuote = f.quote.filter(q => q.giorni !== days);
            } else {
                newQuote = [...f.quote, { giorni: days, quota: 0 }].sort((a, b) => a.giorni - b.giorni);
            }
            // Auto-distribute if divisione_automatica
            if (f.divisione_automatica && newQuote.length > 0) {
                const share = Math.round(10000 / newQuote.length) / 100;
                const remainder = Math.round((100 - share * newQuote.length) * 100) / 100;
                newQuote = newQuote.map((q, i) => ({
                    ...q,
                    quota: i === newQuote.length - 1 ? share + remainder : share,
                }));
            }
            // Sync legacy flags
            const legacyUpdate = {};
            legacyUpdate.immediato = newQuote.some(q => q.giorni === 0);
            for (const d of [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360]) {
                legacyUpdate[`gg_${d}`] = newQuote.some(q => q.giorni === d);
            }
            return { ...f, ...legacyUpdate, quote: newQuote };
        });
        setSimResult(null);
    };

    // Add custom day period
    const addCustomDay = () => {
        const days = parseInt(customDays);
        if (!days || days < 1 || days > 999) {
            toast.error('Inserisci un numero di giorni valido (1-999)');
            return;
        }
        if (form.quote.some(q => q.giorni === days)) {
            toast.error(`Scadenza a ${days} gg già presente`);
            return;
        }
        setForm(f => {
            let newQuote = [...f.quote, { giorni: days, quota: 0 }].sort((a, b) => a.giorni - b.giorni);
            if (f.divisione_automatica && newQuote.length > 0) {
                const share = Math.round(10000 / newQuote.length) / 100;
                const remainder = Math.round((100 - share * newQuote.length) * 100) / 100;
                newQuote = newQuote.map((q, i) => ({
                    ...q,
                    quota: i === newQuote.length - 1 ? share + remainder : share,
                }));
            }
            return { ...f, quote: newQuote };
        });
        setCustomDays('');
        setSimResult(null);
    };

    // Remove quota from table
    const removeQuota = (giorni) => {
        setForm(f => {
            let newQuote = f.quote.filter(q => q.giorni !== giorni);
            if (f.divisione_automatica && newQuote.length > 0) {
                const share = Math.round(10000 / newQuote.length) / 100;
                const remainder = Math.round((100 - share * newQuote.length) * 100) / 100;
                newQuote = newQuote.map((q, i) => ({
                    ...q,
                    quota: i === newQuote.length - 1 ? share + remainder : share,
                }));
            }
            // Sync legacy flags
            const legacyUpdate = {};
            legacyUpdate.immediato = newQuote.some(q => q.giorni === 0);
            for (const d of [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360]) {
                legacyUpdate[`gg_${d}`] = newQuote.some(q => q.giorni === d);
            }
            return { ...f, ...legacyUpdate, quote: newQuote };
        });
        setSimResult(null);
    };

    // Update individual quota percentage
    const updateQuota = (giorni, newQuotaVal) => {
        setForm(f => ({
            ...f,
            quote: f.quote.map(q => q.giorni === giorni ? { ...q, quota: parseFloat(newQuotaVal) || 0 } : q),
            divisione_automatica: false,
        }));
        setSimResult(null);
    };

    // Toggle auto-distribution
    const toggleAutoDistribution = (val) => {
        setForm(f => {
            const newForm = { ...f, divisione_automatica: val };
            if (val && f.quote.length > 0) {
                const share = Math.round(10000 / f.quote.length) / 100;
                const remainder = Math.round((100 - share * f.quote.length) * 100) / 100;
                newForm.quote = f.quote.map((q, i) => ({
                    ...q,
                    quota: i === f.quote.length - 1 ? share + remainder : share,
                }));
            }
            return newForm;
        });
    };

    // Simulate deadlines — client-side calculation (no save needed)
    const handleSimulate = () => {
        if (form.quote.length === 0) {
            toast.error('Aggiungi almeno una scadenza');
            return;
        }
        const invoiceDate = new Date(simDate);
        if (isNaN(invoiceDate.getTime())) {
            toast.error('Data fattura non valida');
            return;
        }
        const importo = parseFloat(simImporto) || 10000;
        const scadenze = form.quote.map((q, i) => {
            const target = new Date(invoiceDate);
            target.setDate(target.getDate() + q.giorni);
            if (form.fine_mese) {
                target.setMonth(target.getMonth() + 1, 0); // last day of month
            }
            if (form.richiedi_giorno_scadenza && form.giorno_scadenza) {
                const gs = Math.min(form.giorno_scadenza, new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate());
                target.setDate(gs);
            }
            const imp = Math.round(importo * q.quota / 100 * 100) / 100;
            return {
                rata: i + 1,
                giorni: q.giorni,
                data_scadenza: target.toISOString().slice(0, 10),
                quota_pct: q.quota,
                importo: imp,
            };
        });
        setSimResult({
            scadenze,
            totale_rate: scadenze.length,
            importo_totale: scadenze.reduce((s, r) => s + r.importo, 0),
        });
    };

    const totalQuota = form.quote.reduce((s, q) => s + (q.quota || 0), 0);

    // Summary text for table
    const getScadenzeSummary = (item) => {
        if (!item.quote || item.quote.length === 0) return '—';
        return item.quote.map(q => `${q.giorni === 0 ? 'Imm.' : q.giorni + 'gg'}`).join(' / ');
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="payment-types-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <CreditCard className="h-6 w-6 text-[#0055FF]" /> Tipi Pagamento
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Gestisci le condizioni di pagamento personalizzate</p>
                    </div>
                    <div className="flex gap-2">
                        {items.length === 0 && (
                            <Button data-testid="btn-seed" variant="outline" onClick={handleSeedDefaults} className="h-10 border-amber-400 text-amber-600 hover:bg-amber-50">
                                <Wand2 className="h-4 w-4 mr-2" /> Carica Predefiniti
                            </Button>
                        )}
                        <Button data-testid="btn-new-pt" onClick={openCreate} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white">
                            <Plus className="h-4 w-4 mr-2" /> Nuovo Tipo
                        </Button>
                    </div>
                </div>

                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                            </div>
                        ) : items.length === 0 ? (
                            <EmptyState type="invoices" title="Nessun tipo pagamento" description="Crea i tuoi tipi pagamento o carica quelli predefiniti." actionLabel="Crea il primo Tipo" onAction={openCreate} />
                        ) : (
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-[#1E293B]">
                                            <TableHead className="text-white font-medium">Codice</TableHead>
                                            <TableHead className="text-white font-medium">Tipo</TableHead>
                                            <TableHead className="text-white font-medium">Descrizione</TableHead>
                                            <TableHead className="text-white font-medium">Cod. FE</TableHead>
                                            <TableHead className="text-white font-medium">Scadenze</TableHead>
                                            <TableHead className="text-white font-medium text-center">FM</TableHead>
                                            <TableHead className="text-white font-medium text-center">Rate</TableHead>
                                            <TableHead className="w-[80px]"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {items.map((item) => {
                                            const badge = getTipoBadge(item.tipo);
                                            return (
                                                <TableRow key={item.payment_type_id} data-testid={`pt-row-${item.payment_type_id}`} className="hover:bg-slate-50">
                                                    <TableCell className="font-mono font-semibold text-sm">{item.codice}</TableCell>
                                                    <TableCell><Badge className={`${badge.color} text-[10px]`}>{badge.label}</Badge></TableCell>
                                                    <TableCell className="text-sm max-w-[250px] truncate">{item.descrizione}</TableCell>
                                                    <TableCell className="font-mono text-xs text-slate-500">{item.codice_fe || '—'}</TableCell>
                                                    <TableCell className="text-xs font-mono">{getScadenzeSummary(item)}</TableCell>
                                                    <TableCell className="text-center">
                                                        {item.fine_mese ? <div className="w-4 h-4 rounded-sm bg-[#0055FF] mx-auto" /> : <div className="w-4 h-4 rounded-sm border border-slate-300 mx-auto" />}
                                                    </TableCell>
                                                    <TableCell className="text-center font-mono text-xs">{item.quote?.length || 0}</TableCell>
                                                    <TableCell>
                                                        <div className="flex gap-1">
                                                            <Button variant="ghost" size="sm" onClick={() => openEdit(item)} data-testid={`edit-pt-${item.payment_type_id}`}><Pencil className="h-3.5 w-3.5" /></Button>
                                                            <Button variant="ghost" size="sm" onClick={() => handleDelete(item.payment_type_id)} className="text-red-500 hover:text-red-700" data-testid={`del-pt-${item.payment_type_id}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Create/Edit Dialog — Invoicex Style */}
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto" data-testid="pt-dialog">
                        <DialogHeader>
                            <DialogTitle className="text-[#1E293B] flex items-center gap-2">
                                <CreditCard className="h-5 w-5 text-[#0055FF]" />
                                {editing ? 'Modifica Tipo Pagamento' : 'Nuovo Tipo Pagamento'}
                            </DialogTitle>
                            <DialogDescription>Configura codice, tipo, scadenze e quote per questa condizione di pagamento.</DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4">
                            {/* Row 1: Codice + Tipo + Codice FE */}
                            <div className="grid grid-cols-3 gap-3">
                                <div>
                                    <Label className="text-xs">Codice *</Label>
                                    <Input data-testid="pt-codice" value={form.codice} onChange={e => setField('codice', e.target.value.toUpperCase())} placeholder="BB30" className="font-mono h-9 text-sm" />
                                </div>
                                <div>
                                    <Label className="text-xs">Tipo</Label>
                                    <Select value={form.tipo} onValueChange={v => setField('tipo', v)}>
                                        <SelectTrigger data-testid="pt-tipo" className="h-9"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {TIPO_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Codice FE (SDI)</Label>
                                    <Select value={form.codice_fe || '__none__'} onValueChange={v => setField('codice_fe', v === '__none__' ? '' : v)}>
                                        <SelectTrigger data-testid="pt-codice-fe" className="h-9 text-xs"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {CODICE_FE_OPTIONS.map(o => <SelectItem key={o.value || '__none__'} value={o.value || '__none__'}>{o.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {/* Descrizione */}
                            <div>
                                <Label className="text-xs">Descrizione *</Label>
                                <Input data-testid="pt-descrizione" value={form.descrizione} onChange={e => setField('descrizione', e.target.value)} placeholder="Bonifico Bancario 60 gg FM + 20" className="h-9 text-sm" />
                            </div>

                            {/* Spese + Banca */}
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Label className="text-xs">Spese Incasso</Label>
                                    <Input type="number" step="0.01" value={form.spese_incasso} onChange={e => setField('spese_incasso', parseFloat(e.target.value) || 0)} className="font-mono h-9 text-sm" />
                                </div>
                                <div className="flex items-end pb-1">
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <Checkbox checked={form.banca_necessaria} onCheckedChange={v => setField('banca_necessaria', v)} />
                                        <span className="text-slate-700">Banca necessaria</span>
                                    </label>
                                </div>
                            </div>

                            <Separator />

                            {/* Scadenze Section */}
                            <div>
                                <Label className="text-sm font-semibold text-[#1E293B]">Scadenze da Generare</Label>
                                <div className="grid grid-cols-[1fr_auto_auto] gap-4 mt-3">
                                    {/* Left: Quick checkboxes */}
                                    <div>
                                        <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wide">Selezione rapida</p>
                                        <div className="grid grid-cols-5 gap-1.5">
                                            {QUICK_DAYS.map(d => (
                                                <label key={d} className="flex items-center gap-1.5 cursor-pointer text-xs">
                                                    <Checkbox
                                                        data-testid={`pt-cb-${d}`}
                                                        checked={form.quote.some(q => q.giorni === d)}
                                                        onCheckedChange={() => toggleDay(d)}
                                                    />
                                                    <span className="text-slate-700">{d === 0 ? 'Imm.' : `${d}gg`}</span>
                                                </label>
                                            ))}
                                        </div>
                                        {/* Custom days input */}
                                        <div className="flex items-center gap-2 mt-2.5">
                                            <Input
                                                data-testid="pt-custom-days"
                                                type="number"
                                                min="1"
                                                max="999"
                                                value={customDays}
                                                onChange={e => setCustomDays(e.target.value)}
                                                placeholder="Giorni personalizzati"
                                                className="h-8 text-xs font-mono w-40"
                                                onKeyDown={e => e.key === 'Enter' && addCustomDay()}
                                            />
                                            <Button type="button" size="sm" variant="outline" onClick={addCustomDay} className="h-8 text-xs" data-testid="pt-add-custom">
                                                <Plus className="h-3 w-3 mr-1" /> Aggiungi
                                            </Button>
                                        </div>
                                    </div>

                                    {/* Center: Quote table */}
                                    <div className="min-w-[160px]">
                                        <div className="flex items-center gap-2 mb-2">
                                            <label className="flex items-center gap-1.5 cursor-pointer">
                                                <Checkbox
                                                    data-testid="pt-auto-div"
                                                    checked={form.divisione_automatica}
                                                    onCheckedChange={toggleAutoDistribution}
                                                />
                                                <span className="text-[10px] text-slate-600 uppercase tracking-wide">Div. automatica</span>
                                            </label>
                                        </div>
                                        <div className="border border-slate-200 rounded-md overflow-hidden">
                                            <div className="grid grid-cols-[1fr_60px_24px] bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600 uppercase">
                                                <span>Periodo</span>
                                                <span className="text-right">Quota</span>
                                                <span></span>
                                            </div>
                                            {form.quote.length === 0 ? (
                                                <div className="px-2 py-3 text-xs text-slate-400 text-center">Nessuna rata</div>
                                            ) : (
                                                form.quote.map(q => (
                                                    <div key={q.giorni} className="grid grid-cols-[1fr_60px_24px] items-center px-2 py-1 border-t border-slate-100 text-xs" data-testid={`quota-row-${q.giorni}`}>
                                                        <span className="font-mono text-slate-700">{q.giorni === 0 ? 'Immediato' : `${q.giorni}gg`}</span>
                                                        <Input
                                                            type="number"
                                                            step="0.01"
                                                            value={q.quota}
                                                            onChange={e => updateQuota(q.giorni, e.target.value)}
                                                            className="h-6 text-[11px] font-mono text-right px-1"
                                                            disabled={form.divisione_automatica}
                                                        />
                                                        <button onClick={() => removeQuota(q.giorni)} className="text-slate-400 hover:text-red-500 ml-1">
                                                            <X className="h-3 w-3" />
                                                        </button>
                                                    </div>
                                                ))
                                            )}
                                            {form.quote.length > 0 && (
                                                <div className="grid grid-cols-[1fr_60px_24px] items-center px-2 py-1 border-t border-slate-300 bg-slate-50 text-xs font-semibold">
                                                    <span className="text-slate-600">{form.quote.length} {form.quote.length === 1 ? 'rata' : 'rate'}</span>
                                                    <span className={`text-right font-mono ${Math.abs(totalQuota - 100) > 0.1 ? 'text-red-600' : 'text-emerald-600'}`}>{totalQuota.toFixed(1)}%</span>
                                                    <span></span>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Right: Options */}
                                    <div className="min-w-[120px]">
                                        <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wide">Opzioni</p>
                                        <div className="space-y-2">
                                            <label className="flex items-center gap-2 cursor-pointer text-xs">
                                                <Checkbox checked={form.fine_mese} onCheckedChange={v => { setField('fine_mese', v); setSimResult(null); }} data-testid="pt-fine-mese" />
                                                <span className="text-slate-700">Fine mese</span>
                                            </label>
                                            <label className="flex items-center gap-2 cursor-pointer text-xs">
                                                <Checkbox checked={form.richiedi_giorno_scadenza} onCheckedChange={v => { setField('richiedi_giorno_scadenza', v); setSimResult(null); }} data-testid="pt-richiedi-gs" />
                                                <span className="text-slate-700">Giorno scadenza</span>
                                            </label>
                                            {form.richiedi_giorno_scadenza && (
                                                <Input
                                                    data-testid="pt-giorno-scadenza"
                                                    type="number"
                                                    min="1"
                                                    max="31"
                                                    value={form.giorno_scadenza || ''}
                                                    onChange={e => { setField('giorno_scadenza', parseInt(e.target.value) || null); setSimResult(null); }}
                                                    placeholder="1-31"
                                                    className="h-7 text-xs font-mono w-16"
                                                />
                                            )}
                                            <label className="flex items-center gap-2 cursor-pointer text-xs">
                                                <Checkbox checked={form.iva_30gg} onCheckedChange={v => { setField('iva_30gg', v); setSimResult(null); }} data-testid="pt-iva-30gg" />
                                                <span className="text-slate-700">IVA a 30gg</span>
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <Separator />

                            {/* Simulazione Scadenze */}
                            <div>
                                <Label className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <Calculator className="h-4 w-4 text-[#0055FF]" /> Simulazione Scadenze
                                </Label>
                                <div className="flex items-end gap-3 mt-2">
                                    <div>
                                        <Label className="text-[10px] text-slate-500">Data Fattura</Label>
                                        <Input
                                            data-testid="pt-sim-date"
                                            type="date"
                                            value={simDate}
                                            onChange={e => { setSimDate(e.target.value); setSimResult(null); }}
                                            className="h-8 text-xs font-mono w-36"
                                        />
                                    </div>
                                    <div>
                                        <Label className="text-[10px] text-slate-500">Importo</Label>
                                        <Input
                                            data-testid="pt-sim-importo"
                                            type="number"
                                            value={simImporto}
                                            onChange={e => { setSimImporto(parseFloat(e.target.value) || 0); setSimResult(null); }}
                                            className="h-8 text-xs font-mono w-28"
                                        />
                                    </div>
                                    <Button type="button" size="sm" onClick={handleSimulate} className="h-8 text-xs bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="pt-simulate-btn">
                                        <Calculator className="h-3 w-3 mr-1" /> Calcola
                                    </Button>
                                </div>
                                {simResult && simResult.scadenze.length > 0 && (
                                    <div className="mt-2 border border-slate-200 rounded-md overflow-hidden" data-testid="pt-sim-results">
                                        <div className="grid grid-cols-4 bg-slate-100 px-3 py-1 text-[10px] font-semibold text-slate-600 uppercase">
                                            <span>Rata</span>
                                            <span>Scadenza</span>
                                            <span className="text-right">Quota</span>
                                            <span className="text-right">Importo</span>
                                        </div>
                                        {simResult.scadenze.map(s => (
                                            <div key={s.rata} className="grid grid-cols-4 items-center px-3 py-1.5 border-t border-slate-100 text-xs">
                                                <span className="font-mono text-slate-500">{s.rata}</span>
                                                <span className="font-semibold text-slate-700">{formatDateIT(s.data_scadenza)}</span>
                                                <span className="text-right font-mono text-slate-500">{s.quota_pct}%</span>
                                                <span className="text-right font-mono font-semibold text-[#0055FF]">{fmtEur(s.importo)}</span>
                                            </div>
                                        ))}
                                        <div className="grid grid-cols-4 items-center px-3 py-1.5 border-t border-slate-300 bg-slate-50 text-xs font-semibold">
                                            <span className="col-span-2">{simResult.totale_rate} {simResult.totale_rate === 1 ? 'rata' : 'rate'}</span>
                                            <span className="text-right font-mono">{simResult.scadenze.reduce((s, r) => s + r.quota_pct, 0).toFixed(1)}%</span>
                                            <span className="text-right font-mono text-[#0055FF]">{fmtEur(simResult.importo_totale)}</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Note */}
                            <div>
                                <Label className="text-xs">Note su Documento</Label>
                                <Input value={form.note_documento} onChange={e => setField('note_documento', e.target.value)} placeholder="Note da stampare in fattura" className="h-9 text-sm" />
                            </div>
                        </div>

                        <DialogFooter>
                            <Button variant="outline" onClick={() => setDialogOpen(false)}>Annulla</Button>
                            <Button data-testid="pt-save" onClick={handleSave} className="bg-[#0055FF] hover:bg-[#0044CC] text-white">
                                {editing ? 'Aggiorna' : 'Crea'}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </DashboardLayout>
    );
}
