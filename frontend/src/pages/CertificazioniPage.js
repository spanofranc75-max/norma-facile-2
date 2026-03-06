/**
 * Certificazioni CE - List Page
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
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { toast } from 'sonner';
import { Plus, Shield, MoreHorizontal, FileDown, Trash2, Edit } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useConfirm } from '../components/ConfirmProvider';

const STATUS_MAP = {
    bozza: { label: 'Bozza', color: 'bg-yellow-100 text-yellow-800' },
    emessa: { label: 'Emessa', color: 'bg-emerald-100 text-emerald-800' },
    revisionata: { label: 'Revisionata', color: 'bg-blue-100 text-blue-800' },
};

export default function CertificazioniPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const [certs, setCerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('all');

    const fetchCerts = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (statusFilter !== 'all') params.append('status', statusFilter);
            const data = await apiRequest(`/certificazioni/?${params}`);
            setCerts(data.certificazioni || []);
        } catch {
            toast.error('Errore nel caricamento');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchCerts(); }, [statusFilter]);

    const handleDelete = async (certId, e) => {
        e.stopPropagation();
        if (!(await confirm('Eliminare questa certificazione?'))) return;
        try {
            await apiRequest(`/certificazioni/${certId}`, { method: 'DELETE' });
            toast.success('Certificazione eliminata');
            fetchCerts();
        } catch {
            toast.error('Errore nell\'eliminazione');
        }
    };

    const handleDownload = (certId, e) => {
        e.stopPropagation();
        const backendUrl = process.env.REACT_APP_BACKEND_URL;
        window.open(`${backendUrl}/api/certificazioni/${certId}/fascicolo-pdf`, '_blank');
    };

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="certificazioni-page">
                <div className="flex items-center justify-between">
                    <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Certificazioni CE</h1>
                    <Button data-testid="btn-new-cert" onClick={() => navigate('/certificazioni/new')} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                        <Plus className="h-4 w-4 mr-2" /> Nuova Certificazione
                    </Button>
                </div>

                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <Select value={statusFilter} onValueChange={setStatusFilter}>
                            <SelectTrigger data-testid="filter-status" className="w-[180px]">
                                <SelectValue placeholder="Stato" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Tutti gli stati</SelectItem>
                                <SelectItem value="bozza">Bozza</SelectItem>
                                <SelectItem value="emessa">Emessa</SelectItem>
                                <SelectItem value="revisionata">Revisionata</SelectItem>
                            </SelectContent>
                        </Select>
                    </CardContent>
                </Card>

                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Progetto</TableHead>
                                    <TableHead className="text-white font-semibold">Norma</TableHead>
                                    <TableHead className="text-white font-semibold">Tipo Prodotto</TableHead>
                                    <TableHead className="text-white font-semibold">N. DOP</TableHead>
                                    <TableHead className="text-white font-semibold">Cliente</TableHead>
                                    <TableHead className="text-white font-semibold">Stato</TableHead>
                                    <TableHead className="w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow><TableCell colSpan={7} className="text-center py-8"><div className="w-6 h-6 loading-spinner mx-auto" /></TableCell></TableRow>
                                ) : certs.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center py-12 text-slate-500">
                                            <Shield className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                                            <p>Nessuna certificazione trovata</p>
                                            <Button className="mt-4 bg-[#0055FF] text-white hover:bg-[#0044CC]" onClick={() => navigate('/certificazioni/new')}>
                                                <Plus className="h-4 w-4 mr-2" /> Crea la prima certificazione
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ) : certs.map((c) => {
                                    const st = STATUS_MAP[c.status] || STATUS_MAP.bozza;
                                    return (
                                        <TableRow key={c.cert_id} data-testid={`cert-row-${c.cert_id}`} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/certificazioni/${c.cert_id}`)}>
                                            <TableCell className="font-medium">{c.project_name}</TableCell>
                                            <TableCell><Badge variant="outline" className="font-mono">{c.standard}</Badge></TableCell>
                                            <TableCell>{c.product_type || '-'}</TableCell>
                                            <TableCell className="font-mono text-sm text-[#0055FF]">{c.declaration_number}</TableCell>
                                            <TableCell>{c.client_name || '-'}</TableCell>
                                            <TableCell><Badge className={st.color}>{st.label}</Badge></TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                        <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/certificazioni/${c.cert_id}`); }}>
                                                            <Edit className="h-4 w-4 mr-2" /> Modifica
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={(e) => handleDownload(c.cert_id, e)}>
                                                            <FileDown className="h-4 w-4 mr-2" /> Scarica PDF
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem className="text-red-600" onClick={(e) => handleDelete(c.cert_id, e)}>
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
