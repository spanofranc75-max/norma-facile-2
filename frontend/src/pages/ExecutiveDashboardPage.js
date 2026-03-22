/**
 * ExecutiveDashboardPage — Cruscotto del Titolare multi-normativa.
 * Vista unica: EN 1090 (Strutture) | EN 13241 (Chiusure) | Generica.
 * Mostra audit-readiness, indice rischio, efficienza produttiva, scadenze.
 */
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
    RefreshCw, Shield, AlertTriangle, CheckCircle2, Clock,
    TrendingUp, Factory, Hammer, DoorOpen, Package, FileText,
    Leaf, ArrowDown,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../components/DashboardLayout';

const SETTORE_CFG = {
    EN_1090:  { icon: Factory,   color: 'indigo', label: 'EN 1090 — Strutture',       border: 'border-indigo-200', bg: 'bg-indigo-50/40', accent: 'text-indigo-700' },
    EN_13241: { icon: DoorOpen,  color: 'amber',  label: 'EN 13241 — Chiusure',       border: 'border-amber-200',  bg: 'bg-amber-50/40',  accent: 'text-amber-700' },
    GENERICA: { icon: Hammer,    color: 'slate',  label: 'Generica — Senza Marcatura', border: 'border-slate-200',  bg: 'bg-slate-50/30',  accent: 'text-slate-600' },
};

function fmtDate(d) {
    if (!d) return '—';
    const p = d.slice(0, 10).split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
}

