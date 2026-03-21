/**
 * POS Wizard - 3-step wizard for Piano Operativo di Sicurezza
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    Save, ArrowLeft, ArrowRight, HardHat, FileDown, Sparkles, Loader2, CheckCircle2, Shield, FileCheck, FileX, AlertTriangle, Download,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STEPS = [
    { num: 1, label: 'Cantiere' },
    { num: 2, label: 'Lavorazioni' },
    { num: 3, label: 'Macchine & DPI' },
    { num: 4, label: 'Documenti' },
];

export default function PosWizardPage() {
    const navigate = useNavigate();
    const { posId } = useParams();
    const isEditing = !!posId;

    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [saved, setSaved] = useState(false);
    const [savedId, setSavedId] = useState(posId || null);
    const [clients, setClients] = useState([]);
    const [refData, setRefData] = useState({ rischi: [], macchine: [], dpi: [] });
    const [globalDocs, setGlobalDocs] = useState(null);
    const [posWorkers, setPosWorkers] = useState([]);
    const [selectedWorkers, setSelectedWorkers] = useState([]);

    const [formData, setFormData] = useState({
        project_name: '',
        client_id: '',
        status: 'bozza',
        cantiere: {
            address: '', city: '', duration_days: 30, start_date: '',
            committente: '', responsabile_lavori: '', coordinatore_sicurezza: '',
        },
        selected_risks: [],
        selected_machines: [],
        selected_dpi: [],
        ai_risk_assessment: null,
        notes: '',
    });

    // Fetch reference data
    useEffect(() => {
        const fetch = async () => {
            try {
                const [cData, rData] = await Promise.all([
                    apiRequest('/clients/'),
                    apiRequest('/sicurezza/rischi'),
                ]);
                setClients(cData.clients || []);
                setRefData(rData);
            } catch { /* ignore */ }
        };
        fetch();
    }, []);

    // Fetch global docs + workers for POS
    useEffect(() => {
        const fetchGlobal = async () => {
            try {
                const [docData, wData] = await Promise.all([
                    apiRequest('/company/documents/sicurezza-globali'),
                    apiRequest('/welders/per-pos'),
                ]);
                setGlobalDocs(docData);
                setPosWorkers(wData.workers || []);
            } catch { /* ignore */ }
        };
        fetchGlobal();
    }, []);

    // Auto-fill committente from client
    useEffect(() => {
        if (formData.client_id) {
            const client = clients.find(c => c.client_id === formData.client_id);
            if (client) {
                setFormData(p => ({
                    ...p,
                    cantiere: { ...p.cantiere, committente: client.business_name },
                }));
            }
        }
    }, [formData.client_id, clients]);

    // Fetch existing POS
    useEffect(() => {
        if (!isEditing) return;
        const fetchPos = async () => {
            try {
                const data = await apiRequest(`/sicurezza/${posId}`);
                setFormData({
                    project_name: data.project_name || '',
                    client_id: data.client_id || '',
                    status: data.status || 'bozza',
                    cantiere: data.cantiere || {
                        address: '', city: '', duration_days: 30, start_date: '',
                        committente: '', responsabile_lavori: '', coordinatore_sicurezza: '',
                    },
                    selected_risks: data.selected_risks || [],
                    selected_machines: data.selected_machines || [],
                    selected_dpi: data.selected_dpi || [],
                    ai_risk_assessment: data.ai_risk_assessment || null,
                    notes: data.notes || '',
                });
            } catch {
                toast.error('Errore nel caricamento');
                navigate('/sicurezza');
            } finally {
                setLoading(false);
            }
        };
        fetchPos();
    }, [isEditing, posId, navigate]);

    const updateField = (f, v) => setFormData(p => ({ ...p, [f]: v }));
    const updateCantiere = (f, v) => setFormData(p => ({ ...p, cantiere: { ...p.cantiere, [f]: v } }));

    const toggleItem = (list, id) => {
        setFormData(p => ({
            ...p,
            [list]: p[list].includes(id) ? p[list].filter(x => x !== id) : [...p[list], id],
        }));
    };

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
                cantiere: { ...formData.cantiere, duration_days: parseInt(formData.cantiere.duration_days) || 30 },
            };
            delete payload.ai_risk_assessment;

            if (isEditing || savedId) {
                await apiRequest(`/sicurezza/${savedId}`, { method: 'PUT', body: payload });
                toast.success('POS aggiornato');
            } else {
                const res = await apiRequest('/sicurezza/', { method: 'POST', body: payload });
                setSavedId(res.pos_id);
                toast.success('POS creato');
            }
            setSaved(true);
        } catch (err) {
            toast.error(err.message || 'Errore nel salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleGenerateAI = async () => {
        const id = savedId || posId;
        if (!id) {
            toast.error('Salva il POS prima di generare la valutazione');
            return;
        }
        if (formData.selected_risks.length === 0) {
            toast.error('Seleziona almeno una lavorazione');
            setStep(2);
            return;
        }
        setGenerating(true);
        try {
            await handleSave();
            const data = await apiRequest(`/sicurezza/${id}/genera-rischi`, { method: 'POST' });
            setFormData(p => ({ ...p, ai_risk_assessment: data.ai_risk_assessment }));
            toast.success('Valutazione rischi generata con AI');
        } catch (err) {
            toast.error(err.message || 'Errore nella generazione AI');
        } finally {
            setGenerating(false);
        }
    };

    const handleDownloadPdf = () => {
        const id = savedId || posId;
        if (!id) return;
        const backendUrl = process.env.REACT_APP_BACKEND_URL;
        window.open(`${backendUrl}/api/sicurezza/${id}/pdf`, '_blank');
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

    // Group items by category
    const groupBy = (items) => {
        const groups = {};
        items.forEach(item => {
            if (!groups[item.category]) groups[item.category] = [];
            groups[item.category].push(item);
        });
        return groups;
    };

    const rischiGrouped = groupBy(refData.rischi || []);
    const macchineGrouped = groupBy(refData.macchine || []);
    const dpiGrouped = groupBy(refData.dpi || []);

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="pos-wizard">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button data-testid="btn-back" variant="outline" onClick={() => navigate('/sicurezza')} className="h-10">
                            <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                        </Button>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">
                            <HardHat className="inline h-6 w-6 text-[#0055FF] mr-2" />
                            {isEditing ? 'Modifica POS' : 'Nuovo Piano Operativo di Sicurezza'}
                        </h1>
                    </div>
                    <div className="flex gap-3">
                        {(saved || isEditing) && (
                            <>
                                <Button data-testid="btn-generate-ai" variant="outline" onClick={handleGenerateAI} disabled={generating} className="h-10 border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                    {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                                    {generating ? 'Generazione...' : 'Genera Rischi (AI)'}
                                </Button>
                                <Button data-testid="btn-download-pdf" variant="outline" onClick={handleDownloadPdf} className="h-10 border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                    <FileDown className="h-4 w-4 mr-2" /> Genera POS (PDF)
                                </Button>
                            </>
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

                {/* Step 1: Cantiere */}
                {step === 1 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg">1. Dati Cantiere</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label>Nome Progetto *</Label>
                                    <Input data-testid="input-project" value={formData.project_name} onChange={(e) => updateField('project_name', e.target.value)} placeholder="es. Cancello Via Roma" className="mt-1" />
                                </div>
                                <div>
                                    <Label>Committente (Cliente)</Label>
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
                                    <Label>Indirizzo Cantiere</Label>
                                    <Input data-testid="input-address" value={formData.cantiere.address} onChange={(e) => updateCantiere('address', e.target.value)} placeholder="Via..." className="mt-1" />
                                </div>
                                <div>
                                    <Label>Citta</Label>
                                    <Input data-testid="input-city" value={formData.cantiere.city} onChange={(e) => updateCantiere('city', e.target.value)} placeholder="Citta..." className="mt-1" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <Label>Durata (giorni)</Label>
                                    <Input type="number" value={formData.cantiere.duration_days} onChange={(e) => updateCantiere('duration_days', e.target.value)} className="mt-1" min={1} />
                                </div>
                                <div>
                                    <Label>Data Inizio</Label>
                                    <Input type="date" value={formData.cantiere.start_date || ''} onChange={(e) => updateCantiere('start_date', e.target.value)} className="mt-1" />
                                </div>
                                <div>
                                    <Label>Committente</Label>
                                    <Input value={formData.cantiere.committente} onChange={(e) => updateCantiere('committente', e.target.value)} className="mt-1" />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label>Responsabile dei Lavori</Label>
                                    <Input value={formData.cantiere.responsabile_lavori} onChange={(e) => updateCantiere('responsabile_lavori', e.target.value)} className="mt-1" />
                                </div>
                                <div>
                                    <Label>Coordinatore Sicurezza</Label>
                                    <Input value={formData.cantiere.coordinatore_sicurezza} onChange={(e) => updateCantiere('coordinatore_sicurezza', e.target.value)} className="mt-1" />
                                </div>
                            </div>
                            <div className="flex justify-end">
                                <Button data-testid="btn-next-1" onClick={() => setStep(2)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                    Avanti <ArrowRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 2: Lavorazioni */}
                {step === 2 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg">2. Lavorazioni e Rischi</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            <p className="text-sm text-slate-600">Seleziona le lavorazioni previste in cantiere. L'AI generera la valutazione dei rischi per ciascuna.</p>
                            {Object.entries(rischiGrouped).map(([cat, items]) => (
                                <div key={cat}>
                                    <h3 className="font-semibold text-[#1E293B] mb-3">{cat}</h3>
                                    <div className="grid grid-cols-2 gap-3">
                                        {items.map(r => (
                                            <label key={r.id} data-testid={`risk-${r.id}`} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                                                formData.selected_risks.includes(r.id) ? 'border-[#0055FF] bg-blue-50' : 'border-gray-200 hover:bg-slate-50'
                                            }`}>
                                                <Checkbox checked={formData.selected_risks.includes(r.id)} onCheckedChange={() => toggleItem('selected_risks', r.id)} />
                                                <span className="text-sm">{r.label}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            <div className="flex justify-between items-center">
                                <Button variant="outline" onClick={() => setStep(1)}>
                                    <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                                </Button>
                                <div className="flex items-center gap-3">
                                    <Badge variant="outline" className="text-[#0055FF]">{formData.selected_risks.length} selezionati</Badge>
                                    <Button data-testid="btn-next-2" onClick={() => setStep(3)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                        Avanti <ArrowRight className="h-4 w-4 ml-2" />
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Step 3: Macchine & DPI */}
                {step === 3 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg">3. Macchine, Attrezzature e DPI</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            {/* Macchine */}
                            <div>
                                <h2 className="font-bold text-[#1E293B] text-base mb-4">Macchine e Attrezzature</h2>
                                {Object.entries(macchineGrouped).map(([cat, items]) => (
                                    <div key={cat} className="mb-4">
                                        <h3 className="font-semibold text-slate-600 text-sm mb-2">{cat}</h3>
                                        <div className="grid grid-cols-3 gap-2">
                                            {items.map(m => (
                                                <label key={m.id} data-testid={`machine-${m.id}`} className={`flex items-center gap-2 p-2 rounded border cursor-pointer text-sm transition-colors ${
                                                    formData.selected_machines.includes(m.id) ? 'border-[#0055FF] bg-blue-50' : 'border-gray-200 hover:bg-slate-50'
                                                }`}>
                                                    <Checkbox checked={formData.selected_machines.includes(m.id)} onCheckedChange={() => toggleItem('selected_machines', m.id)} />
                                                    {m.label}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <Separator />

                            {/* DPI */}
                            <div>
                                <h2 className="font-bold text-[#1E293B] text-base mb-4">Dispositivi di Protezione Individuale (DPI)</h2>
                                {Object.entries(dpiGrouped).map(([cat, items]) => (
                                    <div key={cat} className="mb-4">
                                        <h3 className="font-semibold text-slate-600 text-sm mb-2">{cat}</h3>
                                        <div className="grid grid-cols-3 gap-2">
                                            {items.map(d => (
                                                <label key={d.id} data-testid={`dpi-${d.id}`} className={`flex items-center gap-2 p-2 rounded border cursor-pointer text-sm transition-colors ${
                                                    formData.selected_dpi.includes(d.id) ? 'border-[#0055FF] bg-blue-50' : 'border-gray-200 hover:bg-slate-50'
                                                }`}>
                                                    <Checkbox checked={formData.selected_dpi.includes(d.id)} onCheckedChange={() => toggleItem('selected_dpi', d.id)} />
                                                    {d.label}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <Separator />

                            {/* AI Assessment preview */}
                            {formData.ai_risk_assessment && (
                                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                                    <div className="flex items-center gap-2 mb-3">
                                        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                        <span className="font-semibold text-emerald-700">Valutazione Rischi Generata</span>
                                    </div>
                                    <div className="text-sm text-slate-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                                        {formData.ai_risk_assessment.substring(0, 1000)}
                                        {formData.ai_risk_assessment.length > 1000 && '...'}
                                    </div>
                                </div>
                            )}

                            {isEditing && (
                                <div>
                                    <Label>Stato</Label>
                                    <Select value={formData.status} onValueChange={(v) => updateField('status', v)}>
                                        <SelectTrigger className="mt-1 w-[200px]"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="bozza">Bozza</SelectItem>
                                            <SelectItem value="completo">Completo</SelectItem>
                                            <SelectItem value="approvato">Approvato</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}

                            <div className="flex justify-between">
                                <Button variant="outline" onClick={() => setStep(2)}>
                                    <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                                </Button>
                                <Button data-testid="btn-next-3" onClick={() => setStep(4)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                    Avanti <ArrowRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}
                {/* Step 4: Operai & Documenti */}
                {step === 4 && (
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b border-gray-200">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Shield className="w-5 h-5 text-[#0055FF]" />
                                4. Operai in Cantiere & Documenti
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            {/* Worker selection */}
                            <div>
                                <h3 className="font-semibold text-[#1E293B] mb-2">Quali operai mandi in cantiere?</h3>
                                <p className="text-sm text-slate-500 mb-3">Seleziona gli operai. I loro attestati verranno inclusi automaticamente nel pacchetto ZIP.</p>
                                <div className="space-y-2" data-testid="pos-worker-list">
                                    {posWorkers.length === 0 ? (
                                        <p className="text-sm text-slate-400 text-center py-4">Nessun operaio in anagrafica. <a href="/operai" className="text-[#0055FF] underline">Aggiungi operai</a></p>
                                    ) : posWorkers.map(w => {
                                        const isSelected = selectedWorkers.includes(w.welder_id);
                                        const hasBlockers = w.blockers.length > 0;
                                        return (
                                            <label key={w.welder_id}
                                                data-testid={`pos-worker-${w.welder_id}`}
                                                className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                                                    isSelected
                                                        ? hasBlockers ? 'border-red-300 bg-red-50/50' : 'border-[#0055FF] bg-blue-50'
                                                        : 'border-gray-200 hover:bg-slate-50'
                                                }`}>
                                                <div className="flex items-center gap-3">
                                                    <Checkbox
                                                        checked={isSelected}
                                                        onCheckedChange={() => {
                                                            setSelectedWorkers(prev =>
                                                                prev.includes(w.welder_id)
                                                                    ? prev.filter(id => id !== w.welder_id)
                                                                    : [...prev, w.welder_id]
                                                            );
                                                        }}
                                                    />
                                                    <div>
                                                        <div className="font-medium text-sm text-slate-800">{w.name}</div>
                                                        <div className="text-xs text-slate-500 capitalize">{w.role || 'operaio'} — {w.stamp_id} — {w.cert_files_count} attestati</div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {hasBlockers ? (
                                                        <Badge className="bg-red-100 text-red-700 border border-red-200 text-[10px] gap-1">
                                                            <AlertTriangle className="w-3 h-3" /> {w.blockers.length} problemi
                                                        </Badge>
                                                    ) : w.warnings.length > 0 ? (
                                                        <Badge className="bg-amber-100 text-amber-700 border border-amber-200 text-[10px] gap-1">
                                                            {w.warnings.length} attenzione
                                                        </Badge>
                                                    ) : (
                                                        <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px]">
                                                            <CheckCircle2 className="w-3 h-3 mr-1" /> Idoneo
                                                        </Badge>
                                                    )}
                                                </div>
                                            </label>
                                        );
                                    })}
                                </div>
                                {/* Show warnings for selected workers */}
                                {selectedWorkers.length > 0 && (() => {
                                    const issues = posWorkers
                                        .filter(w => selectedWorkers.includes(w.welder_id))
                                        .flatMap(w => [
                                            ...w.blockers.map(b => ({ name: w.name, msg: b, level: 'error' })),
                                            ...w.warnings.map(b => ({ name: w.name, msg: b, level: 'warn' })),
                                        ]);
                                    if (issues.length === 0) return null;
                                    return (
                                        <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-sm space-y-1" data-testid="pos-worker-issues">
                                            <div className="font-medium text-red-700 flex items-center gap-1">
                                                <AlertTriangle className="w-4 h-4" /> Problemi rilevati:
                                            </div>
                                            {issues.map((iss, i) => (
                                                <div key={i} className={`text-xs ${iss.level === 'error' ? 'text-red-600' : 'text-amber-600'}`}>
                                                    <strong>{iss.name}</strong>: {iss.msg}
                                                </div>
                                            ))}
                                        </div>
                                    );
                                })()}
                            </div>

                            <Separator />

                            {/* Global docs summary */}
                            <div>
                                <h3 className="font-semibold text-[#1E293B] mb-2">Documenti Azienda</h3>
                                {globalDocs ? (() => {
                                    const documenti = globalDocs.documenti || {};
                                    const docTypes = ['durc', 'visura', 'white_list', 'patente_crediti', 'dvr'];
                                    return (
                                        <div className="grid grid-cols-5 gap-2" data-testid="pos-global-docs">
                                            {docTypes.map(dt => {
                                                const d = documenti[dt] || {};
                                                return (
                                                    <div key={dt} className={`p-2 rounded-lg border text-center text-xs ${
                                                        d.presente
                                                            ? d.is_expired ? 'bg-red-50 border-red-200 text-red-700'
                                                            : d.is_expiring ? 'bg-amber-50 border-amber-200 text-amber-700'
                                                            : 'bg-emerald-50 border-emerald-200 text-emerald-700'
                                                            : 'bg-slate-50 border-slate-200 text-slate-500'
                                                    }`}>
                                                        {d.presente ? <FileCheck className="w-4 h-4 mx-auto mb-1" /> : <FileX className="w-4 h-4 mx-auto mb-1" />}
                                                        <div className="font-medium">{d.label || dt}</div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    );
                                })() : <Loader2 className="w-5 h-5 animate-spin text-slate-400" />}
                            </div>

                            <Separator />

                            <div className="flex justify-between">
                                <Button variant="outline" onClick={() => setStep(3)}>
                                    <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                                </Button>
                                <div className="flex gap-3">
                                    <Button data-testid="btn-save-final" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                        <Save className="h-4 w-4 mr-2" /> {saving ? 'Salvataggio...' : 'Salva POS'}
                                    </Button>
                                    {(saved || isEditing) && (
                                        <>
                                            <Button data-testid="btn-ai-final" variant="outline" onClick={handleGenerateAI} disabled={generating} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                                {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                                                Genera Rischi (AI)
                                            </Button>
                                            <Button data-testid="btn-pdf-final" variant="outline" onClick={handleDownloadPdf} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                                <FileDown className="h-4 w-4 mr-2" /> Genera POS (PDF)
                                            </Button>
                                        </>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </DashboardLayout>
    );
}
