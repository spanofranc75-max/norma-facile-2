/**
 * CommessaComplianceBanner — Validazione preventiva documenti aziendali.
 * Mostra un avviso bloccante se documenti mancanti/scaduti per la durata della commessa.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { AlertTriangle, CheckCircle, Shield, ArrowRight, Loader2 } from 'lucide-react';

const ESITO_ICON = {
    ok:           { icon: CheckCircle, color: 'text-emerald-600' },
    mancante:     { icon: AlertTriangle, color: 'text-red-600' },
    scaduto:      { icon: AlertTriangle, color: 'text-red-600' },
    insufficiente:{ icon: AlertTriangle, color: 'text-amber-600' },
    no_scadenza:  { icon: Shield, color: 'text-blue-500' },
    errore:       { icon: AlertTriangle, color: 'text-slate-500' },
};

export default function CommessaComplianceBanner({ commessaId }) {
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!commessaId) return;
        apiRequest(`/dashboard/commessa-compliance/${commessaId}`)
            .then(setData)
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [commessaId]);

    if (loading) return null;
    if (!data) return null;

    // If fully compliant, show small green badge
    if (data.conforme) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg" data-testid="compliance-banner-ok">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="text-xs font-medium text-emerald-700">Documenti aziendali conformi per questa commessa</span>
            </div>
        );
    }

    // Not compliant — show blocking warning
    return (
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 space-y-3" data-testid="compliance-banner-warning">
            <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div>
                    <h4 className="text-sm font-bold text-red-800">Conformita documentale insufficiente</h4>
                    <p className="text-xs text-red-600 mt-0.5">
                        I documenti aziendali non coprono la durata prevista dei lavori. Risolvere prima di procedere.
                    </p>
                </div>
            </div>

            <div className="space-y-1.5">
                {data.checks.map(c => {
                    const cfg = ESITO_ICON[c.esito] || ESITO_ICON.errore;
                    const Icon = cfg.icon;
                    return (
                        <div key={c.tipo} className="flex items-center gap-2 text-xs" data-testid={`check-${c.tipo}`}>
                            <Icon className={`w-3.5 h-3.5 ${cfg.color} shrink-0`} />
                            <span className="font-medium text-slate-700">{c.label}:</span>
                            <span className={c.esito === 'ok' ? 'text-emerald-600' : c.esito === 'no_scadenza' ? 'text-blue-600' : 'text-red-600'}>
                                {c.messaggio}
                            </span>
                        </div>
                    );
                })}
            </div>

            <div className="flex items-center gap-2 pt-1">
                <Button size="sm" className="h-7 text-xs bg-red-600 hover:bg-red-700"
                    onClick={() => navigate('/settings', { state: { tab: 'documenti' } })}
                    data-testid="btn-fix-compliance">
                    Correggi documenti <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
                <Badge className="bg-red-100 text-red-700 text-[10px]">
                    {data.bloccanti.length} {data.bloccanti.length === 1 ? 'problema' : 'problemi'}
                </Badge>
            </div>
        </div>
    );
}
