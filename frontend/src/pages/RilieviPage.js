/**
 * Rilievi List Page - Lista Sopralluoghi
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { toast } from 'sonner';
import {
    Plus,
    MoreHorizontal,
    Download,
    Trash2,
    Eye,
    Ruler,
    Camera,
    MapPin,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-slate-100 text-slate-800' },
    completato: { label: 'Completato', color: 'bg-emerald-100 text-emerald-800' },
    archiviato: { label: 'Archiviato', color: 'bg-gray-100 text-gray-500' },
};

export default function RilieviPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const clientIdFilter = searchParams.get('client_id');
    
    const [rilievi, setRilievi] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('all');

    const fetchRilievi = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (clientIdFilter) params.append('client_id', clientIdFilter);
            if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
            
            const data = await apiRequest(`/rilievi/?${params}`);
            setRilievi(data.rilievi);
            setTotal(data.total);
        } catch (error) {
            toast.error('Errore nel caricamento rilievi');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRilievi();
    }, [statusFilter, clientIdFilter]);

    const handleDownloadPDF = async (rilievo) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/rilievi/${rilievo.rilievo_id}/pdf`,
                { credentials: 'include' }
            );
            if (!response.ok) throw new Error('Errore download');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Rilievo_${rilievo.project_name.replace(/\s+/g, '_')}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch (error) {
            toast.error('Errore nel download del PDF');
        }
    };

    const handleDelete = async (rilievo) => {
        if (!confirm('Sei sicuro di voler eliminare questo rilievo?')) return;
        try {
            await apiRequest(`/rilievi/${rilievo.rilievo_id}`, {
                method: 'DELETE',
            });
            toast.success('Rilievo eliminato');
            fetchRilievi();
        } catch (error) {
            toast.error(error.message);
        }
    };

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-serif text-3xl font-bold text-slate-900">
                            Rilievi Misure
                        </h1>
                        <p className="text-slate-600">
                            {total} rilievo{total !== 1 ? 'i' : ''} 
                            {clientIdFilter && ' per questo cliente'}
                        </p>
                    </div>
                    <Button
                        data-testid="btn-new-rilievo"
                        onClick={() => navigate(clientIdFilter 
                            ? `/rilievi/new?client_id=${clientIdFilter}` 
                            : '/rilievi/new'
                        )}
                        className="bg-slate-900 text-white hover:bg-slate-800"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Nuovo Rilievo
                    </Button>
                </div>

                {/* Filters */}
                <Card className="border-slate-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-4">
                            <Select
                                value={statusFilter}
                                onValueChange={setStatusFilter}
                            >
                                <SelectTrigger data-testid="filter-status" className="w-[180px]">
                                    <SelectValue placeholder="Stato" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti gli stati</SelectItem>
                                    <SelectItem value="bozza">Bozza</SelectItem>
                                    <SelectItem value="completato">Completato</SelectItem>
                                    <SelectItem value="archiviato">Archiviato</SelectItem>
                                </SelectContent>
                            </Select>
                            
                            {clientIdFilter && (
                                <Button
                                    variant="outline"
                                    onClick={() => navigate('/rilievi')}
                                >
                                    Mostra tutti
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-slate-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-50">
                                    <TableHead className="font-semibold">Progetto</TableHead>
                                    <TableHead className="font-semibold">Cliente</TableHead>
                                    <TableHead className="font-semibold">Data</TableHead>
                                    <TableHead className="font-semibold">Località</TableHead>
                                    <TableHead className="font-semibold text-center">Schizzi</TableHead>
                                    <TableHead className="font-semibold text-center">Foto</TableHead>
                                    <TableHead className="font-semibold">Stato</TableHead>
                                    <TableHead className="w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-8">
                                            <div className="w-6 h-6 loading-spinner mx-auto" />
                                        </TableCell>
                                    </TableRow>
                                ) : rilievi.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-12 text-slate-500">
                                            <Ruler className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                                            <p>Nessun rilievo trovato</p>
                                            <Button
                                                className="mt-4 bg-slate-900 text-white hover:bg-slate-800"
                                                onClick={() => navigate('/rilievi/new')}
                                            >
                                                <Plus className="h-4 w-4 mr-2" />
                                                Crea il primo rilievo
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    rilievi.map((rilievo) => (
                                        <TableRow
                                            key={rilievo.rilievo_id}
                                            data-testid={`rilievo-row-${rilievo.rilievo_id}`}
                                            className="hover:bg-slate-50 cursor-pointer"
                                            onClick={() => navigate(`/rilievi/${rilievo.rilievo_id}`)}
                                        >
                                            <TableCell className="font-medium">
                                                {rilievo.project_name}
                                            </TableCell>
                                            <TableCell>{rilievo.client_name}</TableCell>
                                            <TableCell>{formatDateIT(rilievo.survey_date)}</TableCell>
                                            <TableCell>
                                                {rilievo.location ? (
                                                    <div className="flex items-center gap-1 text-slate-600">
                                                        <MapPin className="h-3 w-3" />
                                                        <span className="truncate max-w-[150px]">
                                                            {rilievo.location}
                                                        </span>
                                                    </div>
                                                ) : '-'}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Badge variant="outline" className="gap-1">
                                                    <Ruler className="h-3 w-3" />
                                                    {rilievo.sketches?.length || 0}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Badge variant="outline" className="gap-1">
                                                    <Camera className="h-3 w-3" />
                                                    {rilievo.photos?.length || 0}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={STATUS_BADGES[rilievo.status]?.color}>
                                                    {STATUS_BADGES[rilievo.status]?.label}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                        <Button variant="ghost" size="sm">
                                                            <MoreHorizontal className="h-4 w-4" />
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                navigate(`/rilievi/${rilievo.rilievo_id}`);
                                                            }}
                                                        >
                                                            <Eye className="mr-2 h-4 w-4" />
                                                            Apri
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDownloadPDF(rilievo);
                                                            }}
                                                        >
                                                            <Download className="mr-2 h-4 w-4" />
                                                            Scarica PDF
                                                        </DropdownMenuItem>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDelete(rilievo);
                                                            }}
                                                            className="text-red-600"
                                                        >
                                                            <Trash2 className="mr-2 h-4 w-4" />
                                                            Elimina
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
