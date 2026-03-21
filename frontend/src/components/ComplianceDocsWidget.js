/**
 * ComplianceDocsWidget — Widget dashboard: stato documentazione aziendale,
 * alert 30 giorni, barra avanzamento per commessa, download fascicolo.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { toast } from 'sonner';
import {
    Shield, Download, AlertTriangle, CheckCircle, Clock,
    FileX, ArrowRight, Loader2, FolderDown,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_CFG = {
    scaduto:     { color: 'bg-red-500',    text: 'text-red-700',    bg: 'bg-red-50',    label: 'Scaduto', icon: AlertTriangle },
    critico:     { color: 'bg-red-400',    text: 'text-red-600',    bg: 'bg-red-50',    label: '<15gg',   icon: Clock },
    in_scadenza: { color: 'bg-amber-400',  text: 'text-amber-700',  bg: 'bg-amber-50',  label: '<30gg',   icon: Clock },
    mancante:    { color: 'bg-slate-300',  text: 'text-slate-600',  bg: 'bg-slate-50',  label: 'Mancante', icon: FileX },
    valido:      { color: 'bg-emerald-500',text: 'text-emerald-700',bg: 'bg-emerald-50',label: 'OK',      icon: CheckCircle },
    no_scadenza: { color: 'bg-blue-400',   text: 'text-blue-700',   bg: 'bg-blue-50',   label: 'No data', icon: Clock },
};

export default function ComplianceDocsWidget() {
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        apiRequest('/dashboard/compliance-docs')
            .then(setData)
            .catch(e => console.error('ComplianceDocs:', e))
            .finally(() => setLoading(false));
    }, []);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const res = await fetch(`${API}/api/dashboard/fascicolo-aziendale`, { credentials: 'include' });
            if (!res.ok) { toast.error('Errore download fascicolo'); return; }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Fascicolo_Aziendale_${new Date().toISOString().split('T')[0]}.zip`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Fascicolo scaricato');
        } catch (e) { toast.error(e.message); }
        finally { setDownloading(false); }
    };

    if (loading) return (
        <Card className="border-gray-200"><CardContent className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
        </CardContent></Card>
    );

    if (!data) return null;

    const { riepilogo: r, alert_30gg, commesse_compliance, documenti } = data;
    const hasAlerts = alert_30gg?.length > 0 || r.mancanti > 0;

    return (
        <Card className="border-gray-200" data-testid="widget-compliance-docs">
            <CardHeader className="bg-slate-50 border-b border-gray-200 py-3 px-5">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                        <Shield className="h-4 w-4 text-[#0055FF]" />
                        Conformita Documentale
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {hasAlerts && (
                            <Badge className="bg-red-100 text-red-700 border border-red-200 text-[10px] gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                {r.scaduti + r.critici + r.mancanti} problemi
                            </Badge>
                        )}
                        <Button variant="outline" size="sm" className="h-7 text-xs gap-1 border-[#0055FF] text-[#0055FF]"
                            onClick={handleDownload} disabled={downloading} data-testid="btn-fascicolo">
                            {downloading ? <Loader2 className="w-3 h-3 animate-spin" /> : <FolderDown className="w-3 h-3" />}
                            Fascicolo
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                {/* Document status pills */}
                <div className="px-4 py-3 border-b border-slate-100">
                    <div className="flex flex-wrap gap-1.5">
                        {documenti?.map(d => {
                            const cfg = STATUS_CFG[d.status] || STATUS_CFG.valido;
                            const Icon = cfg.icon;
                            return (
                                <div key={d.tipo}
                                    className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium ${cfg.bg} ${cfg.text}`}
                                    title={`${d.label}: ${d.status}${d.days_left !== null ? ` (${d.days_left}gg)` : ''}`}
                                    data-testid={`doc-pill-${d.tipo}`}
                                >
                                    <Icon className="w-3 h-3" />
                                    <span>{d.label}</span>
                                    {d.days_left !== null && d.days_left <= 30 && (
                                        <span className="font-mono">{d.days_left}gg</span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Alert 30 giorni */}
                {alert_30gg?.length > 0 && (
                    <div className="px-4 py-2 bg-amber-50/60 border-b border-amber-100">
                        <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> Previsione 30 giorni
                        </p>
                        {alert_30gg.map(a => (
                            <div key={a.tipo} className="text-xs text-amber-800 flex items-center gap-1.5 py-0.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${STATUS_CFG[a.status]?.color || 'bg-amber-400'}`} />
                                <span className="font-medium">{a.label}</span>
                                <span className="text-amber-600">
                                    {a.status === 'scaduto' ? 'gia scaduto' :
                                     a.status === 'critico' ? `scade tra ${a.days_left}gg — rinnovare subito` :
                                     `scade tra ${a.days_left}gg`}
                                </span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Commesse compliance */}
                <div className="divide-y divide-gray-100 max-h-[220px] overflow-y-auto">
                    {commesse_compliance?.length > 0 ? commesse_compliance.slice(0, 6).map(c => {
                        const pct = c.pct_conforme;
                        const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-500';
                        return (
                            <div key={c.commessa_id}
                                className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 cursor-pointer transition-colors"
                                onClick={() => navigate(`/commesse/${c.commessa_id}`)}
                                data-testid={`compliance-row-${c.commessa_id}`}
                            >
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-[#1E293B] truncate">{c.numero}</span>
                                        <span className="text-[10px] text-slate-400 truncate">{c.title}</span>
                                    </div>
                                    <div className="mt-1 h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                        <div className={`h-full rounded-full transition-all ${barColor}`}
                                            style={{ width: `${pct}%` }} />
                                    </div>
                                    {c.problemi?.length > 0 && (
                                        <p className="text-[10px] text-red-500 mt-0.5 truncate">
                                            {c.problemi[0]}
                                        </p>
                                    )}
                                </div>
                                <div className="text-right shrink-0">
                                    <span className={`text-sm font-mono font-bold ${
                                        pct >= 80 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600'
                                    }`}>{pct}%</span>
                                </div>
                            </div>
                        );
                    }) : (
                        <div className="text-center py-6 text-slate-400">
                            <Shield className="h-6 w-6 mx-auto mb-2 text-slate-300" />
                            <p className="text-xs">Nessuna commessa attiva</p>
                        </div>
                    )}
                </div>

                {/* Footer link */}
                <div className="px-4 py-2 bg-slate-50 border-t border-slate-100">
                    <button className="text-[10px] text-[#0055FF] font-medium flex items-center gap-1 hover:underline"
                        onClick={() => navigate('/settings', { state: { tab: 'documenti' } })}
                        data-testid="link-gestisci-docs">
                        Gestisci documenti <ArrowRight className="w-3 h-3" />
                    </button>
                </div>
            </CardContent>
        </Card>
    );
}
