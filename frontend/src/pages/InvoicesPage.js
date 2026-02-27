/**
 * Invoices List Page - Lista Fatture
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
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
    Search,
    MoreHorizontal,
    FileText,
    Download,
    RefreshCw,
    Trash2,
    Eye,
    FileCode,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const DOC_TYPES = {
    FT: { label: 'Fattura', color: 'bg-blue-100 text-blue-800' },
    PRV: { label: 'Preventivo', color: 'bg-purple-100 text-purple-800' },
    DDT: { label: 'DDT', color: 'bg-orange-100 text-orange-800' },
    NC: { label: 'Nota Credito', color: 'bg-red-100 text-red-800' },
};

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-slate-100 text-slate-800' },
    emessa: { label: 'Emessa', color: 'bg-blue-100 text-blue-800' },
    inviata_sdi: { label: 'Inviata SDI', color: 'bg-yellow-100 text-yellow-800' },
    accettata: { label: 'Accettata', color: 'bg-green-100 text-green-800' },
    rifiutata: { label: 'Rifiutata', color: 'bg-red-100 text-red-800' },
    pagata: { label: 'Pagata', color: 'bg-emerald-100 text-emerald-800' },
    scaduta: { label: 'Scaduta', color: 'bg-orange-100 text-orange-800' },
    annullata: { label: 'Annullata', color: 'bg-gray-100 text-gray-500' },
};

const formatCurrency = (value) => {
    return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency: 'EUR',
    }).format(value || 0);
};

export default function InvoicesPage() {
    const navigate = useNavigate();
    const [invoices, setInvoices] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        document_type: '',
        status: '',
        year: new Date().getFullYear().toString(),
    });

    const fetchInvoices = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (filters.document_type) params.append('document_type', filters.document_type);
            if (filters.status) params.append('status', filters.status);
            if (filters.year) params.append('year', filters.year);
            
            const data = await apiRequest(`/invoices/?${params}`);
            setInvoices(data.invoices);
            setTotal(data.total);
        } catch (error) {
            toast.error('Errore nel caricamento documenti');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInvoices();
    }, [filters]);

    const handleDownloadPDF = async (invoice) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/invoices/${invoice.invoice_id}/pdf`,
                { credentials: 'include' }
            );
            if (!response.ok) throw new Error('Errore download');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${invoice.document_number}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch (error) {
            toast.error('Errore nel download del PDF');
        }
    };

    const handleDownloadXML = async (invoice) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/invoices/${invoice.invoice_id}/xml`,
                { credentials: 'include' }
            );
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Errore download');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${invoice.document_number}.xml`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('XML scaricato');
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleConvert = async (invoice, targetType) => {
        try {
            await apiRequest('/invoices/convert', {
                method: 'POST',
                body: JSON.stringify({
                    target_type: targetType,
                    source_ids: [invoice.invoice_id],
                }),
            });
            toast.success(`Documento convertito in ${DOC_TYPES[targetType]?.label}`);
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleDelete = async (invoice) => {
        if (!confirm('Sei sicuro di voler eliminare questo documento?')) return;
        try {
            await apiRequest(`/invoices/${invoice.invoice_id}`, {
                method: 'DELETE',
            });
            toast.success('Documento eliminato');
            fetchInvoices();
        } catch (error) {
            toast.error(error.message);
        }
    };

    const years = Array.from({ length: 5 }, (_, i) => 
        (new Date().getFullYear() - i).toString()
    );

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-serif text-3xl font-bold text-slate-900">
                            Fatturazione
                        </h1>
                        <p className="text-slate-600">
                            {total} document{total !== 1 ? 'i' : 'o'}
                        </p>
                    </div>
                    <Button
                        data-testid="btn-new-invoice"
                        onClick={() => navigate('/invoices/new')}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Nuovo Documento
                    </Button>
                </div>

                {/* Filters */}
                <Card className="border-slate-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-4">
                            <Select
                                value={filters.document_type || "all"}
                                onValueChange={(v) => setFilters(f => ({ ...f, document_type: v === "all" ? "" : v }))}
                            >
                                <SelectTrigger data-testid="filter-type" className="w-[180px]">
                                    <SelectValue placeholder="Tipo documento" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti i tipi</SelectItem>
                                    <SelectItem value="FT">Fattura</SelectItem>
                                    <SelectItem value="PRV">Preventivo</SelectItem>
                                    <SelectItem value="DDT">DDT</SelectItem>
                                    <SelectItem value="NC">Nota di Credito</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select
                                value={filters.status || "all"}
                                onValueChange={(v) => setFilters(f => ({ ...f, status: v === "all" ? "" : v }))}
                            >
                                <SelectTrigger data-testid="filter-status" className="w-[180px]">
                                    <SelectValue placeholder="Stato" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti gli stati</SelectItem>
                                    <SelectItem value="bozza">Bozza</SelectItem>
                                    <SelectItem value="emessa">Emessa</SelectItem>
                                    <SelectItem value="inviata_sdi">Inviata SDI</SelectItem>
                                    <SelectItem value="pagata">Pagata</SelectItem>
                                    <SelectItem value="scaduta">Scaduta</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select
                                value={filters.year}
                                onValueChange={(v) => setFilters(f => ({ ...f, year: v }))}
                            >
                                <SelectTrigger data-testid="filter-year" className="w-[120px]">
                                    <SelectValue placeholder="Anno" />
                                </SelectTrigger>
                                <SelectContent>
                                    {years.map(y => (
                                        <SelectItem key={y} value={y}>{y}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-slate-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-50">
                                    <TableHead className="font-semibold">Numero</TableHead>
                                    <TableHead className="font-semibold">Tipo</TableHead>
                                    <TableHead className="font-semibold">Cliente</TableHead>
                                    <TableHead className="font-semibold">Data</TableHead>
                                    <TableHead className="font-semibold">Scadenza</TableHead>
                                    <TableHead className="font-semibold text-right">Totale</TableHead>
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
                                ) : invoices.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-8 text-slate-500">
                                            Nessun documento trovato
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    invoices.map((inv) => (
                                        <TableRow
                                            key={inv.invoice_id}
                                            data-testid={`invoice-row-${inv.invoice_id}`}
                                            className="hover:bg-slate-50 cursor-pointer"
                                            onClick={() => navigate(`/invoices/${inv.invoice_id}`)}
                                        >
                                            <TableCell className="font-mono font-medium">
                                                {inv.document_number}
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={DOC_TYPES[inv.document_type]?.color}>
                                                    {DOC_TYPES[inv.document_type]?.label}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>{inv.client_name}</TableCell>
                                            <TableCell>{formatDateIT(inv.issue_date)}</TableCell>
                                            <TableCell>
                                                {inv.due_date ? formatDateIT(inv.due_date) : '-'}
                                            </TableCell>
                                            <TableCell className="text-right font-medium">
                                                {formatCurrency(inv.totals?.total_document)}
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={STATUS_BADGES[inv.status]?.color}>
                                                    {STATUS_BADGES[inv.status]?.label}
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
                                                                navigate(`/invoices/${inv.invoice_id}`);
                                                            }}
                                                        >
                                                            <Eye className="mr-2 h-4 w-4" />
                                                            Visualizza
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDownloadPDF(inv);
                                                            }}
                                                        >
                                                            <Download className="mr-2 h-4 w-4" />
                                                            Scarica PDF
                                                        </DropdownMenuItem>
                                                        {(inv.document_type === 'FT' || inv.document_type === 'NC') && (
                                                            <DropdownMenuItem
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleDownloadXML(inv);
                                                                }}
                                                            >
                                                                <FileCode className="mr-2 h-4 w-4" />
                                                                Esporta XML
                                                            </DropdownMenuItem>
                                                        )}
                                                        <DropdownMenuSeparator />
                                                        {inv.document_type === 'PRV' && (
                                                            <DropdownMenuItem
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleConvert(inv, 'FT');
                                                                }}
                                                            >
                                                                <RefreshCw className="mr-2 h-4 w-4" />
                                                                Converti in Fattura
                                                            </DropdownMenuItem>
                                                        )}
                                                        {inv.document_type === 'DDT' && (
                                                            <DropdownMenuItem
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleConvert(inv, 'FT');
                                                                }}
                                                            >
                                                                <RefreshCw className="mr-2 h-4 w-4" />
                                                                Converti in Fattura
                                                            </DropdownMenuItem>
                                                        )}
                                                        {inv.status === 'bozza' && (
                                                            <>
                                                                <DropdownMenuSeparator />
                                                                <DropdownMenuItem
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleDelete(inv);
                                                                    }}
                                                                    className="text-red-600"
                                                                >
                                                                    <Trash2 className="mr-2 h-4 w-4" />
                                                                    Elimina
                                                                </DropdownMenuItem>
                                                            </>
                                                        )}
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
