/**
 * MatriceScadenzePage — Matrice scadenze aziendale.
 * Righe = operai, Colonne = tipo attestato.
 * Celle colorate: verde (valido), giallo (in scadenza), rosso (scaduto), grigio (mancante).
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
    Shield, AlertTriangle, CheckCircle, Clock, X as XIcon, Search, Users, Loader2, ArrowLeft,
} from 'lucide-react';

const STATUS_COLORS = {
    valido: 'bg-emerald-500',
    in_scadenza: 'bg-amber-400',
    scaduto: 'bg-red-500',
    mancante: 'bg-slate-300',
};

const STATUS_LABELS = {
    valido: 'Valido',
    in_scadenza: 'In scadenza',
    scaduto: 'Scaduto',
    mancante: 'Mancante',
};

function CellDot({ cell }) {
    const color = STATUS_COLORS[cell.status] || 'bg-slate-300';
    const title = cell.expiry
        ? `${STATUS_LABELS[cell.status]} — scade ${cell.expiry}${cell.days !== null ? ` (${cell.days}gg)` : ''}`
        : STATUS_LABELS[cell.status];

    return (
        <div className="flex items-center justify-center" title={title}>
            <div className={`w-4 h-4 rounded-full ${color} transition-transform hover:scale-125 cursor-pointer`} />
        </div>
    );
}

export default function MatriceScadenzePage() {
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');

    useEffect(() => {
        const load = async () => {
            try {
                const res = await apiRequest('/welders/matrice-scadenze');
                setData(res);
            } catch (e) {
                toast.error('Errore caricamento matrice');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex justify-center items-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    const certTypes = data?.cert_types || [];
    let workers = data?.workers || [];
    if (searchQ.trim()) {
        const q = searchQ.toLowerCase();
        workers = workers.filter(w => w.name.toLowerCase().includes(q) || w.stamp_id.toLowerCase().includes(q));
    }

    // Stats
    const totalWorkers = workers.length;
    const canGo = workers.filter(w => w.can_go_to_cantiere).length;
    const blocked = totalWorkers - canGo;
    const totalExpired = workers.reduce((acc, w) => {
        return acc + Object.values(w.cells).filter(c => c.status === 'scaduto').length;
    }, 0);
    const totalMissing = workers.reduce((acc, w) => {
        return acc + Object.values(w.cells).filter(c => c.status === 'mancante').length;
    }, 0);

    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="matrice-scadenze-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="outline" size="sm" onClick={() => navigate('/operai')} data-testid="btn-back-operai">
                            <ArrowLeft className="w-4 h-4 mr-1" /> Anagrafica
                        </Button>
                        <div>
                            <h1 className="font-sans text-2xl font-bold text-slate-900 flex items-center gap-2">
                                <Shield className="w-6 h-6 text-[#0055FF]" />
                                Matrice Scadenze Aziendale
                            </h1>
                            <p className="text-sm text-slate-500">Vista immediata della compliance di tutto il personale</p>
                        </div>
                    </div>
                </div>

                {/* Stats bar */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="matrice-stats">
                    <Card className="border-slate-200">
                        <CardContent className="pt-3 pb-2 px-4">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center">
                                    <Users className="w-4 h-4 text-slate-600" />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-slate-800">{totalWorkers}</p>
                                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Operai</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="border-emerald-200">
                        <CardContent className="pt-3 pb-2 px-4">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-emerald-700">{canGo}</p>
                                    <p className="text-[10px] text-emerald-600 uppercase tracking-wider">Idonei cantiere</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="border-red-200">
                        <CardContent className="pt-3 pb-2 px-4">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
                                    <AlertTriangle className="w-4 h-4 text-red-600" />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-red-700">{totalExpired}</p>
                                    <p className="text-[10px] text-red-600 uppercase tracking-wider">Scaduti</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="border-amber-200">
                        <CardContent className="pt-3 pb-2 px-4">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
                                    <Clock className="w-4 h-4 text-amber-600" />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-amber-700">{totalMissing}</p>
                                    <p className="text-[10px] text-amber-600 uppercase tracking-wider">Mancanti</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Legend + Search */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-xs text-slate-600">
                        <span className="font-medium text-slate-800">Legenda:</span>
                        {Object.entries(STATUS_COLORS).map(([k, c]) => (
                            <span key={k} className="flex items-center gap-1.5">
                                <div className={`w-3 h-3 rounded-full ${c}`} />
                                {STATUS_LABELS[k]}
                            </span>
                        ))}
                    </div>
                    <div className="relative w-64">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                        <Input
                            value={searchQ}
                            onChange={e => setSearchQ(e.target.value)}
                            placeholder="Cerca operaio..."
                            className="pl-8 h-8 text-sm"
                            data-testid="matrice-search"
                        />
                        {searchQ && (
                            <button onClick={() => setSearchQ('')} className="absolute right-2 top-1/2 -translate-y-1/2">
                                <XIcon className="w-3 h-3 text-slate-400" />
                            </button>
                        )}
                    </div>
                </div>

                {/* Matrix Table */}
                <Card className="border-slate-200 overflow-hidden">
                    <CardContent className="p-0">
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[900px]" data-testid="matrice-table">
                                <thead>
                                    <tr className="bg-[#1E293B]">
                                        <th className="text-left text-white text-xs font-semibold px-3 py-2.5 sticky left-0 bg-[#1E293B] z-10 w-[200px]">Operaio</th>
                                        <th className="text-center text-white text-xs font-semibold px-1 py-2.5 w-[60px]">Punzone</th>
                                        {certTypes.map(ct => (
                                            <th key={ct.code} className="text-center text-white text-[10px] font-medium px-1 py-2.5 min-w-[80px]" title={ct.label}>
                                                <div className="leading-tight">{ct.label}</div>
                                            </th>
                                        ))}
                                        <th className="text-center text-white text-xs font-semibold px-2 py-2.5 w-[80px]">Cantiere</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {workers.length === 0 ? (
                                        <tr>
                                            <td colSpan={certTypes.length + 3} className="text-center py-12 text-slate-400">
                                                <Users className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                                                <p>Nessun operaio trovato</p>
                                            </td>
                                        </tr>
                                    ) : workers.map((w, i) => {
                                        const hasIssue = Object.values(w.cells).some(c => c.status === 'scaduto' || c.status === 'mancante');
                                        return (
                                            <tr key={w.welder_id}
                                                className={`border-b border-slate-100 transition-colors hover:bg-slate-50 ${hasIssue ? 'bg-red-50/30' : ''}`}
                                                data-testid={`matrice-row-${w.welder_id}`}>
                                                <td className="px-3 py-2 sticky left-0 bg-inherit z-10">
                                                    <button className="text-left hover:text-[#0055FF] transition-colors"
                                                        onClick={() => navigate('/operai')}>
                                                        <div className="font-medium text-sm text-slate-800">{w.name}</div>
                                                        <div className="text-[10px] text-slate-400 capitalize">{w.role || 'operaio'}</div>
                                                    </button>
                                                </td>
                                                <td className="text-center font-mono text-xs text-slate-500 px-1 py-2">{w.stamp_id}</td>
                                                {certTypes.map(ct => (
                                                    <td key={ct.code} className="text-center px-1 py-2">
                                                        <CellDot cell={w.cells[ct.code] || { status: 'mancante', days: null, expiry: null }} />
                                                    </td>
                                                ))}
                                                <td className="text-center px-2 py-2">
                                                    {w.can_go_to_cantiere ? (
                                                        <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px]">OK</Badge>
                                                    ) : (
                                                        <Badge className="bg-red-100 text-red-700 border border-red-200 text-[10px]">NO</Badge>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
