/**
 * Sicurezza Cantieri — POS & Schede Cantiere List Page
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { toast } from 'sonner';
import { Plus, HardHat, MoreHorizontal, Trash2, Edit, Shield, ClipboardCheck, MapPin } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useConfirm } from '../components/ConfirmProvider';

const STATUS_MAP = {
    bozza: { label: 'Bozza', color: 'bg-yellow-100 text-yellow-800' },
    in_compilazione: { label: 'In compilazione', color: 'bg-blue-100 text-blue-800' },
    completo: { label: 'Completo', color: 'bg-emerald-100 text-emerald-800' },
    approvato: { label: 'Approvato', color: 'bg-indigo-100 text-indigo-800' },
};

export default function SicurezzaPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const [cantieri, setCantieri] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchCantieri = async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/cantieri-sicurezza');
            setCantieri(data || []);
        } catch {
            toast.error('Errore nel caricamento');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchCantieri(); }, []);

    const handleDelete = async (cantiereId, e) => {
        e.stopPropagation();
        if (!(await confirm('Eliminare questa scheda cantiere?'))) return;
        try {
            await apiRequest(`/cantieri-sicurezza/${cantiereId}`, { method: 'DELETE' });
            toast.success('Scheda eliminata');
            fetchCantieri();
        } catch {
            toast.error("Errore nell'eliminazione");
        }
    };

    const handleNew = async () => {
        try {
            const res = await apiRequest('/cantieri-sicurezza', { method: 'POST', body: {} });
            navigate(`/scheda-cantiere/${res.cantiere_id}`);
        } catch {
            toast.error('Errore nella creazione');
        }
    };

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="sicurezza-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Sicurezza Cantieri</h1>
                        <p className="text-sm text-slate-500">Schede Cantiere POS — D.Lgs. 81/2008</p>
                    </div>
                    <Button data-testid="btn-new-cantiere" onClick={handleNew} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                        <Plus className="h-4 w-4 mr-2" /> Nuova Scheda Cantiere
                    </Button>
                </div>

                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Cantiere</TableHead>
                                    <TableHead className="text-white font-semibold">Committente</TableHead>
                                    <TableHead className="text-white font-semibold text-center">Lavoratori</TableHead>
                                    <TableHead className="text-white font-semibold text-center">Fasi</TableHead>
                                    <TableHead className="text-white font-semibold text-center">Gate</TableHead>
                                    <TableHead className="text-white font-semibold">Stato</TableHead>
                                    <TableHead className="w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow><TableCell colSpan={7} className="text-center py-8"><div className="w-6 h-6 loading-spinner mx-auto" /></TableCell></TableRow>
                                ) : cantieri.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center py-12 text-slate-500">
                                            <HardHat className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                                            <p>Nessuna scheda cantiere trovata</p>
                                            <Button className="mt-4 bg-[#0055FF] text-white hover:bg-[#0044CC]" onClick={handleNew} data-testid="btn-empty-new-cantiere">
                                                <Plus className="h-4 w-4 mr-2" /> Crea la prima scheda cantiere
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ) : cantieri.map((c) => {
                                    const st = STATUS_MAP[c.status] || STATUS_MAP.bozza;
                                    const gatePct = c.gate_pos_status?.completezza_percentuale || 0;
                                    const gateReady = c.gate_pos_status?.pronto_per_generazione;
                                    const addr = c.dati_cantiere?.indirizzo_cantiere || '';
                                    const city = c.dati_cantiere?.citta_cantiere || '';
                                    const committente = (c.soggetti || []).find(s => s.ruolo === 'COMMITTENTE')?.nome || '-';
                                    return (
                                        <TableRow key={c.cantiere_id} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/scheda-cantiere/${c.cantiere_id}`)} data-testid={`cantiere-row-${c.cantiere_id}`}>
                                            <TableCell>
                                                <div className="flex items-center gap-2">
                                                    <MapPin className="h-4 w-4 text-slate-400" />
                                                    <div>
                                                        <div className="font-medium">{addr || 'Senza indirizzo'}</div>
                                                        <div className="text-xs text-slate-500">{city}</div>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-sm">{committente}</TableCell>
                                            <TableCell className="text-center font-mono text-[#0055FF]">{(c.lavoratori_coinvolti || []).length}</TableCell>
                                            <TableCell className="text-center font-mono text-[#0055FF]">{(c.fasi_lavoro_selezionate || []).length}</TableCell>
                                            <TableCell className="text-center">
                                                <Badge className={gateReady ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}>
                                                    {gatePct}%
                                                </Badge>
                                            </TableCell>
                                            <TableCell><Badge className={st.color}>{st.label}</Badge></TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                        <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/scheda-cantiere/${c.cantiere_id}`); }}>
                                                            <Edit className="h-4 w-4 mr-2" /> Modifica
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem className="text-red-600" onClick={(e) => handleDelete(c.cantiere_id, e)}>
                                                            <Trash2 className="h-4 w-4 mr-2" /> Elimina
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
