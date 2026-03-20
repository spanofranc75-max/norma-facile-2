/**
 * ScadenziarioPage — Vista unificata scadenze attive/passive con aging e alert.
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
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    RefreshCw, Filter, Check, ExternalLink, ChevronDown, ChevronUp,
    AlertTriangle, Clock, TrendingDown, TrendingUp, FileSpreadsheet, FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

function fmtCur(v) {
    if (v == null || isNaN(v)) return '—';
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);
}

function fmtDate(d) {
    if (!d) return '';
    const p = d.split('-');
    if (p.length === 3) return `${p[2]}/${p[1]}/${p[0]}`;
    return d;
}

function today() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function daysFromToday(dateStr) {
    if (!dateStr) return null;
    const t = new Date(); t.setHours(0, 0, 0, 0);
    const d = new Date(dateStr); d.setHours(0, 0, 0, 0);
    return Math.round((t - d) / 86400000);
}

export default function ScadenziarioPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);

    // Filters
    const [vista, setVista] = useState('tutti'); // tutti | fornitori | clienti
    const [statoFiltro, setStatoFiltro] = useState('__none__'); // __none__ | scaduto | in_scadenza | ok
    const [dataScadDal, setDataScadDal] = useState('');
    const [dataScadAl, setDataScadAl] = useState('');
    const [soloDaPagare, setSoloDaPagare] = useState(true);
    const [searchText, setSearchText] = useState('');
    const [showFilters, setShowFilters] = useState(true);
    const [sortBy, setSortBy] = useState('data');
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
            const [ficResult, invResult] = await Promise.all([
                apiRequest('/fatture-ricevute/sync-fic', { method: 'POST' }).catch(() => null),
                apiRequest('/invoices/sync-scadenze', { method: 'POST' }).catch(() => null),
            ]);
            const messages = [];
            if (ficResult?.message) messages.push(ficResult.message);
            if (invResult?.message) messages.push(invResult.message);
            toast.success(messages.join(' | ') || 'Sincronizzazione completata');
            fetchData();
        } catch (e) {
            toast.error(e.message || 'Errore sincronizzazione');
        } finally {
            setSyncing(false);
        }
    };

    const buildExportQuery = () => {
        const params = [];
        if (vista === 'fornitori') params.push('tipo=pagamento');
        if (vista === 'clienti') params.push('tipo=incasso');
        if (statoFiltro !== '__none__') params.push(`stato=${statoFiltro}`);
        if (dataScadDal) params.push(`data_dal=${dataScadDal}`);
        if (dataScadAl) params.push(`data_al=${dataScadAl}`);
        return params.length > 0 ? '?' + params.join('&') : '';
    };

    const handleExportXlsx = () => {
        const qs = buildExportQuery();
        downloadPdfBlob(`/fatture-ricevute/scadenziario/export/xlsx${qs}`, `Scadenziario_${new Date().toISOString().slice(0,10)}.xlsx`)
            .catch(e => toast.error(e.message));
    };

    const handleExportPdf = () => {
        const qs = buildExportQuery();
        downloadPdfBlob(`/fatture-ricevute/scadenziario/export/pdf${qs}`, `Scadenziario_${new Date().toISOString().slice(0,10)}.pdf`)
            .catch(e => toast.error(e.message));
    };

    const handleMarkPaid = async (item) => {
        if (item.tipo === 'pagamento') {
            try {
                await apiRequest(`/fatture-ricevute/${item.id}/pagamenti`, {
                    method: 'POST',
                    body: { importo: item.importo, data_pagamento: today(), metodo: 'bonifico', note: '' },
                });
                toast.success('Pagamento registrato');
                fetchData();
            } catch (e) { toast.error(e.message); }
        } else if (item.tipo === 'incasso' && item.rata) {
            try {
                await apiRequest(`/invoices/${item.id}/scadenze/${item.rata}/paga`, { method: 'PATCH' });
                toast.success('Incasso registrato');
                fetchData();
            } catch (e) { toast.error(e.message); }
        }
    };

    // Filter and sort
    const filtered = useMemo(() => {
        if (!data?.scadenze) return [];
        let items = data.scadenze.filter(s => {
            // Solo scadenze finanziarie (pagamento/incasso)
            if (s.tipo !== 'pagamento' && s.tipo !== 'incasso') return false;

            // Vista
            if (vista === 'fornitori' && s.tipo !== 'pagamento') return false;
            if (vista === 'clienti' && s.tipo !== 'incasso') return false;

            // Stato
            if (statoFiltro !== '__none__' && s.stato !== statoFiltro) return false;

            // Date range
            const scad = s.data_scadenza || '';
            if (dataScadDal && scad && scad < dataScadDal) return false;
            if (dataScadAl && scad && scad > dataScadAl) return false;

            // Solo da pagare
            if (soloDaPagare && (!s.importo || s.importo <= 0)) return false;

            // Search
            if (searchText) {
                const q = searchText.toLowerCase();
                if (!(s.sottotitolo || '').toLowerCase().includes(q) &&
                    !(s.titolo || '').toLowerCase().includes(q)) return false;
            }
            return true;
        });

        items.sort((a, b) => {
            let cmp = 0;
            if (sortBy === 'data') cmp = (a.data_scadenza || '').localeCompare(b.data_scadenza || '');
            else if (sortBy === 'fornitore') cmp = (a.sottotitolo || '').localeCompare(b.sottotitolo || '');
            else if (sortBy === 'importo') cmp = (a.importo || 0) - (b.importo || 0);
            return sortDir === 'asc' ? cmp : -cmp;
        });
        return items;
    }, [data, vista, statoFiltro, dataScadDal, dataScadAl, soloDaPagare, searchText, sortBy, sortDir]);

    const totale = filtered.reduce((s, i) => s + (i.importo || 0), 0);

    const toggleSort = (col) => {
        if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortBy(col); setSortDir('asc'); }
    };
    const SortIcon = ({ col }) => {
        if (sortBy !== col) return null;
        return sortDir === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-0.5" /> : <ChevronDown className="h-3 w-3 inline ml-0.5" />;
    };

    function rowColor(item) {
        const days = daysFromToday(item.data_scadenza);
        if (days === null) return '';
        if (days > 0) return 'bg-red-50/70'; // scaduto
        if (days >= -7) return 'bg-amber-50/60'; // entro 7 giorni
        return '';
    }

    function badgeStyle(item) {
        const days = daysFromToday(item.data_scadenza);
        if (days === null) return { cls: 'bg-slate-100 text-slate-500', label: '—' };
        if (days > 90) return { cls: 'bg-red-600 text-white', label: `Scaduto ${days}gg` };
        if (days > 0) return { cls: 'bg-red-100 text-red-700', label: `Scaduto ${days}gg` };
        if (days >= -7) return { cls: 'bg-amber-100 text-amber-700', label: `${Math.abs(days)}gg` };
        return { cls: 'bg-emerald-50 text-emerald-600', label: `${Math.abs(days)}gg` };
    }

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
    const agingP = kpi.aging_pagamenti || {};
    const agingI = kpi.aging_incassi || {};
    const agingData = vista === 'clienti' ? agingI : (vista === 'fornitori' ? agingP : {
        '0_30': (agingP['0_30'] || 0) + (agingI['0_30'] || 0),
        '31_60': (agingP['31_60'] || 0) + (agingI['31_60'] || 0),
        '61_90': (agingP['61_90'] || 0) + (agingI['61_90'] || 0),
        'over_90': (agingP['over_90'] || 0) + (agingI['over_90'] || 0),
    });
    const agingTotal = Object.values(agingData).reduce((a, b) => a + b, 0);

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="scadenziario-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Scadenziario</h1>
                    <div className="flex gap-2 flex-wrap">
                        <Button variant="outline" size="sm" onClick={handleExportXlsx} data-testid="export-xlsx-btn" className="border-slate-200 text-slate-600">
                            <FileSpreadsheet className="h-4 w-4 mr-1.5" />Excel
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleExportPdf} data-testid="export-pdf-btn" className="border-slate-200 text-slate-600">
                            <FileText className="h-4 w-4 mr-1.5" />PDF
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => setShowFilters(f => !f)} className="border-slate-200 text-slate-600">
                            <Filter className="h-4 w-4 mr-1.5" />Filtri
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing} data-testid="sync-fic-btn" className="border-slate-200 text-slate-600">
                            <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                            {syncing ? 'Sync...' : 'Sync SDI'}
                        </Button>
                    </div>
                </div>

                {/* Summary KPI */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <TrendingDown className="h-4 w-4 text-red-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Da Pagare</span>
                            </div>
                            <p className="text-lg font-bold text-slate-800 font-mono" data-testid="total-da-pagare">
                                {fmtCur((kpi.pagamenti_scaduti || 0) + (kpi.pagamenti_mese_corrente || 0))}
                            </p>
                            {kpi.pagamenti_scaduti > 0 && (
                                <span className="text-[10px] text-red-600 font-medium">di cui {fmtCur(kpi.pagamenti_scaduti)} scaduti</span>
                            )}
                        </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <TrendingUp className="h-4 w-4 text-emerald-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Da Incassare</span>
                            </div>
                            <p className="text-lg font-bold text-slate-800 font-mono" data-testid="total-da-incassare">
                                {fmtCur((kpi.incassi_scaduti || 0) + (kpi.incassi_mese_corrente || 0))}
                            </p>
                            {kpi.incassi_scaduti > 0 && (
                                <span className="text-[10px] text-red-600 font-medium">di cui {fmtCur(kpi.incassi_scaduti)} scaduti</span>
                            )}
                        </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Scadute Totali</span>
                            </div>
                            <p className="text-lg font-bold text-amber-700 font-mono" data-testid="total-scaduti">
                                {fmtCur(agingTotal)}
                            </p>
                            <span className="text-[10px] text-slate-500">{kpi.scadute || 0} scadenze</span>
                        </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <Clock className="h-4 w-4 text-sky-500" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Acquisti Anno</span>
                            </div>
                            <p className="text-lg font-bold text-slate-800 font-mono">
                                {fmtCur(kpi.totale_acquisti_anno)}
                            </p>
                            <span className="text-[10px] text-slate-500">{filtered.length} scadenze filtrate</span>
                        </CardContent>
                    </Card>
                </div>

                {/* Aging bar */}
                {agingTotal > 0 && (
                    <Card className="border-red-200 bg-red-50/30" data-testid="aging-section">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="h-4 w-4 text-red-500" />
                                <span className="text-xs font-semibold text-red-700">
                                    Aging Scaduto — {vista === 'clienti' ? 'Crediti' : vista === 'fornitori' ? 'Debiti' : 'Totale'}
                                </span>
                            </div>
                            <div className="grid grid-cols-4 gap-2">
                                {[
                                    { key: '0_30', label: '0-30 gg', color: 'bg-amber-100 text-amber-800 border-amber-200' },
                                    { key: '31_60', label: '31-60 gg', color: 'bg-orange-100 text-orange-800 border-orange-200' },
                                    { key: '61_90', label: '61-90 gg', color: 'bg-red-100 text-red-800 border-red-200' },
                                    { key: 'over_90', label: '>90 gg', color: 'bg-red-200 text-red-900 border-red-300' },
                                ].map(b => (
                                    <div key={b.key} className={`rounded-md border p-2 text-center ${b.color}`}>
                                        <div className="text-[10px] font-semibold uppercase tracking-wider">{b.label}</div>
                                        <div className="text-sm font-bold font-mono mt-0.5">{fmtCur(agingData[b.key] || 0)}</div>
                                    </div>
                                ))}
                            </div>
                            {/* Visual bar */}
                            {agingTotal > 0 && (
                                <div className="flex h-2 rounded-full overflow-hidden mt-2 bg-slate-200">
                                    {[
                                        { key: '0_30', color: 'bg-amber-400' },
                                        { key: '31_60', color: 'bg-orange-400' },
                                        { key: '61_90', color: 'bg-red-400' },
                                        { key: 'over_90', color: 'bg-red-600' },
                                    ].map(b => {
                                        const pct = ((agingData[b.key] || 0) / agingTotal) * 100;
                                        return pct > 0 ? <div key={b.key} className={`${b.color}`} style={{ width: `${pct}%` }} /> : null;
                                    })}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* Filters */}
                {showFilters && (
                    <Card className="border-slate-200">
                        <CardContent className="p-4">
                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 items-end">
                                {/* Vista toggle */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Vista</Label>
                                    <div className="flex gap-0.5">
                                        {[
                                            { v: 'tutti', l: 'Tutti' },
                                            { v: 'fornitori', l: 'Fornitori' },
                                            { v: 'clienti', l: 'Clienti' },
                                        ].map(o => (
                                            <button key={o.v} onClick={() => setVista(o.v)} data-testid={`vista-${o.v}`}
                                                className={`flex-1 px-2 py-1.5 rounded text-[11px] font-medium transition-colors ${vista === o.v ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                                            >{o.l}</button>
                                        ))}
                                    </div>
                                </div>

                                {/* Stato */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Stato</Label>
                                    <Select value={statoFiltro} onValueChange={setStatoFiltro}>
                                        <SelectTrigger className="h-8 text-xs" data-testid="filter-stato">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">Tutti gli stati</SelectItem>
                                            <SelectItem value="scaduto">Scaduto</SelectItem>
                                            <SelectItem value="in_scadenza">In scadenza</SelectItem>
                                            <SelectItem value="ok">Futuro</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* Data dal */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Scadenza dal</Label>
                                    <Input type="date" value={dataScadDal} onChange={e => setDataScadDal(e.target.value)}
                                        data-testid="filter-data-dal" className="h-8 text-xs" />
                                </div>
                                {/* Data al */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Scadenza al</Label>
                                    <Input type="date" value={dataScadAl} onChange={e => setDataScadAl(e.target.value)}
                                        data-testid="filter-data-al" className="h-8 text-xs" />
                                </div>
                                {/* Search */}
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block">Cerca</Label>
                                    <Input value={searchText} onChange={e => setSearchText(e.target.value)}
                                        placeholder="Fornitore / Cliente..." data-testid="filter-search" className="h-8 text-xs" />
                                </div>
                                {/* Solo da pagare */}
                                <div className="flex items-center gap-2 pb-1">
                                    <Checkbox checked={soloDaPagare} onCheckedChange={setSoloDaPagare} data-testid="filter-solo-da-pagare" />
                                    <Label className="text-xs text-slate-600 cursor-pointer">Solo aperte</Label>
                                </div>
                                {/* Reset */}
                                <div className="pb-1">
                                    <Button variant="ghost" size="sm" data-testid="reset-filtri"
                                        onClick={() => { setDataScadDal(''); setDataScadAl(''); setSearchText(''); setSoloDaPagare(true); setStatoFiltro('__none__'); setVista('tutti'); }}
                                        className="text-xs text-slate-500 hover:text-slate-700"
                                    >Reset filtri</Button>
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
                                    <TableHead className="text-white text-[11px] font-semibold w-[36px]">#</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[50px]">Tipo</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold cursor-pointer select-none hover:text-slate-200" onClick={() => toggleSort('data')}>
                                        Scadenza <SortIcon col="data" />
                                    </TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold text-right cursor-pointer select-none hover:text-slate-200" onClick={() => toggleSort('importo')}>
                                        Importo <SortIcon col="importo" />
                                    </TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Documento</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Data Doc.</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold cursor-pointer select-none hover:text-slate-200" onClick={() => toggleSort('fornitore')}>
                                        Soggetto <SortIcon col="fornitore" />
                                    </TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Stato</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[50px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filtered.length === 0 ? (
                                    <TableRow><TableCell colSpan={9} className="text-center py-10 text-slate-400 text-sm">Nessuna scadenza trovata</TableCell></TableRow>
                                ) : filtered.map((item, idx) => {
                                    const bg = rowColor(item);
                                    const badge = badgeStyle(item);
                                    return (
                                        <TableRow key={`${item.id}-${item.rata || idx}`} className={`${bg || (idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50')} hover:bg-blue-50/40 transition-colors`} data-testid={`scadenza-row-${idx}`}>
                                            <TableCell className="text-xs text-slate-500 font-mono">{idx + 1}</TableCell>
                                            <TableCell>
                                                <Badge className={`text-[9px] px-1 py-0 ${item.tipo === 'incasso' ? 'bg-emerald-100 text-emerald-700' : 'bg-sky-100 text-sky-700'}`}>
                                                    {item.tipo === 'incasso' ? 'IN' : 'OUT'}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-xs font-medium text-slate-700">{fmtDate(item.data_scadenza)}</TableCell>
                                            <TableCell className="text-right text-xs font-mono font-semibold text-slate-800">{fmtCur(item.importo)}</TableCell>
                                            <TableCell className="text-xs text-slate-600 max-w-[200px] truncate">{item.titolo}</TableCell>
                                            <TableCell className="text-xs text-slate-500">{fmtDate(item.data_documento)}</TableCell>
                                            <TableCell className="text-xs font-medium text-slate-700 max-w-[180px] truncate">{item.sottotitolo}</TableCell>
                                            <TableCell>
                                                <Badge className={`text-[10px] px-1.5 py-0 ${badge.cls}`}>{badge.label}</Badge>
                                            </TableCell>
                                            <TableCell>
                                                {(item.tipo === 'pagamento' || item.tipo === 'incasso') && (
                                                    <Button variant="ghost" size="sm" onClick={() => handleMarkPaid(item)}
                                                        className="h-7 w-7 p-0 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50"
                                                        title={item.tipo === 'incasso' ? 'Segna incassato' : 'Segna pagato'}
                                                        data-testid={`pay-btn-${item.id}-${item.rata || 0}`}>
                                                        <Check className="h-3.5 w-3.5" />
                                                    </Button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Footer totals */}
                    {filtered.length > 0 && (
                        <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-t border-slate-200" data-testid="footer-totals">
                            <span className="text-xs text-slate-500">{filtered.length} scadenze</span>
                            <span className="text-xs font-semibold text-slate-700">
                                Totale: <span className="font-mono text-slate-900 ml-1">{fmtCur(totale)}</span>
                            </span>
                        </div>
                    )}
                </Card>
            </div>
        </DashboardLayout>
    );
}
