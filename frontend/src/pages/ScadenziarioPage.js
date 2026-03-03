/**
 * ScadenziarioPage — Fintech-style deadline dashboard.
 * Transaction cards, grouped by urgency, with financial KPIs.
 */
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    AlertTriangle, CheckCircle2, Clock, RefreshCw, Filter,
    TrendingDown, TrendingUp, Wallet, ChevronDown, ChevronUp,
    Check, ExternalLink, Calendar as CalendarIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

function fmtCur(v) {
    if (v == null) return '0,00 \u20ac';
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);
}

function fmtDate(d) {
    if (!d) return '';
    try {
        const dt = new Date(d + 'T00:00:00');
        return dt.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch { return d; }
}

function daysUntil(d) {
    if (!d) return null;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const target = new Date(d + 'T00:00:00');
    return Math.round((target - today) / 86400000);
}

function getInitials(name) {
    if (!name) return '?';
    const words = name.trim().split(/\s+/).filter(w => w.length > 1);
    if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = [
    'bg-blue-600', 'bg-emerald-600', 'bg-violet-600', 'bg-amber-600',
    'bg-rose-600', 'bg-cyan-600', 'bg-indigo-600', 'bg-teal-600',
];

function avatarColor(name) {
    let hash = 0;
    for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

const TIPO_LABELS = {
    pagamento: 'Pagamento',
    incasso: 'Incasso',
    patentino: 'Patentino',
    taratura: 'Taratura',
    consegna: 'Consegna',
};

const MONTH_NAMES = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];

export default function ScadenziarioPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filterTipo, setFilterTipo] = useState('tutti');
    const [syncing, setSyncing] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const d = await apiRequest('/fatture-ricevute/scadenziario/dashboard');
            setData(d);
        } catch (e) {
            console.error('Fetch scadenziario error:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleSync = async () => {
        setSyncing(true);
        try {
            const result = await apiRequest('/fatture-ricevute/sync-fic', { method: 'POST' });
            toast.success(result.message || 'Sincronizzazione completata');
            fetchData();
        } catch (e) {
            toast.error(e.message || 'Errore sincronizzazione');
        } finally {
            setSyncing(false);
        }
    };

    const handleMarkPaid = async (item) => {
        if (item.tipo !== 'pagamento') return;
        try {
            await apiRequest(`/fatture-ricevute/${item.id}/pagamenti`, {
                method: 'POST',
                body: { importo: item.importo, data_pagamento: new Date().toISOString().split('T')[0], metodo: 'bonifico', note: '' },
            });
            toast.success('Pagamento registrato');
            fetchData();
        } catch (e) {
            toast.error(e.message || 'Errore registrazione pagamento');
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    const kpi = data?.kpi || {};
    const allScadenze = (data?.scadenze || []).filter(s =>
        filterTipo === 'tutti' || s.tipo === filterTipo
    );

    // Group into 3 sections
    const scaduti = allScadenze.filter(s => s.stato === 'scaduto');
    const questoMese = allScadenze.filter(s => s.stato === 'in_scadenza');
    const futuro = allScadenze.filter(s => s.stato === 'ok');

    // KPI calculations
    const usciteMese = (kpi.pagamenti_scaduti || 0) + (kpi.pagamenti_mese_corrente || 0);
    const entrateMese = (kpi.incassi_scaduti || 0) + (kpi.incassi_mese_corrente || 0);
    const saldo = entrateMese - usciteMese;
    const currentMonth = MONTH_NAMES[new Date().getMonth()];

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="scadenziario-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Scadenziario</h1>
                        <p className="text-sm text-slate-500 mt-0.5">Panoramica finanziaria e scadenze</p>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleSync}
                        disabled={syncing}
                        data-testid="sync-fic-btn"
                        className="border-slate-200 text-slate-600"
                    >
                        <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                        {syncing ? 'Sync...' : 'Sync SDI'}
                    </Button>
                </div>

                {/* KPI Cards - 3 big cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="border-slate-200 overflow-hidden" data-testid="kpi-uscite">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2 rounded-lg bg-red-50">
                                    <TrendingDown className="h-5 w-5 text-red-500" />
                                </div>
                                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Uscite Previste ({currentMonth})</span>
                            </div>
                            <p className="text-3xl font-bold text-red-600 font-mono tracking-tight">{fmtCur(usciteMese)}</p>
                            <p className="text-xs text-slate-400 mt-1.5">{kpi.scadute || 0} scadute + {kpi.in_scadenza || 0} in scadenza</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-200 overflow-hidden" data-testid="kpi-entrate">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2 rounded-lg bg-emerald-50">
                                    <TrendingUp className="h-5 w-5 text-emerald-500" />
                                </div>
                                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Entrate Previste ({currentMonth})</span>
                            </div>
                            <p className="text-3xl font-bold text-emerald-600 font-mono tracking-tight">{fmtCur(entrateMese)}</p>
                            <p className="text-xs text-slate-400 mt-1.5">Incassi attesi da fatture emesse</p>
                        </CardContent>
                    </Card>

                    <Card className={`border-slate-200 overflow-hidden ${saldo >= 0 ? 'bg-slate-50' : 'bg-red-50/30'}`} data-testid="kpi-saldo">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className={`p-2 rounded-lg ${saldo >= 0 ? 'bg-blue-50' : 'bg-red-50'}`}>
                                    <Wallet className={`h-5 w-5 ${saldo >= 0 ? 'text-blue-500' : 'text-red-500'}`} />
                                </div>
                                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Saldo Stimato</span>
                            </div>
                            <p className={`text-3xl font-bold font-mono tracking-tight ${saldo >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                                {saldo >= 0 ? '+' : ''}{fmtCur(saldo)}
                            </p>
                            <p className="text-xs text-slate-400 mt-1.5">Entrate - Uscite previste</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Alert Banner for overdue items */}
                {scaduti.length > 0 && (
                    <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-50 border border-red-200" data-testid="alert-scaduti">
                        <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
                        <p className="text-sm font-medium text-red-700">
                            {scaduti.length} scadenz{scaduti.length === 1 ? 'a' : 'e'} scadut{scaduti.length === 1 ? 'a' : 'e'} per un totale di{' '}
                            <span className="font-bold">{fmtCur(scaduti.reduce((s, i) => s + (i.importo || 0), 0))}</span>
                        </p>
                    </div>
                )}

                {/* Filters */}
                <div className="flex items-center gap-3">
                    <Filter className="h-4 w-4 text-slate-400" />
                    <div className="flex gap-1.5">
                        {['tutti', 'pagamento', 'incasso', 'patentino', 'taratura', 'consegna'].map(t => (
                            <button
                                key={t}
                                onClick={() => setFilterTipo(t)}
                                data-testid={`filter-${t}`}
                                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                                    filterTipo === t
                                        ? 'bg-slate-900 text-white'
                                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                }`}
                            >
                                {t === 'tutti' ? 'Tutti' : TIPO_LABELS[t] || t}
                            </button>
                        ))}
                    </div>
                    <span className="text-xs text-slate-400 ml-auto">{allScadenze.length} scadenze</span>
                </div>

                {/* Sections */}
                {allScadenze.length === 0 ? (
                    <Card className="border-slate-200">
                        <CardContent className="py-16 text-center">
                            <CheckCircle2 className="h-12 w-12 text-emerald-300 mx-auto mb-3" />
                            <p className="text-slate-500">Nessuna scadenza trovata</p>
                        </CardContent>
                    </Card>
                ) : (
                    <>
                        {scaduti.length > 0 && (
                            <ScadenzeSection
                                title="SCADUTI"
                                icon={AlertTriangle}
                                iconColor="text-red-500"
                                borderColor="border-l-red-500"
                                bgColor="bg-red-50/40"
                                items={scaduti}
                                defaultOpen={true}
                                onMarkPaid={handleMarkPaid}
                            />
                        )}
                        {questoMese.length > 0 && (
                            <ScadenzeSection
                                title={`IN SCADENZA \u2014 ${currentMonth.toUpperCase()}`}
                                icon={Clock}
                                iconColor="text-amber-500"
                                borderColor="border-l-amber-400"
                                bgColor=""
                                items={questoMese}
                                defaultOpen={true}
                                onMarkPaid={handleMarkPaid}
                            />
                        )}
                        {futuro.length > 0 && (
                            <ScadenzeSection
                                title="FUTURO"
                                icon={CalendarIcon}
                                iconColor="text-slate-400"
                                borderColor="border-l-slate-300"
                                bgColor=""
                                items={futuro}
                                defaultOpen={false}
                                onMarkPaid={handleMarkPaid}
                            />
                        )}
                    </>
                )}
            </div>
        </DashboardLayout>
    );
}

function ScadenzeSection({ title, icon: Icon, iconColor, borderColor, bgColor, items, defaultOpen, onMarkPaid }) {
    const [open, setOpen] = useState(defaultOpen);
    const total = items.reduce((s, i) => s + (i.importo || 0), 0);

    return (
        <div>
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-1 py-2 group"
                data-testid={`section-${title.split(' ')[0].toLowerCase()}`}
            >
                <div className="flex items-center gap-2.5">
                    <Icon className={`h-4 w-4 ${iconColor}`} />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">{title}</span>
                    <Badge variant="outline" className="text-[10px] font-mono px-1.5">{items.length}</Badge>
                </div>
                <div className="flex items-center gap-3">
                    {total > 0 && <span className="text-xs font-mono text-slate-500">{fmtCur(total)}</span>}
                    {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                </div>
            </button>
            {open && (
                <div className="space-y-2">
                    {items.map((item, i) => (
                        <TransactionCard
                            key={`${item.id}-${i}`}
                            item={item}
                            borderColor={borderColor}
                            bgColor={bgColor}
                            onMarkPaid={onMarkPaid}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

function TransactionCard({ item, borderColor, bgColor, onMarkPaid }) {
    const days = daysUntil(item.data_scadenza);
    const isExpense = item.tipo === 'pagamento';
    const isIncome = item.tipo === 'incasso';
    const entityName = item.sottotitolo || item.titolo;

    let daysLabel = '';
    if (days !== null) {
        if (days < 0) daysLabel = `${Math.abs(days)}gg fa`;
        else if (days === 0) daysLabel = 'Oggi';
        else if (days === 1) daysLabel = 'Domani';
        else if (days <= 7) daysLabel = `Tra ${days}gg`;
        else daysLabel = fmtDate(item.data_scadenza);
    }

    const statoPill = item.stato === 'scaduto'
        ? 'bg-red-100 text-red-700'
        : item.stato === 'in_scadenza'
            ? 'bg-amber-100 text-amber-700'
            : 'bg-slate-100 text-slate-600';

    const statoLabel = item.stato === 'scaduto' ? 'Scaduto'
        : item.stato === 'in_scadenza' ? 'In scadenza' : 'Programmato';

    return (
        <div
            className={`flex items-center gap-4 px-4 py-3.5 rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow ${bgColor} border-l-4 ${borderColor}`}
            data-testid={`scadenza-${item.id}`}
        >
            {/* Avatar */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${avatarColor(entityName)}`}>
                {getInitials(entityName)}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">{entityName}</p>
                <p className="text-xs text-slate-500 truncate mt-0.5">
                    {item.titolo}
                    {item.tipo !== 'pagamento' && item.tipo !== 'incasso' && (
                        <span className="ml-1.5 text-slate-400">({TIPO_LABELS[item.tipo] || item.tipo})</span>
                    )}
                </p>
            </div>

            {/* Status pill */}
            <Badge className={`text-[10px] px-2 py-0.5 shrink-0 ${statoPill}`}>{statoLabel}</Badge>

            {/* Amount + Date */}
            <div className="text-right shrink-0 min-w-[110px]">
                {item.importo != null && item.importo > 0 ? (
                    <p className={`text-base font-bold font-mono ${isExpense ? 'text-red-600' : isIncome ? 'text-emerald-600' : 'text-slate-800'}`}>
                        {isExpense ? '- ' : isIncome ? '+ ' : ''}{fmtCur(item.importo)}
                    </p>
                ) : (
                    <p className="text-sm text-slate-400 italic">N/A</p>
                )}
                <p className={`text-xs mt-0.5 ${item.stato === 'scaduto' ? 'text-red-500 font-medium' : 'text-slate-400'}`}>
                    {daysLabel}
                </p>
            </div>

            {/* Actions */}
            <div className="shrink-0 flex gap-1">
                {isExpense && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); onMarkPaid(item); }}
                        className="h-8 w-8 p-0 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50"
                        title="Segna come pagato"
                        data-testid={`pay-btn-${item.id}`}
                    >
                        <Check className="h-4 w-4" />
                    </Button>
                )}
                {item.link && (
                    <a href={item.link} onClick={(e) => e.stopPropagation()}>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-slate-400 hover:text-blue-600 hover:bg-blue-50"
                            title="Vai al dettaglio"
                        >
                            <ExternalLink className="h-3.5 w-3.5" />
                        </Button>
                    </a>
                )}
            </div>
        </div>
    );
}
