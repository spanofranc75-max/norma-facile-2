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
    Layers, ArrowRightLeft,
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
        if (['non previst', 'bullonatura', 'bullonata', 'nessuna saldatura'].some(kw => t.includes(kw))) return 'negative';
        if (t === 'no' || t === 'no.') return 'negative';
        if (['sì', 'si', 'officina', 'terzi', 'previst'].some(kw => t.includes(kw))) return 'positive';
        if (t.includes('verificare') || t.includes('definire')) return 'pending';
        return 'positive';
    }
    if (category === 'zincatura') {
        // Check external FIRST (priority over negative — "esterno" contains "no")
        if (['esterna', 'terzi', 'subfornitore', 'terzista'].some(kw => t.includes(kw))) return 'external';
        if (['nessun trattamento', 'non previst'].some(kw => t.includes(kw))) return 'negative';
        if (t === 'no' || t === 'no.') return 'negative';
        if (['a caldo', 'a freddo', 'verniciatura', 'industriale'].some(kw => t.includes(kw))) return 'positive';
        if (t.includes('definire') || t.includes('verificare')) return 'pending';
        return 'positive';
    }
    if (category === 'montaggio') {
        // Check positive/external FIRST to avoid "no" in "interno"/"esterno"
        if (['sì', 'si', 'inclusa', 'cantiere', 'installazione'].some(kw => t.includes(kw))) return 'positive';
        if (['terzi', 'affidato'].some(kw => t.includes(kw))) return 'external';
        if (['non previsto', 'non prevista', 'solo officina', 'solo assemblaggio'].some(kw => t.includes(kw))) return 'negative';
        if (t === 'no' || t === 'no.') return 'negative';
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

/* ───────── EVIDENZE (Perché questa proposta) ───────── */
function buildEvidenze(data) {
    const forti = [];
    const daConfermare = [];
    const est = data?.estrazione_tecnica;

    // Structural elements
    const elemConf = (est?.elementi_strutturali || []).filter(e => e.stato === 'confermato' || e.stato === 'dedotto');
    if (elemConf.length > 0) {
        forti.push({ testo: `Rilevati ${elemConf.length} elementi/profili in acciaio`, tipo: elemConf.some(e => e.stato === 'confermato') ? 'confermato' : 'dedotto' });
    }

    // Lavorazioni
    const lavs = est?.lavorazioni_rilevate || [];
    if (lavs.length > 0) {
        forti.push({ testo: `${lavs.length} lavorazion${lavs.length > 1 ? 'i' : 'e'} compatibili con carpenteria strutturale`, tipo: 'dedotto' });
    }

    // Welding
    if (est?.saldature?.presenti) {
        const s = est.saldature.stato;
        if (s === 'confermato' || s === 'dedotto') {
            forti.push({ testo: 'Saldatura prevista o menzionata nel preventivo', tipo: s });
        } else {
            daConfermare.push({ testo: 'Saldatura ipotizzata ma non confermata', impatto: 'Determina WPS, WPQR e qualifiche necessarie' });
        }
    }

    // Surface treatment
    const tratt = est?.trattamenti_superficiali;
    if (tratt?.tipo && tratt.tipo !== 'nessuno') {
        const s = tratt.stato;
        if (s === 'confermato' || s === 'dedotto') {
            forti.push({ testo: `Trattamento superficiale: ${tratt.tipo}`, tipo: s });
        } else {
            daConfermare.push({ testo: `Trattamento superficiale (${tratt.tipo}) da confermare`, impatto: 'Impatta documentazione e subforniture' });
        }
    }

    // Profile motivation — if deduced by analogy
    const prof = data?.profilo_tecnico;
    if (prof?.motivazione) {
        const m = prof.motivazione.toLowerCase();
        if (m.includes('dedott') || m.includes('analog') || m.includes('ipotizz')) {
            daConfermare.push({ testo: 'Classe/profilo proposto per analogia', impatto: prof.motivazione });
        }
    }

    // Uncertain elements
    const incerti = (est?.elementi_strutturali || []).filter(e => e.stato === 'incerto' || e.stato === 'mancante');
    if (incerti.length > 0) {
        daConfermare.push({ testo: `${incerti.length} element${incerti.length > 1 ? 'i' : 'o'} con dati incompleti`, impatto: 'Potrebbe influenzare la classe di esecuzione' });
    }

    return { forti: forti.slice(0, 5), daConfermare: daConfermare.slice(0, 4) };
}

/* ───────── PUNTI INCERTI ───────── */
function buildPuntiIncerti(data, nRisposte, nDomande) {
    const punti = [];

    // From ambiguities
    (data?.estrazione_tecnica?.ambiguita_rilevate || []).forEach(a => {
        punti.push({
            testo: a.punto,
            impatto: a.possibili_interpretazioni?.join(' / '),
            livello: a.impatto === 'alto' ? 'alto' : 'medio',
        });
    });

    // Unanswered questions
    if (nDomande > 0 && nRisposte < nDomande) {
        punti.push({
            testo: `${nDomande - nRisposte} conferme ancora da dare`,
            impatto: 'Le risposte possono cambiare documenti e controlli richiesti',
            livello: 'medio',
        });
    }

    // Uncertain/missing elements
    (data?.estrazione_tecnica?.elementi_strutturali || [])
        .filter(e => e.stato === 'incerto')
        .slice(0, 2)
        .forEach(e => {
            punti.push({
                testo: `${e.descrizione}: dati incompleti`,
                impatto: 'Potrebbe richiedere integrazione dal disegno',
                livello: 'basso',
            });
        });

    return punti.slice(0, 6);
}

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
    const [risposteCtx, setRisposteCtx] = useState({});
    const [savingCtx, setSavingCtx] = useState(false);
    const [segmentazione, setSegmentazione] = useState(null);
    const [segRunning, setSegRunning] = useState(false);
    const [segReviews, setSegReviews] = useState({});
    const [segSaving, setSegSaving] = useState(false);
    const [phase2Elig, setPhase2Elig] = useState(null);
    const [phase2Loading, setPhase2Loading] = useState(false);
    const [phase2Commessa, setPhase2Commessa] = useState(null);

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
        // Init contextual answers
        if (data?.domande_contestuali) {
            const ctxSaved = {};
            data.domande_contestuali.forEach(q => {
                if (q.risposta) ctxSaved[q.id] = q.risposta;
            });
            setRisposteCtx(ctxSaved);
        }
        // Init segmentation
        if (data?.segmentazione_proposta) {
            setSegmentazione(data.segmentazione_proposta);
            const reviews = {};
            (data.segmentazione_proposta.line_classification || []).forEach(lc => {
                if (lc.review?.decision) {
                    reviews[lc.line_id] = lc.review.final_normativa || lc.proposed_normativa;
                }
            });
            setSegReviews(reviews);
        }
        // Check Phase 2 eligibility
        if (data?.confermata) {
            apiRequest(`/istruttoria/phase2/eligibility/${preventivoId}`)
                .then(setPhase2Elig).catch(() => {});
            apiRequest(`/istruttoria/phase2/commessa/${preventivoId}`)
                .then(r => setPhase2Commessa(r.commessa)).catch(() => {});
        }
    }, [data?.risposte_utente, data?.domande_contestuali, data?.segmentazione_proposta, data?.confermata, preventivoId]);

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

    const handleCtxRispostaChange = (id, value) => {
        setRisposteCtx(prev => ({ ...prev, [id]: value }));
    };

    const handleCtxQuickAnswer = (id, option) => {
        const current = risposteCtx[id] || '';
        handleCtxRispostaChange(id, current === option ? '' : option);
    };

    const handleSalvaCtx = async () => {
        if (!data?.istruttoria_id) return;
        const payload = Object.entries(risposteCtx)
            .filter(([, v]) => v.trim())
            .map(([id, risposta]) => ({ id, risposta }));
        if (!payload.length) { toast.warning('Inserisci almeno una risposta'); return; }
        setSavingCtx(true);
        try {
            await apiRequest(`/istruttoria/${data.istruttoria_id}/rispondi-contestuale`, {
                method: 'POST', body: { risposte: payload },
            });
            toast.success(`Risposte contestuali salvate (${payload.length})`);
            fetchIstruttoria();
        } catch (e) { toast.error(e.message); }
        finally { setSavingCtx(false); }
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

    const handleSegmenta = async () => {
        setSegRunning(true);
        try {
            toast.info('Segmentazione in corso...');
            const res = await apiRequest(`/istruttoria/segmenta/${preventivoId}`, { method: 'POST' });
            setSegmentazione(res.segmentazione);
            toast.success('Segmentazione completata');
            fetchIstruttoria();
        } catch (e) { toast.error(e.message); }
        finally { setSegRunning(false); }
    };

    const handleSegReview = (lineId, normativa) => {
        setSegReviews(prev => ({ ...prev, [lineId]: normativa }));
    };

    const handleSegSave = async (action) => {
        if (!data?.istruttoria_id) return;
        setSegSaving(true);
        try {
            const lineReviews = Object.entries(segReviews).map(([lineId, norm]) => ({
                line_id: lineId,
                final_normativa: norm,
                decision: 'corrected',
            }));
            // Also add accepted lines (not explicitly reviewed = accept AI proposal)
            const seg = segmentazione || data?.segmentazione_proposta;
            if (seg?.line_classification) {
                for (const lc of seg.line_classification) {
                    if (!segReviews[lc.line_id]) {
                        lineReviews.push({
                            line_id: lc.line_id,
                            final_normativa: lc.proposed_normativa,
                            decision: 'accepted',
                        });
                    }
                }
            }
            const res = await apiRequest(`/istruttoria/segmenta/${preventivoId}/review`, {
                method: 'POST',
                body: { line_reviews: lineReviews, action },
            });
            if (action === 'confirm') {
                toast.success('Segmentazione confermata');
            } else {
                toast.success('Bozza segmentazione salvata');
            }
            fetchIstruttoria();
        } catch (e) { toast.error(e.message); }
        finally { setSegSaving(false); }
    };

    const handleGeneraCommessa = async () => {
        setPhase2Loading(true);
        try {
            const res = await apiRequest(`/istruttoria/phase2/genera/${preventivoId}`, { method: 'POST' });
            setPhase2Commessa(res.commessa);
            if (res.warnings?.length) {
                res.warnings.forEach(w => toast.warning(w));
            }
            toast.success('Commessa pre-istruita generata');
            fetchIstruttoria();
        } catch (e) {
            const detail = e.message;
            toast.error(typeof detail === 'string' ? detail : 'Generazione non consentita');
        }
        finally { setPhase2Loading(false); }
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

                {/* ════════════════ PERCHÉ QUESTA PROPOSTA ════════════════ */}
                {(() => {
                    const ev = buildEvidenze(data);
                    const hasEvidenze = ev.forti.length > 0 || ev.daConfermare.length > 0;
                    if (!hasEvidenze) return null;
                    return (
                        <Card className="border-slate-200" data-testid="card-perche-proposta">
                            <CardContent className="p-4 space-y-3">
                                <p className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                    <Lightbulb className="h-3.5 w-3.5 text-blue-600" />
                                    Perché propone {normativa.replace('_', ' ')}
                                </p>
                                {ev.forti.length > 0 && (
                                    <div className="space-y-1">
                                        <p className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Evidenze rilevate</p>
                                        {ev.forti.map((e, i) => (
                                            <div key={i} className="flex items-center gap-2 text-[11px] text-slate-700">
                                                <CheckCircle2 className={`h-3 w-3 shrink-0 ${e.tipo === 'confermato' ? 'text-emerald-500' : 'text-blue-500'}`} />
                                                <span>{e.testo}</span>
                                                <StatoBadge stato={e.tipo} />
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {ev.daConfermare.length > 0 && (
                                    <div className="space-y-1">
                                        <p className="text-[9px] font-bold text-amber-600 uppercase tracking-wider">Da confermare</p>
                                        {ev.daConfermare.map((e, i) => (
                                            <div key={i} className="text-[11px]">
                                                <div className="flex items-center gap-2 text-slate-600">
                                                    <HelpCircle className="h-3 w-3 shrink-0 text-amber-500" />
                                                    <span>{e.testo}</span>
                                                </div>
                                                {e.impatto && (
                                                    <p className="text-[9px] text-slate-400 ml-5">{e.impatto}</p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    );
                })()}

                {/* ════════════════ PUNTI INCERTI ════════════════ */}
                {(() => {
                    const punti = buildPuntiIncerti(data, nRisposte, nDomande);
                    if (punti.length === 0) return null;
                    return (
                        <Card className="border-amber-200 bg-amber-50/20" data-testid="card-punti-incerti">
                            <CardContent className="p-4 space-y-2">
                                <p className="text-xs font-bold text-amber-800 flex items-center gap-1.5">
                                    <CircleAlert className="h-3.5 w-3.5" />
                                    Punti da chiarire
                                </p>
                                {punti.map((p, i) => (
                                    <div key={i} className="flex items-start gap-2">
                                        <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                                            p.livello === 'alto' ? 'bg-red-500' : p.livello === 'medio' ? 'bg-amber-500' : 'bg-slate-400'}`} />
                                        <div>
                                            <p className="text-[11px] text-slate-700">{p.testo}</p>
                                            {p.impatto && (
                                                <p className="text-[9px] text-slate-400">{p.impatto}</p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    );
                })()}

                {/* ════════════════ CORREZIONI MOTORE REGOLE ════════════════ */}
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
                                Conferme che mancano
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
                                    <div key={i} className="space-y-2">
                                    <div
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

                                    {/* ── Contextual child questions for this parent ── */}
                                    {(data?.domande_contestuali || [])
                                        .filter(cq => cq.active && cq.parent_domanda_idx === i)
                                        .map(cq => {
                                            const ctxValue = risposteCtx[cq.id] || '';
                                            const ctxSaved = !!cq.risposta;
                                            return (
                                                <div key={cq.id}
                                                    className={`ml-8 rounded-lg border-l-4 border-l-blue-400 border border-blue-200 bg-blue-50/20 transition-all ${ctxSaved ? 'border-l-emerald-400' : ''}`}
                                                    data-testid={`ctx-domanda-${cq.id}`}>
                                                    <div className="p-3 space-y-2">
                                                        <p className="text-[9px] text-blue-500 font-medium flex items-center gap-1">
                                                            <Zap className="h-2.5 w-2.5" />
                                                            {cq.trigger_reason}
                                                        </p>
                                                        <div className="flex items-start gap-2">
                                                            <div className={`w-5 h-5 rounded flex items-center justify-center shrink-0 text-[9px] font-bold text-white ${ctxSaved ? 'bg-emerald-500' : 'bg-blue-400'}`}>
                                                                {ctxSaved ? <CheckCircle2 className="h-2.5 w-2.5" /> : '?'}
                                                            </div>
                                                            <div className="flex-1">
                                                                <p className="text-xs font-medium text-slate-700">{cq.domanda}</p>
                                                                <Badge className="text-[8px] px-1 py-0 bg-blue-100 text-blue-600 mt-0.5">impatto {cq.impatto}</Badge>
                                                            </div>
                                                        </div>

                                                        {cq.opzioni?.length > 0 && (
                                                            <div className="flex flex-wrap gap-1.5 ml-7">
                                                                {cq.opzioni.map(opt => (
                                                                    <button key={opt} type="button"
                                                                        onClick={() => handleCtxQuickAnswer(cq.id, opt)}
                                                                        className={`text-[10px] px-2.5 py-0.5 rounded-full border transition-all ${
                                                                            ctxValue === opt
                                                                                ? 'bg-blue-600 text-white border-blue-600'
                                                                                : 'bg-white text-slate-500 border-slate-300 hover:border-blue-400'}`}
                                                                        data-testid={`ctx-btn-${cq.id}-${opt.substring(0, 8).replace(/\s/g, '_')}`}>
                                                                        {opt}
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        )}

                                                        <div className="ml-7">
                                                            <Textarea
                                                                placeholder={cq.opzioni?.length > 0 ? 'Oppure scrivi...' : 'Scrivi la tua risposta...'}
                                                                value={ctxValue}
                                                                onChange={(e) => handleCtxRispostaChange(cq.id, e.target.value)}
                                                                className="text-xs min-h-[36px] border-blue-200 focus:border-blue-400 bg-white"
                                                                rows={1}
                                                                data-testid={`ctx-input-${cq.id}`} />
                                                            {ctxSaved && (
                                                                <p className="text-[8px] text-emerald-600 mt-0.5 flex items-center gap-1">
                                                                    <CheckCircle2 className="h-2 w-2" />
                                                                    Risposto da {cq.risposto_da_nome}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    }
                                    </div>
                                );
                            })}

                            <div className="flex items-center justify-between pt-2">
                                <p className="text-[10px] text-slate-400">
                                    {tutteRisposte
                                        ? 'Tutte le conferme sono state date. Puoi salvare e procedere alla conferma.'
                                        : 'Puoi salvare anche risposte parziali e completare dopo.'}
                                </p>
                                <div className="flex gap-2">
                                    {(data?.domande_contestuali || []).some(cq => cq.active) && (
                                        <Button onClick={handleSalvaCtx} variant="outline" size="sm"
                                            disabled={savingCtx || !Object.values(risposteCtx).some(v => v.trim())}
                                            className="border-blue-300 text-blue-700 hover:bg-blue-50" data-testid="btn-salva-ctx">
                                            {savingCtx ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
                                            Salva Contestuali
                                        </Button>
                                    )}
                                    <Button onClick={handleSalvaRisposte}
                                        disabled={savingRisposte || !Object.values(risposte).some(v => v.trim())}
                                        className="bg-blue-700 hover:bg-blue-800 text-white" data-testid="btn-salva-risposte">
                                        {savingRisposte ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
                                        {savingRisposte ? 'Salvataggio...' : 'Salva Risposte'}
                                    </Button>
                                </div>
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
                                        <Ban className="h-3 w-3" /> Non necessari per questa commessa ({appData.items_non_applicabili.length})
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
                                        <AlertTriangle className="h-3 w-3" /> Documenti aggiuntivi richiesti ({appData.items_condizionali.length})
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

                {/* ════════════════ TECHNICAL DETAILS (collapsible) ════════════════ */}
                <Card className="border-slate-200">
                    <button onClick={() => setShowTechDetails(!showTechDetails)}
                        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-50 transition-colors rounded-lg"
                        data-testid="toggle-tech-details">
                        <span className="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-2">
                            <FileText className="h-3.5 w-3.5" />
                            Cosa ha rilevato dal preventivo
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
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Documenti da raccogliere ({documenti_richiesti?.length || 0})</p>
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
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Fasi di lavorazione previste</p>
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
                            <p className="text-xs font-bold text-indigo-800 mb-1">Note dal motore regole</p>
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
                                <Brain className="h-3.5 w-3.5 text-blue-500" /> Nota tecnica
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

                {/* ════════════════ SE CONFERMI LA COMMESSA ════════════════ */}
                {!confermata && !hasBloccoBloccante && (
                    <Card className="border-slate-200 bg-slate-50/30" data-testid="card-se-confermi">
                        <CardContent className="p-4 space-y-3">
                            <p className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                <FileText className="h-3.5 w-3.5 text-slate-500" />
                                Se confermi la commessa
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div>
                                    <p className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                                        <CheckCircle2 className="h-3 w-3" /> Verra preparato
                                    </p>
                                    <ul className="space-y-1 text-[11px] text-slate-600">
                                        <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">-</span> Riesame tecnico precompilato</li>
                                        <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">-</span> Lavorazioni e controlli pertinenti</li>
                                        <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">-</span> Documenti da raccogliere</li>
                                        <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">-</span> Requisiti materiali e tracciabilita</li>
                                    </ul>
                                </div>
                                <div>
                                    <p className="text-[10px] font-bold text-amber-700 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                                        <HelpCircle className="h-3 w-3" /> Restera da completare
                                    </p>
                                    <ul className="space-y-1 text-[11px] text-slate-600">
                                        {!tutteRisposte && nDomande > 0 && (
                                            <li className="flex items-start gap-1.5"><span className="text-amber-500 mt-0.5">-</span> {nDomande - nRisposte} conferme ancora mancanti</li>
                                        )}
                                        <li className="flex items-start gap-1.5"><span className="text-amber-500 mt-0.5">-</span> Evidenze documentali</li>
                                        {(riepilogo.saldatura && !riepilogo.saldatura.includes('Non previst')) && (
                                            <li className="flex items-start gap-1.5"><span className="text-amber-500 mt-0.5">-</span> Dati saldatura, se prevista</li>
                                        )}
                                        {(riepilogo.zincatura && riepilogo.zincatura.includes('terzista')) && (
                                            <li className="flex items-start gap-1.5"><span className="text-amber-500 mt-0.5">-</span> Documentazione terzista zincatura</li>
                                        )}
                                        {(riepilogo.montaggio && !riepilogo.montaggio.includes('Non previst')) && (
                                            <li className="flex items-start gap-1.5"><span className="text-amber-500 mt-0.5">-</span> Dati posa in opera, se prevista</li>
                                        )}
                                    </ul>
                                </div>
                                <div>
                                    <p className="text-[10px] font-bold text-red-700 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                                        <ShieldAlert className="h-3 w-3" /> Non ancora emettibile
                                    </p>
                                    <ul className="space-y-1 text-[11px] text-slate-600">
                                        <li className="flex items-start gap-1.5"><span className="text-red-400 mt-0.5">-</span> DoP e documenti finali restano bloccati</li>
                                        <li className="flex items-start gap-1.5"><span className="text-red-400 mt-0.5">-</span> finche non ci sono le prove richieste</li>
                                    </ul>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* ════════════════ SEGMENTAZIONE NORMATIVA ════════════════ */}
                {!confermata && (normativa === 'MISTA' || hasBloccoBloccante || segmentazione?.enabled) && (() => {
                    const seg = segmentazione || data?.segmentazione_proposta;
                    const segConfirmed = data?.official_segmentation?.confirmed;
                    const lines = seg?.line_classification || [];
                    const summary = seg?.summary || {};
                    const NORM_OPTIONS = ['EN_1090', 'EN_13241', 'GENERICA', 'INCERTA'];
                    const NORM_COLORS = { EN_1090: 'bg-blue-100 text-blue-700', EN_13241: 'bg-violet-100 text-violet-700', GENERICA: 'bg-slate-100 text-slate-600', INCERTA: 'bg-amber-100 text-amber-700' };
                    const hasIncerte = lines.some(lc => (segReviews[lc.line_id] || lc.proposed_normativa) === 'INCERTA');

                    return (
                        <Card className={`border-2 ${segConfirmed ? 'border-emerald-300 bg-emerald-50/20' : 'border-purple-200 bg-purple-50/20'}`} data-testid="card-segmentazione">
                            <CardContent className="p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Layers className="h-4 w-4 text-purple-600" />
                                        <span className="text-xs font-bold text-slate-700">Suggerimento di segmentazione</span>
                                        {segConfirmed && <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">Confermata</Badge>}
                                        {seg?.status === 'in_review' && <Badge className="bg-amber-100 text-amber-700 text-[9px]">In revisione</Badge>}
                                    </div>
                                    {!seg && (
                                        <Button size="sm" onClick={handleSegmenta} disabled={segRunning}
                                            className="bg-purple-600 hover:bg-purple-700 text-white text-xs"
                                            data-testid="btn-avvia-segmentazione">
                                            {segRunning ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <ArrowRightLeft className="h-3 w-3 mr-1" />}
                                            Analizza per riga
                                        </Button>
                                    )}
                                </div>

                                {!seg && (
                                    <p className="text-[11px] text-slate-500">
                                        Il preventivo contiene righe che sembrano appartenere a percorsi normativi diversi.
                                        Avvia l'analisi per proporre una divisione riga per riga.
                                    </p>
                                )}

                                {seg && (
                                    <>
                                        {/* Summary badges */}
                                        <div className="flex flex-wrap gap-2">
                                            {summary.en_1090 > 0 && <Badge className="bg-blue-100 text-blue-700 text-[10px]">EN 1090: {summary.en_1090} righe</Badge>}
                                            {summary.en_13241 > 0 && <Badge className="bg-violet-100 text-violet-700 text-[10px]">EN 13241: {summary.en_13241} righe</Badge>}
                                            {summary.generiche > 0 && <Badge className="bg-slate-100 text-slate-600 text-[10px]">Generiche: {summary.generiche} righe</Badge>}
                                            {summary.incerte > 0 && <Badge className="bg-amber-100 text-amber-700 text-[10px]">Incerte: {summary.incerte} righe</Badge>}
                                        </div>

                                        {/* Per-line classification table */}
                                        <div className="space-y-1.5">
                                            {lines.map((lc) => {
                                                const reviewed = segReviews[lc.line_id];
                                                const displayNorm = reviewed || lc.proposed_normativa;
                                                const isChanged = reviewed && reviewed !== lc.proposed_normativa;

                                                return (
                                                    <div key={lc.line_id}
                                                        className={`rounded border p-2 transition-all ${
                                                            isChanged ? 'border-indigo-200 bg-indigo-50/30' :
                                                            displayNorm === 'INCERTA' ? 'border-amber-200 bg-amber-50/20' :
                                                            'border-slate-100 bg-white'
                                                        }`}
                                                        data-testid={`seg-line-${lc.line_id}`}>
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div className="flex-1 min-w-0">
                                                                <p className="text-[11px] text-slate-700 leading-snug truncate" title={lc.descrizione}>
                                                                    {lc.descrizione}
                                                                </p>
                                                                <p className="text-[9px] text-slate-400 mt-0.5">
                                                                    {lc.reasoning}
                                                                    {isChanged && <span className="text-indigo-500 ml-1">(corretto manualmente)</span>}
                                                                </p>
                                                            </div>
                                                            <div className="flex items-center gap-1 shrink-0">
                                                                {!segConfirmed ? (
                                                                    <select
                                                                        value={displayNorm}
                                                                        onChange={(e) => handleSegReview(lc.line_id, e.target.value)}
                                                                        className={`text-[10px] font-medium rounded px-1.5 py-0.5 border-0 ${NORM_COLORS[displayNorm] || 'bg-slate-100'}`}
                                                                        data-testid={`seg-select-${lc.line_id}`}>
                                                                        {NORM_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
                                                                    </select>
                                                                ) : (
                                                                    <Badge className={`text-[9px] ${NORM_COLORS[displayNorm] || 'bg-slate-100'}`}>
                                                                        {displayNorm}
                                                                    </Badge>
                                                                )}
                                                                <span className="text-[9px] text-slate-300">{Math.round(lc.confidence * 100)}%</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        {/* CTA */}
                                        {!segConfirmed && (
                                            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                                                {hasIncerte && (
                                                    <p className="text-[10px] text-amber-600 flex items-center gap-1">
                                                        <AlertTriangle className="h-3 w-3" />
                                                        Classifica le righe incerte prima di confermare
                                                    </p>
                                                )}
                                                <div className="flex gap-2 ml-auto">
                                                    <Button size="sm" variant="outline"
                                                        onClick={() => handleSegSave('save_draft')}
                                                        disabled={segSaving}
                                                        data-testid="btn-seg-bozza">
                                                        <Save className="h-3 w-3 mr-1" /> Salva bozza
                                                    </Button>
                                                    <Button size="sm"
                                                        onClick={() => handleSegSave('confirm')}
                                                        disabled={segSaving || hasIncerte}
                                                        className="bg-purple-600 hover:bg-purple-700 text-white"
                                                        data-testid="btn-seg-conferma">
                                                        {segSaving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <ShieldCheck className="h-3 w-3 mr-1" />}
                                                        Conferma segmentazione
                                                    </Button>
                                                </div>
                                            </div>
                                        )}
                                    </>
                                )}
                            </CardContent>
                        </Card>
                    );
                })()}

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

                {/* ════════════════ PHASE 2 — COMMESSA PRE-ISTRUITA ════════════════ */}
                {confermata && (
                    <Card className={`border-2 ${
                        phase2Commessa ? 'border-indigo-300 bg-indigo-50/30' :
                        phase2Elig?.allowed ? 'border-emerald-200 bg-emerald-50/20' :
                        'border-amber-200 bg-amber-50/20'
                    }`} data-testid="card-phase2">
                        <CardContent className="p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <FileText className="h-4 w-4 text-indigo-600" />
                                    <span className="text-xs font-bold text-slate-700">Fase 2 — Commessa Pre-Istruita</span>
                                    {phase2Commessa && (
                                        <Badge className="bg-indigo-100 text-indigo-700 text-[9px]">{phase2Commessa.status}</Badge>
                                    )}
                                </div>
                                {!phase2Commessa && phase2Elig?.allowed && (
                                    <Button size="sm" onClick={handleGeneraCommessa} disabled={phase2Loading}
                                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
                                        data-testid="btn-genera-commessa">
                                        {phase2Loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Zap className="h-3 w-3 mr-1" />}
                                        Genera Commessa
                                    </Button>
                                )}
                            </div>

                            {/* Motivi di blocco */}
                            {!phase2Commessa && phase2Elig && !phase2Elig.allowed && (
                                <div className="space-y-1.5">
                                    <p className="text-[10px] font-bold text-amber-700">Perche non puoi generare la commessa pre-istruita:</p>
                                    {phase2Elig.reasons.map((r, i) => (
                                        <p key={i} className="text-[10px] text-amber-600 flex items-start gap-1.5">
                                            <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" /> {r}
                                        </p>
                                    ))}
                                </div>
                            )}

                            {/* Warnings */}
                            {phase2Elig?.warnings?.length > 0 && !phase2Commessa && (
                                <div className="space-y-1">
                                    {phase2Elig.warnings.map((w, i) => (
                                        <p key={i} className="text-[9px] text-slate-500 flex items-start gap-1.5">
                                            <HelpCircle className="h-2.5 w-2.5 mt-0.5 shrink-0" /> {w}
                                        </p>
                                    ))}
                                </div>
                            )}

                            {/* Commessa generata */}
                            {phase2Commessa && (
                                <div className="space-y-3">
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                        <div className="rounded-lg bg-white border border-slate-100 p-2.5 text-center">
                                            <p className="text-2xl font-black text-indigo-700">{phase2Commessa.etichette?.precompilato || 0}</p>
                                            <p className="text-[9px] text-slate-500">Precompilati</p>
                                        </div>
                                        <div className="rounded-lg bg-white border border-slate-100 p-2.5 text-center">
                                            <p className="text-2xl font-black text-amber-600">{phase2Commessa.etichette?.da_completare || 0}</p>
                                            <p className="text-[9px] text-slate-500">Da completare</p>
                                        </div>
                                        <div className="rounded-lg bg-white border border-slate-100 p-2.5 text-center">
                                            <p className="text-2xl font-black text-red-600">{phase2Commessa.etichette?.non_emettibile?.length || 0}</p>
                                            <p className="text-[9px] text-slate-500">Non emettibili</p>
                                        </div>
                                        <div className="rounded-lg bg-white border border-slate-100 p-2.5 text-center">
                                            <p className="text-2xl font-black text-slate-800">{phase2Commessa.normativa}</p>
                                            <p className="text-[9px] text-slate-500">Normativa</p>
                                        </div>
                                    </div>

                                    {/* Rami attivi */}
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(phase2Commessa.rami_attivi || {}).map(([k, v]) => (
                                            <Badge key={k} className={`text-[9px] ${
                                                v.attivo ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-400'
                                            }`}>
                                                {k}: {v.attivo ? 'attivo' : 'n/a'}
                                            </Badge>
                                        ))}
                                    </div>

                                    {/* Detail lists */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        {phase2Commessa.voci_lavoro?.length > 0 && (
                                            <div>
                                                <p className="text-[10px] font-bold text-emerald-700 mb-1">Voci lavoro precompilate</p>
                                                {phase2Commessa.voci_lavoro.map((v, i) => (
                                                    <p key={i} className="text-[10px] text-slate-600 flex items-start gap-1">
                                                        <span className="text-emerald-400 mt-0.5">-</span> {v.descrizione?.substring(0, 60)}
                                                    </p>
                                                ))}
                                            </div>
                                        )}
                                        {phase2Commessa.controlli?.length > 0 && (
                                            <div>
                                                <p className="text-[10px] font-bold text-blue-700 mb-1">Controlli proposti</p>
                                                {phase2Commessa.controlli.map((c, i) => (
                                                    <p key={i} className="text-[10px] text-slate-600 flex items-start gap-1">
                                                        <span className="text-blue-400 mt-0.5">-</span> {c.descrizione?.substring(0, 60)}
                                                    </p>
                                                ))}
                                            </div>
                                        )}
                                        {phase2Commessa.documenti?.length > 0 && (
                                            <div>
                                                <p className="text-[10px] font-bold text-violet-700 mb-1">Documenti da raccogliere</p>
                                                {phase2Commessa.documenti.map((d, i) => (
                                                    <p key={i} className="text-[10px] text-slate-600 flex items-start gap-1">
                                                        <span className="text-violet-400 mt-0.5">-</span> {d.documento?.substring(0, 60)}
                                                    </p>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    {phase2Commessa.da_completare?.length > 0 && (
                                        <div>
                                            <p className="text-[10px] font-bold text-amber-700 mb-1">Da completare manualmente</p>
                                            {phase2Commessa.da_completare.map((d, i) => (
                                                <p key={i} className="text-[10px] text-amber-600 flex items-start gap-1">
                                                    <span className="text-amber-400 mt-0.5">-</span> {d.descrizione?.substring(0, 80)}
                                                </p>
                                            ))}
                                        </div>
                                    )}

                                    <p className="text-[9px] text-red-500 flex items-center gap-1 pt-1 border-t border-slate-100">
                                        <ShieldAlert className="h-3 w-3" />
                                        DOP, Etichetta CE e Dichiarazione prestazione non emettibili senza le evidenze richieste
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}
            </div>
        </DashboardLayout>
    );
}
