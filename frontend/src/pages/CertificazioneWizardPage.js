/**
 * Certificazione CE Wizard - 3-step wizard for EN 1090 / EN 13241
 */
import { useState, useEffect } from 'react';
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
    Save, ArrowLeft, ArrowRight, Shield, FileDown, CheckCircle2,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STEPS = [
    { num: 1, label: 'Progetto' },
    { num: 2, label: 'Norma' },
    { num: 3, label: 'Specifiche Tecniche' },
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
            air_permeability: '',
            water_tightness: '',
            wind_resistance: '',
            mechanical_resistance: 'Conforme',
            safe_opening: 'Conforme',
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
                        additional_notes: data.technical_specs?.additional_notes || '',
                    },
                });
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

    const handleSave = async () => {
        if (!formData.project_name.trim()) {
            toast.error('Inserisci il nome del progetto');
            setStep(1);
            return;
        }
        setSaving(true);
        try {
            const payload = {
                ...formData,
                client_id: formData.client_id || null,
                distinta_id: formData.distinta_id || null,
            };
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
        if (!savedId) {
            await handleSave();
        }
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
                                    step === s.num
                                        ? 'bg-[#0055FF] text-white'
                                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
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
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg">1. Seleziona Progetto</CardTitle>
                        </CardHeader>
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
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg">2. Seleziona Norma</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            <div className="grid grid-cols-2 gap-6">
                                <button
                                    data-testid="select-en1090"
                                    onClick={() => updateField('standard', 'EN 1090-1')}
                                    className={`p-6 rounded-lg border-2 text-left transition-all ${
                                        formData.standard === 'EN 1090-1'
                                            ? 'border-[#0055FF] bg-blue-50'
                                            : 'border-gray-200 hover:border-slate-300'
                                    }`}
                                >
                                    <div className="flex items-center gap-3 mb-3">
                                        <Shield className={`h-8 w-8 ${formData.standard === 'EN 1090-1' ? 'text-[#0055FF]' : 'text-slate-400'}`} />
                                        <div>
                                            <h3 className="font-bold text-lg text-[#1E293B]">EN 1090-1</h3>
                                            <Badge variant="outline" className="font-mono">Strutturale</Badge>
                                        </div>
                                    </div>
                                    <p className="text-sm text-slate-600">
                                        Componenti strutturali in acciaio e alluminio. Scale, soppalchi, strutture portanti, pensiline.
                                    </p>
                                </button>
                                <button
                                    data-testid="select-en13241"
                                    onClick={() => updateField('standard', 'EN 13241')}
                                    className={`p-6 rounded-lg border-2 text-left transition-all ${
                                        formData.standard === 'EN 13241'
                                            ? 'border-[#0055FF] bg-blue-50'
                                            : 'border-gray-200 hover:border-slate-300'
                                    }`}
                                >
                                    <div className="flex items-center gap-3 mb-3">
                                        <Shield className={`h-8 w-8 ${formData.standard === 'EN 13241' ? 'text-[#0055FF]' : 'text-slate-400'}`} />
                                        <div>
                                            <h3 className="font-bold text-lg text-[#1E293B]">EN 13241</h3>
                                            <Badge variant="outline" className="font-mono">Cancelli / Porte</Badge>
                                        </div>
                                    </div>
                                    <p className="text-sm text-slate-600">
                                        Porte, cancelli e barriere industriali, commerciali e da garage. Scorrevoli, battenti, sezionali.
                                    </p>
                                </button>
                            </div>
                            <div className="flex justify-between">
                                <Button variant="outline" onClick={() => setStep(1)}>
                                    <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                                </Button>
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
                            <CardTitle className="text-lg">
                                3. Specifiche Tecniche — {formData.standard}
                            </CardTitle>
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
                                            <Input data-testid="input-mech-resistance" value={formData.technical_specs.mechanical_resistance} onChange={(e) => updateSpec('mechanical_resistance', e.target.value)} className="mt-1" />
                                        </div>
                                        <div>
                                            <Label>Sicurezza Apertura</Label>
                                            <Input value={formData.technical_specs.safe_opening} onChange={(e) => updateSpec('safe_opening', e.target.value)} className="mt-1" />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div>
                                            <Label>Permeabilita' all'Aria</Label>
                                            <Input value={formData.technical_specs.air_permeability || ''} onChange={(e) => updateSpec('air_permeability', e.target.value)} placeholder="Non determinata" className="mt-1" />
                                        </div>
                                        <div>
                                            <Label>Tenuta all'Acqua</Label>
                                            <Input value={formData.technical_specs.water_tightness || ''} onChange={(e) => updateSpec('water_tightness', e.target.value)} placeholder="Non determinata" className="mt-1" />
                                        </div>
                                        <div>
                                            <Label>Resistenza al Vento</Label>
                                            <Input value={formData.technical_specs.wind_resistance || ''} onChange={(e) => updateSpec('wind_resistance', e.target.value)} placeholder="Non determinata" className="mt-1" />
                                        </div>
                                    </div>
                                </>
                            )}

                            <Separator />

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label>Durabilita' (Protezione anticorrosione)</Label>
                                    <Select value={formData.technical_specs.durability} onValueChange={(v) => updateSpec('durability', v)}>
                                        <SelectTrigger data-testid="select-durability" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {DURABILITY_OPTIONS.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label>Sostanze Pericolose</Label>
                                    <Input data-testid="input-dangerous" value={formData.technical_specs.dangerous_substances} onChange={(e) => updateSpec('dangerous_substances', e.target.value)} className="mt-1" />
                                </div>
                            </div>

                            <div>
                                <Label>Note Aggiuntive</Label>
                                <Textarea value={formData.technical_specs.additional_notes || ''} onChange={(e) => updateSpec('additional_notes', e.target.value)} placeholder="Note tecniche aggiuntive..." rows={2} className="mt-1" />
                            </div>

                            {isEditing && (
                                <div>
                                    <Label>Stato</Label>
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

                            <Separator />

                            <div className="flex justify-between items-center">
                                <Button variant="outline" onClick={() => setStep(2)}>
                                    <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                                </Button>
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
