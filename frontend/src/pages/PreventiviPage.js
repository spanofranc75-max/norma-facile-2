/**
 * Preventivi Page - Lista Preventivi Commerciali
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { toast } from 'sonner';
import { Plus, FileText, Trash2, CheckCircle2, XCircle, Minus } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const STATUS_MAP = {
    bozza: { label: 'Bozza', color: 'bg-yellow-100 text-yellow-800' },
    inviato: { label: 'Inviato', color: 'bg-blue-100 text-blue-800' },
    accettato: { label: 'Accettato', color: 'bg-emerald-100 text-emerald-800' },
    rifiutato: { label: 'Rifiutato', color: 'bg-red-100 text-red-800' },
};

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

function InvoicingProgressBar({ progress }) {
    if (!progress || progress <= 0) return <span className="text-xs text-slate-400">-</span>;
    const isComplete = progress >= 100;
    return (
        <div className="flex items-center gap-2 min-w-[100px]" data-testid="invoicing-progress">
            <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                <div
                    className={`h-1.5 rounded-full transition-all ${isComplete ? 'bg-emerald-500' : 'bg-[#0055FF]'}`}
                    style={{ width: `${Math.min(progress, 100)}%` }}
                />
            </div>
            <span className={`text-[10px] font-mono font-semibold ${isComplete ? 'text-emerald-600' : 'text-[#0055FF]'}`}>{Math.round(progress)}%</span>
        </div>
    );
}

export default function PreventiviPage() {
    const navigate = useNavigate();
    const [preventivi, setPreventivi] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetch_ = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/preventivi/');
            setPreventivi(data.preventivi || []);
        } catch (e) { console.error(e); } finally { setLoading(false); }
    }, []);

    useEffect(() => { fetch_(); }, [fetch_]);

    const handleDelete = async (id) => {
        if (!window.confirm('Eliminare questo preventivo?')) return;
        try {
            await apiRequest(`/preventivi/${id}`, { method: 'DELETE' });
            toast.success('Preventivo eliminato');
            fetch_();
        } catch (e) { toast.error(e.message); }
    };

    const ComplianceBadge = ({ status }) => {
        if (status === true) return <Badge data-testid="compliance-ok" className="bg-emerald-100 text-emerald-800"><CheckCircle2 className="h-3 w-3 mr-1" />Ecobonus OK</Badge>;
        if (status === false) return <Badge data-testid="compliance-fail" className="bg-red-100 text-red-800"><XCircle className="h-3 w-3 mr-1" />Non conforme</Badge>;
        return <Badge className="bg-slate-100 text-slate-500"><Minus className="h-3 w-3 mr-1" />N/D</Badge>;
    };

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="preventivi-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Preventivi</h1>
                        <p className="text-sm text-slate-500 mt-1">{preventivi.length} preventivi</p>
                    </div>
                    <Button data-testid="btn-new-preventivo" onClick={() => navigate('/preventivi/new')} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                        <Plus className="h-4 w-4 mr-2" /> Nuovo Preventivo
                    </Button>
                </div>

                <Card className="border-gray-200">
                    <CardHeader className="bg-[#1E293B] py-3 px-5 rounded-t-lg">
                        <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                            <FileText className="h-4 w-4" /> Preventivi ({preventivi.length})
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        {loading ? (
                            <div className="flex items-center justify-center py-12"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                        ) : preventivi.length === 0 ? (
                            <EmptyState
                                type="preventivi"
                                title="Nessun preventivo ancora"
                                description="Crea il tuo primo preventivo con controllo conformità integrato e converti direttamente in fattura."
                                actionLabel="Crea il primo Preventivo"
                                onAction={() => navigate('/preventivi/new')}
                            />
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-slate-50">
                                        <TableHead className="font-semibold text-[#1E293B]">Numero</TableHead>
                                        <TableHead className="font-semibold text-[#1E293B]">Cliente</TableHead>
                                        <TableHead className="font-semibold text-[#1E293B]">Oggetto</TableHead>
                                        <TableHead className="text-right font-semibold text-[#1E293B]">Totale</TableHead>
                                        <TableHead className="font-semibold text-[#1E293B]">Compliance</TableHead>
                                        <TableHead className="font-semibold text-[#1E293B]">Stato</TableHead>
                                        <TableHead className="w-16"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {preventivi.map(p => {
                                        const st = STATUS_MAP[p.status] || STATUS_MAP.bozza;
                                        return (
                                            <TableRow key={p.preventivo_id} data-testid={`prev-row-${p.preventivo_id}`} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/preventivi/${p.preventivo_id}`)}>
                                                <TableCell className="font-mono text-sm text-[#0055FF] font-medium">{p.number}</TableCell>
                                                <TableCell className="text-sm">{p.client_name || '-'}</TableCell>
                                                <TableCell className="text-sm text-slate-600 max-w-[200px] truncate">{p.subject || '-'}</TableCell>
                                                <TableCell className="text-right font-mono font-semibold text-sm">{fmtEur(p.totals?.total)}</TableCell>
                                                <TableCell><ComplianceBadge status={p.compliance_status} /></TableCell>
                                                <TableCell><Badge className={st.color + ' text-xs'}>{st.label}</Badge></TableCell>
                                                <TableCell>
                                                    <button onClick={(e) => { e.stopPropagation(); handleDelete(p.preventivo_id); }} className="p-1.5 text-slate-400 hover:text-red-500">
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </button>
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
