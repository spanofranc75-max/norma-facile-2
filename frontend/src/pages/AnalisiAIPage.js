/**
 * AnalisiAIPage — Analisi AI del preventivo con editing pesi in tempo reale.
 * L'utente puo correggere manualmente i pesi estratti dall'AI e vedere il prezzo aggiornarsi live.
 * Include anche il confronto con un preventivo manuale.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import {
    ArrowLeft, Brain, Save, Weight, Euro, Clock, Loader2,
    BarChart3, RefreshCw, Pencil, Check, Target,
} from 'lucide-react';

const fmtEur = (v) => typeof v === 'number' ? v.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' }) : '-';
const fmtKg = (v) => typeof v === 'number' ? v.toLocaleString('it-IT', { maximumFractionDigits: 1 }) + ' kg' : '-';

/* ── Material row with inline weight editing ── */
function MaterialRow({ item, idx, onUpdate, prezzi }) {
    const [editing, setEditing] = useState(false);
    const [kgVal, setKgVal] = useState(item.peso_kg);

    const prezzo_unitario = useMemo(() => {
        const d = (item.descrizione || item.description || '').toUpperCase();
        if (d.includes('BULLON') || d.includes('M16') || d.includes('M20')) return prezzi.bulloneria || 4.50;
        if (d.includes('PIASTR') || d.includes('LAMIER')) return prezzi.piastre || 1.30;
        if (d.includes('ZINC')) return prezzi.zincatura_kg || 0.45;
        return prezzi.S275JR || prezzi.default || 1.15;
    }, [item, prezzi]);

    const costo = (kgVal || 0) * prezzo_unitario;

    const save = () => {
        const newKg = parseFloat(kgVal) || 0;
        setEditing(false);
        onUpdate(idx, newKg);
    };

    return (
        <tr className="border-b border-zinc-800/50 hover:bg-zinc-800/20 group" data-testid={`mat-row-${idx}`}>
            <td className="py-2 px-3 text-sm text-zinc-300 max-w-[280px]">{item.descrizione || item.description}</td>
            <td className="py-2 px-3 text-sm text-zinc-400">{item.profilo || '-'}</td>
            <td className="py-2 px-3 text-sm text-zinc-400 text-center">{item.quantita || item.quantity || 1}</td>
            <td className="py-2 px-3 text-right">
                {editing ? (
                    <div className="flex items-center gap-1 justify-end">
                        <Input
                            type="number" step="0.1" autoFocus
                            value={kgVal}
                            onChange={e => setKgVal(parseFloat(e.target.value) || 0)}
                            onKeyDown={e => e.key === 'Enter' && save()}
                            className="w-24 h-7 text-xs font-mono text-right bg-zinc-800 border-indigo-500"
                            data-testid={`edit-peso-${idx}`}
                        />
                        <button onClick={save} className="text-emerald-400 hover:text-emerald-300" data-testid={`save-peso-${idx}`}>
                            <Check className="w-4 h-4" />
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={() => { setKgVal(item.peso_kg); setEditing(true); }}
                        className="font-mono text-sm text-amber-300 hover:text-amber-200 flex items-center gap-1 justify-end w-full group"
                        data-testid={`btn-edit-peso-${idx}`}
                    >
                        {fmtKg(item.peso_kg)}
                        <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500" />
                    </button>
                )}
            </td>
            <td className="py-2 px-3 text-right text-xs font-mono text-zinc-500">{fmtEur(prezzo_unitario)}/kg</td>
            <td className="py-2 px-3 text-right text-sm font-mono text-blue-300">{fmtEur(costo)}</td>
        </tr>
    );
}

