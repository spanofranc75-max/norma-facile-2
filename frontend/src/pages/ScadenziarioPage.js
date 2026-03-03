/**
 * ScadenziarioPage — Invoicex-style deadline table with filters and totals.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
    RefreshCw, Filter, Check, ExternalLink, ChevronDown, ChevronUp,
    Printer, Download,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

function fmtCur(v) {
    if (v == null || isNaN(v)) return '';
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);
}

function fmtDate(d) {
    if (!d) return '';
    const p = d.split('-');
    if (p.length === 3) return `${p[2]}/${p[1]}/${p[0]}`;
    return d;
}

function today() { return new Date().toISOString().split('T')[0]; }

function firstOfMonth() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}
function lastOfMonth() {
    const d = new Date();
    const last = new Date(d.getFullYear(), d.getMonth() + 1, 0);
    return last.toISOString().split('T')[0];
}

const MONTH_NAMES = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];

export default function ScadenziarioPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);

    // Filters
    const [vista, setVista] = useState('fornitori'); // fornitori | clienti
    const [dataScadDal, setDataScadDal] = useState(firstOfMonth());
    const [dataScadAl, setDataScadAl] = useState(lastOfMonth());
    const [soloDaPagare, setSoloDaPagare] = useState(true);
    const [searchFornitore, setSearchFornitore] = useState('');
    const [showFilters, setShowFilters] = useState(true);
    const [sortBy, setSortBy] = useState('data'); // data | fornitore | importo
    const [sortDir, setSortDir] = useState('asc');

    const fetchData = useCallback(async () => {
        try {
            const d = await apiRequest('/fatture-ricevute/scadenziario/dashboard');
            setData(d);
        } catch (e) {
            console.error('Fetch scadenziario error:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleSync = async () => {
        setSyncing(true);
        try {
            const result = await apiRequest('/fatture-ricevute/sync-fic', { method: 'POST' });
            toast.success(result.message || 'Sincronizzazione completata');
            fetchData();
        } catch (e) {
            toast.error(e.message || 'Errore sincronizzazione');
        } finally {
            setSyncing(false);
        }
    };

    const handleMarkPaid = async (item) => {
        if (item.tipo !== 'pagamento') return;
        try {
            await apiRequest(`/fatture-ricevute/${item.id}/pagamenti`, {
                method: 'POST',
                body: { importo: item.importo, data_pagamento: today(), metodo: 'bonifico', note: '' },
            });
            toast.success('Pagamento registrato');
            fetchData();
        } catch (e) {
            toast.error(e.message || 'Errore');
        }
    };

    // Filter and sort
    const filtered = useMemo(() => {
        if (!data?.scadenze) return [];
        let items = data.scadenze.filter(s => {
            // Vista filter
            if (vista === 'fornitori' && s.tipo !== 'pagamento') return false;
            if (vista === 'clienti' && s.tipo !== 'incasso') return false;

            // Date range
            const scad = s.data_scadenza || '';
            if (dataScadDal && scad && scad < dataScadDal) return false;
            if (dataScadAl && scad && scad > dataScadAl) return false;

            // Solo da pagare (exclude items with 0 amount)
            if (soloDaPagare && (!s.importo || s.importo <= 0)) return false;

            // Search
            if (searchFornitore) {
                const q = searchFornitore.toLowerCase();
                if (!(s.sottotitolo || '').toLowerCase().includes(q) &&
                    !(s.titolo || '').toLowerCase().includes(q)) return false;
            }
            return true;
        });

        // Sort
        items.sort((a, b) => {
            let cmp = 0;
            if (sortBy === 'data') cmp = (a.data_scadenza || '').localeCompare(b.data_scadenza || '');
            else if (sortBy === 'fornitore') cmp = (a.sottotitolo || '').localeCompare(b.sottotitolo || '');
            else if (sortBy === 'importo') cmp = (a.importo || 0) - (b.importo || 0);
            return sortDir === 'asc' ? cmp : -cmp;
        });

        return items;
    }, [data, vista, dataScadDal, dataScadAl, soloDaPagare, searchFornitore, sortBy, sortDir]);

    // Totals
    const totale = filtered.reduce((s, i) => s + (i.importo || 0), 0);
    const currentMonth = MONTH_NAMES[new Date().getMonth()];

    const toggleSort = (col) => {
        if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortBy(col); setSortDir('asc'); }
    };

    const SortIcon = ({ col }) => {
        if (sortBy !== col) return null;
        return sortDir === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-0.5" /> : <ChevronDown className="h-3 w-3 inline ml-0.5" />;
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    const kpi = data?.kpi || {};

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="scadenziario-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Scadenziario</h1>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowFilters(f => !f)} className="border-slate-200 text-slate-600">
                            <Filter className="h-4 w-4 mr-1.5" />
                            Filtri
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing} data-testid="sync-fic-btn" className="border-slate-200 text-slate-600">
                            <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                            {syncing ? 'Sync...' : 'Sync SDI'}
                        </Button>
                    </div>
                </div>

                {/* Summary bar */}
                <div className="flex items-center gap-6 px-5 py-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Da Pagare</span>
                        <p className="text-lg font-bold text-slate-800 font-mono" data-testid="total-da-pagare">{fmtCur(kpi.pagamenti_scaduti + kpi.pagamenti_mese_corrente)}</p>
                    </div>
                    <div className="h-8 w-px bg-slate-200" />
                    <div>
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Da Incassare</span>
                        <p className="text-lg font-bold text-slate-800 font-mono" data-testid="total-da-incassare">{fmtCur(kpi.incassi_scaduti + kpi.incassi_mese_corrente)}</p>
                    </div>
                    <div className="h-8 w-px bg-slate-200" />
                    <div>
                        <span className="text-[10px] font-semibold text-amber-600 uppercase tracking-wider text-[10px] font-semibold">Scaduti</span>
                        <p className="text-lg font-bold text-amber-700 font-mono" data-testid="total-scaduti">{fmtCur(vista === 'fornitori' ? kpi.pagamenti_scaduti : kpi.incassi_scaduti)}</p>
                    </div>
                    <div className="h-8 w-px bg-slate-200" />
                    <div>
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Acquisti Anno</span>
                        <p className="text-lg font-bold text-slate-800 font-mono">{fmtCur(kpi.totale_acquisti_anno)}</p>
                    </div>
                    <div className="ml-auto">
                        <span className="text-xs text-slate-400">{filtered.length} scadenze trovate</span>
                    </div>
                </div>

                {/* Filters */}
                {showFilters && (
                    <Card className="border-slate-200">
                        <CardContent className="p-4">
                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 items-end">
                                {/* Vista toggle */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Scadenze da</Label>
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => setVista('fornitori')}
                                            data-testid="vista-fornitori"
                                            className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-colors ${vista === 'fornitori' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                                        >
                                            Fornitori
                                        </button>
                                        <button
                                            onClick={() => setVista('clienti')}
                                            data-testid="vista-clienti"
                                            className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-colors ${vista === 'clienti' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                                        >
                                            Clienti
                                        </button>
                                    </div>
                                </div>

                                {/* Data scadenza dal */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Scadenza dal</Label>
                                    <Input
                                        type="date"
                                        value={dataScadDal}
                                        onChange={e => setDataScadDal(e.target.value)}
                                        data-testid="filter-data-dal"
                                        className="h-8 text-xs"
                                    />
                                </div>

                                {/* Data scadenza al */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Scadenza al</Label>
                                    <Input
                                        type="date"
                                        value={dataScadAl}
                                        onChange={e => setDataScadAl(e.target.value)}
                                        data-testid="filter-data-al"
                                        className="h-8 text-xs"
                                    />
                                </div>

                                {/* Fornitore search */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">
                                        {vista === 'fornitori' ? 'Fornitore' : 'Cliente'}
                                    </Label>
                                    <Input
                                        value={searchFornitore}
                                        onChange={e => setSearchFornitore(e.target.value)}
                                        placeholder="Cerca..."
                                        data-testid="filter-fornitore"
                                        className="h-8 text-xs"
                                    />
                                </div>

                                {/* Solo da pagare */}
                                <div className="flex items-center gap-2 pb-1">
                                    <Checkbox
                                        checked={soloDaPagare}
                                        onCheckedChange={setSoloDaPagare}
                                        data-testid="filter-solo-da-pagare"
                                    />
                                    <Label className="text-xs text-slate-600 cursor-pointer">Solo da pagare</Label>
                                </div>

                                {/* Reset */}
                                <div className="pb-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => {
                                            setDataScadDal(firstOfMonth());
                                            setDataScadAl(lastOfMonth());
                                            setSearchFornitore('');
                                            setSoloDaPagare(true);
                                        }}
                                        data-testid="reset-filtri"
                                        className="text-xs text-slate-500 hover:text-slate-700"
                                    >
                                        Reset filtri
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Table */}
                <Card className="border-slate-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-700">
                                    <TableHead className="text-white text-[11px] font-semibold w-[40px]">#</TableHead>
                                    <TableHead
                                        className="text-white text-[11px] font-semibold cursor-pointer select-none hover:text-slate-200"
                                        onClick={() => toggleSort('data')}
                                    >
                                        Data Scad. <SortIcon col="data" />
                                    </TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[55px]">Pagata</TableHead>
                                    <TableHead
                                        className="text-white text-[11px] font-semibold text-right cursor-pointer select-none hover:text-slate-200"
                                        onClick={() => toggleSort('importo')}
                                    >
                                        Importo <SortIcon col="importo" />
                                    </TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold text-right">Da Pagare</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Documento</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Data Doc.</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Pagamento</TableHead>
                                    <TableHead
                                        className="text-white text-[11px] font-semibold cursor-pointer select-none hover:text-slate-200"
                                        onClick={() => toggleSort('fornitore')}
                                    >
                                        {vista === 'fornitori' ? 'Fornitore' : 'Cliente'} <SortIcon col="fornitore" />
                                    </TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Stato</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filtered.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={11} className="text-center py-10 text-slate-400 text-sm">
                                            Nessuna scadenza trovata con i filtri selezionati
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filtered.map((item, idx) => {
                                        const isOverdue = item.stato === 'scaduto';
                                        const rowBg = isOverdue ? 'bg-red-50/60' : idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50';
                                        return (
                                            <TableRow
                                                key={`${item.id}-${idx}`}
                                                className={`${rowBg} hover:bg-blue-50/40 transition-colors`}
                                                data-testid={`scadenza-${item.id}`}
                                            >
                                                <TableCell className="text-xs text-slate-500 font-mono">{idx + 1}</TableCell>
                                                <TableCell className={`text-xs font-medium ${isOverdue ? 'text-amber-700 font-semibold' : 'text-slate-700'}`}>
                                                    {fmtDate(item.data_scadenza)}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    <span className={`text-xs font-bold ${isOverdue ? 'text-amber-600' : 'text-slate-400'}`}>N</span>
                                                </TableCell>
                                                <TableCell className="text-right text-xs font-mono font-semibold text-slate-800">
                                                    {fmtCur(item.importo)}
                                                </TableCell>
                                                <TableCell className={`text-right text-xs font-mono font-bold ${isOverdue ? 'text-amber-700' : 'text-slate-800'}`}>
                                                    {fmtCur(item.importo)}
                                                </TableCell>
                                                <TableCell className="text-xs text-slate-600">{item.titolo}</TableCell>
                                                <TableCell className="text-xs text-slate-500">{item.data_documento ? fmtDate(item.data_documento) : ''}</TableCell>
                                                <TableCell className="text-xs text-slate-500">{item.pagamento || ''}</TableCell>
                                                <TableCell className="text-xs font-medium text-slate-700 max-w-[180px] truncate">{item.sottotitolo}</TableCell>
                                                <TableCell>
                                                    <Badge className={`text-[10px] px-1.5 py-0 ${
                                                        isOverdue ? 'bg-amber-100 text-amber-700' :
                                                        item.stato === 'in_scadenza' ? 'bg-sky-100 text-sky-700' :
                                                        'bg-slate-100 text-slate-500'
                                                    }`}>
                                                        {isOverdue ? 'Scaduto' : item.stato === 'in_scadenza' ? 'In scadenza' : 'Futuro'}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex gap-0.5">
                                                        {item.tipo === 'pagamento' && (
                                                            <Button
                                                                variant="ghost" size="sm"
                                                                onClick={() => handleMarkPaid(item)}
                                                                className="h-7 w-7 p-0 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50"
                                                                title="Segna pagato"
                                                                data-testid={`pay-btn-${item.id}`}
                                                            >
                                                                <Check className="h-3.5 w-3.5" />
                                                            </Button>
                                                        )}
                                                        {item.link && (
                                                            <a href={item.link}>
                                                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-slate-400 hover:text-blue-600 hover:bg-blue-50" title="Dettaglio">
                                                                    <ExternalLink className="h-3 w-3" />
                                                                </Button>
                                                            </a>
                                                        )}
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Footer totals - Invoicex style */}
                    {filtered.length > 0 && (
                        <div className="flex items-center justify-end gap-6 px-5 py-3 bg-slate-50 border-t border-slate-200" data-testid="footer-totals">
                            <span className="text-xs text-slate-500">
                                Totale <strong className="text-slate-800 font-mono ml-1">{fmtCur(totale)}</strong>
                            </span>
                            <span className="text-xs text-slate-400">|</span>
                            <span className="text-xs text-slate-500">
                                Gia Pagate <strong className="text-slate-800 font-mono ml-1">{fmtCur(0)}</strong>
                            </span>
                            <span className="text-xs text-slate-400">|</span>
                            <span className="text-xs text-slate-500">
                                Da Pagare <strong className="text-amber-700 font-mono ml-1">{fmtCur(totale)}</strong>
                            </span>
                        </div>
                    )}
                </Card>
            </div>
        </DashboardLayout>
    );
}
