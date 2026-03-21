/**
 * WeldersPage — Registro Saldatori & Patentini
 * Gestione personale qualificato con scadenze patentini ISO 9606.
 * Layout master-detail: lista saldatori (sidebar) + scheda dettaglio con qualifiche.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest, API_BASE } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import {
    Plus, Search, UserCheck, UserX, Users, Loader2, Trash2, Pencil,
    AlertTriangle, CheckCircle2, Clock, Shield, Download, Upload,
    X, File, ChevronRight,
} from 'lucide-react';

/* ── Constants ── */
const OVERALL_STATUS = {
    ok: { label: 'Qualificato', color: 'bg-emerald-500', badge: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
    warning: { label: 'Attenzione', color: 'bg-amber-500', badge: 'bg-amber-100 text-amber-800', icon: Clock },
    expired: { label: 'Scaduto', color: 'bg-red-500', badge: 'bg-red-100 text-red-800', icon: AlertTriangle },
    no_qual: { label: 'Nessun Patentino', color: 'bg-slate-400', badge: 'bg-slate-100 text-slate-600', icon: Shield },
};

const QUAL_STATUS = {
    attivo: { label: 'Attivo', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
    in_scadenza: { label: 'In Scadenza', color: 'bg-amber-100 text-amber-800 border-amber-200' },
    scaduto: { label: 'Scaduto', color: 'bg-red-100 text-red-800 border-red-200' },
};

const EMPTY_WELDER = { name: '', stamp_id: '', role: 'operaio', phone: '', email: '', hire_date: '', notes: '' };
const EMPTY_QUAL = { standard: '', process: '', material_group: '', thickness_range: '', position: '', issue_date: '', expiry_date: '', notes: '', cert_code: '' };

const CERT_PRESETS = [
    { code: 'patentino_saldatura', standard: 'ISO 9606-1', label: 'Patentino Saldatura', showProcess: true },
    { code: 'formazione_base_8108', standard: 'Formazione Base 81/08', label: 'Formazione Base 81/08' },
    { code: 'formazione_specifica', standard: 'Form. Specifica Rischio Alto', label: 'Formazione Specifica Rischio Alto' },
    { code: 'primo_soccorso', standard: 'Primo Soccorso', label: 'Primo Soccorso' },
    { code: 'antincendio', standard: 'Antincendio', label: 'Antincendio' },
    { code: 'lavori_quota', standard: 'Lavori in Quota', label: 'Lavori in Quota' },
    { code: 'ple', standard: 'PLE (Piattaforme)', label: 'PLE (Piattaforme Elevabili)' },
    { code: 'idoneita_sanitaria', standard: 'Idoneita Sanitaria', label: 'Idoneita Sanitaria (Visita Medica)' },
];

function fmtDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

/* ═══════════════════════════════════════════════════════ */

export default function WeldersPage() {
    const navigate = useNavigate();
    const [welders, setWelders] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');
    const [selected, setSelected] = useState(null);

    // Dialogs
    const [showWelderForm, setShowWelderForm] = useState(false);
    const [editWelder, setEditWelder] = useState(null);
    const [welderForm, setWelderForm] = useState({ ...EMPTY_WELDER });
    const [savingWelder, setSavingWelder] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [showQualForm, setShowQualForm] = useState(false);
    const [qualForm, setQualForm] = useState({ ...EMPTY_QUAL });
    const [qualFile, setQualFile] = useState(null);
    const [savingQual, setSavingQual] = useState(false);
    const [deleteQual, setDeleteQual] = useState(null);
    const [deletingQual, setDeletingQual] = useState(false);

    /* ── Fetch ── */
    const fetchWelders = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (searchQ.trim()) params.set('search', searchQ.trim());
            const qs = params.toString();
            const res = await apiRequest(`/welders/${qs ? `?${qs}` : ''}`);
            setWelders(res.items || []);
            setStats(res.stats || {});
            // Refresh selected welder if present
            if (selected) {
                const updated = (res.items || []).find(w => w.welder_id === selected.welder_id);
                if (updated) setSelected(updated);
                else setSelected(null);
            }
        } catch {
            toast.error('Errore caricamento saldatori');
        } finally {
            setLoading(false);
        }
    }, [searchQ]);

    useEffect(() => {
        const timer = setTimeout(fetchWelders, 300);
        return () => clearTimeout(timer);
    }, [fetchWelders]);

    /* ── Welder CRUD ── */
    const handleSaveWelder = async () => {
        if (!welderForm.name.trim()) { toast.error('Inserisci il nome'); return; }
        if (!welderForm.stamp_id.trim()) { toast.error('Inserisci il punzone'); return; }
        setSavingWelder(true);
        try {
            if (editWelder) {
                const res = await apiRequest(`/welders/${editWelder.welder_id}`, { method: 'PUT', body: welderForm });
                toast.success('Saldatore aggiornato');
                setSelected(res);
            } else {
                const res = await apiRequest('/welders/', { method: 'POST', body: welderForm });
                toast.success('Saldatore creato');
                setSelected(res);
            }
            closeWelderForm();
            fetchWelders();
        } catch (e) {
            toast.error(e.message || 'Errore');
        } finally {
            setSavingWelder(false);
        }
    };

    const handleDeleteWelder = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        try {
            await apiRequest(`/welders/${deleteTarget.welder_id}`, { method: 'DELETE' });
            toast.success('Saldatore eliminato');
            if (selected?.welder_id === deleteTarget.welder_id) setSelected(null);
            setDeleteTarget(null);
            fetchWelders();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setDeleting(false);
        }
    };

    const openEditWelder = (w) => {
        setEditWelder(w);
        setWelderForm({ name: w.name, stamp_id: w.stamp_id, role: w.role || 'saldatore', phone: w.phone || '', email: w.email || '', hire_date: w.hire_date || '', notes: w.notes || '' });
        setShowWelderForm(true);
    };

    const closeWelderForm = () => { setShowWelderForm(false); setEditWelder(null); setWelderForm({ ...EMPTY_WELDER }); };

    /* ── Qualification CRUD ── */
    const handleSaveQual = async () => {
        if (!qualForm.expiry_date) { toast.error('Inserisci la data di scadenza'); return; }
        if (!qualForm.cert_code && !qualForm.standard) { toast.error('Seleziona il tipo di attestato'); return; }
        if (!selected) return;
        setSavingQual(true);
        try {
            const fd = new FormData();
            fd.append('standard', qualForm.standard || qualForm.cert_code);
            fd.append('process', qualForm.process);
            fd.append('material_group', qualForm.material_group);
            fd.append('thickness_range', qualForm.thickness_range);
            fd.append('position', qualForm.position);
            fd.append('issue_date', qualForm.issue_date);
            fd.append('expiry_date', qualForm.expiry_date);
            fd.append('notes', qualForm.notes);
            fd.append('cert_code', qualForm.cert_code);
            if (qualFile) fd.append('file', qualFile);

            const res = await fetch(`${API_BASE}/welders/${selected.welder_id}/qualifications`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Errore'); }
            const data = await res.json();
            toast.success('Patentino aggiunto');
            setSelected(data);
            setShowQualForm(false);
            setQualForm({ ...EMPTY_QUAL });
            setQualFile(null);
            fetchWelders();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSavingQual(false);
        }
    };

    const handleDeleteQual = async () => {
        if (!deleteQual || !selected) return;
        setDeletingQual(true);
        try {
            await apiRequest(`/welders/${selected.welder_id}/qualifications/${deleteQual.qual_id}`, { method: 'DELETE' });
            toast.success('Patentino eliminato');
            setDeleteQual(null);
            fetchWelders();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setDeletingQual(false);
        }
    };

    const handleDownloadQual = async (qual) => {
        try {
            const res = await fetch(`${API_BASE}/welders/${selected.welder_id}/qualifications/${qual.qual_id}/download`, { credentials: 'include' });
            if (!res.ok) throw new Error('Errore download');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = qual.filename || 'patentino.pdf'; a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    /* ═══════════════════════════════ RENDER ═══════════════════════════════ */
    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="welders-page">
                {/* ── Header ── */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">Risorse Umane</h1>
                        <p className="text-slate-600">Anagrafica operai, patentini, attestati sicurezza 81/08</p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => navigate('/operai/matrice')} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50" data-testid="btn-matrice">
                            <Shield className="h-4 w-4 mr-2" /> Matrice Scadenze
                        </Button>
                        <Button data-testid="btn-add-welder" onClick={() => setShowWelderForm(true)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Plus className="h-4 w-4 mr-2" /> Nuovo Operaio
                        </Button>
                    </div>
                </div>

                {/* ── Stats ── */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="stats-bar">
                    <StatCard label="Operai" value={stats.total || 0} icon={Users} color="text-slate-700" bg="bg-slate-50" />
                    <StatCard label="Qualificati" value={stats.ok || 0} icon={CheckCircle2} color="text-emerald-700" bg="bg-emerald-50" />
                    <StatCard label="Attenzione" value={(stats.warning || 0) + (stats.expired || 0)} icon={AlertTriangle} color="text-amber-700" bg="bg-amber-50" />
                    <StatCard label="Patentini Tot." value={stats.total_qualifications || 0} icon={Shield} color="text-blue-700" bg="bg-blue-50" />
                </div>

                {/* ── Master-Detail Layout ── */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    {/* Sidebar: welder list */}
                    <div className="lg:col-span-4 xl:col-span-3">
                        <Card className="border-gray-200">
                            <CardContent className="p-3">
                                <div className="relative mb-3">
                                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                                    <Input data-testid="search-welders" placeholder="Cerca saldatore..." value={searchQ} onChange={e => setSearchQ(e.target.value)} className="pl-8 h-8 text-sm" />
                                </div>
                                {loading ? (
                                    <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-slate-400" /></div>
                                ) : welders.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-6">Nessun saldatore</p>
                                ) : (
                                    <div className="space-y-1 max-h-[500px] overflow-y-auto" data-testid="welder-list">
                                        {welders.map(w => {
                                            const st = OVERALL_STATUS[w.overall_status] || OVERALL_STATUS.no_qual;
                                            const isSelected = selected?.welder_id === w.welder_id;
                                            return (
                                                <button
                                                    key={w.welder_id}
                                                    data-testid={`welder-item-${w.welder_id}`}
                                                    onClick={() => setSelected(w)}
                                                    className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-2.5 transition-colors ${
                                                        isSelected ? 'bg-[#0055FF]/10 border border-[#0055FF]/20' : 'hover:bg-slate-50 border border-transparent'
                                                    }`}
                                                >
                                                    <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${st.color}`} />
                                                    <div className="min-w-0 flex-1">
                                                        <p className={`text-sm font-medium truncate ${isSelected ? 'text-[#0055FF]' : 'text-slate-900'}`}>{w.name}</p>
                                                        <p className="text-[10px] text-slate-400 font-mono">{w.stamp_id} - {w.active_quals + w.expiring_quals + w.expired_quals} patentin{(w.active_quals + w.expiring_quals + w.expired_quals) !== 1 ? 'i' : 'o'}</p>
                                                    </div>
                                                    <ChevronRight className={`h-3.5 w-3.5 flex-shrink-0 ${isSelected ? 'text-[#0055FF]' : 'text-slate-300'}`} />
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Detail Panel */}
                    <div className="lg:col-span-8 xl:col-span-9">
                        {selected ? (
                            <WelderDetail
                                welder={selected}
                                onEdit={() => openEditWelder(selected)}
                                onDelete={() => setDeleteTarget(selected)}
                                onAddQual={() => { setQualForm({ ...EMPTY_QUAL }); setQualFile(null); setShowQualForm(true); }}
                                onDeleteQual={setDeleteQual}
                                onDownloadQual={handleDownloadQual}
                            />
                        ) : (
                            <Card className="border-gray-200">
                                <CardContent className="py-20 text-center">
                                    <Users className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                                    <p className="text-sm text-slate-500 font-medium">Seleziona un saldatore dalla lista</p>
                                    <p className="text-xs text-slate-400 mt-1">oppure creane uno nuovo</p>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>

            {/* ══════ Welder Form Dialog ══════ */}
            <Dialog open={showWelderForm} onOpenChange={v => { if (!v) closeWelderForm(); else setShowWelderForm(true); }}>
                <DialogContent className="max-w-md" data-testid="welder-form-dialog">
                    <DialogHeader>
                        <DialogTitle>{editWelder ? 'Modifica Operaio' : 'Nuovo Operaio'}</DialogTitle>
                        <DialogDescription>Inserisci i dati anagrafici.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 mt-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Nome Completo *</Label>
                                <Input data-testid="input-welder-name" value={welderForm.name} onChange={e => setWelderForm(f => ({ ...f, name: e.target.value }))} placeholder="Mario Rossi" className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Punzone (ID) *</Label>
                                <Input data-testid="input-welder-stamp" value={welderForm.stamp_id} onChange={e => setWelderForm(f => ({ ...f, stamp_id: e.target.value }))} placeholder="MR01" className="mt-1 font-mono" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Ruolo</Label>
                                <Select value={welderForm.role} onValueChange={v => setWelderForm(f => ({ ...f, role: v }))}>
                                    <SelectTrigger data-testid="select-welder-role" className="mt-1"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="operaio">Operaio</SelectItem>
                                        <SelectItem value="saldatore">Saldatore</SelectItem>
                                        <SelectItem value="capo_saldatore">Capo Saldatore</SelectItem>
                                        <SelectItem value="montatore">Montatore</SelectItem>
                                        <SelectItem value="carpentiere">Carpentiere</SelectItem>
                                        <SelectItem value="verniciatore">Verniciatore</SelectItem>
                                        <SelectItem value="capo_squadra">Capo Squadra</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Data Assunzione</Label>
                                <Input data-testid="input-welder-hire" type="date" value={welderForm.hire_date} onChange={e => setWelderForm(f => ({ ...f, hire_date: e.target.value }))} className="mt-1" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Telefono</Label>
                                <Input data-testid="input-welder-phone" value={welderForm.phone} onChange={e => setWelderForm(f => ({ ...f, phone: e.target.value }))} placeholder="+39..." className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Email</Label>
                                <Input data-testid="input-welder-email" value={welderForm.email} onChange={e => setWelderForm(f => ({ ...f, email: e.target.value }))} placeholder="mario@azienda.it" className="mt-1" />
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Note</Label>
                            <Input data-testid="input-welder-notes" value={welderForm.notes} onChange={e => setWelderForm(f => ({ ...f, notes: e.target.value }))} placeholder="Note aggiuntive" className="mt-1" />
                        </div>
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={closeWelderForm}>Annulla</Button>
                        <Button data-testid="btn-save-welder" onClick={handleSaveWelder} disabled={savingWelder} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {savingWelder && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            {editWelder ? 'Salva' : 'Crea'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Qualification Form Dialog ══════ */}
            <Dialog open={showQualForm} onOpenChange={v => { if (!v) { setShowQualForm(false); setQualFile(null); } }}>
                <DialogContent className="max-w-lg" data-testid="qual-form-dialog">
                    <DialogHeader>
                        <DialogTitle>Nuovo Attestato / Patentino</DialogTitle>
                        <DialogDescription>Aggiungi certificazione per {selected?.name}.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 mt-2">
                        {/* Quick select cert type */}
                        <div>
                            <Label className="text-xs font-medium">Tipo Attestato</Label>
                            <select
                                data-testid="select-cert-type"
                                value={qualForm.cert_code}
                                onChange={e => {
                                    const preset = CERT_PRESETS.find(p => p.code === e.target.value);
                                    if (preset) {
                                        setQualForm(f => ({
                                            ...f,
                                            cert_code: preset.code,
                                            standard: preset.standard,
                                        }));
                                    } else {
                                        setQualForm(f => ({ ...f, cert_code: e.target.value }));
                                    }
                                }}
                                className="w-full border rounded px-3 py-2 text-sm mt-1 bg-white"
                            >
                                <option value="">-- Seleziona tipo --</option>
                                {CERT_PRESETS.map(p => (
                                    <option key={p.code} value={p.code}>{p.label}</option>
                                ))}
                                <option value="altro">Altro (personalizzato)</option>
                            </select>
                        </div>

                        {/* Standard & Process — show when patentino_saldatura or custom */}
                        {(qualForm.cert_code === 'patentino_saldatura' || qualForm.cert_code === 'altro' || !qualForm.cert_code) && (
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Label className="text-xs font-medium">Norma di Riferimento</Label>
                                    <Select value={qualForm.standard || '__custom__'} onValueChange={v => setQualForm(f => ({ ...f, standard: v === '__custom__' ? '' : v }))}>
                                        <SelectTrigger data-testid="select-qual-standard" className="mt-1"><SelectValue placeholder="Seleziona" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="ISO 9606-1">ISO 9606-1 (Acciaio)</SelectItem>
                                            <SelectItem value="ISO 9606-2">ISO 9606-2 (Alluminio)</SelectItem>
                                            <SelectItem value="ISO 14732">ISO 14732 (Operatore)</SelectItem>
                                            <SelectItem value="EN 287-1">EN 287-1 (Legacy)</SelectItem>
                                            <SelectItem value="__custom__">Altro</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs font-medium">Processo</Label>
                                    <Select value={qualForm.process || '__none__'} onValueChange={v => setQualForm(f => ({ ...f, process: v === '__none__' ? '' : v }))}>
                                        <SelectTrigger data-testid="select-qual-process" className="mt-1"><SelectValue placeholder="Seleziona" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">--</SelectItem>
                                            <SelectItem value="111 (SMAW)">111 - SMAW (Elettrodo)</SelectItem>
                                            <SelectItem value="135 (MAG)">135 - MAG</SelectItem>
                                            <SelectItem value="136 (FCAW)">136 - FCAW (Filo animato)</SelectItem>
                                            <SelectItem value="138 (MAG-MC)">138 - MAG Metal Core</SelectItem>
                                            <SelectItem value="141 (TIG)">141 - TIG</SelectItem>
                                            <SelectItem value="121 (SAW)">121 - SAW (Arco sommerso)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        )}

                        {/* Welding specific fields */}
                        {qualForm.cert_code === 'patentino_saldatura' && (
                            <div className="grid grid-cols-3 gap-3">
                                <div>
                                    <Label className="text-xs font-medium">Gruppo Materiale</Label>
                                    <Input data-testid="input-qual-material" value={qualForm.material_group} onChange={e => setQualForm(f => ({ ...f, material_group: e.target.value }))} placeholder="es. FM1" className="mt-1" />
                                </div>
                                <div>
                                    <Label className="text-xs font-medium">Spessori</Label>
                                    <Input data-testid="input-qual-thickness" value={qualForm.thickness_range} onChange={e => setQualForm(f => ({ ...f, thickness_range: e.target.value }))} placeholder="es. 3-30mm" className="mt-1" />
                                </div>
                                <div>
                                    <Label className="text-xs font-medium">Posizione</Label>
                                    <Input data-testid="input-qual-position" value={qualForm.position} onChange={e => setQualForm(f => ({ ...f, position: e.target.value }))} placeholder="es. PA, PB" className="mt-1" />
                                </div>
                            </div>
                        )}

                        {/* Custom standard name */}
                        {qualForm.cert_code === 'altro' && (
                            <div>
                                <Label className="text-xs font-medium">Nome Attestato</Label>
                                <Input value={qualForm.standard} onChange={e => setQualForm(f => ({ ...f, standard: e.target.value }))} placeholder="es. Corso carrellisti, BLSD..." className="mt-1" />
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Data Rilascio</Label>
                                <Input data-testid="input-qual-issue" type="date" value={qualForm.issue_date} onChange={e => setQualForm(f => ({ ...f, issue_date: e.target.value }))} className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Data di Scadenza *</Label>
                                <Input data-testid="input-qual-expiry" type="date" value={qualForm.expiry_date} onChange={e => setQualForm(f => ({ ...f, expiry_date: e.target.value }))} className="mt-1" />
                            </div>
                        </div>

                        {/* File upload */}
                        <div>
                            <Label className="text-xs font-medium">PDF Attestato</Label>
                            <div
                                className={`mt-1 border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${qualFile ? 'border-[#0055FF] bg-blue-50/40' : 'border-slate-200 hover:border-slate-300'}`}
                                onClick={() => document.getElementById('qual-file-input')?.click()}
                                data-testid="qual-drop-zone"
                            >
                                <input id="qual-file-input" type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" onChange={e => { if (e.target.files?.[0]) setQualFile(e.target.files[0]); }} />
                                {qualFile ? (
                                    <div className="flex items-center justify-center gap-2">
                                        <File className="h-4 w-4 text-[#0055FF]" />
                                        <span className="text-sm text-slate-900 truncate max-w-[200px]">{qualFile.name}</span>
                                        <button onClick={e => { e.stopPropagation(); setQualFile(null); }}><X className="h-4 w-4 text-slate-400 hover:text-red-500" /></button>
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-500"><Upload className="h-4 w-4 inline mr-1" />Carica PDF attestato</p>
                                )}
                            </div>
                        </div>

                        <div>
                            <Label className="text-xs font-medium">Note</Label>
                            <Input value={qualForm.notes} onChange={e => setQualForm(f => ({ ...f, notes: e.target.value }))} placeholder="Note aggiuntive" className="mt-1" />
                        </div>
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => { setShowQualForm(false); setQualFile(null); }}>Annulla</Button>
                        <Button data-testid="btn-save-qual" onClick={handleSaveQual} disabled={savingQual} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {savingQual && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            Aggiungi Attestato
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Delete Welder ══════ */}
            <Dialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-welder-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Operaio</DialogTitle>
                        <DialogDescription>Questa azione elimina anche tutti gli attestati associati.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">Eliminare <strong>{deleteTarget?.name}</strong> ({deleteTarget?.stamp_id})?</p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteTarget(null)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete-welder" onClick={handleDeleteWelder} disabled={deleting} variant="destructive">
                            {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />} Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Delete Qualification ══════ */}
            <Dialog open={!!deleteQual} onOpenChange={v => { if (!v) setDeleteQual(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-qual-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Patentino</DialogTitle>
                        <DialogDescription>Questa azione non puo essere annullata.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">Eliminare il patentino <strong>{deleteQual?.standard} {deleteQual?.process}</strong>?</p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteQual(null)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete-qual" onClick={handleDeleteQual} disabled={deletingQual} variant="destructive">
                            {deletingQual ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />} Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}

/* ══════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ══════════════════════════════════════════════════════════════ */

function StatCard({ label, value, icon: Icon, color, bg }) {
    return (
        <Card className="border-gray-200">
            <CardContent className="pt-4 pb-3 px-4">
                <div className="flex items-center gap-2.5">
                    <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
                        <Icon className={`h-4.5 w-4.5 ${color}`} />
                    </div>
                    <div>
                        <p className={`text-xl font-bold ${color}`}>{value}</p>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

function WelderDetail({ welder, onEdit, onDelete, onAddQual, onDeleteQual, onDownloadQual }) {
    const st = OVERALL_STATUS[welder.overall_status] || OVERALL_STATUS.no_qual;
    const StIcon = st.icon;

    return (
        <div className="space-y-4" data-testid="welder-detail">
            {/* Header card */}
            <Card className="border-gray-200">
                <CardContent className="pt-5 pb-4">
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-14 h-14 rounded-full bg-[#1E293B] flex items-center justify-center text-white font-bold text-lg">
                                {welder.stamp_id}
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-[#1E293B]">{welder.name}</h2>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <Badge className={`${st.badge} border text-xs`}><StIcon className="h-3 w-3 mr-1" />{st.label}</Badge>
                                    <span className="text-xs text-slate-400 capitalize">{welder.role}</span>
                                    {welder.hire_date && <span className="text-xs text-slate-400">dal {fmtDate(welder.hire_date)}</span>}
                                </div>
                                {(welder.phone || welder.email) && (
                                    <p className="text-xs text-slate-500 mt-1">{[welder.phone, welder.email].filter(Boolean).join(' - ')}</p>
                                )}
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" size="sm" data-testid="btn-edit-welder" onClick={onEdit}><Pencil className="h-3.5 w-3.5 mr-1" />Modifica</Button>
                            <Button variant="outline" size="sm" data-testid="btn-delete-welder-detail" onClick={onDelete} className="text-red-500 hover:text-red-700"><Trash2 className="h-3.5 w-3.5" /></Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Qualifications */}
            <Card className="border-gray-200">
                <CardContent className="p-0">
                    <div className="flex items-center justify-between px-4 py-3 border-b">
                        <h3 className="text-sm font-bold text-[#1E293B] flex items-center gap-1.5">
                            <Shield className="h-4 w-4 text-[#0055FF]" /> Patentini e Qualifiche
                            <span className="text-xs text-slate-400 font-normal ml-1">({welder.qualifications?.length || 0})</span>
                        </h3>
                        <Button data-testid="btn-add-qual" onClick={onAddQual} size="sm" className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs">
                            <Plus className="h-3.5 w-3.5 mr-1" /> Nuovo Patentino
                        </Button>
                    </div>
                    {(!welder.qualifications || welder.qualifications.length === 0) ? (
                        <div className="text-center py-10">
                            <Shield className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                            <p className="text-sm text-slate-500">Nessun patentino registrato</p>
                            <p className="text-xs text-slate-400 mt-1">Aggiungi il primo patentino per questo saldatore</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Norma</TableHead>
                                    <TableHead className="text-white font-semibold">Processo</TableHead>
                                    <TableHead className="text-white font-semibold">Materiale</TableHead>
                                    <TableHead className="text-white font-semibold">Spessori</TableHead>
                                    <TableHead className="text-white font-semibold">Scadenza</TableHead>
                                    <TableHead className="text-white font-semibold">Stato</TableHead>
                                    <TableHead className="w-[80px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {welder.qualifications.map(q => {
                                    const qs = QUAL_STATUS[q.status] || QUAL_STATUS.attivo;
                                    const isWarn = q.status === 'in_scadenza';
                                    const isExp = q.status === 'scaduto';
                                    return (
                                        <TableRow
                                            key={q.qual_id}
                                            data-testid={`qual-row-${q.qual_id}`}
                                            className={isExp ? 'bg-red-50/50' : isWarn ? 'bg-amber-50/50' : 'hover:bg-slate-50'}
                                        >
                                            <TableCell className="font-medium text-sm">{q.standard}</TableCell>
                                            <TableCell className="text-sm text-slate-600">{q.process || '--'}</TableCell>
                                            <TableCell className="text-sm text-slate-600">{q.material_group || '--'}</TableCell>
                                            <TableCell className="text-sm text-slate-600">{q.thickness_range || '--'}</TableCell>
                                            <TableCell>
                                                <div>
                                                    <span className={`text-sm font-medium ${isExp ? 'text-red-700' : isWarn ? 'text-amber-700' : 'text-slate-700'}`}>
                                                        {fmtDate(q.expiry_date)}
                                                    </span>
                                                    {q.days_until_expiry !== null && q.days_until_expiry !== undefined && (
                                                        <p className={`text-[10px] ${isExp ? 'text-red-500' : isWarn ? 'text-amber-500' : 'text-slate-400'}`}>
                                                            {q.days_until_expiry < 0 ? `Scaduto da ${Math.abs(q.days_until_expiry)}gg` : `${q.days_until_expiry}gg rimanenti`}
                                                        </p>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={`${qs.color} border text-[10px]`}>{qs.label}</Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex gap-0.5">
                                                    {q.has_file && (
                                                        <Button variant="ghost" size="sm" data-testid={`btn-dl-qual-${q.qual_id}`} onClick={() => onDownloadQual(q)} title="Scarica PDF">
                                                            <Download className="h-3.5 w-3.5 text-slate-500" />
                                                        </Button>
                                                    )}
                                                    <Button variant="ghost" size="sm" data-testid={`btn-del-qual-${q.qual_id}`} onClick={() => onDeleteQual(q)} title="Elimina">
                                                        <Trash2 className="h-3.5 w-3.5 text-slate-500 hover:text-red-500" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
