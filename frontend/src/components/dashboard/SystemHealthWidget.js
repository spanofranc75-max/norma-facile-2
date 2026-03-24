/**
 * SystemHealthWidget — Shows DB health, data integrity and recent audit activity.
 * Loads from GET /api/dashboard/system-health
 */
import { useState, useEffect } from 'react';
import { apiRequest } from '../../lib/utils';
import { Activity, Database, ShieldCheck, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

export default function SystemHealthWidget() {
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);

    const load = async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/dashboard/system-health');
            setHealth(data);
        } catch {
            // silently fail
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    if (loading || !health) {
        return (
            <div className="bg-white border rounded-xl p-4 animate-pulse" data-testid="system-health-widget">
                <div className="h-4 bg-slate-200 rounded w-1/3 mb-3" />
                <div className="h-3 bg-slate-100 rounded w-2/3" />
            </div>
        );
    }

    const isOk = health.status === 'ok';
    const StatusIcon = isOk ? CheckCircle : AlertTriangle;
    const statusColor = isOk ? 'text-emerald-600' : 'text-amber-500';
    const statusBg = isOk ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200';

    return (
        <div className={`border rounded-xl p-4 ${statusBg}`} data-testid="system-health-widget">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <StatusIcon className={`h-4 w-4 ${statusColor}`} />
                    <h3 className="font-semibold text-sm text-slate-800">Stato Sistema</h3>
                </div>
                <button onClick={load} className="text-slate-400 hover:text-slate-600 transition-colors" data-testid="btn-refresh-health">
                    <RefreshCw className="h-3.5 w-3.5" />
                </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                <Stat icon={Database} label="Fatture" value={health.data_counts?.fatture || 0} />
                <Stat icon={Database} label="Preventivi" value={health.data_counts?.preventivi || 0} />
                <Stat icon={Database} label="Commesse" value={health.data_counts?.commesse || 0} />
                <Stat icon={Activity} label="Invii 7gg" value={health.outbound_activity?.last_7d || 0} />
            </div>

            {/* Company status */}
            <div className="flex items-center gap-2 text-xs text-slate-600 mb-1">
                <ShieldCheck className={`h-3 w-3 ${health.company_settings?.complete ? 'text-emerald-500' : 'text-red-500'}`} />
                <span>
                    Azienda: {health.company_settings?.complete
                        ? <span className="text-emerald-700 font-medium">{health.company_settings.business_name}</span>
                        : <span className="text-red-600 font-medium">Impostazioni incomplete</span>
                    }
                </span>
            </div>

            {/* Warnings */}
            {health.warnings?.length > 0 && (
                <div className="mt-2 space-y-1">
                    {health.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-amber-700 flex items-start gap-1">
                            <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                            {w}
                        </p>
                    ))}
                </div>
            )}
        </div>
    );
}

function Stat({ icon: Icon, label, value }) {
    return (
        <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-slate-500 mb-0.5">
                <Icon className="h-3 w-3" />
                <span className="text-[10px] uppercase tracking-wide">{label}</span>
            </div>
            <p className="text-lg font-bold text-slate-800">{value}</p>
        </div>
    );
}
