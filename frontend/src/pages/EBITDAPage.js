/**
 * Cruscotto Finanziario Artigiano — Financial Control Panel
 * IVA trimestrale, Semaforo Liquidità, Scadenzario, Cash Flow, Marginalità.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from 'recharts';
import {
    TrendingUp, TrendingDown, Euro, AlertTriangle, ChevronLeft, ChevronRight,
    Wallet, Shield, Clock, ArrowUpRight, ArrowDownRight, Receipt, Building2,
    CircleDollarSign, CalendarClock, Gauge, FileWarning,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const fmt = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const SEMAFORO_COLORS = {
    verde: { bg: 'bg-emerald-500', text: 'text-emerald-700', light: 'bg-emerald-50', border: 'border-emerald-200', label: 'TUTTO OK' },
    giallo: { bg: 'bg-amber-500', text: 'text-amber-700', light: 'bg-amber-50', border: 'border-amber-200', label: 'ATTENZIONE' },
    rosso: { bg: 'bg-red-500', text: 'text-red-700', light: 'bg-red-50', border: 'border-red-200', label: 'ALLARME' },
};

const ChartTooltipContent = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-[#1E293B] text-white text-xs px-3 py-2 rounded-lg shadow-xl space-y-1">
            <p className="font-medium">{label}</p>
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color }}>{p.name}: {fmt(p.value)}</p>
            ))}
        </div>
    );
};

export default function EBITDAPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [year, setYear] = useState(new Date().getFullYear());
    const [activeTab, setActiveTab] = useState('panoramica');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const res = await apiRequest(`/dashboard/cruscotto-finanziario?year=${year}`);
            setData(res);
        } catch (e) {
            console.error('Cruscotto fetch error:', e);
        } finally {
            setLoading(false);
        }
    }, [year]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const liq = data?.liquidita || {};
    const sem = SEMAFORO_COLORS[liq.semaforo] || SEMAFORO_COLORS.verde;
    const iva = data?.iva_trimestri || [];
    const agingClienti = data?.aging_clienti || {};
    const agingFornitori = data?.aging_fornitori || {};
    const cashflow = data?.cashflow_preview || [];
    const flussoReale = data?.flusso_reale || [];

    const tabs = [
        { id: 'panoramica', label: 'Panoramica' },
        { id: 'iva', label: 'IVA Trimestrale' },
        { id: 'scadenzario', label: 'Scadenzario' },
        { id: 'margini', label: 'Margini Commesse' },
    ];

    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="cruscotto-finanziario">
                {/* Header */}
                <div className="flex items-center justify-between flex-wrap gap-3">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Gauge className="h-6 w-6 text-[#0055FF]" />
                            Cruscotto Finanziario
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Controllo di gestione per artigiani</p>
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

                {/* Tabs */}
                <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit" data-testid="tabs">
                    {tabs.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            data-testid={`tab-${t.id}`}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                                activeTab === t.id ? 'bg-white text-[#1E293B] shadow-sm' : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                    </div>
                ) : (
                    <>
                        {activeTab === 'panoramica' && <PanoramicaTab data={data} liq={liq} sem={sem} agingClienti={agingClienti} agingFornitori={agingFornitori} cashflow={cashflow} flussoReale={flussoReale} />}
                        {activeTab === 'iva' && <IvaTab iva={iva} ivaAnnuale={data?.iva_annuale} year={year} />}
                        {activeTab === 'scadenzario' && <ScadenzarioTab clienti={data?.scadenzario_clienti} fornitori={data?.scadenzario_fornitori} totaleCrediti={data?.totale_crediti} totaleDebiti={data?.totale_debiti} fornitoriScaduti={data?.fornitori_scaduti} />}
                        {activeTab === 'margini' && <MarginiTab top={data?.top_margin} bottom={data?.bottom_margin} />}
                    </>
                )}
            </div>
        </DashboardLayout>
    );
}


// ── TAB: PANORAMICA ──────────────────────────────────────────────

