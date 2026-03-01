/**
 * Dashboard Sostenibilita — Bilancio Ambientale + CO2 Savings
 * Eco-Counter, Indice Economia Circolare, Effetto Foresta, Charts
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    RadialBarChart, RadialBar, Legend, Cell, AreaChart, Area,
} from 'recharts';
import {
    Leaf, Download, Factory, Loader2, CheckCircle2, AlertTriangle,
    TreePine, Weight, Recycle, Building2, TrendingDown, Zap,
    Droplets, Wind,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const fmtKg = (v) => (v || 0).toLocaleString('it-IT', { maximumFractionDigits: 1 });
const fmtT = (v) => ((v || 0) / 1000).toLocaleString('it-IT', { maximumFractionDigits: 2 });
const fmtPerc = (v) => (v || 0).toLocaleString('it-IT', { maximumFractionDigits: 1 });

const MESI_IT = {
    '01': 'Gen', '02': 'Feb', '03': 'Mar', '04': 'Apr',
    '05': 'Mag', '06': 'Giu', '07': 'Lug', '08': 'Ago',
    '09': 'Set', '10': 'Ott', '11': 'Nov', '12': 'Dic',
};

const METODO_LABELS = {
    forno_elettrico_non_legato: 'Forno El. (non legato)',
    forno_elettrico_legato: 'Forno El. (legato)',
    ciclo_integrale: 'Ciclo Integrale',
    sconosciuto: 'Non specificato',
};

const COLORS = ['#059669', '#0284c7', '#7c3aed', '#dc2626', '#ea580c', '#ca8a04'];

export default function ReportCAMPage() {
    const currentYear = new Date().getFullYear();
    const [anno, setAnno] = useState(String(currentYear));
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchReport = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiRequest(`/cam/report-aziendale?anno=${anno}`);
            setReport(data);
        } catch (e) {
            toast.error('Errore caricamento report');
        } finally {
            setLoading(false);
        }
    }, [anno]);

    useEffect(() => { fetchReport(); }, [fetchReport]);

    const handleDownloadPdf = async () => {
        try {
            const res = await fetch(`${API}/api/cam/report-aziendale/pdf?anno=${anno}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Errore'); }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Bilancio_Sostenibilita_${anno}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Report PDF generato');
        } catch (e) { toast.error(e.message); }
    };

    const years = [];
    for (let y = currentYear; y >= currentYear - 5; y--) years.push(String(y));

    // Chart data
    const trendData = (report?.trend_mensile || []).map(t => ({
        ...t,
        label: MESI_IT[t.mese?.split('-')[1]] || t.mese,
    }));

    const co2CommessaData = (report?.co2_per_commessa || [])
        .filter(c => c.co2_risparmiata_kg > 0)
        .slice(0, 8)
        .map(c => ({
            name: c.numero || 'N/A',
            co2: Math.round(c.co2_risparmiata_kg),
            peso: Math.round(c.peso_kg),
        }));

    const gaugeData = report ? [{
        name: 'Circolare',
        value: report.indice_economia_circolare || 0,
        fill: (report.indice_economia_circolare || 0) >= 60 ? '#059669' : '#dc2626',
    }] : [];

    return (
        <DashboardLayout title="Sostenibilita">
            <div className="max-w-6xl mx-auto space-y-5" data-testid="sustainability-dashboard">
                {/* ── Header ─────────────────────────────── */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                        <h1 className="text-xl font-bold text-[#1E293B] flex items-center gap-2" data-testid="dashboard-title">
                            <Leaf className="h-5 w-5 text-emerald-600" />
                            Dashboard Sostenibilita
                        </h1>
                        <p className="text-sm text-slate-500 mt-0.5">Impatto ambientale e economia circolare</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <select
                            value={anno}
                            onChange={(e) => setAnno(e.target.value)}
                            className="h-9 w-28 border rounded-md px-2 text-sm bg-white"
                            data-testid="select-anno"
                        >
                            {years.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                        <Button
                            onClick={handleDownloadPdf}
                            disabled={!report || report.totale_lotti === 0}
                            className="bg-emerald-600 text-white hover:bg-emerald-700"
                            data-testid="btn-download-pdf"
                        >
                            <Download className="h-4 w-4 mr-1.5" /> Report PDF
                        </Button>
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
                    </div>
                ) : !report || report.totale_lotti === 0 ? (
                    <EmptyState anno={anno} />
                ) : (
                    <>
                        {/* ── ECO HERO ───────────────────────────── */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="eco-hero-section">
                            {/* CO2 Eco-Counter */}
                            <EcoCounter co2={report.co2} />
                            {/* Effetto Foresta */}
                            <ForestEffect alberi={report.alberi_equivalenti} />
                            {/* Circular Economy Gauge */}
                            <CircularGauge
                                value={report.indice_economia_circolare}
                                gaugeData={gaugeData}
                            />
                        </div>

                        {/* ── KPI Strip ──────────────────────────── */}
                        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3" data-testid="kpi-strip">
                            <KpiMini icon={Weight} label="Acciaio Totale" value={`${fmtT(report.peso_totale_kg)} t`} />
                            <KpiMini icon={Recycle} label="Riciclato" value={`${fmtT(report.peso_riciclato_kg)} t`} accent />
                            <KpiMini icon={Building2} label="Commesse" value={`${report.commesse_conformi}/${report.commesse_totali}`} />
                            <KpiMini icon={Factory} label="Lotti" value={report.totale_lotti} />
                            <KpiMini icon={TrendingDown} label="Riduzione CO2" value={`${fmtPerc(report.co2?.riduzione_percentuale)}%`} accent />
                        </div>

                        {/* ── Charts Row ─────────────────────────── */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {/* Trend Mensile */}
                            {trendData.length > 0 && (
                                <Card className="border-gray-200" data-testid="chart-trend-mensile">
                                    <CardHeader className="py-3 px-4">
                                        <CardTitle className="text-xs font-semibold text-slate-600 flex items-center gap-2">
                                            <TrendingDown className="h-3.5 w-3.5 text-emerald-600" />
                                            Trend CO2 Risparmiata (mensile)
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="px-2 pb-3">
                                        <ResponsiveContainer width="100%" height={220}>
                                            <AreaChart data={trendData}>
                                                <defs>
                                                    <linearGradient id="co2Grad" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="0%" stopColor="#059669" stopOpacity={0.3} />
                                                        <stop offset="100%" stopColor="#059669" stopOpacity={0.02} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} />
                                                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} unit=" kg" />
                                                <Tooltip
                                                    formatter={(v) => [`${v.toLocaleString('it-IT')} kg`, 'CO2 Risparmiata']}
                                                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                                                />
                                                <Area
                                                    type="monotone"
                                                    dataKey="co2_risparmiata_kg"
                                                    stroke="#059669"
                                                    strokeWidth={2}
                                                    fill="url(#co2Grad)"
                                                />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </CardContent>
                                </Card>
                            )}

                            {/* CO2 per Commessa */}
                            {co2CommessaData.length > 0 && (
                                <Card className="border-gray-200" data-testid="chart-co2-commessa">
                                    <CardHeader className="py-3 px-4">
                                        <CardTitle className="text-xs font-semibold text-slate-600 flex items-center gap-2">
                                            <Building2 className="h-3.5 w-3.5 text-blue-600" />
                                            CO2 Risparmiata per Commessa (kg)
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="px-2 pb-3">
                                        <ResponsiveContainer width="100%" height={220}>
                                            <BarChart data={co2CommessaData} layout="vertical">
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} unit=" kg" />
                                                <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#334155' }} width={85} />
                                                <Tooltip
                                                    formatter={(v) => [`${v.toLocaleString('it-IT')} kg`, 'CO2']}
                                                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                                                />
                                                <Bar dataKey="co2" radius={[0, 4, 4, 0]}>
                                                    {co2CommessaData.map((_, i) => (
                                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                                    ))}
                                                </Bar>
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </CardContent>
                                </Card>
                            )}
                        </div>

                        {/* ── Commesse Table ─────────────────────── */}
                        <Card className="border-gray-200" data-testid="cam-commesse-table">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <Building2 className="h-3.5 w-3.5" /> Dettaglio per Commessa ({report.commesse?.length || 0})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="text-xs">Commessa</TableHead>
                                            <TableHead className="text-xs">Cliente</TableHead>
                                            <TableHead className="text-xs text-right">Peso (kg)</TableHead>
                                            <TableHead className="text-xs text-right">Riciclato (kg)</TableHead>
                                            <TableHead className="text-xs text-center">% Ric.</TableHead>
                                            <TableHead className="text-xs text-center">Stato</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(report.commesse || []).map((c, i) => (
                                            <TableRow key={i} data-testid={`comm-row-${i}`}>
                                                <TableCell className="text-sm">
                                                    <span className="font-mono text-xs text-slate-500">{c.numero}</span>
                                                    {c.titolo && <p className="text-xs text-slate-700 font-medium truncate max-w-[180px]">{c.titolo}</p>}
                                                </TableCell>
                                                <TableCell className="text-xs text-slate-600">{c.cliente || '-'}</TableCell>
                                                <TableCell className="text-right text-xs font-mono">{fmtKg(c.peso_kg)}</TableCell>
                                                <TableCell className="text-right text-xs font-mono text-emerald-700">{fmtKg(c.peso_riciclato_kg)}</TableCell>
                                                <TableCell className="text-center">
                                                    <span className={`text-xs font-bold ${c.percentuale_riciclato >= 60 ? 'text-emerald-700' : 'text-red-600'}`}>
                                                        {fmtPerc(c.percentuale_riciclato)}%
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {c.conforme ? (
                                                        <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">
                                                            <CheckCircle2 className="h-3 w-3 mr-0.5" /> Conforme
                                                        </Badge>
                                                    ) : (
                                                        <Badge className="bg-red-100 text-red-700 text-[9px]">
                                                            <AlertTriangle className="h-3 w-3 mr-0.5" /> Non conf.
                                                        </Badge>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* ── Fornitori Table ────────────────────── */}
                        <Card className="border-gray-200" data-testid="cam-fornitori-table">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <Factory className="h-3.5 w-3.5" /> Breakdown per Fornitore ({report.fornitori?.length || 0})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="text-xs">Fornitore / Acciaieria</TableHead>
                                            <TableHead className="text-xs text-right">Peso (kg)</TableHead>
                                            <TableHead className="text-xs text-right">Riciclato (kg)</TableHead>
                                            <TableHead className="text-xs text-center">% Ric.</TableHead>
                                            <TableHead className="text-xs text-center">Lotti</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(report.fornitori || []).map((f, i) => (
                                            <TableRow key={i}>
                                                <TableCell className="text-sm font-medium">{f.fornitore}</TableCell>
                                                <TableCell className="text-right text-xs font-mono">{fmtKg(f.peso_kg)}</TableCell>
                                                <TableCell className="text-right text-xs font-mono text-emerald-700">{fmtKg(f.peso_riciclato_kg)}</TableCell>
                                                <TableCell className="text-center text-xs font-bold text-blue-700">{fmtPerc(f.percentuale_riciclato)}%</TableCell>
                                                <TableCell className="text-center text-xs">{f.lotti}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* ── Metodi Produttivi ──────────────────── */}
                        {Object.keys(report.metodi_produttivi || {}).length > 0 && (
                            <Card className="border-gray-200" data-testid="cam-metodi-table">
                                <CardHeader className="py-2 px-4">
                                    <CardTitle className="text-xs font-semibold text-slate-500 flex items-center gap-2">
                                        <Recycle className="h-3.5 w-3.5" /> Metodi Produttivi
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4 pb-3">
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                                        {Object.entries(report.metodi_produttivi).map(([metodo, data]) => (
                                            <div key={metodo} className="p-2 bg-slate-50 rounded border text-center">
                                                <p className="text-[10px] text-slate-500">{METODO_LABELS[metodo] || metodo}</p>
                                                <p className="text-sm font-bold text-[#1E293B]">{fmtKg(data.peso_kg)} kg</p>
                                                <p className="text-[10px] text-slate-400">{data.lotti} lotti</p>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* ── Footer Note ────────────────────────── */}
                        <p className="text-[10px] text-slate-400 text-center pb-4">
                            Dati calcolati secondo DM 23/06/2022 n.256 — Fattori emissione World Steel Association, 2023 (EAF: 0,67 tCO2/t | BOF: 2,33 tCO2/t) — 1 albero assorbe ~22 kg CO2/anno (EEA)
                        </p>
                    </>
                )}
            </div>
        </DashboardLayout>
    );
}

/* ═══════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

function EmptyState({ anno }) {
    return (
        <Card className="border-gray-200">
            <CardContent className="py-16 text-center">
                <Leaf className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                <p className="text-slate-500 text-sm">Nessun dato CAM per il {anno}</p>
                <p className="text-xs text-slate-400 mt-1">Aggiungi lotti materiale alle commesse dalla sezione CAM</p>
            </CardContent>
        </Card>
    );
}

function EcoCounter({ co2 }) {
    const saved = co2?.co2_risparmiata_kg || 0;
    const savedT = co2?.co2_risparmiata_t || 0;
    const reduction = co2?.riduzione_percentuale || 0;

    return (
        <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50 via-green-50 to-teal-50 overflow-hidden relative" data-testid="eco-counter">
            <div className="absolute top-2 right-2 opacity-10">
                <Wind className="h-20 w-20 text-emerald-800" />
            </div>
            <CardContent className="p-5 relative z-10">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center">
                        <Droplets className="h-4 w-4 text-white" />
                    </div>
                    <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider">Eco-Counter CO2</span>
                </div>
                <p className="text-4xl font-black text-emerald-900 tabular-nums" data-testid="eco-counter-value">
                    {saved.toLocaleString('it-IT', { maximumFractionDigits: 0 })}
                    <span className="text-lg font-bold ml-1">kg</span>
                </p>
                <p className="text-sm text-emerald-700 font-medium mt-0.5">
                    CO2 equivalente risparmiata
                </p>
                <div className="flex items-center gap-3 mt-3 text-xs text-emerald-600">
                    <span className="flex items-center gap-1">
                        <TrendingDown className="h-3 w-3" />
                        <strong>{fmtPerc(reduction)}%</strong> vs primario
                    </span>
                    <span className="text-emerald-500">{savedT.toLocaleString('it-IT', { maximumFractionDigits: 2 })} tCO2e</span>
                </div>
            </CardContent>
        </Card>
    );
}

function ForestEffect({ alberi }) {
    const treeCount = Math.round(alberi || 0);

    return (
        <Card className="border-green-200 bg-gradient-to-br from-green-50 via-lime-50 to-emerald-50 overflow-hidden relative" data-testid="forest-effect">
            <div className="absolute bottom-0 right-0 opacity-10">
                <TreePine className="h-24 w-24 text-green-800 translate-y-4 translate-x-4" />
            </div>
            <CardContent className="p-5 relative z-10">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
                        <TreePine className="h-4 w-4 text-white" />
                    </div>
                    <span className="text-xs font-semibold text-green-800 uppercase tracking-wider">L'Effetto Foresta</span>
                </div>
                <p className="text-4xl font-black text-green-900 tabular-nums" data-testid="forest-effect-value">
                    {treeCount.toLocaleString('it-IT')}
                </p>
                <p className="text-sm text-green-700 font-medium mt-0.5">
                    alberi equivalenti piantati
                </p>
                <p className="text-[10px] text-green-500 mt-2">
                    1 albero assorbe ~22 kg CO2/anno (EEA)
                </p>
                {/* Mini tree visualization */}
                <div className="flex items-end gap-0.5 mt-2 h-4 overflow-hidden">
                    {Array.from({ length: Math.min(treeCount, 30) }).map((_, i) => (
                        <div
                            key={i}
                            className="w-1.5 bg-green-400 rounded-t-sm"
                            style={{ height: `${8 + Math.random() * 8}px`, opacity: 0.5 + Math.random() * 0.5 }}
                        />
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}

function CircularGauge({ value, gaugeData }) {
    const color = value >= 60 ? '#059669' : value >= 30 ? '#ea580c' : '#dc2626';
    const label = value >= 75 ? 'Eccellente' : value >= 60 ? 'Buono' : value >= 30 ? 'Sufficiente' : 'Critico';

    return (
        <Card className="border-blue-200 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 overflow-hidden" data-testid="circular-gauge">
            <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                        <Zap className="h-4 w-4 text-white" />
                    </div>
                    <span className="text-xs font-semibold text-blue-800 uppercase tracking-wider">Indice Circolare</span>
                </div>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-4xl font-black tabular-nums" style={{ color }} data-testid="circular-gauge-value">
                            {fmtPerc(value)}
                            <span className="text-lg font-bold">%</span>
                        </p>
                        <Badge
                            className="mt-1 text-[9px]"
                            style={{ backgroundColor: `${color}20`, color }}
                        >
                            {label}
                        </Badge>
                    </div>
                    <div className="w-24 h-24">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadialBarChart
                                cx="50%" cy="50%"
                                innerRadius="65%" outerRadius="100%"
                                startAngle={180} endAngle={0}
                                barSize={10}
                                data={[{ value: value || 0, fill: color }]}
                            >
                                <RadialBar
                                    dataKey="value"
                                    cornerRadius={5}
                                    background={{ fill: '#e2e8f0' }}
                                />
                            </RadialBarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">% media ponderata acciaio riciclato</p>
            </CardContent>
        </Card>
    );
}

function KpiMini({ icon: Icon, label, value, accent }) {
    return (
        <div className={`p-3 rounded-lg border ${accent ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center gap-1.5 mb-0.5">
                <Icon className={`h-3.5 w-3.5 ${accent ? 'text-emerald-600' : 'text-slate-400'}`} />
                <span className="text-[10px] text-slate-500 uppercase tracking-wide">{label}</span>
            </div>
            <p className={`text-lg font-bold ${accent ? 'text-emerald-800' : 'text-[#1E293B]'}`}>{value}</p>
        </div>
    );
}
