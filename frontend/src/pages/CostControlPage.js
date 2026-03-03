/**
 * CostControlPage — Invoice Line Processing with Smart Matching & Margin Analysis.
 * Per-row allocation: each line → Magazzino (update PMP), Commessa, or Spese Generali.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import { toast } from 'sonner';
import {
    Receipt, Loader2, Warehouse, Briefcase, Building2, Package,
    Search, ChevronRight, BarChart3, AlertTriangle, CheckCircle2,
    RefreshCw, ArrowRight,
} from 'lucide-react';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);
const fmtDate = (d) => { if (!d) return ''; const p = d.split('-'); return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d; };

const DEST_OPTIONS = [
    { value: 'magazzino', label: 'Magazzino', icon: Warehouse, color: 'text-blue-600' },
    { value: 'commessa', label: 'Commessa', icon: Briefcase, color: 'text-amber-600' },
    { value: 'generale', label: 'Spese Generali', icon: Building2, color: 'text-slate-500' },
];

export default function CostControlPage() {
    const [tab, setTab] = useState('process'); // process | margins
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);
    const [matches, setMatches] = useState([]);
    const [matching, setMatching] = useState(false);
    const [rowAllocs, setRowAllocs] = useState({});
    const [commesseList, setCommesseList] = useState([]);
    const [assigning, setAssigning] = useState(false);
    const [margins, setMargins] = useState([]);

    const fetchInvoices = useCallback(async () => {
        try {
            const data = await apiRequest('/costs/invoices/pending');
            setInvoices(data.invoices || []);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, []);

    const fetchMargins = useCallback(async () => {
        try {
            const data = await apiRequest('/costs/margin-analysis');
            setMargins(data.commesse || []);
        } catch { /* silent */ }
    }, []);

    useEffect(() => { fetchInvoices(); fetchMargins(); }, [fetchInvoices, fetchMargins]);

    // Load commesse list on mount
    useEffect(() => {
        apiRequest('/costs/commesse-search?q=').then(d => setCommesseList(d.commesse || [])).catch(() => {});
    }, []);

    const handleSelectInvoice = async (inv) => {
        setSelected(inv);
        setMatching(true);
        // Initialize allocations to magazzino by default
        const defaultAllocs = {};
        inv.linee.forEach((_, i) => {
            defaultAllocs[i] = { target_type: 'magazzino', target_id: '', create_article: true };
        });
        setRowAllocs(defaultAllocs);

        // Smart match
        try {
            const data = await apiRequest(`/costs/invoices/${inv.invoice_id}/match-articles`, { method: 'POST' });
            setMatches(data.lines || []);
            // Update allocations with matched articles
            (data.lines || []).forEach((m) => {
                if (m.match) {
                    defaultAllocs[m.idx] = {
                        target_type: 'magazzino',
                        target_id: m.match.articolo_id,
                        create_article: false,
                    };
                }
            });
            setRowAllocs({ ...defaultAllocs });
        } catch {
            setMatches([]);
        } finally {
            setMatching(false);
        }
    };

    const updateAlloc = (idx, field, value) => {
        setRowAllocs(prev => ({
            ...prev,
            [idx]: { ...prev[idx], [field]: value },
        }));
    };

    const handleProcess = async () => {
        if (!selected) return;
        setAssigning(true);
        try {
            const rows = Object.entries(rowAllocs).map(([idx, alloc]) => ({
                idx: parseInt(idx),
                target_type: alloc.target_type,
                target_id: alloc.target_id || null,
                category: 'materiali',
                create_article: alloc.create_article || false,
            }));
            const res = await apiRequest(`/costs/invoices/${selected.invoice_id}/assign-rows`, {
                method: 'POST',
                body: { rows },
            });
            toast.success(res.message);
            setSelected(null);
            setMatches([]);
            fetchInvoices();
            fetchMargins();
        } catch (e) { toast.error(e.message); }
        finally { setAssigning(false); }
    };

    const pendingTotal = invoices.reduce((s, i) => s + (i.totale || 0), 0);

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="cost-control-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Controllo Costi</h1>
                        <p className="text-sm text-slate-500 mt-0.5">Importa righe fattura, aggiorna magazzino, analizza margini</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setTab('process')}
                            className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${tab === 'process' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                            data-testid="tab-process"
                        >
                            <Receipt className="h-3.5 w-3.5 inline mr-1" />
                            Processa ({invoices.length})
                        </button>
                        <button
                            onClick={() => setTab('margins')}
                            className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${tab === 'margins' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                            data-testid="tab-margins"
                        >
                            <BarChart3 className="h-3.5 w-3.5 inline mr-1" />
                            Analisi Margini ({margins.length})
                        </button>
                    </div>
                </div>

                {tab === 'process' ? (
                    <ProcessTab
                        invoices={invoices}
                        loading={loading}
                        selected={selected}
                        matches={matches}
                        matching={matching}
                        rowAllocs={rowAllocs}
                        commesseList={commesseList}
                        assigning={assigning}
                        pendingTotal={pendingTotal}
                        onSelect={handleSelectInvoice}
                        onUpdateAlloc={updateAlloc}
                        onProcess={handleProcess}
                    />
                ) : (
                    <MarginsTab margins={margins} onRefresh={fetchMargins} />
                )}
            </div>
        </DashboardLayout>
    );
}


