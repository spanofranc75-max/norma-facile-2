/**
 * FascicoloTecnicoSection — Fascicolo Tecnico EN 1090.
 * Auto-compilazione intelligente + evidenziazione campi mancanti.
 * Timeline produzione + download Fascicolo Completo.
 */
import { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Download, Edit3, Plus, Trash2, Loader2, Save, FileText, CheckCircle2, AlertCircle, PackageOpen, Clock, Users, Wrench, AlertTriangle } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';

const API = process.env.REACT_APP_BACKEND_URL;

const DOCUMENTS = [
    { key: 'dop', label: 'DOP', desc: 'Dichiarazione di Prestazione', endpoint: 'dop-pdf', mod: 'All. 4', requiredFields: ['certificato_numero','ente_notificato','firmatario','luogo_data_firma','ddt_riferimento','ddt_data'] },
    { key: 'ce', label: 'Marcatura CE', desc: 'Etichetta CE EN 1090', endpoint: 'ce-pdf', mod: 'All. 5', requiredFields: ['certificato_numero','ente_notificato','ente_numero','disegno_riferimento'] },
    { key: 'piano', label: 'Piano di Controllo', desc: 'Piano Controllo Qualita\'', endpoint: 'piano-controllo-pdf', mod: 'MOD. 02', requiredFields: ['disegno_numero'] },
    { key: 'vt', label: 'Rapporto VT', desc: 'Esame Visivo Dimensionale', endpoint: 'rapporto-vt-pdf', mod: 'MOD. 06', requiredFields: ['processo_saldatura'] },
    { key: 'registro', label: 'Registro Saldatura', desc: 'Registro di Saldatura', endpoint: 'registro-saldatura-pdf', mod: 'MOD. 04', requiredFields: [] },
    { key: 'riesame', label: 'Riesame Tecnico', desc: 'Riesame Tecnico EN 1090', endpoint: 'riesame-tecnico-pdf', mod: 'MOD. 01', requiredFields: [] },
];

// Common fields that are auto-populated
const SHARED_AUTO = ['client_name','commessa_numero','commessa_title','disegno_numero','disegno_riferimento','redatto_da','classe_esecuzione','materiale','profilato','materiali_saldabilita','spessore'];

