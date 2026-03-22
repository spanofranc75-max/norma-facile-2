import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { apiRequest } from '../lib/utils';
import {
    Brain, Loader2, ShieldCheck, FileText,
    AlertTriangle, CheckCircle2, HelpCircle, Minus,
    Hammer, Flame, Ruler, Package, Truck, Eye, Wrench,
    ArrowLeft, RefreshCw, CircleAlert, Lightbulb, Save,
    Target, ChevronDown, ChevronUp, Zap, Ban, ShieldAlert,
} from 'lucide-react';

/* ───────────── CONSTANTS ───────────── */

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

/* ───────── SMART QUESTION CONFIG ───────── */
function getQuestionConfig(domanda) {
    const t = (domanda || '').toLowerCase();
    if (t.includes('montaggio') || t.includes('installazione') || t.includes('cantiere')) {
        return { opzioni: ['Si, installazione in cantiere inclusa', 'Solo assemblaggio in officina', 'Montaggio affidato a terzi', 'Non previsto'] };
    }
    if (t.includes('protezione superficial') || t.includes('zincatura') || t.includes('verniciatura') || t.includes('trattamento') || t.includes('rivestimento')) {
        return { opzioni: ['Zincatura a caldo', 'Zincatura a freddo', 'Verniciatura industriale', 'Nessun trattamento', 'Da definire con cliente'] };
    }
    if (t.includes('tolleranz') || t.includes('dimension')) {
        return { opzioni: ['Tolleranze standard EN 1090', 'Tolleranze speciali (da disegno)', 'Non specificate dal cliente'] };
    }
    if (t.includes('saldatura') || t.includes('saldare') || t.includes('giunzione')) {
        return { opzioni: ['Si, in officina', 'Si, affidata a terzi', 'No, solo bullonatura', 'Da definire'] };
    }
    if (t.includes('materiale') || t.includes('acciaio') || t.includes('tipo di acciaio')) {
        return { opzioni: ['S235JR', 'S275JR', 'S355JR', 'Inox 304', 'Altro'] };
    }
    if (t.includes('mista') || t.includes('classificazione diversa')) {
        return { opzioni: ['Si, commessa mista', 'No, normativa unica', 'Da verificare'] };
    }
    if (t.includes('è inclus') || t.includes('è previst') || t.includes('è stato consider') ||
        t.includes('ci sono') || t.includes('sono previst') || t.includes('è richiest') ||
        t.includes('è necessari') || t.includes('prevede') || t.includes('richiede')) {
        return { opzioni: ['Si', 'No', 'Da verificare'] };
    }
    return { opzioni: [] };
}

/* ───────── FRONTEND APPLICABILITY ENGINE (mirrors backend) ───────── */
function detectCategory(questionText) {
    const t = (questionText || '').toLowerCase();
    if (['saldatura', 'saldare', 'saldato', 'giunzione'].some(kw => t.includes(kw))) return 'saldatura';
    if (['protezione superficial', 'zincatura', 'verniciatura', 'trattamento superficial', 'rivestimento'].some(kw => t.includes(kw))) return 'zincatura';
    if (['montaggio', 'installazione', 'cantiere', 'posa in opera'].some(kw => t.includes(kw))) return 'montaggio';
    if (['mista', 'normativa mista', 'classificazione diversa'].some(kw => t.includes(kw))) return 'commessa_mista';
    return null;
}

function parseAnswer(answerText, category) {
    const t = (answerText || '').toLowerCase().trim();
    if (!t) return 'pending';

    if (category === 'saldatura') {
        if (['no', 'non previst', 'bullonatura', 'bullonata', 'nessuna saldatura'].some(kw => t.includes(kw))) return 'negative';
        if (['sì', 'si', 'officina', 'terzi', 'previst'].some(kw => t.includes(kw))) return 'positive';
        if (t.includes('verificare') || t.includes('definire')) return 'pending';
        return 'positive';
    }
    if (category === 'zincatura') {
        if (['nessun trattamento', 'non previst', 'no'].some(kw => t.includes(kw))) return 'negative';
        if (['esterna', 'terzi', 'subfornitore', 'terzista'].some(kw => t.includes(kw))) return 'external';
        if (['a caldo', 'a freddo', 'verniciatura', 'industriale'].some(kw => t.includes(kw))) return 'positive';
        if (t.includes('definire') || t.includes('verificare')) return 'pending';
        return 'positive';
    }
    if (category === 'montaggio') {
        if (['no', 'non previsto', 'non prevista', 'solo officina', 'solo assemblaggio'].some(kw => t.includes(kw))) return 'negative';
        if (['sì', 'si', 'inclusa', 'cantiere', 'installazione'].some(kw => t.includes(kw))) return 'positive';
        if (['terzi', 'affidato'].some(kw => t.includes(kw))) return 'external';
        if (t.includes('verificare') || t.includes('definire')) return 'pending';
        return 'positive';
    }
    if (category === 'commessa_mista') {
        if (['sì', 'si', 'mista'].some(kw => t.includes(kw))) return 'positive';
        if (['no', 'non', 'unica'].some(kw => t.includes(kw))) return 'negative';
        return 'pending';
    }
    return 'pending';
}

