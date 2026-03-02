/**
 * ScadenziarioPage — Deadline dashboard: payments, documents, commesse.
 * Aggregates all deadlines in one view with KPIs and inbox.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    Calendar, AlertTriangle, CheckCircle2, Clock, CreditCard, Wrench,
    Award, Truck, ArrowRight, RefreshCw, Filter, FileInput, ChevronDown,
    ChevronUp, Package
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function formatCurrency(v) {
    if (v == null) return '';
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);
}

function formatDate(d) {
    if (!d) return '—';
    const parts = d.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return d;
}

const TIPO_CONFIG = {
    pagamento: { icon: CreditCard, label: 'Pagamento', color: '#dc2626' },
    patentino: { icon: Award, label: 'Patentino', color: '#7c3aed' },
    taratura: { icon: Wrench, label: 'Taratura', color: '#2563eb' },
    consegna: { icon: Truck, label: 'Consegna', color: '#059669' },
};

const STATO_BADGE = {
    scaduto: { label: 'Scaduto', className: 'bg-red-100 text-red-700' },
    in_scadenza: { label: 'In scadenza', className: 'bg-amber-100 text-amber-700' },
    ok: { label: 'OK', className: 'bg-emerald-100 text-emerald-700' },
};

export default function ScadenziarioPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filterTipo, setFilterTipo] = useState('tutti');
    const [filterStato, setFilterStato] = useState('tutti');
    const [syncing, setSyncing] = useState(false);
    const [syncResult, setSyncResult] = useState(null);
    const [inbox, setInbox] = useState([]);
    const [showInbox, setShowInbox] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const token = localStorage.getItem('session_token');
            const res = await fetch(`${API}/api/fatture-ricevute/scadenziario/dashboard`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const d = await res.json();
                setData(d);
            }
        } catch (e) {
            console.error('Fetch scadenziario error:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchInbox = useCallback(async () => {
        try {
            const token = localStorage.getItem('session_token');
            const res = await fetch(`${API}/api/fatture-ricevute?status=da_registrare&limit=50`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const d = await res.json();
                setInbox(d.fatture || []);
            }
        } catch (e) {
            console.error('Fetch inbox error:', e);
        }
    }, []);

    useEffect(() => {
        fetchData();
        fetchInbox();
    }, [fetchData, fetchInbox]);

    const handleSync = async () => {
        setSyncing(true);
        setSyncResult(null);
        try {
            const token = localStorage.getItem('session_token');
            const res = await fetch(`${API}/api/fatture-ricevute/sync-fic`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });
            const d = await res.json();
            if (res.ok) {
                setSyncResult({ type: 'success', text: d.message });
                fetchData();
                fetchInbox();
            } else {
                setSyncResult({ type: 'error', text: d.detail || 'Errore sincronizzazione' });
            }
        } catch (e) {
            setSyncResult({ type: 'error', text: 'Errore di rete' });
        } finally {
            setSyncing(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-6 w-6 animate-spin text-[#0055FF]" />
            </div>
        );
    }

    const kpi = data?.kpi || {};
    const scadenze = (data?.scadenze || []).filter(s => {
        if (filterTipo !== 'tutti' && s.tipo !== filterTipo) return false;
        if (filterStato !== 'tutti' && s.stato !== filterStato) return false;
        return true;
    });

    // Group by month
    const grouped = {};
    scadenze.forEach(s => {
        const d = s.data_scadenza || '';
        const month = d.slice(0, 7) || 'senza_data';
        if (!grouped[month]) grouped[month] = [];
        grouped[month].push(s);
    });

    return (
        <div className="space-y-6" data-testid="scadenziario-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-[#1E293B]">Scadenziario</h1>
                    <p className="text-sm text-gray-500 mt-1">Pagamenti, documenti, consegne — tutto in un posto</p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleSync}
                        disabled={syncing}
                        data-testid="sync-fic-btn"
                    >
                        <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                        {syncing ? 'Sincronizzazione...' : 'Sync FattureInCloud'}
                    </Button>
                </div>
            </div>

            {syncResult && (
                <div className={`px-4 py-2.5 rounded-lg text-sm font-medium ${syncResult.type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`} data-testid="sync-result">
                    {syncResult.text}
                </div>
            )}

            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard
                    icon={AlertTriangle}
                    label="Da Pagare (Scaduti)"
                    value={formatCurrency(kpi.pagamenti_scaduti)}
                    color="#dc2626"
                    count={kpi.scadute}
                    testId="kpi-scaduti"
                />
                <KPICard
                    icon={Clock}
                    label="Da Pagare (Mese)"
                    value={formatCurrency(kpi.pagamenti_mese_corrente)}
                    color="#ea580c"
                    count={kpi.in_scadenza}
                    testId="kpi-mese"
                />
                <KPICard
                    icon={CreditCard}
                    label="Acquisti Anno"
                    value={formatCurrency(kpi.totale_acquisti_anno)}
                    color="#2563eb"
                    testId="kpi-anno"
                />
                <KPICard
                    icon={FileInput}
                    label="Da Processare"
                    value={String(kpi.inbox_da_processare || 0)}
                    color="#7c3aed"
                    testId="kpi-inbox"
                    onClick={() => setShowInbox(!showInbox)}
                />
            </div>

            {/* Inbox (fatture da processare) */}
            {showInbox && (
                <Card className="border-purple-200">
                    <CardHeader className="py-3 px-5 bg-purple-50 border-b border-purple-100 flex flex-row items-center justify-between">
                        <CardTitle className="text-sm font-semibold text-purple-900 flex items-center gap-2">
                            <Package className="h-4 w-4" /> Inbox — Fatture da Processare
                        </CardTitle>
                        <Button variant="ghost" size="sm" onClick={() => setShowInbox(false)}>
                            <ChevronUp className="h-4 w-4" />
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        {inbox.length === 0 ? (
                            <p className="text-sm text-gray-500 p-4">Nessuna fattura in attesa.</p>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {inbox.map(fr => (
                                    <div key={fr.fr_id} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50" data-testid={`inbox-item-${fr.fr_id}`}>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-[#1E293B] truncate">
                                                Fatt. {fr.numero_documento} — {fr.fornitore_nome}
                                            </p>
                                            <p className="text-xs text-gray-500">
                                                {formatDate(fr.data_documento)} · {formatCurrency(fr.totale_documento)}
                                            </p>
                                        </div>
                                        <a
                                            href="/fatture-ricevute"
                                            className="text-xs text-[#0055FF] hover:underline flex items-center gap-1"
                                        >
                                            Processa <ArrowRight className="h-3 w-3" />
                                        </a>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
                <Filter className="h-4 w-4 text-gray-400" />
                <select
                    className="text-sm border border-gray-200 rounded-md px-2.5 py-1.5 bg-white text-[#1E293B]"
                    value={filterTipo}
                    onChange={e => setFilterTipo(e.target.value)}
                    data-testid="filter-tipo"
                >
                    <option value="tutti">Tutti i tipi</option>
                    <option value="pagamento">Pagamenti</option>
                    <option value="patentino">Patentini</option>
                    <option value="taratura">Tarature</option>
                    <option value="consegna">Consegne</option>
                </select>
                <select
                    className="text-sm border border-gray-200 rounded-md px-2.5 py-1.5 bg-white text-[#1E293B]"
                    value={filterStato}
                    onChange={e => setFilterStato(e.target.value)}
                    data-testid="filter-stato"
                >
                    <option value="tutti">Tutti gli stati</option>
                    <option value="scaduto">Scaduti</option>
                    <option value="in_scadenza">In scadenza</option>
                    <option value="ok">OK</option>
                </select>
                <span className="text-xs text-gray-400 ml-2">{scadenze.length} scadenze</span>
            </div>

            {/* Timeline grouped by month */}
            {Object.keys(grouped).length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
                        <p className="text-sm text-gray-500">Nessuna scadenza trovata con i filtri selezionati.</p>
                    </CardContent>
                </Card>
            ) : (
                Object.entries(grouped).map(([month, items]) => (
                    <MonthGroup key={month} month={month} items={items} />
                ))
            )}
        </div>
    );
}

function KPICard({ icon: Icon, label, value, color, count, testId, onClick }) {
    return (
        <Card
            className={`${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
            onClick={onClick}
            data-testid={testId}
        >
            <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                    <div className="p-1.5 rounded-md" style={{ backgroundColor: `${color}15` }}>
                        <Icon className="h-4 w-4" style={{ color }} />
                    </div>
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
                </div>
                <p className="text-xl font-bold text-[#1E293B]">{value}</p>
                {count != null && count > 0 && (
                    <p className="text-xs text-gray-400 mt-0.5">{count} scadenze</p>
                )}
            </CardContent>
        </Card>
    );
}

function MonthGroup({ month, items }) {
    const [expanded, setExpanded] = useState(true);
    const monthLabel = month === 'senza_data'
        ? 'Senza data'
        : new Date(month + '-01').toLocaleDateString('it-IT', { month: 'long', year: 'numeric' });

    return (
        <Card>
            <CardHeader
                className="py-2.5 px-5 bg-gray-50 border-b border-gray-100 cursor-pointer flex flex-row items-center justify-between"
                onClick={() => setExpanded(!expanded)}
            >
                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-[#0055FF]" />
                    {monthLabel}
                    <Badge variant="outline" className="text-xs ml-1">{items.length}</Badge>
                </CardTitle>
                {expanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
            </CardHeader>
            {expanded && (
                <CardContent className="p-0">
                    <div className="divide-y divide-gray-50">
                        {items.map((s, i) => (
                            <ScadenzaRow key={`${s.id}-${i}`} item={s} />
                        ))}
                    </div>
                </CardContent>
            )}
        </Card>
    );
}

function ScadenzaRow({ item }) {
    const config = TIPO_CONFIG[item.tipo] || TIPO_CONFIG.pagamento;
    const stato = STATO_BADGE[item.stato] || STATO_BADGE.ok;
    const Icon = config.icon;

    return (
        <div className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50/50 transition-colors" data-testid={`scadenza-${item.id}`}>
            <div className="p-1.5 rounded-md shrink-0" style={{ backgroundColor: `${config.color}12` }}>
                <Icon className="h-4 w-4" style={{ color: config.color }} />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-[#1E293B] truncate">{item.titolo}</p>
                    <Badge className={`text-[10px] px-1.5 py-0 ${stato.className}`}>{stato.label}</Badge>
                    {item.processata === false && item.tipo === 'pagamento' && (
                        <Badge className="text-[10px] px-1.5 py-0 bg-purple-100 text-purple-700">Da processare</Badge>
                    )}
                </div>
                <p className="text-xs text-gray-500 truncate">{item.sottotitolo}</p>
            </div>
            <div className="text-right shrink-0">
                <p className="text-sm font-semibold text-[#1E293B]">
                    {item.importo != null ? formatCurrency(item.importo) : ''}
                </p>
                <p className="text-xs text-gray-400">{formatDate(item.data_scadenza)}</p>
            </div>
        </div>
    );
}
