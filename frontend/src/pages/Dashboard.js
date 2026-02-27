/**
 * Cruscotto Officina - Workshop Dashboard for Metalworkers
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Scale, HardHat, FileText, Euro, Plus, ArrowRight,
    Ruler, ClipboardList, Calendar, Package, Receipt, Clock,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-yellow-100 text-yellow-800' },
    emessa: { label: 'Emessa', color: 'bg-blue-100 text-blue-800' },
    pagata: { label: 'Pagata', color: 'bg-emerald-100 text-emerald-800' },
    scaduta: { label: 'Scaduta', color: 'bg-orange-100 text-orange-800' },
};

export default function Dashboard() {
    const { user, loading } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [stats, setStats] = useState(null);
    const [loadingStats, setLoadingStats] = useState(true);
    const currentUser = user || location.state?.user;

    useEffect(() => {
        if (!currentUser) return;
        const fetchStats = async () => {
            try {
                const data = await apiRequest('/dashboard/stats');
                setStats(data);
            } catch (e) {
                console.error('Dashboard stats error:', e);
            } finally {
                setLoadingStats(false);
            }
        };
        fetchStats();
    }, [currentUser]);

    if ((loading && !location.state?.user) || !currentUser) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                </div>
            </DashboardLayout>
        );
    }

    const kpis = [
        {
            label: 'Ferro in Lavorazione',
            value: loadingStats ? '-' : `${(stats?.ferro_kg || 0).toLocaleString('it-IT')} kg`,
            sub: `${stats?.distinte_attive || 0} distinte attive`,
            icon: Scale,
            color: 'text-[#0055FF]',
            bg: 'bg-blue-50',
            testId: 'kpi-ferro',
        },
        {
            label: 'Cantieri Attivi',
            value: loadingStats ? '-' : String(stats?.cantieri_attivi || 0),
            sub: 'POS in corso',
            icon: HardHat,
            color: 'text-amber-600',
            bg: 'bg-amber-50',
            testId: 'kpi-cantieri',
        },
        {
            label: 'POS Generati',
            value: loadingStats ? '-' : String(stats?.pos_mese || 0),
            sub: 'questo mese',
            icon: FileText,
            color: 'text-emerald-600',
            bg: 'bg-emerald-50',
            testId: 'kpi-pos',
        },
        {
            label: 'Fatturato Mese',
            value: loadingStats ? '-' : formatCurrency(stats?.fatturato_mese),
            sub: 'emesso + incassato',
            icon: Euro,
            color: 'text-[#0055FF]',
            bg: 'bg-blue-50',
            testId: 'kpi-fatturato',
        },
    ];

    const quickActions = [
        { label: 'Nuovo Rilievo', icon: Ruler, path: '/rilievi', testId: 'qa-rilievo' },
        { label: 'Nuova Distinta', icon: Scale, path: '/distinte/new', testId: 'qa-distinta' },
        { label: 'Stampa POS', icon: ClipboardList, path: '/sicurezza', testId: 'qa-pos' },
    ];

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="workshop-dashboard">
                {/* Header */}
                <div>
                    <h1 className="font-sans text-2xl font-bold text-[#1E293B]">
                        Bentornato, {currentUser.name?.split(' ')[0]}
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">Cruscotto Officina</p>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {kpis.map((k) => (
                        <Card key={k.testId} data-testid={k.testId} className="border-gray-200">
                            <CardContent className="pt-5 pb-4 px-5">
                                <div className="flex items-start justify-between">
                                    <div className="min-w-0">
                                        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{k.label}</p>
                                        <p className={`text-2xl font-mono font-bold mt-1 ${k.color} truncate`}>{k.value}</p>
                                        <p className="text-xs text-slate-400 mt-1">{k.sub}</p>
                                    </div>
                                    <div className={`w-10 h-10 flex items-center justify-center rounded-lg shrink-0 ${k.bg}`}>
                                        <k.icon className={`h-5 w-5 ${k.color}`} />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Quick Actions */}
                <Card className="border-gray-200" data-testid="quick-actions">
                    <CardHeader className="bg-[#1E293B] py-3 px-5 rounded-t-lg">
                        <CardTitle className="text-sm font-semibold text-white">Azioni Rapide</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4">
                        <div className="grid grid-cols-3 gap-3">
                            {quickActions.map((a) => (
                                <Button
                                    key={a.testId}
                                    data-testid={a.testId}
                                    onClick={() => navigate(a.path)}
                                    className="h-auto py-4 bg-[#0055FF] text-white hover:bg-[#0044CC] flex flex-col items-center gap-2"
                                >
                                    <a.icon className="h-5 w-5" />
                                    <span className="text-xs font-medium">{a.label}</span>
                                </Button>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Widgets Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Prossime Scadenze */}
                    <Card className="border-gray-200" data-testid="widget-scadenze">
                        <CardHeader className="bg-blue-50 border-b border-gray-200 py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                <Calendar className="h-4 w-4 text-[#0055FF]" /> Prossime Scadenze
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingStats ? (
                                <div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                            ) : (stats?.scadenze || []).length === 0 ? (
                                <div className="text-center py-8 text-slate-400 text-sm">
                                    <Calendar className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                    Nessuna scadenza imminente
                                </div>
                            ) : (
                                <div className="divide-y divide-gray-100">
                                    {stats.scadenze.map((s, i) => (
                                        <div key={i} className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/sicurezza/${s.pos_id}`)}>
                                            <div>
                                                <p className="text-sm font-medium text-[#1E293B]">{s.project_name}</p>
                                                <p className="text-xs text-slate-400">{s.city}</p>
                                            </div>
                                            <Badge className="bg-amber-100 text-amber-800 font-mono text-xs">{s.deadline}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Materiale da Ordinare */}
                    <Card className="border-gray-200" data-testid="widget-materiale">
                        <CardHeader className="bg-blue-50 border-b border-gray-200 py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                <Package className="h-4 w-4 text-[#0055FF]" /> Materiale da Ordinare
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingStats ? (
                                <div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                            ) : (stats?.materiale || []).length === 0 ? (
                                <div className="text-center py-8 text-slate-400 text-sm">
                                    <Package className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                    Nessun materiale da ordinare
                                </div>
                            ) : (
                                <div className="divide-y divide-gray-100">
                                    {stats.materiale.map((m, i) => (
                                        <div key={i} className="flex items-center justify-between px-5 py-3">
                                            <p className="text-sm text-[#1E293B]">{m.profile}</p>
                                            <div className="flex items-center gap-3">
                                                <span className="text-xs text-slate-400">{m.total_m} m</span>
                                                <Badge className="bg-blue-100 text-[#0055FF] font-mono">{m.bars} barre</Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Documenti Recenti */}
                <Card className="border-gray-200" data-testid="widget-fatture">
                    <CardHeader className="flex flex-row items-center justify-between bg-blue-50 border-b border-gray-200 py-3 px-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <Receipt className="h-4 w-4 text-[#0055FF]" /> Documenti Recenti
                        </CardTitle>
                        <Button variant="ghost" size="sm" onClick={() => navigate('/invoices')} className="text-[#0055FF] hover:text-[#0044CC] text-xs h-7">
                            Vedi tutti <ArrowRight className="h-3 w-3 ml-1" />
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        {loadingStats ? (
                            <div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                        ) : (stats?.recent_invoices || []).length === 0 ? (
                            <div className="text-center py-8">
                                <Receipt className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                <p className="text-sm text-slate-400">Nessun documento ancora</p>
                                <Button data-testid="btn-new-invoice" className="mt-3 bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs h-8" onClick={() => navigate('/invoices/new')}>
                                    <Plus className="h-3 w-3 mr-1" /> Nuova Fattura
                                </Button>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {stats.recent_invoices.map((inv) => {
                                    const st = STATUS_BADGES[inv.status] || STATUS_BADGES.bozza;
                                    return (
                                        <div
                                            key={inv.invoice_id}
                                            data-testid={`recent-inv-${inv.invoice_id}`}
                                            className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 cursor-pointer"
                                            onClick={() => navigate(`/invoices/${inv.invoice_id}`)}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 flex items-center justify-center bg-slate-100 rounded">
                                                    <Receipt className="h-4 w-4 text-slate-500" />
                                                </div>
                                                <div>
                                                    <p className="text-sm font-mono font-medium text-[#1E293B]">{inv.document_number}</p>
                                                    <p className="text-xs text-slate-400">{inv.client_name}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="font-mono font-semibold text-sm text-[#0055FF]">
                                                    {formatCurrency(inv.totals?.total_document)}
                                                </span>
                                                <Badge className={st.color + ' text-xs'}>{st.label}</Badge>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
