/**
 * Sicurezza Cantieri - POS List Page
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
import { Plus, HardHat, MoreHorizontal, FileDown, Trash2, Edit } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useConfirm } from '../components/ConfirmProvider';

const STATUS_MAP = {
    bozza: { label: 'Bozza', color: 'bg-yellow-100 text-yellow-800' },
    completo: { label: 'Completo', color: 'bg-emerald-100 text-emerald-800' },
    approvato: { label: 'Approvato', color: 'bg-blue-100 text-blue-800' },
};

export default function SicurezzaPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const [docs, setDocs] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchDocs = async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/sicurezza/');
            setDocs(data.pos_list || []);
        } catch {
            toast.error('Errore nel caricamento');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchDocs(); }, []);

    const handleDelete = async (posId, e) => {
        e.stopPropagation();
        if (!(await confirm('Eliminare questo POS?'))) return;
        try {
            await apiRequest(`/sicurezza/${posId}`, { method: 'DELETE' });
            toast.success('POS eliminato');
            fetchDocs();
        } catch {
            toast.error('Errore nell\'eliminazione');
        }
    };

    const handleDownload = (posId, e) => {
        e.stopPropagation();
        const backendUrl = process.env.REACT_APP_BACKEND_URL;
        window.open(`${backendUrl}/api/sicurezza/${posId}/pdf`, '_blank');
    };

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="sicurezza-page">
                <div className="flex items-center justify-between">
                    <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Sicurezza Cantieri (POS)</h1>
                    <Button data-testid="btn-new-pos" onClick={() => navigate('/sicurezza/new')} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                        <Plus className="h-4 w-4 mr-2" /> Nuovo POS
                    </Button>
                </div>

                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Progetto</TableHead>
                                    <TableHead className="text-white font-semibold">Cantiere</TableHead>
                                    <TableHead className="text-white font-semibold">Cliente</TableHead>
                                    <TableHead className="text-white font-semibold text-center">Rischi</TableHead>
                                    <TableHead className="text-white font-semibold text-center">AI</TableHead>
                                    <TableHead className="text-white font-semibold">Stato</TableHead>
                                    <TableHead className="w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow><TableCell colSpan={7} className="text-center py-8"><div className="w-6 h-6 loading-spinner mx-auto" /></TableCell></TableRow>
                                ) : docs.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center py-12 text-slate-500">
                                            <HardHat className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                                            <p>Nessun POS trovato</p>
                                            <Button className="mt-4 bg-[#0055FF] text-white hover:bg-[#0044CC]" onClick={() => navigate('/sicurezza/new')}>
                                                <Plus className="h-4 w-4 mr-2" /> Crea il primo POS
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ) : docs.map((d) => {
                                    const st = STATUS_MAP[d.status] || STATUS_MAP.bozza;
                                    return (
                                        <TableRow key={d.pos_id} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/sicurezza/${d.pos_id}`)}>
                                            <TableCell className="font-medium">{d.project_name}</TableCell>
                                            <TableCell className="text-sm text-slate-600">{d.cantiere?.address || '-'}, {d.cantiere?.city || ''}</TableCell>
                                            <TableCell>{d.client_name || '-'}</TableCell>
                                            <TableCell className="text-center font-mono text-[#0055FF]">{d.selected_risks?.length || 0}</TableCell>
                                            <TableCell className="text-center">
                                                {d.ai_risk_assessment ? (
                                                    <Badge className="bg-emerald-100 text-emerald-800">Generato</Badge>
                                                ) : (
                                                    <Badge variant="outline" className="text-slate-400">Mancante</Badge>
                                                )}
                                            </TableCell>
                                            <TableCell><Badge className={st.color}>{st.label}</Badge></TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                        <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/sicurezza/${d.pos_id}`); }}>
                                                            <Edit className="h-4 w-4 mr-2" /> Modifica
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={(e) => handleDownload(d.pos_id, e)}>
                                                            <FileDown className="h-4 w-4 mr-2" /> Scarica PDF
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem className="text-red-600" onClick={(e) => handleDelete(d.pos_id, e)}>
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
