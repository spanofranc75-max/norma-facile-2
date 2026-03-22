/**
 * RiesameTecnicoSection — Gate di commessa pre-produzione.
 * Checklist con auto-verifica + check manuali + firma + PDF.
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
    ShieldCheck, ShieldAlert, CheckCircle, XCircle, FileText,
    Loader2, Lock, Download, RefreshCw, Pen, Minus,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const SEZ_COLORS = {
    Contratto: 'bg-blue-100 text-blue-700',
    Progettazione: 'bg-violet-100 text-violet-700',
    Saldatura: 'bg-orange-100 text-orange-700',
    Attrezzature: 'bg-cyan-100 text-cyan-700',
    Sicurezza: 'bg-emerald-100 text-emerald-700',
    Approvvigionamento: 'bg-amber-100 text-amber-700',
};

const NORM_COLORS = {
    EN_1090: 'bg-blue-700 text-white',
    EN_13241: 'bg-indigo-600 text-white',
    GENERICA: 'bg-slate-500 text-white',
};

const NORM_LABELS = {
    EN_1090: 'EN 1090',
    EN_13241: 'EN 13241',
    GENERICA: 'Generica',
};

export default function RiesameTecnicoSection({ commessaId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [approving, setApproving] = useState(false);
    const [showFirma, setShowFirma] = useState(false);
    const [firmaNome, setFirmaNome] = useState('');
    const [firmaRuolo, setFirmaRuolo] = useState('Responsabile Qualita');
    const [noteGen, setNoteGen] = useState('');
    const [manualChecks, setManualChecks] = useState({});

    const load = useCallback(async () => {
        try {
            const res = await apiRequest(`/riesame/${commessaId}`);
            setData(res);
            setNoteGen(res.note_generali || '');
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
            await apiRequest(`/riesame/${commessaId}`, {
                method: 'POST',
                body: { checks_manuali: manualChecks, note_generali: noteGen },
            });
            toast.success('Riesame salvato');
            load();
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const handleApprova = async () => {
        if (!firmaNome.trim()) { toast.error('Inserire il nome del firmatario'); return; }
        setApproving(true);
        try {
            await apiRequest(`/riesame/${commessaId}/approva`, {
                method: 'POST',
                body: { firma_nome: firmaNome, firma_ruolo: firmaRuolo },
            });
            toast.success('Riesame approvato e firmato');
            setShowFirma(false);
            load();
        } catch (e) { toast.error(e.message); }
        finally { setApproving(false); }
    };

    const handlePdf = async () => {
        try {
            const res = await fetch(`${API}/api/riesame/${commessaId}/pdf`, { credentials: 'include' });
            if (!res.ok) { toast.error('Errore generazione PDF'); return; }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Riesame_Tecnico_${data?.numero || ''}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    if (loading) return (
        <Card className="border-gray-200"><CardContent className="flex justify-center py-6">
            <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
        </CardContent></Card>
    );

    if (!data) return null;

    const { checks, superato, n_ok, n_totale, n_applicabili, n_non_applicabili, normative_attive, approvato, firma } = data;
    const pct = n_applicabili > 0 ? Math.round(n_ok / n_applicabili * 100) : 0;

    // Group by sezione
    const sezioni = {};
    checks.forEach(c => {
        if (!sezioni[c.sezione]) sezioni[c.sezione] = [];
        sezioni[c.sezione].push(c);
    });

    return (
        <Card className={`border-2 ${approvato ? 'border-emerald-300' : superato ? 'border-blue-300' : 'border-amber-300'}`} data-testid="riesame-tecnico-section">
            <CardHeader className={`py-3 px-5 ${approvato ? 'bg-emerald-50' : 'bg-slate-50'} border-b`}>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        {approvato ? <ShieldCheck className="h-5 w-5 text-emerald-600" /> : <ShieldAlert className="h-5 w-5 text-amber-600" />}
                        Riesame Tecnico
                        {approvato ? (
                            <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px] gap-1">
                                <Lock className="w-3 h-3" /> Approvato
                            </Badge>
                        ) : (
                            <Badge className="bg-amber-100 text-amber-700 border border-amber-200 text-[10px]">
                                {n_ok}/{n_applicabili} superati ({pct}%)
                            </Badge>
                        )}
                        {(normative_attive || []).map(n => (
                            <Badge key={n} className={`text-[9px] px-1.5 py-0 ${NORM_COLORS[n] || 'bg-slate-400 text-white'}`}>
                                {NORM_LABELS[n] || n}
                            </Badge>
                        ))}
                        {n_non_applicabili > 0 && (
                            <span className="text-[10px] text-slate-400 font-normal ml-1">
                                ({n_non_applicabili} N/A)
                            </span>
                        )}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {!approvato && (
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={load} data-testid="btn-refresh-riesame">
                                <RefreshCw className="w-3 h-3" /> Aggiorna
                            </Button>
                        )}
                        <Button variant="outline" size="sm" className="h-7 text-xs gap-1" onClick={handlePdf} data-testid="btn-pdf-riesame">
                            <Download className="w-3 h-3" /> PDF
                        </Button>
                    </div>
                </div>
                {approvato && firma && (
                    <p className="text-[10px] text-emerald-600 mt-1">
                        Firmato da <strong>{firma.nome}</strong> ({firma.ruolo}) il {firma.timestamp?.slice(0, 10)}
                    </p>
                )}
            </CardHeader>
            <CardContent className="p-0">
                {/* Progress bar */}
                <div className="px-5 py-2 border-b border-slate-100">
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${pct === 100 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-400' : 'bg-red-400'}`}
                            style={{ width: `${pct}%` }} />
                    </div>
                </div>

                {/* Checks grouped by sezione */}
                <div className="divide-y divide-slate-100">
                    {Object.entries(sezioni).map(([sez, items]) => (
                        <div key={sez} className="px-5 py-2.5">
                            <div className="flex items-center gap-2 mb-2">
                                <Badge className={`text-[10px] px-2 py-0.5 ${SEZ_COLORS[sez] || 'bg-slate-100 text-slate-600'}`}>{sez}</Badge>
                            </div>
                            <div className="space-y-1.5">
                                {items.map(ck => {
                                    const isNA = ck.applicabile === false;
                                    return (
                                    <div key={ck.id}
                                        className={`flex items-start gap-2.5 ${isNA ? 'opacity-40' : ''}`}
                                        data-testid={`check-${ck.id}`}>
                                        {isNA ? (
                                            <Minus className="w-4 h-4 text-slate-300 mt-0.5 shrink-0" />
                                        ) : ck.auto ? (
                                            ck.esito
                                                ? <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                                                : <XCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                                        ) : (
                                            <Checkbox
                                                checked={manualChecks[ck.id] || false}
                                                onCheckedChange={v => !approvato && setManualChecks(prev => ({ ...prev, [ck.id]: v }))}
                                                disabled={approvato}
                                                className="mt-0.5"
                                                data-testid={`manual-check-${ck.id}`}
                                            />
                                        )}
                                        <div className="flex-1 min-w-0">
                                            <div className={`text-xs font-medium ${isNA ? 'text-slate-400 line-through' : 'text-slate-700'}`}>
                                                {ck.label}
                                                {isNA && <span className="ml-1.5 text-[9px] font-normal no-underline text-slate-300">(N/A)</span>}
                                            </div>
                                            <div className="text-[10px] text-slate-400">{ck.desc}</div>
                                            {isNA && ck.nota && (
                                                <div className="text-[10px] mt-0.5 text-slate-300 italic">{ck.nota}</div>
                                            )}
                                            {!isNA && ck.valore && (
                                                <div className={`text-[10px] mt-0.5 ${ck.esito ? 'text-emerald-600' : 'text-red-500'}`}>
                                                    {ck.valore}{ck.nota ? ` — ${ck.nota}` : ''}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Notes + Actions */}
                {!approvato && (
                    <div className="px-5 py-3 border-t border-slate-100 space-y-3">
                        <div>
                            <label className="text-xs font-medium text-slate-600">Note generali</label>
                            <Textarea value={noteGen} onChange={e => setNoteGen(e.target.value)}
                                placeholder="Osservazioni, deroghe, condizioni particolari..."
                                rows={2} className="mt-1 text-sm" data-testid="note-riesame" />
                        </div>
                        <div className="flex items-center gap-2">
                            <Button size="sm" variant="outline" className="h-8 text-xs gap-1"
                                onClick={handleSave} disabled={saving} data-testid="btn-save-riesame">
                                {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
                                Salva bozza
                            </Button>
                            {superato && !showFirma && (
                                <Button size="sm" className="h-8 text-xs gap-1 bg-emerald-600 hover:bg-emerald-700"
                                    onClick={() => setShowFirma(true)} data-testid="btn-show-firma">
                                    <Pen className="w-3 h-3" /> Firma e Approva
                                </Button>
                            )}
                        </div>

                        {showFirma && (
                            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 space-y-2" data-testid="firma-panel">
                                <p className="text-xs font-semibold text-emerald-800">Firma digitale — Approvazione definitiva</p>
                                <p className="text-[10px] text-emerald-600">Una volta firmato, il riesame diventa immutabile e la commessa potra avviare la produzione.</p>
                                <div className="grid grid-cols-2 gap-2">
                                    <Input value={firmaNome} onChange={e => setFirmaNome(e.target.value)}
                                        placeholder="Nome e Cognome" className="h-8 text-xs" data-testid="firma-nome" />
                                    <Input value={firmaRuolo} onChange={e => setFirmaRuolo(e.target.value)}
                                        placeholder="Ruolo" className="h-8 text-xs" data-testid="firma-ruolo" />
                                </div>
                                <div className="flex gap-2">
                                    <Button size="sm" className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 gap-1"
                                        onClick={handleApprova} disabled={approving} data-testid="btn-approva-riesame">
                                        {approving ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                                        Conferma Approvazione
                                    </Button>
                                    <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowFirma(false)}>
                                        Annulla
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
