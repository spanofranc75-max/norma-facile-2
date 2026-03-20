/**
 * SALSection — Stato Avanzamento Lavori e gestione acconti.
 * Calcola il SAL dall'avanzamento reale (ore, fasi, conto lavoro).
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { TrendingUp, Receipt, Plus, Loader2, FileText } from 'lucide-react';

function ProgressBar({ label, value, color = 'bg-blue-600' }) {
    return (
        <div className="space-y-0.5">
            <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-500">{label}</span>
                <span className="font-semibold text-slate-700">{value}%</span>
            </div>
            <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.min(value, 100)}%` }} />
            </div>
        </div>
    );
}

export default function SALSection({ commessaId, onRefresh }) {
    const [sal, setSal] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showAcconto, setShowAcconto] = useState(false);
    const [percentuale, setPercentuale] = useState('');
    const [importo, setImporto] = useState('');
    const [descrizione, setDescrizione] = useState('');
    const [creating, setCreating] = useState(false);
    const [generatingInv, setGeneratingInv] = useState(null);

    const fetchSAL = useCallback(async () => {
        try {
            const data = await apiRequest(`/commesse/${commessaId}/sal`);
            setSal(data);
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { fetchSAL(); }, [fetchSAL]);

    const handleCreateAcconto = async () => {
        const pct = parseFloat(percentuale);
        if (!pct || pct <= 0 || pct > 100) { toast.error('Inserisci una percentuale valida (1-100)'); return; }
        setCreating(true);
        try {
            const body = { percentuale: pct, descrizione };
            if (importo) body.importo = parseFloat(importo);
            const res = await apiRequest(`/commesse/${commessaId}/sal/acconto`, { method: 'POST', body });
            toast.success(res.message);
            setShowAcconto(false);
            setPercentuale('');
            setImporto('');
            setDescrizione('');
            fetchSAL();
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
        finally { setCreating(false); }
    };

    const handleGeneraFattura = async (accontoId) => {
        setGeneratingInv(accontoId);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/sal/acconto/${accontoId}/fattura`, { method: 'POST' });
            toast.success(res.message);
            fetchSAL();
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
        finally { setGeneratingInv(null); }
    };

    const fmtEur = (v) => typeof v === 'number' ? v.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' }) : '-';

    if (loading) return <Card className="border-emerald-200"><CardContent className="py-6 text-center text-xs text-slate-400"><Loader2 className="h-4 w-4 animate-spin inline mr-1" />Calcolo SAL...</CardContent></Card>;

    return (
        <Card className="border-emerald-200" data-testid="sal-section">
            <CardHeader className="bg-emerald-50 border-b border-emerald-200 py-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2 text-emerald-800">
                        <TrendingUp className="h-4 w-4" /> SAL & Acconti
                    </CardTitle>
                    <Button size="sm" variant="outline" className="h-7 text-xs border-emerald-300 text-emerald-700" onClick={() => setShowAcconto(true)} data-testid="btn-new-acconto">
                        <Plus className="h-3 w-3 mr-1" /> Nuovo Acconto
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-4">
                {sal && (
                    <>
                        {/* SAL Overview */}
                        <div className="bg-white border rounded-lg p-3 space-y-2">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-slate-600">Avanzamento Complessivo</span>
                                <span className="text-lg font-bold text-emerald-700" data-testid="sal-percentage">{sal.sal_percentuale}%</span>
                            </div>
                            <ProgressBar label={`Ore (${sal.ore_lavorate}h / ${sal.ore_preventivate}h)`} value={sal.avanzamento_ore_pct} color="bg-blue-600" />
                            <ProgressBar label={`Fasi (${sal.fasi_completate} / ${sal.fasi_totali})`} value={sal.avanzamento_fasi_pct} color="bg-violet-600" />
                            {sal.cl_totali > 0 && (
                                <ProgressBar label={`C/Lavoro (${sal.cl_rientrati} / ${sal.cl_totali})`} value={sal.avanzamento_cl_pct} color="bg-amber-600" />
                            )}
                        </div>

                        {/* Financial Summary */}
                        <div className="grid grid-cols-3 gap-2">
                            <div className="text-center bg-slate-50 rounded p-2 border">
                                <p className="text-[10px] text-slate-500">Valore Commessa</p>
                                <p className="text-xs font-bold text-slate-800">{fmtEur(sal.importo_commessa)}</p>
                            </div>
                            <div className="text-center bg-emerald-50 rounded p-2 border border-emerald-200">
                                <p className="text-[10px] text-emerald-600">Valore SAL</p>
                                <p className="text-xs font-bold text-emerald-800">{fmtEur(sal.valore_sal)}</p>
                            </div>
                            <div className="text-center bg-blue-50 rounded p-2 border border-blue-200">
                                <p className="text-[10px] text-blue-600">Residuo Fatturabile</p>
                                <p className="text-xs font-bold text-blue-800">{fmtEur(sal.residuo_fatturabile)}</p>
                            </div>
                        </div>

                        {/* Acconti List */}
                        {sal.acconti?.length > 0 && (
                            <div>
                                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                                    Acconti emessi ({sal.acconti.length}) — Totale: {fmtEur(sal.totale_accontato)} ({sal.percentuale_accontata}%)
                                </p>
                                <div className="space-y-1.5">
                                    {sal.acconti.map(a => (
                                        <div key={a.acconto_id} className="flex items-center justify-between p-2 border rounded bg-white text-xs" data-testid={`acconto-${a.acconto_id}`}>
                                            <div>
                                                <span className="font-semibold text-slate-700">SAL n.{a.numero_progressivo}</span>
                                                <span className="text-slate-400 ml-2">{a.percentuale}%</span>
                                                <span className="font-bold text-slate-800 ml-2">{fmtEur(a.importo)}</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                {a.fattura_id ? (
                                                    <Badge variant="outline" className="text-[9px] bg-emerald-50 text-emerald-700 border-emerald-300">
                                                        <FileText className="h-2.5 w-2.5 mr-0.5" /> {a.fattura_numero}
                                                    </Badge>
                                                ) : (
                                                    <Button size="sm" variant="outline" className="h-6 text-[10px] border-emerald-300 text-emerald-700" onClick={() => handleGeneraFattura(a.acconto_id)} disabled={generatingInv === a.acconto_id} data-testid={`btn-fattura-${a.acconto_id}`}>
                                                        {generatingInv === a.acconto_id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Receipt className="h-3 w-3 mr-0.5" />}
                                                        Genera Fattura
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </>
                )}
            </CardContent>

            {/* Create Acconto Dialog */}
            <Dialog open={showAcconto} onOpenChange={setShowAcconto}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle className="text-base">Nuovo Acconto SAL</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label className="text-xs">Percentuale di avanzamento *</Label>
                            <div className="flex items-center gap-2">
                                <Input type="number" value={percentuale} onChange={e => setPercentuale(e.target.value)} placeholder="30" className="h-8 text-sm" min="1" max="100" data-testid="input-sal-percentuale" />
                                <span className="text-sm text-slate-500 font-bold">%</span>
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs">Importo (opzionale, calcolato automaticamente)</Label>
                            <Input type="number" value={importo} onChange={e => setImporto(e.target.value)} placeholder="Auto" className="h-8 text-sm" data-testid="input-sal-importo" />
                        </div>
                        <div>
                            <Label className="text-xs">Descrizione</Label>
                            <Input value={descrizione} onChange={e => setDescrizione(e.target.value)} placeholder="Es: Primo SAL — strutture principali" className="h-8 text-sm" />
                        </div>
                    </div>
                    <DialogFooter className="mt-3">
                        <Button variant="outline" size="sm" onClick={() => setShowAcconto(false)} className="text-xs">Annulla</Button>
                        <Button size="sm" onClick={handleCreateAcconto} disabled={creating} className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="btn-confirm-acconto">
                            {creating ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Receipt className="h-3 w-3 mr-1" />}
                            Crea Acconto
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