export default function FascicoloTecnicoSection({ commessaId }) {
    const [ftData, setFtData] = useState({});
    const [autoFields, setAutoFields] = useState([]);
    const [timeline, setTimeline] = useState([]);
    const [downloading, setDownloading] = useState(null);
    const [editOpen, setEditOpen] = useState(false);
    const [editSection, setEditSection] = useState(null);
    const [editForm, setEditForm] = useState({});
    const [saving, setSaving] = useState(false);
    const [completoOpen, setCompletoOpen] = useState(false);
    const [completoSel, setCompletoSel] = useState({dop:true,ce:true,piano:true,vt:true,registro:true,riesame:true});
    const [completoLoading, setCompletoLoading] = useState(false);
    const [superLoading, setSuperLoading] = useState(false);

    const loadData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
            });
            if (res.ok) {
                const data = await res.json();
                setAutoFields(data._auto_fields || []);
                setTimeline(data._timeline || []);
                delete data._auto_fields;
                delete data._timeline;
                delete data._giorni_consegna;
                setFtData(data);
            }
        } catch (e) { /* silent */ }
    }, [commessaId]);

    useEffect(() => { loadData(); }, [loadData]);

    // Calculate completion for each document
    const getCompletion = (doc) => {
        const allFields = [...SHARED_AUTO, ...doc.requiredFields];
        const filled = allFields.filter(f => ftData[f] && String(ftData[f]).trim()).length;
        return { filled, total: allFields.length, pct: allFields.length ? Math.round((filled / allFields.length) * 100) : 100 };
    };

    const getMissing = (doc) => {
        return doc.requiredFields.filter(f => !ftData[f] || !String(ftData[f]).trim());
    };

    const handleDownload = async (doc) => {
        setDownloading(doc.key);
        try {
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}/${doc.endpoint}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
            });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Errore');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `${doc.label.replace(/\s/g, '_')}_${commessaId}.pdf`; a.click();
            URL.revokeObjectURL(url);
            toast.success(`${doc.label} scaricato`);
        } catch (e) { toast.error(e.message); }
        finally { setDownloading(null); }
    };

    const handleDownloadCompleto = async () => {
        const sel = Object.entries(completoSel).filter(([,v])=>v).map(([k])=>k).join(',');
        if (!sel) { toast.error('Seleziona almeno un documento'); return; }
        setCompletoLoading(true);
        try {
            const res = await fetch(`${API}/api/fascicolo-tecnico/${commessaId}/fascicolo-completo-pdf?docs=${sel}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
            });
            if (!res.ok) throw new Error('Errore generazione');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `Fascicolo_Tecnico_Completo_${commessaId}.pdf`; a.click();
            URL.revokeObjectURL(url);
            toast.success('Fascicolo Tecnico Completo scaricato');
            setCompletoOpen(false);
        } catch (e) { toast.error(e.message); }
        finally { setCompletoLoading(false); }
    };

    const handleDownloadSuperFascicolo = async () => {
        setSuperLoading(true);
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/fascicolo-tecnico-completo`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
            });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Errore generazione fascicolo');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `Fascicolo_Tecnico_Unico_${commessaId}.pdf`; a.click();
            URL.revokeObjectURL(url);
            toast.success('Fascicolo Tecnico Unico scaricato con successo');
        } catch (e) { toast.error(e.message); }
        finally { setSuperLoading(false); }
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
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
                body: JSON.stringify(editForm)
            });
            if (!res.ok) throw new Error('Errore salvataggio');
            toast.success('Dati fascicolo salvati');
            setFtData(editForm);
            setEditOpen(false);
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const updateField = (key, val) => setEditForm(p => ({ ...p, [key]: val }));

    const addSaldatura = () => {
        setEditForm(p => ({
            ...p, saldature: [...(p.saldature || []), {
                numero_disegno: '', numero_saldatura: '', periodo: '', saldatore: '', punzone: '',
                diametro: '', spessore: '', materiale_base: '', wps_numero: '',
                vt_esito: '', vt_data: '', vt_firma: '', cnd_tipo: '', cnd_rapporto: '',
                cnd_data: '', cnd_firma: '', cnd_tratto: '', rip_rapporto: '', rip_esito: '', rip_data: ''
            }]
        }));
    };
    const updateSaldatura = (idx, key, val) => {
        const s = [...(editForm.saldature || [])];
        s[idx] = { ...s[idx], [key]: val };
        setEditForm(p => ({ ...p, saldature: s }));
    };
    const removeSaldatura = (idx) => {
        const s = [...(editForm.saldature || [])];
        s.splice(idx, 1);
        setEditForm(p => ({ ...p, saldature: s }));
    };
    const updateRequisito = (idx, key, val) => {
        const r = [...(editForm.requisiti || [])];
        r[idx] = { ...r[idx], [key]: val };
        setEditForm(p => ({ ...p, requisiti: r }));
    };
    const updateItt = (idx, key, val) => {
        const r = [...(editForm.itt || [])];
        r[idx] = { ...r[idx], [key]: val };
        setEditForm(p => ({ ...p, itt: r }));
    };

    const renderEditContent = () => {
        if (!editSection) return null;
        const props = { form: editForm, update: updateField, autoFields, ftData };
        switch (editSection) {
            case 'dop': return <DopEditForm {...props} />;
            case 'ce': return <CeEditForm {...props} />;
            case 'piano': return <PianoEditForm {...props} timeline={timeline} />;
            case 'vt': return <VtEditForm {...props} />;
            case 'registro': return <RegistroEditForm {...props} addSaldatura={addSaldatura} updateSaldatura={updateSaldatura} removeSaldatura={removeSaldatura} />;
            case 'riesame': return <RiesameEditForm {...props} updateRequisito={updateRequisito} updateItt={updateItt} />;
            default: return null;
        }
    };

    const editTitle = DOCUMENTS.find(d => d.key === editSection)?.label || '';

    return (
        <div data-testid="fascicolo-tecnico-section">
            {/* Timeline produzione */}
            {timeline.length > 0 && (
                <div className="mb-3 p-2.5 bg-slate-50 rounded-lg border" data-testid="produzione-timeline">
                    <div className="flex items-center gap-1.5 mb-2">
                        <Clock className="h-3.5 w-3.5 text-slate-500" />
                        <span className="text-[11px] font-bold text-slate-600">Timeline Produzione</span>
                    </div>
                    <div className="flex gap-1">
                        {timeline.map((t, i) => {
                            const bg = t.stato === 'completato' ? 'bg-emerald-500' : t.stato === 'in_corso' ? 'bg-blue-500' : 'bg-slate-300';
                            return (
                                <div key={i} className="flex-1 text-center" title={`${t.fase}: ${t.stato}`}>
                                    <div className={`h-2 rounded-full ${bg} transition-all`} />
                                    <span className="text-[8px] text-slate-500 mt-0.5 block truncate">{t.fase}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Document cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {DOCUMENTS.map(doc => {
                    const comp = getCompletion(doc);
                    const missing = getMissing(doc);
                    const isComplete = missing.length === 0;
                    return (
                        <div key={doc.key}
                            className={`p-3 rounded-lg border transition-shadow hover:shadow-sm ${isComplete ? 'border-emerald-200 bg-emerald-50/30' : 'border-amber-200 bg-amber-50/30'}`}
                            data-testid={`ft-card-${doc.key}`}>
                            <div className="flex items-start justify-between mb-1.5">
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-1.5">
                                        {isComplete
                                            ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                                            : <AlertCircle className="h-3.5 w-3.5 text-amber-500 shrink-0" />}
                                        <span className="font-bold text-slate-800 text-sm truncate">{doc.label}</span>
                                    </div>
                                    <p className="text-[10px] text-slate-500 ml-5">{doc.desc} — {doc.mod}</p>
                                </div>
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${comp.pct === 100 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                                    {comp.filled}/{comp.total}
                                </span>
                            </div>
                            {missing.length > 0 && (
                                <div className="mb-1.5 ml-5">
                                    <p className="text-[9px] text-amber-600 font-medium">
                                        Da completare: {missing.map(f => f.replace(/_/g, ' ')).join(', ')}
                                    </p>
                                </div>
                            )}
                            <div className="flex gap-1.5 ml-5">
                                <Button size="sm" variant="outline" className="text-xs h-7 flex-1"
                                    data-testid={`btn-edit-${doc.key}`} onClick={() => openEdit(doc.key)}>
                                    <Edit3 className="h-3 w-3 mr-1" /> Compila
                                </Button>
                                <Button size="sm" variant="default" className="text-xs h-7 flex-1 bg-slate-800 hover:bg-slate-700"
                                    data-testid={`btn-download-${doc.key}`} disabled={downloading === doc.key}
                                    onClick={() => handleDownload(doc)}>
                                    {downloading === doc.key ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Download className="h-3 w-3 mr-1" />}
                                    PDF
                                </Button>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Genera Fascicolo Tecnico */}
            <div className="mt-4 space-y-2">
                <Button variant="default" className="w-full bg-[#1a3a6b] hover:bg-[#15325c] text-white font-bold text-sm h-11 shadow-md"
                    data-testid="btn-super-fascicolo" disabled={superLoading} onClick={handleDownloadSuperFascicolo}>
                    {superLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
                    Scarica Fascicolo Tecnico Completo (PDF Unico)
                </Button>
                <div className="flex justify-center">
                    <Button variant="outline" size="sm" className="text-xs text-slate-500 border-slate-300"
                        data-testid="btn-fascicolo-completo" onClick={() => setCompletoOpen(true)}>
                        <PackageOpen className="h-3.5 w-3.5 mr-1.5" /> Seleziona documenti singoli
                    </Button>
                </div>
            </div>

            {/* Dialog Fascicolo Completo */}
            <Dialog open={completoOpen} onOpenChange={setCompletoOpen}>
                <DialogContent className="max-w-md" data-testid="dialog-fascicolo-completo">
                    <DialogHeader>
                        <DialogTitle>Genera Fascicolo Tecnico Completo</DialogTitle>
                        <DialogDescription>Seleziona i documenti da includere nel PDF combinato.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 py-2">
                        {DOCUMENTS.map(doc => {
                            const comp = getCompletion(doc);
                            return (
                                <label key={doc.key} className="flex items-center gap-2 p-2 rounded hover:bg-slate-50 cursor-pointer text-sm">
                                    <input type="checkbox" checked={completoSel[doc.key]} className="accent-slate-800"
                                        onChange={e => setCompletoSel(p => ({...p, [doc.key]: e.target.checked}))} />
                                    <span className="flex-1 font-medium">{doc.label}</span>
                                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${comp.pct === 100 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                                        {comp.pct}%
                                    </span>
                                </label>
                            );
                        })}
                        <div className="flex gap-2 pt-2">
                            <Button size="sm" variant="ghost" className="text-xs"
                                onClick={() => setCompletoSel({dop:true,ce:true,piano:true,vt:true,registro:true,riesame:true})}>
                                Tutti
                            </Button>
                            <Button size="sm" variant="ghost" className="text-xs"
                                onClick={() => setCompletoSel({dop:false,ce:false,piano:false,vt:false,registro:false,riesame:false})}>
                                Nessuno
                            </Button>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCompletoOpen(false)}>Annulla</Button>
                        <Button onClick={handleDownloadCompleto} disabled={completoLoading}>
                            {completoLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Download className="h-4 w-4 mr-1" />}
                            Scarica PDF
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Edit Dialog */}
            <Dialog open={editOpen} onOpenChange={setEditOpen}>
                <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="fascicolo-edit-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5" /> Compila — {editTitle}
                        </DialogTitle>
                        <DialogDescription>
                            I campi con bordo <span className="inline-block w-3 h-3 border-2 border-emerald-400 rounded align-middle mx-0.5" /> verde sono auto-compilati.
                            I campi con sfondo <span className="inline-block w-3 h-3 bg-amber-50 border border-amber-300 rounded align-middle mx-0.5" /> ambra richiedono compilazione.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">{renderEditContent()}</div>
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

// ─── Smart Field with auto/manual indicator ───
function SmartField({ label, value, onChange, placeholder, autoFields, fieldKey, className = '' }) {
    const isAuto = autoFields?.includes(fieldKey);
    const isEmpty = !value || !String(value).trim();
    const borderClass = isAuto ? 'border-emerald-300 focus-within:border-emerald-500' : isEmpty ? 'border-amber-300 bg-amber-50/50' : '';
    return (
        <div className={className}>
            <div className="flex items-center gap-1">
                <Label className="text-xs font-semibold text-slate-600">{label}</Label>
                {isAuto && <span className="text-[8px] bg-emerald-100 text-emerald-600 px-1 rounded font-bold">AUTO</span>}
                {!isAuto && isEmpty && <span className="text-[8px] bg-amber-100 text-amber-600 px-1 rounded font-bold">DA COMPILARE</span>}
            </div>
            <Input value={value || ''} onChange={e => onChange(e.target.value)}
                placeholder={placeholder} className={`h-8 text-sm mt-0.5 ${borderClass}`} />
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
                            checked={value === opt.value} onChange={() => onChange(opt.value)}
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

// ─── DOP Form ───
function DopEditForm({ form, update, autoFields }) {
    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Dichiarazione di Prestazione (Regolamento UE 574/2014)</p>
            <div className="grid grid-cols-2 gap-3">
                <SmartField label="DDT Riferimento" value={form.ddt_riferimento} onChange={v => update('ddt_riferimento', v)} placeholder="N. DDT" autoFields={autoFields} fieldKey="ddt_riferimento" />
                <SmartField label="Data DDT" value={form.ddt_data} onChange={v => update('ddt_data', v)} placeholder="GG/MM/AAAA" autoFields={autoFields} fieldKey="ddt_data" />
                <SmartField label="Mandatario" value={form.mandatario} onChange={v => update('mandatario', v)} autoFields={autoFields} fieldKey="mandatario" />
                <SmartField label="Firmatario" value={form.firmatario} onChange={v => update('firmatario', v)} placeholder="Nome e cognome" autoFields={autoFields} fieldKey="firmatario" />
                <SmartField label="Ruolo Firmatario" value={form.ruolo_firmatario} onChange={v => update('ruolo_firmatario', v)} placeholder="Legale Rappresentante" autoFields={autoFields} fieldKey="ruolo_firmatario" />
                <SmartField label="Luogo e Data Firma" value={form.luogo_data_firma} onChange={v => update('luogo_data_firma', v)} placeholder="Bologna, GG/MM/AAAA" autoFields={autoFields} fieldKey="luogo_data_firma" />
                <SmartField label="Certificato Numero" value={form.certificato_numero} onChange={v => update('certificato_numero', v)} autoFields={autoFields} fieldKey="certificato_numero" />
                <SmartField label="Ente Notificato" value={form.ente_notificato} onChange={v => update('ente_notificato', v)} placeholder="Rina Service" autoFields={autoFields} fieldKey="ente_notificato" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <SmartField label="Materiali / Saldabilita'" value={form.materiali_saldabilita} onChange={v => update('materiali_saldabilita', v)} autoFields={autoFields} fieldKey="materiali_saldabilita" />
                <SmartField label="Resilienza" value={form.resilienza} onChange={v => update('resilienza', v)} placeholder="27 Joule a +/- 20 C" autoFields={autoFields} fieldKey="resilienza" />
            </div>
            <SmartField label="Redatto da" value={form.redatto_da} onChange={v => update('redatto_da', v)} autoFields={autoFields} fieldKey="redatto_da" />
        </div>
    );
}

// ─── CE Form ───
function CeEditForm({ form, update, autoFields }) {
    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Etichetta Marcatura CE — EN 1090-1:2009 + A1:2011</p>
            <div className="grid grid-cols-2 gap-3">
                <SmartField label="Ente Notificato" value={form.ente_notificato} onChange={v => update('ente_notificato', v)} autoFields={autoFields} fieldKey="ente_notificato" />
                <SmartField label="Numero Ente" value={form.ente_numero} onChange={v => update('ente_numero', v)} placeholder="0474" autoFields={autoFields} fieldKey="ente_numero" />
                <SmartField label="Certificato N." value={form.certificato_numero} onChange={v => update('certificato_numero', v)} autoFields={autoFields} fieldKey="certificato_numero" />
                <SmartField label="DOP N." value={form.dop_numero} onChange={v => update('dop_numero', v)} autoFields={autoFields} fieldKey="dop_numero" />
                <SmartField label="Disegno Riferimento" value={form.disegno_riferimento} onChange={v => update('disegno_riferimento', v)} autoFields={autoFields} fieldKey="disegno_riferimento" />
                <SmartField label="Materiali" value={form.materiali_saldabilita} onChange={v => update('materiali_saldabilita', v)} autoFields={autoFields} fieldKey="materiali_saldabilita" />
                <SmartField label="Resilienza" value={form.resilienza} onChange={v => update('resilienza', v)} autoFields={autoFields} fieldKey="resilienza" />
            </div>
        </div>
    );
}

// ─── Piano di Controllo Form with Timeline ───
function PianoEditForm({ form, update, autoFields, timeline }) {
    const [regInstruments, setRegInstruments] = useState([]);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${API}/api/smart-assign/instruments`, { credentials: 'include' });
                if (res.ok) { const d = await res.json(); setRegInstruments(d.instruments || []); }
            } catch { /* silent */ }
        })();
    }, []);

    const fasi = form.fasi || [];
    const toggleApplicabile = (idx) => {
        const n = [...fasi]; n[idx] = { ...n[idx], applicabile: !n[idx].applicabile }; update('fasi', n);
    };
    const updateFase = (idx, key, val) => {
        const n = [...fasi]; n[idx] = { ...n[idx], [key]: val }; update('fasi', n);
    };
    const handleSelectInstrument = (idx, instrumentId) => {
        if (!instrumentId) { updateFase(idx, 'strumento_usato', ''); return; }
        const inst = regInstruments.find(x => x.instrument_id === instrumentId);
        if (inst) {
            updateFase(idx, 'strumento_usato', `${inst.name} (S/N: ${inst.serial_number})`);
            updateFase(idx, '_instrument_status', inst.calibration_status);
        }
    };

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Piano di Controllo Qualita' — MOD. 02</p>
            <div className="grid grid-cols-2 gap-3">
                <SmartField label="Disegno N." value={form.disegno_numero} onChange={v => update('disegno_numero', v)} autoFields={autoFields} fieldKey="disegno_numero" />
                <SmartField label="Ordine N." value={form.ordine_numero} onChange={v => update('ordine_numero', v)} autoFields={autoFields} fieldKey="ordine_numero" />
            </div>
            {/* Mini timeline from produzione */}
            {timeline.length > 0 && (
                <div className="p-2 bg-blue-50 rounded border border-blue-200">
                    <p className="text-[10px] font-bold text-blue-700 mb-1.5">Stato Produzione (date auto-sincronizzate)</p>
                    <div className="flex gap-1">
                        {timeline.map((t, i) => {
                            const bg = t.stato === 'completato' ? 'bg-emerald-500' : t.stato === 'in_corso' ? 'bg-blue-500 animate-pulse' : 'bg-slate-300';
                            return (
                                <div key={i} className="flex-1 text-center">
                                    <div className={`h-1.5 rounded-full ${bg}`} />
                                    <span className="text-[7px] text-slate-600 block truncate">{t.fase}</span>
                                    {t.data_inizio && <span className="text-[7px] text-blue-600 block">{new Date(t.data_inizio).toLocaleDateString('it-IT')}</span>}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
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
                                        <option value="">--</option><option value="positivo">Pos.</option><option value="negativo">Neg.</option>
                                    </select>
                                    <input value={f.data_effettiva || ''} onChange={e => updateFase(i, 'data_effettiva', e.target.value)}
                                        placeholder="Data" className={`h-6 text-[10px] rounded border px-1 w-20 ${f.data_effettiva ? 'border-emerald-300' : 'border-amber-300 bg-amber-50/50'}`} />
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Rapporto VT Form ───
function VtEditForm({ form, update, autoFields }) {
    const updateCheckGroup = (group, key, val) => {
        update(group, { ...(form[group] || {}), [key]: val });
    };
    const oggetti = form.oggetti_controllati || [];
    const addOggetto = () => update('oggetti_controllati', [...oggetti, { numero:'',disegno:'',marca:'',dimensioni:'',estensione_controllo:'100',esito:'' }]);
    const updateOggetto = (idx, key, val) => { const n=[...oggetti]; n[idx]={...n[idx],[key]:val}; update('oggetti_controllati',n); };
    const removeOggetto = (idx) => { const n=[...oggetti]; n.splice(idx,1); update('oggetti_controllati',n); };

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Rapporto di Esame Visivo Dimensionale — MOD. 06</p>
            <div className="grid grid-cols-2 gap-3">
                <SmartField label="Report N." value={form.report_numero} onChange={v => update('report_numero', v)} autoFields={autoFields} fieldKey="report_numero" />
                <SmartField label="Data Report" value={form.report_data} onChange={v => update('report_data', v)} placeholder="GG/MM/AAAA" autoFields={autoFields} fieldKey="report_data" />
                <SmartField label="Processo Saldatura" value={form.processo_saldatura} onChange={v => update('processo_saldatura', v)} autoFields={autoFields} fieldKey="processo_saldatura" />
                <SmartField label="Norma/Procedura" value={form.norma_procedura} onChange={v => update('norma_procedura', v)} autoFields={autoFields} fieldKey="norma_procedura" />
                <SmartField label="Accettabilita'" value={form.accettabilita} onChange={v => update('accettabilita', v)} autoFields={autoFields} fieldKey="accettabilita" />
                <SmartField label="Materiale" value={form.materiale} onChange={v => update('materiale', v)} autoFields={autoFields} fieldKey="materiale" />
                <SmartField label="Profilato" value={form.profilato} onChange={v => update('profilato', v)} autoFields={autoFields} fieldKey="profilato" />
                <SmartField label="Spessore" value={form.spessore} onChange={v => update('spessore', v)} autoFields={autoFields} fieldKey="spessore" />
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Condizioni di visione</Label>
                <div className="flex gap-4 flex-wrap">
                    {['naturale','artificiale','lampada_wood'].map(k => (
                        <CheckField key={k} label={k.replace(/_/g,' ')} checked={form.condizioni_visione?.[k]} onChange={v => updateCheckGroup('condizioni_visione',k,v)} />
                    ))}
                </div>
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Stato superficie</Label>
                <div className="flex gap-4 flex-wrap">
                    {['come_saldato','molato','spazzolato','lavorato_macchina','come_laminato','verniciato'].map(k => (
                        <CheckField key={k} label={k.replace(/_/g,' ')} checked={form.stato_superficie?.[k]} onChange={v => updateCheckGroup('stato_superficie',k,v)} />
                    ))}
                </div>
            </div>
            <div className="space-y-2">
                <Label className="text-xs font-semibold text-slate-600">Tipo ispezione</Label>
                <div className="flex gap-4 flex-wrap">
                    {['diretto','remoto','generale','locale'].map(k => (
                        <CheckField key={k} label={k} checked={form.tipo_ispezione?.[k]} onChange={v => updateCheckGroup('tipo_ispezione',k,v)} />
                    ))}
                </div>
            </div>
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700">Oggetti Controllati</span>
                    <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={addOggetto}><Plus className="h-3 w-3 mr-1" /> Aggiungi</Button>
                </div>
                {oggetti.map((o,i) => (
                    <div key={i} className="flex gap-1 px-2 py-1 border-b items-center">
                        <input value={o.numero} onChange={e => updateOggetto(i,'numero',e.target.value)} placeholder="N." className="h-6 text-[10px] border rounded px-1 w-8" />
                        <input value={o.disegno} onChange={e => updateOggetto(i,'disegno',e.target.value)} placeholder="Disegno" className="h-6 text-[10px] border rounded px-1 w-16" />
                        <input value={o.marca} onChange={e => updateOggetto(i,'marca',e.target.value)} placeholder="Marca" className="h-6 text-[10px] border rounded px-1 w-16" />
                        <input value={o.dimensioni} onChange={e => updateOggetto(i,'dimensioni',e.target.value)} placeholder="Dim." className="h-6 text-[10px] border rounded px-1 w-20" />
                        <input value={o.estensione_controllo} onChange={e => updateOggetto(i,'estensione_controllo',e.target.value)} placeholder="%" className="h-6 text-[10px] border rounded px-1 w-10" />
                        <select value={o.esito} onChange={e => updateOggetto(i,'esito',e.target.value)} className="h-6 text-[10px] border rounded px-1 w-18">
                            <option value="">--</option><option value="Positivo">Pos.</option><option value="Negativo">Neg.</option>
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

// ─── Registro Saldatura Form ───
function RegistroEditForm({ form, update, autoFields, addSaldatura, updateSaldatura, removeSaldatura }) {
    const [regWelders, setRegWelders] = useState([]);
    const [loadingWelders, setLoadingWelders] = useState(false);
    const [selectedWelderInfo, setSelectedWelderInfo] = useState(null);

    useEffect(() => {
        (async () => {
            setLoadingWelders(true);
            try {
                const res = await fetch(`${API}/api/smart-assign/welders`, { credentials: 'include' });
                if (res.ok) { const d = await res.json(); setRegWelders(d.welders || []); }
            } catch { /* silent */ }
            finally { setLoadingWelders(false); }
        })();
    }, []);

    const handleImportWelder = (welderId) => {
        if (!welderId) { setSelectedWelderInfo(null); return; }
        const w = regWelders.find(x => x.welder_id === welderId);
        if (!w) return;
        setSelectedWelderInfo(w);
    };

    const addFromRegistry = () => {
        if (!selectedWelderInfo) { addSaldatura(); return; }
        const w = selectedWelderInfo;
        const bestQual = w.qualifications?.find(q => q.status === 'attivo') || w.qualifications?.[0];
        const saldature = form.saldature || [];
        const newRow = {
            numero_disegno: '', numero_saldatura: '', periodo: '',
            saldatore: w.name, punzone: w.stamp_id,
            diametro: '', spessore: '', materiale_base: '',
            wps_numero: bestQual?.process || '',
            vt_esito: '', vt_data: '', vt_firma: '',
            cnd_tipo: '', cnd_rapporto: '', cnd_data: '', cnd_firma: '',
            cnd_tratto: '', rip_rapporto: '', rip_esito: '', rip_data: '',
            _source_welder_id: w.welder_id,
        };
        update('saldature', [...saldature, newRow]);
    };

    const saldature = form.saldature || [];
    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Registro di Saldatura — MOD. 04</p>

            {/* ── Smart Assign: Importa Saldatore ── */}
            <div className="border border-blue-200 bg-blue-50/40 rounded-lg p-3 space-y-2" data-testid="smart-assign-welders">
                <div className="flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5 text-blue-600" />
                    <span className="text-xs font-bold text-blue-800">Importa da Registro Saldatori</span>
                </div>
                <div className="flex items-center gap-2">
                    <select
                        data-testid="select-import-welder"
                        className="flex-1 h-8 text-sm rounded-md border border-input bg-background px-2 focus:outline-none focus:ring-2 focus:ring-ring"
                        onChange={e => handleImportWelder(e.target.value)}
                        defaultValue=""
                    >
                        <option value="">-- Seleziona saldatore dal registro --</option>
                        {loadingWelders && <option disabled>Caricamento...</option>}
                        {regWelders.map(w => {
                            const status = w.overall_status === 'ok' ? '  OK' : w.overall_status === 'warning' ? '  ATT.' : w.overall_status === 'expired' ? '  SCADUTO' : '  N/Q';
                            return (
                                <option key={w.welder_id} value={w.welder_id}>
                                    {w.name} ({w.stamp_id}) —{status}
                                </option>
                            );
                        })}
                    </select>
                    <Button size="sm" className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white" data-testid="btn-add-from-registry" onClick={addFromRegistry}>
                        <Plus className="h-3 w-3 mr-1" /> Aggiungi Riga
                    </Button>
                </div>
                {selectedWelderInfo && (
                    <div className={`flex items-center gap-2 text-xs p-1.5 rounded ${
                        selectedWelderInfo.overall_status === 'ok' ? 'bg-emerald-50 text-emerald-700' :
                        selectedWelderInfo.overall_status === 'expired' ? 'bg-red-50 text-red-700' :
                        'bg-amber-50 text-amber-700'
                    }`} data-testid="welder-status-alert">
                        {selectedWelderInfo.overall_status === 'ok' && <><CheckCircle2 className="h-3.5 w-3.5" /> Tutti i patentini validi</>}
                        {selectedWelderInfo.overall_status === 'expired' && <><AlertTriangle className="h-3.5 w-3.5" /> ATTENZIONE: Tutti i patentini scaduti!</>}
                        {selectedWelderInfo.overall_status === 'warning' && <><AlertTriangle className="h-3.5 w-3.5" /> Attenzione: Alcuni patentini in scadenza/scaduti</>}
                        {selectedWelderInfo.overall_status === 'no_qual' && <><AlertCircle className="h-3.5 w-3.5" /> Nessun patentino registrato</>}
                        {selectedWelderInfo.qualifications?.length > 0 && (
                            <span className="ml-auto text-[10px]">
                                {selectedWelderInfo.qualifications.filter(q => q.status === 'attivo').length}/{selectedWelderInfo.qualifications.length} validi
                            </span>
                        )}
                    </div>
                )}
                {selectedWelderInfo?.qualifications?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {selectedWelderInfo.qualifications.map(q => (
                            <Badge key={q.qual_id} className={`text-[9px] border ${
                                q.status === 'attivo' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
                                q.status === 'in_scadenza' ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                'bg-red-100 text-red-700 border-red-200'
                            }`}>
                                {q.standard} {q.process} — Scad. {new Date(q.expiry_date).toLocaleDateString('it-IT')}
                            </Badge>
                        ))}
                    </div>
                )}
            </div>

            <div className="grid grid-cols-3 gap-3">
                <SmartField label="Data Emissione" value={form.data_emissione} onChange={v => update('data_emissione', v)} placeholder="GG/MM/AAAA" autoFields={autoFields} fieldKey="data_emissione" />
                <SmartField label="Firma CS" value={form.firma_cs} onChange={v => update('firma_cs', v)} autoFields={autoFields} fieldKey="firma_cs" />
                <div />
                <SmartField label="% VT" value={form.perc_vt} onChange={v => update('perc_vt', v)} placeholder="100" autoFields={autoFields} fieldKey="perc_vt" />
                <SmartField label="% MT/PT" value={form.perc_mt_pt} onChange={v => update('perc_mt_pt', v)} placeholder="0" autoFields={autoFields} fieldKey="perc_mt_pt" />
                <SmartField label="% RX-RY/UT" value={form.perc_rx_ut} onChange={v => update('perc_rx_ut', v)} placeholder="0" autoFields={autoFields} fieldKey="perc_rx_ut" />
            </div>
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700">Saldature Registrate</span>
                    <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={addSaldatura} data-testid="btn-add-saldatura">
                        <Plus className="h-3 w-3 mr-1" /> Riga Manuale
                    </Button>
                </div>
                <div className="max-h-64 overflow-y-auto">
                    {saldature.length === 0 && (
                        <p className="text-center text-xs text-slate-400 py-4">Nessuna saldatura. Usa "Importa da Registro" o aggiungi righe manuali.</p>
                    )}
                    {saldature.map((s, i) => (
                        <div key={i} className="p-2 border-b space-y-1">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-[10px] font-bold text-slate-500">#{i + 1}</span>
                                    {s._source_welder_id && (
                                        <Badge className="bg-blue-50 text-blue-600 border-blue-200 border text-[8px]">Da Registro</Badge>
                                    )}
                                </div>
                                <button onClick={() => removeSaldatura(i)} className="text-red-400 hover:text-red-600"><Trash2 className="h-3 w-3" /></button>
                            </div>
                            <div className="grid grid-cols-4 gap-1">
                                {[['numero_disegno','N.Dis.'],['numero_saldatura','N.Sald.'],['periodo','Periodo'],['saldatore','Saldatore'],
                                  ['punzone','Punz.'],['diametro','Diam.'],['spessore','Spess.'],['materiale_base','Mat.Base'],
                                  ['wps_numero','WPS'],['vt_esito','VT Esito'],['vt_data','VT Data'],['vt_firma','VT Firma']
                                ].map(([key,ph]) => (
                                    <input key={key} value={s[key]||''} onChange={e => updateSaldatura(i,key,e.target.value)}
                                        placeholder={ph} className={`h-6 text-[10px] border rounded px-1 ${s._source_welder_id && (key === 'saldatore' || key === 'punzone') ? 'border-blue-300 bg-blue-50/30' : ''}`} />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Riesame Tecnico Form ───
function RiesameEditForm({ form, update, autoFields, updateRequisito, updateItt }) {
    const requisiti = form.requisiti || [];
    const itt = form.itt || [];

    return (
        <div className="space-y-3">
            <p className="text-xs text-slate-500 italic">Riesame Tecnico — MOD. 01 — Checklist requisiti EN 1090</p>
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">Requisiti ({requisiti.filter(r=>r.risposta==='si').length}/{requisiti.length} confermati)</div>
                <div className="max-h-64 overflow-y-auto">
                    {requisiti.map((r, i) => (
                        <div key={i} className="flex items-start gap-2 px-2 py-1.5 border-b text-[10px]">
                            <span className="flex-1 min-w-0 pt-0.5">{r.requisito}</span>
                            <div className="flex gap-1.5 shrink-0 items-center">
                                {['si','no','na'].map(opt => (
                                    <label key={opt} className="flex items-center gap-0.5 cursor-pointer">
                                        <input type="radio" name={`req-${i}`} value={opt}
                                            checked={r.risposta===opt} onChange={() => updateRequisito(i,'risposta',opt)}
                                            className="accent-slate-800" style={{width:12,height:12}} />
                                        <span className="uppercase">{opt}</span>
                                    </label>
                                ))}
                            </div>
                            <input value={r.note||''} onChange={e => updateRequisito(i,'note',e.target.value)}
                                placeholder="Note" className="h-5 text-[10px] border rounded px-1 w-32" />
                        </div>
                    ))}
                </div>
            </div>
            <RadioGroup label="Decisione Fattibilita'" value={form.decisione||'procedere'} onChange={v => update('decisione',v)}
                options={[{value:'procedere',label:'PROCEDERE'},{value:'non_procedere',label:'NON PROCEDERE'}]} />
            <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">ITT di Commessa</div>
                <div className="max-h-48 overflow-y-auto">
                    {itt.map((item, i) => (
                        <div key={i} className="flex items-center gap-1 px-2 py-1 border-b text-[10px]">
                            <span className="flex-1 min-w-0 truncate" title={item.caratteristica}>{item.caratteristica}</span>
                            <input value={item.esito_conformita||''} onChange={e => updateItt(i,'esito_conformita',e.target.value)}
                                placeholder="Esito" className="h-5 text-[10px] border rounded px-1 w-28" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
