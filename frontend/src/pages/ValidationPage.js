import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { apiRequest } from '../lib/utils';
import {
    FlaskConical, Loader2, CheckCircle2, XCircle, Play,
    ArrowLeft, BarChart3, FileText, Target, AlertTriangle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SCORE_COLOR = (v) =>
    v >= 0.8 ? 'text-emerald-700 bg-emerald-100' :
    v >= 0.6 ? 'text-amber-700 bg-amber-100' :
    'text-red-700 bg-red-100';

const SCORE_BAR = (v) =>
    v >= 0.8 ? '[&>div]:bg-emerald-500' :
    v >= 0.6 ? '[&>div]:bg-amber-500' :
    '[&>div]:bg-red-500';

function ScoreCell({ label, value }) {
    const pct = Math.round(value * 100);
    return (
        <div className="space-y-1">
            <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500">{label}</span>
                <Badge className={`text-[9px] px-1.5 py-0 ${SCORE_COLOR(value)}`}>{pct}%</Badge>
            </div>
            <Progress value={pct} className={`h-1.5 ${SCORE_BAR(value)}`} />
        </div>
    );
}

export default function ValidationPage() {
    const navigate = useNavigate();
    const [validationSet, setValidationSet] = useState([]);
    const [results, setResults] = useState([]);
    const [aggregato, setAggregato] = useState(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(null);
    const [runningBatch, setRunningBatch] = useState(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [setRes, resRes] = await Promise.all([
                apiRequest('/validation/set'),
                apiRequest('/validation/results'),
            ]);
            setValidationSet(setRes.validation_set || []);
            setResults(resRes.risultati || []);
            setAggregato(resRes.aggregato || null);
        } catch {
            toast.error('Errore caricamento dati validazione');
        } finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const runSingle = async (pid) => {
        setRunning(pid);
        try {
            toast.info('Analisi AI in corso...');
            await apiRequest(`/validation/run/${pid}`, { method: 'POST' });
            toast.success('Validazione completata');
            fetchData();
        } catch (e) { toast.error(e.message); }
        finally { setRunning(null); }
    };

    const runBatch = async (ids) => {
        setRunningBatch(true);
        try {
            toast.info(`Avvio validazione batch (${ids.length} preventivi)...`);
            const res = await apiRequest('/validation/run-batch', {
                method: 'POST',
                body: { preventivo_ids: ids },
            });
            if (res.errori?.length) {
                toast.warning(`${res.errori.length} errori durante la validazione`);
            } else {
                toast.success('Validazione batch completata');
            }
            fetchData();
        } catch (e) { toast.error(e.message); }
        finally { setRunningBatch(false); }
    };

    const getResult = (pid) => results.find(r => r.preventivo_id === pid);

    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        </DashboardLayout>
    );

    const pilot3 = validationSet.slice(0, 3).map(v => v.preventivo_id);

    return (
        <DashboardLayout>
            <div className="space-y-4 max-w-5xl mx-auto" data-testid="validation-page">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} data-testid="btn-back">
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                        <div>
                            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <FlaskConical className="h-5 w-5 text-indigo-600" />
                                Validazione P1 — Motore AI
                            </h1>
                            <p className="text-xs text-slate-500 mt-0.5">
                                Scorecard su preventivi reali: classificazione, estrazione, domande
                            </p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button size="sm" variant="outline"
                            onClick={() => runBatch(pilot3)}
                            disabled={runningBatch || !!running}
                            data-testid="btn-run-pilot">
                            {runningBatch ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
                            Pilota 3 casi
                        </Button>
                        <Button size="sm"
                            onClick={() => runBatch(validationSet.map(v => v.preventivo_id))}
                            disabled={runningBatch || !!running}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white"
                            data-testid="btn-run-all">
                            {runningBatch ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <BarChart3 className="h-3.5 w-3.5 mr-1" />}
                            Valida tutti ({validationSet.length})
                        </Button>
                    </div>
                </div>

                {/* Aggregate Scorecard */}
                {aggregato && (
                    <Card className="border-2 border-indigo-200 bg-gradient-to-r from-indigo-50/50 to-slate-50" data-testid="card-aggregato">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-2 mb-3">
                                <Target className="h-4 w-4 text-indigo-600" />
                                <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Risultato aggregato</span>
                                <Badge className="bg-indigo-100 text-indigo-700 text-[10px]">
                                    {aggregato.n_preventivi} preventivi
                                </Badge>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                <div className="text-center">
                                    <p className="text-3xl font-black text-slate-900">{Math.round(aggregato.punteggio_medio_globale * 100)}%</p>
                                    <p className="text-[10px] text-slate-500">Globale</p>
                                </div>
                                <ScoreCell label="Classificazione" value={aggregato.media_classificazione} />
                                <ScoreCell label="Profilo" value={aggregato.media_profilo} />
                                <ScoreCell label="Estrazione" value={aggregato.media_estrazione} />
                                <ScoreCell label="Domande" value={aggregato.media_domande} />
                            </div>
                            <p className="text-[10px] text-slate-400 mt-2">
                                Classificazione corretta: {aggregato.classificazione_corretta}
                            </p>
                        </CardContent>
                    </Card>
                )}

                {/* Validation Set Table */}
                <Card data-testid="card-validation-set">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold text-slate-700 flex items-center gap-2">
                            <FileText className="h-4 w-4 text-slate-500" />
                            Set di validazione ({validationSet.length} preventivi)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {validationSet.map((v) => {
                            const res = getResult(v.preventivo_id);
                            const sc = res?.scorecard;
                            const isRunning = running === v.preventivo_id;

                            return (
                                <div key={v.preventivo_id}
                                    className={`rounded-lg border p-3 transition-all ${
                                        sc ? (sc.classificazione.corretto ? 'border-emerald-200 bg-emerald-50/20' : 'border-red-200 bg-red-50/20')
                                        : 'border-slate-200 bg-white'
                                    }`}
                                    data-testid={`val-row-${v.preventivo_id}`}>

                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-xs font-bold text-slate-800">{v.number}</span>
                                                <Badge className="bg-slate-100 text-slate-600 text-[9px]">{v.normativa_attesa}</Badge>
                                                {sc && (
                                                    sc.classificazione.corretto
                                                        ? <Badge className="bg-emerald-100 text-emerald-700 text-[9px] gap-0.5"><CheckCircle2 className="h-2.5 w-2.5" /> OK</Badge>
                                                        : <Badge className="bg-red-100 text-red-700 text-[9px] gap-0.5"><XCircle className="h-2.5 w-2.5" /> {sc.classificazione.ottenuto}</Badge>
                                                )}
                                            </div>
                                            <p className="text-[11px] text-slate-600 mt-0.5 truncate">{v.subject}</p>
                                            <p className="text-[9px] text-slate-400">{v.note}</p>
                                        </div>

                                        {sc && (
                                            <div className="w-48 shrink-0 space-y-1">
                                                <ScoreCell label="Globale" value={sc.punteggio_globale} />
                                                <div className="grid grid-cols-2 gap-1">
                                                    <ScoreCell label="Class." value={sc.classificazione.punteggio} />
                                                    <ScoreCell label="Estr." value={sc.estrazione.punteggio} />
                                                </div>
                                            </div>
                                        )}

                                        {!sc && (
                                            <Button size="sm" variant="outline"
                                                onClick={() => runSingle(v.preventivo_id)}
                                                disabled={isRunning || runningBatch}
                                                data-testid={`btn-run-${v.preventivo_id}`}>
                                                {isRunning ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                                            </Button>
                                        )}
                                    </div>

                                    {/* Expanded scorecard details */}
                                    {sc && (
                                        <div className="mt-2 pt-2 border-t border-slate-100 space-y-1">
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
                                                <div>
                                                    <span className="text-slate-400">Normativa AI:</span>{' '}
                                                    <span className="font-medium">{sc.classificazione.ottenuto}</span>
                                                    <span className="text-slate-300 ml-1">({sc.classificazione.confidenza_ai})</span>
                                                </div>
                                                <div>
                                                    <span className="text-slate-400">Profilo:</span>{' '}
                                                    <span className="font-medium">{sc.profilo.ottenuto_tipo} {sc.profilo.ottenuto_valore}</span>
                                                    {sc.profilo.tipo_corretto ? <CheckCircle2 className="h-2.5 w-2.5 text-emerald-500 inline ml-1" /> : <XCircle className="h-2.5 w-2.5 text-red-400 inline ml-1" />}
                                                </div>
                                                <div>
                                                    <span className="text-slate-400">Elementi:</span>{' '}
                                                    <span className="font-medium">{sc.estrazione.n_elementi} trovati</span>
                                                    <span className="text-slate-300 ml-1">(copertura {Math.round(sc.estrazione.copertura_elementi * 100)}%)</span>
                                                </div>
                                                <div>
                                                    <span className="text-slate-400">Domande:</span>{' '}
                                                    <span className="font-medium">{sc.domande.n_domande}</span>
                                                    <span className="text-slate-300 ml-1">({sc.domande.n_impatto_alto} alto)</span>
                                                </div>
                                            </div>
                                            {sc.classificazione.motivazione_ai && (
                                                <p className="text-[9px] text-slate-400 italic">
                                                    "{sc.classificazione.motivazione_ai}"
                                                </p>
                                            )}
                                            {!sc.estrazione.saldatura_corretta && (
                                                <p className="text-[9px] text-amber-600 flex items-center gap-1">
                                                    <AlertTriangle className="h-2.5 w-2.5" />
                                                    Saldatura: attesa={String(sc.estrazione.saldatura_attesa)}, rilevata={String(sc.estrazione.saldatura_rilevata)}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
