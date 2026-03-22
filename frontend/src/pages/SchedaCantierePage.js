/**
 * SchedaCantierePage — Safety Branch MVP
 * Multi-step form for cantiere_sicurezza (Scheda Cantiere POS)
 * Steps: 1. Dati Cantiere  2. Fasi Lavoro  3. Macchine & DPI  4. Riepilogo & Gate
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Save, ArrowLeft, ArrowRight, HardHat, Loader2, CheckCircle2, 
    Shield, AlertTriangle, Plus, Trash2, Users, Wrench, ClipboardCheck,
    ChevronRight, MapPin, Building2, Phone,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STEPS = [
    { num: 1, label: 'Cantiere', icon: MapPin },
    { num: 2, label: 'Fasi Lavoro', icon: ClipboardCheck },
    { num: 3, label: 'Macchine & DPI', icon: Wrench },
    { num: 4, label: 'Riepilogo', icon: Shield },
];

export default function SchedaCantierePage() {
    const navigate = useNavigate();
    const { cantiereId } = useParams();
    const isEditing = !!cantiereId;

    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [cantiereIdState, setCantiereIdState] = useState(cantiereId || null);
    const [gate, setGate] = useState(null);

    // Libreria rischi (from backend)
    const [fasiDisponibili, setFasiDisponibili] = useState([]);
    const [dpiDisponibili, setDpiDisponibili] = useState([]);

    // Form data matching cantieri_sicurezza model
    const [formData, setFormData] = useState({
        status: 'bozza',
        revisioni: [{ rev: '00', motivazione: 'Emissione', data: '' }],
        dati_cantiere: {
            attivita_cantiere: '',
            data_inizio_lavori: '',
            data_fine_prevista: '',
            indirizzo_cantiere: '',
            citta_cantiere: '',
            provincia_cantiere: '',
        },
        soggetti_riferimento: {
            committente: '',
            responsabile_lavori: '',
            direttore_lavori: '',
            progettista: '',
            csp: '',
            cse: '',
        },
        lavoratori_coinvolti: [],
        turni_lavoro: { mattina: '08:00-13:00', pomeriggio: '14:00-17:00', note: '' },
        subappalti: [],
        dpi_presenti: [],
        macchine_attrezzature: [],
        sostanze_chimiche: [],
        stoccaggio_materiali: '',
        servizi_igienici: '',
        fasi_lavoro_selezionate: [],
        numeri_utili: [],
        includi_covid19: false,
        data_dichiarazione: '',
        note_aggiuntive: '',
    });

    // Load reference data
    useEffect(() => {
        const fetchRef = async () => {
            try {
                const [fasi, dpi] = await Promise.all([
                    apiRequest('/libreria-rischi?tipo=fase_lavoro'),
                    apiRequest('/libreria-rischi?tipo=dpi'),
                ]);
                setFasiDisponibili(fasi || []);
                setDpiDisponibili(dpi || []);
            } catch { /* ignore */ }
        };
        fetchRef();
    }, []);

    // Load existing cantiere
    useEffect(() => {
        if (!isEditing) return;
        const fetchCantiere = async () => {
            try {
                const data = await apiRequest(`/cantieri-sicurezza/${cantiereId}`);
                setFormData({
                    status: data.status || 'bozza',
                    revisioni: data.revisioni || [{ rev: '00', motivazione: 'Emissione', data: '' }],
                    dati_cantiere: data.dati_cantiere || {},
                    soggetti_riferimento: data.soggetti_riferimento || {},
                    lavoratori_coinvolti: data.lavoratori_coinvolti || [],
                    turni_lavoro: data.turni_lavoro || { mattina: '08:00-13:00', pomeriggio: '14:00-17:00', note: '' },
                    subappalti: data.subappalti || [],
                    dpi_presenti: data.dpi_presenti || [],
                    macchine_attrezzature: data.macchine_attrezzature || [],
                    sostanze_chimiche: data.sostanze_chimiche || [],
                    stoccaggio_materiali: data.stoccaggio_materiali || '',
                    servizi_igienici: data.servizi_igienici || '',
                    fasi_lavoro_selezionate: data.fasi_lavoro_selezionate || [],
                    numeri_utili: data.numeri_utili || [],
                    includi_covid19: data.includi_covid19 || false,
                    data_dichiarazione: data.data_dichiarazione || '',
                    note_aggiuntive: data.note_aggiuntive || '',
                });
                setGate(data.gate_pos_status || null);
            } catch {
                toast.error('Errore nel caricamento');
                navigate('/sicurezza');
            } finally {
                setLoading(false);
            }
        };
        fetchCantiere();
    }, [isEditing, cantiereId, navigate]);

    const updateDatiCantiere = (field, value) => {
        setFormData(p => ({ ...p, dati_cantiere: { ...p.dati_cantiere, [field]: value } }));
    };

    const updateSoggetti = (field, value) => {
        setFormData(p => ({ ...p, soggetti_riferimento: { ...p.soggetti_riferimento, [field]: value } }));
    };

    const handleSave = useCallback(async () => {
        setSaving(true);
        try {
            if (isEditing || cantiereIdState) {
                const id = cantiereIdState || cantiereId;
                const res = await apiRequest(`/cantieri-sicurezza/${id}`, { method: 'PUT', body: formData });
                setGate(res.gate_pos_status || null);
                toast.success('Scheda cantiere aggiornata');
            } else {
                const res = await apiRequest('/cantieri-sicurezza', { method: 'POST', body: { pre_fill: formData } });
                setCantiereIdState(res.cantiere_id);
                setGate(res.gate_pos_status || null);
                toast.success('Scheda cantiere creata');
                // Update URL without remount
                window.history.replaceState(null, '', `/scheda-cantiere/${res.cantiere_id}`);
            }
        } catch (err) {
            toast.error(err.message || 'Errore nel salvataggio');
        } finally {
            setSaving(false);
        }
    }, [formData, isEditing, cantiereId, cantiereIdState]);

    // Add/remove workers
    const addLavoratore = () => {
        setFormData(p => ({
            ...p,
            lavoratori_coinvolti: [...p.lavoratori_coinvolti, { nominativo: '', mansione: '', addetto_primo_soccorso: false, addetto_antincendio: false }],
        }));
    };
    const updateLavoratore = (idx, field, value) => {
        setFormData(p => {
            const arr = [...p.lavoratori_coinvolti];
            arr[idx] = { ...arr[idx], [field]: value };
            return { ...p, lavoratori_coinvolti: arr };
        });
    };
    const removeLavoratore = (idx) => {
        setFormData(p => ({ ...p, lavoratori_coinvolti: p.lavoratori_coinvolti.filter((_, i) => i !== idx) }));
    };

    // Add/remove subappalti
    const addSubappalto = () => {
        setFormData(p => ({ ...p, subappalti: [...p.subappalti, { lavorazione: '', impresa: '', durata_prevista: '' }] }));
    };
    const updateSubappalto = (idx, field, value) => {
        setFormData(p => {
            const arr = [...p.subappalti];
            arr[idx] = { ...arr[idx], [field]: value };
            return { ...p, subappalti: arr };
        });
    };
    const removeSubappalto = (idx) => {
        setFormData(p => ({ ...p, subappalti: p.subappalti.filter((_, i) => i !== idx) }));
    };

    // Toggle fase lavoro
    const toggleFase = (fase) => {
        setFormData(p => {
            const existing = p.fasi_lavoro_selezionate.find(f => f.fase_id === fase.codice);
            if (existing) {
                return { ...p, fasi_lavoro_selezionate: p.fasi_lavoro_selezionate.filter(f => f.fase_id !== fase.codice) };
            }
            return {
                ...p,
                fasi_lavoro_selezionate: [...p.fasi_lavoro_selezionate, {
                    fase_id: fase.codice,
                    nome_fase: fase.nome,
                    rischi_valutati: fase.rischi_associati || [],
                    dpi_richiesti: fase.dpi_richiesti || [],
                    misure_aggiuntive: '',
                }],
            };
        });
    };

    // Add/remove macchine
    const addMacchina = () => {
        setFormData(p => ({ ...p, macchine_attrezzature: [...p.macchine_attrezzature, { nome: '', marcata_ce: true, verifiche_periodiche: true }] }));
    };
    const updateMacchina = (idx, field, value) => {
        setFormData(p => {
            const arr = [...p.macchine_attrezzature];
            arr[idx] = { ...arr[idx], [field]: value };
            return { ...p, macchine_attrezzature: arr };
        });
    };
    const removeMacchina = (idx) => {
        setFormData(p => ({ ...p, macchine_attrezzature: p.macchine_attrezzature.filter((_, i) => i !== idx) }));
    };

    // Toggle DPI
    const toggleDpi = (idx) => {
        setFormData(p => {
            const arr = [...p.dpi_presenti];
            arr[idx] = { ...arr[idx], presente: !arr[idx].presente };
            return { ...p, dpi_presenti: arr };
        });
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="scheda-cantiere-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="icon" onClick={() => navigate('/sicurezza')} data-testid="btn-back-sicurezza">
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div>
                            <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Scheda Cantiere Sicurezza</h1>
                            <p className="text-sm text-slate-500">Compilazione POS — D.Lgs. 81/2008</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {gate && (
                            <Badge className={gate.pronto_per_generazione ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}>
                                {gate.completezza_percentuale}% completo
                            </Badge>
                        )}
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-save-cantiere">
                            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Salva
                        </Button>
                    </div>
                </div>

                {/* Step navigation */}
                <div className="flex items-center gap-1 bg-slate-50 rounded-lg p-1">
                    {STEPS.map((s) => {
                        const Icon = s.icon;
                        return (
                            <button
                                key={s.num}
                                onClick={() => handleSave().then(() => setStep(s.num))}
                                data-testid={`step-btn-${s.num}`}
                                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-md text-sm font-medium transition-all ${
                                    step === s.num
                                        ? 'bg-white text-[#0055FF] shadow-sm'
                                        : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                <Icon className="h-4 w-4" />
                                <span className="hidden sm:inline">{s.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* ── Step 1: Dati Cantiere ── */}
                {step === 1 && (
                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2"><MapPin className="h-5 w-5 text-[#0055FF]" /> Dati Cantiere</CardTitle>
                            </CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2">
                                    <Label>Attivita cantiere</Label>
                                    <Textarea data-testid="input-attivita" value={formData.dati_cantiere.attivita_cantiere} onChange={e => updateDatiCantiere('attivita_cantiere', e.target.value)} placeholder="Descrizione attivita..." rows={2} />
                                </div>
                                <div>
                                    <Label>Indirizzo cantiere *</Label>
                                    <Input data-testid="input-indirizzo" value={formData.dati_cantiere.indirizzo_cantiere} onChange={e => updateDatiCantiere('indirizzo_cantiere', e.target.value)} placeholder="Via/Piazza..." />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label>Citta *</Label>
                                        <Input data-testid="input-citta" value={formData.dati_cantiere.citta_cantiere} onChange={e => updateDatiCantiere('citta_cantiere', e.target.value)} placeholder="Citta" />
                                    </div>
                                    <div>
                                        <Label>Provincia</Label>
                                        <Input data-testid="input-provincia" value={formData.dati_cantiere.provincia_cantiere} onChange={e => updateDatiCantiere('provincia_cantiere', e.target.value)} placeholder="PR" />
                                    </div>
                                </div>
                                <div>
                                    <Label>Data inizio lavori *</Label>
                                    <Input data-testid="input-data-inizio" type="date" value={formData.dati_cantiere.data_inizio_lavori} onChange={e => updateDatiCantiere('data_inizio_lavori', e.target.value)} />
                                </div>
                                <div>
                                    <Label>Data fine prevista</Label>
                                    <Input data-testid="input-data-fine" type="date" value={formData.dati_cantiere.data_fine_prevista} onChange={e => updateDatiCantiere('data_fine_prevista', e.target.value)} />
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2"><Building2 className="h-5 w-5 text-[#0055FF]" /> Soggetti di Riferimento</CardTitle>
                            </CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <Label>Committente *</Label>
                                    <Input data-testid="input-committente" value={formData.soggetti_riferimento.committente} onChange={e => updateSoggetti('committente', e.target.value)} />
                                </div>
                                <div>
                                    <Label>Responsabile Lavori</Label>
                                    <Input value={formData.soggetti_riferimento.responsabile_lavori} onChange={e => updateSoggetti('responsabile_lavori', e.target.value)} />
                                </div>
                                <div>
                                    <Label>Direttore Lavori</Label>
                                    <Input value={formData.soggetti_riferimento.direttore_lavori} onChange={e => updateSoggetti('direttore_lavori', e.target.value)} />
                                </div>
                                <div>
                                    <Label>Progettista</Label>
                                    <Input value={formData.soggetti_riferimento.progettista} onChange={e => updateSoggetti('progettista', e.target.value)} />
                                </div>
                                <div>
                                    <Label>CSP (Coordinatore Sicurezza Progettazione)</Label>
                                    <Input value={formData.soggetti_riferimento.csp} onChange={e => updateSoggetti('csp', e.target.value)} />
                                </div>
                                <div>
                                    <Label>CSE (Coordinatore Sicurezza Esecuzione)</Label>
                                    <Input value={formData.soggetti_riferimento.cse} onChange={e => updateSoggetti('cse', e.target.value)} />
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2"><Users className="h-5 w-5 text-[#0055FF]" /> Lavoratori Coinvolti</CardTitle>
                                    <Button variant="outline" size="sm" onClick={addLavoratore} data-testid="btn-add-lavoratore">
                                        <Plus className="h-4 w-4 mr-1" /> Aggiungi
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {formData.lavoratori_coinvolti.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessun lavoratore aggiunto. Clicca "Aggiungi" per iniziare.</p>
                                ) : (
                                    <div className="space-y-3">
                                        {formData.lavoratori_coinvolti.map((lav, idx) => (
                                            <div key={idx} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg" data-testid={`lavoratore-row-${idx}`}>
                                                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                    <Input placeholder="Nominativo" value={lav.nominativo} onChange={e => updateLavoratore(idx, 'nominativo', e.target.value)} />
                                                    <Input placeholder="Mansione" value={lav.mansione} onChange={e => updateLavoratore(idx, 'mansione', e.target.value)} />
                                                </div>
                                                <div className="flex items-center gap-4 pt-2">
                                                    <label className="flex items-center gap-1.5 text-xs">
                                                        <Checkbox checked={lav.addetto_primo_soccorso} onCheckedChange={v => updateLavoratore(idx, 'addetto_primo_soccorso', v)} />
                                                        PS
                                                    </label>
                                                    <label className="flex items-center gap-1.5 text-xs">
                                                        <Checkbox checked={lav.addetto_antincendio} onCheckedChange={v => updateLavoratore(idx, 'addetto_antincendio', v)} />
                                                        AI
                                                    </label>
                                                    <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeLavoratore(idx)}>
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg">Subappalti</CardTitle>
                                    <Button variant="outline" size="sm" onClick={addSubappalto} data-testid="btn-add-subappalto">
                                        <Plus className="h-4 w-4 mr-1" /> Aggiungi
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {formData.subappalti.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessun subappalto previsto.</p>
                                ) : (
                                    <div className="space-y-3">
                                        {formData.subappalti.map((sub, idx) => (
                                            <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                                                <Input className="flex-1" placeholder="Lavorazione" value={sub.lavorazione} onChange={e => updateSubappalto(idx, 'lavorazione', e.target.value)} />
                                                <Input className="flex-1" placeholder="Impresa" value={sub.impresa} onChange={e => updateSubappalto(idx, 'impresa', e.target.value)} />
                                                <Input className="w-28" placeholder="Durata" value={sub.durata_prevista} onChange={e => updateSubappalto(idx, 'durata_prevista', e.target.value)} />
                                                <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeSubappalto(idx)}>
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ── Step 2: Fasi di Lavoro ── */}
                {step === 2 && (
                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2"><ClipboardCheck className="h-5 w-5 text-[#0055FF]" /> Fasi di Lavoro</CardTitle>
                                <CardDescription>Seleziona le fasi di lavoro pertinenti dalla Libreria Rischi. Per ogni fase, il sistema associa automaticamente rischi, misure e DPI.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {fasiDisponibili.map((fase) => {
                                    const isSelected = formData.fasi_lavoro_selezionate.some(f => f.fase_id === fase.codice);
                                    return (
                                        <div
                                            key={fase.codice}
                                            data-testid={`fase-card-${fase.codice}`}
                                            onClick={() => toggleFase(fase)}
                                            className={`cursor-pointer border rounded-lg p-4 transition-all ${
                                                isSelected
                                                    ? 'border-[#0055FF] bg-blue-50/50 shadow-sm'
                                                    : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                        >
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <Checkbox checked={isSelected} />
                                                        <span className="font-medium text-[#1E293B]">{fase.nome}</span>
                                                        <Badge variant="outline" className="text-xs">{fase.codice}</Badge>
                                                        <Badge className="text-xs bg-slate-100 text-slate-600">{fase.categoria}</Badge>
                                                    </div>
                                                    {isSelected && (
                                                        <div className="mt-3 ml-7 space-y-2">
                                                            <div className="text-xs text-slate-500">
                                                                <span className="font-semibold">Rischi:</span>{' '}
                                                                {(fase.rischi_associati || []).map(r => r.descrizione).join(' | ')}
                                                            </div>
                                                            <div className="text-xs text-slate-500">
                                                                <span className="font-semibold">DPI:</span>{' '}
                                                                {(fase.dpi_richiesti || []).join(', ')}
                                                            </div>
                                                            <div className="text-xs text-slate-500">
                                                                <span className="font-semibold">Misure:</span>{' '}
                                                                {(fase.misure_prevenzione || []).join(' | ')}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="flex gap-1">
                                                    {(fase.applicabile_a || []).map(n => (
                                                        <Badge key={n} className="text-[10px] bg-blue-100 text-blue-700">{n}</Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                                {fasiDisponibili.length === 0 && (
                                    <p className="text-sm text-slate-400 text-center py-8">Caricamento libreria rischi...</p>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ── Step 3: Macchine & DPI ── */}
                {step === 3 && (
                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2"><Wrench className="h-5 w-5 text-[#0055FF]" /> Macchine / Attrezzature</CardTitle>
                                    <Button variant="outline" size="sm" onClick={addMacchina} data-testid="btn-add-macchina">
                                        <Plus className="h-4 w-4 mr-1" /> Aggiungi
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {formData.macchine_attrezzature.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessuna macchina aggiunta.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {formData.macchine_attrezzature.map((m, idx) => (
                                            <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg" data-testid={`macchina-row-${idx}`}>
                                                <Input className="flex-1" placeholder="Nome macchina/attrezzatura" value={m.nome} onChange={e => updateMacchina(idx, 'nome', e.target.value)} />
                                                <label className="flex items-center gap-1.5 text-xs whitespace-nowrap">
                                                    <Checkbox checked={m.marcata_ce} onCheckedChange={v => updateMacchina(idx, 'marcata_ce', v)} />
                                                    CE
                                                </label>
                                                <label className="flex items-center gap-1.5 text-xs whitespace-nowrap">
                                                    <Checkbox checked={m.verifiche_periodiche} onCheckedChange={v => updateMacchina(idx, 'verifiche_periodiche', v)} />
                                                    Verifiche
                                                </label>
                                                <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeMacchina(idx)}>
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2"><Shield className="h-5 w-5 text-[#0055FF]" /> DPI Presenti in Cantiere</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {formData.dpi_presenti.map((dpi, idx) => (
                                        <label
                                            key={idx}
                                            className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all ${
                                                dpi.presente ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200'
                                            }`}
                                        >
                                            <Checkbox checked={dpi.presente} onCheckedChange={() => toggleDpi(idx)} />
                                            <span className="text-sm">{dpi.tipo_dpi}</span>
                                        </label>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Altre Informazioni</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                    <Label>Stoccaggio materiali e/o rifiuti</Label>
                                    <Textarea data-testid="input-stoccaggio" value={formData.stoccaggio_materiali} onChange={e => setFormData(p => ({ ...p, stoccaggio_materiali: e.target.value }))} rows={2} placeholder="Descrivi le modalita di stoccaggio..." />
                                </div>
                                <div>
                                    <Label>Servizi igienico-assistenziali</Label>
                                    <Textarea data-testid="input-servizi" value={formData.servizi_igienici} onChange={e => setFormData(p => ({ ...p, servizi_igienici: e.target.value }))} rows={2} placeholder="Descrivi i servizi disponibili..." />
                                </div>
                                <div>
                                    <Label>Note aggiuntive</Label>
                                    <Textarea value={formData.note_aggiuntive} onChange={e => setFormData(p => ({ ...p, note_aggiuntive: e.target.value }))} rows={2} placeholder="Note..." />
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ── Step 4: Riepilogo & Gate ── */}
                {step === 4 && (
                    <div className="space-y-6">
                        {/* Gate POS Status */}
                        <Card className={gate?.pronto_per_generazione ? 'border-emerald-300' : 'border-amber-300'}>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    {gate?.pronto_per_generazione ? (
                                        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                    ) : (
                                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                                    )}
                                    Gate POS — Stato Completezza
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="flex-1 bg-gray-200 rounded-full h-3">
                                        <div
                                            className={`h-3 rounded-full transition-all ${gate?.pronto_per_generazione ? 'bg-emerald-500' : 'bg-amber-500'}`}
                                            style={{ width: `${gate?.completezza_percentuale || 0}%` }}
                                        />
                                    </div>
                                    <span className="text-sm font-bold">{gate?.completezza_percentuale || 0}%</span>
                                </div>
                                {gate?.campi_mancanti?.length > 0 && (
                                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                                        <p className="text-sm font-medium text-amber-800 mb-1">Campi mancanti:</p>
                                        <ul className="text-sm text-amber-700 list-disc list-inside">
                                            {gate.campi_mancanti.map((c, i) => <li key={i}>{c}</li>)}
                                        </ul>
                                    </div>
                                )}
                                {gate?.pronto_per_generazione && (
                                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                                        <p className="text-sm text-emerald-800">Tutti i campi obbligatori sono compilati. La scheda e pronta per la generazione del POS DOCX.</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Summary cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <Card>
                                <CardHeader><CardTitle className="text-base">Dati Cantiere</CardTitle></CardHeader>
                                <CardContent className="text-sm space-y-1">
                                    <p><span className="text-slate-500">Indirizzo:</span> {formData.dati_cantiere.indirizzo_cantiere || '-'}</p>
                                    <p><span className="text-slate-500">Citta:</span> {formData.dati_cantiere.citta_cantiere || '-'}</p>
                                    <p><span className="text-slate-500">Committente:</span> {formData.soggetti_riferimento.committente || '-'}</p>
                                    <p><span className="text-slate-500">Inizio:</span> {formData.dati_cantiere.data_inizio_lavori || '-'}</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader><CardTitle className="text-base">Riepilogo</CardTitle></CardHeader>
                                <CardContent className="text-sm space-y-1">
                                    <p><span className="text-slate-500">Lavoratori:</span> {formData.lavoratori_coinvolti.length}</p>
                                    <p><span className="text-slate-500">Fasi lavoro:</span> {formData.fasi_lavoro_selezionate.length}</p>
                                    <p><span className="text-slate-500">Macchine:</span> {formData.macchine_attrezzature.length}</p>
                                    <p><span className="text-slate-500">DPI attivi:</span> {formData.dpi_presenti.filter(d => d.presente).length}/{formData.dpi_presenti.length}</p>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Fasi selezionate riepilogo */}
                        {formData.fasi_lavoro_selezionate.length > 0 && (
                            <Card>
                                <CardHeader><CardTitle className="text-base">Fasi di Lavoro Selezionate</CardTitle></CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        {formData.fasi_lavoro_selezionate.map((f, i) => (
                                            <div key={i} className="flex items-center gap-2 p-2 bg-blue-50 rounded-md">
                                                <ChevronRight className="h-4 w-4 text-[#0055FF]" />
                                                <span className="text-sm font-medium">{f.nome_fase}</span>
                                                <Badge variant="outline" className="text-xs ml-auto">{(f.rischi_valutati || []).length} rischi</Badge>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* Data dichiarazione */}
                        <Card>
                            <CardHeader><CardTitle className="text-base">Dichiarazione</CardTitle></CardHeader>
                            <CardContent>
                                <div className="max-w-xs">
                                    <Label>Data dichiarazione</Label>
                                    <Input type="date" value={formData.data_dichiarazione} onChange={e => setFormData(p => ({ ...p, data_dichiarazione: e.target.value }))} data-testid="input-data-dichiarazione" />
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* Navigation footer */}
                <div className="flex items-center justify-between pt-4 border-t">
                    <Button variant="outline" onClick={() => step > 1 && setStep(s => s - 1)} disabled={step === 1}>
                        <ArrowLeft className="h-4 w-4 mr-2" /> Precedente
                    </Button>
                    <span className="text-sm text-slate-400">Passo {step} di {STEPS.length}</span>
                    {step < STEPS.length ? (
                        <Button onClick={() => { handleSave(); setStep(s => s + 1); }} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            Successivo <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                    ) : (
                        <Button onClick={handleSave} disabled={saving} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-save-final">
                            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Salva Scheda Finale
                        </Button>
                    )}
                </div>
            </div>
        </DashboardLayout>
    );
}