function PanoramicaTab({ data, liq, sem, agingClienti, agingFornitori, cashflow, flussoReale }) {
    return (
        <div className="space-y-5">
            {/* Semaforo Liquidità */}
            <Card className={`${sem.light} ${sem.border} border-2`} data-testid="semaforo-liquidita">
                <CardContent className="pt-5 pb-4 px-5">
                    <div className="flex items-start gap-4">
                        <div className={`${sem.bg} w-14 h-14 rounded-full flex items-center justify-center shrink-0 shadow-lg`}>
                            {liq.semaforo === 'verde' ? <Shield className="h-7 w-7 text-white" /> :
                             liq.semaforo === 'rosso' ? <AlertTriangle className="h-7 w-7 text-white" /> :
                             <Clock className="h-7 w-7 text-white" />}
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <Badge className={`${sem.bg} text-white text-xs font-bold`}>{sem.label}</Badge>
                                <span className="text-sm font-medium text-slate-600">Liquidità Mese Corrente</span>
                            </div>
                            <p className={`text-sm ${sem.text} font-medium`}>{liq.semaforo_msg}</p>
                            {/* Entrate row */}
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
                                <MiniStat label="Incassi ricevuti" value={liq.incassi_mese} color="text-emerald-600" icon={<ArrowUpRight className="h-3 w-3" />} />
                                <MiniStat label="Da incassare" value={liq.da_incassare_mese} color="text-blue-600" icon={<Clock className="h-3 w-3" />} />
                                <MiniStat label="Tot. entrate previste" value={liq.entrate_previste} color="text-emerald-700" bold />
                            </div>
                            {/* Uscite row */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
                                <MiniStat label="Pagamenti effettuati" value={liq.pagamenti_effettuati} color="text-orange-600" negative icon={<ArrowDownRight className="h-3 w-3" />} />
                                <MiniStat label="Da pagare fornitori" value={liq.da_pagare_fornitori} color="text-amber-600" negative icon={<Building2 className="h-3 w-3" />} />
                                <MiniStat label="IVA prossimo F24" value={liq.iva_prossima} color="text-red-600" negative icon={<Receipt className="h-3 w-3" />} />
                                <MiniStat label="Tot. uscite previste" value={liq.uscite_previste} color="text-red-700" negative bold />
                            </div>
                        </div>
                    </div>
                    {/* Barra Entrate vs Uscite */}
                    <div className="mt-4 pt-3 border-t border-slate-200/50">
                        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                            <span>Entrate: <strong className="text-emerald-600">{fmt(liq.entrate_previste)}</strong></span>
                            <span>Uscite: <strong className="text-red-600">{fmt(liq.uscite_previste)}</strong></span>
                        </div>
                        <div className="h-3 bg-slate-200 rounded-full overflow-hidden flex">
                            {(liq.entrate_previste + liq.uscite_previste) > 0 && (
                                <>
                                    <div className="h-full bg-emerald-500 rounded-l-full transition-all"
                                         style={{ width: `${(liq.entrate_previste / (liq.entrate_previste + liq.uscite_previste)) * 100}%` }} />
                                    <div className="h-full bg-red-400 rounded-r-full transition-all"
                                         style={{ width: `${(liq.uscite_previste / (liq.entrate_previste + liq.uscite_previste)) * 100}%` }} />
                                </>
                            )}
                        </div>
                        <p className="text-center mt-2 text-sm font-bold">
                            Saldo: <span className={liq.saldo_operativo >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                                {fmt(liq.saldo_operativo)}
                            </span>
                        </p>
                    </div>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Flusso di Cassa Reale (ultimi 6 mesi) */}
                <Card className="border-gray-200" data-testid="flusso-reale">
                    <CardHeader className="pb-2 px-5 pt-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <Wallet className="h-4 w-4 text-[#0055FF]" />
                            Flusso di Cassa Reale (6 mesi)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="px-2 pb-4">
                        <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={flussoReale} margin={{ top: 5, right: 15, left: 10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                                <XAxis dataKey="mese" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                                <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false}
                                       tickFormatter={v => Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                                <Tooltip content={<ChartTooltipContent />} cursor={{ fill: '#F1F5F9' }} />
                                <Legend verticalAlign="top" height={30} />
                                <Bar name="Entrate Reali" dataKey="entrate" fill="#10B981" radius={[4, 4, 0, 0]} maxBarSize={30} />
                                <Bar name="Uscite Reali" dataKey="uscite" fill="#EF4444" radius={[4, 4, 0, 0]} maxBarSize={30} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Cash Flow Previsionale */}
                <Card className="border-gray-200" data-testid="cashflow-preview">
                    <CardHeader className="pb-2 px-5 pt-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <CalendarClock className="h-4 w-4 text-[#0055FF]" />
                            Previsione Cash Flow
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="px-2 pb-4">
                        <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={cashflow} margin={{ top: 5, right: 15, left: 10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                                <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
                                <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false}
                                       tickFormatter={v => Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                                <Tooltip content={<ChartTooltipContent />} cursor={{ fill: '#F1F5F9' }} />
                                <Legend verticalAlign="top" height={30} />
                                <Bar name="Entrate Attese" dataKey="entrate" fill="#10B981" radius={[4, 4, 0, 0]} maxBarSize={35} />
                                <Bar name="Uscite Previste" dataKey="uscite" fill="#EF4444" radius={[4, 4, 0, 0]} maxBarSize={35} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Aging Crediti (Clienti) */}
                <Card className="border-gray-200" data-testid="aging-clienti">
                    <CardHeader className="pb-2 px-5 pt-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                            Crediti Clienti (da incassare)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="px-5 pb-4">
                        <AgingBars aging={agingClienti} />
                        <div className="mt-3 pt-3 border-t border-slate-100">
                            <p className="text-xs text-slate-500">Totale crediti: <strong className="text-[#1E293B]">
                                {fmt(data?.totale_crediti)}
                            </strong></p>
                        </div>
                    </CardContent>
                </Card>

                {/* Aging Debiti (Fornitori) */}
                <Card className="border-gray-200" data-testid="aging-fornitori">
                    <CardHeader className="pb-2 px-5 pt-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <ArrowDownRight className="h-4 w-4 text-red-500" />
                            Debiti Fornitori (da pagare)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="px-5 pb-4">
                        <AgingBars aging={agingFornitori} isDebit />
                        <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between">
                            <p className="text-xs text-slate-500">Totale debiti: <strong className="text-red-600">
                                {fmt(data?.totale_debiti)}
                            </strong></p>
                            {(data?.fornitori_scaduti || 0) > 0 && (
                                <p className="text-xs font-semibold text-red-600 flex items-center gap-1">
                                    <AlertTriangle className="h-3 w-3" />
                                    Scaduti: {fmt(data?.fornitori_scaduti)}
                                </p>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Bilancino IVA */}
            <Card className="border-gray-200" data-testid="iva-quick">
                <CardHeader className="pb-2 px-5 pt-5">
                    <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                        <Receipt className="h-4 w-4 text-[#0055FF]" />
                        Bilancino IVA — {data?.year}
                    </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-4">
                    <div className="grid grid-cols-3 gap-4">
                        <div className="text-center p-3 bg-blue-50 rounded-lg">
                            <p className="text-xs text-slate-500 mb-1">IVA Vendite (Debito)</p>
                            <p className="text-lg font-mono font-bold text-blue-700">{fmt(data?.iva_annuale?.totale_debito)}</p>
                        </div>
                        <div className="text-center p-3 bg-emerald-50 rounded-lg">
                            <p className="text-xs text-slate-500 mb-1">IVA Acquisti (Credito)</p>
                            <p className="text-lg font-mono font-bold text-emerald-700">{fmt(data?.iva_annuale?.totale_credito)}</p>
                        </div>
                        <div className={`text-center p-3 rounded-lg ${(data?.iva_annuale?.totale_versare || 0) > 0 ? 'bg-red-50' : 'bg-emerald-50'}`}>
                            <p className="text-xs text-slate-500 mb-1">Saldo da Versare</p>
                            <p className={`text-lg font-mono font-bold ${(data?.iva_annuale?.totale_versare || 0) > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                {fmt(data?.iva_annuale?.totale_versare)}
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}


// ── TAB: IVA TRIMESTRALE ─────────────────────────────────────────

function IvaTab({ iva, ivaAnnuale, year }) {
    const chartData = iva.map(q => ({
        name: q.label.split(' ')[0],
        'IVA Debito': q.iva_debito,
        'IVA Credito': q.iva_credito,
        'Da Versare': q.iva_da_versare,
    }));

    return (
        <div className="space-y-5">
            <Card className="border-gray-200" data-testid="iva-chart">
                <CardHeader className="pb-2 px-5 pt-5">
                    <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                        <Receipt className="h-4 w-4 text-[#0055FF]" />
                        IVA Trimestrale — {year}
                    </CardTitle>
                </CardHeader>
                <CardContent className="px-2 pb-4">
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={chartData} margin={{ top: 5, right: 15, left: 10, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false}
                                   tickFormatter={v => Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                            <Tooltip content={<ChartTooltipContent />} cursor={{ fill: '#F1F5F9' }} />
                            <Legend verticalAlign="top" height={30} />
                            <Bar name="IVA Debito" dataKey="IVA Debito" fill="#3B82F6" radius={[4, 4, 0, 0]} maxBarSize={30} />
                            <Bar name="IVA Credito" dataKey="IVA Credito" fill="#10B981" radius={[4, 4, 0, 0]} maxBarSize={30} />
                            <Bar name="Da Versare" dataKey="Da Versare" fill="#EF4444" radius={[4, 4, 0, 0]} maxBarSize={30} />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            {/* Quarterly detail cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {iva.map(q => (
                    <Card key={q.trimestre} className="border-gray-200" data-testid={`iva-q${q.trimestre}`}>
                        <CardContent className="pt-4 pb-3 px-5">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-bold text-[#1E293B]">{q.label}</h3>
                                <Badge className="text-[10px] bg-slate-100 text-slate-600">F24: {q.f24_scadenza}</Badge>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-center">
                                <div className="bg-blue-50 rounded-lg p-2">
                                    <p className="text-[10px] text-slate-500">Debito</p>
                                    <p className="text-sm font-mono font-bold text-blue-700">{fmt(q.iva_debito)}</p>
                                </div>
                                <div className="bg-emerald-50 rounded-lg p-2">
                                    <p className="text-[10px] text-slate-500">Credito</p>
                                    <p className="text-sm font-mono font-bold text-emerald-700">{fmt(q.iva_credito)}</p>
                                </div>
                                <div className={`rounded-lg p-2 ${q.iva_da_versare > 0 ? 'bg-red-50' : 'bg-emerald-50'}`}>
                                    <p className="text-[10px] text-slate-500">Da Versare</p>
                                    <p className={`text-sm font-mono font-bold ${q.iva_da_versare > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                        {fmt(q.iva_da_versare)}
                                    </p>
                                </div>
                            </div>
                            <p className="text-xs text-slate-400 mt-2">
                                Emesse: {fmt(q.fatturato_attivo)} ({q.n_fatture_emesse} fatt.) — Ricevute: {fmt(q.fatturato_passivo)} ({q.n_fatture_ricevute} fatt.)
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Riepilogo annuale */}
            <Card className="border-2 border-[#0055FF]/20 bg-blue-50/30" data-testid="iva-totale">
                <CardContent className="pt-4 pb-3 px-5">
                    <h3 className="text-sm font-bold text-[#1E293B] mb-3">Riepilogo Annuale IVA {year}</h3>
                    <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                            <p className="text-xs text-slate-500">Totale IVA a Debito</p>
                            <p className="text-xl font-mono font-bold text-blue-700">{fmt(ivaAnnuale?.totale_debito)}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-500">Totale IVA a Credito</p>
                            <p className="text-xl font-mono font-bold text-emerald-700">{fmt(ivaAnnuale?.totale_credito)}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-500">Totale da Versare</p>
                            <p className={`text-xl font-mono font-bold ${(ivaAnnuale?.totale_versare || 0) > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                {fmt(ivaAnnuale?.totale_versare)}
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}


// ── TAB: SCADENZARIO ─────────────────────────────────────────────

function ScadenzarioTab({ clienti, fornitori, totaleCrediti, totaleDebiti, fornitoriScaduti }) {
    const [view, setView] = useState('clienti');
    const items = view === 'clienti' ? (clienti || []) : (fornitori || []);

    return (
        <div className="space-y-4">
            <div className="flex gap-2 flex-wrap">
                <Button
                    variant={view === 'clienti' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setView('clienti')}
                    className={view === 'clienti' ? 'bg-[#0055FF] text-white' : ''}
                    data-testid="btn-scad-clienti"
                >
                    <ArrowUpRight className="h-4 w-4 mr-1" /> Crediti Clienti ({(clienti || []).length})
                    {totaleCrediti > 0 && <span className="ml-1 font-mono">{fmt(totaleCrediti)}</span>}
                </Button>
                <Button
                    variant={view === 'fornitori' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setView('fornitori')}
                    className={view === 'fornitori' ? 'bg-amber-600 text-white hover:bg-amber-700' : ''}
                    data-testid="btn-scad-fornitori"
                >
                    <ArrowDownRight className="h-4 w-4 mr-1" /> Debiti Fornitori ({(fornitori || []).length})
                    {totaleDebiti > 0 && <span className="ml-1 font-mono">{fmt(totaleDebiti)}</span>}
                </Button>
                {(fornitoriScaduti || 0) > 0 && (
                    <Badge className="bg-red-100 text-red-800 text-xs self-center">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        Scaduti: {fmt(fornitoriScaduti)}
                    </Badge>
                )}
            </div>

            <Card className="border-gray-200" data-testid="scadenzario-table">
                <CardContent className="p-0">
                    {items.length === 0 ? (
                        <div className="text-center py-12 text-slate-400">
                            <CircleDollarSign className="h-10 w-10 mx-auto mb-2 text-slate-300" />
                            <p className="text-sm">Nessuna scadenza trovata</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-[#1E293B] text-white">
                                        <th className="px-4 py-2.5 text-left font-medium">
                                            {view === 'clienti' ? 'N. Fattura' : 'N. Documento'}
                                        </th>
                                        <th className="px-4 py-2.5 text-left font-medium">
                                            {view === 'clienti' ? 'Cliente' : 'Fornitore'}
                                        </th>
                                        <th className="px-4 py-2.5 text-right font-medium">Importo</th>
                                        <th className="px-4 py-2.5 text-center font-medium">Scadenza</th>
                                        <th className="px-4 py-2.5 text-center font-medium">Stato</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((item, i) => {
                                        const isOverdue = item.days_overdue > 0;
                                        return (
                                            <tr key={i} className={`border-b border-slate-100 ${isOverdue ? 'bg-red-50/50' : i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}>
                                                <td className="px-4 py-2.5 font-mono text-xs">{item.number || item.numero || '-'}</td>
                                                <td className="px-4 py-2.5 font-medium text-[#1E293B] truncate max-w-[200px]">
                                                    {item.client_name || item.fornitore || '-'}
                                                </td>
                                                <td className="px-4 py-2.5 text-right font-mono font-semibold">{fmt(item.amount)}</td>
                                                <td className="px-4 py-2.5 text-center text-xs">
                                                    {item.due_date ? new Date(item.due_date).toLocaleDateString('it-IT') : '-'}
                                                </td>
                                                <td className="px-4 py-2.5 text-center">
                                                    {isOverdue ? (
                                                        <Badge className="bg-red-100 text-red-800 text-[10px]">
                                                            Scaduta {item.days_overdue}gg
                                                        </Badge>
                                                    ) : (
                                                        <Badge className="bg-emerald-100 text-emerald-800 text-[10px]">In scadenza</Badge>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}


// ── TAB: MARGINI COMMESSE ────────────────────────────────────────

function MarginiTab({ top, bottom }) {
    return (
        <div className="space-y-5">
            {/* Top margin */}
            <Card className="border-gray-200" data-testid="top-margin">
                <CardHeader className="pb-2 px-5 pt-5">
                    <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-emerald-600" />
                        Top Commesse per Margine
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {(!top || top.length === 0) ? (
                        <div className="text-center py-8 text-slate-400">
                            <Wallet className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                            <p className="text-sm">Nessun dato marginalità disponibile</p>
                            <p className="text-xs mt-1">Compila i costi nelle RdP per vedere i margini</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-slate-100">
                            {top.map((c, i) => (
                                <MarginRow key={c.commessa_id} item={c} rank={i + 1} />
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Worst margin */}
            {bottom && bottom.length > 0 && (
                <Card className="border-gray-200" data-testid="bottom-margin">
                    <CardHeader className="pb-2 px-5 pt-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <TrendingDown className="h-4 w-4 text-red-500" />
                            Commesse con Margine Minore
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="divide-y divide-slate-100">
                            {bottom.map((c, i) => (
                                <MarginRow key={c.commessa_id} item={c} rank={i + 1} negative />
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}


// ── Utility Components ───────────────────────────────────────────

function MiniStat({ label, value, color, negative, bold, icon }) {
    return (
        <div className="text-center">
            <p className="text-[10px] text-slate-500 mb-0.5 flex items-center justify-center gap-1">
                {icon}{label}
            </p>
            <p className={`text-sm font-mono ${bold ? 'font-extrabold' : 'font-bold'} ${color}`}>
                {negative && value > 0 ? '-' : ''}{fmt(value)}
            </p>
        </div>
    );
}

function AgingBars({ aging, isDebit }) {
    const max = Math.max(aging["0_30"] || 0, aging["30_60"] || 0, aging["60_90"] || 0, aging["over_90"] || 0, 1);
    const colors = isDebit
        ? ['bg-blue-400', 'bg-amber-500', 'bg-orange-500', 'bg-red-600']
        : ['bg-emerald-500', 'bg-amber-500', 'bg-orange-500', 'bg-red-600'];
    return (
        <div className="space-y-3">
            {[
                { label: '0-30 giorni', key: '0_30', color: colors[0] },
                { label: '30-60 giorni', key: '30_60', color: colors[1] },
                { label: '60-90 giorni', key: '60_90', color: colors[2] },
                { label: 'Oltre 90 giorni', key: 'over_90', color: colors[3] },
            ].map(b => (
                <AgingBar key={b.key} label={b.label} amount={aging[b.key] || 0} color={b.color} max={max} />
            ))}
        </div>
    );
}

function AgingBar({ label, amount, color, max }) {
    const pct = max > 0 ? Math.min((amount / max) * 100, 100) : 0;
    return (
        <div>
            <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-600 font-medium">{label}</span>
                <span className="font-mono font-semibold text-[#1E293B]">{fmt(amount)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
}

function MarginRow({ item, rank, negative }) {
    const isNeg = item.margine < 0;
    return (
        <div className="px-5 py-3 flex items-center gap-3" data-testid={`margin-row-${rank}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 ${
                negative ? 'bg-red-500' : 'bg-emerald-500'
            }`}>
                {rank}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[#1E293B] truncate">{item.title}</p>
                <p className="text-xs text-slate-400">{item.client_name || ''}</p>
            </div>
            <div className="text-right shrink-0">
                <p className="text-xs text-slate-500">
                    {fmt(item.ricavo)} - {fmt(item.costi)}
                </p>
                <p className={`text-sm font-mono font-bold ${isNeg ? 'text-red-600' : 'text-emerald-600'}`}>
                    {fmt(item.margine)} <span className="text-xs">({item.margine_pct}%)</span>
                </p>
            </div>
        </div>
    );
}
