/**
 * PreventivatoreWizard — Wizard multi-step per preventivo predittivo AI.
 * Step 1: Upload disegno → Analisi AI
 * Step 2: Review materiali e pesi
 * Step 3: Margini differenziati e calcolo
 * Step 4: Genera preventivo ufficiale
 */
import { useState, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';
import {
    Upload, Sparkles, Loader2, ChevronRight, ChevronLeft,
    Scale, Calculator, FileText, Check, Brain, TrendingUp,
    Factory, Package, Wrench, CircleDollarSign,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STEP_LABELS = [
    { icon: Upload, label: 'Carica Disegno' },
    { icon: Package, label: 'Materiali' },
    { icon: Calculator, label: 'Margini & Calcolo' },
    { icon: FileText, label: 'Genera Preventivo' },
];

const fmtEur = (v) => typeof v === 'number' ? v.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' }) : '-';

export default function PreventivatoreWizard() {
    const [step, setStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [file, setFile] = useState(null);
    const API = process.env.REACT_APP_BACKEND_URL;

    // Step 1: Analysis results
    const [analysis, setAnalysis] = useState(null);
    const [docId, setDocId] = useState(null);

    // Step 2: Editable materials
    const [materiali, setMateriali] = useState([]);
    const [tipologia, setTipologia] = useState('media');

    // Step 3: Margins and calculation
    const [margineMat, setMargineMat] = useState(25);
    const [margineMano, setMargineMano] = useState(30);
    const [margineCL, setMargineCL] = useState(20);
    const [oreOverride, setOreOverride] = useState('');
    const [calcolo, setCalcolo] = useState(null);
    const [stimaOre, setStimaOre] = useState(null);

    // Step 4: Generate preventivo
    const [clientId, setClientId] = useState('');
    const [subject, setSubject] = useState('');
    const [normativa, setNormativa] = useState('EN_1090');
    const [classeExc, setClasseExc] = useState('EXC2');
    const [giorni, setGiorni] = useState('30');
    const [note, setNote] = useState('');
    const [generatedPrev, setGeneratedPrev] = useState(null);
    const [commessaCreated, setCommessaCreated] = useState(null);
    const [pesoManuale, setPesoManuale] = useState('');

    // Quick estimate (manual weight)
    const handleStimaRapida = useCallback(async () => {
        const peso = parseFloat(pesoManuale);
        if (!peso || peso <= 0) { toast.error('Inserisci un peso valido (kg)'); return; }
        setLoading(true);
        try {
            const body = {
                materiali: [],
                tipologia_struttura: tipologia,
                margine_materiali: margineMat,
                margine_manodopera: margineMano,
                margine_conto_lavoro: margineCL,
                peso_kg_target: peso,
            };
            if (oreOverride) body.ore_override = parseFloat(oreOverride);
            const data = await apiRequest('/preventivatore/calcola', { method: 'POST', body });
            setCalcolo(data.calcolo);
            setStimaOre(data.stima_ore);
            setMateriali(data.calcolo?.righe_materiali || []);
            toast.success(`Stima completata per ${peso} kg`);
            setStep(3);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, [pesoManuale, tipologia, margineMat, margineMano, margineCL, oreOverride]);

    // Step 1: Upload and analyze
    const handleAnalyze = useCallback(async () => {
        if (!file) { toast.error('Seleziona un disegno'); return; }
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch(`${API}/api/preventivatore/analyze-drawing`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Errore analisi');
            }
            const data = await res.json();
            setAnalysis(data);
            setDocId(data.doc_id);
            setMateriali(data.materiali || []);
            setTipologia(data.tipologia_struttura || 'media');
            setSubject(data.titolo_disegno || '');
            toast.success(`${(data.materiali || []).length} materiali estratti (${data.peso_totale_calcolato_kg} kg)`);
            setStep(1);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, [file, API]);

    // Step 3: Calculate
    const handleCalcola = useCallback(async () => {
        setLoading(true);
        try {
            const body = {
                materiali,
                tipologia_struttura: tipologia,
                margine_materiali: margineMat,
                margine_manodopera: margineMano,
                margine_conto_lavoro: margineCL,
            };
            if (oreOverride) body.ore_override = parseFloat(oreOverride);
            const data = await apiRequest('/preventivatore/calcola', { method: 'POST', body });
            setCalcolo(data.calcolo);
            setStimaOre(data.stima_ore);
            toast.success('Calcolo completato');
            setStep(3);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, [materiali, tipologia, margineMat, margineMano, margineCL, oreOverride]);

    // Step 4: Generate
    const handleGenera = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/preventivatore/genera-preventivo', {
                method: 'POST',
                body: {
                    client_id: clientId,
                    subject: subject || 'Preventivo Predittivo AI',
                    calcolo,
                    stima_ore: stimaOre || {},
                    normativa,
                    classe_esecuzione: classeExc,
                    giorni_consegna: parseInt(giorni) || 30,
                    note,
                    doc_id: docId,
                },
            });
            setGeneratedPrev(data);
            toast.success(data.message);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, [clientId, subject, calcolo, stimaOre, normativa, classeExc, giorni, note, docId]);

    // Accept and create commessa
    const handleAccetta = useCallback(async () => {
        if (!generatedPrev?.preventivo_id) return;
        setLoading(true);
        try {
            const data = await apiRequest(`/preventivatore/accetta/${generatedPrev.preventivo_id}`, { method: 'POST' });
            setCommessaCreated(data);
            toast.success(data.message);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, [generatedPrev]);

    const riepilogo = calcolo?.riepilogo || {};

    return (
        <DashboardLayout>
            <div className="max-w-4xl space-y-6">
                {/* Header */}
                <div>
                    <h1 className="font-sans text-3xl font-bold text-slate-900 flex items-center gap-3">
                        <Brain className="h-8 w-8 text-violet-600" />
                        Preventivatore Predittivo
                    </h1>
                    <p className="text-slate-500 mt-1">Carica un disegno tecnico e l'AI genera il preventivo con prezzi storici e stima ore</p>
                </div>

                {/* Stepper */}
                <div className="flex items-center gap-1" data-testid="wizard-stepper">
                    {STEP_LABELS.map((s, i) => {
                        const Icon = s.icon;
                        const active = i === step;
                        const done = i < step;
                        return (
                            <div key={i} className="flex items-center gap-1 flex-1">
                                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                                    active ? 'bg-violet-600 text-white' : done ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>
                                    {done ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                                    <span className="hidden sm:inline">{s.label}</span>
                                </div>
                                {i < STEP_LABELS.length - 1 && <div className={`flex-1 h-0.5 ${done ? 'bg-emerald-300' : 'bg-slate-200'}`} />}
                            </div>
                        );
                    })}
                </div>

                {/* Step 0: Upload */}
                {step === 0 && (
                    <Card className="border-violet-200">
                        <CardHeader className="bg-violet-50 border-b border-violet-200">
                            <CardTitle className="text-sm flex items-center gap-2 text-violet-800">
                                <Upload className="h-4 w-4" /> Carica Disegno Tecnico
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-6 space-y-4">
                            <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-violet-300 rounded-xl cursor-pointer hover:border-violet-500 hover:bg-violet-50/50 transition-colors" data-testid="upload-drawing-area">
                                <input type="file" accept=".pdf,image/png,image/jpeg" onChange={e => setFile(e.target.files?.[0] || null)} className="hidden" data-testid="input-upload-drawing" />
                                <Sparkles className="h-8 w-8 text-violet-400 mb-2" />
                                <span className="text-sm text-violet-600 font-medium">{file ? file.name : 'Seleziona PDF o immagine del disegno'}</span>
                                <span className="text-xs text-violet-400 mt-1">PDF, PNG, JPG — max 20MB</span>
                            </label>
                            <Button onClick={handleAnalyze} disabled={!file || loading} className="w-full bg-violet-600 hover:bg-violet-700 text-white h-11" data-testid="btn-analyze-drawing">
                                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
                                {loading ? 'Analisi AI in corso...' : 'Analizza con AI Vision'}
                            </Button>

                            {/* Divider */}
                            <div className="relative py-2">
                                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200"></div></div>
                                <div className="relative flex justify-center"><span className="bg-white px-3 text-xs text-slate-400 font-medium">oppure</span></div>
                            </div>

                            {/* Quick manual estimate */}
                            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3" data-testid="stima-rapida-section">
                                <div className="flex items-center gap-2">
                                    <Scale className="h-4 w-4 text-slate-600" />
                                    <span className="text-sm font-semibold text-slate-700">Stima Rapida Manuale</span>
                                </div>
                                <p className="text-xs text-slate-500">Inserisci peso e tipologia per un calcolo istantaneo senza disegno</p>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label className="text-xs text-slate-600">Peso stimato (kg)</Label>
                                        <Input type="number" value={pesoManuale} onChange={e => setPesoManuale(e.target.value)}
                                            placeholder="es. 2500" className="h-9 text-sm" data-testid="input-peso-manuale" />
                                    </div>
                                    <div>
                                        <Label className="text-xs text-slate-600">Tipologia struttura</Label>
                                        <Select value={tipologia} onValueChange={setTipologia}>
                                            <SelectTrigger className="h-9 text-xs" data-testid="select-tipologia-rapida"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="leggera">Leggera</SelectItem>
                                                <SelectItem value="media">Media</SelectItem>
                                                <SelectItem value="complessa">Complessa</SelectItem>
                                                <SelectItem value="speciale">Speciale</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <Button onClick={handleStimaRapida} disabled={!pesoManuale || loading}
                                    variant="outline" className="w-full h-10 text-sm border-slate-300 hover:bg-slate-100" data-testid="btn-stima-rapida">
                                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Calculator className="h-4 w-4 mr-2" />}
                                    Calcola con peso manuale
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 1: Review Materials */}
                {step === 1 && (
                    <Card className="border-blue-200">
                        <CardHeader className="bg-blue-50 border-b border-blue-200">
                            <CardTitle className="text-sm flex items-center gap-2 text-blue-800">
                                <Package className="h-4 w-4" /> Materiali Estratti — {analysis?.peso_totale_calcolato_kg} kg
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 space-y-3">
                            <div className="flex items-center gap-3 mb-2">
                                <Label className="text-xs whitespace-nowrap">Tipologia Struttura:</Label>
                                <Select value={tipologia} onValueChange={setTipologia}>
                                    <SelectTrigger className="h-8 text-xs w-48" data-testid="select-tipologia"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="leggera">Leggera (ringhiere, parapetti)</SelectItem>
                                        <SelectItem value="media">Media (tettoie, scale, portoni)</SelectItem>
                                        <SelectItem value="complessa">Complessa (capannoni, ponti)</SelectItem>
                                        <SelectItem value="speciale">Speciale (EXC3/4, antisismico)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="max-h-64 overflow-y-auto space-y-1.5 border rounded-lg p-2">
                                {materiali.map((m, i) => (
                                    <div key={i} className="flex items-center gap-3 text-xs p-2 rounded border bg-white hover:bg-blue-50/30" data-testid={`material-${i}`}>
                                        <Badge variant="outline" className="text-[9px] min-w-[60px] text-center">{m.tipo}</Badge>
                                        <div className="flex-1 min-w-0">
                                            <span className="font-semibold text-slate-700">{m.profilo || m.descrizione}</span>
                                            {m.materiale && <span className="text-slate-400 ml-2">{m.materiale}</span>}
                                            {m.lunghezza_mm && <span className="text-slate-400 ml-1">L={m.lunghezza_mm}mm</span>}
                                        </div>
                                        <span className="text-slate-500 whitespace-nowrap">x{m.quantita || 1}</span>
                                        <span className="font-mono font-bold text-blue-700 min-w-[60px] text-right">{m.peso_calcolato_kg || '?'} kg</span>
                                    </div>
                                ))}
                            </div>

                            <div className="flex justify-between pt-2">
                                <Button variant="outline" size="sm" onClick={() => setStep(0)} className="text-xs"><ChevronLeft className="h-3 w-3 mr-1" /> Indietro</Button>
                                <Button size="sm" onClick={() => setStep(2)} className="text-xs bg-blue-600 hover:bg-blue-700 text-white" data-testid="btn-to-margins"><ChevronRight className="h-3 w-3 mr-1" /> Margini & Calcolo</Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 2: Margins and Calculation */}
                {step === 2 && (
                    <Card className="border-amber-200">
                        <CardHeader className="bg-amber-50 border-b border-amber-200">
                            <CardTitle className="text-sm flex items-center gap-2 text-amber-800">
                                <Calculator className="h-4 w-4" /> Margini Differenziati
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 space-y-5">
                            {/* Margin sliders */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="space-y-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-xs flex items-center gap-1"><Package className="h-3 w-3 text-blue-600" /> Materiali</Label>
                                        <span className="text-sm font-bold text-blue-700">{margineMat}%</span>
                                    </div>
                                    <Slider value={[margineMat]} onValueChange={v => setMargineMat(v[0])} min={0} max={60} step={1} className="mt-1" data-testid="slider-margine-mat" />
                                </div>
                                <div className="space-y-2 p-3 bg-orange-50 rounded-lg border border-orange-200">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-xs flex items-center gap-1"><Factory className="h-3 w-3 text-orange-600" /> Manodopera</Label>
                                        <span className="text-sm font-bold text-orange-700">{margineMano}%</span>
                                    </div>
                                    <Slider value={[margineMano]} onValueChange={v => setMargineMano(v[0])} min={0} max={60} step={1} className="mt-1" data-testid="slider-margine-mano" />
                                </div>
                                <div className="space-y-2 p-3 bg-purple-50 rounded-lg border border-purple-200">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-xs flex items-center gap-1"><Wrench className="h-3 w-3 text-purple-600" /> Conto Lavoro</Label>
                                        <span className="text-sm font-bold text-purple-700">{margineCL}%</span>
                                    </div>
                                    <Slider value={[margineCL]} onValueChange={v => setMargineCL(v[0])} min={0} max={60} step={1} className="mt-1" data-testid="slider-margine-cl" />
                                </div>
                            </div>

                            <div>
                                <Label className="text-xs">Override ore stimate (lascia vuoto per auto)</Label>
                                <Input type="number" value={oreOverride} onChange={e => setOreOverride(e.target.value)} placeholder="Auto (ML + Parametrico)" className="h-8 text-sm w-48" data-testid="input-ore-override" />
                            </div>

                            <div className="flex justify-between pt-2">
                                <Button variant="outline" size="sm" onClick={() => setStep(1)} className="text-xs"><ChevronLeft className="h-3 w-3 mr-1" /> Materiali</Button>
                                <Button size="sm" onClick={handleCalcola} disabled={loading} className="text-xs bg-amber-600 hover:bg-amber-700 text-white" data-testid="btn-calcola">
                                    {loading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Calculator className="h-3 w-3 mr-1" />}
                                    Calcola Preventivo
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 3: Results and Generate */}
                {step === 3 && calcolo && (
                    <div className="space-y-4">
                        {/* ML Info */}
                        {stimaOre && (
                            <Card className="border-violet-200">
                                <CardContent className="p-4">
                                    <div className="flex items-start gap-3">
                                        <Brain className="h-5 w-5 text-violet-600 mt-0.5" />
                                        <div className="flex-1">
                                            <p className="text-sm font-semibold text-violet-800">Stima Ore — {stimaOre.metodo?.replace(/_/g, ' ')}</p>
                                            <div className="grid grid-cols-3 gap-3 mt-2">
                                                <div className="text-center p-2 bg-slate-50 rounded border">
                                                    <p className="text-[10px] text-slate-500">Parametriche</p>
                                                    <p className="text-sm font-bold text-slate-700">{stimaOre.ore_parametriche}h</p>
                                                </div>
                                                {stimaOre.ore_ml && (
                                                    <div className="text-center p-2 bg-violet-50 rounded border border-violet-200">
                                                        <p className="text-[10px] text-violet-500">Machine Learning</p>
                                                        <p className="text-sm font-bold text-violet-700">{stimaOre.ore_ml}h</p>
                                                    </div>
                                                )}
                                                <div className="text-center p-2 bg-emerald-50 rounded border border-emerald-200">
                                                    <p className="text-[10px] text-emerald-500">Suggerite</p>
                                                    <p className="text-sm font-bold text-emerald-700">{stimaOre.ore_suggerite}h</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-500">
                                                <span>Confidenza: <Badge variant="outline" className={`text-[9px] ${stimaOre.confidence === 'alta' ? 'bg-emerald-50 text-emerald-700' : stimaOre.confidence === 'media' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-500'}`}>{stimaOre.confidence}</Badge></span>
                                                <span>Campioni storici: {stimaOre.campioni}</span>
                                                {stimaOre.r_squared > 0 && <span>R2: {stimaOre.r_squared}</span>}
                                                {stimaOre.media_ore_ton_storica > 0 && <span>Media storica: {stimaOre.media_ore_ton_storica} h/ton</span>}
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* Cost Breakdown */}
                        <Card className="border-emerald-200">
                            <CardHeader className="bg-emerald-50 border-b border-emerald-200">
                                <CardTitle className="text-sm flex items-center gap-2 text-emerald-800">
                                    <CircleDollarSign className="h-4 w-4" /> Riepilogo Economico
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4">
                                <div className="grid grid-cols-4 gap-3 mb-4">
                                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-center">
                                        <p className="text-[10px] text-blue-500">Costo Materiali</p>
                                        <p className="text-xs font-bold text-blue-800">{fmtEur(riepilogo.costo_materiali)}</p>
                                        <p className="text-[10px] text-blue-400">+{riepilogo.margine_materiali_pct}%</p>
                                        <p className="text-sm font-bold text-blue-900">{fmtEur(riepilogo.materiali_vendita)}</p>
                                    </div>
                                    <div className="p-3 bg-orange-50 rounded-lg border border-orange-200 text-center">
                                        <p className="text-[10px] text-orange-500">Manodopera ({riepilogo.ore_stimate}h)</p>
                                        <p className="text-xs font-bold text-orange-800">{fmtEur(riepilogo.costo_manodopera)}</p>
                                        <p className="text-[10px] text-orange-400">+{riepilogo.margine_manodopera_pct}%</p>
                                        <p className="text-sm font-bold text-orange-900">{fmtEur(riepilogo.manodopera_vendita)}</p>
                                    </div>
                                    <div className="p-3 bg-purple-50 rounded-lg border border-purple-200 text-center">
                                        <p className="text-[10px] text-purple-500">Conto Lavoro</p>
                                        <p className="text-xs font-bold text-purple-800">{fmtEur(riepilogo.costo_cl)}</p>
                                        <p className="text-[10px] text-purple-400">+{riepilogo.margine_cl_pct}%</p>
                                        <p className="text-sm font-bold text-purple-900">{fmtEur(riepilogo.cl_vendita)}</p>
                                    </div>
                                    <div className="p-3 bg-emerald-100 rounded-lg border-2 border-emerald-300 text-center">
                                        <p className="text-[10px] text-emerald-600">TOTALE</p>
                                        <p className="text-lg font-bold text-emerald-900" data-testid="totale-vendita">{fmtEur(riepilogo.totale_vendita)}</p>
                                        <p className="text-[10px] text-emerald-600">Margine: {riepilogo.margine_globale_pct}%</p>
                                        <p className="text-xs font-semibold text-emerald-700">Utile: {fmtEur(riepilogo.utile_lordo)}</p>
                                    </div>
                                </div>

                                {/* Generate form */}
                                <div className="border-t pt-4 space-y-3">
                                    <h3 className="text-sm font-semibold text-slate-700">Genera Preventivo Ufficiale</h3>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Label className="text-xs">Oggetto</Label>
                                            <Input value={subject} onChange={e => setSubject(e.target.value)} placeholder="Oggetto del preventivo" className="h-8 text-sm" data-testid="input-subject" />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Giorni Consegna</Label>
                                            <Input type="number" value={giorni} onChange={e => setGiorni(e.target.value)} className="h-8 text-sm" />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Label className="text-xs">Normativa</Label>
                                            <Select value={normativa} onValueChange={setNormativa}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="EN_1090">EN 1090</SelectItem>
                                                    <SelectItem value="EN_13241">EN 13241</SelectItem>
                                                    <SelectItem value="NESSUNA">Nessuna</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div>
                                            <Label className="text-xs">Classe Esecuzione</Label>
                                            <Select value={classeExc} onValueChange={setClasseExc}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="EXC1">EXC1</SelectItem>
                                                    <SelectItem value="EXC2">EXC2</SelectItem>
                                                    <SelectItem value="EXC3">EXC3</SelectItem>
                                                    <SelectItem value="EXC4">EXC4</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex justify-between pt-3">
                                    <Button variant="outline" size="sm" onClick={() => setStep(2)} className="text-xs"><ChevronLeft className="h-3 w-3 mr-1" /> Margini</Button>
                                    <Button size="sm" onClick={handleGenera} disabled={loading} className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="btn-genera-preventivo">
                                        {loading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <FileText className="h-3 w-3 mr-1" />}
                                        Genera Preventivo
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Generated Preventivo Confirmation */}
                        {generatedPrev && (
                            <Card className="border-2 border-emerald-400 bg-emerald-50/50">
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                                            <Check className="h-5 w-5 text-emerald-600" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-emerald-800">{generatedPrev.message}</p>
                                            <p className="text-xs text-emerald-600">N. {generatedPrev.number} — Totale: {fmtEur(generatedPrev.totale)}</p>
                                        </div>
                                    </div>
                                    {!commessaCreated ? (
                                        <Button onClick={handleAccetta} disabled={loading} className="w-full bg-violet-600 hover:bg-violet-700 text-white h-10" data-testid="btn-accetta-genera-commessa">
                                            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <TrendingUp className="h-4 w-4 mr-2" />}
                                            Accetta e Genera Commessa Automaticamente
                                        </Button>
                                    ) : (
                                        <div className="bg-white border-2 border-violet-300 rounded-lg p-4 text-center">
                                            <Check className="h-6 w-6 text-violet-600 mx-auto mb-2" />
                                            <p className="text-sm font-bold text-violet-800">{commessaCreated.message}</p>
                                            <p className="text-xs text-violet-600 mt-1">
                                                Commessa {commessaCreated.commessa_number} — {commessaCreated.ore_preventivate}h preventivate
                                            </p>
                                            <div className="flex gap-3 justify-center mt-2 text-xs text-slate-500">
                                                <span>Budget Mat: {fmtEur(commessaCreated.budget?.materiali)}</span>
                                                <span>Budget Mano: {fmtEur(commessaCreated.budget?.manodopera)}</span>
                                                <span>Budget C/L: {fmtEur(commessaCreated.budget?.conto_lavoro)}</span>
                                            </div>
                                            <Button variant="outline" size="sm" className="mt-3 text-xs" onClick={() => window.location.href = `/commesse/${commessaCreated.commessa_id}`} data-testid="btn-go-to-commessa">
                                                Vai alla Commessa
                                            </Button>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
