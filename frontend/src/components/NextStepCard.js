/**
 * NextStepCard — Shows the user what they should do next based on commessa state.
 * This is the answer to "cosa devo fare adesso?"
 */
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
    Ruler, FileText, CheckCircle2, Play, Receipt, Pause,
    AlertTriangle, ArrowRight,
} from 'lucide-react';

const NEXT_STEPS = {
    richiesta: {
        title: 'Completa il Rilievo',
        description: 'Vai a fare il sopralluogo e collega il rilievo alla commessa.',
        icon: Ruler,
        color: 'bg-violet-50 border-violet-200',
        iconColor: 'text-violet-600',
        actions: [
            { tipo: 'RILIEVO_COMPLETATO', label: 'Rilievo Completato' },
            { tipo: 'PREVENTIVO_ACCETTATO', label: 'Preventivo Accettato' },
        ],
    },
    bozza: {
        title: 'Prepara il Preventivo',
        description: 'Crea il preventivo e invialo al cliente per approvazione.',
        icon: FileText,
        color: 'bg-slate-50 border-slate-200',
        iconColor: 'text-slate-600',
        actions: [
            { tipo: 'RILIEVO_COMPLETATO', label: 'Rilievo Completato' },
            { tipo: 'PREVENTIVO_ACCETTATO', label: 'Preventivo Accettato' },
        ],
    },
    rilievo_completato: {
        title: 'Attendi la Firma del Cliente',
        description: 'Il rilievo e il preventivo sono pronti. Aspetta la conferma del cliente.',
        icon: FileText,
        color: 'bg-amber-50 border-amber-200',
        iconColor: 'text-amber-600',
        actions: [
            { tipo: 'FIRMA_CLIENTE', label: 'Firma Cliente' },
            { tipo: 'PREVENTIVO_ACCETTATO', label: 'Preventivo Accettato' },
        ],
    },
    firmato: {
        title: 'Avvia la Produzione',
        description: 'Il cliente ha firmato. Puoi avviare la produzione in officina.',
        icon: Play,
        color: 'bg-blue-50 border-blue-200',
        iconColor: 'text-blue-600',
        actions: [
            { tipo: 'AVVIO_PRODUZIONE', label: 'Avvia Produzione' },
        ],
    },
    in_produzione: {
        title: 'Produzione in Corso',
        description: 'Monitora l\'avanzamento e completa la checklist documentale.',
        icon: Play,
        color: 'bg-orange-50 border-orange-200',
        iconColor: 'text-orange-600',
        actions: [
            { tipo: 'FATTURA_EMESSA', label: 'Fattura Emessa' },
            { tipo: 'CHIUSURA_COMMESSA', label: 'Chiudi Commessa' },
        ],
    },
    fatturato: {
        title: 'Chiudi la Commessa',
        description: 'La fattura e stata emessa. Puoi completare la commessa.',
        icon: CheckCircle2,
        color: 'bg-emerald-50 border-emerald-200',
        iconColor: 'text-emerald-600',
        actions: [
            { tipo: 'CHIUSURA_COMMESSA', label: 'Chiudi Commessa' },
        ],
    },
    chiuso: {
        title: 'Commessa Completata',
        description: 'Tutti i passaggi sono stati completati. La commessa e archiviata.',
        icon: CheckCircle2,
        color: 'bg-slate-50 border-slate-200',
        iconColor: 'text-emerald-600',
        actions: [],
    },
    sospesa: {
        title: 'Commessa Sospesa',
        description: 'La commessa e in pausa. Riattivala quando sei pronto.',
        icon: Pause,
        color: 'bg-red-50 border-red-200',
        iconColor: 'text-red-600',
        actions: [
            { tipo: 'RIATTIVAZIONE', label: 'Riattiva' },
        ],
    },
};

export default function NextStepCard({ stato, onEmitEvent, emitting, obblighi }) {
    const step = NEXT_STEPS[stato] || NEXT_STEPS.bozza;
    const Icon = step.icon;

    // Show blocking obblighi warning
    const hardBlocks = obblighi?.filter(o => o.blocking_level === 'hard_block' && o.status !== 'completato') || [];

    return (
        <Card className={`border-2 ${step.color}`} data-testid="next-step-card">
            <CardContent className="p-4">
                <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${step.color.replace('border-', 'bg-').split(' ')[0]}`}>
                        <Icon className={`h-5 w-5 ${step.iconColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-bold text-slate-800" data-testid="next-step-title">
                            {step.title}
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">{step.description}</p>

                        {hardBlocks.length > 0 && (
                            <div className="flex items-center gap-1.5 mt-2 text-xs text-red-600 bg-red-50 p-1.5 rounded" data-testid="hard-blocks-warning">
                                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                <span>{hardBlocks.length} obblighi bloccanti da risolvere prima</span>
                            </div>
                        )}

                        {step.actions.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-3">
                                {step.actions.map(a => (
                                    <Button key={a.tipo} size="sm" disabled={emitting}
                                        className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs h-7"
                                        onClick={() => onEmitEvent(a)}
                                        data-testid={`next-action-${a.tipo}`}
                                    >
                                        {a.label} <ArrowRight className="h-3 w-3 ml-1" />
                                    </Button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
