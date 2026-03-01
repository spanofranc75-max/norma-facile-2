/**
 * FascicoloTecnicoSection — Sezione Fascicolo Tecnico EN 1090.
 * Gestisce editing dati + download PDF per tutti e 6 i documenti.
 */
import { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Download, Edit3, Plus, Trash2, Loader2, Save, FileText } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const DOCUMENTS = [
    { key: 'dop', label: 'DOP', desc: 'Dichiarazione di Prestazione', endpoint: 'dop-pdf', mod: 'All. 4' },
    { key: 'ce', label: 'Marcatura CE', desc: 'Etichetta CE EN 1090', endpoint: 'ce-pdf', mod: 'All. 5' },
    { key: 'piano', label: 'Piano di Controllo', desc: 'Piano Controllo Qualita\'', endpoint: 'piano-controllo-pdf', mod: 'MOD. 02' },
    { key: 'vt', label: 'Rapporto VT', desc: 'Esame Visivo Dimensionale', endpoint: 'rapporto-vt-pdf', mod: 'MOD. 06' },
    { key: 'registro', label: 'Registro Saldatura', desc: 'Registro di Saldatura', endpoint: 'registro-saldatura-pdf', mod: 'MOD. 04' },
    { key: 'riesame', label: 'Riesame Tecnico', desc: 'Riesame Tecnico EN 1090', endpoint: 'riesame-tecnico-pdf', mod: 'MOD. 01' },
];

