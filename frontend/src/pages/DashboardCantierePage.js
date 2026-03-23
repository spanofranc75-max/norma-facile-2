/**
 * DashboardCantierePage — Dashboard Commessa Multilivello
 * Step A: Executive overview con semaforo, obblighi, readiness
 * Step B: Drill-down 4 livelli (Commessa, Rami, Sicurezza, Committenza)
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
    Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '../components/ui/collapsible';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import {
    RefreshCw, ChevronDown, ChevronRight, AlertTriangle,
    CheckCircle2, Clock, Shield, FileText, Package, Users,
    GitBranch, HardHat, Eye, ExternalLink, CircleAlert,
    CircleCheck, CircleMinus, Loader2, LayoutDashboard,
    ArrowRight, Folder, ClipboardList, Search,
} from 'lucide-react';

/* ── helpers ─────────────────────────────────────── */
const fmtDate = (d) => {
    if (!d) return '--';
    const p = d.slice(0, 10).split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
};

const fmtMoney = (v) =>
    (v || 0).toLocaleString('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

const SEMAFORO = {
    rosso:  { bg: 'bg-red-500',    ring: 'ring-red-200',    text: 'text-red-700',    label: 'Critico',    cardBg: 'bg-red-50/60 border-red-200' },
    giallo: { bg: 'bg-amber-400',  ring: 'ring-amber-200',  text: 'text-amber-700',  label: 'Attenzione', cardBg: 'bg-amber-50/60 border-amber-200' },
    verde:  { bg: 'bg-emerald-500',ring: 'ring-emerald-200',text: 'text-emerald-700', label: 'OK',         cardBg: 'bg-emerald-50/40 border-emerald-200' },
};

const SOURCE_LABELS = {
    evidence_gate: 'Evidence Gate',
    gate_pos: 'Gate POS',
    soggetti: 'Soggetti',
    istruttoria: 'Istruttoria',
    rami_normativi: 'Rami Normativi',
    documenti_scadenza: 'Doc. Scaduti',
    pacchetti_documentali: 'Pacchetti Doc.',
    committenza: 'Committenza',
};

const STATO_LABELS = {
    richiesta: 'Richiesta', bozza: 'Bozza', rilievo_completato: 'Rilievo',
    firmato: 'Firmato', in_produzione: 'Produzione', fatturato: 'Fatturato',
    chiuso: 'Chiuso', sospesa: 'Sospesa',
};

/* ═══════════════════════════════════════════════════
   STEP A — Global Summary + Commessa Cards
   ═══════════════════════════════════════════════════ */

function GlobalSummary({ summary }) {
    const { totale, verdi, gialli, rossi, bloccanti_totali, aperti_totali } = summary;
    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="global-summary">
            <SummaryCard label="Commesse Attive" value={totale} icon={LayoutDashboard} color="text-slate-700" />
            <SummaryCard label="Verdi" value={verdi} icon={CircleCheck} color="text-emerald-600" />
            <SummaryCard label="Gialli" value={gialli} icon={CircleAlert} color="text-amber-600" />
            <SummaryCard label="Rossi" value={rossi} icon={CircleMinus} color="text-red-600" />
            <SummaryCard label="Bloccanti" value={bloccanti_totali} icon={AlertTriangle} color="text-red-700" />
            <SummaryCard label="Aperti" value={aperti_totali} icon={ClipboardList} color="text-blue-600" />
        </div>
    );
}

function SummaryCard({ label, value, icon: Icon, color }) {
    return (
        <Card className="border-slate-200">
            <CardContent className="p-3">
                <div className="flex items-center gap-2 mb-1">
                    <Icon className={`h-4 w-4 ${color}`} />
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
                </div>
                <p className={`text-2xl font-bold font-mono ${color}`} data-testid={`summary-${label.toLowerCase().replace(/\s/g,'-')}`}>
                    {value}
                </p>
            </CardContent>
        </Card>
    );
}

/* ═══════════════════════════════════════════════════
   COMMESSA CARD — Semaphore + Key Metrics
   ═══════════════════════════════════════════════════ */

