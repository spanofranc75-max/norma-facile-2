/**
 * MovimentiBancariPage — Import CSV, lista movimenti, riconciliazione scadenze.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '../components/ui/dialog';
import {
    Upload, RefreshCw, Link2, Zap, ChevronUp, ChevronDown,
    TrendingDown, TrendingUp, AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

const API = process.env.REACT_APP_BACKEND_URL;

function fmtCur(v) {
    if (v == null || isNaN(v)) return '—';
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);
}
function fmtDate(d) {
    if (!d) return '';
    const p = d.split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
}

export default function MovimentiBancariPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const fileRef = useRef(null);

    // Filters
    const [dataDal, setDataDal] = useState('');
    const [dataAl, setDataAl] = useState('');
    const [conto, setConto] = useState('__none__');
    const [stato, setStato] = useState('__none__');
    const [search, setSearch] = useState('');
    const [sortBy, setSortBy] = useState('data');
    const [sortDir, setSortDir] = useState('desc');

    // Riconciliazione modal
    const [ricModal, setRicModal] = useState(null); // { movimento, candidates }
    const [ricLoading, setRicLoading] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const params = new URLSearchParams();
            if (dataDal) params.set('data_dal', dataDal);
            if (dataAl) params.set('data_al', dataAl);
            if (conto !== '__none__') params.set('conto', conto);
            if (stato !== '__none__') params.set('stato', stato);
            if (search) params.set('search', search);
            const qs = params.toString();
            const d = await apiRequest(`/movimenti/${qs ? '?' + qs : ''}`);
            setData(d);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [dataDal, dataAl, conto, stato, search]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // Import CSV
    const handleImport = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const contoName = prompt('Nome conto bancario:', 'Banca MPS');
        if (!contoName) return;
        try {
            const formData = new FormData();
            formData.append('file', file);
            const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
            const res = await fetch(`${API}/api/movimenti/import-csv?conto=${encodeURIComponent(contoName)}`, {
                method: 'POST',
                body: formData,
                credentials: 'include',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || 'Errore import');
            toast.success(result.message);
            if (result.errors?.length) toast.warning(`${result.errors.length} righe con errori`);
            fetchData();
        } catch (err) {
            toast.error(err.message);
        }
        if (fileRef.current) fileRef.current.value = '';
    };

    // Auto riconcilia
    const handleAutoRic = async () => {
        try {
            const r = await apiRequest('/movimenti/auto-riconcilia', { method: 'POST' });
            toast.success(r.message);
            fetchData();
        } catch (e) { toast.error(e.message); }
    };

    // Open riconciliazione modal
    const openRicModal = async (mov) => {
        setRicLoading(true);
        try {
            const r = await apiRequest(`/movimenti/${mov.movimento_id}/scadenze-candidate`);
            setRicModal({ movimento: mov, candidates: r.candidates || [] });
        } catch (e) { toast.error(e.message); }
        finally { setRicLoading(false); }
    };

    // Riconcilia
    const handleRiconcilia = async (candidate) => {
        try {
            await apiRequest(`/movimenti/${ricModal.movimento.movimento_id}/riconcilia`, {
                method: 'PATCH',
                body: {
                    scadenza_tipo: candidate.tipo,
                    fattura_id: candidate.fattura_id,
                    scadenza_idx: candidate.scadenza_idx,
                    importo: candidate.importo,
                },
            });
            toast.success('Riconciliazione completata');
            setRicModal(null);
            fetchData();
        } catch (e) { toast.error(e.message); }
    };

    // Sort
    const toggleSort = (col) => {
        if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortBy(col); setSortDir('desc'); }
    };
    const SortIcon = ({ col }) => {
        if (sortBy !== col) return null;
        return sortDir === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-0.5" /> : <ChevronDown className="h-3 w-3 inline ml-0.5" />;
    };

    const items = useMemo(() => {
        if (!data?.items) return [];
        const sorted = [...data.items];
        sorted.sort((a, b) => {
            let cmp = 0;
            if (sortBy === 'data') cmp = (a.data || '').localeCompare(b.data || '');
            else if (sortBy === 'importo') cmp = (a.importo || 0) - (b.importo || 0);
            else if (sortBy === 'descrizione') cmp = (a.descrizione || '').localeCompare(b.descrizione || '');
            return sortDir === 'asc' ? cmp : -cmp;
        });
        return sorted;
    }, [data, sortBy, sortDir]);

    const kpi = data?.kpi || {};
    const conti = data?.conti || [];

    if (loading) {
        return <DashboardLayout><div className="flex items-center justify-center h-64"><RefreshCw className="h-6 w-6 animate-spin text-slate-400" /></div></DashboardLayout>;
    }

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="movimenti-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Movimenti Bancari</h1>
                    <div className="flex gap-2">
                        <input ref={fileRef} type="file" accept=".csv" onChange={handleImport} className="hidden" data-testid="csv-input" />
                        <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} data-testid="import-csv-btn" className="border-slate-200">
                            <Upload className="h-4 w-4 mr-1.5" />Import CSV
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleAutoRic} data-testid="auto-ric-btn" className="border-slate-200">
                            <Zap className="h-4 w-4 mr-1.5" />Auto Riconcilia
                        </Button>
                    </div>
                </div>

                {/* KPI */}
                <div className="grid grid-cols-3 gap-3">
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <AlertCircle className="h-4 w-4 text-amber-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Non Riconciliati</span>
                            </div>
                            <p className="text-lg font-bold text-amber-700 font-mono" data-testid="kpi-non-ric">{kpi.non_riconciliati || 0}</p>
                        </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <TrendingDown className="h-4 w-4 text-red-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Uscite non ric.</span>
                            </div>
                            <p className="text-lg font-bold text-red-700 font-mono" data-testid="kpi-dare">{fmtCur(kpi.dare_non_riconciliato)}</p>
                        </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <TrendingUp className="h-4 w-4 text-emerald-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Entrate non ric.</span>
                            </div>
                            <p className="text-lg font-bold text-emerald-700 font-mono" data-testid="kpi-avere">{fmtCur(kpi.avere_non_riconciliato)}</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Filters */}
                <Card className="border-slate-200">
                    <CardContent className="p-3">
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
                            <div>
                                <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Dal</Label>
                                <Input type="date" value={dataDal} onChange={e => setDataDal(e.target.value)} className="h-8 text-xs" data-testid="filter-dal" />
                            </div>
                            <div>
                                <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Al</Label>
                                <Input type="date" value={dataAl} onChange={e => setDataAl(e.target.value)} className="h-8 text-xs" data-testid="filter-al" />
                            </div>
                            <div>
                                <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Conto</Label>
                                <Select value={conto} onValueChange={setConto}>
                                    <SelectTrigger className="h-8 text-xs" data-testid="filter-conto"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="__none__">Tutti</SelectItem>
                                        {conti.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Stato</Label>
                                <Select value={stato} onValueChange={setStato}>
                                    <SelectTrigger className="h-8 text-xs" data-testid="filter-stato"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="__none__">Tutti</SelectItem>
                                        <SelectItem value="non_riconciliato">Non riconciliato</SelectItem>
                                        <SelectItem value="riconciliato">Riconciliato</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Cerca</Label>
                                <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Descrizione..." className="h-8 text-xs" data-testid="filter-search" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-slate-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-700">
                                    <TableHead className="text-white text-[11px] font-semibold cursor-pointer hover:text-slate-200" onClick={() => toggleSort('data')}>Data <SortIcon col="data" /></TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold cursor-pointer hover:text-slate-200 text-right" onClick={() => toggleSort('importo')}>Importo <SortIcon col="importo" /></TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold cursor-pointer hover:text-slate-200" onClick={() => toggleSort('descrizione')}>Descrizione <SortIcon col="descrizione" /></TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Conto</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Stato</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {items.length === 0 ? (
                                    <TableRow><TableCell colSpan={6} className="text-center py-10 text-slate-400 text-sm">Nessun movimento. Importa un CSV per iniziare.</TableCell></TableRow>
                                ) : items.map((m, idx) => (
                                    <TableRow key={m.movimento_id} className={`${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'} hover:bg-blue-50/40`} data-testid={`mov-row-${idx}`}>
                                        <TableCell className="text-xs font-medium text-slate-700">{fmtDate(m.data)}</TableCell>
                                        <TableCell className={`text-right text-xs font-mono font-semibold ${m.segno === 'dare' ? 'text-red-600' : 'text-emerald-600'}`}>
                                            {m.segno === 'dare' ? '-' : '+'}{fmtCur(Math.abs(m.importo))}
                                        </TableCell>
                                        <TableCell className="text-xs text-slate-600 max-w-[350px] truncate">{m.descrizione}</TableCell>
                                        <TableCell className="text-xs text-slate-500">{m.conto}</TableCell>
                                        <TableCell>
                                            <Badge className={`text-[10px] px-1.5 py-0 ${m.stato_riconciliazione === 'riconciliato' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                                                {m.stato_riconciliazione === 'riconciliato' ? 'Riconciliato' : 'Non ric.'}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            {m.stato_riconciliazione !== 'riconciliato' && (
                                                <Button variant="ghost" size="sm" onClick={() => openRicModal(m)}
                                                    className="h-7 w-7 p-0 text-slate-400 hover:text-blue-600 hover:bg-blue-50"
                                                    title="Riconcilia" data-testid={`ric-btn-${m.movimento_id}`} disabled={ricLoading}>
                                                    <Link2 className="h-3.5 w-3.5" />
                                                </Button>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                    {items.length > 0 && (
                        <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-t border-slate-200">
                            <span className="text-xs text-slate-500">{items.length} movimenti</span>
                            <span className="text-xs text-slate-500">Totale: {data?.total || 0}</span>
                        </div>
                    )}
                </Card>

                {/* Riconciliazione Modal */}
                <Dialog open={!!ricModal} onOpenChange={() => setRicModal(null)}>
                    <DialogContent className="max-w-lg" data-testid="ric-modal">
                        <DialogHeader>
                            <DialogTitle className="text-base">Riconcilia Movimento</DialogTitle>
                            <DialogDescription className="text-xs">
                                {ricModal && <>
                                    <span className="font-mono font-semibold">{fmtCur(Math.abs(ricModal.movimento.importo))}</span>
                                    {' — '}{ricModal.movimento.descrizione?.substring(0, 60)}
                                </>}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto">
                            {ricModal?.candidates?.length === 0 && (
                                <p className="text-sm text-slate-400 text-center py-6">Nessuna scadenza compatibile trovata (±10% importo)</p>
                            )}
                            {ricModal?.candidates?.map((c, i) => (
                                <div key={`${c.fattura_id}-${c.scadenza_idx ?? i}`}
                                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/30 cursor-pointer transition-colors"
                                    onClick={() => handleRiconcilia(c)} data-testid={`candidate-${i}`}>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <Badge className={`text-[9px] ${c.tipo === 'passiva' ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                                                {c.tipo === 'passiva' ? 'Passiva' : 'Attiva'}
                                            </Badge>
                                            <span className="text-xs font-medium text-slate-700">{c.numero}</span>
                                        </div>
                                        <p className="text-[11px] text-slate-500 mt-0.5 truncate">{c.soggetto}</p>
                                    </div>
                                    <div className="text-right ml-3">
                                        <p className="text-xs font-mono font-semibold text-slate-800">{fmtCur(c.importo)}</p>
                                        <p className="text-[10px] text-slate-400">{fmtDate(c.data_scadenza)}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </DialogContent>
                </Dialog>
            </div>
        </DashboardLayout>
    );
}