function ProcessTab({ invoices, loading, selected, matches, matching, rowAllocs, commesseList, assigning, pendingTotal, onSelect, onUpdateAlloc, onProcess }) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            {/* Left: Invoice list */}
            <div className="lg:col-span-2 space-y-2">
                <div className="flex items-center justify-between mb-1">
                    <h2 className="text-sm font-semibold text-slate-700">Fatture da Processare</h2>
                    <span className="text-xs font-mono text-amber-600">{fmtEur(pendingTotal)}</span>
                </div>
                {loading ? (
                    <div className="flex items-center justify-center py-12 text-slate-400">
                        <Loader2 className="h-5 w-5 animate-spin mr-2" /> Caricamento...
                    </div>
                ) : invoices.length === 0 ? (
                    <Card className="border-dashed">
                        <CardContent className="py-10 text-center text-sm text-slate-400">
                            <CheckCircle2 className="h-10 w-10 mx-auto mb-2 text-emerald-300" />
                            Tutte le fatture sono state processate
                        </CardContent>
                    </Card>
                ) : (
                    invoices.map(inv => (
                        <div
                            key={inv.invoice_id}
                            onClick={() => onSelect(inv)}
                            data-testid={`invoice-${inv.invoice_id}`}
                            className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                selected?.invoice_id === inv.invoice_id
                                    ? 'border-slate-800 bg-slate-50 shadow-sm'
                                    : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-semibold text-slate-800 truncate">{inv.fornitore}</p>
                                <span className="text-sm font-bold font-mono text-slate-700">{fmtEur(inv.totale)}</span>
                            </div>
                            <div className="flex items-center justify-between mt-1">
                                <span className="text-xs text-slate-500">N. {inv.numero} — {fmtDate(inv.data)}</span>
                                <Badge variant="outline" className="text-[9px]">{inv.linee?.length || 0} righe</Badge>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Right: Line allocation */}
            <div className="lg:col-span-3">
                {!selected ? (
                    <Card className="border-dashed h-full">
                        <CardContent className="flex items-center justify-center py-20 text-sm text-slate-400">
                            <ArrowRight className="h-5 w-5 mr-2 text-slate-300" />
                            Seleziona una fattura per processare le righe
                        </CardContent>
                    </Card>
                ) : (
                    <Card className="border-slate-200">
                        <CardContent className="p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-bold text-slate-800">{selected.fornitore}</p>
                                    <p className="text-xs text-slate-500">Fatt. {selected.numero} del {fmtDate(selected.data)} — {fmtEur(selected.totale)}</p>
                                </div>
                                {matching && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
                            </div>

                            {/* Line allocation table */}
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="text-[10px] font-semibold">Descrizione Riga</TableHead>
                                            <TableHead className="text-[10px] font-semibold text-right w-[60px]">Q.tà</TableHead>
                                            <TableHead className="text-[10px] font-semibold text-right w-[80px]">Prezzo</TableHead>
                                            <TableHead className="text-[10px] font-semibold text-right w-[80px]">Importo</TableHead>
                                            <TableHead className="text-[10px] font-semibold w-[120px]">Destinazione</TableHead>
                                            <TableHead className="text-[10px] font-semibold w-[140px]">Dettaglio</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(selected.linee || []).map((line, i) => {
                                            const alloc = rowAllocs[i] || { target_type: 'generale' };
                                            const matchInfo = matches.find(m => m.idx === i);
                                            return (
                                                <TableRow key={i} className="group">
                                                    <TableCell className="text-xs max-w-[200px]">
                                                        <p className="truncate font-medium text-slate-700">{line.descrizione}</p>
                                                        {matchInfo?.match && (
                                                            <p className="text-[10px] text-blue-500 mt-0.5">
                                                                Trovato: {matchInfo.match.codice} (giacenza: {matchInfo.match.giacenza || 0})
                                                            </p>
                                                        )}
                                                        {matchInfo && !matchInfo.match && (
                                                            <p className="text-[10px] text-amber-500 mt-0.5">Nuovo articolo</p>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-xs text-right font-mono">{line.quantita}</TableCell>
                                                    <TableCell className="text-xs text-right font-mono">{fmtEur(line.prezzo_unitario)}</TableCell>
                                                    <TableCell className="text-xs text-right font-mono font-semibold">{fmtEur(line.importo)}</TableCell>
                                                    <TableCell>
                                                        <Select value={alloc.target_type} onValueChange={v => onUpdateAlloc(i, 'target_type', v)}>
                                                            <SelectTrigger className="h-7 text-[10px]" data-testid={`dest-${i}`}>
                                                                <SelectValue />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                {DEST_OPTIONS.map(o => (
                                                                    <SelectItem key={o.value} value={o.value}>
                                                                        <span className="text-xs">{o.label}</span>
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    </TableCell>
                                                    <TableCell>
                                                        {alloc.target_type === 'commessa' && (
                                                            <Select value={alloc.target_id || ''} onValueChange={v => onUpdateAlloc(i, 'target_id', v)}>
                                                                <SelectTrigger className="h-7 text-[10px]" data-testid={`commessa-${i}`}>
                                                                    <SelectValue placeholder="Seleziona..." />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    {commesseList.map(c => (
                                                                        <SelectItem key={c.commessa_id} value={c.commessa_id}>
                                                                            <span className="text-[10px]">{c.numero} — {c.title?.slice(0, 20)}</span>
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        )}
                                                        {alloc.target_type === 'magazzino' && matchInfo?.match && (
                                                            <span className="text-[10px] text-blue-600">{matchInfo.match.codice}</span>
                                                        )}
                                                        {alloc.target_type === 'magazzino' && !matchInfo?.match && (
                                                            <span className="text-[10px] text-amber-600">Nuovo art.</span>
                                                        )}
                                                        {alloc.target_type === 'generale' && (
                                                            <span className="text-[10px] text-slate-400">Spese gen.</span>
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </div>

                            {/* Process button */}
                            <div className="flex justify-end pt-2">
                                <Button
                                    onClick={onProcess}
                                    disabled={assigning}
                                    data-testid="btn-process-rows"
                                    className="bg-slate-800 text-white hover:bg-slate-700"
                                >
                                    {assigning ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <CheckCircle2 className="h-4 w-4 mr-1.5" />}
                                    {assigning ? 'Elaborazione...' : `Processa ${Object.keys(rowAllocs).length} righe`}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}


function MarginsTab({ margins, onRefresh }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-700">Preventivato vs Reale per Commessa</h2>
                <Button variant="ghost" size="sm" onClick={onRefresh} className="text-xs text-slate-500 h-7">
                    <RefreshCw className="h-3 w-3 mr-1" /> Aggiorna
                </Button>
            </div>

            {margins.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="py-12 text-center text-sm text-slate-400">
                        <BarChart3 className="h-10 w-10 mx-auto mb-2 text-slate-300" />
                        Nessuna commessa con costi imputati. Processa le fatture per vedere l'analisi.
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-3">
                    {margins.map(m => {
                        const costoTotale = m.costo_totale || (m.costi_materiali + m.costo_personale);
                        const alertColor = m.alert === 'rosso' ? 'border-l-red-500' :
                            m.alert === 'arancione' ? 'border-l-orange-500' :
                            m.alert === 'giallo' ? 'border-l-amber-400' : 'border-l-emerald-500';
                        return (
                        <Card key={m.commessa_id} className={`border-l-4 ${alertColor}`} data-testid={`margin-${m.commessa_id}`}>
                            <CardContent className="p-4">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <p className="text-sm font-bold text-slate-800">{m.numero} — {m.title}</p>
                                        <p className="text-xs text-slate-500">{m.client_name}</p>
                                    </div>
                                    {m.alert === 'rosso' && (
                                        <Badge className="bg-red-100 text-red-700 text-[10px]">
                                            <AlertTriangle className="h-3 w-3 mr-0.5" /> In Perdita
                                        </Badge>
                                    )}
                                    {m.alert === 'arancione' && (
                                        <Badge className="bg-orange-100 text-orange-700 text-[10px]">
                                            <AlertTriangle className="h-3 w-3 mr-0.5" /> Margine Eroso
                                        </Badge>
                                    )}
                                    {m.alert === 'giallo' && (
                                        <Badge className="bg-amber-100 text-amber-700 text-[10px]">Attenzione</Badge>
                                    )}
                                    {m.alert === 'verde' && (
                                        <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">OK</Badge>
                                    )}
                                </div>

                                {/* Stacked bars: Materiali + Personale */}
                                <div className="mt-3 space-y-2">
                                    <div className="flex items-center gap-3">
                                        <span className="text-[10px] text-slate-500 w-20">Preventivo</span>
                                        <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: '100%' }} />
                                        </div>
                                        <span className="text-xs font-mono font-bold text-slate-700 w-24 text-right">{fmtEur(m.valore_preventivo)}</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-[10px] text-slate-500 w-20">Materiali</span>
                                        <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
                                            <div className="h-full bg-amber-500 rounded-full"
                                                style={{ width: m.valore_preventivo > 0 ? `${Math.min((m.costi_materiali / m.valore_preventivo) * 100, 100)}%` : '0%' }} />
                                        </div>
                                        <span className="text-xs font-mono font-bold text-amber-700 w-24 text-right">{fmtEur(m.costi_materiali)}</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-[10px] text-slate-500 w-20">Personale</span>
                                        <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
                                            <div className="h-full bg-violet-500 rounded-full"
                                                style={{ width: m.valore_preventivo > 0 ? `${Math.min((m.costo_personale / m.valore_preventivo) * 100, 100)}%` : '0%' }} />
                                        </div>
                                        <span className="text-xs font-mono font-bold text-violet-700 w-24 text-right">
                                            {fmtEur(m.costo_personale)}
                                            {m.ore_lavorate > 0 && <span className="text-[10px] text-slate-400 ml-1">({m.ore_lavorate}h)</span>}
                                        </span>
                                    </div>
                                </div>

                                {/* Margin */}
                                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100">
                                    <div className="text-xs text-slate-500">
                                        Margine Netto
                                        {m.costo_orario_pieno > 0 && (
                                            <span className="text-[10px] text-slate-400 ml-1">(@ {fmtEur(m.costo_orario_pieno)}/h)</span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className={`text-sm font-bold font-mono ${m.margine >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                            {fmtEur(m.margine)}
                                        </span>
                                        <Badge className={`text-[10px] ${m.margine >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                                            {m.margine_pct > 0 ? '+' : ''}{m.margine_pct}%
                                        </Badge>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
