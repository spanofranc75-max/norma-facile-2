/**
 * KPIDashboard — Confidence Score & Analytics Dashboard.
 * Mostra accuratezza stime AI, marginalita, ritardi fornitori, tempi medi.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line,
} from 'recharts';
import {
    Brain, TrendingUp, Factory, Truck, Clock,
    Target, AlertTriangle, Loader2, CircleDollarSign,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
const fmtEur = (v) => typeof v === 'number' ? v.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' }) : '-';

function ScoreGauge({ score, label }) {
    const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (Math.min(score || 0, 100) / 100) * circumference;

    return (
        <div className="flex flex-col items-center" data-testid="accuracy-gauge">
            <svg width="140" height="140" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="54" fill="none" stroke="#e2e8f0" strokeWidth="8" />
                <circle cx="60" cy="60" r="54" fill="none" stroke={color} strokeWidth="8"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round" transform="rotate(-90 60 60)" className="transition-all duration-1000" />
                <text x="60" y="55" textAnchor="middle" className="fill-slate-800 text-2xl font-bold" style={{ fontSize: '28px', fontWeight: 800 }}>
                    {score != null ? `${score}%` : '—'}
                </text>
                <text x="60" y="75" textAnchor="middle" className="fill-slate-400" style={{ fontSize: '9px' }}>
                    {label}
                </text>
            </svg>
        </div>
    );
}

function StatCard({ icon: Icon, label, value, sub, color = 'text-slate-700', bg = 'bg-white' }) {
    return (
        <div className={`${bg} rounded-lg border p-3 text-center`}>
            <Icon className={`h-4 w-4 ${color} mx-auto mb-1`} />
            <p className="text-[10px] text-slate-500">{label}</p>
            <p className={`text-lg font-bold ${color}`}>{value}</p>
            {sub && <p className="text-[9px] text-slate-400">{sub}</p>}
        </div>
    );
}

export default function KPIDashboard() {
    const [overview, setOverview] = useState(null);
    const [accuracy, setAccuracy] = useState(null);
    const [trend, setTrend] = useState(null);
    const [marginalita, setMarginalita] = useState(null);
    const [fornitori, setFornitori] = useState(null);
    const [tempi, setTempi] = useState(null);
    const [loading, setLoading] = useState(true);

    const [calibrazione, setCalibrazione] = useState(null);

    const fetchAll = useCallback(async () => {
        try {
            const [ov, acc, tr, mar, forn, tmp, cal] = await Promise.all([
                apiRequest('/kpi/overview'),
                apiRequest('/kpi/accuracy-score'),
                apiRequest('/kpi/trend-accuracy'),
                apiRequest('/kpi/marginalita'),
                apiRequest('/kpi/ritardi-fornitori'),
                apiRequest('/kpi/tempi-medi'),
                apiRequest('/calibrazione/status').catch(() => null),
            ]);
            setOverview(ov);
            setAccuracy(acc);
            setTrend(tr);
            setMarginalita(mar);
            setFornitori(forn);
            setTempi(tmp);
            setCalibrazione(cal);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
                </div>
            </DashboardLayout>
        );
    }

    const margData = (marginalita?.commesse || [])
        .filter(c => c.importo > 0)
        .slice(0, 12)
        .map(c => ({ name: c.numero || c.commessa_id?.slice(-6), importo: c.importo, costo: c.costo_totale, margine: c.margine_pct }));

    const trendData = trend?.trend || [];

    const tempiData = Object.entries(tempi?.tipologie || {}).map(([k, v]) => ({
        name: k.charAt(0).toUpperCase() + k.slice(1),
        ore_per_ton: v.ore_per_ton,
        commesse: v.commesse_count,
    }));

    const fornitoriData = (fornitori?.fornitori || []).slice(0, 8);

    return (
        <DashboardLayout>
            <div className="space-y-6 max-w-7xl">
                {/* Header */}
                <div>
                    <h1 className="font-sans text-3xl font-bold text-slate-900 flex items-center gap-3">
                        <Target className="h-8 w-8 text-violet-600" />
                        Dashboard KPI
                    </h1>
                    <p className="text-slate-500 mt-1">Confidence Score AI, marginalita reale, performance fornitori</p>
                </div>

                {/* Overview Cards */}
                {overview && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2" data-testid="kpi-overview">
                        <StatCard icon={Factory} label="Commesse" value={overview.commesse_totali} sub={`${overview.commesse_chiuse} chiuse`} />
                        <StatCard icon={Brain} label="Preventivi AI" value={overview.preventivi_predittivi} sub={`/ ${overview.preventivi_totali} totali`} color="text-violet-700" bg="bg-violet-50" />
                        <StatCard icon={CircleDollarSign} label="Fatturato" value={fmtEur(overview.fatturato_totale)} color="text-emerald-700" bg="bg-emerald-50" />
                        <StatCard icon={TrendingUp} label="Fatture" value={overview.fatture_emesse} />
                        <StatCard icon={Truck} label="C/L Attivi" value={overview.cl_attivi} sub={`/ ${overview.cl_totali} totali`} color={overview.cl_attivi > 0 ? 'text-amber-700' : 'text-slate-700'} bg={overview.cl_attivi > 0 ? 'bg-amber-50' : 'bg-white'} />
                        <StatCard icon={Clock} label="Score Ore" value={accuracy?.score_ore != null ? `${accuracy.score_ore}%` : '—'} color="text-blue-700" bg="bg-blue-50" />
                        <StatCard icon={CircleDollarSign} label="Score Costi" value={accuracy?.score_costi != null ? `${accuracy.score_costi}%` : '—'} color="text-emerald-700" bg="bg-emerald-50" />
                    </div>
                )}

                {/* Main Row: Accuracy Gauge + Trend */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Accuracy Gauge */}
                    <Card className="border-violet-200 md:col-span-1" data-testid="accuracy-card">
                        <CardHeader className="bg-violet-50 border-b border-violet-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-violet-800">
                                <Brain className="h-4 w-4" /> Confidence Score AI
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 flex flex-col items-center space-y-3">
                            <ScoreGauge score={accuracy?.score_globale} label="Accuratezza Globale" />
                            <div className="text-center text-xs text-slate-500">
                                <p>{accuracy?.commesse_analizzate || 0} commesse analizzate</p>
                                <p>{accuracy?.commesse_con_dati_ore || 0} con dati ore</p>
                            </div>
                            {accuracy?.score_globale == null && (
                                <p className="text-xs text-amber-600 text-center bg-amber-50 p-2 rounded">
                                    Completa commesse con ore e costi reali per attivare il punteggio
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    {/* Trend Accuracy */}
                    <Card className="border-blue-200 md:col-span-2" data-testid="trend-card">
                        <CardHeader className="bg-blue-50 border-b border-blue-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-blue-800">
                                <TrendingUp className="h-4 w-4" /> Trend Accuratezza nel Tempo
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4">
                            {trendData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={trendData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                        <XAxis dataKey="mese" tick={{ fontSize: 10 }} />
                                        <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                                        <Tooltip formatter={(v) => [`${v}%`, 'Accuratezza']} />
                                        <Line type="monotone" dataKey="accuracy" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
                                    </LineChart>
                                </ResponsiveContainer>
                            ) : (
                                <p className="text-xs text-slate-400 text-center py-8">Dati insufficienti. Le commesse chiuse con ore reali popoleranno questo grafico.</p>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Top Scostamenti */}
                {accuracy?.top_scostamenti?.length > 0 && (
                    <Card className="border-red-200" data-testid="scostamenti-card">
                        <CardHeader className="bg-red-50 border-b border-red-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-red-800">
                                <AlertTriangle className="h-4 w-4" /> Top 3 Scostamenti (dove migliorare)
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-3">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                                {accuracy.top_scostamenti.map((c, i) => (
                                    <div key={i} className="border rounded-lg p-3 bg-white">
                                        <p className="text-xs font-bold text-slate-700">{c.numero}</p>
                                        <p className="text-[10px] text-slate-400 truncate">{c.title}</p>
                                        <div className="flex items-center justify-between mt-2">
                                            <div>
                                                <p className="text-[10px] text-slate-500">Previste</p>
                                                <p className="text-xs font-semibold">{c.ore_preventivate}h</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-slate-500">Reali</p>
                                                <p className="text-xs font-semibold">{c.ore_reali}h</p>
                                            </div>
                                            <Badge variant="outline" className={`text-[10px] ${c.accuracy_ore >= 80 ? 'bg-emerald-50 text-emerald-700' : c.accuracy_ore >= 60 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>
                                                {c.accuracy_ore}%
                                            </Badge>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Second Row: Marginalita + Fornitori */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Marginalita */}
                    <Card className="border-emerald-200" data-testid="marginalita-card">
                        <CardHeader className="bg-emerald-50 border-b border-emerald-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-emerald-800">
                                <CircleDollarSign className="h-4 w-4" /> Marginalita per Commessa
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4">
                            {margData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={margData} barGap={2}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                        <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                                        <YAxis tick={{ fontSize: 9 }} />
                                        <Tooltip formatter={(v) => fmtEur(v)} />
                                        <Bar dataKey="importo" fill="#10b981" name="Fatturato" radius={[2, 2, 0, 0]} />
                                        <Bar dataKey="costo" fill="#f59e0b" name="Costo Reale" radius={[2, 2, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <p className="text-xs text-slate-400 text-center py-8">Nessuna commessa con dati finanziari</p>
                            )}
                        </CardContent>
                    </Card>

                    {/* Fornitori C/L */}
                    <Card className="border-amber-200" data-testid="fornitori-card">
                        <CardHeader className="bg-amber-50 border-b border-amber-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-amber-800">
                                <Truck className="h-4 w-4" /> Performance Fornitori C/L
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-3">
                            {fornitoriData.length > 0 ? (
                                <div className="space-y-2">
                                    {fornitoriData.map((f, i) => (
                                        <div key={i} className="flex items-center justify-between p-2 border rounded bg-white text-xs">
                                            <div className="flex-1 min-w-0">
                                                <span className="font-semibold text-slate-700">{f.fornitore}</span>
                                                <div className="flex gap-1 mt-0.5">
                                                    {f.tipi.map(t => (
                                                        <Badge key={t} variant="outline" className="text-[8px]">{t}</Badge>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3 text-right">
                                                <div>
                                                    <p className="text-[10px] text-slate-400">Lavoraz.</p>
                                                    <p className="font-semibold">{f.totali}</p>
                                                </div>
                                                <div>
                                                    <p className="text-[10px] text-slate-400">In corso</p>
                                                    <p className={`font-semibold ${f.in_corso > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{f.in_corso}</p>
                                                </div>
                                                {f.giorni_medi != null && (
                                                    <div>
                                                        <p className="text-[10px] text-slate-400">gg medi</p>
                                                        <p className={`font-semibold ${f.giorni_medi > 15 ? 'text-red-600' : f.giorni_medi > 7 ? 'text-amber-600' : 'text-emerald-600'}`}>{f.giorni_medi}</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-xs text-slate-400 text-center py-8">Nessun dato conto lavoro</p>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Tempi Medi */}
                {tempiData.length > 0 && (
                    <Card className="border-indigo-200" data-testid="tempi-card">
                        <CardHeader className="bg-indigo-50 border-b border-indigo-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-indigo-800">
                                <Clock className="h-4 w-4" /> Tempi Medi Lavorazione (h/ton)
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4">
                            <ResponsiveContainer width="100%" height={180}>
                                <BarChart data={tempiData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                                    <YAxis tick={{ fontSize: 10 }} />
                                    <Tooltip formatter={(v, name) => [name === 'ore_per_ton' ? `${v} h/ton` : v, name === 'ore_per_ton' ? 'Ore/Ton' : 'Commesse']} />
                                    <Bar dataKey="ore_per_ton" fill="#6366f1" name="Ore/Ton" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                )}

                {/* ML Calibration Panel */}
                {calibrazione && calibrazione.n_progetti > 0 && (
                    <Card className="border-indigo-200" data-testid="calibrazione-card">
                        <CardHeader className="bg-indigo-50 border-b border-indigo-200 py-3">
                            <CardTitle className="text-sm flex items-center gap-2 text-indigo-800">
                                <Brain className="h-4 w-4" /> Calibrazione ML Predittiva
                                {calibrazione.calibrato && (
                                    <Badge variant="outline" className="border-emerald-500 text-emerald-700 text-[10px] ml-auto">Attiva</Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 space-y-4">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <div className="text-center p-2 bg-white rounded border">
                                    <p className="text-[10px] text-slate-500">Progetti Training</p>
                                    <p className="text-xl font-bold text-indigo-700">{calibrazione.n_progetti}</p>
                                </div>
                                <div className="text-center p-2 bg-white rounded border">
                                    <p className="text-[10px] text-slate-500">Accuracy Pre-ML</p>
                                    <p className="text-xl font-bold text-amber-600">{calibrazione.accuracy_pre_calibrazione}%</p>
                                </div>
                                <div className="text-center p-2 bg-white rounded border">
                                    <p className="text-[10px] text-slate-500">Accuracy Post-ML</p>
                                    <p className="text-xl font-bold text-emerald-600">{calibrazione.accuracy_post_calibrazione}%</p>
                                </div>
                                <div className="text-center p-2 bg-white rounded border">
                                    <p className="text-[10px] text-slate-500">Miglioramento</p>
                                    <p className={`text-xl font-bold ${calibrazione.miglioramento_pct > 0 ? 'text-emerald-600' : 'text-slate-600'}`}>
                                        {calibrazione.miglioramento_pct > 0 ? '+' : ''}{calibrazione.miglioramento_pct}%
                                    </p>
                                </div>
                            </div>

                            {/* Correction factors */}
                            {calibrazione.fattori && (
                                <div>
                                    <p className="text-xs font-medium text-slate-600 mb-2">Fattori Correttivi Appresi</p>
                                    <div className="grid grid-cols-4 gap-2">
                                        {Object.entries(calibrazione.fattori).map(([k, v]) => (
                                            <div key={k} className="text-center p-1.5 bg-slate-50 rounded text-xs">
                                                <span className="text-slate-500 capitalize">{k.replace('_', ' ')}</span>
                                                <p className={`font-mono font-bold ${v > 1.05 ? 'text-red-600' : v < 0.95 ? 'text-emerald-600' : 'text-slate-700'}`}>
                                                    x{v.toFixed(3)}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Evolution chart */}
                            {calibrazione.evoluzione?.length > 2 && (
                                <div>
                                    <p className="text-xs font-medium text-slate-600 mb-2">Evoluzione Accuratezza</p>
                                    <ResponsiveContainer width="100%" height={160}>
                                        <LineChart data={calibrazione.evoluzione}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                            <XAxis dataKey="n" tick={{ fontSize: 10 }} label={{ value: 'Progetti', position: 'bottom', fontSize: 10 }} />
                                            <YAxis domain={[50, 100]} tick={{ fontSize: 10 }} />
                                            <Tooltip formatter={(v, name) => [`${v}%`, name === 'accuracy_pre' ? 'Senza ML' : 'Con ML']} />
                                            <Line type="monotone" dataKey="accuracy_pre" stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="5 5" name="Senza ML" dot={false} />
                                            <Line type="monotone" dataKey="accuracy_post" stroke="#10b981" strokeWidth={2} name="Con ML" dot={{ r: 3 }} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            )}

                            {/* Distribution by type */}
                            {calibrazione.distribuzione_tipologia && (
                                <div>
                                    <p className="text-xs font-medium text-slate-600 mb-2">Distribuzione per Tipologia</p>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(calibrazione.distribuzione_tipologia).map(([tipo, data]) => (
                                            <Badge key={tipo} variant="outline" className="text-xs">
                                                {tipo}: {data.count} progetti (err. {data.errore_medio_ore}%)
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}
            </div>
        </DashboardLayout>
    );
}
