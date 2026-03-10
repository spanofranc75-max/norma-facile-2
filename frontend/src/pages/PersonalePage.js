/**
 * PersonalePage — Modulo Personale completo.
 * 4 tab: Dipendenti | Presenze | Documenti | Report
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest, formatDateIT } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
    Plus, Trash2, Upload, Download, FileText, Mail, Settings,
    CalendarDays, Users, Clock, CheckCircle2,
} from 'lucide-react';
import { useConfirm } from '../components/ConfirmProvider';

const API = process.env.REACT_APP_BACKEND_URL;

const TIPI_CONTRATTO = [
    { value: 'dipendente', label: 'Dipendente' },
    { value: 'amministratore', label: 'Amministratore' },
    { value: 'socio', label: 'Socio' },
];

const TIPI_PRESENZA = [
    { value: 'presente', label: 'Presente', color: 'bg-emerald-100 text-emerald-800' },
    { value: 'assente', label: 'Assente', color: 'bg-red-100 text-red-800' },
    { value: 'ferie', label: 'Ferie', color: 'bg-blue-100 text-blue-800' },
    { value: 'permesso', label: 'Permesso', color: 'bg-amber-100 text-amber-800' },
    { value: 'malattia', label: 'Malattia', color: 'bg-slate-200 text-slate-700' },
    { value: 'straordinario', label: 'Straordinario', color: 'bg-purple-100 text-purple-800' },
];

const TIPI_DOCUMENTO = [
    { value: 'busta_paga', label: 'Busta Paga' },
    { value: 'rimborso_spese', label: 'Rimborso Spese' },
    { value: 'contratto', label: 'Contratto' },
    { value: 'altro', label: 'Altro' },
];

const GIORNI = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab'];
const GIORNI_FULL = { lun: 'Lunedi', mar: 'Martedi', mer: 'Mercoledi', gio: 'Giovedi', ven: 'Venerdi', sab: 'Sabato' };

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

function currentMese() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function meseLabel(m) {
    if (!m) return '';
    const [y, mm] = m.split('-');
    const mesi = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];
    return `${mesi[parseInt(mm) - 1] || mm} ${y}`;
}

// ─── MAIN PAGE ──────────────────────────────────────────────────

export default function PersonalePage() {
    const [activeTab, setActiveTab] = useState('dipendenti');
    const [dipendenti, setDipendenti] = useState([]);

    const fetchDipendenti = useCallback(async () => {
        try {
            const data = await apiRequest('/personale/dipendenti');
            setDipendenti(data.dipendenti || []);
        } catch (e) { console.error(e); }
    }, []);

    useEffect(() => { fetchDipendenti(); }, [fetchDipendenti]);

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="personale-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900" data-testid="personale-title">Personale</h1>
                        <p className="text-sm text-slate-500 mt-1">Gestione dipendenti, presenze, documenti e report</p>
                    </div>
                </div>

                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid w-full grid-cols-4 max-w-lg" data-testid="personale-tabs">
                        <TabsTrigger value="dipendenti" data-testid="tab-dipendenti">Dipendenti</TabsTrigger>
                        <TabsTrigger value="presenze" data-testid="tab-presenze">Presenze</TabsTrigger>
                        <TabsTrigger value="documenti" data-testid="tab-documenti">Documenti</TabsTrigger>
                        <TabsTrigger value="report" data-testid="tab-report">Report</TabsTrigger>
                    </TabsList>

                    <TabsContent value="dipendenti">
                        <DipendentiTab dipendenti={dipendenti} onRefresh={fetchDipendenti} />
                    </TabsContent>
                    <TabsContent value="presenze">
                        <PresenzeTab dipendenti={dipendenti} />
                    </TabsContent>
                    <TabsContent value="documenti">
                        <DocumentiTab dipendenti={dipendenti} />
                    </TabsContent>
                    <TabsContent value="report">
                        <ReportTab dipendenti={dipendenti} />
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}

// ─── TAB 1: DIPENDENTI ──────────────────────────────────────────

function DipendentiTab({ dipendenti, onRefresh }) {
    const confirm = useConfirm();
    const [open, setOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState({
        nome: '', cognome: '', codice_fiscale: '', ruolo: '', tipo_contratto: 'dipendente',
        ore_settimanali: 40, giorni_lavorativi: ['lun', 'mar', 'mer', 'gio', 'ven', 'sab'], email: '',
    });

    const resetForm = () => {
        setForm({
            nome: '', cognome: '', codice_fiscale: '', ruolo: '', tipo_contratto: 'dipendente',
            ore_settimanali: 40, giorni_lavorativi: ['lun', 'mar', 'mer', 'gio', 'ven', 'sab'], email: '',
        });
        setEditing(null);
    };

    const openNew = () => { resetForm(); setOpen(true); };
    const openEdit = (d) => {
        setEditing(d.dipendente_id);
        setForm({
            nome: d.nome || '', cognome: d.cognome || '', codice_fiscale: d.codice_fiscale || '',
            ruolo: d.ruolo || '', tipo_contratto: d.tipo_contratto || 'dipendente',
            ore_settimanali: d.ore_settimanali || 40,
            giorni_lavorativi: d.giorni_lavorativi || GIORNI,
            email: d.email || '',
        });
        setOpen(true);
    };

    const handleSave = async () => {
        if (!form.nome || !form.cognome) { toast.error('Nome e cognome richiesti'); return; }
        try {
            if (editing) {
                await apiRequest(`/personale/dipendenti/${editing}`, { method: 'PUT', body: JSON.stringify(form) });
                toast.success('Dipendente aggiornato');
            } else {
                await apiRequest('/personale/dipendenti', { method: 'POST', body: JSON.stringify(form) });
                toast.success('Dipendente creato');
            }
            setOpen(false);
            resetForm();
            onRefresh();
        } catch (e) { toast.error(e.message); }
    };

    const handleDeactivate = async (d) => {
        const ok = await confirm({
            title: 'Disattiva Dipendente',
            description: `Confermi la disattivazione di ${d.nome} ${d.cognome}?`,
        });
        if (!ok) return;
        try {
            await apiRequest(`/personale/dipendenti/${d.dipendente_id}`, { method: 'DELETE' });
            toast.success('Dipendente disattivato');
            onRefresh();
        } catch (e) { toast.error(e.message); }
    };

    const toggleGiorno = (g) => {
        setForm(f => ({
            ...f,
            giorni_lavorativi: f.giorni_lavorativi.includes(g)
                ? f.giorni_lavorativi.filter(x => x !== g)
                : [...f.giorni_lavorativi, g],
        }));
    };

    return (
        <Card data-testid="dipendenti-tab">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
                <CardTitle className="text-lg">Dipendenti Attivi ({dipendenti.length})</CardTitle>
                <Button size="sm" onClick={openNew} data-testid="btn-add-dipendente">
                    <Plus className="h-4 w-4 mr-1" /> Aggiungi
                </Button>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Nome</TableHead>
                            <TableHead>Ruolo</TableHead>
                            <TableHead>Contratto</TableHead>
                            <TableHead>Ore/Sett.</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead className="w-[80px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {dipendenti.map(d => (
                            <TableRow key={d.dipendente_id} className="cursor-pointer hover:bg-slate-50"
                                onClick={() => openEdit(d)} data-testid={`row-dip-${d.dipendente_id}`}>
                                <TableCell className="font-medium">{d.cognome} {d.nome}</TableCell>
                                <TableCell>{d.ruolo}</TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="capitalize">{d.tipo_contratto}</Badge>
                                </TableCell>
                                <TableCell>{d.ore_settimanali}h</TableCell>
                                <TableCell className="text-sm text-slate-500">{d.email || '-'}</TableCell>
                                <TableCell>
                                    <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500"
                                        onClick={(e) => { e.stopPropagation(); handleDeactivate(d); }}
                                        data-testid={`btn-deactivate-${d.dipendente_id}`}>
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                        {dipendenti.length === 0 && (
                            <TableRow><TableCell colSpan={6} className="text-center py-8 text-slate-400">
                                Nessun dipendente registrato
                            </TableCell></TableRow>
                        )}
                    </TableBody>
                </Table>
            </CardContent>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-lg" data-testid="dialog-dipendente">
                    <DialogHeader>
                        <DialogTitle>{editing ? 'Modifica Dipendente' : 'Nuovo Dipendente'}</DialogTitle>
                    </DialogHeader>
                    <div className="grid grid-cols-2 gap-3">
                        <div><Label>Nome *</Label><Input value={form.nome} onChange={e => setForm(f => ({ ...f, nome: e.target.value }))} data-testid="input-nome" /></div>
                        <div><Label>Cognome *</Label><Input value={form.cognome} onChange={e => setForm(f => ({ ...f, cognome: e.target.value }))} data-testid="input-cognome" /></div>
                        <div><Label>Codice Fiscale</Label><Input value={form.codice_fiscale} onChange={e => setForm(f => ({ ...f, codice_fiscale: e.target.value.toUpperCase() }))} data-testid="input-cf" /></div>
                        <div><Label>Ruolo</Label><Input value={form.ruolo} onChange={e => setForm(f => ({ ...f, ruolo: e.target.value }))} data-testid="input-ruolo" /></div>
                        <div>
                            <Label>Tipo Contratto</Label>
                            <Select value={form.tipo_contratto} onValueChange={v => setForm(f => ({ ...f, tipo_contratto: v }))}>
                                <SelectTrigger data-testid="select-contratto"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {TIPI_CONTRATTO.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div><Label>Ore Settimanali</Label><Input type="number" value={form.ore_settimanali} onChange={e => setForm(f => ({ ...f, ore_settimanali: parseFloat(e.target.value) || 0 }))} data-testid="input-ore" /></div>
                        <div className="col-span-2"><Label>Email</Label><Input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} data-testid="input-email" /></div>
                        <div className="col-span-2">
                            <Label>Giorni Lavorativi</Label>
                            <div className="flex gap-2 mt-1">
                                {GIORNI.map(g => (
                                    <button key={g} type="button" onClick={() => toggleGiorno(g)}
                                        className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${form.giorni_lavorativi.includes(g) ? 'bg-[#0055FF] text-white' : 'bg-slate-100 text-slate-500'}`}
                                        data-testid={`giorno-${g}`}>
                                        {g.toUpperCase()}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)}>Annulla</Button>
                        <Button onClick={handleSave} data-testid="btn-save-dipendente">{editing ? 'Salva' : 'Crea'}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}

// ─── TAB 2: PRESENZE ────────────────────────────────────────────

function PresenzeTab({ dipendenti }) {
    const [mese, setMese] = useState(currentMese());
    const [selectedDip, setSelectedDip] = useState('');
    const [presenze, setPresenze] = useState([]);
    const [cellDialog, setCellDialog] = useState(null);
    const [cellForm, setCellForm] = useState({ tipo: 'presente', ore_lavorate: 0, ore_straordinario: 0, note: '' });

    const fetchPresenze = useCallback(async () => {
        try {
            const params = new URLSearchParams({ mese });
            if (selectedDip) params.append('dipendente_id', selectedDip);
            const data = await apiRequest(`/personale/presenze?${params}`);
            setPresenze(data.presenze || []);
        } catch (e) { console.error(e); }
    }, [mese, selectedDip]);

    useEffect(() => { fetchPresenze(); }, [fetchPresenze]);

    // Calculate days of month
    const [year, month] = mese.split('-').map(Number);
    const daysInMonth = new Date(year, month, 0).getDate();
    const allDays = Array.from({ length: daysInMonth }, (_, i) => {
        const d = new Date(year, month - 1, i + 1);
        const dayOfWeek = d.getDay(); // 0=sun
        return {
            date: `${mese}-${String(i + 1).padStart(2, '0')}`,
            dayNum: i + 1,
            dayName: ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab'][dayOfWeek],
            isSunday: dayOfWeek === 0,
        };
    });

    const getPresenza = (dipId, date) => presenze.find(p => p.dipendente_id === dipId && p.data === date);

    const openCell = (dipId, day) => {
        const existing = getPresenza(dipId, day.date);
        setCellForm({
            tipo: existing?.tipo || 'presente',
            ore_lavorate: existing?.ore_lavorate || 0,
            ore_straordinario: existing?.ore_straordinario || 0,
            note: existing?.note || '',
        });
        setCellDialog({ dipId, date: day.date, dayNum: day.dayNum });
    };

    const saveCell = async () => {
        if (!cellDialog) return;
        try {
            await apiRequest('/personale/presenze', {
                method: 'POST',
                body: JSON.stringify({
                    dipendente_id: cellDialog.dipId,
                    data: cellDialog.date,
                    ...cellForm,
                }),
            });
            setCellDialog(null);
            fetchPresenze();
        } catch (e) { toast.error(e.message); }
    };

    // Summary for selected dip
    const dipPresenze = selectedDip ? presenze.filter(p => p.dipendente_id === selectedDip) : presenze;
    const summary = {};
    TIPI_PRESENZA.forEach(t => { summary[t.value] = 0; });
    let totOre = 0, totStraord = 0;
    dipPresenze.forEach(p => {
        if (summary[p.tipo] !== undefined) summary[p.tipo]++;
        totOre += p.ore_lavorate || 0;
        totStraord += p.ore_straordinario || 0;
    });

    const filteredDips = selectedDip ? dipendenti.filter(d => d.dipendente_id === selectedDip) : dipendenti;

    return (
        <Card data-testid="presenze-tab">
            <CardHeader className="pb-4">
                <div className="flex items-center gap-4 flex-wrap">
                    <div>
                        <Label className="text-xs">Mese</Label>
                        <Input type="month" value={mese} onChange={e => setMese(e.target.value)} className="w-44" data-testid="input-mese-presenze" />
                    </div>
                    <div>
                        <Label className="text-xs">Dipendente</Label>
                        <Select value={selectedDip} onValueChange={setSelectedDip}>
                            <SelectTrigger className="w-52" data-testid="select-dipendente-presenze"><SelectValue placeholder="Tutti" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value=" ">Tutti</SelectItem>
                                {dipendenti.map(d => <SelectItem key={d.dipendente_id} value={d.dipendente_id}>{d.cognome} {d.nome}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {/* Attendance grid */}
                <div className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="sticky left-0 bg-white z-10 min-w-[140px]">Dipendente</TableHead>
                                {allDays.map(day => (
                                    <TableHead key={day.date} className={`text-center text-[10px] px-1 min-w-[32px] ${day.isSunday ? 'bg-red-50' : ''}`}>
                                        <div>{day.dayNum}</div>
                                        <div className="text-slate-400">{day.dayName}</div>
                                    </TableHead>
                                ))}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredDips.map(dip => (
                                <TableRow key={dip.dipendente_id}>
                                    <TableCell className="sticky left-0 bg-white z-10 font-medium text-xs whitespace-nowrap">
                                        {dip.cognome} {dip.nome}
                                    </TableCell>
                                    {allDays.map(day => {
                                        const p = getPresenza(dip.dipendente_id, day.date);
                                        const tipo = p?.tipo;
                                        const color = TIPI_PRESENZA.find(t => t.value === tipo)?.color || '';
                                        return (
                                            <TableCell key={day.date}
                                                className={`text-center p-0.5 cursor-pointer hover:bg-slate-100 ${day.isSunday ? 'bg-red-50/50' : ''}`}
                                                onClick={() => !day.isSunday && openCell(dip.dipendente_id, day)}
                                                data-testid={`cell-${dip.dipendente_id}-${day.date}`}>
                                                {tipo && (
                                                    <span className={`inline-block w-6 h-5 rounded text-[8px] font-bold leading-5 ${color}`}>
                                                        {tipo.charAt(0).toUpperCase()}
                                                    </span>
                                                )}
                                            </TableCell>
                                        );
                                    })}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>

                {/* Summary */}
                <div className="mt-4 flex flex-wrap gap-3" data-testid="presenze-summary">
                    {TIPI_PRESENZA.map(t => (
                        <div key={t.value} className={`px-3 py-1.5 rounded-md text-xs font-medium ${t.color}`}>
                            {t.label}: {summary[t.value]}
                        </div>
                    ))}
                    <div className="px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700">
                        Ore: {totOre.toFixed(1)}
                    </div>
                    <div className="px-3 py-1.5 rounded-md text-xs font-medium bg-purple-50 text-purple-700">
                        Straordinario: {totStraord.toFixed(1)}h
                    </div>
                </div>
            </CardContent>

            {/* Cell edit dialog */}
            <Dialog open={!!cellDialog} onOpenChange={() => setCellDialog(null)}>
                <DialogContent className="max-w-sm" data-testid="dialog-presenza">
                    <DialogHeader>
                        <DialogTitle>Presenza — Giorno {cellDialog?.dayNum}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label>Tipo</Label>
                            <Select value={cellForm.tipo} onValueChange={v => setCellForm(f => ({ ...f, tipo: v }))}>
                                <SelectTrigger data-testid="select-tipo-presenza"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {TIPI_PRESENZA.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Ore Lavorate</Label>
                                <Input type="number" step="0.5" value={cellForm.ore_lavorate}
                                    onChange={e => setCellForm(f => ({ ...f, ore_lavorate: parseFloat(e.target.value) || 0 }))}
                                    data-testid="input-ore-lavorate" />
                            </div>
                            <div>
                                <Label>Ore Straordinario</Label>
                                <Input type="number" step="0.5" value={cellForm.ore_straordinario}
                                    onChange={e => setCellForm(f => ({ ...f, ore_straordinario: parseFloat(e.target.value) || 0 }))}
                                    data-testid="input-ore-straordinario" />
                            </div>
                        </div>
                        <div>
                            <Label>Note</Label>
                            <Textarea value={cellForm.note} onChange={e => setCellForm(f => ({ ...f, note: e.target.value }))}
                                rows={2} data-testid="input-note-presenza" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCellDialog(null)}>Annulla</Button>
                        <Button onClick={saveCell} data-testid="btn-save-presenza">Salva</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}

// ─── TAB 3: DOCUMENTI ───────────────────────────────────────────

function DocumentiTab({ dipendenti }) {
    const confirm = useConfirm();
    const [docs, setDocs] = useState([]);
    const [filters, setFilters] = useState({ dipendente_id: '', tipo: '', mese: '' });
    const [uploadOpen, setUploadOpen] = useState(false);
    const [uploadForm, setUploadForm] = useState({
        dipendente_id: '', tipo: 'busta_paga', mese: currentMese(), descrizione: '', importo: 0, file: null,
    });
    const [uploading, setUploading] = useState(false);

    const fetchDocs = useCallback(async () => {
        try {
            const params = new URLSearchParams();
            if (filters.dipendente_id) params.append('dipendente_id', filters.dipendente_id);
            if (filters.tipo) params.append('tipo', filters.tipo);
            if (filters.mese) params.append('mese', filters.mese);
            const data = await apiRequest(`/personale/documenti?${params}`);
            setDocs(data.documenti || []);
        } catch (e) { console.error(e); }
    }, [filters]);

    useEffect(() => { fetchDocs(); }, [fetchDocs]);

    const handleUpload = async () => {
        if (!uploadForm.dipendente_id || !uploadForm.file) {
            toast.error('Seleziona dipendente e file');
            return;
        }
        setUploading(true);
        try {
            const fd = new FormData();
            fd.append('file', uploadForm.file);
            fd.append('dipendente_id', uploadForm.dipendente_id);
            fd.append('tipo', uploadForm.tipo);
            fd.append('mese', uploadForm.tipo === 'busta_paga' ? uploadForm.mese : '');
            fd.append('descrizione', uploadForm.descrizione);
            fd.append('importo', uploadForm.importo.toString());

            const resp = await fetch(`${API}/api/personale/documenti/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${document.cookie.split('session_id=')[1]?.split(';')[0] || ''}` },
                body: fd,
                credentials: 'include',
            });
            if (!resp.ok) throw new Error('Upload fallito');
            toast.success('Documento caricato');
            setUploadOpen(false);
            setUploadForm({ dipendente_id: '', tipo: 'busta_paga', mese: currentMese(), descrizione: '', importo: 0, file: null });
            fetchDocs();
        } catch (e) { toast.error(e.message); } finally { setUploading(false); }
    };

    const handleDelete = async (doc) => {
        const ok = await confirm({ title: 'Elimina Documento', description: `Confermi l'eliminazione di "${doc.descrizione}"?` });
        if (!ok) return;
        try {
            await apiRequest(`/personale/documenti/${doc.documento_id}`, { method: 'DELETE' });
            toast.success('Documento eliminato');
            fetchDocs();
        } catch (e) { toast.error(e.message); }
    };

    const handleDownload = async (doc) => {
        try {
            const resp = await fetch(`${API}/api/personale/documenti/${doc.documento_id}/download`, {
                credentials: 'include',
            });
            if (!resp.ok) throw new Error('Download fallito');
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = doc.descrizione || 'documento.pdf';
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    const totalRimborsi = docs.filter(d => d.tipo === 'rimborso_spese').reduce((s, d) => s + (d.importo || 0), 0);
    const tipoLabel = (t) => TIPI_DOCUMENTO.find(x => x.value === t)?.label || t;
    const dipName = (id) => { const d = dipendenti.find(x => x.dipendente_id === id); return d ? `${d.cognome} ${d.nome}` : id; };

    return (
        <Card data-testid="documenti-tab">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Documenti</CardTitle>
                    <Button size="sm" onClick={() => setUploadOpen(true)} data-testid="btn-upload-doc">
                        <Upload className="h-4 w-4 mr-1" /> Upload
                    </Button>
                </div>
                <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <Select value={filters.dipendente_id} onValueChange={v => setFilters(f => ({ ...f, dipendente_id: v === ' ' ? '' : v }))}>
                        <SelectTrigger className="w-48" data-testid="filter-dip-doc"><SelectValue placeholder="Tutti i dipendenti" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value=" ">Tutti</SelectItem>
                            {dipendenti.map(d => <SelectItem key={d.dipendente_id} value={d.dipendente_id}>{d.cognome} {d.nome}</SelectItem>)}
                        </SelectContent>
                    </Select>
                    <Select value={filters.tipo} onValueChange={v => setFilters(f => ({ ...f, tipo: v === ' ' ? '' : v }))}>
                        <SelectTrigger className="w-40" data-testid="filter-tipo-doc"><SelectValue placeholder="Tutti i tipi" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value=" ">Tutti</SelectItem>
                            {TIPI_DOCUMENTO.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                        </SelectContent>
                    </Select>
                    <Input type="month" value={filters.mese} onChange={e => setFilters(f => ({ ...f, mese: e.target.value }))} className="w-40" placeholder="Mese" data-testid="filter-mese-doc" />
                </div>
            </CardHeader>
            <CardContent>
                {totalRimborsi > 0 && (
                    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2" data-testid="totale-rimborsi">
                        <span className="text-sm font-medium text-amber-800">Totale Rimborsi Spese:</span>
                        <span className="text-sm font-bold text-amber-900">{fmtEur(totalRimborsi)}</span>
                    </div>
                )}
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Tipo</TableHead>
                            <TableHead>Dipendente</TableHead>
                            <TableHead>Descrizione</TableHead>
                            <TableHead>Mese</TableHead>
                            <TableHead>Importo</TableHead>
                            <TableHead>Data</TableHead>
                            <TableHead className="w-[100px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {docs.map(doc => (
                            <TableRow key={doc.documento_id} data-testid={`row-doc-${doc.documento_id}`}>
                                <TableCell><Badge variant="outline">{tipoLabel(doc.tipo)}</Badge></TableCell>
                                <TableCell className="text-sm">{dipName(doc.dipendente_id)}</TableCell>
                                <TableCell className="text-sm">{doc.descrizione}</TableCell>
                                <TableCell className="text-sm">{doc.mese ? meseLabel(doc.mese) : '-'}</TableCell>
                                <TableCell className="text-sm">{doc.importo ? fmtEur(doc.importo) : '-'}</TableCell>
                                <TableCell className="text-xs text-slate-500">{formatDateIT(doc.created_at)}</TableCell>
                                <TableCell>
                                    <div className="flex gap-1">
                                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDownload(doc)} data-testid={`btn-download-${doc.documento_id}`}>
                                            <Download className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleDelete(doc)} data-testid={`btn-delete-doc-${doc.documento_id}`}>
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                        {docs.length === 0 && (
                            <TableRow><TableCell colSpan={7} className="text-center py-8 text-slate-400">Nessun documento</TableCell></TableRow>
                        )}
                    </TableBody>
                </Table>
            </CardContent>

            {/* Upload dialog */}
            <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
                <DialogContent className="max-w-md" data-testid="dialog-upload-doc">
                    <DialogHeader><DialogTitle>Upload Documento</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label>Dipendente *</Label>
                            <Select value={uploadForm.dipendente_id} onValueChange={v => setUploadForm(f => ({ ...f, dipendente_id: v }))}>
                                <SelectTrigger data-testid="upload-select-dip"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                <SelectContent>
                                    {dipendenti.map(d => <SelectItem key={d.dipendente_id} value={d.dipendente_id}>{d.cognome} {d.nome}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label>Tipo</Label>
                            <Select value={uploadForm.tipo} onValueChange={v => setUploadForm(f => ({ ...f, tipo: v }))}>
                                <SelectTrigger data-testid="upload-select-tipo"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {TIPI_DOCUMENTO.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        {uploadForm.tipo === 'busta_paga' && (
                            <div><Label>Mese</Label><Input type="month" value={uploadForm.mese} onChange={e => setUploadForm(f => ({ ...f, mese: e.target.value }))} data-testid="upload-mese" /></div>
                        )}
                        {uploadForm.tipo === 'rimborso_spese' && (
                            <div><Label>Importo</Label><Input type="number" step="0.01" value={uploadForm.importo} onChange={e => setUploadForm(f => ({ ...f, importo: parseFloat(e.target.value) || 0 }))} data-testid="upload-importo" /></div>
                        )}
                        <div><Label>Descrizione</Label><Input value={uploadForm.descrizione} onChange={e => setUploadForm(f => ({ ...f, descrizione: e.target.value }))} data-testid="upload-desc" /></div>
                        <div>
                            <Label>File PDF *</Label>
                            <Input type="file" accept=".pdf,.doc,.docx,.xlsx,.jpg,.png" onChange={e => setUploadForm(f => ({ ...f, file: e.target.files[0] }))} data-testid="upload-file" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setUploadOpen(false)}>Annulla</Button>
                        <Button onClick={handleUpload} disabled={uploading} data-testid="btn-confirm-upload">
                            {uploading ? 'Caricamento...' : 'Carica'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}

// ─── TAB 4: REPORT ──────────────────────────────────────────────

function ReportTab({ dipendenti }) {
    const confirm = useConfirm();
    const [mese, setMese] = useState(currentMese());
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [impostazioni, setImpostazioni] = useState({ report_presenze_giorno_invio: 5, report_presenze_email_consulente: '' });
    const [savingSettings, setSavingSettings] = useState(false);

    const fetchReport = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiRequest(`/personale/report/mensile?mese=${mese}`);
            setReport(data);
        } catch (e) { console.error(e); } finally { setLoading(false); }
    }, [mese]);

    const fetchSettings = useCallback(async () => {
        try {
            const data = await apiRequest('/personale/report/impostazioni');
            setImpostazioni(data);
        } catch (e) { console.error(e); }
    }, []);

    useEffect(() => { fetchReport(); }, [fetchReport]);
    useEffect(() => { fetchSettings(); }, [fetchSettings]);

    const handleDownloadPdf = async () => {
        try {
            const resp = await fetch(`${API}/api/personale/report/pdf?mese=${mese}`, { credentials: 'include' });
            if (!resp.ok) throw new Error('Download fallito');
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `presenze_${mese}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    const handleSendEmail = async () => {
        const email = impostazioni.report_presenze_email_consulente;
        if (!email) { toast.error('Configura email consulente nelle impostazioni'); return; }
        const ok = await confirm({
            title: 'Invia Report al Consulente',
            description: `Confermi l'invio del report ${meseLabel(mese)} a ${email}?`,
        });
        if (!ok) return;
        try {
            await apiRequest(`/personale/report/invia-email?mese=${mese}`, { method: 'POST' });
            toast.success('Report inviato!');
            fetchReport();
        } catch (e) { toast.error(e.message); }
    };

    const handleSaveSettings = async () => {
        setSavingSettings(true);
        try {
            await apiRequest('/personale/report/schedula', {
                method: 'POST',
                body: JSON.stringify(impostazioni),
            });
            toast.success('Impostazioni salvate');
        } catch (e) { toast.error(e.message); } finally { setSavingSettings(false); }
    };

    return (
        <div className="space-y-4" data-testid="report-tab">
            <Card>
                <CardHeader className="pb-4">
                    <div className="flex items-center justify-between flex-wrap gap-3">
                        <div className="flex items-center gap-3">
                            <div>
                                <Label className="text-xs">Mese</Label>
                                <Input type="month" value={mese} onChange={e => setMese(e.target.value)} className="w-44" data-testid="input-mese-report" />
                            </div>
                            {report?.inviato && (
                                <Badge className="bg-emerald-100 text-emerald-800 mt-4" data-testid="badge-inviato">
                                    <CheckCircle2 className="h-3 w-3 mr-1" />
                                    Inviato il {formatDateIT(report.inviato_il)}
                                </Badge>
                            )}
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" size="sm" onClick={handleDownloadPdf} data-testid="btn-download-report">
                                <Download className="h-4 w-4 mr-1" /> Scarica PDF
                            </Button>
                            <Button size="sm" onClick={handleSendEmail} data-testid="btn-send-report">
                                <Mail className="h-4 w-4 mr-1" /> Invia al Consulente
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8 text-slate-400">Caricamento...</div>
                    ) : report?.report?.length > 0 ? (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Dipendente</TableHead>
                                    <TableHead className="text-center">Presenze</TableHead>
                                    <TableHead className="text-center">Assenze</TableHead>
                                    <TableHead className="text-center">Ferie</TableHead>
                                    <TableHead className="text-center">Permessi</TableHead>
                                    <TableHead className="text-center">Malattia</TableHead>
                                    <TableHead className="text-center">Ore</TableHead>
                                    <TableHead className="text-center">Straord.</TableHead>
                                    <TableHead className="text-right">Rimborsi</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {report.report.map(r => (
                                    <TableRow key={r.dipendente_id} data-testid={`report-row-${r.dipendente_id}`}>
                                        <TableCell className="font-medium">{r.cognome} {r.nome}</TableCell>
                                        <TableCell className="text-center">{r.conteggi.presente}</TableCell>
                                        <TableCell className="text-center">{r.conteggi.assente}</TableCell>
                                        <TableCell className="text-center">{r.conteggi.ferie}</TableCell>
                                        <TableCell className="text-center">{r.conteggi.permesso}</TableCell>
                                        <TableCell className="text-center">{r.conteggi.malattia}</TableCell>
                                        <TableCell className="text-center">{r.ore_totali}</TableCell>
                                        <TableCell className="text-center">{r.ore_straordinario}</TableCell>
                                        <TableCell className="text-right">{r.rimborsi_spese > 0 ? fmtEur(r.rimborsi_spese) : '-'}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <div className="text-center py-8 text-slate-400">Nessun dato per questo mese</div>
                    )}
                </CardContent>
            </Card>

            {/* Impostazioni invio automatico */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Settings className="h-4 w-4" /> Impostazioni Invio Automatico
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-end gap-4 flex-wrap">
                        <div>
                            <Label>Email Consulente</Label>
                            <Input
                                type="email" className="w-72"
                                value={impostazioni.report_presenze_email_consulente}
                                onChange={e => setImpostazioni(s => ({ ...s, report_presenze_email_consulente: e.target.value }))}
                                placeholder="consulente@studio.it"
                                data-testid="input-email-consulente" />
                        </div>
                        <div>
                            <Label>Giorno invio (1-28)</Label>
                            <Input
                                type="number" min={1} max={28} className="w-24"
                                value={impostazioni.report_presenze_giorno_invio}
                                onChange={e => setImpostazioni(s => ({ ...s, report_presenze_giorno_invio: parseInt(e.target.value) || 5 }))}
                                data-testid="input-giorno-invio" />
                        </div>
                        <Button onClick={handleSaveSettings} disabled={savingSettings} data-testid="btn-save-settings">
                            Salva
                        </Button>
                    </div>
                    <p className="text-xs text-slate-400 mt-2">
                        Il report del mese precedente verra inviato automaticamente il giorno {impostazioni.report_presenze_giorno_invio} di ogni mese.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
