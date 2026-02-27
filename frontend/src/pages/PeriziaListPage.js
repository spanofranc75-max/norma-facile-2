/**
 * Perizia Sinistro — List Page
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Plus, Search, Trash2, FileDown, ShieldAlert, Eye } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const STATUS_MAP = {
    bozza: { label: 'Bozza', color: 'bg-slate-100 text-slate-700' },
    analizzata: { label: 'Analizzata', color: 'bg-blue-100 text-blue-800' },
    completata: { label: 'Completata', color: 'bg-emerald-100 text-emerald-800' },
    inviata: { label: 'Inviata', color: 'bg-amber-100 text-amber-800' },
};

const TIPO_MAP = {
    strutturale: { label: 'Strutturale', color: 'bg-red-100 text-red-700' },
    estetico: { label: 'Estetico', color: 'bg-yellow-100 text-yellow-700' },
    automatismi: { label: 'Automatismi', color: 'bg-purple-100 text-purple-700' },
};

export default function PeriziaListPage() {
    const navigate = useNavigate();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [toDelete, setToDelete] = useState(null);

    const fetch = useCallback(async () => {
        try {
            const data = await apiRequest(`/perizie/?search=${search}`);
            setItems(data.items || []);
        } catch { toast.error('Errore caricamento perizie'); }
        finally { setLoading(false); }
    }, [search]);

    useEffect(() => { fetch(); }, [fetch]);

    const handleDelete = async () => {
        if (!toDelete) return;
        try {
            await apiRequest(`/perizie/${toDelete.perizia_id}`, { method: 'DELETE' });
            toast.success('Perizia eliminata');
            setDeleteOpen(false);
            fetch();
        } catch (e) { toast.error(e.message); }
    };

    const fmtDate = (d) => {
        if (!d) return '-';
        const dt = new Date(d);
        return dt.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    const fmtMoney = (v) => v ? `${Number(v).toLocaleString('it-IT', { minimumFractionDigits: 2 })} EUR` : '-';

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="perizia-list-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <ShieldAlert className="h-6 w-6 text-[#0055FF]" /> Perizie Sinistro
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Perizie tecniche estimative per danni da sinistro su recinzioni e cancelli</p>
                    </div>
                    <Button data-testid="btn-new-perizia" onClick={() => navigate('/perizie/new')} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white">
                        <Plus className="h-4 w-4 mr-2" /> Nuova Perizia
                    </Button>
                </div>

                <Card className="border-gray-200">
                    <CardContent className="p-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                            <Input data-testid="search-perizie" value={search} onChange={e => setSearch(e.target.value)} placeholder="Cerca per numero, cliente o descrizione..." className="pl-10" />
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-medium">Numero</TableHead>
                                    <TableHead className="text-white font-medium">Data</TableHead>
                                    <TableHead className="text-white font-medium">Cliente</TableHead>
                                    <TableHead className="text-white font-medium">Tipo Danno</TableHead>
                                    <TableHead className="text-white font-medium">Totale</TableHead>
                                    <TableHead className="text-white font-medium">Stato</TableHead>
                                    <TableHead className="w-[100px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow><TableCell colSpan={7} className="text-center py-8"><div className="w-6 h-6 loading-spinner mx-auto" /></TableCell></TableRow>
                                ) : items.length === 0 ? (
                                    <TableRow><TableCell colSpan={7} className="p-0">
                                        <EmptyState type="distinte" title="Nessuna perizia creata" description="Crea la tua prima perizia sinistro per generare un preventivo tecnico dettagliato." actionLabel="Nuova Perizia" onAction={() => navigate('/perizie/new')} />
                                    </TableCell></TableRow>
                                ) : items.map(p => {
                                    const st = STATUS_MAP[p.status] || STATUS_MAP.bozza;
                                    const tp = TIPO_MAP[p.tipo_danno] || TIPO_MAP.strutturale;
                                    return (
                                        <TableRow key={p.perizia_id} data-testid={`perizia-row-${p.perizia_id}`} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/perizie/${p.perizia_id}`)}>
                                            <TableCell className="font-mono font-medium text-[#0055FF]">{p.number}</TableCell>
                                            <TableCell className="text-sm">{fmtDate(p.created_at)}</TableCell>
                                            <TableCell className="font-medium">{p.client_name || '-'}</TableCell>
                                            <TableCell><Badge className={`${tp.color} text-[10px]`}>{tp.label}</Badge></TableCell>
                                            <TableCell className="font-mono font-medium">{fmtMoney(p.total_perizia)}</TableCell>
                                            <TableCell><Badge className={`${st.color} text-[10px]`}>{st.label}</Badge></TableCell>
                                            <TableCell>
                                                <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                                    <Button variant="ghost" size="sm" onClick={() => navigate(`/perizie/${p.perizia_id}`)} className="text-[#0055FF]"><Eye className="h-4 w-4" /></Button>
                                                    <Button variant="ghost" size="sm" onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/perizie/${p.perizia_id}/pdf`, '_blank')} className="text-slate-500"><FileDown className="h-4 w-4" /></Button>
                                                    <Button variant="ghost" size="sm" onClick={() => { setToDelete(p); setDeleteOpen(true); }} className="text-red-600"><Trash2 className="h-4 w-4" /></Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Elimina Perizia</DialogTitle>
                        <DialogDescription>Eliminare <strong>{toDelete?.number}</strong>? Non reversibile.</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteOpen(false)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete" variant="destructive" onClick={handleDelete}>Elimina</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
