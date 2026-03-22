import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import {
    AlertTriangle, CheckCircle2, XCircle, Clock, Shield, RefreshCw,
    Loader2, ExternalLink, ChevronDown, ChevronUp, Filter,
} from 'lucide-react';

const SEVERITY_COLORS = {
    alta: 'bg-red-100 text-red-800',
    media: 'bg-amber-100 text-amber-800',
    bassa: 'bg-blue-100 text-blue-700',
};

const BLOCKING_ICON = {
    hard_block: { Icon: XCircle, cls: 'text-red-500' },
    warning: { Icon: AlertTriangle, cls: 'text-amber-500' },
    none: { Icon: Clock, cls: 'text-slate-400' },
};

const STATUS_CONFIG = {
    bloccante: { label: 'Bloccante', color: 'bg-red-100 text-red-800' },
    nuovo: { label: 'Nuovo', color: 'bg-blue-100 text-blue-700' },
    da_verificare: { label: 'Da verificare', color: 'bg-amber-100 text-amber-800' },
    in_corso: { label: 'In corso', color: 'bg-sky-100 text-sky-800' },
    completato: { label: 'Completato', color: 'bg-emerald-100 text-emerald-800' },
    chiuso: { label: 'Chiuso', color: 'bg-slate-100 text-slate-600' },
    non_applicabile: { label: 'N/A', color: 'bg-gray-100 text-gray-500' },
};

const SOURCE_LABELS = {
    evidence_gate: 'Evidence Gate',
    gate_pos: 'Gate POS',
    soggetti: 'Soggetti',
    istruttoria: 'Istruttoria',
    rami_normativi: 'Rami Normativi',
    documenti_scadenza: 'Scadenze Doc.',
    pacchetti_documentali: 'Pacchetti Doc.',
    committenza: 'Committenza',
};

const CATEGORY_LABELS = {
    istruttoria: 'Istruttoria',
    qualita: 'Qualita',
    sicurezza: 'Sicurezza',
    documentale: 'Documentale',
    emissione: 'Emissione',
    soggetti: 'Soggetti',
    commessa: 'Commessa',
};

const ROLE_LABELS = {
    ufficio_tecnico: 'Uff. Tecnico',
    sicurezza: 'Sicurezza',
    amministrazione: 'Amm.ne',
    produzione: 'Produzione',
    qualita: 'Qualita',
    commerciale: 'Commerciale',
};

const SLA_LABELS = {
    manuale: '',
    da_documento_cliente: 'da cliente',
    da_scadenza_documento: 'da scadenza',
    da_emissione: 'da emissione',
    da_cantiere: 'da cantiere',
    da_pacchetto_documentale: 'da pacchetto',
};

