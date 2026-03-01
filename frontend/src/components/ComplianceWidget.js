/**
 * ComplianceWidget — Dashboard widget showing EN 1090 compliance
 * status for all active commesse with completion indicators.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Shield, ArrowRight, CheckCircle2, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ComplianceWidget() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API}/api/dashboard/compliance-en1090`, {
                    headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
                });
                if (res.ok) setData(await res.json());
            } catch { /* silent */ }
            finally { setLoading(false); }
        };
        load();
    }, []);

    const commesse = data?.commesse || [];

    return (
        <Card className="border-gray-200" data-testid="widget-compliance">
            <CardHeader className="flex flex-row items-center justify-between bg-slate-50 border-b border-gray-200 py-3 px-5">
                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                    <Shield className="h-4 w-4 text-[#0055FF]" /> Compliance EN 1090
                </CardTitle>
                {commesse.length > 0 && (
                    <Badge className="bg-blue-100 text-[#0055FF] text-xs" data-testid="compliance-badge">
                        {commesse.length === 1 ? '1 commessa' : `${commesse.length} commesse`}
                    </Badge>
                )}
            </CardHeader>
            <CardContent className="p-0">
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" />
                    </div>
                ) : commesse.length === 0 ? (
                    <div className="text-center py-10 text-slate-400">
                        <Shield className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                        <p className="text-sm">Nessuna commessa EN 1090 attiva</p>
                        <p className="text-xs mt-1">Le commesse in produzione appariranno qui</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {commesse.slice(0, 5).map(c => {
                            const isComplete = c.compliance_pct === 100;
                            const barColor = c.compliance_pct >= 80 ? 'bg-emerald-500' : c.compliance_pct >= 50 ? 'bg-amber-500' : 'bg-red-400';
                            return (
                                <div key={c.commessa_id}
                                    className="px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                                    data-testid={`compliance-row-${c.commessa_id}`}
                                    onClick={() => navigate(`/commesse/${c.commessa_id}`)}>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <div className="flex items-center gap-2 min-w-0">
                                            {isComplete
                                                ? <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                                                : <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />}
                                            <div className="min-w-0">
                                                <p className="text-sm font-medium text-[#1E293B] truncate">
                                                    {c.numero} — {c.title}
                                                </p>
                                                <p className="text-[10px] text-slate-400">{c.client_name} {c.classe_esecuzione && `| ${c.classe_esecuzione}`}</p>
                                            </div>
                                        </div>
                                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${isComplete ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                                            {c.compliance_pct}%
                                        </span>
                                    </div>
                                    {/* Progress bar */}
                                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div className={`h-full rounded-full transition-all ${barColor}`}
                                            style={{ width: `${c.compliance_pct}%` }} />
                                    </div>
                                    {/* Doc status pills */}
                                    <div className="flex gap-1 mt-1.5 flex-wrap">
                                        {Object.entries(c.docs).map(([name, s]) => (
                                            <span key={name} className={`text-[8px] px-1.5 py-0.5 rounded font-medium ${s.complete ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>
                                                {name}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                        {commesse.length > 5 && (
                            <div className="px-5 py-2 text-center">
                                <Button variant="ghost" size="sm" className="text-[#0055FF] text-xs h-7"
                                    onClick={() => navigate('/commesse')}>
                                    Vedi tutte ({commesse.length}) <ArrowRight className="h-3 w-3 ml-1" />
                                </Button>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
