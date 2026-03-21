/**
 * ReportIspezioniSection — Rapporto Ispezioni VT/Dimensionali EN 1090-2.
 * Checklist VT (ISO 5817-C) + Dimensionale (B6/B8) con firma e PDF.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { toast } from 'sonner';
import {
    Eye, Ruler, CheckCircle, XCircle, Loader2, Lock, Pen, FileDown,
    RefreshCw, AlertTriangle, Minus,
} from 'lucide-react';

const AREA = {
    vt: { label: 'Visual Testing — ISO 5817 Livello C', icon: Eye, color: 'violet' },
    dim: { label: 'Dimensionale — EN 1090-2 B6/B8', icon: Ruler, color: 'cyan' },
};

export default function ReportIspezioniSection({ commessaId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [approving, setApproving] = useState(false);
    const [showFirma, setShowFirma] = useState(false);
    const [firmaNome, setFirmaNome] = useState('');
    const [firmaRuolo, setFirmaRuolo] = useState('Ispettore VT/Dimensionale');
    const [expandedArea, setExpandedArea] = useState('vt');

    // Editable state
    const [vtResults, setVtResults] = useState({});
    const [dimResults, setDimResults] = useState({});
    const [metadata, setMetadata] = useState({ strumenti: '', condizioni: '', ispettore: '', note: '' });

    const load = useCallback(async () => {
        try {
            const res = await apiRequest(`/report-ispezioni/${commessaId}`);
            setData(res);
            // Populate editable state
            const vt = {};
            res.checks_vt?.forEach(c => { vt[c.id] = { esito: c.esito, valore_misurato: c.valore_misurato || '', note: c.note || '' }; });
            setVtResults(vt);
            const dim = {};
            res.checks_dim?.forEach(c => { dim[c.id] = { esito: c.esito, valore_misurato: c.valore_misurato || '', note: c.note || '' }; });
            setDimResults(dim);
            setMetadata({
                strumenti: res.strumenti_utilizzati || '',
                condizioni: res.condizioni_ambientali || '',
                ispettore: res.ispettore_nome || '',
                note: res.note_generali || '',
            });
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { load(); }, [load]);

    const setCheckResult = (area, checkId, field, value) => {
        const setter = area === 'vt' ? setVtResults : setDimResults;
        setter(prev => ({
            ...prev,
            [checkId]: { ...prev[checkId], [field]: value },
        }));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const ispezioni_vt = Object.entries(vtResults).map(([check_id, v]) => ({
                check_id, esito: v.esito, valore_misurato: v.valore_misurato || '', note: v.note || '',
            }));
            const ispezioni_dim = Object.entries(dimResults).map(([check_id, v]) => ({
                check_id, esito: v.esito, valore_misurato: v.valore_misurato || '', note: v.note || '',
            }));
            await apiRequest(`/report-ispezioni/${commessaId}`, {
                method: 'POST',
                body: {
                    ispezioni_vt, ispezioni_dim,
                    strumenti_utilizzati: metadata.strumenti,
                    condizioni_ambientali: metadata.condizioni,
                    ispettore_nome: metadata.ispettore,
                    note_generali: metadata.note,
                },
            });
            toast.success('Report ispezioni salvato');
            load();
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const handleApprova = async () => {
        if (!firmaNome.trim()) { toast.error('Inserisci il nome per la firma'); return; }
        setApproving(true);
        try {
            await handleSave();
            await apiRequest(`/report-ispezioni/${commessaId}/approva`, {
                method: 'POST',
                body: { firma_nome: firmaNome, firma_ruolo: firmaRuolo },
            });
            toast.success('Report approvato e firmato');
            setShowFirma(false);
            load();
        } catch (e) { toast.error(e.message); }
        finally { setApproving(false); }
    };

    const handleDownloadPdf = async () => {
        try {
            toast.info('Generazione PDF Report Ispezioni...');
            await downloadPdfBlob(`/report-ispezioni/${commessaId}/pdf`, `Report_Ispezioni_${commessaId}.pdf`);
        } catch (e) { toast.error(e.message); }
    };

    if (loading) {
        return (
            <Card className="border-gray-200">
                <CardContent className="py-8 flex items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-violet-500" />
                </CardContent>
            </Card>
        );
    }

    if (!data) return null;

    const { stats, approvato, firma, completo, superato } = data;
    const isLocked = approvato;

    const renderChecks = (checks, results, area) => {
        return checks.map(ck => {
            const r = results[ck.id] || {};
            const esito = r.esito;
            return (
                <div key={ck.id} className={`flex items-start gap-2 p-2 rounded-lg border transition-colors text-xs ${
                    esito === true ? 'bg-emerald-50/50 border-emerald-200' :
                    esito === false ? 'bg-red-50/50 border-red-200' :
                    'bg-white border-slate-200'
                }`} data-testid={`rpt-check-${ck.id}`}>
                    {/* Esito buttons */}
                    <div className="flex flex-col gap-0.5 mt-0.5">
                        <button
                            disabled={isLocked}
                            onClick={() => setCheckResult(area, ck.id, 'esito', esito === true ? null : true)}
                            className={`p-0.5 rounded ${esito === true ? 'bg-emerald-500 text-white' : 'text-slate-300 hover:text-emerald-500'}`}
                            data-testid={`rpt-ok-${ck.id}`}
                        >
                            <CheckCircle className="h-3.5 w-3.5" />
                        </button>
                        <button
                            disabled={isLocked}
                            onClick={() => setCheckResult(area, ck.id, 'esito', esito === false ? null : false)}
                            className={`p-0.5 rounded ${esito === false ? 'bg-red-500 text-white' : 'text-slate-300 hover:text-red-500'}`}
                            data-testid={`rpt-nok-${ck.id}`}
                        >
                            <XCircle className="h-3.5 w-3.5" />
                        </button>
                    </div>
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-medium text-slate-700">{ck.label}</span>
                            <Badge className="bg-slate-100 text-slate-400 text-[7px]">{ck.rif}</Badge>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">{ck.desc}</p>
                    </div>
                    {/* Valore + Note inline */}
                    <div className="flex items-center gap-1.5 shrink-0">
                        <Input
                            disabled={isLocked}
                            value={r.valore_misurato || ''}
                            onChange={e => setCheckResult(area, ck.id, 'valore_misurato', e.target.value)}
                            placeholder="Misura"
                            className="w-20 h-6 text-[10px]"
                            data-testid={`rpt-val-${ck.id}`}
                        />
                        <Input
                            disabled={isLocked}
                            value={r.note || ''}
                            onChange={e => setCheckResult(area, ck.id, 'note', e.target.value)}
                            placeholder="Note"
                            className="w-24 h-6 text-[10px]"
                            data-testid={`rpt-note-${ck.id}`}
                        />
                    </div>
                </div>
            );
        });
    };

    return (
        <Card className="border-gray-200" data-testid="report-ispezioni-section">
            <CardHeader className="bg-gradient-to-r from-violet-700 to-purple-600 py-2.5 px-4 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                        <Eye className="h-3.5 w-3.5" /> Report Ispezioni VT / Dimensionale
                        <Badge className={`text-[10px] ml-1 ${superato ? 'bg-white/20 text-white' : 'bg-red-400/30 text-red-100'}`}>
                            VT {stats.vt.ok}/{stats.vt.totale} | DIM {stats.dim.ok}/{stats.dim.totale}
                        </Badge>
                        {isLocked && <Lock className="h-3 w-3 text-white/70" />}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Button size="sm" variant="ghost" onClick={handleDownloadPdf} className="text-white hover:bg-white/10 h-7 w-7 p-0" data-testid="rpt-pdf-btn">
                            <FileDown className="h-3 w-3" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={load} className="text-white hover:bg-white/10 h-7 w-7 p-0" data-testid="rpt-refresh">
                            <RefreshCw className="h-3 w-3" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-3">
                {/* Stats */}
                <div className="grid grid-cols-2 gap-2">
                    {Object.entries(AREA).map(([key, cfg]) => {
                        const AIcon = cfg.icon;
                        const s = stats[key];
                        const allDone = s.pending === 0;
                        const allOk = allDone && s.nok === 0;
                        return (
                            <button key={key} onClick={() => setExpandedArea(key)}
                                className={`p-2 rounded-lg border text-left transition-colors ${
                                    expandedArea === key ? `border-${cfg.color}-300 bg-${cfg.color}-50/50` : 'border-slate-200'
                                } ${allOk ? 'ring-1 ring-emerald-300' : ''}`}
                                data-testid={`rpt-area-${key}`}>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <AIcon className="h-3 w-3" />
                                    <span className="text-[10px] font-semibold text-slate-700">{cfg.label}</span>
                                </div>
                                <div className="flex items-center gap-2 text-[10px]">
                                    <span className="text-emerald-600 font-bold">{s.ok} OK</span>
                                    {s.nok > 0 && <span className="text-red-600 font-bold">{s.nok} NOK</span>}
                                    {s.pending > 0 && <span className="text-slate-400">{s.pending} da fare</span>}
                                </div>
                            </button>
                        );
                    })}
                </div>

                {/* Approved banner */}
                {isLocked && firma && (
                    <div className="p-2 bg-violet-50 border border-violet-200 rounded-lg text-xs text-violet-700 flex items-center gap-2" data-testid="rpt-approved-banner">
                        <Lock className="h-3.5 w-3.5" />
                        <span className="font-semibold">Report Approvato</span>
                        <span className="text-violet-500">{firma.nome} — {firma.ruolo} — {firma.timestamp?.slice(0, 10)}</span>
                    </div>
                )}

                {/* Checklist area */}
                <div className="space-y-1.5" data-testid={`rpt-checklist-${expandedArea}`}>
                    {expandedArea === 'vt' && renderChecks(data.checks_vt, vtResults, 'vt')}
                    {expandedArea === 'dim' && renderChecks(data.checks_dim, dimResults, 'dim')}
                </div>

                {/* Metadata */}
                {!isLocked && (
                    <div className="grid grid-cols-2 gap-2 pt-1">
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Ispettore</label>
                            <Input value={metadata.ispettore} onChange={e => setMetadata(m => ({ ...m, ispettore: e.target.value }))}
                                placeholder="Nome ispettore" className="text-xs h-7 mt-0.5" data-testid="rpt-ispettore" />
                        </div>
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Strumenti utilizzati</label>
                            <Input value={metadata.strumenti} onChange={e => setMetadata(m => ({ ...m, strumenti: e.target.value }))}
                                placeholder="Calibro, flessometro, livella..." className="text-xs h-7 mt-0.5" data-testid="rpt-strumenti" />
                        </div>
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Condizioni ambientali</label>
                            <Input value={metadata.condizioni} onChange={e => setMetadata(m => ({ ...m, condizioni: e.target.value }))}
                                placeholder="Luce naturale, 20C..." className="text-xs h-7 mt-0.5" data-testid="rpt-condizioni" />
                        </div>
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Note generali</label>
                            <Input value={metadata.note} onChange={e => setMetadata(m => ({ ...m, note: e.target.value }))}
                                placeholder="Note..." className="text-xs h-7 mt-0.5" data-testid="rpt-note-gen" />
                        </div>
                    </div>
                )}

                {/* Actions */}
                {!isLocked && (
                    <div className="flex items-center gap-2 pt-1">
                        <Button size="sm" variant="outline" onClick={handleSave} disabled={saving}
                            className="text-xs" data-testid="rpt-save-btn">
                            {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Pen className="h-3 w-3 mr-1" />}
                            Salva bozza
                        </Button>
                        {!showFirma ? (
                            <Button size="sm" onClick={() => setShowFirma(true)}
                                className="bg-violet-600 text-white hover:bg-violet-700 text-xs"
                                disabled={!completo}
                                data-testid="rpt-approve-start-btn">
                                <Lock className="h-3 w-3 mr-1" /> Approva e Firma
                            </Button>
                        ) : (
                            <div className="flex items-center gap-2 flex-1">
                                <Input value={firmaNome} onChange={e => setFirmaNome(e.target.value)}
                                    placeholder="Nome" className="text-xs h-7 w-32" data-testid="rpt-firma-nome" />
                                <Input value={firmaRuolo} onChange={e => setFirmaRuolo(e.target.value)}
                                    placeholder="Ruolo" className="text-xs h-7 w-32" data-testid="rpt-firma-ruolo" />
                                <Button size="sm" onClick={handleApprova} disabled={approving}
                                    className="bg-violet-600 text-white hover:bg-violet-700 text-xs"
                                    data-testid="rpt-approve-confirm-btn">
                                    {approving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Lock className="h-3 w-3 mr-1" />}
                                    Firma
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => setShowFirma(false)} className="text-xs">Annulla</Button>
                            </div>
                        )}
                        {!completo && (
                            <span className="text-[10px] text-amber-600 flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" /> Completa tutte le ispezioni per approvare
                            </span>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
