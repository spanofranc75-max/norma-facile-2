/**
 * Cruscotto Officina — Workshop Dashboard for Metalworkers
 * Upgraded: Gradient KPIs, Recharts bar chart, FAB quick-actions.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
    Scale, HardHat, FileText, Euro, ArrowRight,
    Calendar, Package, Receipt, TrendingUp, AlertTriangle, CheckCircle, Clock,
    CircleAlert, Users, Truck, ClipboardCheck,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import QuickActionFAB from '../components/QuickActionFAB';
import QualityScoreWidget from '../components/QualityScoreWidget';
import ComplianceWidget from '../components/ComplianceWidget';

const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-yellow-100 text-yellow-800' },
    emessa: { label: 'Emessa', color: 'bg-blue-100 text-blue-800' },
    pagata: { label: 'Pagata', color: 'bg-emerald-100 text-emerald-800' },
    scaduta: { label: 'Scaduta', color: 'bg-orange-100 text-orange-800' },
};

const ChartTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-[#1E293B] text-white text-xs px-3 py-2 rounded-lg shadow-xl">
            <p className="font-medium mb-1">{label}</p>
            <p className="font-mono">{formatCurrency(payload[0].value)}</p>
            <p className="text-slate-400">{payload[0].payload.documenti} documenti</p>
        </div>
    );
};

export default function Dashboard() {
    const { user, loading } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [stats, setStats] = useState(null);
    const [loadingStats, setLoadingStats] = useState(true);
    const [semaforo, setSemaforo] = useState(null);
    const [briefing, setBriefing] = useState(null);
    const [alertCount, setAlertCount] = useState(0);
    const currentUser = user || location.state?.user;

    useEffect(() => {
        if (!currentUser) return;
        const fetchStats = async () => {
            try {
                const [data, sem, brief] = await Promise.all([
                    apiRequest('/dashboard/stats'),
                    apiRequest('/dashboard/semaforo').catch(() => null),
                    apiRequest('/dashboard/morning-briefing').catch(() => null),
                ]);
                setStats(data);
                setSemaforo(sem);
                setBriefing(brief);
                // Fetch officina quality alerts
                const alerts = await apiRequest(`/officina/alerts/count?admin_id=${currentUser.user_id}`).catch(() => ({ count: 0 }));
                setAlertCount(alerts.count || 0);
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
            gradient: 'from-blue-600 to-blue-400',
            testId: 'kpi-ferro',
        },
        {
            label: 'Cantieri Attivi',
            value: loadingStats ? '-' : String(stats?.cantieri_attivi || 0),
            sub: 'POS in corso',
            icon: HardHat,
            gradient: 'from-amber-500 to-amber-400',
            testId: 'kpi-cantieri',
        },
        {
            label: 'POS Generati',
            value: loadingStats ? '-' : String(stats?.pos_mese || 0),
            sub: 'questo mese',
            icon: FileText,
            gradient: 'from-emerald-600 to-emerald-400',
            testId: 'kpi-pos',
        },
        {
            label: 'Fatturato Mese',
            value: loadingStats ? '-' : formatCurrency(stats?.fatturato_mese),
            sub: 'emesso + incassato',
            icon: Euro,
            gradient: 'from-violet-600 to-violet-400',
            testId: 'kpi-fatturato',
        },
    ];

    const chartData = stats?.fatturato_mensile || [];

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="workshop-dashboard">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">
                            Bentornato, {currentUser.name?.split(' ')[0]}
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Cruscotto Officina</p>
                    </div>
                    {alertCount > 0 && (
                        <button
                            onClick={() => navigate('/notifications')}
                            className="relative flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-xl hover:bg-red-100 transition-colors"
                            data-testid="quality-alert-badge"
                        >
                            <CircleAlert className="h-5 w-5 text-red-600" />
                            <span className="text-sm font-bold text-red-700">{alertCount}</span>
                            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping" />
                            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full" />
                        </button>
                    )}
                </div>

                {/* Morning Briefing */}
                {briefing && <MorningBriefing data={briefing} navigate={navigate} />}

                {/* KPI Cards — Gradient */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {kpis.map((k) => (
                        <Card
                            key={k.testId}
                            data-testid={k.testId}
                            className={`relative overflow-hidden border-0 bg-gradient-to-r ${k.gradient} text-white shadow-lg`}
                        >
                            <CardContent className="pt-5 pb-4 px-5">
                                <div className="flex items-start justify-between">
                                    <div className="min-w-0">
                                        <p className="text-xs font-medium text-white/80 uppercase tracking-wider">{k.label}</p>
                                        <p className="text-2xl font-mono font-bold mt-1 truncate">{k.value}</p>
                                        <p className="text-xs text-white/70 mt-1">{k.sub}</p>
                                    </div>
                                    <div className="w-10 h-10 flex items-center justify-center rounded-lg shrink-0 bg-white/20 backdrop-blur-sm">
                                        <k.icon className="h-5 w-5 text-white" />
                                    </div>
                                </div>
                                {/* Decorative circle */}
                                <div className="absolute -right-4 -bottom-4 w-24 h-24 rounded-full bg-white/10" />
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Semaforo Commesse */}
                {semaforo && semaforo.total > 0 && (
                    <Card className="border-gray-200" data-testid="widget-semaforo">
                        <CardHeader className="bg-slate-50 border-b border-gray-200 py-3 px-5">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <AlertTriangle className="h-4 w-4 text-[#0055FF]" /> Stato Commesse
                                </CardTitle>
                                <div className="flex items-center gap-3">
                                    {semaforo.counts.red > 0 && <span className="flex items-center gap-1 text-xs font-medium text-red-600"><span className="w-2.5 h-2.5 rounded-full bg-red-500" />{semaforo.counts.red}</span>}
                                    {semaforo.counts.yellow > 0 && <span className="flex items-center gap-1 text-xs font-medium text-amber-600"><span className="w-2.5 h-2.5 rounded-full bg-amber-400" />{semaforo.counts.yellow}</span>}
                                    {semaforo.counts.green > 0 && <span className="flex items-center gap-1 text-xs font-medium text-emerald-600"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />{semaforo.counts.green}</span>}
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y divide-gray-100 max-h-[280px] overflow-y-auto">
                                {semaforo.items.map((c) => {
                                    const colors = {
                                        red: { bg: 'bg-red-50', border: 'border-l-red-500', text: 'text-red-700', badge: 'bg-red-100 text-red-700' },
                                        yellow: { bg: 'bg-amber-50', border: 'border-l-amber-400', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-700' },
                                        green: { bg: 'bg-emerald-50', border: 'border-l-emerald-500', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-700' },
                                    }[c.semaforo];
                                    const StatusIcon = c.semaforo === 'red' ? AlertTriangle : c.semaforo === 'yellow' ? Clock : CheckCircle;
                                    return (
                                        <div
                                            key={c.commessa_id}
                                            data-testid={`semaforo-${c.commessa_id}`}
                                            className={`flex items-center gap-3 px-4 py-3 border-l-4 ${colors.border} ${colors.bg} hover:brightness-95 cursor-pointer transition-all`}
                                            onClick={() => navigate(`/commesse/${c.commessa_id}`)}
                                        >
                                            <StatusIcon className={`h-4 w-4 shrink-0 ${colors.text}`} />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm font-medium text-[#1E293B] truncate">{c.numero || ''} {c.title}</span>
                                                </div>
                                                <p className="text-xs text-slate-500 truncate">{c.client_name || 'Nessun cliente'}</p>
                                            </div>
                                            <div className="text-right shrink-0">
                                                {c.days_left !== null && c.days_left !== undefined ? (
                                                    <Badge className={`${colors.badge} text-xs font-mono`}>
                                                        {c.days_left < 0 ? `${Math.abs(c.days_left)}gg ritardo` : c.days_left === 0 ? 'Oggi' : `${c.days_left}gg`}
                                                    </Badge>
                                                ) : (
                                                    <span className="text-xs text-slate-400">No scadenza</span>
                                                )}
                                                {c.prod_total > 0 && (
                                                    <p className="text-xs text-slate-400 mt-0.5">
                                                        {c.prod_done}/{c.prod_total} fasi
                                                        {c.fasi_in_ritardo > 0 && <span className="text-red-500 font-medium ml-1">({c.fasi_in_ritardo} in ritardo)</span>}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Fatturato Mensile Chart + Quality Score */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Chart */}
                    <Card className="lg:col-span-2 border-gray-200" data-testid="chart-fatturato">
                        <CardHeader className="pb-2 px-5 pt-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                <TrendingUp className="h-4 w-4 text-[#0055FF]" /> Fatturato Mensile
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="px-2 pb-4">
                            {loadingStats ? (
                                <div className="flex items-center justify-center h-48">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" />
                                </div>
                            ) : chartData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                                        <XAxis dataKey="mese_short" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
                                        <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                                        <Tooltip content={<ChartTooltip />} cursor={{ fill: '#F1F5F9' }} />
                                        <Bar dataKey="importo" fill="url(#barGradient)" radius={[6, 6, 0, 0]} maxBarSize={40} />
                                        <defs>
                                            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor="#3B82F6" />
                                                <stop offset="100%" stopColor="#2563EB" />
                                            </linearGradient>
                                        </defs>
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-48 text-slate-400">
                                    <TrendingUp className="h-8 w-8 mb-2 text-slate-300" />
                                    <p className="text-sm">Nessun dato di fatturato ancora</p>
                                    <p className="text-xs text-slate-400 mt-1">I dati appariranno quando emetterai fatture</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Quality Score + Compliance */}
                    <div className="space-y-6">
                        <QualityScoreWidget />
                        <ComplianceWidget />
                    </div>
                </div>

                {/* Widgets Row — 3 columns */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Prossime Scadenze */}
                    <Card className="border-gray-200" data-testid="widget-scadenze">
                        <CardHeader className="bg-slate-50 border-b border-gray-200 py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                <Calendar className="h-4 w-4 text-[#0055FF]" /> Prossime Scadenze
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingStats ? (
                                <div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                            ) : (stats?.scadenze || []).length === 0 ? (
                                <div className="text-center py-10 text-slate-400">
                                    <Calendar className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                    <p className="text-sm">Nessuna scadenza</p>
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
                        <CardHeader className="bg-slate-50 border-b border-gray-200 py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                <Package className="h-4 w-4 text-[#0055FF]" /> Materiale da Ordinare
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingStats ? (
                                <div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                            ) : (stats?.materiale || []).length === 0 ? (
                                <div className="text-center py-10 text-slate-400">
                                    <Package className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                    <p className="text-sm">Nessun materiale da ordinare</p>
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

                    {/* Documenti Recenti */}
                    <Card className="border-gray-200" data-testid="widget-fatture">
                        <CardHeader className="flex flex-row items-center justify-between bg-slate-50 border-b border-gray-200 py-3 px-5">
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
                                <div className="text-center py-10 text-slate-400">
                                    <Receipt className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                    <p className="text-sm">Nessun documento ancora</p>
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
                                                    <div className="w-8 h-8 flex items-center justify-center bg-blue-50 rounded-lg">
                                                        <Receipt className="h-4 w-4 text-[#0055FF]" />
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
            </div>

            {/* FAB */}
            <QuickActionFAB />
        </DashboardLayout>
    );
}


const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

function MorningBriefing({ data, navigate }) {
    const { scadenze_oggi_domani, totale_scadenze_oggi, totale_scadenze_domani,
            pagamenti_ritardo, totale_importo_ritardo, commesse_allarme, da_fare } = data;

    const hasSomething = scadenze_oggi_domani?.length > 0 || pagamenti_ritardo?.length > 0 ||
        commesse_allarme?.length > 0 || da_fare?.preventivi_da_convertire > 0 ||
        da_fare?.ddt_non_fatturati > 0 || da_fare?.fatture_scadute > 0;

    if (!hasSomething) return null;

    return (
        <div data-testid="morning-briefing" className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {/* Card 1: Scadenze oggi/domani */}
            <Card className="border-slate-200 overflow-hidden" data-testid="briefing-scadenze">
                <CardHeader className="py-3 px-4 bg-gradient-to-r from-red-50 to-orange-50 border-b">
                    <CardTitle className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                        <Calendar className="h-3.5 w-3.5 text-red-500" />
                        Scadenze Oggi/Domani
                        {(totale_scadenze_oggi > 0 || totale_scadenze_domani > 0) && (
                            <span className="ml-auto flex gap-1">
                                {totale_scadenze_oggi > 0 && <Badge className="bg-red-500 text-white text-[10px] px-1.5">{totale_scadenze_oggi} oggi</Badge>}
                                {totale_scadenze_domani > 0 && <Badge className="bg-orange-400 text-white text-[10px] px-1.5">{totale_scadenze_domani} domani</Badge>}
                            </span>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0 max-h-44 overflow-y-auto">
                    {scadenze_oggi_domani?.length > 0 ? scadenze_oggi_domani.map((s, i) => (
                        <div key={i} className={`flex items-center justify-between px-4 py-2 text-xs border-b border-slate-50 ${s.is_oggi ? 'bg-red-50/50' : ''}`}>
                            <div className="min-w-0">
                                <p className="font-medium text-slate-700 truncate">{s.fornitore_cliente}</p>
                                <p className="text-slate-400">{s.numero} ({s.tipo})</p>
                            </div>
                            <span className="font-mono font-semibold text-slate-800 shrink-0 ml-2">{fmtEur(s.importo)}</span>
                        </div>
                    )) : (
                        <p className="text-xs text-slate-400 text-center py-6">Nessuna scadenza oggi/domani</p>
                    )}
                </CardContent>
            </Card>

            {/* Card 2: Pagamenti in ritardo */}
            <Card className="border-slate-200 overflow-hidden" data-testid="briefing-ritardi">
                <CardHeader className="py-3 px-4 bg-gradient-to-r from-amber-50 to-yellow-50 border-b">
                    <CardTitle className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                        <CircleAlert className="h-3.5 w-3.5 text-amber-500" />
                        Clienti in Ritardo
                        {pagamenti_ritardo?.length > 0 && (
                            <Badge className="ml-auto bg-amber-500 text-white text-[10px] px-1.5">{fmtEur(totale_importo_ritardo)}</Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0 max-h-44 overflow-y-auto">
                    {pagamenti_ritardo?.length > 0 ? pagamenti_ritardo.map((p, i) => (
                        <div key={i} className="flex items-center justify-between px-4 py-2 text-xs border-b border-slate-50">
                            <div className="min-w-0">
                                <p className="font-medium text-slate-700 truncate">{p.cliente}</p>
                                <p className="text-slate-400">{p.numero}</p>
                            </div>
                            <div className="text-right shrink-0 ml-2">
                                <p className="font-mono font-semibold text-slate-800">{fmtEur(p.importo)}</p>
                                <p className="text-red-500 font-medium">{p.giorni_ritardo}gg</p>
                            </div>
                        </div>
                    )) : (
                        <p className="text-xs text-emerald-500 text-center py-6">Tutti i pagamenti in regola</p>
                    )}
                </CardContent>
            </Card>

            {/* Card 3: Commesse in allarme */}
            <Card className="border-slate-200 overflow-hidden" data-testid="briefing-allarme">
                <CardHeader className="py-3 px-4 bg-gradient-to-r from-slate-50 to-blue-50 border-b">
                    <CardTitle className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-blue-500" />
                        Commesse Ferme
                        {commesse_allarme?.length > 0 && (
                            <Badge className="ml-auto bg-blue-500 text-white text-[10px] px-1.5">{commesse_allarme.length}</Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0 max-h-44 overflow-y-auto">
                    {commesse_allarme?.length > 0 ? commesse_allarme.map((c, i) => (
                        <div key={i} className="flex items-center justify-between px-4 py-2 text-xs border-b border-slate-50 hover:bg-slate-50 cursor-pointer"
                            onClick={() => navigate(`/commesse/${c.commessa_id}`)}>
                            <div className="min-w-0">
                                <p className="font-medium text-slate-700 truncate">{c.numero} {c.title}</p>
                                <p className="text-slate-400 truncate">{c.client_name}</p>
                            </div>
                            <Badge className="bg-slate-200 text-slate-600 text-[10px] shrink-0 ml-2">{c.giorni_fermo}gg fermo</Badge>
                        </div>
                    )) : (
                        <p className="text-xs text-emerald-500 text-center py-6">Tutte le commesse aggiornate</p>
                    )}
                </CardContent>
            </Card>

            {/* Card 4: Da fare oggi */}
            <Card className="border-slate-200 overflow-hidden" data-testid="briefing-dafere">
                <CardHeader className="py-3 px-4 bg-gradient-to-r from-emerald-50 to-teal-50 border-b">
                    <CardTitle className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                        <ClipboardCheck className="h-3.5 w-3.5 text-emerald-500" />
                        Da Fare Oggi
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-3 space-y-2">
                    {da_fare?.preventivi_da_convertire > 0 && (
                        <div className="flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 rounded p-1.5"
                            onClick={() => navigate('/preventivi')}>
                            <span className="w-5 h-5 rounded bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-[10px]">{da_fare.preventivi_da_convertire}</span>
                            <span className="text-slate-600">Preventivi accettati da convertire</span>
                        </div>
                    )}
                    {da_fare?.ddt_non_fatturati > 0 && (
                        <div className="flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 rounded p-1.5"
                            onClick={() => navigate('/ddt')}>
                            <span className="w-5 h-5 rounded bg-violet-100 text-violet-600 flex items-center justify-center font-bold text-[10px]">{da_fare.ddt_non_fatturati}</span>
                            <span className="text-slate-600">DDT non fatturati (&gt;30gg)</span>
                        </div>
                    )}
                    {da_fare?.fatture_scadute > 0 && (
                        <div className="flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 rounded p-1.5"
                            onClick={() => navigate('/scadenziario')}>
                            <span className="w-5 h-5 rounded bg-red-100 text-red-600 flex items-center justify-center font-bold text-[10px]">{da_fare.fatture_scadute}</span>
                            <span className="text-slate-600">Fatture passive scadute non pagate</span>
                        </div>
                    )}
                    {!da_fare?.preventivi_da_convertire && !da_fare?.ddt_non_fatturati && !da_fare?.fatture_scadute && (
                        <p className="text-xs text-emerald-500 text-center py-4">Tutto in ordine!</p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