function fmtMoney(v) {
    return (v || 0).toLocaleString('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
}

function AuditBadge({ ok, label }) {
    return ok
        ? <Badge className="text-[9px] px-1.5 py-0 bg-emerald-100 text-emerald-700">{label}</Badge>
        : <Badge className="text-[9px] px-1.5 py-0 bg-red-100 text-red-600">{label}</Badge>;
}

function SectorSection({ skey, data, navigate }) {
    const cfg = SETTORE_CFG[skey] || SETTORE_CFG.GENERICA;
    const Icon = cfg.icon;
    const stats = data.stats || {};
    const commesse = data.commesse || [];
    const isNormed = skey !== 'GENERICA';

    return (
        <Card className={`${cfg.border} overflow-hidden`} data-testid={`sector-${skey}`}>
            {/* Sector Header */}
            <div className={`${cfg.bg} px-4 py-3 border-b ${cfg.border} flex items-center justify-between`}>
                <div className="flex items-center gap-2.5">
                    <Icon className={`h-5 w-5 ${cfg.accent}`} />
                    <div>
                        <h2 className={`text-sm font-bold ${cfg.accent}`}>{cfg.label}</h2>
                        <p className="text-[10px] text-slate-500">
                            {stats.totale_commesse || 0} commesse — {fmtMoney(stats.valore_totale)}
                        </p>
                    </div>
                </div>
                {/* KPI Badges */}
                <div className="flex gap-2">
                    {isNormed && (
                        <>
                            <div className="text-center">
                                <p className={`text-lg font-bold font-mono ${(stats.indice_rischio || 0) > 30 ? 'text-red-600' : 'text-emerald-600'}`}>
                                    {stats.indice_rischio || 0}%
                                </p>
                                <p className="text-[8px] text-slate-400 uppercase tracking-wider">Rischio</p>
                            </div>
                            <div className="text-center ml-3">
                                <p className="text-lg font-bold font-mono text-emerald-600">{stats.audit_ready || 0}/{stats.totale_commesse || 0}</p>
                                <p className="text-[8px] text-slate-400 uppercase tracking-wider">Audit-Ready</p>
                            </div>
                        </>
                    )}
                    {!isNormed && (
                        <div className="text-center">
                            <p className="text-lg font-bold font-mono text-slate-700">{stats.efficienza_produttiva || 0}%</p>
                            <p className="text-[8px] text-slate-400 uppercase tracking-wider">Efficienza</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Commesse Table */}
            {commesse.length === 0 ? (
                <div className="p-6 text-center text-slate-400 text-xs">
                    Nessuna commessa in questo settore
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-slate-50/80">
                                <TableHead className="text-[10px] font-semibold text-slate-500">Commessa</TableHead>
                                <TableHead className="text-[10px] font-semibold text-slate-500">Stato</TableHead>
                                <TableHead className="text-[10px] font-semibold text-slate-500">Valore</TableHead>
                                <TableHead className="text-[10px] font-semibold text-slate-500">Scadenza</TableHead>
                                <TableHead className="text-[10px] font-semibold text-slate-500">Produzione</TableHead>
                                {isNormed && <TableHead className="text-[10px] font-semibold text-slate-500">Audit</TableHead>}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {commesse.slice(0, 10).map((c, idx) => {
                                const dlCls = c.days_left !== null && c.days_left < 0 ? 'text-red-600 font-bold' :
                                              c.days_left !== null && c.days_left <= 7 ? 'text-amber-600 font-medium' : 'text-slate-600';
                                const prodPct = c.prod_total > 0 ? Math.round(c.prod_done / c.prod_total * 100) : 0;
                                return (
                                    <TableRow key={c.commessa_id}
                                        className={`${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'} hover:bg-blue-50/30 cursor-pointer transition-colors`}
                                        onClick={() => navigate(`/commesse/${c.commessa_id}`)}
                                        data-testid={`exec-row-${c.commessa_id}`}
                                    >
                                        <TableCell>
                                            <div className="text-xs font-medium text-slate-800">{c.numero}</div>
                                            <div className="text-[10px] text-slate-500 truncate max-w-[200px]">{c.title || c.client_name}</div>
                                            {c.mista && (
                                                <Badge variant="outline" className="text-[8px] px-1 py-0 mt-0.5 border-purple-300 text-purple-600">
                                                    MISTA
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-slate-200 text-slate-600">
                                                {c.stato}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-xs text-slate-700 font-mono">{fmtMoney(c.value)}</TableCell>
                                        <TableCell className={`text-xs ${dlCls}`}>
                                            {c.deadline ? fmtDate(c.deadline) : '—'}
                                            {c.days_left !== null && c.days_left < 0 && (
                                                <span className="text-[9px] ml-1">({Math.abs(c.days_left)}gg ritardo)</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-1.5">
                                                <div className="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                                    <div className="h-full bg-emerald-500 rounded-full transition-all"
                                                        style={{ width: `${prodPct}%` }} />
                                                </div>
                                                <span className="text-[10px] text-slate-500">{prodPct}%</span>
                                            </div>
                                        </TableCell>
                                        {isNormed && c.audit && (
                                            <TableCell>
                                                <div className="flex gap-1 flex-wrap">
                                                    <AuditBadge ok={c.audit.riesame_ok} label="Riesame" />
                                                    <AuditBadge ok={c.audit.ispezioni_ok} label="Ispezioni" />
                                                    <AuditBadge ok={c.audit.controllo_ok} label="Ctrl.Finale" />
                                                    {c.audit.dop_count > 0 && (
                                                        <Badge className="text-[9px] px-1.5 py-0 bg-indigo-100 text-indigo-700">
                                                            <FileText className="h-2.5 w-2.5 mr-0.5" />{c.audit.dop_count} DOP
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                        )}
                                        {isNormed && !c.audit && (
                                            <TableCell className="text-[10px] text-slate-400">—</TableCell>
                                        )}
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </div>
            )}
        </Card>
    );
}

export default function ExecutiveDashboardPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const fetch_ = useCallback(async () => {
        try {
            const d = await apiRequest('/dashboard/executive');
            setData(d);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetch_(); }, [fetch_]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    const scadenze = data?.scadenze_imminenti || [];

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="executive-dashboard-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                            Cruscotto Executive
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            {data?.totale_commesse || 0} commesse attive — {fmtMoney(data?.totale_valore)} portafoglio
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={fetch_} className="border-slate-200 text-slate-600" data-testid="refresh-executive">
                        <RefreshCw className="h-4 w-4 mr-1.5" /> Aggiorna
                    </Button>
                </div>

                {/* Scadenze Alert */}
                {scadenze.length > 0 && (
                    <Card className="border-red-200 bg-red-50/50" data-testid="scadenze-alert">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="h-4 w-4 text-red-600" />
                                <span className="text-xs font-bold text-red-800">
                                    {scadenze.length} scadenze nei prossimi 30 giorni
                                </span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {scadenze.slice(0, 6).map((s, i) => (
                                    <Badge key={i} className={`text-[9px] px-2 py-0.5 ${s.giorni < 0 ? 'bg-red-600 text-white' : s.giorni <= 7 ? 'bg-amber-500 text-white' : 'bg-amber-100 text-amber-700'}`}>
                                        {s.tipo === 'patentino' ? <Shield className="h-2.5 w-2.5 mr-1" /> :
                                         s.tipo === 'taratura' ? <Clock className="h-2.5 w-2.5 mr-1" /> :
                                         <Package className="h-2.5 w-2.5 mr-1" />}
                                        {s.nome} — {s.giorni < 0 ? `${Math.abs(s.giorni)}gg scaduto` : `${s.giorni}gg`}
                                    </Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* KPI Top Row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                        { label: 'Commesse Attive', value: data?.totale_commesse || 0, icon: Factory, color: 'text-slate-700' },
                        { label: 'EN 1090', value: data?.settori?.EN_1090?.stats?.totale_commesse || 0, icon: Shield, color: 'text-indigo-600' },
                        { label: 'EN 13241', value: data?.settori?.EN_13241?.stats?.totale_commesse || 0, icon: DoorOpen, color: 'text-amber-600' },
                        { label: 'Generiche', value: data?.settori?.GENERICA?.stats?.totale_commesse || 0, icon: Hammer, color: 'text-slate-500' },
                    ].map(kpi => {
                        const KIcon = kpi.icon;
                        return (
                            <Card key={kpi.label} className="border-slate-200">
                                <CardContent className="p-3">
                                    <div className="flex items-center gap-2 mb-1">
                                        <KIcon className={`h-4 w-4 ${kpi.color}`} />
                                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{kpi.label}</span>
                                    </div>
                                    <p className={`text-2xl font-bold font-mono ${kpi.color}`} data-testid={`kpi-${kpi.label.replace(/\s/g, '-').toLowerCase()}`}>
                                        {kpi.value}
                                    </p>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>

                {/* CAM Safety Gate */}
                {data?.cam_safety_gate && data.cam_safety_gate.level !== 'info' && (
                    <Card className={`overflow-hidden ${data.cam_safety_gate.level === 'danger' ? 'border-red-300 bg-red-50/50' : 'border-emerald-200 bg-emerald-50/30'}`}
                        data-testid="cam-safety-gate">
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3 mb-3">
                                <div className={`p-2 rounded-lg ${data.cam_safety_gate.level === 'danger' ? 'bg-red-100' : 'bg-emerald-100'}`}>
                                    <Leaf className={`h-5 w-5 ${data.cam_safety_gate.level === 'danger' ? 'text-red-600' : 'text-emerald-600'}`} />
                                </div>
                                <div className="flex-1">
                                    <h3 className={`text-sm font-bold ${data.cam_safety_gate.level === 'danger' ? 'text-red-800' : 'text-emerald-800'}`}>
                                        Safety Gate CAM — DM 23/06/2022
                                    </h3>
                                    <p className="text-xs text-slate-600 mt-0.5">
                                        {data.cam_safety_gate.percentuale_globale?.toFixed(1)}% riciclato globale ({data.cam_safety_gate.peso_totale_kg?.toLocaleString('it-IT')} kg)
                                        — Soglia: {data.cam_safety_gate.soglia}%
                                    </p>
                                </div>
                                {data.cam_safety_gate.level === 'danger' && (
                                    <Badge className="bg-red-600 text-white text-[10px] gap-1 px-2.5 py-1">
                                        <AlertTriangle className="h-3 w-3" /> RISCHIO NON CONFORMITA
                                    </Badge>
                                )}
                                {data.cam_safety_gate.level === 'success' && (
                                    <Badge className="bg-emerald-600 text-white text-[10px] gap-1 px-2.5 py-1">
                                        <CheckCircle2 className="h-3 w-3" /> CONFORME
                                    </Badge>
                                )}
                            </div>
                            {data.cam_safety_gate.n_non_conformi > 0 && (
                                <div className="space-y-1.5">
                                    <p className="text-[10px] font-semibold text-red-700 uppercase tracking-wider">
                                        {data.cam_safety_gate.n_non_conformi} commesse sotto soglia:
                                    </p>
                                    <div className="flex flex-wrap gap-2">
                                        {(data.cam_safety_gate.commesse || []).filter(c => !c.conforme).map(c => (
                                            <Badge key={c.commessa_id} variant="outline"
                                                className="text-[9px] px-2 py-0.5 border-red-300 text-red-700 cursor-pointer hover:bg-red-100"
                                                onClick={() => navigate(`/commesse/${c.commessa_id}`)}>
                                                <ArrowDown className="h-2.5 w-2.5 mr-0.5" />
                                                {c.numero} — {c.percentuale_riciclato}%
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="flex justify-end mt-2">
                                <Button size="sm" variant="outline"
                                    className="text-[10px] h-7 border-slate-300"
                                    data-testid="btn-report-cam-mensile"
                                    onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/cam/report-mensile/pdf`, '_blank')}>
                                    <FileText className="h-3 w-3 mr-1" /> Report CAM Mensile (PDF)
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Three Sector Sections */}
                {['EN_1090', 'EN_13241', 'GENERICA'].map(skey => (
                    <SectorSection key={skey} skey={skey}
                        data={data?.settori?.[skey] || { commesse: [], stats: {} }}
                        navigate={navigate} />
                ))}
            </div>
        </DashboardLayout>
    );
}
