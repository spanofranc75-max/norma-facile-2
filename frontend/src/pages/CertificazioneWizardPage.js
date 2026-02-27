/**
 * Certificazione CE Wizard - 4-step wizard with Thermal Calculator
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    Save, ArrowLeft, ArrowRight, Shield, FileDown, CheckCircle2, Thermometer, AlertTriangle,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STEPS = [
    { num: 1, label: 'Progetto' },
    { num: 2, label: 'Norma' },
    { num: 3, label: 'Specifiche' },
    { num: 4, label: 'Calcolo Termico' },
];

const DURABILITY_OPTIONS = [
    "Classe C1 (molto bassa)",
    "Classe C2 (bassa)",
    "Classe C3 (media)",
    "Classe C4 (alta)",
    "Classe C5-I (molto alta, industriale)",
    "Classe C5-M (molto alta, marina)",
];

export default function CertificazioneWizardPage() {
    const navigate = useNavigate();
    const { certId } = useParams();
    const isEditing = !!certId;

    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [savedId, setSavedId] = useState(certId || null);
    const [clients, setClients] = useState([]);
    const [distinte, setDistinte] = useState([]);

    // Thermal reference data
    const [thermalRef, setThermalRef] = useState({ glass_types: [], frame_types: [], spacer_types: [], zone_limits: {} });
    const [thermalResult, setThermalResult] = useState(null);
    const [thermalCalcing, setThermalCalcing] = useState(false);

    const [formData, setFormData] = useState({
        project_name: '',
        distinta_id: '',
        client_id: '',
        standard: 'EN 1090-1',
        product_description: '',
        product_type: '',
        status: 'bozza',
        notes: '',
        technical_specs: {
            execution_class: 'EXC2',
            durability: 'Classe C3 (media)',
            reaction_to_fire: 'Classe A1 (non combustibile)',
            dangerous_substances: 'Nessuna',
            air_permeability: '', water_tightness: '', wind_resistance: '',
            mechanical_resistance: 'Conforme', safe_opening: 'Conforme',
            thermal_enabled: false,
            thermal_uw: null, thermal_glass_id: 'doppio_be_argon', thermal_frame_id: 'acciaio_standard',
            thermal_spacer_id: 'alluminio', thermal_height_mm: 2100, thermal_width_mm: 3000,
            thermal_frame_width_mm: 80,
            thermal_glass_label: null, thermal_frame_label: null, thermal_spacer_label: null,
            additional_notes: '',
        },
    });

    useEffect(() => {
        const fetch = async () => {
            try {
                const [cData, dData] = await Promise.all([
                    apiRequest('/clients/'),
                    apiRequest('/distinte/'),
                ]);
                setClients(cData.clients || []);
                setDistinte(dData.distinte || []);
            } catch { /* ignore */ }
        };
        fetch();
    }, []);

    // Fetch thermal reference data
    useEffect(() => {
        const fetchThermal = async () => {
            try {
                const data = await apiRequest('/certificazioni/thermal/reference-data');
                setThermalRef(data);
            } catch { /* ignore */ }
        };
        fetchThermal();
    }, []);

    useEffect(() => {
        if (!isEditing) return;
        const fetchCert = async () => {
            try {
                const data = await apiRequest(`/certificazioni/${certId}`);
                setFormData({
                    project_name: data.project_name || '',
                    distinta_id: data.distinta_id || '',
                    client_id: data.client_id || '',
                    standard: data.standard || 'EN 1090-1',
                    product_description: data.product_description || '',
                    product_type: data.product_type || '',
                    status: data.status || 'bozza',
                    notes: data.notes || '',
                    technical_specs: {
                        execution_class: data.technical_specs?.execution_class || 'EXC2',
                        durability: data.technical_specs?.durability || 'Classe C3 (media)',
                        reaction_to_fire: data.technical_specs?.reaction_to_fire || 'Classe A1 (non combustibile)',
                        dangerous_substances: data.technical_specs?.dangerous_substances || 'Nessuna',
                        air_permeability: data.technical_specs?.air_permeability || '',
                        water_tightness: data.technical_specs?.water_tightness || '',
                        wind_resistance: data.technical_specs?.wind_resistance || '',
                        mechanical_resistance: data.technical_specs?.mechanical_resistance || 'Conforme',
                        safe_opening: data.technical_specs?.safe_opening || 'Conforme',
                        thermal_enabled: data.technical_specs?.thermal_enabled || false,
                        thermal_uw: data.technical_specs?.thermal_uw || null,
                        thermal_glass_id: data.technical_specs?.thermal_glass_id || 'doppio_be_argon',
                        thermal_frame_id: data.technical_specs?.thermal_frame_id || 'acciaio_standard',
                        thermal_spacer_id: data.technical_specs?.thermal_spacer_id || 'alluminio',
                        thermal_height_mm: data.technical_specs?.thermal_height_mm || 2100,
                        thermal_width_mm: data.technical_specs?.thermal_width_mm || 3000,
                        thermal_frame_width_mm: data.technical_specs?.thermal_frame_width_mm || 80,
                        thermal_glass_label: data.technical_specs?.thermal_glass_label || null,
                        thermal_frame_label: data.technical_specs?.thermal_frame_label || null,
                        thermal_spacer_label: data.technical_specs?.thermal_spacer_label || null,
                        additional_notes: data.technical_specs?.additional_notes || '',
                    },
                });
                if (data.technical_specs?.thermal_uw) {
                    setThermalResult({ uw: data.technical_specs.thermal_uw });
                }
            } catch {
                toast.error('Errore nel caricamento');
                navigate('/certificazioni');
            } finally {
                setLoading(false);
            }
        };
        fetchCert();
    }, [isEditing, certId, navigate]);

    const updateField = (field, value) => setFormData(p => ({ ...p, [field]: value }));
    const updateSpec = (field, value) => setFormData(p => ({ ...p, technical_specs: { ...p.technical_specs, [field]: value } }));

    // Calculate Uw
    const handleCalcUw = useCallback(async () => {
        const ts = formData.technical_specs;
        if (!ts.thermal_height_mm || !ts.thermal_width_mm) return;
        setThermalCalcing(true);
        try {
            const result = await apiRequest('/certificazioni/thermal/calculate', {
                method: 'POST',
                body: {
                    height_mm: parseFloat(ts.thermal_height_mm) || 2100,
                    width_mm: parseFloat(ts.thermal_width_mm) || 3000,
                    frame_width_mm: parseFloat(ts.thermal_frame_width_mm) || 80,
                    glass_id: ts.thermal_glass_id,
                    frame_id: ts.thermal_frame_id,
                    spacer_id: ts.thermal_spacer_id,
                },
            });
            setThermalResult(result);
            setFormData(p => ({
                ...p,
                technical_specs: {
                    ...p.technical_specs,
                    thermal_enabled: true,
                    thermal_uw: result.uw,
                    thermal_glass_label: result.glass_label,
                    thermal_frame_label: result.frame_label,
                    thermal_spacer_label: result.spacer_label,
                },
            }));
        } catch (err) {
            toast.error('Errore nel calcolo termico');
        } finally {
            setThermalCalcing(false);
        }
    }, [formData.technical_specs]);

    const handleSave = async () => {
        if (!formData.project_name.trim()) {
            toast.error('Inserisci il nome del progetto');
            setStep(1);
            return;
        }
        setSaving(true);
        try {
            const payload = { ...formData, client_id: formData.client_id || null, distinta_id: formData.distinta_id || null };
            if (isEditing || savedId) {
                payload.status = formData.status;
                await apiRequest(`/certificazioni/${savedId}`, { method: 'PUT', body: payload });
                toast.success('Certificazione aggiornata');
            } else {
                const res = await apiRequest('/certificazioni/', { method: 'POST', body: payload });
                setSavedId(res.cert_id);
                toast.success('Certificazione creata');
            }
            setSaved(true);
        } catch (err) {
            toast.error(err.message || 'Errore nel salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleGeneratePdf = async () => {
        if (!savedId) await handleSave();
        if (savedId) {
            const backendUrl = process.env.REACT_APP_BACKEND_URL;
            window.open(`${backendUrl}/api/certificazioni/${savedId}/fascicolo-pdf`, '_blank');
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                </div>
            </DashboardLayout>
        );
    }

    const isEN13241 = formData.standard === 'EN 13241';
    const uwValue = thermalResult?.uw ?? formData.technical_specs.thermal_uw;
    const uwExceedsLimit = uwValue > 1.3;

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="cert-wizard">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button data-testid="btn-back" variant="outline" onClick={() => navigate('/certificazioni')} className="h-10">
                            <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                        </Button>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">
                            <Shield className="inline h-6 w-6 text-[#0055FF] mr-2" />
                            {isEditing ? 'Modifica Certificazione CE' : 'Nuova Certificazione CE'}
                        </h1>
                    </div>
                    <div className="flex gap-3">
                        {(saved || isEditing) && (
                            <Button data-testid="btn-generate-pdf" variant="outline" onClick={handleGeneratePdf} className="h-10 border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                <FileDown className="h-4 w-4 mr-2" /> Genera Fascicolo Tecnico
                            </Button>
                        )}
                        <Button data-testid="btn-save" onClick={handleSave} disabled={saving} className="h-10 bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Save className="h-4 w-4 mr-2" /> {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </div>
                </div>

                {/* Stepper */}
                <div className="flex items-center justify-center gap-2">
                    {STEPS.map((s, i) => (
                        <div key={s.num} className="flex items-center gap-2">
                            <button
                                data-testid={`step-${s.num}`}
                                onClick={() => setStep(s.num)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                                    step === s.num ? 'bg-[#0055FF] text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                }`}
                            >
                                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                    step === s.num ? 'bg-white text-[#0055FF]' : 'bg-slate-300 text-white'
                                }`}>{s.num}</span>
                                {s.label}
                            </button>
                            {i < STEPS.length - 1 && <div className="w-8 h-px bg-slate-300" />}
                        </div>
                    ))}
                </div>

                {/* Step 1: Project */}
                {step === 1 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200"><CardTitle className="text-lg">1. Seleziona Progetto</CardTitle></CardHeader>
                        <CardContent className="pt-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label>Nome Progetto *</Label>
                                    <Input data-testid="input-project-name" value={formData.project_name} onChange={(e) => updateField('project_name', e.target.value)} placeholder="es. Cancello Rossi" className="mt-1" />
                                </div>
                                <div>
                                    <Label>Cliente</Label>
                                    <Select value={formData.client_id || 'none'} onValueChange={(v) => updateField('client_id', v === 'none' ? '' : v)}>
                                        <SelectTrigger data-testid="select-client" className="mt-1"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="none">Nessun cliente</SelectItem>
                                            {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label>Distinta Collegata</Label>
                                    <Select value={formData.distinta_id || 'none'} onValueChange={(v) => updateField('distinta_id', v === 'none' ? '' : v)}>
                                        <SelectTrigger data-testid="select-distinta" className="mt-1"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="none">Nessuna distinta</SelectItem>
                                            {distinte.map(d => <SelectItem key={d.distinta_id} value={d.distinta_id}>{d.name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label>Tipo Prodotto</Label>
                                    <Input data-testid="input-product-type" value={formData.product_type} onChange={(e) => updateField('product_type', e.target.value)} placeholder="es. Cancello scorrevole in acciaio S235" className="mt-1" />
                                </div>
                            </div>
                            <div>
                                <Label>Descrizione Prodotto</Label>
                                <Textarea data-testid="input-description" value={formData.product_description} onChange={(e) => updateField('product_description', e.target.value)} placeholder="Descrizione dettagliata del prodotto..." rows={3} className="mt-1" />
                            </div>
                            <div className="flex justify-end">
                                <Button data-testid="btn-next-1" onClick={() => setStep(2)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                    Avanti <ArrowRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 2: Standard */}
                {step === 2 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200"><CardTitle className="text-lg">2. Seleziona Norma</CardTitle></CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            <div className="grid grid-cols-2 gap-6">
                                {[
                                    { val: 'EN 1090-1', title: 'EN 1090-1', tag: 'Strutturale', desc: 'Componenti strutturali in acciaio e alluminio. Scale, soppalchi, strutture portanti, pensiline.' },
                                    { val: 'EN 13241', title: 'EN 13241', tag: 'Cancelli / Porte', desc: 'Porte, cancelli e barriere industriali, commerciali e da garage. Scorrevoli, battenti, sezionali.' },
                                ].map(s => (
                                    <button key={s.val} data-testid={`select-${s.val.replace(/\s/g,'')}`} onClick={() => updateField('standard', s.val)}
                                        className={`p-6 rounded-lg border-2 text-left transition-all ${formData.standard === s.val ? 'border-[#0055FF] bg-blue-50' : 'border-gray-200 hover:border-slate-300'}`}>
                                        <div className="flex items-center gap-3 mb-3">
                                            <Shield className={`h-8 w-8 ${formData.standard === s.val ? 'text-[#0055FF]' : 'text-slate-400'}`} />
                                            <div>
                                                <h3 className="font-bold text-lg text-[#1E293B]">{s.title}</h3>
                                                <Badge variant="outline" className="font-mono">{s.tag}</Badge>
                                            </div>
                                        </div>
                                        <p className="text-sm text-slate-600">{s.desc}</p>
                                    </button>
                                ))}
                            </div>
                            <div className="flex justify-between">
                                <Button variant="outline" onClick={() => setStep(1)}><ArrowLeft className="h-4 w-4 mr-2" /> Indietro</Button>
                                <Button data-testid="btn-next-2" onClick={() => setStep(3)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                    Avanti <ArrowRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 3: Technical Specs */}
                {step === 3 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg">3. Specifiche Tecniche — {formData.standard}</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-4">
                            {!isEN13241 && (
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <Label>Classe di Esecuzione</Label>
                                        <Select value={formData.technical_specs.execution_class} onValueChange={(v) => updateSpec('execution_class', v)}>
                                            <SelectTrigger data-testid="select-exc" className="mt-1"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="EXC1">EXC1 - Strutture semplici</SelectItem>
                                                <SelectItem value="EXC2">EXC2 - Strutture normali (default)</SelectItem>
                                                <SelectItem value="EXC3">EXC3 - Strutture complesse</SelectItem>
                                                <SelectItem value="EXC4">EXC4 - Strutture critiche</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label>Reazione al Fuoco</Label>
                                        <Input value={formData.technical_specs.reaction_to_fire} onChange={(e) => updateSpec('reaction_to_fire', e.target.value)} className="mt-1" />
                                    </div>
                                </div>
                            )}
                            {isEN13241 && (
                                <>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <Label>Resistenza Meccanica</Label>
                                            <Input value={formData.technical_specs.mechanical_resistance} onChange={(e) => updateSpec('mechanical_resistance', e.target.value)} className="mt-1" />
                                        </div>
                                        <div>
                                            <Label>Sicurezza Apertura</Label>
                                            <Input value={formData.technical_specs.safe_opening} onChange={(e) => updateSpec('safe_opening', e.target.value)} className="mt-1" />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div><Label>Permeabilita all'Aria</Label><Input value={formData.technical_specs.air_permeability || ''} onChange={(e) => updateSpec('air_permeability', e.target.value)} placeholder="Non determinata" className="mt-1" /></div>
                                        <div><Label>Tenuta all'Acqua</Label><Input value={formData.technical_specs.water_tightness || ''} onChange={(e) => updateSpec('water_tightness', e.target.value)} placeholder="Non determinata" className="mt-1" /></div>
                                        <div><Label>Resistenza al Vento</Label><Input value={formData.technical_specs.wind_resistance || ''} onChange={(e) => updateSpec('wind_resistance', e.target.value)} placeholder="Non determinata" className="mt-1" /></div>
                                    </div>
                                </>
                            )}
                            <Separator />
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label>Durabilita (Protezione anticorrosione)</Label>
                                    <Select value={formData.technical_specs.durability} onValueChange={(v) => updateSpec('durability', v)}>
                                        <SelectTrigger data-testid="select-durability" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>{DURABILITY_OPTIONS.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label>Sostanze Pericolose</Label>
                                    <Input value={formData.technical_specs.dangerous_substances} onChange={(e) => updateSpec('dangerous_substances', e.target.value)} className="mt-1" />
                                </div>
                            </div>
                            {isEditing && (
                                <div><Label>Stato</Label>
                                    <Select value={formData.status} onValueChange={(v) => updateField('status', v)}>
                                        <SelectTrigger className="mt-1 w-[200px]"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="bozza">Bozza</SelectItem>
                                            <SelectItem value="emessa">Emessa</SelectItem>
                                            <SelectItem value="revisionata">Revisionata</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}
                            <div className="flex justify-between">
                                <Button variant="outline" onClick={() => setStep(2)}><ArrowLeft className="h-4 w-4 mr-2" /> Indietro</Button>
                                <Button data-testid="btn-next-3" onClick={() => setStep(4)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                    Avanti: Calcolo Termico <ArrowRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 4: Thermal Calculator */}
                {step === 4 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Thermometer className="h-5 w-5 text-[#0055FF]" />
                                4. Calcolatore Termico (Uw) — EN ISO 10077-1
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            <p className="text-sm text-slate-600">
                                Calcola la trasmittanza termica (Uw) del serramento per verificare la conformita Ecobonus.
                                Formula: <span className="font-mono text-[#0055FF]">Uw = (Ag*Ug + Af*Uf + lg*Psi) / (Ag + Af)</span>
                            </p>

                            {/* Dimensions */}
                            <div>
                                <h3 className="font-semibold text-[#1E293B] mb-3">Dimensioni Serramento</h3>
                                <div className="grid grid-cols-3 gap-4">
                                    <div>
                                        <Label>Altezza H (mm)</Label>
                                        <Input data-testid="thermal-height" type="number" value={formData.technical_specs.thermal_height_mm || ''} onChange={(e) => updateSpec('thermal_height_mm', parseFloat(e.target.value) || 0)} className="mt-1 font-mono" />
                                    </div>
                                    <div>
                                        <Label>Larghezza L (mm)</Label>
                                        <Input data-testid="thermal-width" type="number" value={formData.technical_specs.thermal_width_mm || ''} onChange={(e) => updateSpec('thermal_width_mm', parseFloat(e.target.value) || 0)} className="mt-1 font-mono" />
                                    </div>
                                    <div>
                                        <Label>Larghezza Telaio (mm)</Label>
                                        <Input data-testid="thermal-frame-width" type="number" value={formData.technical_specs.thermal_frame_width_mm || ''} onChange={(e) => updateSpec('thermal_frame_width_mm', parseFloat(e.target.value) || 0)} className="mt-1 font-mono" />
                                    </div>
                                </div>
                            </div>

                            {/* Selections */}
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <Label>Tipo Vetro / Pannello</Label>
                                    <Select value={formData.technical_specs.thermal_glass_id} onValueChange={(v) => updateSpec('thermal_glass_id', v)}>
                                        <SelectTrigger data-testid="thermal-glass" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {thermalRef.glass_types.map(g => (
                                                <SelectItem key={g.id} value={g.id}>
                                                    {g.label} (Ug={g.ug})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label>Tipo Telaio / Profilo</Label>
                                    <Select value={formData.technical_specs.thermal_frame_id} onValueChange={(v) => updateSpec('thermal_frame_id', v)}>
                                        <SelectTrigger data-testid="thermal-frame" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {thermalRef.frame_types.map(f => (
                                                <SelectItem key={f.id} value={f.id}>
                                                    {f.label} (Uf={f.uf})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label>Canalina Distanziale</Label>
                                    <Select value={formData.technical_specs.thermal_spacer_id} onValueChange={(v) => updateSpec('thermal_spacer_id', v)}>
                                        <SelectTrigger data-testid="thermal-spacer" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {thermalRef.spacer_types.map(s => (
                                                <SelectItem key={s.id} value={s.id}>
                                                    {s.label} (Psi={s.psi})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {/* Calculate Button */}
                            <Button data-testid="btn-calc-uw" onClick={handleCalcUw} disabled={thermalCalcing} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                <Thermometer className="h-4 w-4 mr-2" />
                                {thermalCalcing ? 'Calcolo in corso...' : 'Calcola Uw'}
                            </Button>

                            {/* Result */}
                            {thermalResult && (
                                <div className={`p-6 rounded-lg border-2 ${uwExceedsLimit ? 'border-red-300 bg-red-50' : 'border-emerald-300 bg-emerald-50'}`}>
                                    <div className="flex items-center justify-between mb-4">
                                        <div>
                                            <p className="text-sm text-slate-600 mb-1">Trasmittanza Termica</p>
                                            <p data-testid="uw-value" className={`text-4xl font-mono font-bold ${uwExceedsLimit ? 'text-red-600' : 'text-emerald-600'}`}>
                                                Uw = {thermalResult.uw} <span className="text-lg">W/m2K</span>
                                            </p>
                                        </div>
                                        {uwExceedsLimit ? (
                                            <div className="flex items-center gap-2 px-4 py-2 bg-red-100 rounded-lg">
                                                <AlertTriangle className="h-5 w-5 text-red-600" />
                                                <span className="text-sm font-bold text-red-700">NON detraibile Ecobonus</span>
                                            </div>
                                        ) : (
                                            <div className="flex items-center gap-2 px-4 py-2 bg-emerald-100 rounded-lg">
                                                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                                <span className="text-sm font-bold text-emerald-700">Detraibile Ecobonus (Zona E)</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Detail grid */}
                                    <div className="grid grid-cols-4 gap-3 text-sm">
                                        <div className="bg-white p-3 rounded border">
                                            <p className="text-slate-500">Area vetro (Ag)</p>
                                            <p className="font-mono font-semibold text-[#0055FF]">{thermalResult.ag} m2</p>
                                        </div>
                                        <div className="bg-white p-3 rounded border">
                                            <p className="text-slate-500">Area telaio (Af)</p>
                                            <p className="font-mono font-semibold text-[#0055FF]">{thermalResult.af} m2</p>
                                        </div>
                                        <div className="bg-white p-3 rounded border">
                                            <p className="text-slate-500">Perimetro vetro (lg)</p>
                                            <p className="font-mono font-semibold text-[#0055FF]">{thermalResult.lg} m</p>
                                        </div>
                                        <div className="bg-white p-3 rounded border">
                                            <p className="text-slate-500">Area totale</p>
                                            <p className="font-mono font-semibold text-[#0055FF]">{thermalResult.total_area} m2</p>
                                        </div>
                                    </div>

                                    {/* Zone limits */}
                                    {thermalResult.ecobonus_eligible && (
                                        <div className="mt-4">
                                            <p className="text-sm text-slate-600 mb-2">Conformita per zona climatica:</p>
                                            <div className="flex gap-2">
                                                {Object.entries(thermalResult.ecobonus_eligible).map(([zone, ok]) => (
                                                    <Badge key={zone} className={ok ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}>
                                                        Zona {zone}: {ok ? 'OK' : 'NO'} ({thermalRef.zone_limits?.[zone]} W/m2K)
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {thermalResult.warnings?.length > 0 && (
                                        <div className="mt-3 p-3 bg-red-100 rounded-lg border border-red-200">
                                            {thermalResult.warnings.map((w, i) => (
                                                <p key={i} className="text-sm text-red-700 font-medium flex items-center gap-2">
                                                    <AlertTriangle className="h-4 w-4 shrink-0" /> {w}
                                                </p>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            <Separator />

                            <div className="flex justify-between items-center">
                                <Button variant="outline" onClick={() => setStep(3)}><ArrowLeft className="h-4 w-4 mr-2" /> Indietro</Button>
                                <div className="flex gap-3">
                                    <Button data-testid="btn-save-final" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                        <Save className="h-4 w-4 mr-2" /> {saving ? 'Salvataggio...' : 'Salva Certificazione'}
                                    </Button>
                                    <Button data-testid="btn-generate-pdf-final" onClick={handleGeneratePdf} variant="outline" className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                        <FileDown className="h-4 w-4 mr-2" /> Genera Fascicolo Tecnico
                                    </Button>
                                </div>
                            </div>

                            {saved && (
                                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                    <span className="text-emerald-700 font-medium">Certificazione salvata. Puoi generare il fascicolo tecnico PDF.</span>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}
            </div>
        </DashboardLayout>
    );
}
