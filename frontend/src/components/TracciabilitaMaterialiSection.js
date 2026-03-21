/**
 * TracciabilitaMaterialiSection — Link DDT → Lotti FPC (EN 1090 FPC Fase 2).
 * Auto-associazione DDT di carico ai lotti materiale FPC.
 * Scheda rintracciabilita con colata, certificato 3.1, DDT, fornitore.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import {
    Link2, Package, Loader2, RefreshCw, CheckCircle, XCircle,
    FileText, Truck, ArrowRight, Zap, AlertTriangle, Search,
} from 'lucide-react';

export default function TracciabilitaMaterialiSection({ commessaId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [linking, setLinking] = useState(false);
    const [linkResult, setLinkResult] = useState(null);
    const [verifying, setVerifying] = useState(false);
    const [verifyResult, setVerifyResult] = useState(null);

    const load = useCallback(async () => {
        try {
            const res = await apiRequest(`/fpc/batches/rintracciabilita/${commessaId}`);
            setData(res);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { load(); }, [load]);

    const handleAutoLink = async () => {
        setLinking(true);
        setLinkResult(null);
        try {
            const res = await apiRequest(`/fpc/batches/link-ddt/${commessaId}`, { method: 'POST' });
            setLinkResult(res);
            if (res.totale > 0) {
                toast.success(`${res.totale} lotti collegati a DDT automaticamente`);
            } else {
                toast.info('Nessuna nuova corrispondenza trovata');
            }
            load();
        } catch (e) {
            toast.error(e.message || 'Errore durante il collegamento');
        } finally {
            setLinking(false);
        }
    };

    const handleVerificaCoerenza = async () => {
        setVerifying(true);
        setVerifyResult(null);
        try {
            const res = await apiRequest(`/fpc/batches/verifica-coerenza/${commessaId}`);
            setVerifyResult(res);
            const r = res.riepilogo;
            if (r.critici > 0) {
                toast.error(`${r.critici} discrepanze critiche trovate`);
            } else if (r.attenzione > 0) {
                toast.warning(`${r.attenzione} avvisi trovati — nessuna criticita`);
            } else {
                toast.success('Verifica superata — tutti i lotti conformi');
            }
        } catch (e) {
            toast.error(e.message || 'Errore durante la verifica');
        } finally {
            setVerifying(false);
        }
    };

    if (loading) {
        return (
            <Card className="border-gray-200">
                <CardContent className="py-8 flex items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                </CardContent>
            </Card>
        );
    }

    const righe = data?.righe || [];
    const collegati = data?.collegati || 0;
    const totale = data?.totale || 0;

    return (
        <Card className="border-gray-200" data-testid="tracciabilita-materiali-section">
            <CardHeader className="bg-gradient-to-r from-blue-700 to-cyan-600 py-2.5 px-4 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                        <Package className="h-3.5 w-3.5" /> Tracciabilita Materiali
                        {totale > 0 && (
                            <Badge className="bg-white/20 text-white text-[10px] ml-1">
                                {collegati}/{totale} collegati
                            </Badge>
                        )}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Button size="sm" variant="ghost" onClick={load} className="text-white hover:bg-white/10 h-7 w-7 p-0" data-testid="tracciabilita-refresh">
                            <RefreshCw className="h-3 w-3" />
                        </Button>
                        <Button
                            size="sm"
                            onClick={handleVerificaCoerenza}
                            disabled={verifying || totale === 0}
                            className="bg-white/20 text-white hover:bg-white/30 text-[11px] h-7 px-2.5 border border-white/30"
                            data-testid="tracciabilita-verifica-btn"
                        >
                            {verifying ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Search className="h-3 w-3 mr-1" />}
                            Verifica Coerenza
                        </Button>
                        <Button
                            size="sm"
                            onClick={handleAutoLink}
                            disabled={linking}
                            className="bg-white text-blue-700 hover:bg-blue-50 text-[11px] h-7 px-2.5"
                            data-testid="tracciabilita-autolink-btn"
                        >
                            {linking ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Zap className="h-3 w-3 mr-1" />}
                            Auto-Collega DDT
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-3">
                {/* Link Result Feedback */}
                {linkResult && (
                    <div className={`p-2.5 rounded-lg text-xs ${linkResult.totale > 0 ? 'bg-emerald-50 border border-emerald-200 text-emerald-700' : 'bg-slate-50 border border-slate-200 text-slate-600'}`}
                         data-testid="tracciabilita-link-result">
                        <div className="flex items-center gap-1.5 font-semibold mb-1">
                            {linkResult.totale > 0 ? <CheckCircle className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                            {linkResult.message}
                        </div>
                        {linkResult.links?.length > 0 && (
                            <div className="space-y-1 mt-2">
                                {linkResult.links.map((l, i) => (
                                    <div key={i} className="flex items-center gap-2 text-[10px] bg-white/70 p-1.5 rounded">
                                        <Badge className="bg-blue-100 text-blue-700 text-[9px]">{l.match_type}</Badge>
                                        <span className="font-mono">{l.batch_desc || l.heat_number}</span>
                                        <ArrowRight className="h-2.5 w-2.5 text-slate-400" />
                                        <span>DDT {l.ddt_number}</span>
                                        <span className="text-slate-400">({l.fornitore})</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Verify Result Panel */}
                {verifyResult && (
                    <div className="space-y-2" data-testid="tracciabilita-verify-result">
                        <div className={`p-2.5 rounded-lg text-xs border ${
                            verifyResult.riepilogo.critici > 0
                                ? 'bg-red-50 border-red-200 text-red-700'
                                : verifyResult.riepilogo.attenzione > 0
                                    ? 'bg-amber-50 border-amber-200 text-amber-700'
                                    : 'bg-emerald-50 border-emerald-200 text-emerald-700'
                        }`}>
                            <div className="flex items-center justify-between mb-1.5">
                                <span className="font-semibold flex items-center gap-1.5">
                                    {verifyResult.riepilogo.critici > 0 ? <XCircle className="h-3.5 w-3.5" /> :
                                     verifyResult.riepilogo.attenzione > 0 ? <AlertTriangle className="h-3.5 w-3.5" /> :
                                     <CheckCircle className="h-3.5 w-3.5" />}
                                    Verifica Coerenza — {verifyResult.riepilogo.pct_conforme}% conforme
                                </span>
                                <span className="text-[10px]">{verifyResult.riepilogo.conformi}/{verifyResult.riepilogo.totale} lotti OK</span>
                            </div>
                            <div className="grid grid-cols-4 gap-2 mt-2">
                                <div className="text-center p-1 bg-white/60 rounded">
                                    <p className="text-[9px]">Conformi</p>
                                    <p className="font-bold text-emerald-700">{verifyResult.riepilogo.conformi}</p>
                                </div>
                                <div className="text-center p-1 bg-white/60 rounded">
                                    <p className="text-[9px]">Critici</p>
                                    <p className="font-bold text-red-700">{verifyResult.riepilogo.critici}</p>
                                </div>
                                <div className="text-center p-1 bg-white/60 rounded">
                                    <p className="text-[9px]">Senza colata</p>
                                    <p className="font-bold text-red-700">{verifyResult.riepilogo.senza_colata}</p>
                                </div>
                                <div className="text-center p-1 bg-white/60 rounded">
                                    <p className="text-[9px]">Senza cert.</p>
                                    <p className="font-bold text-amber-700">{verifyResult.riepilogo.senza_certificato}</p>
                                </div>
                            </div>
                        </div>
                        {/* Issue details */}
                        {verifyResult.lotti.filter(l => !l.conforme).map(l => (
                            <div key={l.batch_id} className="p-2 bg-white border border-slate-200 rounded-lg text-xs">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="font-mono font-semibold text-slate-800">{l.descrizione || l.batch_id}</span>
                                    <span className="text-slate-400">Colata: {l.colata || '—'}</span>
                                </div>
                                {l.issues.map((issue, i) => (
                                    <div key={i} className={`flex items-start gap-1.5 mt-1 ${issue.gravita === 'critica' ? 'text-red-600' : 'text-amber-600'}`}>
                                        {issue.gravita === 'critica' ? <XCircle className="h-3 w-3 mt-0.5 shrink-0" /> : <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />}
                                        <span className="text-[10px]">{issue.messaggio}</span>
                                    </div>
                                ))}
                            </div>
                        ))}
                    </div>
                )}

                {/* Stats bar */}
                {totale > 0 && (
                    <div className="flex items-center gap-2" data-testid="tracciabilita-stats">
                        <div className="flex-1 bg-slate-200 rounded-full h-2 overflow-hidden">
                            <div
                                className={`h-2 rounded-full transition-all ${collegati === totale ? 'bg-emerald-500' : 'bg-blue-500'}`}
                                style={{ width: `${totale > 0 ? (collegati / totale) * 100 : 0}%` }}
                            />
                        </div>
                        <span className={`text-xs font-mono font-semibold ${collegati === totale ? 'text-emerald-600' : 'text-blue-600'}`}>
                            {totale > 0 ? Math.round((collegati / totale) * 100) : 0}%
                        </span>
                    </div>
                )}

                {/* Tabella Rintracciabilita */}
                {righe.length === 0 ? (
                    <div className="text-center py-6 text-sm text-slate-400" data-testid="tracciabilita-empty">
                        <Package className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                        Nessun lotto materiale registrato per questa commessa.
                        <br />
                        <span className="text-xs">I lotti vengono creati dalla sezione Tracciabilita FPC o automaticamente dai DDT.</span>
                    </div>
                ) : (
                    <div className="overflow-x-auto" data-testid="tracciabilita-table">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b text-left text-slate-500">
                                    <th className="pb-2 pr-2 font-medium">Materiale</th>
                                    <th className="pb-2 pr-2 font-medium">Colata</th>
                                    <th className="pb-2 pr-2 font-medium">Cert. 3.1</th>
                                    <th className="pb-2 pr-2 font-medium">Fornitore</th>
                                    <th className="pb-2 pr-2 font-medium">DDT</th>
                                    <th className="pb-2 pr-2 font-medium">Pos. Dwg</th>
                                    <th className="pb-2 font-medium">Stato</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {righe.map(r => (
                                    <tr key={r.batch_id} className="hover:bg-slate-50 transition-colors" data-testid={`tracciabilita-riga-${r.batch_id}`}>
                                        <td className="py-2 pr-2">
                                            <span className="text-slate-700">{r.descrizione || r.materiale || '—'}</span>
                                        </td>
                                        <td className="py-2 pr-2">
                                            <span className="font-mono text-slate-800">{r.colata || '—'}</span>
                                        </td>
                                        <td className="py-2 pr-2">
                                            {r.certificato_31 ? (
                                                <Badge className="bg-emerald-100 text-emerald-700 text-[10px] gap-1">
                                                    <FileText className="h-2.5 w-2.5" /> {r.certificato_31}
                                                </Badge>
                                            ) : (
                                                <span className="text-slate-400">—</span>
                                            )}
                                        </td>
                                        <td className="py-2 pr-2 text-slate-500">{r.fornitore || '—'}</td>
                                        <td className="py-2 pr-2">
                                            {r.ddt_numero ? (
                                                <Badge className="bg-blue-100 text-blue-700 text-[10px] gap-1">
                                                    <Truck className="h-2.5 w-2.5" /> {r.ddt_numero}
                                                </Badge>
                                            ) : (
                                                <span className="text-slate-400">—</span>
                                            )}
                                        </td>
                                        <td className="py-2 pr-2 text-slate-500">{r.posizione_dwg || '—'}</td>
                                        <td className="py-2">
                                            {r.linked ? (
                                                <Badge className="bg-emerald-100 text-emerald-700 text-[10px] gap-1">
                                                    <Link2 className="h-2.5 w-2.5" /> Collegato
                                                </Badge>
                                            ) : (
                                                <Badge className="bg-amber-100 text-amber-700 text-[10px] gap-1">
                                                    <XCircle className="h-2.5 w-2.5" /> Da collegare
                                                </Badge>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