function ObbligRow({ obl, onNavigate, onUpdateStatus, onUpdateField }) {
    const sc = STATUS_CONFIG[obl.status] || STATUS_CONFIG.nuovo;
    const bl = BLOCKING_ICON[obl.blocking_level] || BLOCKING_ICON.none;
    const BlIcon = bl.Icon;

    // Due date coloring
    const dueDateCls = (() => {
        if (!obl.due_date) return '';
        const today = new Date().toISOString().slice(0, 10);
        if (obl.due_date.slice(0, 10) < today) return 'text-red-600 font-medium';
        const soon = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
        if (obl.due_date.slice(0, 10) <= soon) return 'text-amber-600';
        return 'text-slate-500';
    })();

    return (
        <div
            className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                obl.blocking_level === 'hard_block' ? 'border-red-200 bg-red-50/40' :
                obl.blocking_level === 'warning' ? 'border-amber-200 bg-amber-50/30' :
                'border-gray-200 bg-white'
            }`}
            data-testid={`obbligo-${obl.obbligo_id}`}
        >
            <BlIcon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${bl.cls}`} />
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 leading-snug">{obl.title}</p>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                    <Badge className={`text-[10px] ${sc.color}`}>{sc.label}</Badge>
                    <Badge className={`text-[10px] ${SEVERITY_COLORS[obl.severity] || ''}`}>{obl.severity}</Badge>
                    <Badge className="text-[10px] bg-slate-100 text-slate-600">{SOURCE_LABELS[obl.source_module] || obl.source_module}</Badge>
                    {obl.category && <Badge className="text-[10px] bg-violet-50 text-violet-700">{CATEGORY_LABELS[obl.category] || obl.category}</Badge>}
                    {obl.owner_role && <Badge className="text-[10px] bg-cyan-50 text-cyan-700">{ROLE_LABELS[obl.owner_role] || obl.owner_role}</Badge>}
                    {obl.due_date && <span className={`text-[10px] ${dueDateCls}`}>{obl.due_date.slice(0, 10)}</span>}
                    {obl.sla_source && <span className="text-[10px] text-slate-400">{SLA_LABELS[obl.sla_source] || ''}</span>}
                </div>
                {obl.description && obl.description !== obl.title && (
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{obl.description}</p>
                )}
                {obl.resolution_note && (
                    <p className="text-xs text-emerald-600 mt-1 italic">{obl.resolution_note}</p>
                )}
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
                {obl.status !== 'completato' && obl.status !== 'chiuso' && obl.status !== 'non_applicabile' && (
                    <>
                        <Select value={obl.owner_role || ''} onValueChange={v => onUpdateField(obl.obbligo_id, 'owner_role', v)}>
                            <SelectTrigger className="h-7 text-[10px] w-[90px]" data-testid={`role-select-${obl.obbligo_id}`}>
                                <SelectValue placeholder="Ruolo" />
                            </SelectTrigger>
                            <SelectContent>
                                {Object.entries(ROLE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        <input
                            type="date"
                            className="h-7 text-[10px] border rounded px-1 w-[105px] text-slate-600"
                            value={obl.due_date?.slice(0, 10) || ''}
                            onChange={e => onUpdateField(obl.obbligo_id, 'due_date', e.target.value || null)}
                            data-testid={`date-${obl.obbligo_id}`}
                        />
                        <Select value={obl.status} onValueChange={v => onUpdateStatus(obl.obbligo_id, v)}>
                            <SelectTrigger className="h-7 text-[10px] w-[100px]" data-testid={`status-select-${obl.obbligo_id}`}>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="nuovo">Nuovo</SelectItem>
                                <SelectItem value="da_verificare">Da verificare</SelectItem>
                                <SelectItem value="in_corso">In corso</SelectItem>
                                <SelectItem value="completato">Completato</SelectItem>
                                <SelectItem value="non_applicabile">N/A</SelectItem>
                            </SelectContent>
                        </Select>
                    </>
                )}
                {obl.linked_route && (
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-[#0055FF]"
                        onClick={() => onNavigate(obl.linked_route)}
                        data-testid={`btn-open-${obl.obbligo_id}`}
                    >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        <span className="text-[10px]">{obl.linked_label || 'Apri'}</span>
                    </Button>
                )}
            </div>
        </div>
    );
}

export default function ObbrighiCommessaSection({ commessaId }) {
    const [obblighi, setObblighi] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [expanded, setExpanded] = useState(true);
    const [showClosed, setShowClosed] = useState(false);
    const [filterSource, setFilterSource] = useState('');
    const [filterCategory, setFilterCategory] = useState('');

    const loadData = useCallback(async () => {
        try {
            const [obls, sum] = await Promise.all([
                apiRequest(`/obblighi/commessa/${commessaId}`),
                apiRequest(`/obblighi/summary/${commessaId}`),
            ]);
            setObblighi(obls);
            setSummary(sum);
        } catch (err) {
            // Silently handle — section is optional context
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { loadData(); }, [loadData]);

    const handleSync = async () => {
        setSyncing(true);
        try {
            const result = await apiRequest(`/obblighi/sync/${commessaId}`, { method: 'POST' });
            toast.success(`Obblighi sincronizzati: ${result.created} nuovi, ${result.updated} aggiornati, ${result.closed} chiusi`);
            await loadData();
        } catch (err) {
            toast.error(err.message || 'Errore sync obblighi');
        } finally {
            setSyncing(false);
        }
    };

    const handleUpdateStatus = async (obblId, newStatus) => {
        try {
            await apiRequest(`/obblighi/${obblId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus }),
            });
            setObblighi(prev => prev.map(o =>
                o.obbligo_id === obblId ? { ...o, status: newStatus } : o
            ));
            toast.success('Stato aggiornato');
        } catch (err) {
            toast.error('Errore aggiornamento');
        }
    };

    const handleUpdateField = async (obblId, field, value) => {
        try {
            await apiRequest(`/obblighi/${obblId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [field]: value }),
            });
            setObblighi(prev => prev.map(o =>
                o.obbligo_id === obblId ? { ...o, [field]: value } : o
            ));
        } catch (err) {
            toast.error('Errore aggiornamento');
        }
    };

    const handleNavigate = (route) => {
        window.location.href = route;
    };

    // Grouping
    const bloccanti = obblighi.filter(o => o.blocking_level === 'hard_block' && !['completato', 'chiuso', 'non_applicabile'].includes(o.status));
    const daCompletare = obblighi.filter(o => ['nuovo', 'in_corso'].includes(o.status) && o.blocking_level !== 'hard_block');
    const daVerificare = obblighi.filter(o => o.status === 'da_verificare');
    const chiusi = obblighi.filter(o => ['completato', 'chiuso', 'non_applicabile'].includes(o.status));

    // Apply filters
    const applyFilter = (list) => list.filter(o => {
        if (filterSource && o.source_module !== filterSource) return false;
        if (filterCategory && o.category !== filterCategory) return false;
        return true;
    });

    const s = summary || {};
    const hasFilters = filterSource || filterCategory;

    if (loading) return null; // Don't show empty section while loading
    if (!summary && obblighi.length === 0) {
        // Show a minimal sync prompt instead of nothing
        return (
            <Card className="border-gray-200" data-testid="obblighi-section-empty">
                <CardContent className="p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Shield className="h-4 w-4" /> Registro Obblighi
                    </div>
                    <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing} data-testid="btn-sync-obblighi-empty">
                        {syncing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
                        Analizza obblighi
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={`${bloccanti.length > 0 ? 'border-red-300 bg-red-50/20' : 'border-gray-200'}`} data-testid="obblighi-section">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle
                        className="text-sm flex items-center gap-2 cursor-pointer select-none"
                        onClick={() => setExpanded(!expanded)}
                        data-testid="obblighi-header-toggle"
                    >
                        <Shield className="h-4 w-4 text-[#0055FF]" />
                        Registro Obblighi
                        {expanded ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-400" />}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {/* Summary counters */}
                        {s.bloccanti > 0 && <Badge className="bg-red-100 text-red-800 text-[10px]" data-testid="count-bloccanti">{s.bloccanti} bloccanti</Badge>}
                        {s.aperti > 0 && <Badge className="bg-amber-100 text-amber-800 text-[10px]" data-testid="count-aperti">{s.aperti} aperti</Badge>}
                        {s.da_verificare > 0 && <Badge className="bg-sky-100 text-sky-800 text-[10px]" data-testid="count-da-verificare">{s.da_verificare} da verificare</Badge>}
                        {s.chiusi > 0 && <Badge className="bg-emerald-100 text-emerald-800 text-[10px]" data-testid="count-chiusi">{s.chiusi} chiusi</Badge>}
                        <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing} className="h-7" data-testid="btn-sync-obblighi">
                            {syncing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                        </Button>
                    </div>
                </div>
            </CardHeader>

            {expanded && (
                <CardContent className="pt-0 space-y-3">
                    {/* Filters */}
                    <div className="flex items-center gap-2 flex-wrap">
                        <Filter className="h-3 w-3 text-slate-400" />
                        <Select value={filterSource} onValueChange={v => setFilterSource(v === 'all' ? '' : v)}>
                            <SelectTrigger className="h-7 text-[10px] w-[130px]" data-testid="filter-source">
                                <SelectValue placeholder="Fonte" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Tutte le fonti</SelectItem>
                                {Object.entries(SOURCE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        <Select value={filterCategory} onValueChange={v => setFilterCategory(v === 'all' ? '' : v)}>
                            <SelectTrigger className="h-7 text-[10px] w-[120px]" data-testid="filter-category">
                                <SelectValue placeholder="Categoria" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Tutte</SelectItem>
                                {Object.entries(CATEGORY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        {hasFilters && (
                            <Button variant="ghost" size="sm" className="h-7 text-[10px]" onClick={() => { setFilterSource(''); setFilterCategory(''); }}>
                                Rimuovi filtri
                            </Button>
                        )}
                    </div>

                    {/* Group: Bloccanti */}
                    {applyFilter(bloccanti).length > 0 && (
                        <div data-testid="group-bloccanti">
                            <p className="text-xs font-bold text-red-700 mb-1.5 uppercase tracking-wider">Bloccanti</p>
                            <div className="space-y-1.5">
                                {applyFilter(bloccanti).map(o => <ObbligRow key={o.obbligo_id} obl={o} onNavigate={handleNavigate} onUpdateStatus={handleUpdateStatus} onUpdateField={handleUpdateField} />)}
                            </div>
                        </div>
                    )}

                    {/* Group: Da completare */}
                    {applyFilter(daCompletare).length > 0 && (
                        <div data-testid="group-da-completare">
                            <p className="text-xs font-bold text-amber-700 mb-1.5 uppercase tracking-wider">Da completare</p>
                            <div className="space-y-1.5">
                                {applyFilter(daCompletare).map(o => <ObbligRow key={o.obbligo_id} obl={o} onNavigate={handleNavigate} onUpdateStatus={handleUpdateStatus} onUpdateField={handleUpdateField} />)}
                            </div>
                        </div>
                    )}

                    {/* Group: Da verificare */}
                    {applyFilter(daVerificare).length > 0 && (
                        <div data-testid="group-da-verificare">
                            <p className="text-xs font-bold text-sky-700 mb-1.5 uppercase tracking-wider">Da verificare</p>
                            <div className="space-y-1.5">
                                {applyFilter(daVerificare).map(o => <ObbligRow key={o.obbligo_id} obl={o} onNavigate={handleNavigate} onUpdateStatus={handleUpdateStatus} onUpdateField={handleUpdateField} />)}
                            </div>
                        </div>
                    )}

                    {/* Group: Chiusi */}
                    {chiusi.length > 0 && (
                        <div data-testid="group-chiusi">
                            <Button variant="ghost" size="sm" className="text-[10px] text-slate-400 h-6 p-0"
                                onClick={() => setShowClosed(!showClosed)}
                                data-testid="btn-toggle-chiusi"
                            >
                                {showClosed ? <ChevronUp className="h-3 w-3 mr-1" /> : <ChevronDown className="h-3 w-3 mr-1" />}
                                {chiusi.length} chiusi
                            </Button>
                            {showClosed && (
                                <div className="space-y-1.5 mt-1.5 opacity-60">
                                    {applyFilter(chiusi).map(o => <ObbligRow key={o.obbligo_id} obl={o} onNavigate={handleNavigate} onUpdateStatus={handleUpdateStatus} onUpdateField={handleUpdateField} />)}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Empty state */}
                    {obblighi.length === 0 && (
                        <p className="text-xs text-slate-400 text-center py-3">Nessun obbligo rilevato. Clicca il pulsante sync per analizzare.</p>
                    )}
                    {obblighi.length > 0 && applyFilter(bloccanti).length === 0 && applyFilter(daCompletare).length === 0 && applyFilter(daVerificare).length === 0 && !showClosed && (
                        <div className="flex items-center gap-2 text-xs text-emerald-600 py-2" data-testid="all-clear">
                            <CheckCircle2 className="h-4 w-4" />
                            Tutti gli obblighi aperti sono risolti.
                        </div>
                    )}
                </CardContent>
            )}
        </Card>
    );
}
