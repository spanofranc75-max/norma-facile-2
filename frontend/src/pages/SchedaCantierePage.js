/**
 * SchedaCantierePage — Safety Branch v2
 * Multi-step form with 3-level library: Fasi → Rischi → DPI/Misure
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
import { toast } from 'sonner';
import {
    Save, ArrowLeft, ArrowRight, Loader2, CheckCircle2,
    Shield, AlertTriangle, Plus, Trash2, Users, Wrench, ClipboardCheck,
    ChevronDown, ChevronRight, MapPin, Building2, CircleAlert,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const STEPS = [
    { num: 1, label: 'Cantiere', icon: MapPin },
    { num: 2, label: 'Fasi & Rischi', icon: ClipboardCheck },
    { num: 3, label: 'Macchine & DPI', icon: Wrench },
    { num: 4, label: 'Riepilogo', icon: Shield },
];

const CONFIDENCE_BADGE = {
    dedotto: 'bg-blue-100 text-blue-800',
    confermato: 'bg-emerald-100 text-emerald-800',
    incerto: 'bg-amber-100 text-amber-800',
    mancante: 'bg-red-100 text-red-800',
};

export default function SchedaCantierePage() {
    const navigate = useNavigate();
    const { cantiereId } = useParams();
    const isEditing = !!cantiereId;

    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [cantiereIdState, setCantiereIdState] = useState(cantiereId || null);
    const [gate, setGate] = useState(null);

    // Libreria 3 livelli
    const [fasiLib, setFasiLib] = useState([]);
    const [rischiLib, setRischiLib] = useState([]);
    const [dpiMisureLib, setDpiMisureLib] = useState([]);
    const [expandedFasi, setExpandedFasi] = useState({});

    const [formData, setFormData] = useState({
        status: 'bozza',
        revisioni: [{ rev: '00', motivazione: 'Emissione', data: '' }],
        dati_cantiere: {
            attivita_cantiere: '', data_inizio_lavori: '', data_fine_prevista: '',
            indirizzo_cantiere: '', citta_cantiere: '', provincia_cantiere: '',
        },
        soggetti: [],
        lavoratori_coinvolti: [],
        turni_lavoro: { mattina: '08:00-13:00', pomeriggio: '14:00-17:00', note: '' },
        subappalti: [],
        dpi_presenti: [],
        macchine_attrezzature: [],
        sostanze_chimiche: [],
        stoccaggio_materiali: '',
        servizi_igienici: '',
        fasi_lavoro_selezionate: [],
        dpi_calcolati: [],
        misure_calcolate: [],
        apprestamenti_calcolati: [],
        domande_residue: [],
        numeri_utili: [],
        includi_covid19: false,
        data_dichiarazione: '',
        note_aggiuntive: '',
    });

    // Load library
    useEffect(() => {
        const fetchLib = async () => {
            try {
                const [fasi, rischi, dpiM] = await Promise.all([
                    apiRequest('/libreria/fasi'),
                    apiRequest('/libreria/rischi'),
                    apiRequest('/libreria/dpi-misure'),
                ]);
                setFasiLib(fasi || []);
                setRischiLib(rischi || []);
                setDpiMisureLib(dpiM || []);
            } catch { /* */ }
        };
        fetchLib();
    }, []);

    // Build lookup maps
    const rischiMap = {};
    rischiLib.forEach(r => { rischiMap[r.codice] = r; });
    const dpiMap = {};
    dpiMisureLib.forEach(d => { dpiMap[d.codice] = d; });

    // Load existing cantiere
    useEffect(() => {
        if (!isEditing) return;
        const fetchCantiere = async () => {
            try {
                const data = await apiRequest(`/cantieri-sicurezza/${cantiereId}`);
                setFormData(prev => ({
                    ...prev,
                    ...Object.fromEntries(
                        Object.entries(data).filter(([k]) =>
                            k !== 'cantiere_id' && k !== 'user_id' && k !== '_id' &&
                            k !== 'created_at' && k !== 'updated_at' && k !== 'gate_pos_status' && k !== 'ai_precompilazione'
                        )
                    ),
                }));
                setGate(data.gate_pos_status || null);
            } catch {
                toast.error('Errore nel caricamento');
                navigate('/sicurezza');
            } finally { setLoading(false); }
        };
        fetchCantiere();
    }, [isEditing, cantiereId, navigate]);

    const updateDatiCantiere = (f, v) => setFormData(p => ({ ...p, dati_cantiere: { ...p.dati_cantiere, [f]: v } }));
    const updateSoggetto = (ruolo, field, value) => {
        setFormData(p => ({
            ...p,
            soggetti: p.soggetti.map(s =>
                s.ruolo === ruolo ? { ...s, [field]: value, status: value ? 'confermato' : 'mancante' } : s
            ),
        }));
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
                window.history.replaceState(null, '', `/scheda-cantiere/${res.cantiere_id}`);
            }
        } catch (err) {
            toast.error(err.message || 'Errore nel salvataggio');
        } finally { setSaving(false); }
    }, [formData, isEditing, cantiereId, cantiereIdState]);

    // ── Workers ──
    const addLavoratore = () => setFormData(p => ({ ...p, lavoratori_coinvolti: [...p.lavoratori_coinvolti, { nominativo: '', mansione: '', addetto_primo_soccorso: false, addetto_antincendio: false }] }));
    const updateLavoratore = (i, f, v) => setFormData(p => { const a = [...p.lavoratori_coinvolti]; a[i] = { ...a[i], [f]: v }; return { ...p, lavoratori_coinvolti: a }; });
    const removeLavoratore = (i) => setFormData(p => ({ ...p, lavoratori_coinvolti: p.lavoratori_coinvolti.filter((_, j) => j !== i) }));

    // ── Subappalti ──
    const addSubappalto = () => setFormData(p => ({ ...p, subappalti: [...p.subappalti, { lavorazione: '', impresa: '', durata_prevista: '' }] }));
    const updateSubappalto = (i, f, v) => setFormData(p => { const a = [...p.subappalti]; a[i] = { ...a[i], [f]: v }; return { ...p, subappalti: a }; });
    const removeSubappalto = (i) => setFormData(p => ({ ...p, subappalti: p.subappalti.filter((_, j) => j !== i) }));

    // ── Macchine ──
    const addMacchina = () => setFormData(p => ({ ...p, macchine_attrezzature: [...p.macchine_attrezzature, { nome: '', marcata_ce: true, verifiche_periodiche: true }] }));
    const updateMacchina = (i, f, v) => setFormData(p => { const a = [...p.macchine_attrezzature]; a[i] = { ...a[i], [f]: v }; return { ...p, macchine_attrezzature: a }; });
    const removeMacchina = (i) => setFormData(p => ({ ...p, macchine_attrezzature: p.macchine_attrezzature.filter((_, j) => j !== i) }));

    // ── Toggle DPI ──
    const toggleDpi = (i) => setFormData(p => { const a = [...p.dpi_presenti]; a[i] = { ...a[i], presente: !a[i].presente }; return { ...p, dpi_presenti: a }; });

    // ── Toggle Fase (v2: with rischi_ids resolution) ──
    const toggleFase = (fase) => {
        setFormData(p => {
            const existing = p.fasi_lavoro_selezionate.find(f => f.fase_codice === fase.codice);
            if (existing) {
                // Deselect
                const newFasi = p.fasi_lavoro_selezionate.filter(f => f.fase_codice !== fase.codice);
                return { ...p, fasi_lavoro_selezionate: newFasi, ...recalcDpiMisure(newFasi) };
            }
            // Select — resolve rischi from library
            const rischiAttivati = (fase.rischi_ids || []).map(rc => {
                const rischio = rischiMap[rc];
                return {
                    rischio_codice: rc,
                    confidence: 'dedotto',
                    origin: 'rules',
                    reasoning: `Attivato da fase ${fase.codice}`,
                    valutazione_override: null,
                    overridden_by_user: false,
                };
            }).filter(Boolean);

            const newEntry = {
                fase_codice: fase.codice,
                confidence: 'confermato',
                origin: 'user',
                reasoning: 'Selezionata manualmente dall\'utente',
                source_refs: [],
                overridden_by_user: false,
                rischi_attivati: rischiAttivati,
                note_utente: '',
            };
            const newFasi = [...p.fasi_lavoro_selezionate, newEntry];
            return { ...p, fasi_lavoro_selezionate: newFasi, ...recalcDpiMisure(newFasi) };
        });
    };

    // Recalculate DPI/Misure/Apprestamenti from selected fasi + rischi
    const recalcDpiMisure = (fasiSel) => {
        const dpiSet = new Map();
        const misSet = new Map();
        const appSet = new Map();
        const domande = [];

        fasiSel.forEach(f => {
            (f.rischi_attivati || []).forEach(ra => {
                const rischio = rischiMap[ra.rischio_codice];
                if (!rischio) return;
                (rischio.dpi_ids || []).forEach(c => { if (!dpiSet.has(c)) dpiSet.set(c, { codice: c, origin: 'rules', da_rischi: [] }); dpiSet.get(c).da_rischi.push(ra.rischio_codice); });
                (rischio.misure_ids || []).forEach(c => { if (!misSet.has(c)) misSet.set(c, { codice: c, origin: 'rules', da_rischi: [] }); misSet.get(c).da_rischi.push(ra.rischio_codice); });
                (rischio.apprestamenti_ids || []).forEach(c => { if (!appSet.has(c)) appSet.set(c, { codice: c, origin: 'rules', da_rischi: [], confidence: 'dedotto' }); appSet.get(c).da_rischi.push(ra.rischio_codice); });
                (rischio.domande_verifica || []).forEach(d => {
                    if (!domande.find(x => x.testo === d.testo)) {
                        domande.push({ testo: d.testo, origine_rischio: ra.rischio_codice, impatto: d.impatto || 'medio', gate_critical: d.gate_critical || false, risposta: null, stato: 'aperta' });
                    }
                });
            });
        });

        return {
            dpi_calcolati: Array.from(dpiSet.values()),
            misure_calcolate: Array.from(misSet.values()),
            apprestamenti_calcolati: Array.from(appSet.values()),
            domande_residue: domande,
        };
    };

    if (loading) {
        return <DashboardLayout><div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" /></div></DashboardLayout>;
    }

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="scheda-cantiere-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="icon" onClick={() => navigate('/sicurezza')} data-testid="btn-back-sicurezza"><ArrowLeft className="h-5 w-5" /></Button>
                        <div>
                            <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Scheda Cantiere Sicurezza</h1>
                            <p className="text-sm text-slate-500">POS — D.Lgs. 81/2008 | Libreria 3 livelli</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {gate && (
                            <Badge className={gate.pronto_per_generazione ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}>
                                {gate.completezza_percentuale}%
                            </Badge>
                        )}
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-save-cantiere">
                            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />} Salva
                        </Button>
                    </div>
                </div>

                {/* Step nav */}
                <div className="flex items-center gap-1 bg-slate-50 rounded-lg p-1">
                    {STEPS.map(s => {
                        const Icon = s.icon;
                        return (
                            <button key={s.num} onClick={() => setStep(s.num)} data-testid={`step-btn-${s.num}`}
                                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-md text-sm font-medium transition-all ${step === s.num ? 'bg-white text-[#0055FF] shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
                                <Icon className="h-4 w-4" /><span className="hidden sm:inline">{s.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* ── Step 1: Dati Cantiere ── */}
                {step === 1 && (
                    <div className="space-y-6">
                        <Card>
                            <CardHeader><CardTitle className="text-lg flex items-center gap-2"><MapPin className="h-5 w-5 text-[#0055FF]" /> Dati Cantiere</CardTitle></CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2"><Label>Attivita cantiere</Label><Textarea data-testid="input-attivita" value={formData.dati_cantiere.attivita_cantiere} onChange={e => updateDatiCantiere('attivita_cantiere', e.target.value)} rows={2} /></div>
                                <div><Label>Indirizzo cantiere *</Label><Input data-testid="input-indirizzo" value={formData.dati_cantiere.indirizzo_cantiere} onChange={e => updateDatiCantiere('indirizzo_cantiere', e.target.value)} /></div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div><Label>Citta *</Label><Input data-testid="input-citta" value={formData.dati_cantiere.citta_cantiere} onChange={e => updateDatiCantiere('citta_cantiere', e.target.value)} /></div>
                                    <div><Label>Provincia</Label><Input data-testid="input-provincia" value={formData.dati_cantiere.provincia_cantiere} onChange={e => updateDatiCantiere('provincia_cantiere', e.target.value)} /></div>
                                </div>
                                <div><Label>Data inizio lavori *</Label><Input data-testid="input-data-inizio" type="date" value={formData.dati_cantiere.data_inizio_lavori} onChange={e => updateDatiCantiere('data_inizio_lavori', e.target.value)} /></div>
                                <div><Label>Data fine prevista</Label><Input data-testid="input-data-fine" type="date" value={formData.dati_cantiere.data_fine_prevista} onChange={e => updateDatiCantiere('data_fine_prevista', e.target.value)} /></div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Building2 className="h-5 w-5 text-[#0055FF]" /> Soggetti & Referenti</CardTitle></CardHeader>
                            <CardContent className="space-y-6">
                                {[
                                    { cat: 'azienda', label: 'Figure Aziendali', color: 'border-blue-200 bg-blue-50/30' },
                                    { cat: 'committente', label: 'Figure Committente / Cantiere', color: 'border-amber-200 bg-amber-50/30' },
                                    { cat: 'tecnico', label: 'Figure Tecniche', color: 'border-slate-200 bg-slate-50/30' },
                                ].map(({ cat, label, color }) => {
                                    const group = formData.soggetti.filter(s => s.categoria === cat);
                                    if (group.length === 0) return null;
                                    return (
                                        <div key={cat} className={`rounded-lg border p-4 ${color}`}>
                                            <h4 className="text-sm font-semibold text-slate-700 mb-3">{label}</h4>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {group.map(s => (
                                                    <div key={s.ruolo} className="bg-white rounded-md p-3 border border-gray-100" data-testid={`soggetto-${s.ruolo}`}>
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <Label className="text-xs font-semibold">{s.label} {s.obbligatorio && <span className="text-red-500">*</span>}</Label>
                                                            {s.status === 'precompilato' && <Badge className="text-[10px] bg-blue-100 text-blue-700">precompilato</Badge>}
                                                            {s.status === 'confermato' && <Badge className="text-[10px] bg-emerald-100 text-emerald-700">confermato</Badge>}
                                                            {s.status === 'mancante' && s.obbligatorio && <Badge className="text-[10px] bg-red-100 text-red-700">mancante</Badge>}
                                                        </div>
                                                        <Input placeholder="Nome / Ragione Sociale" value={s.nome || ''} onChange={e => updateSoggetto(s.ruolo, 'nome', e.target.value)} className="mb-1.5 text-sm" />
                                                        <div className="grid grid-cols-2 gap-1.5">
                                                            <Input placeholder="Telefono" value={s.telefono || ''} onChange={e => updateSoggetto(s.ruolo, 'telefono', e.target.value)} className="text-xs" />
                                                            <Input placeholder="Email" value={s.email || ''} onChange={e => updateSoggetto(s.ruolo, 'email', e.target.value)} className="text-xs" />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2"><Users className="h-5 w-5 text-[#0055FF]" /> Lavoratori</CardTitle>
                                    <Button variant="outline" size="sm" onClick={addLavoratore} data-testid="btn-add-lavoratore"><Plus className="h-4 w-4 mr-1" /> Aggiungi</Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {formData.lavoratori_coinvolti.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessun lavoratore aggiunto.</p>
                                ) : formData.lavoratori_coinvolti.map((lav, i) => (
                                    <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg mb-2" data-testid={`lavoratore-row-${i}`}>
                                        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                                            <Input placeholder="Nominativo" value={lav.nominativo} onChange={e => updateLavoratore(i, 'nominativo', e.target.value)} />
                                            <Input placeholder="Mansione" value={lav.mansione} onChange={e => updateLavoratore(i, 'mansione', e.target.value)} />
                                        </div>
                                        <div className="flex items-center gap-4 pt-2">
                                            <label className="flex items-center gap-1.5 text-xs"><Checkbox checked={lav.addetto_primo_soccorso} onCheckedChange={v => updateLavoratore(i, 'addetto_primo_soccorso', v)} />PS</label>
                                            <label className="flex items-center gap-1.5 text-xs"><Checkbox checked={lav.addetto_antincendio} onCheckedChange={v => updateLavoratore(i, 'addetto_antincendio', v)} />AI</label>
                                            <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeLavoratore(i)}><Trash2 className="h-4 w-4" /></Button>
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg">Subappalti</CardTitle>
                                    <Button variant="outline" size="sm" onClick={addSubappalto} data-testid="btn-add-subappalto"><Plus className="h-4 w-4 mr-1" /> Aggiungi</Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {formData.subappalti.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessun subappalto.</p>
                                ) : formData.subappalti.map((s, i) => (
                                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg mb-2">
                                        <Input className="flex-1" placeholder="Lavorazione" value={s.lavorazione} onChange={e => updateSubappalto(i, 'lavorazione', e.target.value)} />
                                        <Input className="flex-1" placeholder="Impresa" value={s.impresa} onChange={e => updateSubappalto(i, 'impresa', e.target.value)} />
                                        <Input className="w-28" placeholder="Durata" value={s.durata_prevista} onChange={e => updateSubappalto(i, 'durata_prevista', e.target.value)} />
                                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeSubappalto(i)}><Trash2 className="h-4 w-4" /></Button>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ── Step 2: Fasi & Rischi (3 livelli) ── */}
                {step === 2 && (
                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2"><ClipboardCheck className="h-5 w-5 text-[#0055FF]" /> Fasi di Lavoro & Rischi Associati</CardTitle>
                                <CardDescription>Seleziona le fasi pertinenti. Il sistema attiva automaticamente rischi, DPI e misure collegate (catena Fase → Rischi → DPI/Misure).</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {fasiLib.map(fase => {
                                    const isSelected = formData.fasi_lavoro_selezionate.some(f => f.fase_codice === fase.codice);
                                    const isExpanded = expandedFasi[fase.codice];
                                    const rischiFase = (fase.rischi_ids || []).map(rc => rischiMap[rc]).filter(Boolean);
                                    return (
                                        <div key={fase.codice} data-testid={`fase-card-${fase.codice}`}
                                            className={`border rounded-lg transition-all ${isSelected ? 'border-[#0055FF] bg-blue-50/30 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
                                            <div className="flex items-center gap-3 p-4 cursor-pointer" onClick={() => toggleFase(fase)}>
                                                <Checkbox checked={isSelected} />
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <span className="font-medium text-[#1E293B]">{fase.nome}</span>
                                                        <Badge variant="outline" className="text-xs">{fase.codice}</Badge>
                                                        <Badge className="text-xs bg-slate-100 text-slate-600">{fase.categoria}</Badge>
                                                        {(fase.applicabile_a || []).map(n => <Badge key={n} className="text-[10px] bg-blue-100 text-blue-700">{n}</Badge>)}
                                                    </div>
                                                    {fase.descrizione && <p className="text-xs text-slate-500 mt-1">{fase.descrizione}</p>}
                                                </div>
                                                <div className="flex items-center gap-1 text-xs text-slate-400">
                                                    <span>{rischiFase.length} rischi</span>
                                                    {isSelected && (
                                                        <button onClick={e => { e.stopPropagation(); setExpandedFasi(p => ({ ...p, [fase.codice]: !p[fase.codice] })); }}
                                                            className="ml-2 p-1 hover:bg-white rounded">
                                                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                            {/* Expanded: show rischi chain */}
                                            {isSelected && isExpanded && (
                                                <div className="px-4 pb-4 border-t border-blue-100">
                                                    <div className="mt-3 space-y-2">
                                                        {rischiFase.map(rischio => (
                                                            <div key={rischio.codice} className="ml-4 p-3 bg-white border border-gray-100 rounded-md">
                                                                <div className="flex items-center gap-2 flex-wrap">
                                                                    <CircleAlert className={`h-3.5 w-3.5 ${rischio.gate_critical ? 'text-red-500' : 'text-amber-500'}`} />
                                                                    <span className="text-sm font-medium">{rischio.nome}</span>
                                                                    <Badge className={`text-[10px] ${rischio.gate_critical ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                                                                        {rischio.valutazione_default?.classe || ''}
                                                                    </Badge>
                                                                    {rischio.gate_critical && <Badge className="text-[10px] bg-red-50 text-red-600">CRITICO</Badge>}
                                                                </div>
                                                                <p className="text-xs text-slate-500 mt-1">{rischio.descrizione_breve}</p>
                                                                <div className="mt-2 flex flex-wrap gap-1">
                                                                    {(rischio.dpi_ids || []).map(d => (
                                                                        <Badge key={d} className="text-[10px] bg-emerald-50 text-emerald-700">{dpiMap[d]?.nome || d}</Badge>
                                                                    ))}
                                                                    {(rischio.misure_ids || []).map(m => (
                                                                        <Badge key={m} className="text-[10px] bg-purple-50 text-purple-700">{dpiMap[m]?.nome || m}</Badge>
                                                                    ))}
                                                                    {(rischio.apprestamenti_ids || []).map(a => (
                                                                        <Badge key={a} className="text-[10px] bg-orange-50 text-orange-700">{dpiMap[a]?.nome || a}</Badge>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                                {fasiLib.length === 0 && <p className="text-sm text-slate-400 text-center py-8">Caricamento libreria...</p>}
                            </CardContent>
                        </Card>

                        {/* Domande residue generate */}
                        {formData.domande_residue.length > 0 && (
                            <Card className="border-amber-200">
                                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-600" /> Domande Residue ({formData.domande_residue.length})</CardTitle></CardHeader>
                                <CardContent className="space-y-2">
                                    {formData.domande_residue.map((d, i) => (
                                        <div key={i} className={`p-3 rounded-lg border ${d.gate_critical ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'}`}>
                                            <div className="flex items-start gap-2">
                                                <CircleAlert className={`h-4 w-4 mt-0.5 ${d.gate_critical ? 'text-red-500' : 'text-amber-500'}`} />
                                                <div className="flex-1">
                                                    <p className="text-sm font-medium">{d.testo}</p>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <Badge className="text-[10px]" variant="outline">Da: {d.origine_rischio}</Badge>
                                                        <Badge className={`text-[10px] ${d.gate_critical ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                                                            {d.gate_critical ? 'Blocca POS' : `Impatto: ${d.impatto}`}
                                                        </Badge>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </CardContent>
                            </Card>
                        )}
                    </div>
                )}

                {/* ── Step 3: Macchine & DPI ── */}
                {step === 3 && (
                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2"><Wrench className="h-5 w-5 text-[#0055FF]" /> Macchine / Attrezzature</CardTitle>
                                    <Button variant="outline" size="sm" onClick={addMacchina} data-testid="btn-add-macchina"><Plus className="h-4 w-4 mr-1" /> Aggiungi</Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {formData.macchine_attrezzature.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessuna macchina.</p>
                                ) : formData.macchine_attrezzature.map((m, i) => (
                                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg mb-2" data-testid={`macchina-row-${i}`}>
                                        <Input className="flex-1" placeholder="Nome" value={m.nome} onChange={e => updateMacchina(i, 'nome', e.target.value)} />
                                        <label className="flex items-center gap-1.5 text-xs whitespace-nowrap"><Checkbox checked={m.marcata_ce} onCheckedChange={v => updateMacchina(i, 'marcata_ce', v)} />CE</label>
                                        <label className="flex items-center gap-1.5 text-xs whitespace-nowrap"><Checkbox checked={m.verifiche_periodiche} onCheckedChange={v => updateMacchina(i, 'verifiche_periodiche', v)} />Verifiche</label>
                                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeMacchina(i)}><Trash2 className="h-4 w-4" /></Button>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Shield className="h-5 w-5 text-[#0055FF]" /> DPI Presenti in Cantiere</CardTitle></CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {formData.dpi_presenti.map((dpi, i) => (
                                        <label key={i} className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all ${dpi.presente ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200'}`}>
                                            <Checkbox checked={dpi.presente} onCheckedChange={() => toggleDpi(i)} />
                                            <span className="text-sm">{dpi.tipo_dpi}</span>
                                        </label>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                        {/* DPI calcolati da rischi */}
                        {formData.dpi_calcolati.length > 0 && (
                            <Card className="border-emerald-200">
                                <CardHeader><CardTitle className="text-base text-emerald-800">DPI Calcolati da Rischi ({formData.dpi_calcolati.length})</CardTitle></CardHeader>
                                <CardContent>
                                    <div className="flex flex-wrap gap-2">
                                        {formData.dpi_calcolati.map((d, i) => (
                                            <Badge key={i} className="bg-emerald-50 text-emerald-800 text-xs">{dpiMap[d.codice]?.nome || d.codice}</Badge>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                        {formData.misure_calcolate.length > 0 && (
                            <Card className="border-purple-200">
                                <CardHeader><CardTitle className="text-base text-purple-800">Misure Organizzative ({formData.misure_calcolate.length})</CardTitle></CardHeader>
                                <CardContent>
                                    <div className="flex flex-wrap gap-2">
                                        {formData.misure_calcolate.map((m, i) => (
                                            <Badge key={i} className="bg-purple-50 text-purple-800 text-xs">{dpiMap[m.codice]?.nome || m.codice}</Badge>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                        {formData.apprestamenti_calcolati.length > 0 && (
                            <Card className="border-orange-200">
                                <CardHeader><CardTitle className="text-base text-orange-800">Apprestamenti ({formData.apprestamenti_calcolati.length})</CardTitle></CardHeader>
                                <CardContent>
                                    <div className="flex flex-wrap gap-2">
                                        {formData.apprestamenti_calcolati.map((a, i) => (
                                            <Badge key={i} className="bg-orange-50 text-orange-800 text-xs">{dpiMap[a.codice]?.nome || a.codice}</Badge>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                        <Card>
                            <CardHeader><CardTitle className="text-lg">Altre Informazioni</CardTitle></CardHeader>
                            <CardContent className="space-y-4">
                                <div><Label>Stoccaggio materiali e/o rifiuti</Label><Textarea data-testid="input-stoccaggio" value={formData.stoccaggio_materiali} onChange={e => setFormData(p => ({ ...p, stoccaggio_materiali: e.target.value }))} rows={2} /></div>
                                <div><Label>Servizi igienico-assistenziali</Label><Textarea data-testid="input-servizi" value={formData.servizi_igienici} onChange={e => setFormData(p => ({ ...p, servizi_igienici: e.target.value }))} rows={2} /></div>
                                <div><Label>Note aggiuntive</Label><Textarea value={formData.note_aggiuntive} onChange={e => setFormData(p => ({ ...p, note_aggiuntive: e.target.value }))} rows={2} /></div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ── Step 4: Riepilogo & Gate ── */}
                {step === 4 && (
                    <div className="space-y-6">
                        <Card className={gate?.pronto_per_generazione ? 'border-emerald-300' : 'border-amber-300'}>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    {gate?.pronto_per_generazione ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <AlertTriangle className="h-5 w-5 text-amber-600" />}
                                    Gate POS
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="flex-1 bg-gray-200 rounded-full h-3">
                                        <div className={`h-3 rounded-full transition-all ${gate?.pronto_per_generazione ? 'bg-emerald-500' : 'bg-amber-500'}`}
                                            style={{ width: `${gate?.completezza_percentuale || 0}%` }} />
                                    </div>
                                    <span className="text-sm font-bold">{gate?.completezza_percentuale || 0}%</span>
                                </div>
                                {gate?.campi_mancanti?.length > 0 && (
                                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3">
                                        <p className="text-sm font-medium text-amber-800 mb-1">Campi mancanti:</p>
                                        <ul className="text-sm text-amber-700 list-disc list-inside">{gate.campi_mancanti.map((c, i) => <li key={i}>{c}</li>)}</ul>
                                    </div>
                                )}
                                {gate?.blockers?.length > 0 && (
                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                                        <p className="text-sm font-medium text-red-800 mb-1">Blockers:</p>
                                        <ul className="text-sm text-red-700 list-disc list-inside">{gate.blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>
                                    </div>
                                )}
                                {gate?.pronto_per_generazione && (
                                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                                        <p className="text-sm text-emerald-800">Scheda pronta per la generazione POS DOCX.</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <Card>
                                <CardHeader><CardTitle className="text-base">Dati Cantiere</CardTitle></CardHeader>
                                <CardContent className="text-sm space-y-1">
                                    <p><span className="text-slate-500">Indirizzo:</span> {formData.dati_cantiere.indirizzo_cantiere || '-'}</p>
                                    <p><span className="text-slate-500">Citta:</span> {formData.dati_cantiere.citta_cantiere || '-'}</p>
                                    <p><span className="text-slate-500">Committente:</span> {(formData.soggetti.find(s => s.ruolo === 'COMMITTENTE') || {}).nome || '-'}</p>
                                    <p><span className="text-slate-500">Inizio:</span> {formData.dati_cantiere.data_inizio_lavori || '-'}</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader><CardTitle className="text-base">Contatori</CardTitle></CardHeader>
                                <CardContent className="text-sm space-y-1">
                                    <p><span className="text-slate-500">Lavoratori:</span> {formData.lavoratori_coinvolti.length}</p>
                                    <p><span className="text-slate-500">Fasi lavoro:</span> {formData.fasi_lavoro_selezionate.length}</p>
                                    <p><span className="text-slate-500">Rischi attivati:</span> {formData.fasi_lavoro_selezionate.reduce((a, f) => a + (f.rischi_attivati?.length || 0), 0)}</p>
                                    <p><span className="text-slate-500">DPI calcolati:</span> {formData.dpi_calcolati.length}</p>
                                    <p><span className="text-slate-500">Misure:</span> {formData.misure_calcolate.length}</p>
                                    <p><span className="text-slate-500">Apprestamenti:</span> {formData.apprestamenti_calcolati.length}</p>
                                    <p><span className="text-slate-500">Domande residue:</span> {formData.domande_residue.length}</p>
                                </CardContent>
                            </Card>
                        </div>
                        {formData.fasi_lavoro_selezionate.length > 0 && (
                            <Card>
                                <CardHeader><CardTitle className="text-base">Catena Fase → Rischi</CardTitle></CardHeader>
                                <CardContent className="space-y-2">
                                    {formData.fasi_lavoro_selezionate.map((f, i) => {
                                        const faseLib = fasiLib.find(fl => fl.codice === f.fase_codice);
                                        return (
                                            <div key={i} className="p-3 bg-blue-50 rounded-md">
                                                <div className="flex items-center gap-2">
                                                    <ChevronRight className="h-4 w-4 text-[#0055FF]" />
                                                    <span className="text-sm font-medium">{faseLib?.nome || f.fase_codice}</span>
                                                    <Badge className={`text-[10px] ${CONFIDENCE_BADGE[f.confidence] || ''}`}>{f.confidence}</Badge>
                                                    <Badge variant="outline" className="text-xs ml-auto">{(f.rischi_attivati || []).length} rischi</Badge>
                                                </div>
                                                <div className="mt-1 ml-6 flex flex-wrap gap-1">
                                                    {(f.rischi_attivati || []).map((ra, j) => (
                                                        <Badge key={j} className={`text-[10px] ${rischiMap[ra.rischio_codice]?.gate_critical ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                                                            {rischiMap[ra.rischio_codice]?.nome || ra.rischio_codice}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </CardContent>
                            </Card>
                        )}
                        <Card>
                            <CardHeader><CardTitle className="text-base">Dichiarazione</CardTitle></CardHeader>
                            <CardContent>
                                <div className="max-w-xs"><Label>Data dichiarazione</Label><Input type="date" value={formData.data_dichiarazione} onChange={e => setFormData(p => ({ ...p, data_dichiarazione: e.target.value }))} data-testid="input-data-dichiarazione" /></div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* Navigation footer */}
                <div className="flex items-center justify-between pt-4 border-t">
                    <Button variant="outline" onClick={() => step > 1 && setStep(s => s - 1)} disabled={step === 1}><ArrowLeft className="h-4 w-4 mr-2" /> Precedente</Button>
                    <span className="text-sm text-slate-400">Passo {step} di {STEPS.length}</span>
                    {step < STEPS.length ? (
                        <Button onClick={() => { handleSave(); setStep(s => s + 1); }} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">Successivo <ArrowRight className="h-4 w-4 ml-2" /></Button>
                    ) : (
                        <Button onClick={handleSave} disabled={saving} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-save-final">
                            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />} Salva Scheda Finale
                        </Button>
                    )}
                </div>
            </div>
        </DashboardLayout>
    );
}