export default function AnalisiAIPage() {
    const { prevId } = useParams();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [preventivo, setPreventivo] = useState(null);
    const [materiali, setMateriali] = useState([]);
    const [prezzi, setPrezzi] = useState({});
    const [margini, setMargini] = useState({ materiali: 15, manodopera: 40, conto_lavoro: 10 });
    const [oreTotali, setOreTotali] = useState(0);
    const [costoOrario, setCostoOrario] = useState(35);
    const [saving, setSaving] = useState(false);
    const [confronto, setConfronto] = useState(null);
    const [prevList, setPrevList] = useState([]);
    const [manPrevId, setManPrevId] = useState(searchParams.get('man') || '');

    const [analyzing, setAnalyzing] = useState(false);

    // AI analysis of preventivo lines
    const runAIAnalysis = useCallback(async (lines) => {
        setAnalyzing(true);
        try {
            const result = await apiRequest('/preventivatore/analizza-righe', {
                method: 'POST',
                body: { lines },
            });
            const aiMats = (result?.materiali || []).map((m, i) => ({
                id: i,
                descrizione: m.descrizione || m.description || lines[i]?.description || '',
                profilo: m.profilo || '-',
                quantita: m.quantita || m.quantity || 1,
                peso_kg: m.peso_calcolato_kg || m.peso_stimato_kg || 0,
                prezzo_base: lines[i]?.unit_price || 0,
                tipo: m.tipo || 'altro',
            }));
            setMateriali(aiMats);
            toast.success(`Analisi AI completata: ${result?.peso_totale_calcolato_kg || 0} kg stimati`);
            return aiMats;
        } catch (e) {
            toast.error('Analisi AI fallita: ' + e.message);
            return null;
        } finally { setAnalyzing(false); }
    }, []);

    // Load preventivo + prezzi
    useEffect(() => {
        async function load() {
            try {
                const [prev, prezziRes, list] = await Promise.all([
                    apiRequest(`/preventivi/${prevId}`),
                    apiRequest('/preventivatore/prezzi-storici'),
                    apiRequest('/preventivi/'),
                ]);
                setPreventivo(prev);
                setPrezzi(prezziRes?.prezzi || {});
                const items = list?.preventivi || list || [];
                setPrevList(items);

                // Extract lines excluding manodopera/zincatura for material analysis
                const lines = prev?.lines || [];
                const matLines = lines.filter(l => {
                    const d = (l.description || '').toLowerCase();
                    return !d.includes('manodopera') && !d.includes('zincatura');
                });

                // Use AI to extract weights (the regex fallback is unreliable)
                const aiResult = await runAIAnalysis(matLines);

                if (!aiResult) {
                    // Fallback: regex extraction (will likely give 0s)
                    const mats = matLines.map((l, i) => ({
                        id: i,
                        descrizione: l.description,
                        profilo: extractProfilo(l.description),
                        quantita: l.quantity,
                        peso_kg: extractPeso(l.description) || 0,
                        prezzo_base: l.unit_price,
                    }));
                    setMateriali(mats);
                }

                // Extract ore
                const oreLine = lines.find(l => (l.description || '').toLowerCase().includes('manodopera'));
                if (oreLine) setOreTotali(oreLine.quantity || 0);
                else setOreTotali(prev?.ore_stimate || 0);
            } catch (e) {
                toast.error('Errore caricamento: ' + e.message);
            } finally { setLoading(false); }
        }
        load();
    }, [prevId, runAIAnalysis]);

    function extractProfilo(desc) {
        if (!desc) return '-';
        const m = desc.match(/(IPE|HEA|HEB|UPN|TUBO)\s*\d+/i);
        return m ? m[0] : '-';
    }

    function extractPeso(desc) {
        if (!desc) return 0;
        const m = desc.match(/([\d.,]+)\s*kg/i);
        return m ? parseFloat(m[1].replace(',', '.')) : 0;
    }

    const handleUpdatePeso = useCallback((idx, newKg) => {
        setMateriali(prev => prev.map((m, i) => i === idx ? { ...m, peso_kg: newKg } : m));
    }, []);

    // Real-time calculations
    const calcoli = useMemo(() => {
        let pesoTotale = 0;
        let costoMateriali = 0;

        materiali.forEach(m => {
            const d = (m.descrizione || '').toUpperCase();
            let pu = prezzi.S275JR || 1.15;
            if (d.includes('BULLON') || d.includes('M16') || d.includes('M20')) pu = prezzi.bulloneria || 4.50;
            else if (d.includes('PIASTR') || d.includes('LAMIER')) pu = prezzi.piastre || 1.30;
            else if (d.includes('ZINC')) pu = prezzi.zincatura_kg || 0.45;

            pesoTotale += m.peso_kg || 0;
            costoMateriali += (m.peso_kg || 0) * pu;
        });

        const costoMano = oreTotali * costoOrario;
        const costoZinc = pesoTotale * (prezzi.zincatura_kg || 0.45);

        const matVendita = costoMateriali * (1 + margini.materiali / 100);
        const manoVendita = costoMano * (1 + margini.manodopera / 100);
        const clVendita = costoZinc * (1 + margini.conto_lavoro / 100);
        const subtotale = matVendita + manoVendita + clVendita;

        return {
            pesoTotale: Math.round(pesoTotale * 10) / 10,
            costoMateriali: Math.round(costoMateriali * 100) / 100,
            costoMano: Math.round(costoMano * 100) / 100,
            costoZinc: Math.round(costoZinc * 100) / 100,
            matVendita: Math.round(matVendita * 100) / 100,
            manoVendita: Math.round(manoVendita * 100) / 100,
            clVendita: Math.round(clVendita * 100) / 100,
            subtotale: Math.round(subtotale * 100) / 100,
            iva: Math.round(subtotale * 0.22 * 100) / 100,
            totale: Math.round(subtotale * 1.22 * 100) / 100,
        };
    }, [materiali, oreTotali, costoOrario, margini, prezzi]);

    // Save updated preventivo
    const handleSave = async () => {
        setSaving(true);
        try {
            const lines = materiali.map((m, i) => {
                const d = (m.descrizione || '').toUpperCase();
                let pu = prezzi.S275JR || 1.15;
                if (d.includes('BULLON') || d.includes('M16') || d.includes('M20')) pu = prezzi.bulloneria || 4.50;
                else if (d.includes('PIASTR') || d.includes('LAMIER')) pu = prezzi.piastre || 1.30;
                else if (d.includes('ZINC')) pu = prezzi.zincatura_kg || 0.45;

                const costo = (m.peso_kg || 0) * pu;
                const vendita = costo * (1 + margini.materiali / 100);
                return {
                    line_id: `ai_${i + 1}`,
                    description: `${m.descrizione || ''} (${m.peso_kg?.toFixed(0) || 0} kg)`,
                    quantity: m.quantita || 1,
                    unit: 'pz',
                    unit_price: Math.round(vendita / (m.quantita || 1) * 100) / 100,
                    vat_rate: '22',
                    line_total: Math.round(vendita * 100) / 100,
                    sconto_1: 0, sconto_2: 0,
                };
            });

            // Add manodopera line
            lines.push({
                line_id: 'ai_mano',
                description: `Manodopera specializzata (${oreTotali}h officina+montaggio)`,
                quantity: oreTotali,
                unit: 'ore',
                unit_price: Math.round(calcoli.manoVendita / oreTotali * 100) / 100,
                vat_rate: '22',
                line_total: calcoli.manoVendita,
                sconto_1: 0, sconto_2: 0,
            });

            // Add zincatura line
            lines.push({
                line_id: 'ai_zinc',
                description: `Zincatura a caldo (${calcoli.pesoTotale.toFixed(0)} kg)`,
                quantity: 1,
                unit: 'a corpo',
                unit_price: calcoli.clVendita,
                vat_rate: '22',
                line_total: calcoli.clVendita,
                sconto_1: 0, sconto_2: 0,
            });

            await apiRequest(`/preventivi/${prevId}`, {
                method: 'PUT',
                body: JSON.stringify({
                    lines,
                    totals: {
                        subtotal: calcoli.subtotale,
                        total_vat: calcoli.iva,
                        total: calcoli.totale,
                        total_document: calcoli.totale,
                        line_count: lines.length,
                    },
                    peso_totale_kg: calcoli.pesoTotale,
                    ore_stimate: oreTotali,
                    predittivo_data: {
                        riepilogo: {
                            peso_totale_calcolato_kg: calcoli.pesoTotale,
                            costo_materiali: calcoli.costoMateriali,
                            materiali_vendita: calcoli.matVendita,
                            costo_manodopera: calcoli.costoMano,
                            manodopera_vendita: calcoli.manoVendita,
                            costo_cl: calcoli.costoZinc,
                            cl_vendita: calcoli.clVendita,
                            ore_stimate: oreTotali,
                        },
                    },
                }),
            });
            toast.success('Preventivo aggiornato con i pesi corretti');
        } catch (e) {
            toast.error('Errore salvataggio: ' + e.message);
        } finally { setSaving(false); }
    };

    // Run confronto
    const runConfronto = async () => {
        if (!manPrevId) { toast.error('Seleziona un preventivo manuale per il confronto'); return; }
        try {
            const res = await apiRequest('/preventivatore/confronta', {
                method: 'POST',
                body: JSON.stringify({ preventivo_ai_id: prevId, preventivo_manuale_id: manPrevId }),
            });
            setConfronto(res);
        } catch (e) { toast.error('Errore confronto: ' + e.message); }
    };

    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            </div>
        </DashboardLayout>
    );

    return (
        <DashboardLayout>
            <div className="max-w-6xl mx-auto space-y-4 p-4" data-testid="analisi-ai-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="back-btn">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                        <div>
                            <h1 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
                                <Brain className="w-5 h-5 text-indigo-400" />
                                Analisi AI — {preventivo?.number || prevId}
                            </h1>
                            <p className="text-sm text-zinc-500">{preventivo?.subject || ''}</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button onClick={() => {
                            const lines = (preventivo?.lines || []).filter(l => {
                                const d = (l.description || '').toLowerCase();
                                return !d.includes('manodopera') && !d.includes('zincatura');
                            });
                            runAIAnalysis(lines);
                        }} disabled={analyzing}
                            variant="outline" className="border-indigo-600 text-indigo-400 hover:bg-indigo-950" data-testid="reanalyze-btn">
                            {analyzing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                            Ricalcola AI
                        </Button>
                        <Button onClick={handleSave} disabled={saving}
                            className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-analysis-btn">
                            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                            Salva Correzioni
                        </Button>
                    </div>
                </div>

                {/* AI Analysis Status */}
                {analyzing && (
                    <Card className="bg-indigo-950 border-indigo-700">
                        <CardContent className="py-3 flex items-center gap-3">
                            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                            <span className="text-sm text-indigo-300">Analisi AI in corso — estrazione profili e pesi dai materiali...</span>
                        </CardContent>
                    </Card>
                )}

                {/* Live KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardContent className="pt-3 pb-3 text-center">
                            <Weight className="w-5 h-5 mx-auto text-zinc-500 mb-1" />
                            <div className="text-2xl font-bold text-amber-300 font-mono" data-testid="live-peso">{fmtKg(calcoli.pesoTotale)}</div>
                            <span className="text-[10px] text-zinc-500">Peso Totale</span>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardContent className="pt-3 pb-3 text-center">
                            <Clock className="w-5 h-5 mx-auto text-zinc-500 mb-1" />
                            <div className="flex items-center justify-center gap-1">
                                <Input
                                    type="number" step="1" value={oreTotali}
                                    onChange={e => setOreTotali(parseFloat(e.target.value) || 0)}
                                    className="w-20 h-8 text-xl font-bold font-mono text-center bg-zinc-800 border-zinc-700 text-blue-300"
                                    data-testid="edit-ore"
                                />
                                <span className="text-xl font-bold text-blue-300">h</span>
                            </div>
                            <span className="text-[10px] text-zinc-500">Ore Manodopera</span>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardContent className="pt-3 pb-3 text-center">
                            <Euro className="w-5 h-5 mx-auto text-zinc-500 mb-1" />
                            <div className="text-2xl font-bold text-emerald-300 font-mono" data-testid="live-subtotale">{fmtEur(calcoli.subtotale)}</div>
                            <span className="text-[10px] text-zinc-500">Subtotale Vendita</span>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardContent className="pt-3 pb-3 text-center">
                            <Euro className="w-5 h-5 mx-auto text-zinc-500 mb-1" />
                            <div className="text-2xl font-bold text-zinc-100 font-mono" data-testid="live-totale">{fmtEur(calcoli.totale)}</div>
                            <span className="text-[10px] text-zinc-500">Totale IVA incl.</span>
                        </CardContent>
                    </Card>
                </div>

                {/* Margini editors */}
                <Card className="bg-zinc-900 border-zinc-800">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center gap-6 flex-wrap">
                            <span className="text-xs text-zinc-500">Margini:</span>
                            <div className="flex items-center gap-1">
                                <label className="text-xs text-zinc-400">Materiali</label>
                                <Input type="number" step="1" value={margini.materiali}
                                    onChange={e => setMargini(m => ({ ...m, materiali: parseFloat(e.target.value) || 0 }))}
                                    className="w-16 h-7 text-xs font-mono text-center bg-zinc-800 border-zinc-700" data-testid="margine-mat" />
                                <span className="text-xs text-zinc-500">%</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <label className="text-xs text-zinc-400">Manodopera</label>
                                <Input type="number" step="1" value={margini.manodopera}
                                    onChange={e => setMargini(m => ({ ...m, manodopera: parseFloat(e.target.value) || 0 }))}
                                    className="w-16 h-7 text-xs font-mono text-center bg-zinc-800 border-zinc-700" data-testid="margine-mano" />
                                <span className="text-xs text-zinc-500">%</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <label className="text-xs text-zinc-400">C/Lavoro</label>
                                <Input type="number" step="1" value={margini.conto_lavoro}
                                    onChange={e => setMargini(m => ({ ...m, conto_lavoro: parseFloat(e.target.value) || 0 }))}
                                    className="w-16 h-7 text-xs font-mono text-center bg-zinc-800 border-zinc-700" data-testid="margine-cl" />
                                <span className="text-xs text-zinc-500">%</span>
                            </div>
                            <div className="flex items-center gap-1 ml-auto">
                                <label className="text-xs text-zinc-400">Costo/h</label>
                                <Input type="number" step="0.5" value={costoOrario}
                                    onChange={e => setCostoOrario(parseFloat(e.target.value) || 35)}
                                    className="w-16 h-7 text-xs font-mono text-center bg-zinc-800 border-zinc-700" data-testid="costo-orario" />
                                <span className="text-xs text-zinc-500">EUR</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Materiali Table */}
                <Card className="bg-zinc-900 border-zinc-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-zinc-300 flex items-center gap-2">
                            <Weight className="w-4 h-4 text-amber-400" />
                            Lista Materiali
                            <Badge variant="outline" className="ml-auto text-[10px] border-indigo-500 text-indigo-400">
                                Clicca sul peso per modificarlo
                            </Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="overflow-x-auto">
                        <table className="w-full" data-testid="materiali-table">
                            <thead>
                                <tr className="text-xs text-zinc-500 border-b border-zinc-700">
                                    <th className="text-left py-2 px-3">Descrizione</th>
                                    <th className="text-left py-2 px-3">Profilo</th>
                                    <th className="text-center py-2 px-3">Qty</th>
                                    <th className="text-right py-2 px-3">Peso</th>
                                    <th className="text-right py-2 px-3">Prezzo/kg</th>
                                    <th className="text-right py-2 px-3">Costo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {materiali.map((m, i) => (
                                    <MaterialRow key={i} item={m} idx={i} onUpdate={handleUpdatePeso} prezzi={prezzi} />
                                ))}
                            </tbody>
                            <tfoot>
                                <tr className="border-t border-zinc-700 bg-zinc-800/50">
                                    <td colSpan={3} className="py-2 px-3 text-sm font-semibold text-zinc-300">Totale Materiali</td>
                                    <td className="py-2 px-3 text-right text-sm font-mono font-bold text-amber-300">{fmtKg(calcoli.pesoTotale)}</td>
                                    <td></td>
                                    <td className="py-2 px-3 text-right text-sm font-mono font-bold text-blue-300">{fmtEur(calcoli.costoMateriali)}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </CardContent>
                </Card>

                {/* Cost Riepilogo */}
                <Card className="bg-zinc-900 border-zinc-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-zinc-300">Riepilogo Costi (Live)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-1 text-sm">
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">Materiali (costo)</span>
                                <span className="font-mono text-zinc-300">{fmtEur(calcoli.costoMateriali)}</span>
                            </div>
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">Materiali (vendita +{margini.materiali}%)</span>
                                <span className="font-mono text-blue-300">{fmtEur(calcoli.matVendita)}</span>
                            </div>
                            <div className="border-t border-zinc-800 my-1"></div>
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">Manodopera ({oreTotali}h x {fmtEur(costoOrario)}/h)</span>
                                <span className="font-mono text-zinc-300">{fmtEur(calcoli.costoMano)}</span>
                            </div>
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">Manodopera (vendita +{margini.manodopera}%)</span>
                                <span className="font-mono text-blue-300">{fmtEur(calcoli.manoVendita)}</span>
                            </div>
                            <div className="border-t border-zinc-800 my-1"></div>
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">Zincatura ({calcoli.pesoTotale} kg x {fmtEur(prezzi.zincatura_kg || 0.45)}/kg)</span>
                                <span className="font-mono text-zinc-300">{fmtEur(calcoli.costoZinc)}</span>
                            </div>
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">Zincatura (vendita +{margini.conto_lavoro}%)</span>
                                <span className="font-mono text-blue-300">{fmtEur(calcoli.clVendita)}</span>
                            </div>
                            <div className="border-t-2 border-zinc-700 my-2"></div>
                            <div className="flex justify-between py-1 font-bold">
                                <span className="text-zinc-200">Subtotale</span>
                                <span className="font-mono text-emerald-300 text-lg" data-testid="riepilogo-subtotale">{fmtEur(calcoli.subtotale)}</span>
                            </div>
                            <div className="flex justify-between py-1">
                                <span className="text-zinc-400">IVA 22%</span>
                                <span className="font-mono text-zinc-400">{fmtEur(calcoli.iva)}</span>
                            </div>
                            <div className="flex justify-between py-1 font-bold text-lg">
                                <span className="text-zinc-100">Totale</span>
                                <span className="font-mono text-zinc-100" data-testid="riepilogo-totale">{fmtEur(calcoli.totale)}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Confronto Section */}
                <Card className="bg-zinc-900 border-zinc-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-zinc-300 flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-blue-400" /> Confronta con Preventivo Manuale
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-end gap-3">
                            <div className="flex-1">
                                <Select value={manPrevId} onValueChange={setManPrevId}>
                                    <SelectTrigger className="bg-zinc-800 border-zinc-700" data-testid="select-manual-prev">
                                        <SelectValue placeholder="Seleziona preventivo manuale..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {prevList.filter(p => !p.predittivo && p.preventivo_id !== prevId).map(p => (
                                            <SelectItem key={p.preventivo_id} value={p.preventivo_id}>
                                                {p.number} - {(p.subject || '').substring(0, 50)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button onClick={runConfronto} disabled={!manPrevId}
                                className="bg-blue-600 hover:bg-blue-700" data-testid="btn-run-confronto">
                                <BarChart3 className="w-4 h-4 mr-2" /> Confronta
                            </Button>
                        </div>

                        {confronto && (
                            <div className="mt-4 space-y-3">
                                <div className="flex items-center gap-4">
                                    <Badge className={confronto.confidence_score >= 85 ? 'bg-emerald-900/50 text-emerald-300' : confronto.confidence_score >= 55 ? 'bg-amber-900/50 text-amber-300' : 'bg-red-900/50 text-red-300'}>
                                        <Target className="w-3 h-3 mr-1" />
                                        Confidence: {confronto.confidence_score} — {confronto.giudizio}
                                    </Badge>
                                    <span className="text-sm text-zinc-400">
                                        Scostamento: <span className={Math.abs(confronto.scostamento_totale_pct) < 10 ? 'text-emerald-400' : 'text-amber-400'}>
                                            {confronto.scostamento_totale_pct > 0 ? '+' : ''}{confronto.scostamento_totale_pct}%
                                        </span>
                                    </span>
                                </div>
                                {confronto.insights?.length > 0 && (
                                    <ul className="space-y-1" data-testid="confronto-insights">
                                        {confronto.insights.map((ins, i) => (
                                            <li key={i} className="text-xs text-zinc-400 flex items-start gap-1">
                                                <span className="text-blue-400 mt-0.5">&#8226;</span> {ins}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                <Button variant="outline" size="sm"
                                    onClick={() => navigate(`/confronto?ai=${prevId}&man=${manPrevId}`)}
                                    className="border-blue-600 text-blue-400 text-xs" data-testid="btn-full-report">
                                    Apri Report Completo
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
