/**
 * IntegrityWidget — Small admin-only card showing DB health status.
 * Semaphore green/yellow/red + timestamp + counts + "Esegui check" CTA.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ShieldCheck, ShieldAlert, ShieldX, RefreshCw } from 'lucide-react';

const STATUS_MAP = {
    healthy: { icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Sano' },
    warning: { icon: ShieldAlert, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Attenzione' },
    critical: { icon: ShieldX, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'Critico' },
};

export default function IntegrityWidget() {
    const [report, setReport] = useState(null);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState(null);

    const fetchLatest = useCallback(() => {
        apiRequest('/admin/data-integrity/latest')
            .then(setReport)
            .catch(() => setReport(null));
    }, []);

    useEffect(() => { fetchLatest(); }, [fetchLatest]);

    const runCheck = async () => {
        setRunning(true);
        setError(null);
        try {
            const result = await apiRequest('/admin/data-integrity/run', { method: 'POST' });
            setReport(result);
        } catch (e) {
            setError('Errore durante il check');
        } finally {
            setRunning(false);
        }
    };

    const cfg = report ? (STATUS_MAP[report.status] || STATUS_MAP.healthy) : null;
    const Icon = cfg?.icon || ShieldCheck;

    const fmtDate = (iso) => {
        if (!iso) return '—';
        const d = new Date(iso);
        return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    };

    return (
        <Card className={`border ${report ? cfg.border : 'border-slate-200'}`} data-testid="integrity-widget">
            <CardContent className="py-3 px-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${report ? cfg.bg : 'bg-slate-100'}`}>
                            <Icon className={`h-4 w-4 ${report ? cfg.color : 'text-slate-400'}`} />
                        </div>
                        <div>
                            <p className="text-xs font-semibold text-slate-700">
                                Integrita DB {report && <span className={`ml-1 ${cfg.color}`}>{cfg.label}</span>}
                            </p>
                            {report ? (
                                <p className="text-[11px] text-slate-400">
                                    {report.ok_count}/{report.total_checks} OK
                                    {report.warning_count > 0 && <span className="text-amber-500 ml-1">{report.warning_count}W</span>}
                                    {report.critical_count > 0 && <span className="text-red-500 ml-1">{report.critical_count}C</span>}
                                    {' · '}{fmtDate(report.generated_at)}
                                </p>
                            ) : (
                                <p className="text-[11px] text-slate-400">Nessun check eseguito</p>
                            )}
                        </div>
                    </div>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={runCheck}
                        disabled={running}
                        className="h-7 text-xs text-slate-500 hover:text-[#0055FF]"
                        data-testid="integrity-run-btn"
                    >
                        <RefreshCw className={`h-3.5 w-3.5 mr-1 ${running ? 'animate-spin' : ''}`} />
                        {running ? 'Analisi...' : 'Esegui'}
                    </Button>
                </div>
                {error && <p className="text-[11px] text-red-500 mt-1">{error}</p>}
            </CardContent>
        </Card>
    );
}