function calcolaApplicabilitaLocale(domande, risposteLocali) {
    const decisioni = {};
    (domande || []).forEach((q, idx) => {
        const cat = detectCategory(q.domanda);
        if (!cat) return;
        const answer = risposteLocali[String(idx)] || '';
        decisioni[cat] = { stato: parseAnswer(answer, cat), risposta: answer, domanda_idx: idx };
    });

    const itemsNonApplicabili = [];
    const itemsCondizionali = [];
    const blocchiConferma = [];
    const riepilogo = {};

    // Saldatura
    const sald = decisioni.saldatura;
    if (sald?.stato === 'negative') {
        riepilogo.saldatura = 'Non prevista';
        ['WPS', 'WPQR', 'Qualifica saldatori', 'VT saldature', 'Registro saldatura'].forEach(nome =>
            itemsNonApplicabili.push({ nome, reason_code: 'NO_WELDING', reason_text: 'Non applicabile: nessuna saldatura prevista', categoria: 'saldatura' })
        );
    } else if (sald?.stato === 'positive') { riepilogo.saldatura = 'Prevista'; }
    else if (sald?.stato === 'pending') { riepilogo.saldatura = 'Da confermare'; }

    // Zincatura
    const zinc = decisioni.zincatura;
    if (zinc?.stato === 'negative') {
        riepilogo.zincatura = 'Non prevista';
        ['Certificato zincatura', 'Controllo trattamento superficiale'].forEach(nome =>
            itemsNonApplicabili.push({ nome, reason_code: 'NO_GALVANIZING', reason_text: 'Non applicabile: nessun trattamento superficiale previsto', categoria: 'zincatura' })
        );
    } else if (zinc?.stato === 'external') {
        riepilogo.zincatura = 'Esterna (terzista)';
        ['Documentazione subfornitore', 'DDT verso terzista', 'Certificato trattamento esterno'].forEach(nome =>
            itemsCondizionali.push({ nome, reason_code: 'EXTERNAL_GALVANIZING', reason_text: 'Richiesto: trattamento affidato a terzista', categoria: 'zincatura' })
        );
    } else if (zinc?.stato === 'positive') { riepilogo.zincatura = 'Prevista (interna)'; }
    else if (zinc?.stato === 'pending') { riepilogo.zincatura = 'Da confermare'; }

    // Commessa mista
    const mista = decisioni.commessa_mista;
    if (mista?.stato === 'positive') {
        riepilogo.commessa_mista = 'Si — richiede segmentazione';
        blocchiConferma.push({
            tipo: 'MIXED_ORDER_REQUIRES_SEGMENTATION',
            messaggio: 'La commessa non puo essere confermata come blocco unico. E necessaria la segmentazione normativa.',
            bloccante: true,
        });
    } else if (mista?.stato === 'negative') { riepilogo.commessa_mista = 'No — normativa unica'; }
    else if (mista?.stato === 'pending') { riepilogo.commessa_mista = 'Da confermare'; }

    // Montaggio
    const mont = decisioni.montaggio;
    if (mont?.stato === 'negative') {
        riepilogo.montaggio = 'Non previsto';
        ['Piano montaggio', 'Documenti posa in opera', 'POS cantiere', 'Controllo posa', 'Ispezione cantiere'].forEach(nome =>
            itemsNonApplicabili.push({ nome, reason_code: 'NO_INSTALLATION', reason_text: 'Non applicabile: montaggio/installazione non previsto', categoria: 'montaggio' })
        );
    } else if (mont?.stato === 'positive') { riepilogo.montaggio = 'Previsto (inclusa installazione)'; }
    else if (mont?.stato === 'external') { riepilogo.montaggio = 'Affidato a terzi'; }
    else if (mont?.stato === 'pending') { riepilogo.montaggio = 'Da confermare'; }

    return { decisioni, items_non_applicabili: itemsNonApplicabili, items_condizionali: itemsCondizionali, blocchi_conferma: blocchiConferma, riepilogo };
}

/* ───────── SUB-COMPONENTS ───────── */

function StatoBadge({ stato }) {
    return (
        <Badge className={`text-[9px] px-1.5 py-0 gap-0.5 border ${STATO_COLORS[stato] || 'bg-slate-100 text-slate-600'}`}>
            {STATO_ICONS[stato]} {stato}
        </Badge>
    );
}

const RIEPILOGO_LABELS = {
    saldatura: 'Saldatura', zincatura: 'Zincatura',
    montaggio: 'Montaggio', commessa_mista: 'Commessa mista',
};
const RIEPILOGO_ICONS = {
    saldatura: Flame, zincatura: Truck, montaggio: Hammer, commessa_mista: AlertTriangle,
};

/* ───────────── PAGE ───────────── */

