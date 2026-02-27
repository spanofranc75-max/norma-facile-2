/**
 * Core Engine — Norme Manager + Componenti + Product Configurator
 * Data-driven norm engine: add a new norm JSON = add a new regulation.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import {
    Tabs, TabsContent, TabsList, TabsTrigger,
} from '../components/ui/tabs';
import { toast } from 'sonner';
import {
    Shield, BookOpen, Layers, Cpu, Pencil, Trash2, Plus, Database,
    CheckCircle2, XCircle, AlertTriangle, ChevronRight, Zap,
    Thermometer, Wind, Droplets, GaugeCircle, FileDown, FolderArchive,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const formatNum = (v, d = 2) => (v ?? 0).toFixed(d);

const PRODUCT_TYPES = [
    { value: 'cancello', label: 'Cancello' },
    { value: 'portone', label: 'Portone' },
    { value: 'finestra', label: 'Finestra' },
    { value: 'portafinestra', label: 'Portafinestra' },
    { value: 'tettoia', label: 'Tettoia' },
    { value: 'scala', label: 'Scala' },
    { value: 'soppalco', label: 'Soppalco' },
    { value: 'ringhiera', label: 'Ringhiera' },
    { value: 'pensilina', label: 'Pensilina' },
    { value: 'recinzione', label: 'Recinzione' },
];

const ZONE_LABELS = {
    A: 'Zona A (Lampedusa)', B: 'Zona B (Palermo, Catania)',
    C: 'Zona C (Napoli, Roma)', D: 'Zona D (Firenze, Milano)',
    E: 'Zona E (Torino, Bologna)', F: 'Zona F (Cuneo, Belluno)',
};

export default function CoreEnginePage() {
    const [tab, setTab] = useState('configurator');
    const [norme, setNorme] = useState([]);
    const [componenti, setComponenti] = useState([]);
    const [loadingNorme, setLoadingNorme] = useState(true);
    const [loadingComp, setLoadingComp] = useState(true);

    // Configurator state
    const [selectedProduct, setSelectedProduct] = useState('');
    const [configResult, setConfigResult] = useState(null);
    const [calcResult, setCalcResult] = useState(null);
    const [calcForm, setCalcForm] = useState({
        height_mm: 1400, width_mm: 1200, frame_width_mm: 80,
        vetro_id: '', telaio_id: '', distanziatore_id: '',
        zona_climatica: 'E', specs: {},
    });
    const [calculating, setCalculating] = useState(false);

    // Component dialog
    const [compDialog, setCompDialog] = useState(false);
    const [compForm, setCompForm] = useState({ codice: '', label: '', tipo: 'vetro', ug: 0, uf: 0, psi: 0, thickness_mm: 0, produttore: '' });
    const [editingComp, setEditingComp] = useState(null);
    const [savingComp, setSavingComp] = useState(false);

    // Norma detail dialog
    const [normaDetail, setNormaDetail] = useState(null);

    const fetchNorme = useCallback(async () => {
        try {
            setLoadingNorme(true);
            const data = await apiRequest('/engine/norme?active_only=false');
            setNorme(data.norme || []);
        } catch { toast.error('Errore caricamento norme'); }
        finally { setLoadingNorme(false); }
    }, []);

    const fetchComponenti = useCallback(async () => {
        try {
            setLoadingComp(true);
            const data = await apiRequest('/engine/componenti');
            setComponenti(data.componenti || []);
        } catch { toast.error('Errore caricamento componenti'); }
        finally { setLoadingComp(false); }
    }, []);

    useEffect(() => { fetchNorme(); fetchComponenti(); }, [fetchNorme, fetchComponenti]);

    // Seed
    const seedNorme = async () => {
        try {
            const r = await apiRequest('/engine/norme/seed', { method: 'POST' });
            toast.success(r.message);
            fetchNorme();
        } catch (e) { toast.error(e.message); }
    };
    const seedComponenti = async () => {
        try {
            const r = await apiRequest('/engine/componenti/seed', { method: 'POST' });
            toast.success(r.message);
            fetchComponenti();
        } catch (e) { toast.error(e.message); }
    };

    // Configure product
    const configureProduct = async (product) => {
        setSelectedProduct(product);
        setCalcResult(null);
        try {
            const data = await apiRequest('/engine/configure', {
                method: 'POST', body: JSON.stringify({ product_type: product }),
            });
            setConfigResult(data);
            // Pre-select first components
            const vetri = data.componenti?.vetri || [];
            const telai = data.componenti?.telai || [];
            const dist = data.componenti?.distanziatori || [];
            setCalcForm(f => ({
                ...f,
                vetro_id: vetri[0]?.comp_id || '',
                telaio_id: telai[0]?.comp_id || '',
                distanziatore_id: dist[0]?.comp_id || '',
            }));
        } catch { toast.error('Errore configurazione'); }
    };

    // Calculate
    const runCalculation = async () => {
        if (!configResult?.norme?.length) return;
        setCalculating(true);
        try {
            const normaId = configResult.norme[0].norma_id;
            const data = await apiRequest('/engine/calculate', {
                method: 'POST', body: JSON.stringify({
                    norma_id: normaId,
                    product_type: selectedProduct,
                    ...calcForm,
                }),
            });
            setCalcResult(data);
            if (data.compliant) toast.success('Prodotto CONFORME');
            else toast.error('Prodotto NON conforme — verifica gli avvisi');
        } catch (e) { toast.error(e.message); }
        finally { setCalculating(false); }
    };

    // Component CRUD
    const openNewComp = (tipo) => {
        setEditingComp(null);
        setCompForm({ codice: '', label: '', tipo, ug: 0, uf: 0, psi: 0, thickness_mm: 0, produttore: '' });
        setCompDialog(true);
    };
    const openEditComp = (c) => {
        setEditingComp(c);
        setCompForm({ codice: c.codice, label: c.label, tipo: c.tipo, ug: c.ug || 0, uf: c.uf || 0, psi: c.psi || 0, thickness_mm: c.thickness_mm || 0, produttore: c.produttore || '' });
        setCompDialog(true);
    };
    const saveComp = async () => {
        if (!compForm.codice || !compForm.label) { toast.error('Codice e label obbligatori'); return; }
        setSavingComp(true);
        try {
            if (editingComp) {
                await apiRequest(`/engine/componenti/${editingComp.comp_id}`, {
                    method: 'PUT', body: JSON.stringify(compForm),
                });
                toast.success('Componente aggiornato');
            } else {
                await apiRequest('/engine/componenti', {
                    method: 'POST', body: JSON.stringify(compForm),
                });
                toast.success('Componente creato');
            }
            setCompDialog(false);
            fetchComponenti();
        } catch (e) { toast.error(e.message); }
        finally { setSavingComp(false); }
    };
    const deleteComp = async (c) => {
        if (!window.confirm(`Eliminare ${c.codice}?`)) return;
        try {
            await apiRequest(`/engine/componenti/${c.comp_id}`, { method: 'DELETE' });
            toast.success('Eliminato');
            fetchComponenti();
        } catch { toast.error('Errore'); }
    };

    const vetri = componenti.filter(c => c.tipo === 'vetro');
    const telai = componenti.filter(c => c.tipo === 'telaio');
    const distanziatori = componenti.filter(c => c.tipo === 'distanziatore');

    return (
        <DashboardLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="font-sans text-3xl font-bold text-slate-900 flex items-center gap-3">
                        <Cpu className="h-8 w-8 text-[#0055FF]" />
                        Core Engine
                    </h1>
                    <p className="text-slate-600">Motore normativo universale — Configurazione, calcolo e validazione</p>
                </div>

                <Tabs value={tab} onValueChange={setTab}>
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="configurator" data-testid="tab-configurator">
                            <Zap className="h-4 w-4 mr-2" /> Configuratore
                        </TabsTrigger>
                        <TabsTrigger value="norme" data-testid="tab-norme">
                            <BookOpen className="h-4 w-4 mr-2" /> Norme
                        </TabsTrigger>
                        <TabsTrigger value="componenti" data-testid="tab-componenti">
                            <Layers className="h-4 w-4 mr-2" /> Componenti
                        </TabsTrigger>
                    </TabsList>

                    {/* ═══ TAB: CONFIGURATORE PRODOTTO ═══ */}
                    <TabsContent value="configurator" className="space-y-6 mt-4">
                        {/* Step 1: Select product */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-lg">1. Seleziona Tipo Prodotto</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-5 gap-2">
                                    {PRODUCT_TYPES.map(p => (
                                        <Button
                                            key={p.value}
                                            variant={selectedProduct === p.value ? 'default' : 'outline'}
                                            className={selectedProduct === p.value ? 'bg-[#0055FF] text-white' : ''}
                                            onClick={() => configureProduct(p.value)}
                                            data-testid={`btn-product-${p.value}`}
                                        >
                                            {p.label}
                                        </Button>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Step 2: Show applicable norms & fields */}
                        {configResult && (
                            <>
                                <Card className="border-gray-200">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-lg">2. Norme Applicabili</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {configResult.norme.map(n => (
                                                <div key={n.norma_id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                                                    <Shield className="h-5 w-5 text-[#0055FF] mt-0.5" />
                                                    <div className="flex-1">
                                                        <p className="font-semibold">{n.title}</p>
                                                        <p className="text-sm text-slate-500">{n.standard_ref} — {n.notes}</p>
                                                        <div className="flex flex-wrap gap-1 mt-2">
                                                            {(n.required_performances || []).map(rp => (
                                                                <Badge key={rp.code} className={rp.mandatory ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600'}>
                                                                    {rp.label} {rp.mandatory ? '(Obb.)' : '(Opz.)'}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Step 3: Input dimensions & components */}
                                {configResult.has_thermal_calc && (
                                    <Card className="border-gray-200">
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-lg flex items-center gap-2">
                                                <Thermometer className="h-5 w-5 text-orange-500" />
                                                3. Calcolo Prestazioni
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            {/* Dimensions */}
                                            <div className="grid grid-cols-3 gap-4">
                                                <div>
                                                    <Label className="text-xs">Altezza (mm)</Label>
                                                    <Input data-testid="input-height" type="number" value={calcForm.height_mm}
                                                        onChange={e => setCalcForm(f => ({ ...f, height_mm: +e.target.value }))} />
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Larghezza (mm)</Label>
                                                    <Input data-testid="input-width" type="number" value={calcForm.width_mm}
                                                        onChange={e => setCalcForm(f => ({ ...f, width_mm: +e.target.value }))} />
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Larghezza telaio (mm)</Label>
                                                    <Input data-testid="input-frame-width" type="number" value={calcForm.frame_width_mm}
                                                        onChange={e => setCalcForm(f => ({ ...f, frame_width_mm: +e.target.value }))} />
                                                </div>
                                            </div>
                                            {/* Component selectors */}
                                            <div className="grid grid-cols-3 gap-4">
                                                <div>
                                                    <Label className="text-xs">Vetro (Ug)</Label>
                                                    <Select value={calcForm.vetro_id || '__none__'} onValueChange={v => setCalcForm(f => ({ ...f, vetro_id: v === '__none__' ? '' : v }))}>
                                                        <SelectTrigger data-testid="select-vetro"><SelectValue placeholder="Seleziona vetro" /></SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                                            {(configResult.componenti?.vetri || []).map(v => (
                                                                <SelectItem key={v.comp_id} value={v.comp_id}>
                                                                    {v.label} (Ug={v.ug})
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Telaio (Uf)</Label>
                                                    <Select value={calcForm.telaio_id || '__none__'} onValueChange={v => setCalcForm(f => ({ ...f, telaio_id: v === '__none__' ? '' : v }))}>
                                                        <SelectTrigger data-testid="select-telaio"><SelectValue placeholder="Seleziona telaio" /></SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                                            {(configResult.componenti?.telai || []).map(t => (
                                                                <SelectItem key={t.comp_id} value={t.comp_id}>
                                                                    {t.label} (Uf={t.uf})
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Distanziatore (Ψ)</Label>
                                                    <Select value={calcForm.distanziatore_id || '__none__'} onValueChange={v => setCalcForm(f => ({ ...f, distanziatore_id: v === '__none__' ? '' : v }))}>
                                                        <SelectTrigger data-testid="select-distanziatore"><SelectValue placeholder="Seleziona distanziatore" /></SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                                            {(configResult.componenti?.distanziatori || []).map(d => (
                                                                <SelectItem key={d.comp_id} value={d.comp_id}>
                                                                    {d.label} (Ψ={d.psi})
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                            </div>
                                            {/* Zone */}
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <Label className="text-xs">Zona Climatica Cantiere</Label>
                                                    <Select value={calcForm.zona_climatica} onValueChange={v => setCalcForm(f => ({ ...f, zona_climatica: v }))}>
                                                        <SelectTrigger data-testid="select-zona"><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            {Object.entries(ZONE_LABELS).map(([k, v]) => (
                                                                <SelectItem key={k} value={k}>{v}</SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="flex items-end">
                                                    <Button
                                                        data-testid="btn-calculate"
                                                        onClick={runCalculation}
                                                        disabled={calculating}
                                                        className="bg-[#0055FF] text-white hover:bg-[#0044CC] w-full h-10"
                                                    >
                                                        <Zap className="h-4 w-4 mr-2" />
                                                        {calculating ? 'Calcolo...' : 'Calcola Prestazioni'}
                                                    </Button>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Step 4: Results */}
                                {calcResult && (
                                    <Card className={`border-2 ${calcResult.compliant ? 'border-emerald-400' : 'border-red-400'}`}>
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-lg flex items-center gap-2">
                                                {calcResult.compliant
                                                    ? <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                                                    : <XCircle className="h-6 w-6 text-red-600" />
                                                }
                                                4. Risultati — {calcResult.compliant ? 'CONFORME' : 'NON CONFORME'}
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            {/* Thermal result */}
                                            {calcResult.results?.thermal && (
                                                <div className="space-y-3">
                                                    <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
                                                        <div className="text-center">
                                                            <p className="text-4xl font-bold font-mono text-[#0055FF]">
                                                                {calcResult.results.thermal.uw}
                                                            </p>
                                                            <p className="text-xs text-slate-500">W/m²K</p>
                                                        </div>
                                                        <div className="flex-1 space-y-1 text-sm">
                                                            <p>Vetro: <strong>{calcResult.results.thermal.vetro_label}</strong> (Ug={calcResult.results.thermal.ug})</p>
                                                            <p>Telaio: <strong>{calcResult.results.thermal.telaio_label}</strong> (Uf={calcResult.results.thermal.uf})</p>
                                                            <p>Distanziatore: <strong>{calcResult.results.thermal.distanziatore_label}</strong> (Ψ={calcResult.results.thermal.psi})</p>
                                                            <p className="text-xs text-slate-400">Area vetro: {formatNum(calcResult.results.thermal.ag, 3)} m² | Area telaio: {formatNum(calcResult.results.thermal.af, 3)} m²</p>
                                                        </div>
                                                    </div>
                                                    {/* Zone compliance grid */}
                                                    <div className="grid grid-cols-6 gap-2">
                                                        {Object.entries(calcResult.results.thermal.zone_compliance || {}).map(([zone, info]) => (
                                                            <div key={zone}
                                                                className={`p-2 rounded-lg text-center text-xs ${
                                                                    info.compliant ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'
                                                                } ${zone === calcForm.zona_climatica ? 'ring-2 ring-[#0055FF]' : ''}`}
                                                            >
                                                                <p className="font-bold">Zona {zone}</p>
                                                                <p className="text-slate-500">Limite: {info.limit}</p>
                                                                {info.compliant
                                                                    ? <CheckCircle2 className="h-4 w-4 text-emerald-600 mx-auto mt-1" />
                                                                    : <XCircle className="h-4 w-4 text-red-500 mx-auto mt-1" />
                                                                }
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Warnings */}
                                            {(calcResult.warnings || []).length > 0 && (
                                                <div className="space-y-2">
                                                    {calcResult.warnings.map((w, i) => (
                                                        <div key={i} className="flex items-start gap-2 p-2 bg-yellow-50 rounded-lg text-sm">
                                                            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                                                            <span>{w}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Suggestions */}
                                            {(calcResult.suggestions || []).length > 0 && (
                                                <div className="space-y-2">
                                                    {calcResult.suggestions.map((s, i) => (
                                                        <div key={i} className="flex items-start gap-2 p-2 bg-blue-50 rounded-lg text-sm">
                                                            <Zap className="h-4 w-4 text-[#0055FF] mt-0.5 shrink-0" />
                                                            <span>{s.message}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Validation rules */}
                                            {calcResult.validation?.errors?.length > 0 && (
                                                <div className="space-y-2">
                                                    {calcResult.validation.errors.map((e, i) => (
                                                        <div key={i} className="flex items-start gap-2 p-2 bg-red-50 rounded-lg text-sm">
                                                            <XCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                                                            <span className="font-medium text-red-800">{e.message}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {calcResult.validation?.warnings?.length > 0 && (
                                                <div className="space-y-2">
                                                    {calcResult.validation.warnings.map((w, i) => (
                                                        <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 rounded-lg text-sm">
                                                            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                                                            <span>{w.message}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                )}
                            </>
                        )}
                    </TabsContent>

                    {/* ═══ TAB: NORME ═══ */}
                    <TabsContent value="norme" className="space-y-4 mt-4">
                        <div className="flex items-center justify-between">
                            <p className="text-slate-600">{norme.length} norme configurate</p>
                            <Button data-testid="btn-seed-norme" variant="outline" onClick={seedNorme}>
                                <Database className="h-4 w-4 mr-2" /> Seed Norme Standard
                            </Button>
                        </div>
                        {norme.map(n => (
                            <Card key={n.norma_id} className="border-gray-200">
                                <CardContent className="pt-4">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-start gap-3">
                                            <Shield className="h-5 w-5 text-[#0055FF] mt-0.5" />
                                            <div>
                                                <p className="font-semibold">{n.title}</p>
                                                <p className="text-sm text-slate-500">{n.norma_id} — {n.standard_ref}</p>
                                                <div className="flex flex-wrap gap-1 mt-2">
                                                    {(n.product_types || []).map(pt => (
                                                        <Badge key={pt} className="bg-blue-100 text-blue-800">{pt}</Badge>
                                                    ))}
                                                </div>
                                                <div className="flex flex-wrap gap-1 mt-1">
                                                    {(n.required_performances || []).map(rp => (
                                                        <Badge key={rp.code} variant="outline" className="text-xs">
                                                            {rp.label} {rp.mandatory && '*'}
                                                        </Badge>
                                                    ))}
                                                </div>
                                                {(n.validation_rules || []).length > 0 && (
                                                    <p className="text-xs text-slate-400 mt-1">
                                                        {n.validation_rules.length} regole di validazione
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                        <Badge className={n.active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'}>
                                            {n.active ? 'Attiva' : 'Disattiva'}
                                        </Badge>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </TabsContent>

                    {/* ═══ TAB: COMPONENTI ═══ */}
                    <TabsContent value="componenti" className="space-y-4 mt-4">
                        <div className="flex items-center justify-between">
                            <p className="text-slate-600">{componenti.length} componenti in database</p>
                            <div className="flex gap-2">
                                <Button data-testid="btn-seed-componenti" variant="outline" onClick={seedComponenti}>
                                    <Database className="h-4 w-4 mr-2" /> Seed Componenti
                                </Button>
                                <Button data-testid="btn-new-componente" className="bg-[#0055FF] text-white" onClick={() => openNewComp('vetro')}>
                                    <Plus className="h-4 w-4 mr-2" /> Nuovo
                                </Button>
                            </div>
                        </div>

                        {/* Vetri */}
                        <CompTable title="Vetri" icon={<Layers className="h-4 w-4 text-blue-500" />}
                            items={vetri} valueKey="ug" valueLabel="Ug (W/m²K)"
                            onEdit={openEditComp} onDelete={deleteComp} onNew={() => openNewComp('vetro')} />

                        {/* Telai */}
                        <CompTable title="Telai / Profili" icon={<GaugeCircle className="h-4 w-4 text-amber-500" />}
                            items={telai} valueKey="uf" valueLabel="Uf (W/m²K)"
                            onEdit={openEditComp} onDelete={deleteComp} onNew={() => openNewComp('telaio')} />

                        {/* Distanziatori */}
                        <CompTable title="Distanziatori" icon={<Thermometer className="h-4 w-4 text-orange-500" />}
                            items={distanziatori} valueKey="psi" valueLabel="Ψ (W/mK)"
                            onEdit={openEditComp} onDelete={deleteComp} onNew={() => openNewComp('distanziatore')} />
                    </TabsContent>
                </Tabs>
            </div>

            {/* Component Dialog */}
            <Dialog open={compDialog} onOpenChange={setCompDialog}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{editingComp ? 'Modifica' : 'Nuovo'} Componente</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Codice</Label>
                                <Input data-testid="input-comp-codice" value={compForm.codice}
                                    onChange={e => setCompForm(f => ({ ...f, codice: e.target.value.toUpperCase() }))} />
                            </div>
                            <div>
                                <Label className="text-xs">Tipo</Label>
                                <Select value={compForm.tipo} onValueChange={v => setCompForm(f => ({ ...f, tipo: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="vetro">Vetro</SelectItem>
                                        <SelectItem value="telaio">Telaio</SelectItem>
                                        <SelectItem value="distanziatore">Distanziatore</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs">Descrizione</Label>
                            <Input data-testid="input-comp-label" value={compForm.label}
                                onChange={e => setCompForm(f => ({ ...f, label: e.target.value }))} />
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                            {compForm.tipo === 'vetro' && (
                                <>
                                    <div>
                                        <Label className="text-xs">Ug (W/m²K)</Label>
                                        <Input type="number" step="0.01" value={compForm.ug}
                                            onChange={e => setCompForm(f => ({ ...f, ug: +e.target.value }))} />
                                    </div>
                                    <div>
                                        <Label className="text-xs">Spessore (mm)</Label>
                                        <Input type="number" value={compForm.thickness_mm}
                                            onChange={e => setCompForm(f => ({ ...f, thickness_mm: +e.target.value }))} />
                                    </div>
                                </>
                            )}
                            {compForm.tipo === 'telaio' && (
                                <div>
                                    <Label className="text-xs">Uf (W/m²K)</Label>
                                    <Input type="number" step="0.01" value={compForm.uf}
                                        onChange={e => setCompForm(f => ({ ...f, uf: +e.target.value }))} />
                                </div>
                            )}
                            {compForm.tipo === 'distanziatore' && (
                                <div>
                                    <Label className="text-xs">Ψ (W/mK)</Label>
                                    <Input type="number" step="0.001" value={compForm.psi}
                                        onChange={e => setCompForm(f => ({ ...f, psi: +e.target.value }))} />
                                </div>
                            )}
                            <div>
                                <Label className="text-xs">Produttore</Label>
                                <Input value={compForm.produttore}
                                    onChange={e => setCompForm(f => ({ ...f, produttore: e.target.value }))} />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCompDialog(false)}>Annulla</Button>
                        <Button data-testid="btn-save-comp" onClick={saveComp} disabled={savingComp}
                            className="bg-[#0055FF] text-white">{savingComp ? 'Salvataggio...' : 'Salva'}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}

/* ─── Sub-component: Component Table ─── */
function CompTable({ title, icon, items, valueKey, valueLabel, onEdit, onDelete, onNew }) {
    return (
        <Card className="border-gray-200">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">{icon} {title}</CardTitle>
                    <Button variant="ghost" size="sm" onClick={onNew}><Plus className="h-3 w-3 mr-1" />Aggiungi</Button>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-slate-50">
                            <TableHead className="text-xs">Codice</TableHead>
                            <TableHead className="text-xs">Descrizione</TableHead>
                            <TableHead className="text-xs text-right">{valueLabel}</TableHead>
                            <TableHead className="text-xs">Produttore</TableHead>
                            <TableHead className="w-[80px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {items.length === 0 ? (
                            <TableRow><TableCell colSpan={5} className="text-center py-4 text-sm text-slate-400">Nessun componente</TableCell></TableRow>
                        ) : items.map(c => (
                            <TableRow key={c.comp_id} className="hover:bg-slate-50">
                                <TableCell className="font-mono text-xs text-[#0055FF]">{c.codice}</TableCell>
                                <TableCell className="text-sm">{c.label}</TableCell>
                                <TableCell className="text-right font-mono font-semibold">{c[valueKey]}</TableCell>
                                <TableCell className="text-sm text-slate-500">{c.produttore || '-'}</TableCell>
                                <TableCell>
                                    <div className="flex gap-1">
                                        <Button variant="ghost" size="sm" onClick={() => onEdit(c)}>
                                            <Pencil className="h-3.5 w-3.5 text-slate-500" />
                                        </Button>
                                        <Button variant="ghost" size="sm" onClick={() => onDelete(c)}>
                                            <Trash2 className="h-3.5 w-3.5 text-red-500" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
