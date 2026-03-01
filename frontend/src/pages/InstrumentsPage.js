/**
 * InstrumentsPage — Registro Apparecchiature & Strumenti
 * Gestione asset aziendali: saldatrici, strumenti di misura, macchinari.
 * Monitora scadenze taratura e manutenzione (EN 1090 / ISO 3834).
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
    Plus, Search, Wrench, Ruler, Cog, Package,
    Loader2, Trash2, Pencil, AlertTriangle, CheckCircle2,
    XCircle, Clock, CalendarDays,
} from 'lucide-react';

/* ── Constants ── */
const TYPES = [
    { value: 'misura', label: 'Strumenti di Misura', icon: Ruler },
    { value: 'saldatura', label: 'Saldatrici', icon: Wrench },
    { value: 'macchinario', label: 'Macchinari', icon: Cog },
    { value: 'altro', label: 'Altro', icon: Package },
];

const STATUS_CONFIG = {
    attivo: { label: 'Attivo / Tarato', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircle2, dotColor: 'bg-emerald-500' },
    in_scadenza: { label: 'In Scadenza', color: 'bg-amber-100 text-amber-800 border-amber-200', icon: Clock, dotColor: 'bg-amber-500' },
    scaduto: { label: 'Scaduto', color: 'bg-red-100 text-red-800 border-red-200', icon: AlertTriangle, dotColor: 'bg-red-500' },
    in_manutenzione: { label: 'In Manutenzione', color: 'bg-blue-100 text-blue-800 border-blue-200', icon: Wrench, dotColor: 'bg-blue-500' },
    fuori_uso: { label: 'Fuori Uso', color: 'bg-slate-200 text-slate-600 border-slate-300', icon: XCircle, dotColor: 'bg-slate-400' },
};

const TYPE_COLORS = {
    misura: 'border-l-violet-500',
    saldatura: 'border-l-orange-500',
    macchinario: 'border-l-sky-500',
    altro: 'border-l-slate-400',
};

const EMPTY_FORM = {
    name: '', serial_number: '', type: 'misura', manufacturer: '',
    purchase_date: '', last_calibration_date: '', next_calibration_date: '',
    calibration_interval_months: 12, status: 'attivo', notes: '',
};

function formatDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

/* ═══════════════════════════════════════════════════════ */

