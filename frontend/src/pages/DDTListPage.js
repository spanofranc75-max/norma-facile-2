/**
 * DDT List Page — Registro DDT con KPI, filtri avanzati e reportistica mensile.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import { Plus, Search, Truck, Pencil, Trash2, Package, FileCheck, BarChart3, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';
import { useConfirm } from '../components/ConfirmProvider';

const DDT_TYPES = [
    { value: '', label: 'Tutti' },
    { value: 'vendita', label: 'Vendita' },
    { value: 'conto_lavoro', label: 'Conto Lavoro' },
    { value: 'rientro_conto_lavoro', label: 'Rientro C/L' },
];

const STATUS_OPTIONS = [
    { value: '', label: 'Tutti' },
    { value: 'non_fatturato', label: 'Non Fatt.' },
    { value: 'fatturato', label: 'Fatturato' },
];

const TYPE_BADGES = {
    vendita: { label: 'Vendita', color: 'bg-blue-100 text-blue-800' },
    conto_lavoro: { label: 'C/Lavoro', color: 'bg-amber-100 text-amber-800' },
    rientro_conto_lavoro: { label: 'Rientro', color: 'bg-emerald-100 text-emerald-800' },
};

const STATUS_BADGES = {
    non_fatturato: { label: 'Non Fatt.', color: 'bg-slate-100 text-slate-700' },
    parzialmente_fatturato: { label: 'Parz. Fatt.', color: 'bg-amber-100 text-amber-700' },
    fatturato: { label: 'Fatturato', color: 'bg-emerald-100 text-emerald-800' },
};

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const MONTHS = ['Gen','Feb','Mar','Apr','Mag','Giu','Lug','Ago','Set','Ott','Nov','Dic'];

export default function DDTListPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [stats, setStats] = useState(null);
    const activeType = searchParams.get('type') || '';
    const activeStatus = searchParams.get('status') || '';
    const [statsYear, setStatsYear] = useState(new Date().getFullYear());
    const [statsMonth, setStatsMonth] = useState(new Date().getMonth() + 1);

    const fetchItems = useCallback(async () => {
        try {
            let url = '/ddt/?';
            if (activeType) url += `ddt_type=${activeType}&`;
            if (activeStatus) url += `status=${activeStatus}&`;
            if (search) url += `search=${search}&`;
            const data = await apiRequest(url);
            setItems(data.items || []);
        } catch (e) {
            toast.error('Errore caricamento DDT');
        } finally {
            setLoading(false);
        }
    }, [activeType, activeStatus, search]);

    const fetchStats = useCallback(async () => {
        try {
            const data = await apiRequest(`/ddt/stats/registro?year=${statsYear}&month=${statsMonth}`);
            setStats(data);
        } catch { /* stats are optional */ }
    }, [statsYear, statsMonth]);

    useEffect(() => { fetchItems(); }, [fetchItems]);
    useEffect(() => { fetchStats(); }, [fetchStats]);

    const handleDelete = async (id) => {
        if (!(await confirm('Eliminare questo DDT?'))) return;
        try {
            await apiRequest(`/ddt/${id}`, { method: 'DELETE' });
            toast.success('DDT eliminato');
            fetchItems();
            fetchStats();
        } catch (e) { toast.error(e.message); }
    };

    const setFilter = (key, val) => {
        if (val) searchParams.set(key, val);
        else searchParams.delete(key);
        setSearchParams(searchParams);
    };

    const prevMonth = () => {
        if (statsMonth === 1) { setStatsMonth(12); setStatsYear(y => y - 1); }
        else setStatsMonth(m => m - 1);
    };
    const nextMonth = () => {
        if (statsMonth === 12) { setStatsMonth(1); setStatsYear(y => y + 1); }
        else setStatsMonth(m => m + 1);
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="ddt-list-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Truck className="h-6 w-6 text-[#0055FF]" /> Registro DDT
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Documenti di Trasporto — Vendita, Conto Lavoro e Rientro</p>
                    </div>
                    <Button data-testid="btn-new-ddt" onClick={() => navigate('/ddt/new')} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white">
                        <Plus className="h-4 w-4 mr-2" /> Nuovo DDT
                    </Button>
                </div>

                {/* KPI Cards */}
                {stats && (
                    <div data-testid="ddt-stats">
                        <div className="flex items-center gap-2 mb-2">
                            <button onClick={prevMonth} className="p-1 hover:bg-slate-100 rounded"><ChevronLeft className="h-4 w-4" /></button>
                            <span className="text-sm font-semibold text-[#1E293B]">{MONTHS[statsMonth - 1]} {statsYear}</span>
                            <button onClick={nextMonth} className="p-1 hover:bg-slate-100 rounded"><ChevronRight className="h-4 w-4" /></button>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <KpiCard icon={Package} label="DDT Mese" value={stats.total_month} sub={`${stats.total_all} totali`} color="blue" testId="kpi-total-month" />
                            <KpiCard icon={BarChart3} label="Volume Mese" value={fmtEur(stats.volume_month)} sub={`${stats.per_status?.fatturato || 0} fatturati`} color="emerald" testId="kpi-volume" />
                            <KpiCard icon={Truck} label="Vendita" value={stats.per_type?.vendita || 0} sub={`C/L: ${stats.per_type?.conto_lavoro || 0} | Rientro: ${stats.per_type?.rientro_conto_lavoro || 0}`} color="amber" testId="kpi-types" />
                            <KpiCard icon={FileCheck} label="Non Fatturati" value={stats.per_status?.non_fatturato || 0} sub={`da convertire in fattura`} color="red" testId="kpi-unfilled" />
                        </div>
                    </div>
                )}

                {/* Filters */}
                <Card className="border-gray-200">
                    <CardContent className="p-3 flex flex-wrap items-center gap-3">
                        <div className="flex gap-1">
                            {DDT_TYPES.map(t => (
                                <button
                                    key={t.value}
                                    data-testid={`filter-type-${t.value || 'all'}`}
                                    onClick={() => setFilter('type', t.value)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeType === t.value ? 'bg-[#0055FF] text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                                >{t.label}</button>
                            ))}
                        </div>
                        <div className="h-6 w-px bg-slate-200" />
                        <div className="flex gap-1">
                            {STATUS_OPTIONS.map(s => (
                                <button
                                    key={s.value}
                                    data-testid={`filter-status-${s.value || 'all'}`}
                                    onClick={() => setFilter('status', s.value)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeStatus === s.value ? 'bg-[#1E293B] text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                                >{s.label}</button>
                            ))}
                        </div>
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                            <Input data-testid="search-ddt" value={search} onChange={e => setSearch(e.target.value)} placeholder="Cerca DDT..." className="pl-9 h-8 text-sm" />
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        {loading ? (
                            <div className="flex items-center justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" /></div>
                        ) : items.length === 0 ? (
                            <EmptyState type="distinte" title="Nessun DDT trovato" description="Crea il primo Documento di Trasporto per gestire le spedizioni e il conto lavoro." actionLabel="Crea il primo DDT" onAction={() => navigate('/ddt/new')} />
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-[#1E293B]">
                                        <TableHead className="text-white font-medium">Numero</TableHead>
                                        <TableHead className="text-white font-medium">Tipo</TableHead>
                                        <TableHead className="text-white font-medium">Cliente</TableHead>
                                        <TableHead className="text-white font-medium">Commessa</TableHead>
                                        <TableHead className="text-white font-medium">Causale</TableHead>
                                        <TableHead className="text-white font-medium text-right">Totale</TableHead>
                                        <TableHead className="text-white font-medium">Stato</TableHead>
                                        <TableHead className="text-white font-medium">Data</TableHead>
                                        <TableHead className="w-[80px]"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {items.map(ddt => {
                                        const tb = TYPE_BADGES[ddt.ddt_type] || TYPE_BADGES.vendita;
                                        const sb = STATUS_BADGES[ddt.status] || STATUS_BADGES.non_fatturato;
                                        return (
                                            <TableRow key={ddt.ddt_id} data-testid={`ddt-row-${ddt.ddt_id}`} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/ddt/${ddt.ddt_id}`)}>
                                                <TableCell className="font-mono font-semibold text-sm text-[#0055FF]">{ddt.number}</TableCell>
                                                <TableCell><Badge className={`${tb.color} text-[10px]`}>{tb.label}</Badge></TableCell>
                                                <TableCell className="text-sm">{ddt.client_name || '-'}</TableCell>
                                                <TableCell>
                                                    {ddt.commessa_info ? (
                                                        <button
                                                            data-testid={`ddt-commessa-link-${ddt.ddt_id}`}
                                                            className="flex items-center gap-1 text-xs text-[#0055FF] hover:underline font-medium"
                                                            onClick={(e) => { e.stopPropagation(); navigate(`/commesse/${ddt.commessa_info.commessa_id}`); }}
                                                        >
                                                            {ddt.commessa_info.numero || 'N/A'}
                                                            <ExternalLink className="h-2.5 w-2.5" />
                                                        </button>
                                                    ) : (
                                                        <span className="text-xs text-slate-300">--</span>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-xs text-slate-500">{ddt.causale_trasporto}</TableCell>
                                                <TableCell className="text-right font-mono text-sm">{fmtEur(ddt.totals?.total)}</TableCell>
                                                <TableCell><Badge className={`${sb.color} text-[10px]`}>{sb.label}</Badge></TableCell>
                                                <TableCell className="text-xs text-slate-400">{ddt.data_ora_trasporto?.split(' ')[0] || '-'}</TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                                        <Button variant="ghost" size="sm" onClick={() => navigate(`/ddt/${ddt.ddt_id}`)}><Pencil className="h-3.5 w-3.5" /></Button>
                                                        <Button variant="ghost" size="sm" onClick={() => handleDelete(ddt.ddt_id)} className="text-red-500"><Trash2 className="h-3.5 w-3.5" /></Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}

function KpiCard({ icon: Icon, label, value, sub, color, testId }) {
    const colors = {
        blue: 'from-blue-500 to-blue-600',
        emerald: 'from-emerald-500 to-emerald-600',
        amber: 'from-amber-500 to-amber-600',
        red: 'from-red-500 to-red-600',
    };
    return (
        <Card className="border-gray-200 overflow-hidden" data-testid={testId}>
            <CardContent className="p-3">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">{label}</p>
                        <p className="text-xl font-bold text-[#1E293B] mt-0.5">{value}</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>
                    </div>
                    <div className={`p-2 rounded-lg bg-gradient-to-br ${colors[color]} text-white`}>
                        <Icon className="h-4 w-4" />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
