/**
 * EBITDA Dashboard — Pannello Analisi Finanziaria
 * Revenue vs Costs, margin analysis, supplier breakdown.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
    PieChart, Pie, Cell, LineChart, Line, Area, AreaChart,
} from 'recharts';
import {
    TrendingUp, TrendingDown, Euro, ArrowUpRight, ArrowDownRight,
    ChevronLeft, ChevronRight, Wallet, CreditCard, Building2,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const fmt = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);
const fmtShort = (v) => {
    if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
    return v.toFixed(0);
};

const COLORS = ['#0055FF', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'];

const ChartTooltipContent = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-[#1E293B] text-white text-xs px-3 py-2 rounded-lg shadow-xl space-y-1">
            <p className="font-medium">{label}</p>
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color }}>
                    {p.name}: {fmt(p.value)}
                </p>
            ))}
        </div>
    );
};

export default function EBITDAPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [year, setYear] = useState(new Date().getFullYear());

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const res = await apiRequest(`/dashboard/ebitda?year=${year}`);
            setData(res);
        } catch (e) {
            console.error('EBITDA fetch error:', e);
        } finally {
            setLoading(false);
        }
    }, [year]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const ytd = data?.ytd || {};
    const monthly = data?.monthly || [];
    const isPositive = (ytd.margin || 0) >= 0;

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="ebitda-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <TrendingUp className="h-6 w-6 text-[#0055FF]" />
                            Analisi Finanziaria
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Ricavi, costi e margine operativo</p>
                    </div>
                    <div className="flex items-center gap-2" data-testid="year-selector">
                        <Button variant="outline" size="sm" onClick={() => setYear(y => y - 1)} data-testid="btn-prev-year">
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span className="font-mono font-bold text-lg text-[#1E293B] w-16 text-center">{year}</span>
                        <Button variant="outline" size="sm" onClick={() => setYear(y => y + 1)} data-testid="btn-next-year" disabled={year >= new Date().getFullYear()}>
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                    </div>
                ) : (
                    <>
                        {/* KPI Cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <KPICard
                                testId="kpi-revenue"
                                label="Ricavi YTD"
                                value={fmt(ytd.revenue)}
                                icon={Euro}
                                gradient="from-blue-600 to-blue-400"
                                sub={`${monthly.reduce((a, m) => a + m.rev_count, 0)} fatture`}
                            />
                            <KPICard
                                testId="kpi-costs"
                                label="Costi YTD"
                                value={fmt(ytd.costs)}
                                icon={CreditCard}
                                gradient="from-amber-500 to-amber-400"
                                sub={`${monthly.reduce((a, m) => a + m.cost_count, 0)} fatture ricevute`}
                            />
                            <KPICard
                                testId="kpi-margin"
                                label="Margine YTD"
                                value={fmt(ytd.margin)}
                                icon={isPositive ? TrendingUp : TrendingDown}
                                gradient={isPositive ? 'from-emerald-600 to-emerald-400' : 'from-red-600 to-red-400'}
                                sub={`${ytd.margin_pct}% margine`}
                            />
                            <KPICard
                                testId="kpi-incassato"
                                label="Incassato"
                                value={fmt(data?.incassato)}
                                icon={Wallet}
                                gradient="from-violet-600 to-violet-400"
                                sub={`Da incassare: ${fmt(data?.da_incassare)}`}
                            />
                        </div>

                        {/* Main Chart — Revenue vs Costs */}
                        <Card className="border-gray-200" data-testid="chart-ebitda">
                            <CardHeader className="pb-2 px-5 pt-5">
                                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-[#0055FF]" />
                                    Ricavi vs Costi — {year}
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="px-2 pb-4">
                                <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={monthly} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                                        <XAxis dataKey="month_label" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
                                        <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} tickFormatter={fmtShort} />
                                        <Tooltip content={<ChartTooltipContent />} cursor={{ fill: '#F1F5F9' }} />
                                        <Legend verticalAlign="top" height={36} />
                                        <Bar name="Ricavi" dataKey="revenue" fill="#0055FF" radius={[4, 4, 0, 0]} maxBarSize={30} />
                                        <Bar name="Costi" dataKey="costs" fill="#F59E0B" radius={[4, 4, 0, 0]} maxBarSize={30} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>

                        {/* Second Row — Margin Trend + Top Suppliers */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Margin Trend */}
                            <Card className="border-gray-200" data-testid="chart-margin">
                                <CardHeader className="pb-2 px-5 pt-5">
                                    <CardTitle className="text-sm font-semibold text-[#1E293B]">
                                        Andamento Margine
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-2 pb-4">
                                    <ResponsiveContainer width="100%" height={250}>
                                        <AreaChart data={monthly} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                            <defs>
                                                <linearGradient id="marginGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                                                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                                            <XAxis dataKey="month_label" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                                            <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} tickFormatter={fmtShort} />
                                            <Tooltip content={<ChartTooltipContent />} />
                                            <Area type="monotone" name="Margine" dataKey="margin" stroke="#10B981" fill="url(#marginGrad)" strokeWidth={2} />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>

                            {/* Top Suppliers */}
                            <Card className="border-gray-200" data-testid="top-suppliers">
                                <CardHeader className="pb-2 px-5 pt-5">
                                    <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                        <Building2 className="h-4 w-4 text-[#0055FF]" />
                                        Top Fornitori per Spesa
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="p-0">
                                    {(data?.top_suppliers || []).length === 0 ? (
                                        <div className="text-center py-10 text-slate-400">
                                            <Building2 className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                                            <p className="text-sm">Nessuna fattura ricevuta registrata</p>
                                        </div>
                                    ) : (
                                        <div className="divide-y divide-gray-100">
                                            {data.top_suppliers.map((s, i) => {
                                                const maxTotal = data.top_suppliers[0]?.total || 1;
                                                const pct = Math.round((s.total / maxTotal) * 100);
                                                return (
                                                    <div key={i} className="px-5 py-3" data-testid={`supplier-row-${i}`}>
                                                        <div className="flex items-center justify-between mb-1">
                                                            <span className="text-sm font-medium text-[#1E293B] truncate max-w-[200px]">{s.supplier}</span>
                                                            <span className="font-mono text-sm text-[#0055FF] font-semibold">{fmt(s.total)}</span>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                                                <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }} />
                                                            </div>
                                                            <span className="text-xs text-slate-400">{s.count} fatt.</span>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>

                        {/* Monthly Detail Table */}
                        <Card className="border-gray-200" data-testid="monthly-table">
                            <CardHeader className="pb-2 px-5 pt-5">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">
                                    Dettaglio Mensile
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="bg-[#1E293B] text-white">
                                                <th className="px-4 py-2.5 text-left font-medium">Mese</th>
                                                <th className="px-4 py-2.5 text-right font-medium">Ricavi</th>
                                                <th className="px-4 py-2.5 text-right font-medium">Costi</th>
                                                <th className="px-4 py-2.5 text-right font-medium">Margine</th>
                                                <th className="px-4 py-2.5 text-right font-medium">%</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {monthly.map((m, i) => (
                                                <tr key={m.month} className={`border-b border-slate-100 ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`} data-testid={`month-row-${m.month}`}>
                                                    <td className="px-4 py-2.5 font-medium text-[#1E293B]">{m.month_label}</td>
                                                    <td className="px-4 py-2.5 text-right font-mono text-blue-600">{fmt(m.revenue)}</td>
                                                    <td className="px-4 py-2.5 text-right font-mono text-amber-600">{fmt(m.costs)}</td>
                                                    <td className={`px-4 py-2.5 text-right font-mono font-semibold ${m.margin >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                        {fmt(m.margin)}
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right">
                                                        <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${m.margin >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                            {m.margin >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                                                            {m.margin_pct}%
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                            {/* YTD Total row */}
                                            <tr className="bg-[#1E293B] text-white font-semibold">
                                                <td className="px-4 py-3">TOTALE YTD</td>
                                                <td className="px-4 py-3 text-right font-mono">{fmt(ytd.revenue)}</td>
                                                <td className="px-4 py-3 text-right font-mono">{fmt(ytd.costs)}</td>
                                                <td className="px-4 py-3 text-right font-mono">{fmt(ytd.margin)}</td>
                                                <td className="px-4 py-3 text-right font-mono">{ytd.margin_pct}%</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </CardContent>
                        </Card>
                    </>
                )}
            </div>
        </DashboardLayout>
    );
}

function KPICard({ testId, label, value, icon: Icon, gradient, sub }) {
    return (
        <Card data-testid={testId} className={`relative overflow-hidden border-0 bg-gradient-to-r ${gradient} text-white shadow-lg`}>
            <CardContent className="pt-5 pb-4 px-5">
                <div className="flex items-start justify-between">
                    <div className="min-w-0">
                        <p className="text-xs font-medium text-white/80 uppercase tracking-wider">{label}</p>
                        <p className="text-2xl font-mono font-bold mt-1 truncate">{value}</p>
                        <p className="text-xs text-white/70 mt-1">{sub}</p>
                    </div>
                    <div className="w-10 h-10 flex items-center justify-center rounded-lg shrink-0 bg-white/20 backdrop-blur-sm">
                        <Icon className="h-5 w-5 text-white" />
                    </div>
                </div>
                <div className="absolute -right-4 -bottom-4 w-24 h-24 rounded-full bg-white/10" />
            </CardContent>
        </Card>
    );
}
