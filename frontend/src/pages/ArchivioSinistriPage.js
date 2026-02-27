/**
 * Archivio Sinistri — Dashboard statistiche perizie
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { ShieldAlert, TrendingUp, FileText, Euro, ArrowRight, Tag } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const TIPO_COLORS = { strutturale: '#DC2626', estetico: '#F59E0B', automatismi: '#8B5CF6' };
const TIPO_LABELS = { strutturale: 'Strutturale', estetico: 'Estetico', automatismi: 'Automatismi' };
const STATUS_LABELS = { bozza: 'Bozza', analizzata: 'Analizzata', completata: 'Completata', inviata: 'Inviata' };
const PIE_COLORS = ['#DC2626', '#F59E0B', '#8B5CF6', '#0055FF'];

const fmtMoney = (v) => `${Number(v || 0).toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

export default function ArchivioSinistriPage() {
    const navigate = useNavigate();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiRequest('/perizie/archivio/stats')
            .then(setStats)
            .catch(() => toast.error('Errore caricamento statistiche'))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-[#0055FF] border-t-transparent rounded-full animate-spin" /></div>
        </DashboardLayout>
    );

    if (!stats || stats.total_count === 0) return (
        <DashboardLayout>
            <div className="text-center py-20" data-testid="archivio-empty">
                <ShieldAlert className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <h2 className="text-lg font-bold text-[#1E293B]">Nessuna perizia nell'archivio</h2>
                <p className="text-sm text-slate-500 mt-1">Crea la tua prima perizia per vedere le statistiche</p>
                <Button onClick={() => navigate('/perizie/new')} className="mt-4 bg-[#0055FF] text-white">Nuova Perizia</Button>
            </div>
        </DashboardLayout>
    );

    const tipoData = Object.entries(stats.by_tipo).map(([k, v]) => ({
        name: TIPO_LABELS[k] || k, count: v.count, amount: v.amount, color: TIPO_COLORS[k] || '#6B7280',
    }));

    const monthData = (stats.by_month || []).map(m => ({
        month: m.month.slice(5), // "01", "02" etc
        count: m.count,
        amount: m.amount,
    }));

    const statusData = Object.entries(stats.by_status).map(([k, v], i) => ({
        name: STATUS_LABELS[k] || k, value: v, color: PIE_COLORS[i % PIE_COLORS.length],
    }));

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="archivio-sinistri-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <ShieldAlert className="h-6 w-6 text-[#0055FF]" /> Archivio Sinistri
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Riepilogo e statistiche delle perizie sinistro</p>
                    </div>
                    <Button onClick={() => navigate('/perizie')} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                        <ArrowRight className="h-4 w-4 mr-2" /> Vai alle Perizie
                    </Button>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <KpiCard icon={FileText} label="Perizie Totali" value={stats.total_count} color="blue" />
                    <KpiCard icon={Euro} label="Volume Totale" value={`${fmtMoney(stats.total_amount)} EUR`} color="emerald" />
                    <KpiCard icon={TrendingUp} label="Importo Medio" value={`${fmtMoney(stats.avg_amount)} EUR`} color="amber" />
                    <KpiCard icon={Tag} label="Codici Danno Usati" value={stats.codici_frequency?.length || 0} color="purple" />
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Monthly Trend */}
                    {monthData.length > 0 && (
                        <Card className="border-gray-200">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">Andamento Mensile</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={monthData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                                        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                                        <YAxis tick={{ fontSize: 11 }} />
                                        <Tooltip formatter={(v) => `${fmtMoney(v)} EUR`} />
                                        <Bar dataKey="amount" fill="#0055FF" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    )}

                    {/* By Status Pie */}
                    <Card className="border-gray-200">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-semibold text-[#1E293B]">Stato Perizie</CardTitle>
                        </CardHeader>
                        <CardContent className="flex items-center gap-4">
                            <ResponsiveContainer width="50%" height={200}>
                                <PieChart>
                                    <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={75} paddingAngle={2}>
                                        {statusData.map((s, i) => <Cell key={i} fill={s.color} />)}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="space-y-2">
                                {statusData.map(s => (
                                    <div key={s.name} className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color }} />
                                        <span className="text-xs text-slate-600">{s.name}: <strong>{s.value}</strong></span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Bottom Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* By Tipo Danno */}
                    <Card className="border-gray-200">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-semibold text-[#1E293B]">Per Tipo di Danno</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {tipoData.map(t => {
                                    const pct = stats.total_count > 0 ? (t.count / stats.total_count * 100) : 0;
                                    return (
                                        <div key={t.name}>
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-xs font-medium text-slate-700">{t.name}</span>
                                                <span className="text-xs font-mono text-slate-500">{t.count} ({pct.toFixed(0)}%) — {fmtMoney(t.amount)} EUR</span>
                                            </div>
                                            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                                                <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: t.color }} />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Codici Danno Frequency */}
                    <Card className="border-gray-200">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-semibold text-[#1E293B]">Codici Danno Piu Frequenti</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {(stats.codici_frequency || []).length === 0 ? (
                                <p className="text-sm text-slate-400 text-center py-4">Nessun codice danno registrato</p>
                            ) : (
                                <div className="space-y-2">
                                    {stats.codici_frequency.slice(0, 7).map(cf => (
                                        <div key={cf.codice} className="flex items-center justify-between px-2 py-1.5 bg-slate-50 rounded-lg">
                                            <Badge className="bg-[#0055FF]/10 text-[#0055FF] font-mono text-xs">{cf.codice}</Badge>
                                            <div className="flex items-center gap-2">
                                                <div className="h-1.5 bg-[#0055FF] rounded-full" style={{ width: Math.max(20, cf.count * 30) }} />
                                                <span className="text-xs font-bold text-slate-700 w-6 text-right">{cf.count}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </DashboardLayout>
    );
}

function KpiCard({ icon: Icon, label, value, color }) {
    const colors = {
        blue: 'from-blue-500 to-blue-600',
        emerald: 'from-emerald-500 to-emerald-600',
        amber: 'from-amber-500 to-amber-600',
        purple: 'from-purple-500 to-purple-600',
    };
    return (
        <Card className="border-gray-200 overflow-hidden">
            <CardContent className="p-4">
                <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl bg-gradient-to-br ${colors[color]}`}>
                        <Icon className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <p className="text-[11px] text-slate-500 font-medium">{label}</p>
                        <p className="text-lg font-bold text-[#1E293B]" data-testid={`kpi-${label.toLowerCase().replace(/\s/g, '-')}`}>{value}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