export default function FascicoloTecnicoSection({ commessaId }) {
    const [ftData, setFtData] = useState({});
    const [loading, setLoading] = useState(false);
    const [downloading, setDownloading] = useState(null);
    const [editOpen, setEditOpen] = useState(false);
    const [editSection, setEditSection] = useState(null);
    const [editForm, setEditForm] = useState({});
    const [saving, setSaving] = useState(false);

    const loadData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
            });
            if (res.ok) {
                const data = await res.json();
                setFtData(data);
            }
        } catch (e) { /* silent */ }
    }, [commessaId]);

    useEffect(() => { loadData(); }, [loadData]);

    const handleDownload = async (doc) => {
        setDownloading(doc.key);
        try {
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}/${doc.endpoint}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Errore generazione PDF');
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${doc.label.replace(/\s/g, '_')}_${commessaId}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`${doc.label} scaricato`);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setDownloading(null);
        }
    };

    const openEdit = (sectionKey) => {
        setEditSection(sectionKey);
        setEditForm({ ...ftData });
        setEditOpen(true);
    };

    const saveData = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify(editForm)
            });
            if (!res.ok) throw new Error('Errore salvataggio');
            toast.success('Dati fascicolo salvati');
            setFtData(editForm);
            setEditOpen(false);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    const updateField = (key, val) => setEditForm(p => ({ ...p, [key]: val }));

    const addSaldatura = () => {
        const saldature = editForm.saldature || [];
        setEditForm(p => ({
            ...p,
            saldature: [...saldature, {
                numero_disegno: '', numero_saldatura: '', periodo: '', saldatore: '',
                punzone: '', diametro: '', spessore: '', materiale_base: '', wps_numero: '',
                vt_esito: '', vt_data: '', vt_firma: '',
                cnd_tipo: '', cnd_rapporto: '', cnd_data: '', cnd_firma: '', cnd_tratto: '',
                rip_rapporto: '', rip_esito: '', rip_data: ''
            }]
        }));
    };

    const updateSaldatura = (idx, key, val) => {
        const saldature = [...(editForm.saldature || [])];
        saldature[idx] = { ...saldature[idx], [key]: val };
        setEditForm(p => ({ ...p, saldature }));
    };

    const removeSaldatura = (idx) => {
        const saldature = [...(editForm.saldature || [])];
        saldature.splice(idx, 1);
        setEditForm(p => ({ ...p, saldature }));
    };

    const updateRequisito = (idx, key, val) => {
        const requisiti = [...(editForm.requisiti || [])];
        requisiti[idx] = { ...requisiti[idx], [key]: val };
        setEditForm(p => ({ ...p, requisiti }));
    };

    const updateItt = (idx, key, val) => {
        const itt = [...(editForm.itt || [])];
        itt[idx] = { ...itt[idx], [key]: val };
        setEditForm(p => ({ ...p, itt }));
    };

    // Render edit sections based on document type
    const renderEditContent = () => {
        if (!editSection) return null;

        switch (editSection) {
            case 'dop':
                return <DopEditForm form={editForm} update={updateField} />;
            case 'ce':
                return <CeEditForm form={editForm} update={updateField} />;
            case 'piano':
                return <PianoEditForm form={editForm} update={updateField} />;
            case 'vt':
                return <VtEditForm form={editForm} update={updateField} />;
            case 'registro':
                return <RegistroEditForm form={editForm} update={updateField}
                    addSaldatura={addSaldatura} updateSaldatura={updateSaldatura} removeSaldatura={removeSaldatura} />;
            case 'riesame':
                return <RiesameEditForm form={editForm} update={updateField}
                    updateRequisito={updateRequisito} updateItt={updateItt} />;
            default:
                return null;
        }
    };

    const editTitle = DOCUMENTS.find(d => d.key === editSection)?.label || '';

    return (
        <div data-testid="fascicolo-tecnico-section">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {DOCUMENTS.map(doc => (
                    <div key={doc.key}
                        className="p-3 rounded-lg border border-slate-200 bg-white hover:shadow-sm transition-shadow"
                        data-testid={`ft-card-${doc.key}`}>
                        <div className="flex items-center justify-between mb-1.5">
                            <div className="min-w-0">
                                <span className="font-bold text-slate-800 text-sm block truncate">{doc.label}</span>
                                <p className="text-[10px] text-slate-500">{doc.desc} — {doc.mod}</p>
                            </div>
                        </div>
                        <div className="flex gap-1.5">
                            <Button size="sm" variant="outline"
                                className="text-xs h-7 flex-1"
                                data-testid={`btn-edit-${doc.key}`}
                                onClick={() => openEdit(doc.key)}>
                                <Edit3 className="h-3 w-3 mr-1" /> Compila
                            </Button>
                            <Button size="sm" variant="default"
                                className="text-xs h-7 flex-1 bg-slate-800 hover:bg-slate-700"
                                data-testid={`btn-download-${doc.key}`}
                                disabled={downloading === doc.key}
                                onClick={() => handleDownload(doc)}>
                                {downloading === doc.key
                                    ? <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                    : <Download className="h-3 w-3 mr-1" />}
                                PDF
                            </Button>
                        </div>
                    </div>
                ))}
            </div>

            <Dialog open={editOpen} onOpenChange={setEditOpen}>
                <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="fascicolo-edit-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5" />
                            Compila — {editTitle}
                        </DialogTitle>
                        <DialogDescription>Modifica i campi editabili. I dati della commessa vengono compilati automaticamente.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        {renderEditContent()}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)} data-testid="btn-cancel-edit">Annulla</Button>
                        <Button onClick={saveData} disabled={saving} data-testid="btn-save-fascicolo">
                            {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}
                            Salva
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

// ─── Field helpers ───
function Field({ label, value, onChange, placeholder, className = '' }) {
    return (
        <div className={className}>
            <Label className="text-xs font-semibold text-slate-600">{label}</Label>
            <Input value={value || ''} onChange={e => onChange(e.target.value)}
                placeholder={placeholder} className="h-8 text-sm mt-0.5" />
        </div>
    );
}

function RadioGroup({ label, value, onChange, options }) {
    return (
        <div>
            <Label className="text-xs font-semibold text-slate-600">{label}</Label>
            <div className="flex gap-3 mt-1">
                {options.map(opt => (
                    <label key={opt.value} className="flex items-center gap-1 text-xs cursor-pointer">
                        <input type="radio" name={label} value={opt.value}
                            checked={value === opt.value}
                            onChange={() => onChange(opt.value)}
                            className="accent-slate-800" />
                        {opt.label}
                    </label>
                ))}
            </div>
        </div>
    );
}

function CheckField({ label, checked, onChange }) {
    return (
        <label className="flex items-center gap-1.5 text-xs cursor-pointer">
            <input type="checkbox" checked={!!checked} onChange={e => onChange(e.target.checked)} className="accent-slate-800" />
            {label}
        </label>
    );
}


