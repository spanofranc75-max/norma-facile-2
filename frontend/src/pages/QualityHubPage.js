/**
 * QualityHubPage — Dashboard riepilogativa del Sistema Qualità
 * Visione unificata di tutti gli alert: patentini, strumenti, NC, audit.
 * Pensata per il riesame della direzione ISO 9001.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    AlertTriangle, CheckCircle2, Clock, Shield, Users, Wrench,
    ClipboardCheck, FileText, Loader2, ChevronRight, CalendarDays,
    AlertCircle, XCircle, ArrowRight,
} from 'lucide-react';

function fmtDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function QualityHubPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        (async () => {
            try {
                const res = await apiRequest('/quality-hub/summary');
                setData(res);
            } catch { toast.error('Errore caricamento dati'); }
            finally { setLoading(false); }
        })();
    }, []);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
            </DashboardLayout>
        );
    }

    const s = data?.summary || {};
    const alerts = data?.alerts || {};
    const nextAudit = data?.next_audit;
    const hasAlerts = s.total_alerts > 0;

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="quality-hub-page">
                {/* Header */}
                <div>
                    <h1 className="font-sans text-3xl font-bold text-slate-900">Quality Hub</h1>
                    <p className="text-slate-600">Riepilogo Sistema Qualità — EN 1090 / ISO 9001</p>
                </div>

                {/* Status Banner */}
                {hasAlerts ? (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3" data-testid="alert-banner">
                        <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
                        <div>
                            <p className="text-sm font-semibold text-amber-800">
                                {s.total_alerts} {s.total_alerts === 1 ? 'elemento richiede' : 'elementi richiedono'} attenzione
                            </p>
                            <p className="text-xs text-amber-600 mt-0.5">
                                {[
                                    s.patents_expired > 0 && `${s.patents_expired} patentini scaduti`,
                                    s.patents_expiring > 0 && `${s.patents_expiring} patentini in scadenza`,
                                    s.instruments_expired > 0 && `${s.instruments_expired} strumenti scaduti`,
                                    s.instruments_expiring > 0 && `${s.instruments_expiring} strumenti in scadenza`,
                                    s.nc_open > 0 && `${s.nc_open} NC aperte`,
                                ].filter(Boolean).join(' · ')}
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3" data-testid="ok-banner">
                        <CheckCircle2 className="h-5 w-5 text-emerald-600 flex-shrink-0" />
                        <p className="text-sm font-semibold text-emerald-800">Tutti i sistemi sono in regola</p>
                    </div>
                )}

                {/* KPI Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="hub-kpi-grid">
                    <HubKPI icon={Users} label="Saldatori" value={s.welders_total || 0} sublabel={s.patents_expired > 0 ? `${s.patents_expired} scaduti` : 'OK'} subcolor={s.patents_expired > 0 ? 'text-red-600' : 'text-emerald-600'} color="text-blue-700" bg="bg-blue-50" onClick={() => navigate('/saldatori')} />
                    <HubKPI icon={Wrench} label="Apparecchiature" value={s.instruments_total || 0} sublabel={s.instruments_expired > 0 ? `${s.instruments_expired} scaduti` : 'OK'} subcolor={s.instruments_expired > 0 ? 'text-red-600' : 'text-emerald-600'} color="text-purple-700" bg="bg-purple-50" onClick={() => navigate('/strumenti')} />
                    <HubKPI icon={AlertCircle} label="NC Aperte" value={s.nc_open || 0} sublabel={s.nc_high_priority > 0 ? `${s.nc_high_priority} alta priorità` : '--'} subcolor={s.nc_high_priority > 0 ? 'text-red-600' : 'text-slate-400'} color="text-red-700" bg="bg-red-50" onClick={() => navigate('/audit')} />
                    <HubKPI icon={ClipboardCheck} label="Audit Anno" value={s.audits_this_year || 0} sublabel={nextAudit ? `Prossimo: ${fmtDate(nextAudit.date)}` : 'Nessuno programmato'} subcolor="text-slate-500" color="text-teal-700" bg="bg-teal-50" onClick={() => navigate('/audit')} />
                    <HubKPI icon={FileText} label="Documenti" value={s.documents_total || 0} sublabel="Archivio aziendale" subcolor="text-slate-500" color="text-slate-700" bg="bg-slate-50" onClick={() => navigate('/sistema-qualita')} />
                </div>

                {/* Alert Sections */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Patentini */}
                    <AlertSection
                        title="Patentini Saldatori"
                        icon={Users}
                        iconColor="text-blue-600"
                        expired={alerts.expired_patents || []}
                        expiring={alerts.expiring_patents || []}
                        emptyMsg="Tutti i patentini sono validi"
                        renderItem={(item) => (
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-slate-800">{item.welder_name} <span className="font-mono text-xs text-slate-400">({item.stamp_id})</span></p>
                                    <p className="text-xs text-slate-500">{item.standard} {item.process}</p>
                                </div>
                                <div className="text-right">
                                    <Badge className={`${item.type === 'expired' ? 'bg-red-100 text-red-700 border-red-200' : 'bg-amber-100 text-amber-700 border-amber-200'} border text-[10px]`}>
                                        {item.type === 'expired' ? 'Scaduto' : 'In Scadenza'}
                                    </Badge>
                                    <p className="text-[10px] text-slate-400 mt-0.5">{fmtDate(item.expiry_date)}</p>
                                </div>
                            </div>
                        )}
                        onViewAll={() => navigate('/saldatori')}
                        testId="section-patents"
                    />

                    {/* Strumenti */}
                    <AlertSection
                        title="Tarature Strumenti"
                        icon={Wrench}
                        iconColor="text-purple-600"
                        expired={alerts.expired_instruments || []}
                        expiring={alerts.expiring_instruments || []}
                        emptyMsg="Tutte le tarature sono in regola"
                        renderItem={(item) => (
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-slate-800">{item.name}</p>
                                    <p className="text-xs text-slate-500">{item.serial_number} — {item.instrument_type}</p>
                                </div>
                                <div className="text-right">
                                    <Badge className={`${item.type === 'expired' ? 'bg-red-100 text-red-700 border-red-200' : 'bg-amber-100 text-amber-700 border-amber-200'} border text-[10px]`}>
                                        {item.type === 'expired' ? 'Scaduto' : 'In Scadenza'}
                                    </Badge>
                                    <p className="text-[10px] text-slate-400 mt-0.5">{fmtDate(item.next_calibration_date)}</p>
                                </div>
                            </div>
                        )}
                        onViewAll={() => navigate('/strumenti')}
                        testId="section-instruments"
                    />
                </div>

                {/* NC Aperte */}
                <Card className="border-gray-200" data-testid="section-ncs">
                    <CardContent className="p-0">
                        <div className="flex items-center justify-between px-4 py-3 border-b">
                            <h3 className="text-sm font-bold text-[#1E293B] flex items-center gap-1.5">
                                <AlertCircle className="h-4 w-4 text-red-500" /> Non Conformità Aperte
                                <span className="text-xs text-slate-400 font-normal ml-1">({(alerts.open_ncs || []).length})</span>
                            </h3>
                            <Button variant="ghost" size="sm" onClick={() => navigate('/audit')} className="text-xs text-[#0055FF]">
                                Vai al Registro <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                            </Button>
                        </div>
                        {(!alerts.open_ncs || alerts.open_ncs.length === 0) ? (
                            <div className="text-center py-8">
                                <CheckCircle2 className="h-7 w-7 text-emerald-400 mx-auto mb-2" />
                                <p className="text-sm text-slate-500">Nessuna NC aperta</p>
                            </div>
                        ) : (
                            <div className="divide-y">
                                {alerts.open_ncs.map(nc => {
                                    const prColor = nc.priority === 'alta' ? 'bg-red-100 text-red-700 border-red-200' : nc.priority === 'media' ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-slate-100 text-slate-600 border-slate-200';
                                    const stColor = nc.status === 'in_lavorazione' ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-red-100 text-red-700 border-red-200';
                                    return (
                                        <div key={nc.nc_id} className={`px-4 py-2.5 flex items-center gap-3 hover:bg-slate-50 cursor-pointer ${nc.priority === 'alta' ? 'bg-red-50/30' : ''}`} data-testid={`hub-nc-${nc.nc_id}`} onClick={() => navigate('/audit')}>
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-mono text-xs text-slate-500">{nc.nc_number}</span>
                                                    <Badge className={`${prColor} border text-[9px]`}>{nc.priority}</Badge>
                                                    <Badge className={`${stColor} border text-[9px]`}>{nc.status === 'in_lavorazione' ? 'In Lavorazione' : 'Aperta'}</Badge>
                                                </div>
                                                <p className="text-sm text-slate-700 truncate mt-0.5">{nc.description}</p>
                                                <p className="text-[10px] text-slate-400">{nc.source || '--'} · {nc.days_open != null ? `${nc.days_open}gg` : '--'}</p>
                                            </div>
                                            <ChevronRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Next Audit */}
                {nextAudit && (
                    <Card className="border-gray-200 bg-gradient-to-r from-teal-50/50 to-transparent" data-testid="next-audit-card">
                        <CardContent className="py-4 px-5">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-lg bg-teal-100 flex items-center justify-center">
                                        <CalendarDays className="h-5 w-5 text-teal-700" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-[#1E293B]">Prossimo Audit Programmato</p>
                                        <p className="text-xs text-slate-500">
                                            {fmtDate(nextAudit.date)} — {nextAudit.audit_type === 'interno' ? 'Interno' : nextAudit.audit_type === 'esterno_ente' ? 'Ente Certificatore' : 'Cliente'}
                                            {nextAudit.auditor_name && ` · ${nextAudit.auditor_name}`}
                                        </p>
                                    </div>
                                </div>
                                <Button variant="outline" size="sm" onClick={() => navigate('/audit')} className="text-xs">
                                    Dettagli <ArrowRight className="h-3.5 w-3.5 ml-1" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </DashboardLayout>
    );
}

/* ── Sub-components ── */

function HubKPI({ icon: Icon, label, value, sublabel, subcolor, color, bg, onClick }) {
    return (
        <Card className="border-gray-200 cursor-pointer hover:shadow-sm transition-shadow" onClick={onClick} data-testid={`hub-kpi-${label.toLowerCase().replace(/\s/g, '-')}`}>
            <CardContent className="pt-4 pb-3 px-4">
                <div className="flex items-center gap-2.5">
                    <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
                        <Icon className={`h-4.5 w-4.5 ${color}`} />
                    </div>
                    <div>
                        <p className={`text-xl font-bold ${color}`}>{value}</p>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                        <p className={`text-[9px] font-medium ${subcolor}`}>{sublabel}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

function AlertSection({ title, icon: Icon, iconColor, expired, expiring, emptyMsg, renderItem, onViewAll, testId }) {
    const items = [...expired, ...expiring];
    return (
        <Card className="border-gray-200" data-testid={testId}>
            <CardContent className="p-0">
                <div className="flex items-center justify-between px-4 py-3 border-b">
                    <h3 className="text-sm font-bold text-[#1E293B] flex items-center gap-1.5">
                        <Icon className={`h-4 w-4 ${iconColor}`} /> {title}
                        {items.length > 0 && <span className="text-xs text-red-500 font-normal ml-1">({items.length})</span>}
                    </h3>
                    <Button variant="ghost" size="sm" onClick={onViewAll} className="text-xs text-[#0055FF]">
                        Vedi Tutto <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                    </Button>
                </div>
                {items.length === 0 ? (
                    <div className="text-center py-6">
                        <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto mb-1.5" />
                        <p className="text-xs text-slate-500">{emptyMsg}</p>
                    </div>
                ) : (
                    <div className="divide-y">
                        {items.map((item, i) => (
                            <div key={i} className={`px-4 py-2.5 ${item.type === 'expired' ? 'bg-red-50/30' : ''}`}>
                                {renderItem(item)}
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
