/**
 * Distinte List Page - Lista Distinte Materiali (BOM)
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
    Trash2,
    Eye,
    Package,
    Weight,
    Euro,
    Layers,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-slate-100 text-slate-800' },
    confermata: { label: 'Confermata', color: 'bg-blue-100 text-blue-800' },
    ordinata: { label: 'Ordinata', color: 'bg-amber-100 text-amber-800' },
    completata: { label: 'Completata', color: 'bg-emerald-100 text-emerald-800' },
};

const formatCurrency = (value) => {
    return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency: 'EUR',
    }).format(value || 0);
};

export default function DistintePage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const rilievoIdFilter = searchParams.get('rilievo_id');
    
    const [distinte, setDistinte] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('all');

    const fetchDistinte = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (rilievoIdFilter) params.append('rilievo_id', rilievoIdFilter);
            if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
            
            const data = await apiRequest(`/distinte/?${params}`);
            setDistinte(data.distinte);
            setTotal(data.total);
        } catch (error) {
            toast.error('Errore nel caricamento distinte');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDistinte();
    }, [statusFilter, rilievoIdFilter]);

    const handleDelete = async (distinta) => {
        if (!confirm('Sei sicuro di voler eliminare questa distinta?')) return;
        try {
            await apiRequest(`/distinte/${distinta.distinta_id}`, {
                method: 'DELETE',
            });
            toast.success('Distinta eliminata');
            fetchDistinte();
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
                            Distinte Materiali
                        </h1>
                        <p className="text-slate-600">
                            {total} distinta{total !== 1 ? 'e' : ''} 
                            {rilievoIdFilter && ' per questo rilievo'}
                        </p>
                    </div>
                    <Button
                        data-testid="btn-new-distinta"
                        onClick={() => navigate(rilievoIdFilter 
                            ? `/distinte/new?rilievo_id=${rilievoIdFilter}` 
                            : '/distinte/new'
                        )}
                        className="bg-slate-900 text-white hover:bg-slate-800"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Nuova Distinta
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
                                    <SelectItem value="confermata">Confermata</SelectItem>
                                    <SelectItem value="ordinata">Ordinata</SelectItem>
                                    <SelectItem value="completata">Completata</SelectItem>
                                </SelectContent>
                            </Select>
                            
                            {rilievoIdFilter && (
                                <Button
                                    variant="outline"
                                    onClick={() => navigate('/distinte')}
                                >
                                    Mostra tutte
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
                                    <TableHead className="font-semibold">Nome</TableHead>
                                    <TableHead className="font-semibold">Rilievo</TableHead>
                                    <TableHead className="font-semibold">Cliente</TableHead>
                                    <TableHead className="font-semibold text-center">Articoli</TableHead>
                                    <TableHead className="font-semibold text-right">Peso (kg)</TableHead>
                                    <TableHead className="font-semibold text-right">Costo</TableHead>
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
                                ) : distinte.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-12 text-slate-500">
                                            <Package className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                                            <p>Nessuna distinta trovata</p>
                                            <Button
                                                className="mt-4 bg-slate-900 text-white hover:bg-slate-800"
                                                onClick={() => navigate('/distinte/new')}
                                            >
                                                <Plus className="h-4 w-4 mr-2" />
                                                Crea la prima distinta
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    distinte.map((distinta) => (
                                        <TableRow
                                            key={distinta.distinta_id}
                                            data-testid={`distinta-row-${distinta.distinta_id}`}
                                            className="hover:bg-slate-50 cursor-pointer"
                                            onClick={() => navigate(`/distinte/${distinta.distinta_id}`)}
                                        >
                                            <TableCell className="font-medium">
                                                {distinta.name}
                                            </TableCell>
                                            <TableCell>
                                                {distinta.rilievo_name || '-'}
                                            </TableCell>
                                            <TableCell>
                                                {distinta.client_name || '-'}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Badge variant="outline" className="gap-1">
                                                    <Layers className="h-3 w-3" />
                                                    {distinta.totals?.total_items || 0}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-1 text-slate-600">
                                                    <Weight className="h-3 w-3" />
                                                    {distinta.totals?.total_weight_kg?.toFixed(2) || '0.00'}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right font-medium">
                                                {formatCurrency(distinta.totals?.total_cost)}
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={STATUS_BADGES[distinta.status]?.color}>
                                                    {STATUS_BADGES[distinta.status]?.label}
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
                                                                navigate(`/distinte/${distinta.distinta_id}`);
                                                            }}
                                                        >
                                                            <Eye className="mr-2 h-4 w-4" />
                                                            Apri
                                                        </DropdownMenuItem>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDelete(distinta);
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