// ─── DOP Edit Form ───
function DopEditForm({ form, update }) {
    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Dichiarazione di Prestazione (Regolamento UE 574/2014)</p>
            <div className="grid grid-cols-2 gap-3">
                <Field label="DDT Riferimento" value={form.ddt_riferimento} onChange={v => update('ddt_riferimento', v)} placeholder="N. DDT" />
                <Field label="Data DDT" value={form.ddt_data} onChange={v => update('ddt_data', v)} placeholder="GG/MM/AAAA" />
                <Field label="Mandatario" value={form.mandatario} onChange={v => update('mandatario', v)} placeholder="Nome mandatario" />
                <Field label="Firmatario" value={form.firmatario} onChange={v => update('firmatario', v)} placeholder="Nome e cognome" />
                <Field label="Ruolo Firmatario" value={form.ruolo_firmatario} onChange={v => update('ruolo_firmatario', v)} placeholder="Legale Rappresentante" />
                <Field label="Luogo e Data Firma" value={form.luogo_data_firma} onChange={v => update('luogo_data_firma', v)} placeholder="Bologna, GG/MM/AAAA" />
                <Field label="Certificato Numero" value={form.certificato_numero} onChange={v => update('certificato_numero', v)} placeholder="N. certificato" />
                <Field label="Ente Notificato" value={form.ente_notificato} onChange={v => update('ente_notificato', v)} placeholder="Rina Service" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <Field label="Materiali / Saldabilita'" value={form.materiali_saldabilita} onChange={v => update('materiali_saldabilita', v)} />
                <Field label="Resilienza" value={form.resilienza} onChange={v => update('resilienza', v)} placeholder="27 Joule a +/- 20 C" />
            </div>
        </div>
    );
}

// ─── CE Edit Form ───
function CeEditForm({ form, update }) {
    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Etichetta Marcatura CE — EN 1090-1:2009 + A1:2011</p>
            <div className="grid grid-cols-2 gap-3">
                <Field label="Ente Notificato" value={form.ente_notificato} onChange={v => update('ente_notificato', v)} placeholder="Rina Service" />
                <Field label="Numero Ente" value={form.ente_numero} onChange={v => update('ente_numero', v)} placeholder="0474" />
                <Field label="Certificato N." value={form.certificato_numero} onChange={v => update('certificato_numero', v)} />
                <Field label="DOP N." value={form.dop_numero} onChange={v => update('dop_numero', v)} />
                <Field label="Disegno Riferimento" value={form.disegno_riferimento} onChange={v => update('disegno_riferimento', v)} placeholder="STR02" />
                <Field label="Materiali" value={form.materiali_saldabilita} onChange={v => update('materiali_saldabilita', v)} />
                <Field label="Resilienza" value={form.resilienza} onChange={v => update('resilienza', v)} />
            </div>
        </div>
    );
}

