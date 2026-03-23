/**
 * OnboardingChecklist — First-time user guidance on Dashboard.
 * Auto-detects completed steps and shows progress.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
    Building2, Users, FileText, Hammer,
    CheckCircle2, Circle, X, ArrowRight, Rocket,
} from 'lucide-react';

const STEP_CONFIG = [
    {
        key: 'company_configured',
        title: 'Configura i dati aziendali',
        description: 'Inserisci ragione sociale, P.IVA e dati fiscali per fatture e documenti.',
        afterHint: 'Serviranno per generare preventivi, fatture e certificazioni.',
        icon: Building2,
        color: 'text-violet-600',
        bg: 'bg-violet-50',
        path: '/impostazioni',
    },
    {
        key: 'first_client',
        title: 'Aggiungi il primo cliente',
        description: 'Crea l\'anagrafica del tuo primo committente.',
        afterHint: 'Potrai poi creare preventivi e commesse associate a questo cliente.',
        icon: Users,
        color: 'text-blue-600',
        bg: 'bg-blue-50',
        path: '/clients',
    },
    {
        key: 'first_preventivo',
        title: 'Crea il primo preventivo',
        description: 'Prepara un preventivo con voci, prezzi e condizioni.',
        afterHint: 'Una volta accettato, il preventivo diventa la base per la commessa.',
        icon: FileText,
        color: 'text-emerald-600',
        bg: 'bg-emerald-50',
        path: '/preventivi/new',
    },
    {
        key: 'first_commessa',
        title: 'Genera la prima commessa',
        description: 'Crea la commessa per tracciare lavorazione, materiali e certificazioni.',
        afterHint: 'Da qui gestisci tutto: produzione, qualita, sicurezza e documentazione.',
        icon: Hammer,
        color: 'text-amber-600',
        bg: 'bg-amber-50',
        path: '/planning',
    },
];

export default function OnboardingChecklist() {
    const navigate = useNavigate();
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [dismissing, setDismissing] = useState(false);

    useEffect(() => {
        apiRequest('/onboarding/status')
            .then(setStatus)
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const handleDismiss = async () => {
        setDismissing(true);
        try {
            await apiRequest('/onboarding/dismiss', { method: 'POST' });
            setStatus(prev => ({ ...prev, dismissed: true, show_onboarding: false }));
        } catch {
            // silent
        } finally {
            setDismissing(false);
        }
    };

    if (loading || !status || !status.show_onboarding) return null;

    const pct = Math.round((status.completed_count / status.total_steps) * 100);
    // Find first incomplete step
    const nextStep = STEP_CONFIG.find(s => !status.steps[s.key]);

    return (
        <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50/50 to-white overflow-hidden" data-testid="onboarding-checklist">
            <CardContent className="p-0">
                {/* Header */}
                <div className="flex items-center justify-between px-5 pt-4 pb-3">
                    <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-xl bg-[#0055FF] flex items-center justify-center">
                            <Rocket className="h-5 w-5 text-white" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-800" data-testid="onboarding-title">
                                Inizia con NormaFacile
                            </h3>
                            <p className="text-xs text-slate-500">
                                {status.completed_count} di {status.total_steps} passi completati
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleDismiss}
                        disabled={dismissing}
                        className="text-slate-400 hover:text-slate-600 transition-colors p-1"
                        title="Nascondi checklist"
                        data-testid="onboarding-dismiss"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Progress bar */}
                <div className="px-5 pb-3">
                    <div className="w-full bg-slate-200 rounded-full h-1.5">
                        <div
                            className="h-1.5 rounded-full bg-[#0055FF] transition-all duration-500"
                            style={{ width: `${pct}%` }}
                            data-testid="onboarding-progress"
                        />
                    </div>
                </div>

                {/* Steps */}
                <div className="px-5 pb-4 space-y-1.5">
                    {STEP_CONFIG.map((step) => {
                        const done = status.steps[step.key];
                        const isNext = nextStep?.key === step.key;
                        const StepIcon = step.icon;

                        return (
                            <div
                                key={step.key}
                                className={`flex items-center gap-3 p-2.5 rounded-lg transition-all ${
                                    done
                                        ? 'bg-emerald-50/60'
                                        : isNext
                                            ? 'bg-white border border-blue-200 shadow-sm'
                                            : 'bg-slate-50/50'
                                }`}
                                data-testid={`onboarding-step-${step.key}`}
                            >
                                {/* Status icon */}
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                                    done ? 'bg-emerald-100' : step.bg
                                }`}>
                                    {done ? (
                                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                    ) : (
                                        <StepIcon className={`h-4 w-4 ${isNext ? step.color : 'text-slate-400'}`} />
                                    )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    <p className={`text-xs font-semibold ${
                                        done ? 'text-emerald-700 line-through' : 'text-slate-700'
                                    }`}>
                                        {step.title}
                                    </p>
                                    {isNext && (
                                        <p className="text-[11px] text-slate-500 mt-0.5">{step.description}</p>
                                    )}
                                </div>

                                {/* Action */}
                                {!done && isNext && (
                                    <Button
                                        size="sm"
                                        className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs h-7 shrink-0"
                                        onClick={() => navigate(step.path)}
                                        data-testid={`onboarding-cta-${step.key}`}
                                    >
                                        Vai <ArrowRight className="h-3 w-3 ml-1" />
                                    </Button>
                                )}
                                {done && (
                                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Next step hint */}
                {nextStep && (
                    <div className="bg-slate-50 border-t border-slate-100 px-5 py-2.5">
                        <p className="text-[11px] text-slate-400 italic" data-testid="onboarding-hint">
                            {nextStep.afterHint}
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
