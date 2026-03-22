import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { apiRequest } from '../lib/utils';
import {
    Brain, Loader2, ShieldCheck, ShieldAlert, FileText,
    AlertTriangle, CheckCircle2, HelpCircle, Minus,
    Hammer, Flame, Ruler, Package, Truck, Eye, Wrench,
    ArrowLeft, RefreshCw, CircleAlert, Lightbulb,
} from 'lucide-react';

const STATO_COLORS = {
    confermato: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    dedotto: 'bg-blue-100 text-blue-700 border-blue-200',
    mancante: 'bg-red-100 text-red-700 border-red-200',
    incerto: 'bg-amber-100 text-amber-700 border-amber-200',
};
const STATO_ICONS = {
    confermato: <CheckCircle2 className="h-3 w-3" />,
    dedotto: <Lightbulb className="h-3 w-3" />,
    mancante: <Minus className="h-3 w-3" />,
    incerto: <HelpCircle className="h-3 w-3" />,
};

const NORM_COLORS = {
    EN_1090: 'bg-blue-700 text-white',
    EN_13241: 'bg-indigo-600 text-white',
    GENERICA: 'bg-slate-500 text-white',
    MISTA: 'bg-purple-600 text-white',
};

const LAV_ICONS = {
    taglio: Ruler, saldatura: Flame, foratura: Wrench, assemblaggio: Package,
    zincatura: Truck, verniciatura: Eye, montaggio: Hammer, piegatura: Wrench,
};

function StatoBadge({ stato }) {
    return (
        <Badge className={`text-[9px] px-1.5 py-0 gap-0.5 border ${STATO_COLORS[stato] || 'bg-slate-100 text-slate-600'}`}>
            {STATO_ICONS[stato]} {stato}
        </Badge>
    );
}