// ─── Piano di Controllo Edit Form ───
function PianoEditForm({ form, update }) {
    const fasi = form.fasi || [];
    const toggleApplicabile = (idx) => {
        const newFasi = [...fasi];
        newFasi[idx] = { ...newFasi[idx], applicabile: !newFasi[idx].applicabile };
        update('fasi', newFasi);
    };
    const updateFase = (idx, key, val) => {
        const newFasi = [...fasi];
        newFasi[idx] = { ...newFasi[idx], [key]: val };
        update('fasi', newFasi);
    };

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Piano di Controllo Qualita' — MOD. 02</p>
            <div className="grid grid-cols-2 gap-3">
                <Field label="Disegno N." value={form.disegno_numero} onChange={v => update('disegno_numero', v)} placeholder="STR02" />
                <Field label="Ordine N." value={form.ordine_numero} onChange={v => update('ordine_numero', v)} />
            </div>
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">Fasi di Controllo</div>
                <div className="max-h-64 overflow-y-auto">
                    {fasi.map((f, i) => (
                        <div key={i} className={`flex items-center gap-2 px-3 py-1.5 border-b text-xs ${!f.applicabile ? 'bg-slate-50 opacity-60' : ''}`}>
                            <CheckField label="" checked={f.applicabile} onChange={() => toggleApplicabile(i)} />
                            <span className="flex-1 min-w-0 truncate" title={f.fase}>{f.fase}</span>
                            {f.applicabile && (
                                <>
                                    <select value={f.esito || ''} onChange={e => updateFase(i, 'esito', e.target.value)}
                                        className="h-6 text-[10px] rounded border px-1 w-20">
                                        <option value="">—</option>
                                        <option value="positivo">Positivo</option>
                                        <option value="negativo">Negativo</option>
                                    </select>
                                    <input value={f.data_effettiva || ''} onChange={e => updateFase(i, 'data_effettiva', e.target.value)}
                                        placeholder="Data" className="h-6 text-[10px] rounded border px-1 w-20" />
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Rapporto VT Edit Form ───
function VtEditForm({ form, update }) {
    const updateCheckGroup = (group, key, val) => {
        const current = form[group] || {};
        update(group, { ...current, [key]: val });
    };

    const oggetti = form.oggetti_controllati || [];
    const addOggetto = () => {
        update('oggetti_controllati', [...oggetti, { numero: '', disegno: '', marca: '', dimensioni: '', estensione_controllo: '100', esito: '' }]);
    };
    const updateOggetto = (idx, key, val) => {
        const newOgg = [...oggetti];
        newOgg[idx] = { ...newOgg[idx], [key]: val };
        update('oggetti_controllati', newOgg);
    };
    const removeOggetto = (idx) => {
        const newOgg = [...oggetti];
        newOgg.splice(idx, 1);
        update('oggetti_controllati', newOgg);
    };

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Rapporto di Esame Visivo Dimensionale — MOD. 06</p>
            <div className="grid grid-cols-2 gap-3">
                <Field label="Report N." value={form.report_numero} onChange={v => update('report_numero', v)} />
                <Field label="Data Report" value={form.report_data} onChange={v => update('report_data', v)} placeholder="GG/MM/AAAA" />
                <Field label="Processo Saldatura" value={form.processo_saldatura} onChange={v => update('processo_saldatura', v)} />
                <Field label="Norma/Procedura" value={form.norma_procedura} onChange={v => update('norma_procedura', v)} />
                <Field label="Accettabilita'" value={form.accettabilita} onChange={v => update('accettabilita', v)} />
                <Field label="Materiale" value={form.materiale} onChange={v => update('materiale', v)} />
                <Field label="Temp. pezzo" value={form.temperatura_pezzo} onChange={v => update('temperatura_pezzo', v)} />
                <Field label="Profilato" value={form.profilato} onChange={v => update('profilato', v)} />
                <Field label="Spessore" value={form.spessore} onChange={v => update('spessore', v)} />
                <Field label="Tipo illuminatore" value={form.tipo_illuminatore} onChange={v => update('tipo_illuminatore', v)} />
                <Field label="Distanza max (mm)" value={form.distanza_max_mm} onChange={v => update('distanza_max_mm', v)} />
                <Field label="Angolo min (gradi)" value={form.angolo_min_gradi} onChange={v => update('angolo_min_gradi', v)} />
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Condizioni di visione</Label>
                <div className="flex gap-4 flex-wrap">
                    {['naturale', 'artificiale', 'lampada_wood'].map(k => (
                        <CheckField key={k} label={k.replace(/_/g, ' ')} checked={form.condizioni_visione?.[k]}
                            onChange={v => updateCheckGroup('condizioni_visione', k, v)} />
                    ))}
                </div>
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Stato superficie</Label>
                <div className="flex gap-4 flex-wrap">
                    {['come_saldato', 'molato', 'spazzolato', 'lavorato_macchina', 'come_laminato', 'verniciato'].map(k => (
                        <CheckField key={k} label={k.replace(/_/g, ' ')} checked={form.stato_superficie?.[k]}
                            onChange={v => updateCheckGroup('stato_superficie', k, v)} />
                    ))}
                </div>
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Tipo ispezione</Label>
                <div className="flex gap-4 flex-wrap">
                    {['diretto', 'remoto', 'generale', 'locale'].map(k => (
                        <CheckField key={k} label={k.replace(/_/g, ' ')} checked={form.tipo_ispezione?.[k]}
                            onChange={v => updateCheckGroup('tipo_ispezione', k, v)} />
                    ))}
                </div>
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Attrezzatura</Label>
                <div className="flex gap-4 flex-wrap">
                    {['calibro', 'specchio', 'lente', 'endoscopio', 'fotocamera', 'videocamera'].map(k => (
                        <CheckField key={k} label={k} checked={form.attrezzatura?.[k]}
                            onChange={v => updateCheckGroup('attrezzatura', k, v)} />
                    ))}
                </div>
            </div>
            <Field label="Marca/Modello/Matricola calibro" value={form.calibro_info} onChange={v => update('calibro_info', v)} />
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700">Oggetti Controllati</span>
                    <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={addOggetto}>
                        <Plus className="h-3 w-3 mr-1" /> Aggiungi
                    </Button>
                </div>
                {oggetti.map((o, i) => (
                    <div key={i} className="flex gap-1 px-2 py-1 border-b items-center">
                        <input value={o.numero} onChange={e => updateOggetto(i, 'numero', e.target.value)} placeholder="N." className="h-6 text-[10px] border rounded px-1 w-8" />
                        <input value={o.disegno} onChange={e => updateOggetto(i, 'disegno', e.target.value)} placeholder="Disegno" className="h-6 text-[10px] border rounded px-1 w-16" />
                        <input value={o.marca} onChange={e => updateOggetto(i, 'marca', e.target.value)} placeholder="Marca" className="h-6 text-[10px] border rounded px-1 w-16" />
                        <input value={o.dimensioni} onChange={e => updateOggetto(i, 'dimensioni', e.target.value)} placeholder="Dimensioni" className="h-6 text-[10px] border rounded px-1 w-20" />
                        <input value={o.estensione_controllo} onChange={e => updateOggetto(i, 'estensione_controllo', e.target.value)} placeholder="%" className="h-6 text-[10px] border rounded px-1 w-10" />
                        <select value={o.esito} onChange={e => updateOggetto(i, 'esito', e.target.value)} className="h-6 text-[10px] border rounded px-1 w-18">
                            <option value="">—</option>
                            <option value="Positivo">Positivo</option>
                            <option value="Negativo">Negativo</option>
                        </select>
                        <button onClick={() => removeOggetto(i)} className="text-red-400 hover:text-red-600"><Trash2 className="h-3 w-3" /></button>
                    </div>
                ))}
            </div>
            <div>
                <Label className="text-xs font-semibold text-slate-600">Note</Label>
                <Textarea value={form.note_vt || ''} onChange={e => update('note_vt', e.target.value)} rows={2} className="text-sm mt-0.5" />
            </div>
        </div>
    );
}

// ─── Registro Saldatura Edit Form ───
function RegistroEditForm({ form, update, addSaldatura, updateSaldatura, removeSaldatura }) {
    const saldature = form.saldature || [];

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Registro di Saldatura — MOD. 04</p>
            <div className="grid grid-cols-3 gap-3">
                <Field label="Data Emissione" value={form.data_emissione} onChange={v => update('data_emissione', v)} placeholder="GG/MM/AAAA" />
                <Field label="Firma CS" value={form.firma_cs} onChange={v => update('firma_cs', v)} placeholder="Nome responsabile" />
                <div />
                <Field label="% VT" value={form.perc_vt} onChange={v => update('perc_vt', v)} placeholder="100" />
                <Field label="% MT/PT" value={form.perc_mt_pt} onChange={v => update('perc_mt_pt', v)} placeholder="0" />
                <Field label="% RX-RY/UT" value={form.perc_rx_ut} onChange={v => update('perc_rx_ut', v)} placeholder="0" />
            </div>
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700">Saldature Registrate</span>
                    <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={addSaldatura} data-testid="btn-add-saldatura">
                        <Plus className="h-3 w-3 mr-1" /> Aggiungi Riga
                    </Button>
                </div>
                <div className="max-h-64 overflow-y-auto">
                    {saldature.length === 0 && (
                        <p className="text-center text-xs text-slate-400 py-4">Nessuna saldatura. Aggiungi righe o il PDF conterrà righe vuote da compilare a mano.</p>
                    )}
                    {saldature.map((s, i) => (
                        <div key={i} className="p-2 border-b space-y-1">
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold text-slate-500">Saldatura #{i + 1}</span>
                                <button onClick={() => removeSaldatura(i)} className="text-red-400 hover:text-red-600">
                                    <Trash2 className="h-3 w-3" />
                                </button>
                            </div>
                            <div className="grid grid-cols-4 gap-1">
                                <input value={s.numero_disegno} onChange={e => updateSaldatura(i, 'numero_disegno', e.target.value)} placeholder="N. Disegno" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.numero_saldatura} onChange={e => updateSaldatura(i, 'numero_saldatura', e.target.value)} placeholder="N. Saldatura" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.periodo} onChange={e => updateSaldatura(i, 'periodo', e.target.value)} placeholder="Periodo" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.saldatore} onChange={e => updateSaldatura(i, 'saldatore', e.target.value)} placeholder="Saldatore" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.punzone} onChange={e => updateSaldatura(i, 'punzone', e.target.value)} placeholder="Punzone" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.diametro} onChange={e => updateSaldatura(i, 'diametro', e.target.value)} placeholder="Diam." className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.spessore} onChange={e => updateSaldatura(i, 'spessore', e.target.value)} placeholder="Spess." className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.materiale_base} onChange={e => updateSaldatura(i, 'materiale_base', e.target.value)} placeholder="Mat. Base" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.wps_numero} onChange={e => updateSaldatura(i, 'wps_numero', e.target.value)} placeholder="WPS N." className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.vt_esito} onChange={e => updateSaldatura(i, 'vt_esito', e.target.value)} placeholder="VT Esito" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.vt_data} onChange={e => updateSaldatura(i, 'vt_data', e.target.value)} placeholder="VT Data" className="h-6 text-[10px] border rounded px-1" />
                                <input value={s.vt_firma} onChange={e => updateSaldatura(i, 'vt_firma', e.target.value)} placeholder="VT Firma" className="h-6 text-[10px] border rounded px-1" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Riesame Tecnico Edit Form ───
