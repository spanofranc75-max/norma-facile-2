import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { TrendingUp, TrendingDown, AlertTriangle, BarChart3, Search, Eye, Activity, Loader2, ArrowUpRight, ArrowDownRight, Target } from 'lucide-react';
import { toast } from 'sonner';

const ALERT_COLORS = {
    verde: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    giallo: 'bg-amber-100 text-amber-700 border-amber-200',
    arancione: 'bg-orange-100 text-orange-700 border-orange-200',
    rosso: 'bg-red-100 text-red-700 border-red-200',
};
const ALERT_LABELS = { verde: 'Sano', giallo: 'Attenzione', arancione: 'Critico', rosso: 'In Perdita' };

function MarginBar({ pct }) {
    const w = Math.min(Math.abs(pct), 100);
    const color = pct >= 20 ? 'bg-emerald-500' : pct >= 10 ? 'bg-amber-500' : pct >= 0 ? 'bg-orange-500' : 'bg-red-500';
    return (
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${w}%` }} />
        </div>
    );
}

function KpiCard({ label, value, sub, icon: Icon, color = 'text-slate-700' }) {
    return (
        <div className="bg-white border rounded-xl p-4 space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-500">
                {Icon && <Icon className="h-3.5 w-3.5" />} {label}
            </div>
            <p className={`text-xl font-bold ${color}`}>{value}</p>
            {sub && <p className="text-[11px] text-slate-400">{sub}</p>}
        </div>
    );
}

function DetailDialog({ commessaId, open, onClose }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!open || !commessaId) return;
        (async () => {
            setLoading(true);
            try {
                const d = await apiRequest(`/costs/commessa/${commessaId}/predict`);
                setData(d);
            } catch (e) { toast.error(e.message); }
            finally { setLoading(false); }
        })();
    }, [commessaId, open]);

    if (!open) return null;

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="margin-detail-dialog">
                <DialogHeader>
                    <DialogTitle className="text-lg">
                        {data ? `${data.numero} — ${data.title}` : 'Caricamento...'}
                    </DialogTitle>
                </DialogHeader>
                {loading && <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>}
                {data && !loading && (
                    <div className="space-y-5">
                        {/* Summary */}
                        <div className="grid grid-cols-3 gap-3">
                            <KpiCard label="Ricavo" value={fmtEur(data.ricavo)} icon={TrendingUp} color="text-slate-800" />
                            <KpiCard label="Costi Totali" value={fmtEur(data.costo_totale)} icon={TrendingDown} color="text-red-600" />
                            <KpiCard label="Margine" value={`${fmtEur(data.margine)} (${data.margine_pct}%)`}
                                icon={data.margine >= 0 ? TrendingUp : TrendingDown}
                                color={data.margine >= 0 ? 'text-emerald-600' : 'text-red-600'} />
                        </div>
                        <MarginBar pct={data.margine_pct} />

                        {/* Cost Breakdown */}
                        <Card>
                            <CardHeader className="py-3 px-4">
                                <CardTitle className="text-sm">Dettaglio Costi</CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4 space-y-2 text-sm">
                                <div className="flex justify-between"><span className="text-slate-500">Materiali (manuali)</span><span className="font-mono">{fmtEur(data.costi_materiali_manuali)}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Fatture imputate</span><span className="font-mono">{fmtEur(data.costi_fatture_imputate)}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Lavorazioni esterne</span><span className="font-mono">{fmtEur(data.costi_esterni)}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Manodopera ({data.ore_lavorate}h x {fmtEur(data.costo_orario)}/h)</span><span className="font-mono">{fmtEur(data.costo_personale)}</span></div>
                                <div className="flex justify-between border-t pt-2 font-bold"><span>Totale Costi</span><span className="font-mono text-red-600">{fmtEur(data.costo_totale)}</span></div>
                            </CardContent>
                        </Card>

                        {/* Fatture imputate detail */}
                        {data.fatture_imputate_detail?.length > 0 && (
                            <Card>
                                <CardHeader className="py-3 px-4"><CardTitle className="text-sm">Fatture Fornitori Imputate</CardTitle></CardHeader>
                                <CardContent className="px-4 pb-3">
                                    {data.fatture_imputate_detail.map((f, i) => (
                                        <div key={i} className="flex justify-between text-xs py-1 border-b last:border-0">
                                            <span className="text-slate-600">{f.fornitore} — {f.numero}</span>
                                            <span className="font-mono">{fmtEur(f.importo)}</span>
                                        </div>
                                    ))}
                                </CardContent>
                            </Card>
                        )}

                        {/* AI Prediction */}
                        {data.prediction && (
                            <Card className={`border-2 ${data.prediction.risk === 'alto' ? 'border-red-300 bg-red-50/30' : data.prediction.risk === 'medio' ? 'border-amber-300 bg-amber-50/30' : 'border-emerald-300 bg-emerald-50/30'}`}>
                                <CardHeader className="py-3 px-4">
                                    <CardTitle className="text-sm flex items-center gap-2">
                                        <Activity className="h-4 w-4" /> Previsione AI
                                        <Badge className={`text-[10px] ${data.prediction.risk === 'alto' ? 'bg-red-200 text-red-800' : data.prediction.risk === 'medio' ? 'bg-amber-200 text-amber-800' : 'bg-emerald-200 text-emerald-800'}`}>
                                            Rischio {data.prediction.risk}
                                        </Badge>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4 pb-4 space-y-3 text-sm">
                                    <p className="text-slate-600">{data.prediction.risk_msg}</p>
                                    <div className="grid grid-cols-2 gap-3 text-xs">
                                        <div className="bg-white rounded-lg p-3 border">
                                            <p className="text-slate-400">Margine Stimato</p>
                                            <p className="font-bold text-lg">{data.prediction.margine_stimato_pct}%</p>
                                            <p className="text-slate-500">{fmtEur(data.prediction.margine_stimato)}</p>
                                        </div>
                                        <div className="bg-white rounded-lg p-3 border">
                                            <p className="text-slate-400">Ore Stimate</p>
                                            <p className="font-bold text-lg">{data.prediction.ore_stimate}h</p>
                                            <p className="text-slate-500">Usate: {data.ore_lavorate}h ({data.prediction.progress_ore_pct}%)</p>
                                        </div>
                                    </div>
                                    <p className="text-[10px] text-slate-400">
                                        Basato su {data.prediction.num_commesse_confronto} commesse storiche (media margine: {data.prediction.avg_margin_storico}%)
                                    </p>
                                </CardContent>
                            </Card>
                        )}
                        {!data.prediction && data.prediction_msg && (
                            <div className="text-center py-4 bg-slate-50 rounded-lg border border-dashed">
                                <Activity className="h-5 w-5 text-slate-400 mx-auto mb-1" />
                                <p className="text-xs text-slate-500">{data.prediction_msg}</p>
                            </div>
                        )}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}

export default function MarginAnalysisPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [filterAlert, setFilterAlert] = useState('all');
    const [filterStato, setFilterStato] = useState('all');
    const [detailId, setDetailId] = useState(null);

    const fetch_ = useCallback(async () => {
        setLoading(true);
        try {
            const d = await apiRequest('/costs/margin-full');
            setData(d);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetch_(); }, [fetch_]);

    const filtered = (data?.commesse || []).filter(c => {
        if (search) {
            const s = search.toLowerCase();
            if (!c.numero?.toLowerCase().includes(s) && !c.title?.toLowerCase().includes(s) && !c.client_name?.toLowerCase().includes(s)) return false;
        }
        if (filterAlert !== 'all' && c.alert !== filterAlert) return false;
        if (filterStato !== 'all' && c.stato !== filterStato) return false;
        return true;
    });

    const summary = {
        rosso: filtered.filter(c => c.alert === 'rosso').length,
        arancione: filtered.filter(c => c.alert === 'arancione').length,
        giallo: filtered.filter(c => c.alert === 'giallo').length,
        verde: filtered.filter(c => c.alert === 'verde').length,
    };

    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="margin-analysis-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                            <BarChart3 className="h-5 w-5 text-indigo-600" /> Analisi Margini
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Margine reale per commessa — Materiali + Fatture Imputate + Manodopera + Lavorazioni Esterne
                        </p>
                    </div>
                    {data && (
                        <div className="text-right">
                            <p className="text-xs text-slate-400">Costo Orario Pieno</p>
                            <p className="text-lg font-bold text-slate-700">{fmtEur(data.costo_orario)}/h</p>
                        </div>
                    )}
                </div>

                {/* KPI Cards */}
                {data && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <KpiCard label="Ricavi Totali" value={fmtEur(data.totale_ricavi)} icon={TrendingUp} color="text-slate-800" />
                        <KpiCard label="Costi Totali" value={fmtEur(data.totale_costi)} icon={TrendingDown} color="text-red-600" />
                        <KpiCard label="Margine Totale" value={fmtEur(data.margine_totale)}
                            icon={data.margine_totale >= 0 ? ArrowUpRight : ArrowDownRight}
                            color={data.margine_totale >= 0 ? 'text-emerald-600' : 'text-red-600'} />
                        <KpiCard label="Margine Medio" value={`${data.margine_medio_pct}%`} icon={Target}
                            sub={`${data.total} commesse`}
                            color={data.margine_medio_pct >= 15 ? 'text-emerald-600' : data.margine_medio_pct >= 0 ? 'text-amber-600' : 'text-red-600'} />
                    </div>
                )}

                {/* Alert Summary */}
                <div className="flex gap-2">
                    {[['rosso', 'In Perdita'], ['arancione', 'Critiche'], ['giallo', 'Attenzione'], ['verde', 'Sane']].map(([k, label]) => (
                        <button key={k} onClick={() => setFilterAlert(filterAlert === k ? 'all' : k)}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${filterAlert === k ? ALERT_COLORS[k] + ' ring-2 ring-offset-1' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}`}
                            data-testid={`filter-alert-${k}`}>
                            {summary[k]} {label}
                        </button>
                    ))}
                </div>

                {/* Filters */}
                <div className="flex gap-3 items-center">
                    <div className="relative flex-1 max-w-xs">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                        <Input placeholder="Cerca commessa..." value={search} onChange={e => setSearch(e.target.value)}
                            className="pl-9 h-9 text-sm" data-testid="margin-search" />
                    </div>
                    <Select value={filterStato} onValueChange={setFilterStato}>
                        <SelectTrigger className="w-40 h-9 text-sm" data-testid="filter-stato">
                            <SelectValue placeholder="Stato" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">Tutti gli stati</SelectItem>
                            <SelectItem value="aperto">Aperte</SelectItem>
                            <SelectItem value="in_lavorazione">In Lavorazione</SelectItem>
                            <SelectItem value="chiuso">Chiuse</SelectItem>
                            <SelectItem value="fatturato">Fatturate</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Table */}
                {loading ? (
                    <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
                ) : (
                    <Card>
                        <CardContent className="p-0">
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="bg-slate-50 border-b">
                                            <th className="text-left py-2.5 px-3 font-medium text-slate-600 text-xs">Commessa</th>
                                            <th className="text-left py-2.5 px-3 font-medium text-slate-600 text-xs">Cliente</th>
                                            <th className="text-right py-2.5 px-3 font-medium text-slate-600 text-xs">Valore</th>
                                            <th className="text-right py-2.5 px-3 font-medium text-slate-600 text-xs">Materiali</th>
                                            <th className="text-right py-2.5 px-3 font-medium text-slate-600 text-xs">Personale</th>
                                            <th className="text-right py-2.5 px-3 font-medium text-slate-600 text-xs">Costo Tot.</th>
                                            <th className="text-right py-2.5 px-3 font-medium text-slate-600 text-xs">Margine</th>
                                            <th className="text-center py-2.5 px-3 font-medium text-slate-600 text-xs w-24">Salute</th>
                                            <th className="w-10"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filtered.map(c => (
                                            <tr key={c.commessa_id} className="border-b hover:bg-slate-50/60 transition-colors cursor-pointer"
                                                onClick={() => setDetailId(c.commessa_id)} data-testid={`margin-row-${c.commessa_id}`}>
                                                <td className="py-2.5 px-3">
                                                    <p className="font-semibold text-slate-800 text-xs">{c.numero}</p>
                                                    <p className="text-[11px] text-slate-400 truncate max-w-[180px]">{c.title}</p>
                                                </td>
                                                <td className="py-2.5 px-3 text-xs text-slate-600 max-w-[140px] truncate">{c.client_name}</td>
                                                <td className="py-2.5 px-3 text-right font-mono text-xs">{fmtEur(c.valore)}</td>
                                                <td className="py-2.5 px-3 text-right font-mono text-xs text-slate-500">{fmtEur(c.costi_materiali)}</td>
                                                <td className="py-2.5 px-3 text-right font-mono text-xs text-slate-500">{c.ore > 0 ? `${fmtEur(c.costo_personale)} (${c.ore}h)` : '-'}</td>
                                                <td className="py-2.5 px-3 text-right font-mono text-xs font-medium text-red-600">{fmtEur(c.costo_totale)}</td>
                                                <td className="py-2.5 px-3 text-right">
                                                    <span className={`font-mono text-xs font-bold ${c.margine >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                        {fmtEur(c.margine)}
                                                    </span>
                                                    <span className={`ml-1 text-[10px] ${c.margine >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                        ({c.margine_pct > 0 ? '+' : ''}{c.margine_pct}%)
                                                    </span>
                                                </td>
                                                <td className="py-2.5 px-3 text-center">
                                                    <Badge className={`text-[10px] ${ALERT_COLORS[c.alert]}`}>
                                                        {ALERT_LABELS[c.alert]}
                                                    </Badge>
                                                </td>
                                                <td className="py-2.5 px-1">
                                                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" data-testid={`margin-detail-${c.commessa_id}`}>
                                                        <Eye className="h-3.5 w-3.5 text-slate-400" />
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))}
                                        {filtered.length === 0 && (
                                            <tr><td colSpan={9} className="text-center py-8 text-sm text-slate-400">
                                                {search || filterAlert !== 'all' ? 'Nessuna commessa corrisponde ai filtri' : 'Nessuna commessa trovata'}
                                            </td></tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>

            <DetailDialog commessaId={detailId} open={!!detailId} onClose={() => setDetailId(null)} />
        </DashboardLayout>
    );
}