export default function InstrumentsPage() {
    const [instruments, setInstruments] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');
    const [filterType, setFilterType] = useState('');
    const [filterStatus, setFilterStatus] = useState('');

    // Dialogs
    const [showForm, setShowForm] = useState(false);
    const [editTarget, setEditTarget] = useState(null);
    const [saving, setSaving] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [form, setForm] = useState({ ...EMPTY_FORM });

    /* ── Data fetch ── */
    const fetchInstruments = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterType) params.set('type', filterType);
            if (filterStatus) params.set('status', filterStatus);
            if (searchQ.trim()) params.set('search', searchQ.trim());
            const qs = params.toString();
            const res = await apiRequest(`/instruments/${qs ? `?${qs}` : ''}`);
            setInstruments(res.items || []);
            setStats(res.stats || {});
        } catch {
            toast.error('Errore caricamento strumenti');
        } finally {
            setLoading(false);
        }
    }, [filterType, filterStatus, searchQ]);

    useEffect(() => {
        const timer = setTimeout(fetchInstruments, 300);
        return () => clearTimeout(timer);
    }, [fetchInstruments]);

    /* ── CRUD ── */
    const handleSave = async () => {
        if (!form.name.trim()) { toast.error('Inserisci il nome'); return; }
        if (!form.serial_number.trim()) { toast.error('Inserisci la matricola'); return; }
        setSaving(true);
        try {
            if (editTarget) {
                await apiRequest(`/instruments/${editTarget.instrument_id}`, { method: 'PUT', body: form });
                toast.success('Strumento aggiornato');
            } else {
                await apiRequest('/instruments/', { method: 'POST', body: form });
                toast.success('Strumento creato');
            }
            closeForm();
            fetchInstruments();
        } catch (e) {
            toast.error(e.message || 'Errore salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        try {
            await apiRequest(`/instruments/${deleteTarget.instrument_id}`, { method: 'DELETE' });
            toast.success('Strumento eliminato');
            setDeleteTarget(null);
            fetchInstruments();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setDeleting(false);
        }
    };

    const openEdit = (inst) => {
        setEditTarget(inst);
        setForm({
            name: inst.name, serial_number: inst.serial_number, type: inst.type,
            manufacturer: inst.manufacturer || '', purchase_date: inst.purchase_date || '',
            last_calibration_date: inst.last_calibration_date || '',
            next_calibration_date: inst.next_calibration_date || '',
            calibration_interval_months: inst.calibration_interval_months || 12,
            status: inst.status, notes: inst.notes || '',
        });
        setShowForm(true);
    };

    const closeForm = () => {
        setShowForm(false);
        setEditTarget(null);
        setForm({ ...EMPTY_FORM });
    };

    /* ═══════════════════════════════ RENDER ═══════════════════════════════ */
    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="instruments-page">
                {/* ── Header ── */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">
                            Apparecchiature e Strumenti
                        </h1>
                        <p className="text-slate-600">Registro tarature e manutenzioni (EN 1090 / ISO 3834)</p>
                    </div>
                    <Button
                        data-testid="btn-add-instrument"
                        onClick={() => setShowForm(true)}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Aggiungi Strumento
                    </Button>
                </div>

                {/* ── Stats Cards ── */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="stats-bar">
                    <StatCard label="Totali" value={stats.total || 0} icon={Package} color="text-slate-700" bg="bg-slate-50" testId="stat-total" />
                    <StatCard label="Attivi" value={stats.attivi || 0} icon={CheckCircle2} color="text-emerald-700" bg="bg-emerald-50" testId="stat-attivi" />
                    <StatCard label="In Scadenza" value={stats.in_scadenza || 0} icon={Clock} color="text-amber-700" bg="bg-amber-50" testId="stat-in-scadenza" />
                    <StatCard label="Scaduti" value={stats.scaduti || 0} icon={AlertTriangle} color="text-red-700" bg="bg-red-50" testId="stat-scaduti" />
                    <StatCard label="Manutenzione" value={stats.in_manutenzione || 0} icon={Wrench} color="text-blue-700" bg="bg-blue-50" testId="stat-manutenzione" />
                    <StatCard label="Fuori Uso" value={stats.fuori_uso || 0} icon={XCircle} color="text-slate-500" bg="bg-slate-50" testId="stat-fuori-uso" />
                </div>

                {/* ── Toolbar ── */}
                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-3 flex-wrap">
                            <div className="relative flex-1 min-w-[200px] max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input
                                    data-testid="search-instruments"
                                    placeholder="Cerca per nome, matricola, marca..."
                                    value={searchQ}
                                    onChange={e => setSearchQ(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                            <Select value={filterType || '__all__'} onValueChange={v => setFilterType(v === '__all__' ? '' : v)}>
                                <SelectTrigger data-testid="filter-type" className="w-[180px]">
                                    <SelectValue placeholder="Tipo" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">Tutti i tipi</SelectItem>
                                    {TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                            <Select value={filterStatus || '__all__'} onValueChange={v => setFilterStatus(v === '__all__' ? '' : v)}>
                                <SelectTrigger data-testid="filter-status" className="w-[180px]">
                                    <SelectValue placeholder="Stato" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">Tutti gli stati</SelectItem>
                                    <SelectItem value="attivo">Attivo / Tarato</SelectItem>
                                    <SelectItem value="in_scadenza">In Scadenza (30gg)</SelectItem>
                                    <SelectItem value="scaduto">Scaduto</SelectItem>
                                    <SelectItem value="in_manutenzione">In Manutenzione</SelectItem>
                                    <SelectItem value="fuori_uso">Fuori Uso</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* ── Grid ── */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-6 w-6 animate-spin text-[#0055FF]" />
                    </div>
                ) : instruments.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-center" data-testid="empty-state">
                        <Ruler className="h-12 w-12 text-slate-300 mb-4" />
                        <h3 className="text-sm font-semibold text-slate-500 mb-1">Nessuno strumento trovato</h3>
                        <p className="text-xs text-slate-400 mb-4">
                            {searchQ || filterType || filterStatus
                                ? 'Prova a modificare i filtri'
                                : 'Aggiungi il primo strumento per iniziare il registro'}
                        </p>
                        {!searchQ && !filterType && !filterStatus && (
                            <Button data-testid="btn-empty-add" onClick={() => setShowForm(true)} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" size="sm">
                                <Plus className="h-3.5 w-3.5 mr-1.5" /> Aggiungi Strumento
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="instruments-grid">
                        {instruments.map(inst => (
                            <InstrumentCard
                                key={inst.instrument_id}
                                inst={inst}
                                onEdit={() => openEdit(inst)}
                                onDelete={() => setDeleteTarget(inst)}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* ══════ Create/Edit Dialog ══════ */}
            <Dialog open={showForm} onOpenChange={v => { if (!v) closeForm(); else setShowForm(true); }}>
                <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="instrument-form-dialog">
                    <DialogHeader>
                        <DialogTitle>{editTarget ? 'Modifica Strumento' : 'Nuovo Strumento'}</DialogTitle>
                        <DialogDescription>
                            {editTarget ? 'Aggiorna i dati dello strumento o registra una nuova taratura.' : 'Inserisci i dati del nuovo strumento o apparecchiatura.'}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 mt-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Nome *</Label>
                                <Input data-testid="input-name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="es. Calibro Digitale 150mm" className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Matricola / S/N *</Label>
                                <Input data-testid="input-serial" value={form.serial_number} onChange={e => setForm(f => ({ ...f, serial_number: e.target.value }))} placeholder="es. SN-12345" className="mt-1" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Tipo</Label>
                                <Select value={form.type} onValueChange={v => setForm(f => ({ ...f, type: v }))}>
                                    <SelectTrigger data-testid="select-type" className="mt-1"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Produttore</Label>
                                <Input data-testid="input-manufacturer" value={form.manufacturer} onChange={e => setForm(f => ({ ...f, manufacturer: e.target.value }))} placeholder="es. Mitutoyo" className="mt-1" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Data Acquisto</Label>
                                <Input data-testid="input-purchase-date" type="date" value={form.purchase_date} onChange={e => setForm(f => ({ ...f, purchase_date: e.target.value }))} className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Stato</Label>
                                <Select value={form.status} onValueChange={v => setForm(f => ({ ...f, status: v }))}>
                                    <SelectTrigger data-testid="select-status" className="mt-1"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="attivo">Attivo</SelectItem>
                                        <SelectItem value="in_manutenzione">In Manutenzione</SelectItem>
                                        <SelectItem value="fuori_uso">Fuori Uso</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="border-t pt-3">
                            <p className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
                                <CalendarDays className="h-3.5 w-3.5" /> Taratura / Calibrazione
                            </p>
                            <div className="grid grid-cols-3 gap-3">
                                <div>
                                    <Label className="text-xs font-medium">Ultima Taratura</Label>
                                    <Input data-testid="input-last-cal" type="date" value={form.last_calibration_date} onChange={e => setForm(f => ({ ...f, last_calibration_date: e.target.value }))} className="mt-1" />
                                </div>
                                <div>
                                    <Label className="text-xs font-medium">Prossima Scadenza</Label>
                                    <Input data-testid="input-next-cal" type="date" value={form.next_calibration_date} onChange={e => setForm(f => ({ ...f, next_calibration_date: e.target.value }))} className="mt-1" />
                                </div>
                                <div>
                                    <Label className="text-xs font-medium">Intervallo (mesi)</Label>
                                    <Input data-testid="input-interval" type="number" min={1} value={form.calibration_interval_months} onChange={e => setForm(f => ({ ...f, calibration_interval_months: parseInt(e.target.value) || 12 }))} className="mt-1" />
                                </div>
                            </div>
                        </div>

                        <div>
                            <Label className="text-xs font-medium">Note</Label>
                            <Textarea data-testid="input-notes" value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Note aggiuntive..." rows={2} className="mt-1" />
                        </div>
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={closeForm}>Annulla</Button>
                        <Button data-testid="btn-save-instrument" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            {editTarget ? 'Salva Modifiche' : 'Crea Strumento'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Delete Confirm ══════ */}
            <Dialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Strumento</DialogTitle>
                        <DialogDescription>Questa azione non puo essere annullata.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">
                        Sei sicuro di voler eliminare <strong>{deleteTarget?.name}</strong> ({deleteTarget?.serial_number})?
                    </p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteTarget(null)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete" onClick={handleDelete} disabled={deleting} variant="destructive">
                            {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
                            Elimina
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

function StatCard({ label, value, icon: Icon, color, bg, testId }) {
    return (
        <Card className="border-gray-200" data-testid={testId}>
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

function InstrumentCard({ inst, onEdit, onDelete }) {
    const sc = STATUS_CONFIG[inst.computed_status] || STATUS_CONFIG.attivo;
    const StatusIcon = sc.icon;
    const typeLabel = TYPES.find(t => t.value === inst.type)?.label || inst.type;
    const borderColor = TYPE_COLORS[inst.type] || TYPE_COLORS.altro;
    const isExpiring = inst.computed_status === 'in_scadenza';
    const isExpired = inst.computed_status === 'scaduto';

    return (
        <Card
            className={`border-gray-200 border-l-4 ${borderColor} hover:shadow-md transition-all group`}
            data-testid={`inst-card-${inst.instrument_id}`}
        >
            <CardContent className="pt-4 pb-3 px-4">
                {/* Header */}
                <div className="flex items-start justify-between mb-2">
                    <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-bold text-[#1E293B] truncate" title={inst.name}>
                            {inst.name}
                        </h3>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">{inst.serial_number}</p>
                    </div>
                    <Badge className={`${sc.color} border text-[10px] px-2 py-0.5 flex-shrink-0 ml-2`}>
                        <StatusIcon className="h-3 w-3 mr-1" />
                        {sc.label}
                    </Badge>
                </div>

                {/* Details */}
                <div className="space-y-1.5 mb-3">
                    {inst.manufacturer && (
                        <div className="flex items-center text-xs text-slate-600">
                            <span className="text-slate-400 w-20">Marca:</span>
                            <span className="font-medium">{inst.manufacturer}</span>
                        </div>
                    )}
                    <div className="flex items-center text-xs text-slate-600">
                        <span className="text-slate-400 w-20">Tipo:</span>
                        <span>{typeLabel}</span>
                    </div>
                    {inst.last_calibration_date && (
                        <div className="flex items-center text-xs text-slate-600">
                            <span className="text-slate-400 w-20">Ult. taratura:</span>
                            <span>{formatDate(inst.last_calibration_date)}</span>
                        </div>
                    )}
                </div>

                {/* Expiry bar */}
                {inst.next_calibration_date && (
                    <div className={`rounded-lg px-3 py-2 mb-3 ${
                        isExpired ? 'bg-red-50 border border-red-200' :
                        isExpiring ? 'bg-amber-50 border border-amber-200' :
                        'bg-slate-50 border border-slate-200'
                    }`}>
                        <div className="flex items-center justify-between">
                            <span className={`text-[10px] uppercase tracking-wider font-semibold ${
                                isExpired ? 'text-red-600' : isExpiring ? 'text-amber-600' : 'text-slate-500'
                            }`}>
                                {isExpired ? 'Taratura scaduta' : 'Prossima taratura'}
                            </span>
                            <span className={`text-xs font-bold ${
                                isExpired ? 'text-red-700' : isExpiring ? 'text-amber-700' : 'text-slate-700'
                            }`}>
                                {formatDate(inst.next_calibration_date)}
                            </span>
                        </div>
                        {inst.days_until_expiry !== null && inst.days_until_expiry !== undefined && (
                            <p className={`text-[10px] mt-0.5 ${
                                isExpired ? 'text-red-500' : isExpiring ? 'text-amber-500' : 'text-slate-400'
                            }`}>
                                {inst.days_until_expiry < 0
                                    ? `Scaduto da ${Math.abs(inst.days_until_expiry)} giorni`
                                    : inst.days_until_expiry === 0
                                        ? 'Scade oggi'
                                        : `${inst.days_until_expiry} giorni rimanenti`}
                            </p>
                        )}
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="outline" size="sm" data-testid={`btn-edit-${inst.instrument_id}`} onClick={onEdit} className="flex-1 text-xs">
                        <Pencil className="h-3 w-3 mr-1" /> Modifica
                    </Button>
                    <Button variant="outline" size="sm" data-testid={`btn-delete-${inst.instrument_id}`} onClick={onDelete} className="text-xs text-red-500 hover:text-red-700 hover:border-red-200">
                        <Trash2 className="h-3 w-3" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
