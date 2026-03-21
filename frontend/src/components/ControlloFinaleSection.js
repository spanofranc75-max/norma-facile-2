/**
 * ControlloFinaleSection — Checklist pre-spedizione EN 1090-2:2024.
 * 3 macro-aree: Visual Testing (ISO 5817-C), Dimensionale (B6/B8), Compliance (CE/DOP/colate).
 * Verifica automatica + check manuali + firma + approvazione bloccante.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Checkbox } from './ui/checkbox';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { toast } from 'sonner';
import {
    ClipboardCheck, CheckCircle, XCircle, Loader2, Lock,
    RefreshCw, Pen, Eye, Ruler, ShieldCheck, AlertTriangle,
} from 'lucide-react';

const AREA_CONFIG = {
    'Visual Testing': { icon: Eye, color: 'bg-violet-100 text-violet-700', border: 'border-violet-200' },
    'Dimensionale': { icon: Ruler, color: 'bg-cyan-100 text-cyan-700', border: 'border-cyan-200' },
    'Compliance': { icon: ShieldCheck, color: 'bg-emerald-100 text-emerald-700', border: 'border-emerald-200' },
};

export default function ControlloFinaleSection({ commessaId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [approving, setApproving] = useState(false);
    const [showFirma, setShowFirma] = useState(false);
    const [firmaNome, setFirmaNome] = useState('');
    const [firmaRuolo, setFirmaRuolo] = useState('Responsabile Qualita');
    const [noteGen, setNoteGen] = useState('');
    const [noteVt, setNoteVt] = useState('');
    const [noteDim, setNoteDim] = useState('');
    const [manualChecks, setManualChecks] = useState({});

    const load = useCallback(async () => {
        try {
            const res = await apiRequest(`/controllo-finale/${commessaId}`);
            setData(res);
            setNoteGen(res.note_generali || '');
            setNoteVt(res.note_vt || '');
            setNoteDim(res.note_dim || '');
            const mc = {};
            res.checks?.filter(c => !c.auto).forEach(c => { mc[c.id] = c.esito; });
            setManualChecks(mc);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { load(); }, [load]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await apiRequest(`/controllo-finale/${commessaId}`, {
                method: 'POST',
                body: { checks_manuali: manualChecks, note_generali: noteGen, note_vt: noteVt, note_dim: noteDim },
            });
            toast.success('Controllo finale salvato');
            load();
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const handleApprova = async () => {
        if (!firmaNome.trim()) { toast.error('Inserisci il nome per la firma'); return; }
        setApproving(true);
        try {
            await apiRequest(`/controllo-finale/${commessaId}/approva`, {
                method: 'POST',
                body: { firma_nome: firmaNome, firma_ruolo: firmaRuolo },
            });
            toast.success('Controllo finale approvato e firmato');
            setShowFirma(false);
            load();
        } catch (e) { toast.error(e.message); }
        finally { setApproving(false); }
    };

    const toggleManual = (id) => {
        setManualChecks(prev => ({ ...prev, [id]: !prev[id] }));
    };

    if (loading) {
        return (
            <Card className="border-gray-200">
                <CardContent className="py-8 flex items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-emerald-500" />
                </CardContent>
            </Card>
        );
    }

    if (!data) return null;

    const { checks, superato, n_ok, n_totale, approvato, firma, areas } = data;
    const isLocked = approvato;

    // Group checks by area
    const grouped = {};
    checks.forEach(c => {
        if (!grouped[c.area]) grouped[c.area] = [];
        grouped[c.area].push(c);
    });

    return (
        <Card className="border-gray-200" data-testid="controllo-finale-section">
            <CardHeader className="bg-gradient-to-r from-emerald-700 to-teal-600 py-2.5 px-4 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                        <ClipboardCheck className="h-3.5 w-3.5" /> Controllo Finale Pre-Spedizione
                        <Badge className={`text-[10px] ml-1 ${superato ? 'bg-white/20 text-white' : 'bg-red-400/30 text-red-100'}`}>
                            {n_ok}/{n_totale}
                        </Badge>
                        {isLocked && <Lock className="h-3 w-3 text-white/70" />}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Button size="sm" variant="ghost" onClick={load} className="text-white hover:bg-white/10 h-7 w-7 p-0" data-testid="cf-refresh">
                            <RefreshCw className="h-3 w-3" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-3">
                {/* Area progress bars */}
                <div className="grid grid-cols-3 gap-2" data-testid="cf-areas-stats">
                    {Object.entries(AREA_CONFIG).map(([area, cfg]) => {
                        const AIcon = cfg.icon;
                        const aData = areas?.[area] || { totale: 0, ok: 0 };
                        const pct = aData.totale > 0 ? Math.round((aData.ok / aData.totale) * 100) : 0;
                        const allOk = aData.ok === aData.totale && aData.totale > 0;
                        return (
                            <div key={area} className={`p-2 rounded-lg border ${cfg.border} ${allOk ? 'bg-emerald-50' : 'bg-white'}`}>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <AIcon className={`h-3 w-3 ${allOk ? 'text-emerald-600' : ''}`} />
                                    <span className="text-[10px] font-semibold text-slate-700">{area}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                                        <div className={`h-1.5 rounded-full transition-all ${allOk ? 'bg-emerald-500' : 'bg-amber-400'}`}
                                             style={{ width: `${pct}%` }} />
                                    </div>
                                    <span className="text-[9px] font-mono font-semibold text-slate-500">{aData.ok}/{aData.totale}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Approved banner */}
                {isLocked && firma && (
                    <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700 flex items-center gap-2" data-testid="cf-approved-banner">
                        <Lock className="h-3.5 w-3.5" />
                        <div>
                            <span className="font-semibold">Controllo Finale Approvato</span>
                            <span className="ml-2 text-emerald-600">{firma.nome} — {firma.ruolo} — {firma.timestamp?.slice(0, 10)}</span>
                        </div>
                    </div>
                )}

                {/* Checklist per area */}
                {Object.entries(grouped).map(([area, areaChecks]) => {
                    const cfg = AREA_CONFIG[area] || {};
                    return (
                        <div key={area} className="space-y-1.5" data-testid={`cf-area-${area.toLowerCase().replace(/\s/g, '-')}`}>
                            <div className="flex items-center gap-2">
                                <Badge className={`${cfg.color} text-[10px]`}>{area}</Badge>
                            </div>
                            {areaChecks.map(ck => {
                                const isManual = !ck.auto;
                                const checked = isManual ? !!manualChecks[ck.id] : ck.esito;
                                return (
                                    <div key={ck.id} className={`flex items-start gap-2.5 p-2 rounded-lg border transition-colors
                                        ${checked ? 'bg-emerald-50/50 border-emerald-200' : 'bg-white border-slate-200'}`}
                                         data-testid={`cf-check-${ck.id}`}>
                                        {isManual ? (
                                            <Checkbox
                                                checked={checked}
                                                onCheckedChange={() => !isLocked && toggleManual(ck.id)}
                                                disabled={isLocked}
                                                className="mt-0.5"
                                                data-testid={`cf-toggle-${ck.id}`}
                                            />
                                        ) : (
                                            <div className="mt-0.5">
                                                {checked ? (
                                                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                                                ) : (
                                                    <XCircle className="h-4 w-4 text-red-400" />
                                                )}
                                            </div>
                                        )}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-1.5">
                                                <span className={`text-xs font-medium ${checked ? 'text-emerald-700' : 'text-slate-700'}`}>
                                                    {ck.label}
                                                </span>
                                                {ck.auto && <Badge className="bg-slate-100 text-slate-500 text-[8px]">auto</Badge>}
                                            </div>
                                            <p className="text-[10px] text-slate-400 mt-0.5">{ck.desc}</p>
                                            {ck.auto && ck.valore && (
                                                <p className={`text-[10px] mt-0.5 font-medium ${checked ? 'text-emerald-600' : 'text-amber-600'}`}>
                                                    {ck.valore}
                                                </p>
                                            )}
                                            {ck.auto && ck.nota && !checked && (
                                                <p className="text-[10px] text-red-500 mt-0.5 flex items-center gap-1">
                                                    <AlertTriangle className="h-2.5 w-2.5" /> {ck.nota}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    );
                })}

                {/* Notes */}
                {!isLocked && (
                    <div className="space-y-2 pt-1">
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Note VT</label>
                            <Textarea value={noteVt} onChange={e => setNoteVt(e.target.value)}
                                placeholder="Annotazioni controllo visivo..." className="text-xs h-12 mt-0.5"
                                data-testid="cf-note-vt" />
                        </div>
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Note Dimensionale</label>
                            <Textarea value={noteDim} onChange={e => setNoteDim(e.target.value)}
                                placeholder="Annotazioni controllo dimensionale..." className="text-xs h-12 mt-0.5"
                                data-testid="cf-note-dim" />
                        </div>
                        <div>
                            <label className="text-[10px] font-medium text-slate-500">Note generali</label>
                            <Textarea value={noteGen} onChange={e => setNoteGen(e.target.value)}
                                placeholder="Note generali pre-spedizione..." className="text-xs h-12 mt-0.5"
                                data-testid="cf-note-gen" />
                        </div>
                    </div>
                )}

                {/* Actions */}
                {!isLocked && (
                    <div className="flex items-center gap-2 pt-1">
                        <Button size="sm" variant="outline" onClick={handleSave} disabled={saving}
                            className="text-xs" data-testid="cf-save-btn">
                            {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Pen className="h-3 w-3 mr-1" />}
                            Salva bozza
                        </Button>
                        {!showFirma ? (
                            <Button size="sm" onClick={() => setShowFirma(true)}
                                className="bg-emerald-600 text-white hover:bg-emerald-700 text-xs"
                                disabled={!superato}
                                data-testid="cf-approve-start-btn">
                                <ShieldCheck className="h-3 w-3 mr-1" /> Approva e Firma
                            </Button>
                        ) : (
                            <div className="flex items-center gap-2 flex-1">
                                <Input value={firmaNome} onChange={e => setFirmaNome(e.target.value)}
                                    placeholder="Nome completo" className="text-xs h-8 w-36"
                                    data-testid="cf-firma-nome" />
                                <Input value={firmaRuolo} onChange={e => setFirmaRuolo(e.target.value)}
                                    placeholder="Ruolo" className="text-xs h-8 w-32"
                                    data-testid="cf-firma-ruolo" />
                                <Button size="sm" onClick={handleApprova} disabled={approving}
                                    className="bg-emerald-600 text-white hover:bg-emerald-700 text-xs"
                                    data-testid="cf-approve-confirm-btn">
                                    {approving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Lock className="h-3 w-3 mr-1" />}
                                    Firma
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => setShowFirma(false)} className="text-xs">
                                    Annulla
                                </Button>
                            </div>
                        )}
                        {!superato && (
                            <span className="text-[10px] text-amber-600 flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" /> Completa tutti i check per approvare
                            </span>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