export default function IstruttoriaPage() {
    const { preventivoId } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [risposte, setRisposte] = useState({});
    const [savingRisposte, setSavingRisposte] = useState(false);
    const [showTechDetails, setShowTechDetails] = useState(false);

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

    useEffect(() => {
        if (data?.risposte_utente) {
            const saved = {};
            Object.entries(data.risposte_utente).forEach(([idx, val]) => {
                saved[idx] = val.risposta || '';
            });
            setRisposte(saved);
        }
    }, [data?.risposte_utente]);

    const handleRispostaChange = (idx, value) => {
        setRisposte(prev => ({ ...prev, [String(idx)]: value }));
    };

    const handleQuickAnswer = (idx, option) => {
        const current = risposte[String(idx)] || '';
        handleRispostaChange(idx, current === option ? '' : option);
    };

    const handleSalvaRisposte = async () => {
        if (!data?.istruttoria_id) return;
        const payload = Object.entries(risposte)
            .filter(([, v]) => v.trim())
            .map(([idx, risposta]) => ({ domanda_idx: parseInt(idx), risposta }));
        if (!payload.length) { toast.warning('Inserisci almeno una risposta'); return; }
        setSavingRisposte(true);
        try {
            await apiRequest(`/istruttoria/${data.istruttoria_id}/rispondi`, {
                method: 'POST', body: { risposte: payload },
            });
            toast.success(`Risposte salvate (${payload.length})`);
            fetchIstruttoria();
        } catch (e) { toast.error(e.message); }
        finally { setSavingRisposte(false); }
    };

    const handleAnalizza = async () => {
        setAnalyzing(true);
        try {
            toast.info('Analisi AI in corso...');
            const res = await apiRequest(`/istruttoria/analizza-preventivo/${preventivoId}`, { method: 'POST' });
            setData(res);
            toast.success('Istruttoria completata');
        } catch (e) { toast.error(e.message); }
        finally { setAnalyzing(false); }
    };

    const handleRevisione = async (campo, valoreCorretto, motivazione = '') => {
        try {
            await apiRequest(`/istruttoria/${data.istruttoria_id}/revisione`, {
                method: 'POST', body: { campo, valore_corretto: valoreCorretto, motivazione },
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

    // ── Real-time applicability (local, mirrors backend) ──
    const applicabilita = useMemo(() => {
        if (!data?.domande_residue) return null;
        return calcolaApplicabilitaLocale(data.domande_residue, risposte);
    }, [data?.domande_residue, risposte]);

    // Check if user has unsaved changes (local risposte differs from saved)
    const hasLocalChanges = useMemo(() => {
        if (!data?.risposte_utente) return Object.keys(risposte).length > 0;
        const savedRisposte = {};
        Object.entries(data.risposte_utente).forEach(([idx, val]) => {
            savedRisposte[idx] = val.risposta || '';
        });
        return Object.keys(risposte).some(idx => risposte[idx] !== savedRisposte[idx]);
    }, [data?.risposte_utente, risposte]);

    // Use local calculation for real-time updates when user has unsaved changes
    const appData = hasLocalChanges ? applicabilita : (data?.applicabilita || applicabilita);
    const nonApplicabiliNomi = useMemo(() =>
        new Set((appData?.items_non_applicabili || []).map(i => i.nome.toLowerCase())),
        [appData?.items_non_applicabili]
    );
    const blocchiConferma = appData?.blocchi_conferma || [];
    const hasBloccoBloccante = blocchiConferma.some(b => b.bloccante);

    /* ─── Loading ─── */
    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        </DashboardLayout>
    );

    /* ─── No analysis yet ─── */
    if (!data) return (
        <DashboardLayout>
            <div className="max-w-2xl mx-auto mt-16 text-center space-y-6">
                <Brain className="h-16 w-16 mx-auto text-blue-600 opacity-80" />
                <h1 className="text-2xl font-bold text-slate-800">Motore di Istruttoria Automatica</h1>
                <p className="text-slate-500">
                    Analizza il preventivo <strong>{preventivoId}</strong> per estrarre dati tecnici,
                    classificare la normativa e proporre l'istruttoria completa.
                </p>
                <Button size="lg" onClick={handleAnalizza} disabled={analyzing}
                    className="bg-blue-700 hover:bg-blue-800 text-white px-8" data-testid="btn-avvia-istruttoria">
                    {analyzing ? <Loader2 className="h-5 w-5 mr-2 animate-spin" /> : <Brain className="h-5 w-5 mr-2" />}
                    {analyzing ? 'Analisi in corso...' : 'Avvia Istruttoria AI'}
                </Button>
            </div>
        </DashboardLayout>
    );

    /* ─── Destructure data ─── */
    const { classificazione, profilo_tecnico, estrazione_tecnica, stato_conoscenza,
        fasi_produttive_attese, documenti_richiesti, controlli_richiesti,
        prerequisiti_saldatura, prerequisiti_tracciabilita,
        domande_residue, warnings_regole, enrichments_regole,
        revisioni_umane, confermata, stato_revisione } = data;

    const normativa = classificazione?.normativa_proposta || 'N/D';
    const conf = classificazione?.confidenza || 'bassa';
    const nDomande = domande_residue?.length || 0;
    const nRisposte = data?.n_risposte || Object.keys(data?.risposte_utente || {}).length;
    const progressPct = nDomande > 0 ? Math.round((nRisposte / nDomande) * 100) : 100;
    const tutteRisposte = nDomande > 0 && nRisposte >= nDomande;
    const profiloLabel = profilo_tecnico?.tipo === 'exc' ? 'Classe Esecuzione'
        : profilo_tecnico?.tipo === 'categorie_prestazione' ? 'Categorie Prestazione' : 'Complessita';

    // Riepilogo for display
    const riepilogo = appData?.riepilogo || {};
    const hasRiepilogo = Object.keys(riepilogo).length > 0;

    // Helper: is a document/control name in the non-applicable list?
    const isNonApplicabile = (nome) => nonApplicabiliNomi.has(nome.toLowerCase());

    // Check prerequisiti against non-applicable
    const wpsNonApplicabile = nonApplicabiliNomi.has('wps');
    const wpqrNonApplicabile = nonApplicabiliNomi.has('wpqr');
    const qualificaNonApplicabile = nonApplicabiliNomi.has('qualifica saldatori');

    return (
        <DashboardLayout>
            <div className="space-y-4 max-w-5xl mx-auto" data-testid="istruttoria-page">

                {/* ════════════════ HEADER ════════════════ */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} data-testid="btn-indietro">
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                        <div>
                            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <Brain className="h-5 w-5 text-blue-600" />
                                Istruttoria Automatica
                            </h1>
                            <p className="text-xs text-slate-500 mt-0.5">Preventivo {data.preventivo_number} — v{data.versione}</p>
                        </div>
                    </div>
                    <Button size="sm" variant="outline" onClick={handleAnalizza} disabled={analyzing} data-testid="btn-riesegui-istruttoria">
                        <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${analyzing ? 'animate-spin' : ''}`} />
                        Riesegui
                    </Button>
                </div>

                {/* ════════════════ ESITO ISTRUTTORIA ════════════════ */}
                <Card className={`border-2 ${confermata ? 'border-emerald-400 bg-emerald-50/40' : 'border-blue-300 bg-gradient-to-r from-blue-50/80 to-slate-50'}`}
                    data-testid="card-esito-istruttoria">
                    <CardContent className="p-5">
                        <div className="flex items-start justify-between gap-6">
                            <div className="flex-1 space-y-3">
                                <div className="flex items-center gap-2">
                                    <Target className="h-4 w-4 text-blue-700" />
                                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Esito Istruttoria</span>
                                    {confermata ? (
                                        <Badge className="bg-emerald-600 text-white text-[9px] px-2 gap-1">
                                            <ShieldCheck className="h-3 w-3" /> Confermata
                                        </Badge>
                                    ) : (
                                        <Badge className="bg-blue-100 text-blue-700 text-[9px] px-2 border border-blue-200">Proposta AI</Badge>
                                    )}
                                </div>

                                <div className="flex items-center gap-4 flex-wrap">
                                    <div>
                                        <p className="text-[10px] text-slate-500 mb-0.5">Normativa</p>
                                        <Badge className={`text-sm px-3 py-1 ${NORM_COLORS[normativa]}`} data-testid="badge-normativa">
                                            {normativa.replace('_', ' ')}
                                        </Badge>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-slate-500 mb-0.5">{profiloLabel}</p>
                                        <span className="text-xl font-black text-slate-900" data-testid="profilo-valore">
                                            {profilo_tecnico?.valore || 'N/D'}
                                        </span>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-slate-500 mb-0.5">Confidenza</p>
                                        <Badge className={`text-[10px] px-2 py-0.5 ${conf === 'alta' ? 'bg-emerald-100 text-emerald-700' : conf === 'media' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                                            {conf}
                                        </Badge>
                                    </div>
                                    <div className="flex flex-wrap gap-1 ml-2">
                                        {['confermato', 'dedotto', 'mancante', 'incerto'].map(s => (
                                            stato_conoscenza?.[s] > 0 && (
                                                <Badge key={s} className={`text-[8px] px-1 py-0 gap-0.5 border ${STATO_COLORS[s]}`}>
                                                    {STATO_ICONS[s]} {stato_conoscenza[s]}
                                                </Badge>
                                            )
                                        ))}
                                    </div>
                                </div>

                                {classificazione?.motivazione && (
                                    <p className="text-[11px] text-slate-600 leading-relaxed border-l-2 border-blue-300 pl-3 italic" data-testid="motivazione-ai">
                                        {classificazione.motivazione}
                                    </p>
                                )}

                                {/* ── Riepilogo decisioni ── */}
                                {hasRiepilogo && (
                                    <div className="flex flex-wrap gap-2 pt-1" data-testid="riepilogo-decisioni">
                                        {Object.entries(riepilogo).map(([key, val]) => {
                                            const Icon = RIEPILOGO_ICONS[key] || HelpCircle;
                                            const isPending = val?.includes('Da confermare');
                                            const isNeg = val?.includes('Non previst');
                                            const isBlock = key === 'commessa_mista' && val?.includes('segmentazione');
                                            return (
                                                <div key={key}
                                                    className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border ${
                                                        isBlock ? 'bg-red-50 border-red-300 text-red-700' :
                                                        isNeg ? 'bg-slate-100 border-slate-300 text-slate-500' :
                                                        isPending ? 'bg-amber-50 border-amber-200 text-amber-700' :
                                                        'bg-emerald-50 border-emerald-200 text-emerald-700'
                                                    }`}>
                                                    <Icon className="h-3 w-3" />
                                                    <span className="font-medium">{RIEPILOGO_LABELS[key] || key}:</span>
                                                    <span>{val}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Right: Progress */}
                            {!confermata && nDomande > 0 && (
                                <div className="w-52 shrink-0 space-y-2 text-right" data-testid="progress-section">
                                    <div>
                                        <span className="text-2xl font-black text-slate-900">{nRisposte}</span>
                                        <span className="text-sm text-slate-400">/{nDomande}</span>
                                        <p className="text-[10px] text-slate-500">conferme date</p>
                                    </div>
                                    <Progress value={progressPct}
                                        className={`h-2.5 ${tutteRisposte ? '[&>div]:bg-emerald-500' : '[&>div]:bg-blue-600'}`} />
                                    <p className="text-[10px] text-slate-500">
                                        {tutteRisposte
                                            ? 'Tutte le conferme date — puoi procedere'
                                            : `Rispondi a ${nDomande - nRisposte} domand${nDomande - nRisposte === 1 ? 'a' : 'e'} per procedere`}
                                    </p>
                                </div>
                            )}
                            {confermata && (
                                <div className="w-48 shrink-0 text-center space-y-1">
                                    <ShieldCheck className="h-10 w-10 text-emerald-600 mx-auto" />
                                    <p className="text-xs font-bold text-emerald-700">Confermata</p>
                                    <p className="text-[9px] text-slate-500">da {data.confermata_da_nome}</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* ════════════════ BLOCCHI CONFERMA (commessa mista) ════════════════ */}
                {blocchiConferma.length > 0 && (
                    <Card className="border-2 border-red-400 bg-red-50/50" data-testid="card-blocchi-conferma">
                        <CardContent className="p-4">
                            {blocchiConferma.map((b, i) => (
                                <div key={i} className="flex items-start gap-3">
                                    <ShieldAlert className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                                    <div>
                                        <p className="text-sm font-bold text-red-800">Conferma bloccata</p>
                                        <p className="text-xs text-red-700 mt-0.5">{b.messaggio}</p>
                                        <Badge className="bg-red-100 text-red-700 text-[9px] mt-1.5">
                                            {b.tipo}
                                        </Badge>
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ WARNINGS (compact) ════════════════ */}
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

                {/* ════════════════ DOMANDE RESIDUE — INTERACTIVE ════════════════ */}
                {domande_residue?.length > 0 && (
                    <Card className="border-blue-300 bg-white" data-testid="card-domande-residue">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-bold text-slate-800 flex items-center gap-2">
                                <Zap className="h-4 w-4 text-blue-600" />
                                Conferme richieste
                                <Badge className="bg-blue-100 text-blue-700 text-[10px] ml-1">{nRisposte}/{nDomande}</Badge>
                                {tutteRisposte && (
                                    <Badge className="bg-emerald-100 text-emerald-700 text-[9px] gap-0.5">
                                        <CheckCircle2 className="h-2.5 w-2.5" /> Completate
                                    </Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {domande_residue.map((q, i) => {
                                const cfg = getQuestionConfig(q.domanda);
                                const savedAnswer = data?.risposte_utente?.[String(i)];
                                const localValue = risposte[String(i)] || '';
                                const isAnswered = !!savedAnswer;

                                return (
                                    <div key={i}
                                        className={`rounded-lg border transition-all ${isAnswered ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 bg-slate-50/30'}`}
                                        data-testid={`domanda-${i}`}>
                                        <div className="p-3 space-y-2">
                                            <div className="flex items-start gap-3">
                                                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold text-white ${
                                                    isAnswered ? 'bg-emerald-500' :
                                                    q.impatto === 'alto' ? 'bg-red-500' :
                                                    q.impatto === 'medio' ? 'bg-amber-500' : 'bg-slate-400'}`}>
                                                    {isAnswered ? <CheckCircle2 className="h-3 w-3" /> : i + 1}
                                                </div>
                                                <div className="flex-1">
                                                    <p className="text-xs font-semibold text-slate-800">{q.domanda}</p>
                                                    <p className="text-[10px] text-slate-500 mt-0.5">
                                                        <Badge className={`text-[8px] px-1 py-0 mr-1 ${
                                                            q.impatto === 'alto' ? 'bg-red-100 text-red-700' :
                                                            q.impatto === 'medio' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
                                                            impatto {q.impatto}
                                                        </Badge>
                                                        {q.perche_serve}
                                                    </p>
                                                </div>
                                            </div>

                                            {cfg.opzioni.length > 0 && (
                                                <div className="flex flex-wrap gap-1.5 ml-9">
                                                    {cfg.opzioni.map((opt) => (
                                                        <button key={opt} type="button"
                                                            onClick={() => handleQuickAnswer(i, opt)}
                                                            className={`text-[11px] px-3 py-1 rounded-full border transition-all ${
                                                                localValue === opt
                                                                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                                                                    : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400 hover:text-blue-700'}`}
                                                            data-testid={`quick-btn-${i}-${opt.substring(0, 10).replace(/\s/g, '_')}`}>
                                                            {opt}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}

                                            <div className="ml-9">
                                                <Textarea
                                                    placeholder={cfg.opzioni.length > 0 ? 'Oppure scrivi una risposta personalizzata...' : 'Scrivi la tua risposta...'}
                                                    value={localValue}
                                                    onChange={(e) => handleRispostaChange(i, e.target.value)}
                                                    className="text-xs min-h-[44px] border-slate-200 focus:border-blue-400 bg-white"
                                                    rows={2}
                                                    data-testid={`risposta-input-${i}`} />
                                                {isAnswered && (
                                                    <p className="text-[9px] text-emerald-600 mt-1 flex items-center gap-1">
                                                        <CheckCircle2 className="h-2.5 w-2.5" />
                                                        Risposto da {savedAnswer.risposto_da_nome} il {new Date(savedAnswer.risposto_il).toLocaleDateString('it-IT')}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}

                            <div className="flex items-center justify-between pt-2">
                                <p className="text-[10px] text-slate-400">
                                    {tutteRisposte
                                        ? 'Tutte le conferme sono state date. Puoi salvare e procedere alla conferma.'
                                        : 'Puoi salvare anche risposte parziali e completare dopo.'}
                                </p>
                                <Button onClick={handleSalvaRisposte}
                                    disabled={savingRisposte || !Object.values(risposte).some(v => v.trim())}
                                    className="bg-blue-700 hover:bg-blue-800 text-white" data-testid="btn-salva-risposte">
                                    {savingRisposte ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
                                    {savingRisposte ? 'Salvataggio...' : 'Salva Risposte'}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ NON-APPLICABLE ITEMS SUMMARY ════════════════ */}
                {(appData?.items_non_applicabili?.length > 0 || appData?.items_condizionali?.length > 0) && (
                    <Card className="border-slate-300" data-testid="card-applicabilita">
                        <CardContent className="p-3 space-y-2">
                            {appData.items_non_applicabili?.length > 0 && (
                                <div>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                                        <Ban className="h-3 w-3" /> Requisiti non applicabili ({appData.items_non_applicabili.length})
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {appData.items_non_applicabili.map((item, i) => (
                                            <div key={i} className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-400 border border-slate-200 line-through"
                                                title={item.reason_text}>
                                                <Ban className="h-2.5 w-2.5" />
                                                {item.nome}
                                                <span className="text-[8px] no-underline text-slate-300 ml-0.5">[{item.reason_code}]</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {appData.items_condizionali?.length > 0 && (
                                <div>
                                    <p className="text-[10px] font-bold text-amber-600 uppercase tracking-wider mb-1 flex items-center gap-1">
                                        <AlertTriangle className="h-3 w-3" /> Requisiti aggiuntivi ({appData.items_condizionali.length})
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {appData.items_condizionali.map((item, i) => (
                                            <div key={i} className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200"
                                                title={item.reason_text}>
                                                <Lightbulb className="h-2.5 w-2.5" />
                                                {item.nome}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ AMBIGUITIES ════════════════ */}
                {estrazione_tecnica?.ambiguita_rilevate?.length > 0 && (
                    <Card className="border-amber-200 bg-amber-50/30">
                        <CardContent className="p-3">
                            <p className="text-xs font-bold text-amber-800 flex items-center gap-1.5 mb-1">
                                <AlertTriangle className="h-3.5 w-3.5" /> Punti incerti da verificare
                            </p>
                            <div className="space-y-0.5">
                                {estrazione_tecnica.ambiguita_rilevate.map((a, i) => (
                                    <div key={i} className="text-[10px] text-amber-800 py-0.5">
                                        <strong>{a.punto}</strong>
                                        <Badge className={`text-[8px] px-1 py-0 ml-1 ${a.impatto === 'alto' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>{a.impatto}</Badge>
                                        <span className="text-amber-600 ml-1">Possibili: {a.possibili_interpretazioni?.join(' / ')}</span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ TECHNICAL DETAILS (collapsible) ════════════════ */}
                <Card className="border-slate-200">
                    <button onClick={() => setShowTechDetails(!showTechDetails)}
                        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-50 transition-colors rounded-lg"
                        data-testid="toggle-tech-details">
                        <span className="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-2">
                            <FileText className="h-3.5 w-3.5" />
                            Dettaglio tecnico estratto
                            <Badge className="bg-slate-100 text-slate-500 text-[8px]">
                                {(estrazione_tecnica?.elementi_strutturali?.length || 0)} elementi ·
                                {(estrazione_tecnica?.lavorazioni_rilevate?.length || 0)} lavorazioni ·
                                {(documenti_richiesti?.length || 0)} documenti
                            </Badge>
                        </span>
                        {showTechDetails ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                    </button>

                    {showTechDetails && (
                        <CardContent className="pt-0 space-y-4">
                            {/* Structural Elements */}
                            <div>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Materiali e elementi rilevati</p>
                                <div className="space-y-1">
                                    {(estrazione_tecnica?.elementi_strutturali || []).map((el, i) => (
                                        <div key={i} className="flex items-start gap-2 py-1 border-b border-slate-100 last:border-0">
                                            <Package className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <div className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                                                    {el.descrizione} <StatoBadge stato={el.stato} />
                                                </div>
                                                <div className="text-[10px] text-slate-500 flex gap-3 mt-0.5">
                                                    {el.profilo && <span>Profilo: <strong>{el.profilo}</strong></span>}
                                                    {el.materiale_base && <span>Mat: <strong>{el.materiale_base}</strong></span>}
                                                    {el.spessore_mm && <span>Sp: {el.spessore_mm}mm</span>}
                                                    {el.peso_stimato_kg && <span>~{el.peso_stimato_kg}kg</span>}
                                                </div>
                                                {el.fonte_nel_testo && <div className="text-[9px] text-slate-400 italic mt-0.5">"{el.fonte_nel_testo}"</div>}
                                            </div>
                                        </div>
                                    ))}
                                    {(!estrazione_tecnica?.elementi_strutturali?.length) && (
                                        <p className="text-xs text-slate-400 italic">Nessun elemento strutturale estratto</p>
                                    )}
                                </div>
                            </div>

                            {/* Processes + Welding + Treatments */}
                            <div>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Lavorazioni previste</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {(estrazione_tecnica?.lavorazioni_rilevate || []).map((lav, i) => {
                                        const Icon = LAV_ICONS[lav.tipo] || Wrench;
                                        return (
                                            <Badge key={i} variant="outline" className="text-[9px] px-2 py-0.5 gap-1">
                                                <Icon className="h-2.5 w-2.5" /> {lav.tipo}: {lav.dettaglio} <StatoBadge stato={lav.stato} />
                                            </Badge>
                                        );
                                    })}
                                </div>

                                {estrazione_tecnica?.saldature?.presenti && (
                                    <div className={`rounded-lg p-2.5 mt-2 space-y-1 border ${
                                        wpsNonApplicabile ? 'bg-slate-50 border-slate-200 opacity-60' : 'bg-orange-50 border-orange-200'}`}>
                                        <p className={`text-xs font-bold flex items-center gap-1 ${wpsNonApplicabile ? 'text-slate-400' : 'text-orange-800'}`}>
                                            <Flame className="h-3.5 w-3.5" /> Saldature attese
                                            <StatoBadge stato={estrazione_tecnica.saldature.stato} />
                                            {wpsNonApplicabile && <Badge className="bg-slate-200 text-slate-500 text-[8px] ml-1">non applicabile</Badge>}
                                        </p>
                                        {!wpsNonApplicabile && (
                                            <>
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
                                            </>
                                        )}
                                    </div>
                                )}

                                {estrazione_tecnica?.trattamenti_superficiali?.tipo && estrazione_tecnica.trattamenti_superficiali.tipo !== 'nessuno' && (
                                    <div className={`rounded-lg p-2.5 mt-2 border ${
                                        nonApplicabiliNomi.has('certificato zincatura') ? 'bg-slate-50 border-slate-200 opacity-60' : 'bg-cyan-50 border-cyan-200'}`}>
                                        <p className={`text-xs font-bold flex items-center gap-1 ${
                                            nonApplicabiliNomi.has('certificato zincatura') ? 'text-slate-400' : 'text-cyan-800'}`}>
                                            <Truck className="h-3.5 w-3.5" />
                                            {estrazione_tecnica.trattamenti_superficiali.tipo}
                                            {estrazione_tecnica.trattamenti_superficiali.esecuzione && (
                                                <Badge className="bg-cyan-100 text-cyan-700 text-[9px] px-1.5 py-0 ml-1">
                                                    {estrazione_tecnica.trattamenti_superficiali.esecuzione}
                                                </Badge>
                                            )}
                                            <StatoBadge stato={estrazione_tecnica.trattamenti_superficiali.stato} />
                                            {nonApplicabiliNomi.has('certificato zincatura') && (
                                                <Badge className="bg-slate-200 text-slate-500 text-[8px] ml-1">non applicabile</Badge>
                                            )}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Documents + Controls + Prerequisites */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Documenti da produrre ({documenti_richiesti?.length || 0})</p>
                                    {(documenti_richiesti || []).map((d, i) => {
                                        const na = isNonApplicabile(d.documento);
                                        return (
                                            <div key={i} className={`flex items-start gap-1.5 py-0.5 ${na ? 'opacity-40' : ''}`}>
                                                {na ? <Ban className="h-3 w-3 mt-0.5 shrink-0 text-slate-300" /> :
                                                    <FileText className={`h-3 w-3 mt-0.5 shrink-0 ${d.obbligatorio ? 'text-red-500' : 'text-slate-400'}`} />}
                                                <p className={`text-[10px] ${na ? 'text-slate-400 line-through' : 'text-slate-700'}`}>{d.documento}</p>
                                            </div>
                                        );
                                    })}
                                    {/* Conditionally required */}
                                    {(appData?.items_condizionali || []).filter(c => c.categoria === 'zincatura').map((c, i) => (
                                        <div key={`cond-${i}`} className="flex items-start gap-1.5 py-0.5">
                                            <Lightbulb className="h-3 w-3 mt-0.5 shrink-0 text-amber-500" />
                                            <p className="text-[10px] text-amber-700 font-medium">{c.nome} <span className="text-[8px] text-amber-400">(aggiunto)</span></p>
                                        </div>
                                    ))}
                                </div>

                                <div>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Controlli da fare ({controlli_richiesti?.length || 0})</p>
                                    {(controlli_richiesti || []).map((c, i) => {
                                        const na = isNonApplicabile(c.descrizione) || isNonApplicabile(c.tipo);
                                        return (
                                            <div key={i} className={`flex items-start gap-1.5 py-0.5 ${na ? 'opacity-40' : ''}`}>
                                                {na ? <Ban className="h-3 w-3 mt-0.5 shrink-0 text-slate-300" /> :
                                                    <Eye className={`h-3 w-3 mt-0.5 shrink-0 ${c.tipo.startsWith('CND') ? 'text-purple-500' : 'text-blue-500'}`} />}
                                                <p className={`text-[10px] ${na ? 'text-slate-400 line-through' : 'text-slate-700'}`}>
                                                    <span className="font-mono text-[8px] text-slate-400 mr-1">{c.tipo}</span>
                                                    {c.descrizione}
                                                </p>
                                            </div>
                                        );
                                    })}
                                </div>

                                <div>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Prerequisiti</p>
                                    {prerequisiti_saldatura?.richiesti && (
                                        <div className={`text-[10px] space-y-0.5 mb-2 ${wpsNonApplicabile ? 'opacity-40' : ''}`}>
                                            <p className={`font-medium ${wpsNonApplicabile ? 'text-slate-400' : 'text-orange-700'}`}>
                                                Saldatura: {wpsNonApplicabile && <span className="text-[8px]">(non applicabile)</span>}
                                            </p>
                                            <p className={wpsNonApplicabile ? 'text-slate-400 line-through' : prerequisiti_saldatura.wps_necessarie ? 'text-red-600' : 'text-slate-400'}>
                                                WPS: {prerequisiti_saldatura.wps_necessarie ? 'Obbligatorie' : 'Non richieste'}
                                            </p>
                                            <p className={wpqrNonApplicabile ? 'text-slate-400 line-through' : prerequisiti_saldatura.wpqr_necessarie ? 'text-red-600' : 'text-slate-400'}>
                                                WPQR: {prerequisiti_saldatura.wpqr_necessarie ? 'Obbligatorie' : 'Non richieste'}
                                            </p>
                                            <p className={qualificaNonApplicabile ? 'text-slate-400 line-through' : prerequisiti_saldatura.qualifica_saldatori ? 'text-red-600' : 'text-slate-400'}>
                                                Qualifica: {prerequisiti_saldatura.qualifica_saldatori ? 'Obbligatoria' : 'Non richiesta'}
                                            </p>
                                        </div>
                                    )}
                                    {prerequisiti_tracciabilita?.certificati_31_richiesti && (
                                        <div className="text-[10px] space-y-0.5">
                                            <p className="font-medium text-blue-700">Tracciabilita:</p>
                                            <p className="text-red-600">Cert. 3.1: Obbligatori</p>
                                            <p className={prerequisiti_tracciabilita.tracciabilita_colata ? 'text-red-600' : 'text-slate-400'}>
                                                Colata: {prerequisiti_tracciabilita.tracciabilita_colata ? 'Si' : 'No'}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Production phases */}
                            {fasi_produttive_attese?.length > 0 && (
                                <div>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Fasi produttive attese</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {fasi_produttive_attese.sort((a, b) => a.ordine - b.ordine).map((f, i) => (
                                            <Badge key={i} variant="outline"
                                                className={`text-[9px] px-2 py-0.5 ${f.obbligatoria ? 'border-blue-300 text-blue-700' : 'border-slate-200 text-slate-500'}`}>
                                                <span className="font-mono text-[8px] mr-1 opacity-50">{f.ordine}.</span>
                                                {f.fase}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    )}
                </Card>

                {/* ════════════════ RULES ENRICHMENTS ════════════════ */}
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

                {/* ════════════════ AI NOTE ════════════════ */}
                {estrazione_tecnica?.note_tecnico && (
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <p className="text-xs font-bold text-slate-600 mb-1 flex items-center gap-1">
                                <Brain className="h-3.5 w-3.5 text-blue-500" /> Nota del Tecnico AI
                            </p>
                            <p className="text-[10px] text-slate-600 leading-relaxed italic">"{estrazione_tecnica.note_tecnico}"</p>
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ HUMAN REVISIONS ════════════════ */}
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
                                            {r.motivazione_correzione && <span className="text-slate-400 ml-1">— {r.motivazione_correzione}</span>}
                                            <span className="text-slate-300 ml-1">({r.corretto_da_nome})</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ CTA — CONFIRMATION BAR ════════════════ */}
                <Card className={`border-2 ${
                    confermata ? 'border-emerald-400 bg-emerald-50/40' :
                    hasBloccoBloccante ? 'border-red-300 bg-red-50/30' :
                    tutteRisposte ? 'border-emerald-300 bg-emerald-50/30' :
                    'border-slate-300 bg-slate-50/30'
                }`} data-testid="card-conferma">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            {confermata ? (
                                <>
                                    <p className="text-sm font-bold text-emerald-800 flex items-center gap-2">
                                        <ShieldCheck className="h-4 w-4" /> Istruttoria Confermata
                                    </p>
                                    <p className="text-[10px] text-slate-500 mt-0.5">
                                        Confermata da {data.confermata_da_nome} — Pronta per Fase 2 (Generazione Commessa)
                                    </p>
                                </>
                            ) : hasBloccoBloccante ? (
                                <>
                                    <p className="text-sm font-bold text-red-800 flex items-center gap-2">
                                        <ShieldAlert className="h-4 w-4" /> Richiede segmentazione
                                    </p>
                                    <p className="text-[10px] text-red-600 mt-0.5">
                                        La commessa non puo essere confermata come blocco unico. Completa la segmentazione normativa.
                                    </p>
                                </>
                            ) : tutteRisposte ? (
                                <>
                                    <p className="text-sm font-bold text-emerald-800">Pronta per la conferma</p>
                                    <p className="text-[10px] text-slate-500 mt-0.5">
                                        Tutte le conferme sono state date. Conferma per generare la commessa pre-istruita.
                                    </p>
                                </>
                            ) : (
                                <>
                                    <p className="text-sm font-bold text-slate-700">Conferma e procedi</p>
                                    <p className="text-[10px] text-slate-500 mt-0.5">
                                        {nDomande > 0
                                            ? `Completa le ${nDomande - nRisposte} conferme rimanenti, poi conferma per procedere`
                                            : 'Revisiona i dati e conferma per procedere alla generazione commessa'}
                                    </p>
                                </>
                            )}
                            {stato_revisione === 'revisionato' && !confermata && (
                                <Badge className="bg-indigo-100 text-indigo-700 text-[9px] mt-1">
                                    {revisioni_umane?.length || 0} correzioni applicate
                                </Badge>
                            )}
                        </div>
                        {!confermata && !hasBloccoBloccante && (
                            <Button onClick={handleConferma}
                                className={`${tutteRisposte ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-slate-600 hover:bg-slate-700'} text-white`}
                                data-testid="btn-conferma-istruttoria">
                                <ShieldCheck className="h-4 w-4 mr-1.5" />
                                {tutteRisposte ? 'Conferma Istruttoria' : 'Conferma Comunque'}
                            </Button>
                        )}
                        {!confermata && hasBloccoBloccante && (
                            <Badge className="bg-red-100 text-red-700 text-sm px-3 py-1.5 gap-1">
                                <ShieldAlert className="h-4 w-4" /> Completa segmentazione
                            </Badge>
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
