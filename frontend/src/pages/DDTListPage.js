/**
 * DDT List Page — Lista DDT con filtro per tipo.
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
import { Plus, Search, Truck, Pencil, Trash2 } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const DDT_TYPES = [
    { value: '', label: 'Tutti' },
    { value: 'vendita', label: 'Vendita' },
    { value: 'conto_lavoro', label: 'Conto Lavoro' },
    { value: 'rientro_conto_lavoro', label: 'Rientro C/L' },
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

export default function DDTListPage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const activeType = searchParams.get('type') || '';

    const fetchItems = useCallback(async () => {
        try {
            let url = '/ddt/?';
            if (activeType) url += `ddt_type=${activeType}&`;
            if (search) url += `search=${search}&`;
            const data = await apiRequest(url);
            setItems(data.items || []);
        } catch (e) {
            toast.error('Errore caricamento DDT');
        } finally {
            setLoading(false);
        }
    }, [activeType, search]);

    useEffect(() => { fetchItems(); }, [fetchItems]);

    const handleDelete = async (id) => {
        if (!window.confirm('Eliminare questo DDT?')) return;
        try {
            await apiRequest(`/ddt/${id}`, { method: 'DELETE' });
            toast.success('DDT eliminato');
            fetchItems();
        } catch (e) { toast.error(e.message); }
    };

    const setType = (t) => {
        if (t) searchParams.set('type', t);
        else searchParams.delete('type');
        setSearchParams(searchParams);
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="ddt-list-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Truck className="h-6 w-6 text-[#0055FF]" /> Documenti di Trasporto
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">DDT Vendita, Conto Lavoro e Rientro</p>
                    </div>
                    <Button data-testid="btn-new-ddt" onClick={() => navigate('/ddt/new')} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white">
                        <Plus className="h-4 w-4 mr-2" /> Nuovo DDT
                    </Button>
                </div>

                {/* Type Tabs + Search */}
                <Card className="border-gray-200">
                    <CardContent className="p-3 flex items-center gap-3">
                        <div className="flex gap-1">
                            {DDT_TYPES.map(t => (
                                <button
                                    key={t.value}
                                    data-testid={`filter-${t.value || 'all'}`}
                                    onClick={() => setType(t.value)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                                        activeType === t.value
                                            ? 'bg-[#0055FF] text-white'
                                            : 'text-slate-600 hover:bg-slate-100'
                                    }`}
                                >
                                    {t.label}
                                </button>
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
                            <EmptyState
                                type="distinte"
                                title="Nessun DDT trovato"
                                description="Crea il primo Documento di Trasporto per gestire le spedizioni e il conto lavoro."
                                actionLabel="Crea il primo DDT"
                                onAction={() => navigate('/ddt/new')}
                            />
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-[#1E293B]">
                                        <TableHead className="text-white font-medium">Numero</TableHead>
                                        <TableHead className="text-white font-medium">Tipo</TableHead>
                                        <TableHead className="text-white font-medium">Cliente</TableHead>
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
