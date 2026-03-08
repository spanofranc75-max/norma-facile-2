/**
 * GateCertificationPanel — EN 13241 (Gates) & EN 12453 (Automation) certification.
 * Shown in commessa detail when normativa_tipo is EN_13241 or tipologia is cancello.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
    Shield, FileText, Tag, Wrench, AlertTriangle, CheckCircle2, Download,
    Save, Plus, ChevronDown, ChevronUp, Zap
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const TIPO_OPTIONS = [
    { value: 'cancello_scorrevole', label: 'Cancello Scorrevole' },
    { value: 'cancello_battente', label: 'Cancello a Battente' },
    { value: 'portone_industriale', label: 'Portone Industriale' },
    { value: 'serranda', label: 'Serranda' },
    { value: 'portone_sezionale', label: 'Portone Sezionale' },
    { value: 'barriera', label: 'Barriera' },
];

const VENTO_OPTIONS = ['Classe 0', 'Classe 1', 'Classe 2', 'Classe 3', 'Classe 4', 'Classe 5'];

async function apiCall(path, opts = {}) {
    const res = await fetch(`${API}/api/gate-cert${path}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...opts,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Errore');
    }
    return res.json();
}

export default function GateCertificationPanel({ commessaId, commessa }) {
    const [cert, setCert] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeSection, setActiveSection] = useState('prestazioni');
    const [form, setForm] = useState({});

    const fetchCert = useCallback(async () => {
        try {
            const data = await apiCall(`/${commessaId}`);
            if (data.certification) {
                setCert(data.certification);
                setForm(data.certification);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchCert(); }, [fetchCert]);

    const handleCreate = async () => {
        setSaving(true);
        try {
            const data = await apiCall('/', {
                method: 'POST',
                body: JSON.stringify({
                    commessa_id: commessaId,
                    tipo_chiusura: 'cancello_scorrevole',
                    azionamento: 'manuale',
                }),
            });
            setCert(data.certification);
            setForm(data.certification);
            toast.success('Certificazione cancello creata');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleSave = async () => {
        if (!cert) return;
        setSaving(true);
        try {
            const data = await apiCall(`/${cert.cert_id}`, {
                method: 'PUT',
                body: JSON.stringify(form),
            });
            setCert(data.certification);
            setForm(data.certification);
            toast.success('Salvato');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDownload = async (type) => {
        const endpoints = {
            dop: 'dop-pdf',
            ce_label: 'ce-label-pdf',
            maintenance: 'maintenance-pdf',
            dichiarazione: 'dichiarazione-ce-pdf',
        };
        try {
            const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
            const res = await fetch(`${API}/api/gate-cert/${commessaId}/${endpoints[type]}`, {
                credentials: 'include',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            });
            if (!res.ok) throw new Error('Errore generazione PDF');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${type}_${commessa?.numero || ''}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch (e) {
            toast.error(e.message);
        }
    };

    const updateForm = (field, value) => setForm(f => ({ ...f, [field]: value }));
    const isMotorizzato = form.azionamento === 'motorizzato';

    if (loading) return <div className="text-center py-8 text-gray-400">Caricamento...</div>;

    if (!cert) {
        return (
            <Card className="border-dashed border-2 border-gray-300">
                <CardContent className="py-10 text-center">
                    <Shield className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                    <p className="text-sm text-gray-500 mb-4">Questa commessa non ha ancora una certificazione cancello EN 13241.</p>
                    <Button onClick={handleCreate} disabled={saving} className="bg-[#0055FF]" data-testid="create-gate-cert-btn">
                        <Plus className="h-4 w-4 mr-2" />
                        Inizia Certificazione Cancello
                    </Button>
                </CardContent>
            </Card>
        );
    }

    const sections = [
        { key: 'prestazioni', label: 'Dati Prestazionali', icon: Shield },
        ...(isMotorizzato ? [{ key: 'sicurezza', label: 'Sicurezza & Automazione', icon: Zap }] : []),
        { key: 'documenti', label: 'Documenti PDF', icon: FileText },
    ];

    return (
        <div className="space-y-4" data-testid="gate-cert-panel">
            {/* Section tabs */}
            <div className="flex gap-2 flex-wrap">
                {sections.map(s => (
                    <Button
                        key={s.key}
                        variant={activeSection === s.key ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setActiveSection(s.key)}
                        className={activeSection === s.key ? 'bg-[#0055FF]' : ''}
                        data-testid={`tab-${s.key}`}
                    >
                        <s.icon className="h-4 w-4 mr-1.5" />
                        {s.label}
                    </Button>
                ))}
            </div>

            {/* Section A: Dati Prestazionali */}
            {activeSection === 'prestazioni' && (
                <Card>
                    <CardHeader className="py-3 px-5">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <Shield className="h-4 w-4 text-[#0055FF]" />
                            Dati Prestazionali (EN 13241)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div>
                                <Label className="text-xs text-gray-500">Tipo Chiusura</Label>
                                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm" value={form.tipo_chiusura || ''} onChange={e => updateForm('tipo_chiusura', e.target.value)} data-testid="select-tipo">
                                    {TIPO_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label className="text-xs text-gray-500">Azionamento</Label>
                                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm" value={form.azionamento || ''} onChange={e => updateForm('azionamento', e.target.value)} data-testid="select-azionamento">
                                    <option value="manuale">Manuale</option>
                                    <option value="motorizzato">Motorizzato</option>
                                </select>
                            </div>
                            <div>
                                <Label className="text-xs text-gray-500">Resistenza al Vento</Label>
                                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm" value={form.resistenza_vento || ''} onChange={e => updateForm('resistenza_vento', e.target.value)} data-testid="select-vento">
                                    {VENTO_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div><Label className="text-xs text-gray-500">Larghezza (mm)</Label><Input type="number" value={form.larghezza_mm || ''} onChange={e => updateForm('larghezza_mm', parseFloat(e.target.value) || null)} data-testid="input-larghezza" /></div>
                            <div><Label className="text-xs text-gray-500">Altezza (mm)</Label><Input type="number" value={form.altezza_mm || ''} onChange={e => updateForm('altezza_mm', parseFloat(e.target.value) || null)} data-testid="input-altezza" /></div>
                            <div><Label className="text-xs text-gray-500">Peso (kg)</Label><Input type="number" value={form.peso_kg || ''} onChange={e => updateForm('peso_kg', parseFloat(e.target.value) || null)} data-testid="input-peso" /></div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div><Label className="text-xs text-gray-500">Sistema a Cascata</Label><Input placeholder="Es. Fac, Rolling Center, BFT" value={form.sistema_cascata || ''} onChange={e => updateForm('sistema_cascata', e.target.value)} data-testid="input-cascata" /></div>
                            <div><Label className="text-xs text-gray-500">Note</Label><Input value={form.note || ''} onChange={e => updateForm('note', e.target.value)} /></div>
                        </div>

                        <div className="flex justify-end pt-2">
                            <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF]" data-testid="save-prestazioni-btn">
                                <Save className="h-4 w-4 mr-2" />{saving ? 'Salvataggio...' : 'Salva Prestazioni'}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Section B: Sicurezza & Automazione (only motorizzato) */}
            {activeSection === 'sicurezza' && isMotorizzato && (
                <div className="space-y-4">
                    {/* Components */}
                    <Card>
                        <CardHeader className="py-3 px-5">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                <Wrench className="h-4 w-4 text-[#0055FF]" />
                                Componenti Installati
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div><Label className="text-xs text-gray-500">Motore — Marca</Label><Input value={form.motore_marca || ''} onChange={e => updateForm('motore_marca', e.target.value)} data-testid="input-motore-marca" /></div>
                                <div><Label className="text-xs text-gray-500">Motore — Modello</Label><Input value={form.motore_modello || ''} onChange={e => updateForm('motore_modello', e.target.value)} /></div>
                                <div><Label className="text-xs text-gray-500">Motore — Matricola</Label><Input value={form.motore_matricola || ''} onChange={e => updateForm('motore_matricola', e.target.value)} /></div>
                                <div><Label className="text-xs text-gray-500">Fotocellule</Label><Input value={form.fotocellule || ''} onChange={e => updateForm('fotocellule', e.target.value)} /></div>
                                <div><Label className="text-xs text-gray-500">Costa Sensibile</Label><Input value={form.costola_sicurezza || ''} onChange={e => updateForm('costola_sicurezza', e.target.value)} /></div>
                                <div><Label className="text-xs text-gray-500">Centralina</Label><Input value={form.centralina || ''} onChange={e => updateForm('centralina', e.target.value)} /></div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Risk Analysis */}
                    <RiskAnalysis rischi={form.analisi_rischi || []} onChange={r => updateForm('analisi_rischi', r)} />

                    {/* Force Tests */}
                    <ForceTests prove={form.prove_forza || []} onChange={p => updateForm('prove_forza', p)} />

                    <div className="flex justify-end">
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF]" data-testid="save-sicurezza-btn">
                            <Save className="h-4 w-4 mr-2" />{saving ? 'Salvataggio...' : 'Salva Sicurezza'}
                        </Button>
                    </div>
                </div>
            )}

            {/* Section C: Documents */}
            {activeSection === 'documenti' && (
                <Card>
                    <CardHeader className="py-3 px-5">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <FileText className="h-4 w-4 text-[#0055FF]" />
                            Genera Documenti
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <DocButton label="DoP (Dichiarazione di Prestazione)" desc="EN 13241 — Prestazioni prodotto" onClick={() => handleDownload('dop')} testId="dl-dop" />
                            <DocButton label="Etichetta CE" desc="Da stampare e applicare al prodotto" onClick={() => handleDownload('ce_label')} testId="dl-ce-label" />
                            {isMotorizzato && (
                                <>
                                    <DocButton label="Dichiarazione CE (Macchine)" desc="Direttiva 2006/42/CE — Insieme cancello+motore" onClick={() => handleDownload('dichiarazione')} testId="dl-dichiarazione" />
                                    <DocButton label="Registro Manutenzione" desc="Libretto obbligatorio per cancelli motorizzati" onClick={() => handleDownload('maintenance')} testId="dl-maintenance" />
                                </>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

function DocButton({ label, desc, onClick, testId }) {
    return (
        <button
            className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-[#0055FF] hover:bg-blue-50/50 transition-all text-left w-full"
            onClick={onClick}
            data-testid={testId}
        >
            <Download className="h-5 w-5 text-[#0055FF] shrink-0" />
            <div>
                <p className="text-sm font-medium text-[#1E293B]">{label}</p>
                <p className="text-xs text-gray-400">{desc}</p>
            </div>
        </button>
    );
}

function RiskAnalysis({ rischi, onChange }) {
    const [open, setOpen] = useState(true);

    const update = (idx, field, value) => {
        const updated = [...rischi];
        updated[idx] = { ...updated[idx], [field]: value };
        onChange(updated);
    };

    const allConforme = rischi.filter(r => r.presente).every(r => r.conforme);

    return (
        <Card>
            <CardHeader className="py-3 px-5 cursor-pointer flex flex-row items-center justify-between" onClick={() => setOpen(!open)}>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    Analisi Rischi (EN 12453)
                    {allConforme && rischi.length > 0 ? (
                        <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Tutti conformi</Badge>
                    ) : rischi.some(r => r.presente && !r.conforme) ? (
                        <Badge className="bg-amber-100 text-amber-700 text-[10px]">Da verificare</Badge>
                    ) : null}
                </CardTitle>
                {open ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
            </CardHeader>
            {open && (
                <CardContent className="p-0">
                    <div className="divide-y divide-gray-100">
                        {rischi.map((r, i) => r.presente && (
                            <div key={r.id} className="px-5 py-2.5 grid grid-cols-12 gap-2 items-center" data-testid={`risk-${r.id}`}>
                                <div className="col-span-1 text-xs font-mono text-gray-400">{r.id}</div>
                                <div className="col-span-4 text-xs text-[#1E293B]">{r.descrizione}</div>
                                <div className="col-span-5">
                                    <Input
                                        placeholder="Misura adottata..."
                                        value={r.misura_adottata || ''}
                                        onChange={e => update(i, 'misura_adottata', e.target.value)}
                                        className="text-xs h-8"
                                    />
                                </div>
                                <div className="col-span-2 flex justify-center">
                                    <button
                                        onClick={() => update(i, 'conforme', !r.conforme)}
                                        className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors ${r.conforme ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}
                                    >
                                        {r.conforme ? 'CONFORME' : 'DA VERIFICARE'}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            )}
        </Card>
    );
}

function ForceTests({ prove, onChange }) {
    const [open, setOpen] = useState(true);

    const addProva = () => {
        onChange([...prove, { punto_misura: '', forza_dinamica_n: null, forza_statica_n: null, conforme: false }]);
    };

    const update = (idx, field, value) => {
        const updated = [...prove];
        updated[idx] = { ...updated[idx], [field]: value };
        // Auto-check compliance
        const fd = parseFloat(updated[idx].forza_dinamica_n) || 0;
        const fs = parseFloat(updated[idx].forza_statica_n) || 0;
        updated[idx].conforme = fd > 0 && fd < 400 && (fs === 0 || fs < 150);
        onChange(updated);
    };

    return (
        <Card>
            <CardHeader className="py-3 px-5 cursor-pointer flex flex-row items-center justify-between" onClick={() => setOpen(!open)}>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Zap className="h-4 w-4 text-blue-500" />
                    Prove di Forza (EN 12453)
                    <span className="text-[10px] text-gray-400 font-normal ml-2">Dinamica &lt; 400N — Statica &lt; 150N</span>
                </CardTitle>
                {open ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
            </CardHeader>
            {open && (
                <CardContent className="space-y-2">
                    {prove.map((p, i) => (
                        <div key={i} className="grid grid-cols-4 gap-2 items-end" data-testid={`force-test-${i}`}>
                            <div>
                                <Label className="text-[10px] text-gray-500">Punto di misura</Label>
                                <select className="w-full border rounded-md px-2 py-1.5 text-xs" value={p.punto_misura || ''} onChange={e => update(i, 'punto_misura', e.target.value)}>
                                    <option value="">Seleziona...</option>
                                    <option value="bordo_primario">Bordo primario</option>
                                    <option value="bordo_secondario">Bordo secondario</option>
                                    <option value="zona_cesoiamento">Zona cesoiamento</option>
                                    <option value="altro">Altro</option>
                                </select>
                            </div>
                            <div>
                                <Label className="text-[10px] text-gray-500">F. Dinamica (N)</Label>
                                <Input type="number" className="text-xs h-8" value={p.forza_dinamica_n || ''} onChange={e => update(i, 'forza_dinamica_n', parseFloat(e.target.value) || null)} />
                            </div>
                            <div>
                                <Label className="text-[10px] text-gray-500">F. Statica (N)</Label>
                                <Input type="number" className="text-xs h-8" value={p.forza_statica_n || ''} onChange={e => update(i, 'forza_statica_n', parseFloat(e.target.value) || null)} />
                            </div>
                            <div className="flex items-center justify-center h-8">
                                {p.conforme ? (
                                    <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-3 w-3 mr-1" />OK</Badge>
                                ) : p.forza_dinamica_n ? (
                                    <Badge className="bg-red-100 text-red-700 text-[10px]"><AlertTriangle className="h-3 w-3 mr-1" />KO</Badge>
                                ) : null}
                            </div>
                        </div>
                    ))}
                    <Button variant="outline" size="sm" onClick={addProva} className="mt-1" data-testid="add-force-test-btn">
                        <Plus className="h-3 w-3 mr-1" /> Aggiungi Prova
                    </Button>
                </CardContent>
            )}
        </Card>
    );
}
