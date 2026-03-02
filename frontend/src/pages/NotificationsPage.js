/**
 * NotificationsPage — "Il Cane da Guardia"
 * Dashboard for monitoring expiration alerts (welders, instruments)
 * and managing notification settings.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    Bell, ShieldAlert, Wrench, Users, Clock, CheckCircle2,
    AlertTriangle, XCircle, Loader2, RefreshCw, Mail, History,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function fmtDate(d) {
    if (!d) return '-';
    try {
        return new Date(d).toLocaleString('it-IT', {
            day: '2-digit', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    } catch { return d; }
}

export default function NotificationsPage() {
    const [status, setStatus] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [checking, setChecking] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false);

    const fetchStatus = useCallback(async () => {
        try {
            const data = await apiRequest('/notifications/status');
            setStatus(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchHistory = useCallback(async () => {
        setLoadingHistory(true);
        try {
            const data = await apiRequest('/notifications/history');
            setHistory(data.logs || []);
        } catch { /* silent */ }
        finally { setLoadingHistory(false); }
    }, []);

    useEffect(() => {
        fetchStatus();
        fetchHistory();
    }, [fetchStatus, fetchHistory]);

    const handleManualCheck = async () => {
        setChecking(true);
        try {
            const result = await apiRequest('/notifications/check-now', { method: 'POST' });
            toast.success(`Controllo completato: ${result.total_alerts} scadenze trovate${result.email_sent ? ', email inviata' : ''}`);
            await fetchStatus();
            await fetchHistory();
        } catch (e) {
            toast.error(e.message || 'Errore nel controllo');
        } finally {
            setChecking(false);
        }
    };

    const alerts = status?.current_alerts;
    const totalAlerts = alerts?.total || 0;

    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center py-24">
                <Loader2 className="h-6 w-6 animate-spin text-[#0055FF]" />
            </div>
        </DashboardLayout>
    );

    return (
        <DashboardLayout>
            <div className="space-y-6 max-w-5xl" data-testid="notifications-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900 flex items-center gap-3">
                            <Bell className="h-7 w-7 text-amber-500" />
                            Il Cane da Guardia
                        </h1>
                        <p className="text-slate-500 mt-1">
                            Monitoraggio automatico scadenze qualifiche e calibrazioni
                        </p>
                    </div>
                    <Button
                        onClick={handleManualCheck}
                        disabled={checking}
                        className="bg-amber-500 hover:bg-amber-600 text-white"
                        data-testid="btn-check-now"
                    >
                        {checking
                            ? <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            : <RefreshCw className="h-4 w-4 mr-2" />
                        }
                        {checking ? 'Controllo in corso...' : 'Controlla Ora'}
                    </Button>
                </div>

                {/* Status Summary */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className={`border-l-4 ${totalAlerts > 0 ? 'border-l-amber-500' : 'border-l-emerald-500'}`} data-testid="alert-summary">
                        <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-xs text-slate-500 uppercase tracking-wider">Scadenze Attive</p>
                                    <p className={`text-3xl font-bold mt-1 ${totalAlerts > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                                        {totalAlerts}
                                    </p>
                                </div>
                                {totalAlerts > 0
                                    ? <AlertTriangle className="h-8 w-8 text-amber-400" />
                                    : <CheckCircle2 className="h-8 w-8 text-emerald-400" />
                                }
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-l-4 border-l-blue-500" data-testid="welder-alert-count">
                        <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-xs text-slate-500 uppercase tracking-wider">Qualifiche Saldatori</p>
                                    <p className="text-3xl font-bold mt-1 text-blue-600">{alerts?.welder_count || 0}</p>
                                </div>
                                <Users className="h-8 w-8 text-blue-400" />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-l-4 border-l-violet-500" data-testid="instrument-alert-count">
                        <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-xs text-slate-500 uppercase tracking-wider">Calibrazioni Strumenti</p>
                                    <p className="text-3xl font-bold mt-1 text-violet-600">{alerts?.instrument_count || 0}</p>
                                </div>
                                <Wrench className="h-8 w-8 text-violet-400" />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Scheduler Info */}
                {status?.last_check && (
                    <Card className="border-gray-200 bg-slate-50" data-testid="last-check-info">
                        <CardContent className="p-4 flex items-center gap-3">
                            <Clock className="h-4 w-4 text-slate-400" />
                            <span className="text-sm text-slate-600">
                                Ultimo controllo: <strong>{fmtDate(status.last_check.checked_at)}</strong>
                                {' '}({status.last_check.source === 'automatico' ? 'automatico' : 'manuale'})
                                {status.last_check.email_sent && (
                                    <Badge className="ml-2 bg-emerald-100 text-emerald-700 text-[10px]">
                                        <Mail className="h-3 w-3 mr-1" /> Email inviata
                                    </Badge>
                                )}
                            </span>
                        </CardContent>
                    </Card>
                )}

                {/* Welder Alerts Detail */}
                {alerts?.welders?.length > 0 && (
                    <Card className="border-gray-200" data-testid="welder-alerts-table">
                        <CardHeader className="bg-blue-50 border-b">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Users className="h-4 w-4 text-blue-600" />
                                Qualifiche Saldatori in Scadenza
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-slate-50 text-slate-500 text-xs">
                                        <th className="text-left px-4 py-2">Saldatore</th>
                                        <th className="text-left px-4 py-2">Punzone</th>
                                        <th className="text-left px-4 py-2">Qualifica</th>
                                        <th className="text-left px-4 py-2">Scadenza</th>
                                        <th className="text-left px-4 py-2">Stato</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {alerts.welders.sort((a, b) => a.days_remaining - b.days_remaining).map((a, i) => (
                                        <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                                            <td className="px-4 py-2 font-medium">{a.welder_name}</td>
                                            <td className="px-4 py-2 font-mono text-xs">{a.stamp_id}</td>
                                            <td className="px-4 py-2 text-xs">{a.qualification}</td>
                                            <td className="px-4 py-2 text-xs">{a.expiry_date}</td>
                                            <td className="px-4 py-2">
                                                <AlertBadge days={a.days_remaining} label={a.status_label} />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </CardContent>
                    </Card>
                )}

                {/* Instrument Alerts Detail */}
                {alerts?.instruments?.length > 0 && (
                    <Card className="border-gray-200" data-testid="instrument-alerts-table">
                        <CardHeader className="bg-violet-50 border-b">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Wrench className="h-4 w-4 text-violet-600" />
                                Calibrazioni Strumenti in Scadenza
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-slate-50 text-slate-500 text-xs">
                                        <th className="text-left px-4 py-2">Strumento</th>
                                        <th className="text-left px-4 py-2">N. Serie</th>
                                        <th className="text-left px-4 py-2">Prossima Taratura</th>
                                        <th className="text-left px-4 py-2">Stato</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {alerts.instruments.sort((a, b) => a.days_remaining - b.days_remaining).map((a, i) => (
                                        <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                                            <td className="px-4 py-2 font-medium">{a.instrument_name}</td>
                                            <td className="px-4 py-2 font-mono text-xs">{a.serial_number}</td>
                                            <td className="px-4 py-2 text-xs">{a.next_calibration_date}</td>
                                            <td className="px-4 py-2">
                                                <AlertBadge days={a.days_remaining} label={a.status_label} />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </CardContent>
                    </Card>
                )}

                {/* No alerts */}
                {totalAlerts === 0 && (
                    <Card className="border-emerald-200 bg-emerald-50" data-testid="no-alerts">
                        <CardContent className="p-8 text-center">
                            <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto mb-3" />
                            <h3 className="text-lg font-semibold text-emerald-800">Tutto in regola</h3>
                            <p className="text-sm text-emerald-600 mt-1">
                                Nessuna scadenza imminente nei prossimi 30 giorni
                            </p>
                        </CardContent>
                    </Card>
                )}

                {/* History */}
                <Card className="border-gray-200" data-testid="notification-history">
                    <CardHeader className="bg-slate-50 border-b">
                        <CardTitle className="text-base flex items-center gap-2">
                            <History className="h-4 w-4 text-slate-600" />
                            Storico Controlli
                        </CardTitle>
                        <CardDescription>Ultimi 20 controlli effettuati</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        {loadingHistory ? (
                            <div className="p-6 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin" /> Caricamento...
                            </div>
                        ) : history.length === 0 ? (
                            <div className="p-6 text-center text-slate-400 text-sm">
                                Nessun controllo ancora effettuato
                            </div>
                        ) : (
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-slate-50 text-slate-500 text-xs border-t">
                                        <th className="text-left px-4 py-2">Data</th>
                                        <th className="text-left px-4 py-2">Tipo</th>
                                        <th className="text-left px-4 py-2">Saldatori</th>
                                        <th className="text-left px-4 py-2">Strumenti</th>
                                        <th className="text-left px-4 py-2">Totale</th>
                                        <th className="text-left px-4 py-2">Email</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {history.map((log, i) => (
                                        <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                                            <td className="px-4 py-2 text-xs">{fmtDate(log.checked_at)}</td>
                                            <td className="px-4 py-2">
                                                <Badge className={`text-[10px] ${log.source === 'automatico' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                                                    {log.source === 'automatico' ? 'Auto' : 'Manuale'}
                                                </Badge>
                                            </td>
                                            <td className="px-4 py-2 text-center">{log.welder_count || 0}</td>
                                            <td className="px-4 py-2 text-center">{log.instrument_count || 0}</td>
                                            <td className="px-4 py-2 text-center font-semibold">{log.total_alerts || 0}</td>
                                            <td className="px-4 py-2">
                                                {log.email_sent
                                                    ? <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                                                    : <XCircle className="h-4 w-4 text-slate-300" />
                                                }
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}

function AlertBadge({ days, label }) {
    let classes = 'bg-amber-100 text-amber-700 border-amber-300';
    if (days < 0) classes = 'bg-red-100 text-red-700 border-red-300';
    else if (days <= 7) classes = 'bg-orange-100 text-orange-700 border-orange-300';

    return (
        <span className={`text-[10px] font-bold border rounded-full px-2 py-0.5 ${classes}`}>
            {label}
        </span>
    );
}