export default function IstruttoriaPage() {
    const { preventivoId } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);

    const fetchIstruttoria = useCallback(async () => {
        setLoading(true);
        try {
            const res = await apiRequest(`/istruttoria/preventivo/${preventivoId}`);
            setData(res);
        } catch {
            setData(null);
        } finally { setLoading(false); }
    }, [preventivoId]);

    useEffect(() => { fetchIstruttoria(); }, [fetchIstruttoria]);

    const handleAnalizza = async () => {
        setAnalyzing(true);
        try {
            toast.info('Analisi AI in corso — Livello 1A (Estrazione) + 1B (Classificazione)...');
            const res = await apiRequest(`/istruttoria/analizza-preventivo/${preventivoId}`, { method: 'POST' });
            setData(res);
            toast.success('Istruttoria completata');
        } catch (e) { toast.error(e.message); }
        finally { setAnalyzing(false); }
    };

    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        </DashboardLayout>
    );

    // No analysis yet — show CTA
    if (!data) return (
        <DashboardLayout>
            <div className="max-w-2xl mx-auto mt-16 text-center space-y-6">
                <Brain className="h-16 w-16 mx-auto text-blue-600 opacity-80" />
                <h1 className="text-2xl font-bold text-slate-800">Motore di Istruttoria Automatica</h1>
                <p className="text-slate-500">
                    Analizza il preventivo <strong>{preventivoId}</strong> per estrarre dati tecnici,
                    classificare la normativa e proporre l'istruttoria completa.
                </p>
                <Button
                    size="lg"
                    onClick={handleAnalizza}
                    disabled={analyzing}
                    className="bg-blue-700 hover:bg-blue-800 text-white px-8"
                    data-testid="btn-avvia-istruttoria"
                >
                    {analyzing ? <Loader2 className="h-5 w-5 mr-2 animate-spin" /> : <Brain className="h-5 w-5 mr-2" />}
                    {analyzing ? 'Analisi in corso...' : 'Avvia Istruttoria AI'}
                </Button>
            </div>
        </DashboardLayout>
    );

    const { classificazione, profilo_tecnico, estrazione_tecnica, stato_conoscenza,
        fasi_produttive_attese, documenti_richiesti, controlli_richiesti,
        prerequisiti_saldatura, prerequisiti_tracciabilita,
        domande_residue, warnings_regole, enrichments_regole,
        revisioni_umane, confermata, stato_revisione } = data;

    const normativa = classificazione?.normativa_proposta || 'N/D';
    const conf = classificazione?.confidenza || 'bassa';

    const handleRevisione = async (campo, valoreCorretto, motivazione = '') => {
        try {
            await apiRequest(`/istruttoria/${data.istruttoria_id}/revisione`, {
                method: 'POST',
                body: { campo, valore_corretto: valoreCorretto, motivazione },
            });
            toast.success(`Revisione salvata: ${campo}`);
            fetchIstruttoria();
        } catch (e) { toast.error(e.message); }
    };

    const handleConferma = async () => {
        try {
            await apiRequest(`/istruttoria/${data.istruttoria_id}/conferma`, { method: 'POST' });
            toast.success('Istruttoria confermata — pronta per Fase 2');
            fetchIstruttoria();
        } catch (e) { toast.error(e.message); }
    };

    return (
        <DashboardLayout>
            <div className="space-y-4 max-w-7xl mx-auto" data-testid="istruttoria-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                        <div>
                            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <Brain className="h-5 w-5 text-blue-600" />
                                Istruttoria Automatica
                                <Badge className={`text-[10px] px-2 ${NORM_COLORS[normativa] || 'bg-slate-400 text-white'}`}>
                                    {normativa}
                                </Badge>
                            </h1>
                            <p className="text-xs text-slate-500 mt-0.5">
                                Preventivo {data.preventivo_number} — v{data.versione}
                            </p>
                        </div>
                    </div>
                    <Button size="sm" variant="outline" onClick={handleAnalizza} disabled={analyzing}
                        data-testid="btn-riesegui-istruttoria">
                        <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${analyzing ? 'animate-spin' : ''}`} />
                        Riesegui
                    </Button>
                </div>

                {/* Warnings from rules engine */}
                {warnings_regole?.length > 0 && (
                    <Card className="border-amber-300 bg-amber-50/50">
                        <CardContent className="p-3 space-y-1">
                            <p className="text-xs font-bold text-amber-800 flex items-center gap-1.5">
                                <CircleAlert className="h-3.5 w-3.5" /> Correzioni del Motore Regole
                            </p>
                            {warnings_regole.map((w, i) => (
                                <p key={i} className="text-[10px] text-amber-700">{w.messaggio}</p>
                            ))}
                        </CardContent>
                    </Card>
                )}

                {/* Row 1: Classification + EXC + Knowledge State */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Card data-testid="card-classificazione">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                A. Classificazione Proposta
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex items-center gap-2">
                                <Badge className={`text-sm px-3 py-1 ${NORM_COLORS[normativa]}`}>
                                    {normativa}
                                </Badge>
                                <Badge className={`text-[9px] ${conf === 'alta' ? 'bg-emerald-100 text-emerald-700' : conf === 'media' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                                    Confidenza: {conf}
                                </Badge>
                            </div>
                            <p className="text-[10px] text-slate-600 leading-relaxed">{classificazione?.motivazione}</p>
                        </CardContent>
                    </Card>

                    <Card data-testid="card-profilo-tecnico">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                Profilo Tecnico {profilo_tecnico?.tipo === 'exc' ? '(Classe Esecuzione)' : profilo_tecnico?.tipo === 'categorie_prestazione' ? '(Categorie Prestazione)' : '(Complessita)'}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="text-2xl font-black text-blue-800">{profilo_tecnico?.valore || 'N/D'}</div>
                            <p className="text-[10px] text-slate-600 leading-relaxed">{profilo_tecnico?.motivazione}</p>
                            <Badge className="text-[8px] bg-slate-100 text-slate-500">
                                Applicabile a: {profilo_tecnico?.applicabile_a}
                            </Badge>
                        </CardContent>
                    </Card>

                    <Card data-testid="card-stato-conoscenza">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                D. Stato Conoscenza
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="text-lg font-bold text-slate-800">{stato_conoscenza?.completezza_pct}%</div>
                            <div className="flex flex-wrap gap-1.5">
                                {['confermato', 'dedotto', 'mancante', 'incerto'].map(s => (
                                    <Badge key={s} className={`text-[9px] px-1.5 py-0 gap-0.5 border ${STATO_COLORS[s]}`}>
                                        {STATO_ICONS[s]} {stato_conoscenza?.[s] || 0} {s}
                                    </Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Row 2: Extracted Data */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {/* Elements */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                B. Elementi Strutturali Estratti
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1.5">
                                {(estrazione_tecnica?.elementi_strutturali || []).map((el, i) => (
                                    <div key={i} className="flex items-start gap-2 py-1 border-b border-slate-100 last:border-0">
                                        <Package className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                                                {el.descrizione}
                                                <StatoBadge stato={el.stato} />
                                            </div>
                                            <div className="text-[10px] text-slate-500 flex gap-3 mt-0.5">
                                                {el.profilo && <span>Profilo: <strong>{el.profilo}</strong></span>}
                                                {el.materiale_base && <span>Mat: <strong>{el.materiale_base}</strong></span>}
                                                {el.spessore_mm && <span>Sp: {el.spessore_mm}mm</span>}
                                                {el.peso_stimato_kg && <span>~{el.peso_stimato_kg}kg</span>}
                                            </div>
                                            {el.fonte_nel_testo && (
                                                <div className="text-[9px] text-slate-400 italic mt-0.5">"{el.fonte_nel_testo}"</div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {(!estrazione_tecnica?.elementi_strutturali?.length) && (
                                    <p className="text-xs text-slate-400 italic">Nessun elemento strutturale estratto</p>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Processes + Welding */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                Lavorazioni + Saldatura + Trattamenti
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {/* Lavorazioni */}
                            <div className="flex flex-wrap gap-1.5">
                                {(estrazione_tecnica?.lavorazioni_rilevate || []).map((lav, i) => {
                                    const Icon = LAV_ICONS[lav.tipo] || Wrench;
                                    return (
                                        <Badge key={i} variant="outline" className="text-[9px] px-2 py-0.5 gap-1">
                                            <Icon className="h-2.5 w-2.5" />
                                            {lav.tipo}: {lav.dettaglio}
                                            <StatoBadge stato={lav.stato} />
                                        </Badge>
                                    );
                                })}
                            </div>

                            {/* Saldatura */}
                            {estrazione_tecnica?.saldature?.presenti && (
                                <div className="bg-orange-50 border border-orange-200 rounded-lg p-2.5 space-y-1">
                                    <p className="text-xs font-bold text-orange-800 flex items-center gap-1">
                                        <Flame className="h-3.5 w-3.5" /> Saldature
                                        <StatoBadge stato={estrazione_tecnica.saldature.stato} />
                                    </p>
                                    <div className="flex flex-wrap gap-1">
                                        {(estrazione_tecnica.saldature.processi_ipotizzati || []).map(p => (
                                            <Badge key={p} className="bg-orange-100 text-orange-700 text-[9px] px-1.5 py-0">{p}</Badge>
                                        ))}
                                    </div>
                                    {(estrazione_tecnica.saldature.giunti_attesi || []).map((g, i) => (
                                        <p key={i} className="text-[10px] text-orange-700">
                                            {g.descrizione} ({g.tipo_giunto}) <StatoBadge stato={g.stato} />
                                        </p>
                                    ))}
                                </div>
                            )}

                            {/* Trattamenti */}
                            {estrazione_tecnica?.trattamenti_superficiali?.tipo && estrazione_tecnica.trattamenti_superficiali.tipo !== 'nessuno' && (
                                <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-2.5">
                                    <p className="text-xs font-bold text-cyan-800 flex items-center gap-1">
                                        <Truck className="h-3.5 w-3.5" />
                                        {estrazione_tecnica.trattamenti_superficiali.tipo}
                                        {estrazione_tecnica.trattamenti_superficiali.esecuzione && (
                                            <Badge className="bg-cyan-100 text-cyan-700 text-[9px] px-1.5 py-0 ml-1">
                                                {estrazione_tecnica.trattamenti_superficiali.esecuzione}
                                            </Badge>
                                        )}
                                        <StatoBadge stato={estrazione_tecnica.trattamenti_superficiali.stato} />
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Row 3: Requirements */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    {/* Documents */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                C. Documenti Richiesti ({documenti_richiesti?.length || 0})
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1">
                                {(documenti_richiesti || []).map((d, i) => (
                                    <div key={i} className="flex items-start gap-1.5 py-0.5">
                                        <FileText className={`h-3 w-3 mt-0.5 shrink-0 ${d.obbligatorio ? 'text-red-500' : 'text-slate-400'}`} />
                                        <div>
                                            <p className="text-[10px] font-medium text-slate-700">{d.documento}</p>
                                            <p className="text-[9px] text-slate-400">{d.motivazione}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Controls */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                Controlli Richiesti ({controlli_richiesti?.length || 0})
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1">
                                {(controlli_richiesti || []).map((c, i) => (
                                    <div key={i} className="flex items-start gap-1.5 py-0.5">
                                        <Eye className={`h-3 w-3 mt-0.5 shrink-0 ${c.tipo.startsWith('CND') ? 'text-purple-500' : 'text-blue-500'}`} />
                                        <div>
                                            <p className="text-[10px] font-medium text-slate-700">
                                                <Badge className="bg-slate-100 text-slate-600 text-[8px] px-1 py-0 mr-1">{c.tipo}</Badge>
                                                {c.descrizione}
                                            </p>
                                            <p className="text-[9px] text-slate-400">Fase: {c.fase}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Prerequisites */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                Prerequisiti
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {prerequisiti_saldatura?.richiesti && (
                                <div className="text-[10px] space-y-0.5">
                                    <p className="font-bold text-orange-700">Saldatura:</p>
                                    <p className={prerequisiti_saldatura.wps_necessarie ? 'text-red-600' : 'text-slate-400'}>
                                        WPS: {prerequisiti_saldatura.wps_necessarie ? 'Obbligatorie' : 'Non richieste'}
                                    </p>
                                    <p className={prerequisiti_saldatura.wpqr_necessarie ? 'text-red-600' : 'text-slate-400'}>
                                        WPQR: {prerequisiti_saldatura.wpqr_necessarie ? 'Obbligatorie' : 'Non richieste'}
                                    </p>
                                    <p className={prerequisiti_saldatura.qualifica_saldatori ? 'text-red-600' : 'text-slate-400'}>
                                        Qualifica saldatori: {prerequisiti_saldatura.qualifica_saldatori ? 'Obbligatoria' : 'Non richiesta'}
                                    </p>
                                </div>
                            )}
                            {prerequisiti_tracciabilita?.certificati_31_richiesti && (
                                <div className="text-[10px] space-y-0.5">
                                    <p className="font-bold text-blue-700">Tracciabilita:</p>
                                    <p className="text-red-600">Cert. 3.1: Obbligatori</p>
                                    <p className={prerequisiti_tracciabilita.tracciabilita_colata ? 'text-red-600' : 'text-slate-400'}>
                                        Tracciabilita colata: {prerequisiti_tracciabilita.tracciabilita_colata ? 'Si' : 'No'}
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Row 4: Residual Questions — THE KEY SECTION */}
                {domande_residue?.length > 0 && (
                    <Card className="border-blue-300 bg-blue-50/30" data-testid="card-domande-residue">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-bold text-blue-800 flex items-center gap-2">
                                <HelpCircle className="h-4 w-4" />
                                E. Domande Residue ({domande_residue.length})
                                <span className="text-[10px] font-normal text-blue-600 ml-2">
                                    Rispondi a queste per completare l'istruttoria
                                </span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {domande_residue.map((q, i) => (
                                    <div key={i} className="flex items-start gap-3 p-2.5 bg-white rounded-lg border border-blue-200">
                                        <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold text-white ${q.impatto === 'alto' ? 'bg-red-500' : q.impatto === 'medio' ? 'bg-amber-500' : 'bg-slate-400'}`}>
                                            {i + 1}
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-xs font-semibold text-slate-800">{q.domanda}</p>
                                            <p className="text-[10px] text-slate-500 mt-0.5">
                                                <Badge className={`text-[8px] px-1 py-0 mr-1 ${q.impatto === 'alto' ? 'bg-red-100 text-red-700' : q.impatto === 'medio' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
                                                    {q.impatto}
                                                </Badge>
                                                {q.perche_serve}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Ambiguities */}
                {estrazione_tecnica?.ambiguita_rilevate?.length > 0 && (
                    <Card className="border-amber-200">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-amber-700 flex items-center gap-1.5">
                                <AlertTriangle className="h-3.5 w-3.5" /> Ambiguita Rilevate
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1">
                                {estrazione_tecnica.ambiguita_rilevate.map((a, i) => (
                                    <div key={i} className="text-[10px] text-amber-800 py-0.5">
                                        <strong>{a.punto}</strong>
                                        <Badge className={`text-[8px] px-1 py-0 ml-1 ${a.impatto === 'alto' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                                            {a.impatto}
                                        </Badge>
                                        <span className="text-amber-600 ml-1">
                                            Possibili: {a.possibili_interpretazioni?.join(' / ')}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Production phases */}
                {fasi_produttive_attese?.length > 0 && (
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                                Fasi Produttive Attese
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex flex-wrap gap-1.5">
                                {fasi_produttive_attese.sort((a, b) => a.ordine - b.ordine).map((f, i) => (
                                    <Badge key={i} variant="outline"
                                        className={`text-[9px] px-2 py-1 ${f.obbligatoria ? 'border-blue-300 text-blue-700' : 'border-slate-200 text-slate-500'}`}>
                                        <span className="font-mono text-[8px] mr-1 opacity-50">{f.ordine}.</span>
                                        {f.fase}
                                    </Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Enrichments from rules */}
                {enrichments_regole?.length > 0 && (
                    <Card className="border-indigo-200 bg-indigo-50/30">
                        <CardContent className="p-3">
                            <p className="text-xs font-bold text-indigo-800 mb-1">Note Arricchimento Regole</p>
                            {enrichments_regole.map((e, i) => (
                                <p key={i} className="text-[10px] text-indigo-700">{e.messaggio}</p>
                            ))}
                        </CardContent>
                    </Card>
                )}

                {/* AI Tech Note */}
                {estrazione_tecnica?.note_tecnico && (
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <p className="text-xs font-bold text-slate-600 mb-1 flex items-center gap-1">
                                <Brain className="h-3.5 w-3.5 text-blue-500" /> Nota del Tecnico AI
                            </p>
                            <p className="text-[10px] text-slate-600 leading-relaxed italic">
                                "{estrazione_tecnica.note_tecnico}"
                            </p>
                        </CardContent>
                    </Card>
                )}

                {/* Human Revisions Log */}
                {revisioni_umane?.length > 0 && (
                    <Card className="border-indigo-200">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-bold text-indigo-700 uppercase tracking-wider">
                                Revisioni Umane ({revisioni_umane.length})
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1">
                                {revisioni_umane.map((r, i) => (
                                    <div key={i} className="flex items-start gap-2 text-[10px] py-1 border-b border-slate-100 last:border-0">
                                        <CheckCircle2 className="h-3 w-3 text-indigo-500 mt-0.5 shrink-0" />
                                        <div>
                                            <span className="font-medium text-slate-700">{r.campo}: </span>
                                            <span className="line-through text-red-400 mr-1">{String(r.valore_ai)}</span>
                                            <span className="text-emerald-700 font-bold">{String(r.valore_umano)}</span>
                                            {r.motivazione_correzione && (
                                                <span className="text-slate-400 ml-1">— {r.motivazione_correzione}</span>
                                            )}
                                            <span className="text-slate-300 ml-1">({r.corretto_da_nome})</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Confirmation Bar */}
                <Card className={`${confermata ? 'border-emerald-300 bg-emerald-50/30' : 'border-blue-300 bg-blue-50/30'}`}>
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <p className={`text-sm font-bold ${confermata ? 'text-emerald-800' : 'text-blue-800'}`}>
                                {confermata ? 'Istruttoria Confermata' : 'Revisione e Conferma'}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-0.5">
                                {confermata
                                    ? `Confermata da ${data.confermata_da_nome} — Pronta per Fase 2`
                                    : 'Revisiona i dati proposti e conferma per procedere alla generazione commessa'
                                }
                            </p>
                            {stato_revisione === 'revisionato' && !confermata && (
                                <Badge className="bg-indigo-100 text-indigo-700 text-[9px] mt-1">
                                    {revisioni_umane?.length || 0} correzioni applicate
                                </Badge>
                            )}
                        </div>
                        {!confermata && (
                            <Button
                                onClick={handleConferma}
                                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                                data-testid="btn-conferma-istruttoria"
                            >
                                <ShieldCheck className="h-4 w-4 mr-1.5" /> Conferma Istruttoria
                            </Button>
                        )}
                        {confermata && (
                            <Badge className="bg-emerald-100 text-emerald-700 text-sm px-3 py-1 gap-1">
                                <ShieldCheck className="h-4 w-4" /> Confermata
                            </Badge>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