function CommessaCard({ commessa, navigate }) {
    const [open, setOpen] = useState(false);
    const sem = SEMAFORO[commessa.semaforo] || SEMAFORO.verde;
    const obl = commessa.obblighi || {};
    const rami = commessa.rami_summary || {};
    const pos = commessa.pos;
    const packs = commessa.pacchetti_summary || {};
    const comm = commessa.committenza_summary || {};

    return (
        <Card className={`${sem.cardBg} transition-all duration-300`} data-testid={`commessa-card-${commessa.commessa_id}`}>
            <Collapsible open={open} onOpenChange={setOpen}>
                {/* HEADER ROW — always visible */}
                <CollapsibleTrigger asChild>
                    <div className="px-4 py-3 cursor-pointer hover:bg-white/30 transition-colors">
                        <div className="flex items-center gap-3">
                            {/* Semaphore dot */}
                            <div className={`w-3.5 h-3.5 rounded-full ${sem.bg} ring-2 ${sem.ring} shrink-0`} />

                            {/* Info */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-sm font-bold text-slate-900">{commessa.numero}</span>
                                    <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-slate-300 text-slate-600">
                                        {STATO_LABELS[commessa.stato] || commessa.stato}
                                    </Badge>
                                    {commessa.normativa_tipo && (
                                        <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-blue-300 text-blue-600">
                                            {commessa.normativa_tipo}
                                        </Badge>
                                    )}
                                </div>
                                <p className="text-xs text-slate-600 truncate">{commessa.title || commessa.client_name}</p>
                            </div>

                            {/* Quick Stats */}
                            <div className="hidden md:flex items-center gap-4">
                                {obl.bloccanti > 0 && (
                                    <div className="flex items-center gap-1 text-red-700">
                                        <AlertTriangle className="h-3.5 w-3.5" />
                                        <span className="text-xs font-bold">{obl.bloccanti}</span>
                                    </div>
                                )}
                                {obl.aperti > 0 && (
                                    <div className="flex items-center gap-1 text-amber-700">
                                        <Clock className="h-3.5 w-3.5" />
                                        <span className="text-xs font-medium">{obl.aperti} aperti</span>
                                    </div>
                                )}
                                {commessa.deadline && (
                                    <div className={`text-xs ${commessa.days_left !== null && commessa.days_left < 0 ? 'text-red-600 font-bold' : commessa.days_left !== null && commessa.days_left <= 7 ? 'text-amber-600 font-medium' : 'text-slate-500'}`}>
                                        {fmtDate(commessa.deadline)}
                                        {commessa.days_left !== null && commessa.days_left < 0 && (
                                            <span className="ml-1">({Math.abs(commessa.days_left)}gg ritardo)</span>
                                        )}
                                    </div>
                                )}
                                <span className="text-xs font-mono text-slate-600">{fmtMoney(commessa.value)}</span>
                            </div>

                            {/* Expand arrow */}
                            <div className="shrink-0">
                                {open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                            </div>
                        </div>

                        {/* Mini badges row (mobile) */}
                        <div className="flex md:hidden items-center gap-2 mt-1.5 flex-wrap">
                            {obl.bloccanti > 0 && <Badge className="text-[9px] bg-red-600 text-white">{obl.bloccanti} blk</Badge>}
                            {obl.aperti > 0 && <Badge className="text-[9px] bg-amber-500 text-white">{obl.aperti} aperti</Badge>}
                            <span className="text-[10px] text-slate-500">{fmtMoney(commessa.value)}</span>
                        </div>
                    </div>
                </CollapsibleTrigger>

                {/* DRILL-DOWN CONTENT — Step B */}
                <CollapsibleContent>
                    <Separator />
                    <div className="px-4 py-4 space-y-4 bg-white/50">
                        {/* 4 readiness mini-cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                            <ReadinessCard
                                icon={ClipboardList}
                                title="Obblighi"
                                status={obl.bloccanti > 0 ? 'rosso' : obl.aperti > 0 ? 'giallo' : 'verde'}
                                detail={`${obl.aperti || 0} aperti / ${obl.bloccanti || 0} blk`}
                            />
                            <ReadinessCard
                                icon={GitBranch}
                                title="Rami Normativi"
                                status={rami.totale === 0 ? 'giallo' : rami.pronti === rami.totale ? 'verde' : 'giallo'}
                                detail={`${rami.pronti || 0}/${rami.totale || 0} pronti`}
                            />
                            <ReadinessCard
                                icon={HardHat}
                                title="POS Sicurezza"
                                status={!pos ? 'giallo' : pos.gate_pos_ready ? 'verde' : 'rosso'}
                                detail={!pos ? 'Non creato' : pos.gate_pos_ready ? 'Pronto' : `${pos.campi_mancanti} campi manc.`}
                            />
                            <ReadinessCard
                                icon={Package}
                                title="Pacchetti Doc."
                                status={packs.totale === 0 ? 'giallo' : packs.missing_totali > 0 || packs.expired_totali > 0 ? 'rosso' : 'verde'}
                                detail={`${packs.completi || 0}/${packs.totale || 0} completi`}
                            />
                        </div>

                        {/* L1: Top Blockers */}
                        {commessa.top_blockers && commessa.top_blockers.length > 0 && (
                            <DrillSection title="Blockers Critici" icon={AlertTriangle} accentColor="text-red-700">
                                <div className="space-y-1.5">
                                    {commessa.top_blockers.map((b, i) => (
                                        <div key={i} className="flex items-start gap-2 px-3 py-2 bg-red-50 rounded border border-red-100">
                                            <CircleMinus className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs text-red-800 font-medium truncate">{b.title}</p>
                                                <p className="text-[10px] text-red-600">{SOURCE_LABELS[b.source_module] || b.source_module}</p>
                                            </div>
                                            {b.due_date && <span className="text-[9px] text-red-500">{fmtDate(b.due_date)}</span>}
                                        </div>
                                    ))}
                                </div>
                            </DrillSection>
                        )}

                        {/* L1: Obblighi per Fonte */}
                        {obl.aperti > 0 && Object.keys(obl.by_source || {}).length > 0 && (
                            <DrillSection title="Obblighi per Fonte" icon={Eye} accentColor="text-slate-700">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                    {Object.entries(obl.by_source).sort((a, b) => b[1] - a[1]).map(([src, cnt]) => (
                                        <div key={src} className="flex items-center justify-between px-2.5 py-1.5 bg-slate-50 rounded border border-slate-100">
                                            <span className="text-[10px] text-slate-600">{SOURCE_LABELS[src] || src}</span>
                                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">{cnt}</Badge>
                                        </div>
                                    ))}
                                </div>
                            </DrillSection>
                        )}

                        {/* L2: Rami Normativi Detail */}
                        {commessa.rami && commessa.rami.length > 0 && (
                            <DrillSection title="Rami Normativi" icon={GitBranch} accentColor="text-blue-700">
                                <div className="space-y-2">
                                    {commessa.rami.map((ramo) => (
                                        <RamoRow key={ramo.ramo_id} ramo={ramo} />
                                    ))}
                                </div>
                            </DrillSection>
                        )}

                        {/* L3: Sicurezza POS */}
                        {pos && (
                            <DrillSection title="Sicurezza / POS" icon={HardHat} accentColor="text-orange-700">
                                <div className="flex items-center gap-4 px-3 py-2 bg-slate-50 rounded border border-slate-100">
                                    <div className={`w-2.5 h-2.5 rounded-full ${pos.gate_pos_ready ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                    <div className="flex-1">
                                        <p className="text-xs font-medium text-slate-800">
                                            {pos.nome || 'Cantiere sicurezza'}
                                        </p>
                                        <p className="text-[10px] text-slate-500">
                                            Gate POS: {pos.gate_pos_ready ? 'Pronto' : `${pos.campi_mancanti} campi mancanti, ${pos.blockers} blockers`}
                                        </p>
                                    </div>
                                    <Button variant="ghost" size="sm" className="h-7 text-[10px]"
                                        onClick={(e) => { e.stopPropagation(); navigate(`/sicurezza/${pos.cantiere_id}`); }}
                                        data-testid={`goto-pos-${commessa.commessa_id}`}>
                                        <ExternalLink className="h-3 w-3 mr-1" /> Apri
                                    </Button>
                                </div>
                            </DrillSection>
                        )}

                        {/* L3b: Pacchetti Documentali */}
                        {commessa.pacchetti && commessa.pacchetti.length > 0 && (
                            <DrillSection title="Pacchetti Documentali" icon={Package} accentColor="text-indigo-700">
                                <div className="space-y-1.5">
                                    {commessa.pacchetti.map((p) => (
                                        <div key={p.pack_id} className="flex items-center gap-3 px-3 py-2 bg-slate-50 rounded border border-slate-100">
                                            <div className={`w-2 h-2 rounded-full ${p.completo ? 'bg-emerald-500' : p.missing > 0 ? 'bg-red-500' : 'bg-amber-400'}`} />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs font-medium text-slate-800 truncate">{p.label}</p>
                                                <p className="text-[10px] text-slate-500">
                                                    {p.attached}/{p.totale_items} allegati
                                                    {p.missing > 0 && <span className="text-red-600 ml-1">{p.missing} mancanti</span>}
                                                    {p.expired > 0 && <span className="text-red-600 ml-1">{p.expired} scaduti</span>}
                                                </p>
                                            </div>
                                            <Progress value={p.totale_items > 0 ? (p.attached / p.totale_items * 100) : 0}
                                                className="w-16 h-1.5" />
                                        </div>
                                    ))}
                                </div>
                            </DrillSection>
                        )}

                        {/* L4: Committenza */}
                        {(commessa.committenza_packages?.length > 0 || commessa.committenza_analisi?.length > 0) && (
                            <DrillSection title="Verifica Committenza" icon={Search} accentColor="text-purple-700">
                                <div className="space-y-2">
                                    {/* Packages */}
                                    {commessa.committenza_packages?.map((pkg) => (
                                        <div key={pkg.package_id} className="flex items-center gap-3 px-3 py-2 bg-slate-50 rounded border border-slate-100">
                                            <Folder className="h-3.5 w-3.5 text-purple-500" />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs font-medium text-slate-800 truncate">{pkg.title}</p>
                                                <p className="text-[10px] text-slate-500">{pkg.n_documenti} documenti - {pkg.status}</p>
                                            </div>
                                        </div>
                                    ))}
                                    {/* Analyses summary */}
                                    {comm.analisi_totali > 0 && (
                                        <div className="grid grid-cols-3 gap-2">
                                            <MiniStat label="Analisi" value={`${comm.analisi_approvate}/${comm.analisi_totali}`} sub="approvate" />
                                            <MiniStat label="Obblighi" value={comm.obblighi_estratti} sub="estratti" />
                                            <MiniStat label="Anomalie" value={comm.anomalie_totali + comm.mismatch_totali} sub="+ mismatch" />
                                        </div>
                                    )}
                                </div>
                            </DrillSection>
                        )}

                        {/* CTA: Go to CommessaHub */}
                        <div className="flex justify-end pt-1">
                            <Button variant="outline" size="sm" className="h-7 text-[10px] border-slate-300"
                                onClick={() => navigate(`/commesse/${commessa.commessa_id}`)}
                                data-testid={`goto-hub-${commessa.commessa_id}`}>
                                <ArrowRight className="h-3 w-3 mr-1" /> Apri Hub Commessa
                            </Button>
                        </div>
                    </div>
                </CollapsibleContent>
            </Collapsible>
        </Card>
    );
}

/* ── Sub-components ── */

function ReadinessCard({ icon: Icon, title, status, detail }) {
    const sem = SEMAFORO[status] || SEMAFORO.verde;
    return (
        <div className="flex items-center gap-2.5 px-3 py-2 bg-white rounded-md border border-slate-100">
            <div className={`w-2.5 h-2.5 rounded-full ${sem.bg}`} />
            <div className="min-w-0">
                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{title}</p>
                <p className="text-xs font-medium text-slate-800">{detail}</p>
            </div>
        </div>
    );
}

function DrillSection({ title, icon: Icon, accentColor, children }) {
    const [open, setOpen] = useState(false);
    return (
        <Collapsible open={open} onOpenChange={setOpen}>
            <CollapsibleTrigger asChild>
                <div className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity py-1">
                    {open ? <ChevronDown className={`h-3.5 w-3.5 ${accentColor}`} /> : <ChevronRight className={`h-3.5 w-3.5 ${accentColor}`} />}
                    <Icon className={`h-3.5 w-3.5 ${accentColor}`} />
                    <span className={`text-xs font-bold ${accentColor}`}>{title}</span>
                </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
                <div className="ml-7 mt-1.5">
                    {children}
                </div>
            </CollapsibleContent>
        </Collapsible>
    );
}

function RamoRow({ ramo }) {
    const statoOk = ['confermato', 'completato', 'pronto'].includes(ramo.stato);
    return (
        <div className="flex items-center gap-3 px-3 py-2 bg-slate-50 rounded border border-slate-100">
            <div className={`w-2 h-2 rounded-full ${statoOk ? 'bg-emerald-500' : 'bg-amber-400'}`} />
            <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-800">
                    {ramo.codice} <span className="text-slate-500">— {ramo.normativa}</span>
                </p>
                <p className="text-[10px] text-slate-500">
                    Stato: {ramo.stato || 'draft'}
                    {ramo.emissioni_totali > 0 && (
                        <span className="ml-2">| Emissioni: {ramo.emissioni_pronte}/{ramo.emissioni_totali} pronte</span>
                    )}
                </p>
            </div>
            {/* Emissioni mini progress */}
            {ramo.emissioni_totali > 0 && (
                <Progress value={ramo.emissioni_totali > 0 ? (ramo.emissioni_pronte / ramo.emissioni_totali * 100) : 0}
                    className="w-14 h-1.5" />
            )}
        </div>
    );
}

function MiniStat({ label, value, sub }) {
    return (
        <div className="text-center px-2 py-1.5 bg-slate-50 rounded border border-slate-100">
            <p className="text-sm font-bold font-mono text-slate-800">{value}</p>
            <p className="text-[9px] text-slate-500 uppercase tracking-wider">{label}</p>
            {sub && <p className="text-[8px] text-slate-400">{sub}</p>}
        </div>
    );
}

/* ═══════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════ */

export default function DashboardCantierePage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('tutti'); // tutti | rosso | giallo | verde
    const navigate = useNavigate();

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const d = await apiRequest('/dashboard/cantiere-multilivello');
            setData(d);
        } catch (e) {
            toast.error('Errore caricamento dashboard: ' + e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64" data-testid="dashboard-loading">
                    <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    const commesse = data?.commesse || [];
    const summary = data?.global_summary || {};
    const filtered = filter === 'tutti' ? commesse : commesse.filter(c => c.semaforo === filter);

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="dashboard-cantiere-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                            Dashboard Cantiere
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Visibilita multilivello su tutte le commesse attive
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={fetchData} className="border-slate-200 text-slate-600"
                        data-testid="refresh-dashboard-cantiere">
                        <RefreshCw className="h-4 w-4 mr-1.5" /> Aggiorna
                    </Button>
                </div>

                {/* Step A: Global Summary */}
                <GlobalSummary summary={summary} />

                {/* Filter bar */}
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Filtra:</span>
                    {[
                        { key: 'tutti', label: 'Tutte', count: commesse.length },
                        { key: 'rosso', label: 'Critiche', count: summary.rossi || 0 },
                        { key: 'giallo', label: 'Attenzione', count: summary.gialli || 0 },
                        { key: 'verde', label: 'OK', count: summary.verdi || 0 },
                    ].map(f => (
                        <Button key={f.key} variant={filter === f.key ? 'default' : 'outline'}
                            size="sm" className="h-7 text-[10px]"
                            onClick={() => setFilter(f.key)}
                            data-testid={`filter-${f.key}`}>
                            {f.key !== 'tutti' && <div className={`w-2 h-2 rounded-full mr-1.5 ${SEMAFORO[f.key]?.bg || ''}`} />}
                            {f.label} ({f.count})
                        </Button>
                    ))}
                </div>

                {/* Step A+B: Commessa Cards with drill-down */}
                {filtered.length === 0 ? (
                    <Card className="border-slate-200">
                        <CardContent className="p-8 text-center">
                            <LayoutDashboard className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                            <p className="text-sm text-slate-500">
                                {commesse.length === 0
                                    ? 'Nessuna commessa attiva trovata.'
                                    : 'Nessuna commessa corrisponde al filtro selezionato.'}
                            </p>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="space-y-3">
                        {filtered.map(c => (
                            <CommessaCard key={c.commessa_id} commessa={c} navigate={navigate} />
                        ))}
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