function RiesameEditForm({ form, update, updateRequisito, updateItt }) {
    const requisiti = form.requisiti || [];
    const itt = form.itt || [];

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Riesame Tecnico — MOD. 01 — Checklist requisiti EN 1090</p>
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">Requisiti</div>
                <div className="max-h-64 overflow-y-auto">
                    {requisiti.map((r, i) => (
                        <div key={i} className="flex items-start gap-2 px-2 py-1.5 border-b text-[10px]">
                            <span className="flex-1 min-w-0 pt-0.5">{r.requisito}</span>
                            <div className="flex gap-1.5 shrink-0 items-center">
                                {['si', 'no', 'na'].map(opt => (
                                    <label key={opt} className="flex items-center gap-0.5 cursor-pointer">
                                        <input type="radio" name={`req-${i}`} value={opt}
                                            checked={r.risposta === opt} onChange={() => updateRequisito(i, 'risposta', opt)}
                                            className="accent-slate-800" style={{ width: 12, height: 12 }} />
                                        <span className="uppercase">{opt}</span>
                                    </label>
                                ))}
                            </div>
                            <input value={r.note || ''} onChange={e => updateRequisito(i, 'note', e.target.value)}
                                placeholder="Note/Rif." className="h-5 text-[10px] border rounded px-1 w-32" />
                        </div>
                    ))}
                </div>
            </div>

            <RadioGroup label="Decisione Fattibilita'" value={form.decisione || 'procedere'} onChange={v => update('decisione', v)}
                options={[{ value: 'procedere', label: 'PROCEDERE' }, { value: 'non_procedere', label: 'NON PROCEDERE' }]} />

            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">ITT di Commessa</div>
                <div className="max-h-48 overflow-y-auto">
                    {itt.map((item, i) => (
                        <div key={i} className="flex items-center gap-1 px-2 py-1 border-b text-[10px]">
                            <span className="flex-1 min-w-0 truncate" title={item.caratteristica}>{item.caratteristica}</span>
                            <input value={item.esito_conformita || ''} onChange={e => updateItt(i, 'esito_conformita', e.target.value)}
                                placeholder="Esito" className="h-5 text-[10px] border rounded px-1 w-28" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
