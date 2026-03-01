/**
 * AuditPage — Gestione Audit & Non Conformità
 * Registro audit interni/esterni e NC con workflow apertura → chiusura.
 * EN 1090 / ISO 9001 compliance.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest, API_BASE } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
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
    Plus, Search, Loader2, Trash2, Pencil, ClipboardCheck,
    AlertTriangle, CheckCircle2, Clock, Shield, Download, Upload,
    X, File, Eye, XCircle, RotateCcw, CalendarDays, AlertCircle,
} from 'lucide-react';

/* ── Constants ── */
const AUDIT_TYPE_MAP = {
    interno: { label: 'Interno', color: 'bg-blue-100 text-blue-800 border-blue-200' },
    esterno_ente: { label: 'Ente Certificatore', color: 'bg-purple-100 text-purple-800 border-purple-200' },
    cliente: { label: 'Cliente', color: 'bg-teal-100 text-teal-800 border-teal-200' },
};

const OUTCOME_MAP = {
    positivo: { label: 'Positivo', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircle2 },
    negativo: { label: 'Negativo', color: 'bg-red-100 text-red-800 border-red-200', icon: XCircle },
    con_osservazioni: { label: 'Con Osservazioni', color: 'bg-amber-100 text-amber-800 border-amber-200', icon: AlertTriangle },
};

const NC_STATUS_MAP = {
    aperta: { label: 'Aperta', color: 'bg-red-100 text-red-800 border-red-200', icon: AlertCircle },
    in_lavorazione: { label: 'In Lavorazione', color: 'bg-amber-100 text-amber-800 border-amber-200', icon: Clock },
    chiusa: { label: 'Chiusa', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircle2 },
};

const NC_PRIORITY_MAP = {
    alta: { label: 'Alta', color: 'bg-red-100 text-red-700 border-red-200' },
    media: { label: 'Media', color: 'bg-amber-100 text-amber-700 border-amber-200' },
    bassa: { label: 'Bassa', color: 'bg-slate-100 text-slate-600 border-slate-200' },
};

function fmtDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

/* ═══════════════════════════════════════════════════════ */

export default function AuditPage() {
    const [activeTab, setActiveTab] = useState('audits');
    const [audits, setAudits] = useState([]);
    const [auditStats, setAuditStats] = useState({});
    const [ncs, setNcs] = useState([]);
    const [ncStats, setNcStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');

    // Audit dialogs
    const [showAuditForm, setShowAuditForm] = useState(false);
    const [editAudit, setEditAudit] = useState(null);
    const [auditForm, setAuditForm] = useState({ date: '', audit_type: 'interno', auditor_name: '', scope: '', outcome: 'positivo', notes: '', next_audit_date: '' });
    const [auditFile, setAuditFile] = useState(null);
    const [savingAudit, setSavingAudit] = useState(false);
    const [deleteAuditTarget, setDeleteAuditTarget] = useState(null);
    const [deletingAudit, setDeletingAudit] = useState(false);

    // NC dialogs
    const [showNCForm, setShowNCForm] = useState(false);
    const [ncForm, setNcForm] = useState({ date: '', description: '', source: '', priority: 'media', audit_id: '' });
    const [savingNC, setSavingNC] = useState(false);
    const [selectedNC, setSelectedNC] = useState(null);
    const [ncDetailForm, setNcDetailForm] = useState({});
    const [savingNCDetail, setSavingNCDetail] = useState(false);
    const [deleteNCTarget, setDeleteNCTarget] = useState(null);
    const [deletingNC, setDeletingNC] = useState(false);
    const [ncForAudit, setNcForAudit] = useState(null);

    /* ── Fetch ── */
    const fetchAudits = useCallback(async () => {
        try {
            const params = new URLSearchParams();
            if (searchQ.trim()) params.set('search', searchQ.trim());
            const qs = params.toString();
            const res = await apiRequest(`/audits${qs ? `?${qs}` : ''}`);
            setAudits(res.items || []);
            setAuditStats(res.stats || {});
        } catch { toast.error('Errore caricamento audit'); }
    }, [searchQ]);

    const fetchNCs = useCallback(async () => {
        try {
            const params = new URLSearchParams();
            if (searchQ.trim()) params.set('search', searchQ.trim());
            const qs = params.toString();
            const res = await apiRequest(`/ncs${qs ? `?${qs}` : ''}`);
            setNcs(res.items || []);
            setNcStats(res.stats || {});
        } catch { toast.error('Errore caricamento NC'); }
    }, [searchQ]);

    const fetchAll = useCallback(async () => {
        setLoading(true);
        await Promise.all([fetchAudits(), fetchNCs()]);
        setLoading(false);
    }, [fetchAudits, fetchNCs]);

    useEffect(() => {
        const timer = setTimeout(fetchAll, 300);
        return () => clearTimeout(timer);
    }, [fetchAll]);

    /* ── Audit CRUD ── */
    const handleSaveAudit = async () => {
        if (!auditForm.auditor_name.trim()) { toast.error('Inserisci il nome dell\'auditor'); return; }
        if (!auditForm.date) { toast.error('Inserisci la data'); return; }
        setSavingAudit(true);
        try {
            if (editAudit) {
                await apiRequest(`/audits/${editAudit.audit_id}`, { method: 'PUT', body: auditForm });
                toast.success('Audit aggiornato');
            } else {
                const fd = new FormData();
                Object.entries(auditForm).forEach(([k, v]) => fd.append(k, v || ''));
                if (auditFile) fd.append('file', auditFile);
                const res = await fetch(`${API_BASE}/audits`, { method: 'POST', credentials: 'include', body: fd });
                if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Errore'); }
                toast.success('Audit creato');
            }
            closeAuditForm();
            fetchAll();
        } catch (e) { toast.error(e.message || 'Errore'); }
        finally { setSavingAudit(false); }
    };

    const handleDeleteAudit = async () => {
        if (!deleteAuditTarget) return;
        setDeletingAudit(true);
        try {
            await apiRequest(`/audits/${deleteAuditTarget.audit_id}`, { method: 'DELETE' });
            toast.success('Audit eliminato');
            setDeleteAuditTarget(null);
            fetchAll();
        } catch (e) { toast.error(e.message); }
        finally { setDeletingAudit(false); }
    };

    const openEditAudit = (a) => {
        setEditAudit(a);
        setAuditForm({ date: a.date, audit_type: a.audit_type, auditor_name: a.auditor_name, scope: a.scope || '', outcome: a.outcome, notes: a.notes || '', next_audit_date: a.next_audit_date || '' });
        setShowAuditForm(true);
    };

    const closeAuditForm = () => {
        setShowAuditForm(false); setEditAudit(null); setAuditFile(null);
        setAuditForm({ date: '', audit_type: 'interno', auditor_name: '', scope: '', outcome: 'positivo', notes: '', next_audit_date: '' });
    };

    const handleDownloadReport = async (audit) => {
        try {
            const res = await fetch(`${API_BASE}/audits/${audit.audit_id}/report/download`, { credentials: 'include' });
            if (!res.ok) throw new Error('Errore download');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = audit.report_filename || 'report.pdf'; a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    /* ── NC CRUD ── */
    const handleSaveNC = async () => {
        if (!ncForm.description.trim()) { toast.error('Inserisci la descrizione'); return; }
        if (!ncForm.date) { toast.error('Inserisci la data'); return; }
        setSavingNC(true);
        try {
            const endpoint = ncForAudit ? `/audits/${ncForAudit}/ncs` : '/ncs';
            const body = { ...ncForm };
            if (ncForAudit) body.audit_id = ncForAudit;
            await apiRequest(endpoint, { method: 'POST', body });
            toast.success('Non conformità registrata');
            setShowNCForm(false);
            setNcForm({ date: '', description: '', source: '', priority: 'media', audit_id: '' });
            setNcForAudit(null);
            fetchAll();
        } catch (e) { toast.error(e.message || 'Errore'); }
        finally { setSavingNC(false); }
    };

    const openNCDetail = (nc) => {
        setSelectedNC(nc);
        setNcDetailForm({
            cause: nc.cause || '',
            corrective_action: nc.corrective_action || '',
            preventive_action: nc.preventive_action || '',
            notes: nc.notes || '',
            priority: nc.priority,
            status: nc.status,
        });
    };

    const handleUpdateNC = async () => {
        if (!selectedNC) return;
        setSavingNCDetail(true);
        try {
            await apiRequest(`/ncs/${selectedNC.nc_id}`, { method: 'PUT', body: ncDetailForm });
            toast.success('NC aggiornata');
            setSelectedNC(null);
            fetchAll();
        } catch (e) { toast.error(e.message); }
        finally { setSavingNCDetail(false); }
    };

    const handleCloseNC = async (nc) => {
        try {
            await apiRequest(`/ncs/${nc.nc_id}/close`, { method: 'PUT' });
            toast.success('NC chiusa');
            setSelectedNC(null);
            fetchAll();
        } catch (e) { toast.error(e.message); }
    };

    const handleReopenNC = async (nc) => {
        try {
            await apiRequest(`/ncs/${nc.nc_id}/reopen`, { method: 'PUT' });
            toast.success('NC riaperta');
            setSelectedNC(null);
            fetchAll();
        } catch (e) { toast.error(e.message); }
    };

    const handleDeleteNC = async () => {
        if (!deleteNCTarget) return;
        setDeletingNC(true);
        try {
            await apiRequest(`/ncs/${deleteNCTarget.nc_id}`, { method: 'DELETE' });
            toast.success('NC eliminata');
            setDeleteNCTarget(null);
            if (selectedNC?.nc_id === deleteNCTarget.nc_id) setSelectedNC(null);
            fetchAll();
        } catch (e) { toast.error(e.message); }
        finally { setDeletingNC(false); }
    };

    /* ═══════════════════════════════ RENDER ═══════════════════════════════ */
    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="audit-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">Audit & Miglioramento</h1>
                        <p className="text-slate-600">Registro audit e non conformità (EN 1090 / ISO 9001)</p>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="audit-stats-bar">
                    <KPICard label="NC Aperte" value={ncStats.aperte || 0} icon={AlertCircle} color="text-red-700" bg="bg-red-50" accent={ncStats.alta > 0 ? `${ncStats.alta} alta priorità` : null} />
                    <KPICard label="Audit Anno" value={auditStats.audits_this_year || 0} icon={ClipboardCheck} color="text-blue-700" bg="bg-blue-50" />
                    <KPICard label="Prossimo Audit" value={auditStats.next_audit_date ? fmtDate(auditStats.next_audit_date) : '--'} icon={CalendarDays} color="text-purple-700" bg="bg-purple-50" isText />
                    <KPICard label="NC Chiuse" value={ncStats.chiuse || 0} icon={CheckCircle2} color="text-emerald-700" bg="bg-emerald-50" />
                </div>

                {/* Tabs */}
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <div className="flex items-center justify-between">
                        <TabsList data-testid="audit-tabs">
                            <TabsTrigger value="audits" data-testid="tab-audits">Registro Audit</TabsTrigger>
                            <TabsTrigger value="ncs" data-testid="tab-ncs">Non Conformità</TabsTrigger>
                        </TabsList>
                        <div className="flex items-center gap-2">
                            <div className="relative">
                                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                                <Input data-testid="search-audit" placeholder="Cerca..." value={searchQ} onChange={e => setSearchQ(e.target.value)} className="pl-8 h-8 text-sm w-56" />
                            </div>
                            {activeTab === 'audits' ? (
                                <Button data-testid="btn-add-audit" onClick={() => setShowAuditForm(true)} className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs h-8">
                                    <Plus className="h-3.5 w-3.5 mr-1" /> Nuovo Audit
                                </Button>
                            ) : (
                                <Button data-testid="btn-add-nc" onClick={() => { setNcForAudit(null); setShowNCForm(true); }} className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs h-8">
                                    <Plus className="h-3.5 w-3.5 mr-1" /> Nuova NC
                                </Button>
                            )}
                        </div>
                    </div>

                    {/* ── AUDITS TAB ── */}
                    <TabsContent value="audits" className="mt-4">
                        <Card className="border-gray-200">
                            <CardContent className="p-0">
                                {loading ? (
                                    <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-slate-400" /></div>
                                ) : audits.length === 0 ? (
                                    <div className="text-center py-12">
                                        <ClipboardCheck className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                                        <p className="text-sm text-slate-500">Nessun audit registrato</p>
                                    </div>
                                ) : (
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="bg-[#1E293B]">
                                                <TableHead className="text-white font-semibold">Data</TableHead>
                                                <TableHead className="text-white font-semibold">Tipo</TableHead>
                                                <TableHead className="text-white font-semibold">Auditor</TableHead>
                                                <TableHead className="text-white font-semibold">Ambito</TableHead>
                                                <TableHead className="text-white font-semibold">Esito</TableHead>
                                                <TableHead className="text-white font-semibold">NC</TableHead>
                                                <TableHead className="text-white font-semibold">Report</TableHead>
                                                <TableHead className="w-[100px]"></TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {audits.map(a => {
                                                const type = AUDIT_TYPE_MAP[a.audit_type] || AUDIT_TYPE_MAP.interno;
                                                const outcome = OUTCOME_MAP[a.outcome] || OUTCOME_MAP.positivo;
                                                const OutIcon = outcome.icon;
                                                return (
                                                    <TableRow key={a.audit_id} data-testid={`audit-row-${a.audit_id}`} className="hover:bg-slate-50">
                                                        <TableCell className="font-medium text-sm">{fmtDate(a.date)}</TableCell>
                                                        <TableCell><Badge className={`${type.color} border text-[10px]`}>{type.label}</Badge></TableCell>
                                                        <TableCell className="text-sm text-slate-600">{a.auditor_name}</TableCell>
                                                        <TableCell className="text-sm text-slate-600 max-w-[200px] truncate">{a.scope || '--'}</TableCell>
                                                        <TableCell><Badge className={`${outcome.color} border text-[10px]`}><OutIcon className="h-3 w-3 mr-1" />{outcome.label}</Badge></TableCell>
                                                        <TableCell>
                                                            {a.nc_count > 0 ? (
                                                                <span className="text-sm">
                                                                    <span className="font-medium">{a.nc_count}</span>
                                                                    {a.nc_open > 0 && <span className="text-red-600 text-xs ml-1">({a.nc_open} aperte)</span>}
                                                                </span>
                                                            ) : <span className="text-xs text-slate-400">--</span>}
                                                        </TableCell>
                                                        <TableCell>
                                                            {a.has_report && (
                                                                <Button variant="ghost" size="sm" data-testid={`btn-dl-report-${a.audit_id}`} onClick={() => handleDownloadReport(a)}>
                                                                    <Download className="h-3.5 w-3.5 text-slate-500" />
                                                                </Button>
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            <div className="flex gap-0.5">
                                                                <Button variant="ghost" size="sm" data-testid={`btn-add-nc-audit-${a.audit_id}`} onClick={() => { setNcForAudit(a.audit_id); setShowNCForm(true); }} title="Aggiungi NC">
                                                                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                                                                </Button>
                                                                <Button variant="ghost" size="sm" data-testid={`btn-edit-audit-${a.audit_id}`} onClick={() => openEditAudit(a)} title="Modifica">
                                                                    <Pencil className="h-3.5 w-3.5 text-slate-500" />
                                                                </Button>
                                                                <Button variant="ghost" size="sm" data-testid={`btn-del-audit-${a.audit_id}`} onClick={() => setDeleteAuditTarget(a)} title="Elimina">
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
                    </TabsContent>

                    {/* ── NC TAB ── */}
                    <TabsContent value="ncs" className="mt-4">
                        <Card className="border-gray-200">
                            <CardContent className="p-0">
                                {loading ? (
                                    <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-slate-400" /></div>
                                ) : ncs.length === 0 ? (
                                    <div className="text-center py-12">
                                        <Shield className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                                        <p className="text-sm text-slate-500">Nessuna non conformità registrata</p>
                                    </div>
                                ) : (
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="bg-[#1E293B]">
                                                <TableHead className="text-white font-semibold">N.</TableHead>
                                                <TableHead className="text-white font-semibold">Data</TableHead>
                                                <TableHead className="text-white font-semibold">Descrizione</TableHead>
                                                <TableHead className="text-white font-semibold">Origine</TableHead>
                                                <TableHead className="text-white font-semibold">Priorità</TableHead>
                                                <TableHead className="text-white font-semibold">Stato</TableHead>
                                                <TableHead className="text-white font-semibold">Giorni</TableHead>
                                                <TableHead className="w-[120px]"></TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {ncs.map(nc => {
                                                const st = NC_STATUS_MAP[nc.status] || NC_STATUS_MAP.aperta;
                                                const pr = NC_PRIORITY_MAP[nc.priority] || NC_PRIORITY_MAP.media;
                                                const StIcon = st.icon;
                                                const isOpen = nc.status !== 'chiusa';
                                                return (
                                                    <TableRow
                                                        key={nc.nc_id}
                                                        data-testid={`nc-row-${nc.nc_id}`}
                                                        className={`cursor-pointer ${nc.status === 'aperta' && nc.priority === 'alta' ? 'bg-red-50/50' : nc.status === 'chiusa' ? 'bg-emerald-50/30' : 'hover:bg-slate-50'}`}
                                                        onClick={() => openNCDetail(nc)}
                                                    >
                                                        <TableCell className="font-mono text-xs font-medium text-slate-600">{nc.nc_number}</TableCell>
                                                        <TableCell className="text-sm">{fmtDate(nc.date)}</TableCell>
                                                        <TableCell className="text-sm text-slate-700 max-w-[300px] truncate">{nc.description}</TableCell>
                                                        <TableCell className="text-xs text-slate-500">{nc.source || nc.audit_ref || '--'}</TableCell>
                                                        <TableCell><Badge className={`${pr.color} border text-[10px]`}>{pr.label}</Badge></TableCell>
                                                        <TableCell><Badge className={`${st.color} border text-[10px]`}><StIcon className="h-3 w-3 mr-1" />{st.label}</Badge></TableCell>
                                                        <TableCell>
                                                            {nc.days_open !== null && nc.days_open !== undefined ? (
                                                                <span className={`text-xs font-medium ${isOpen && nc.days_open > 30 ? 'text-red-600' : isOpen ? 'text-amber-600' : 'text-slate-500'}`}>
                                                                    {nc.days_open}gg
                                                                </span>
                                                            ) : '--'}
                                                        </TableCell>
                                                        <TableCell>
                                                            <div className="flex gap-0.5" onClick={e => e.stopPropagation()}>
                                                                {isOpen && (
                                                                    <Button variant="ghost" size="sm" data-testid={`btn-close-nc-${nc.nc_id}`} onClick={() => handleCloseNC(nc)} title="Chiudi NC">
                                                                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                                                                    </Button>
                                                                )}
                                                                {!isOpen && (
                                                                    <Button variant="ghost" size="sm" data-testid={`btn-reopen-nc-${nc.nc_id}`} onClick={() => handleReopenNC(nc)} title="Riapri NC">
                                                                        <RotateCcw className="h-3.5 w-3.5 text-amber-500" />
                                                                    </Button>
                                                                )}
                                                                <Button variant="ghost" size="sm" data-testid={`btn-view-nc-${nc.nc_id}`} onClick={() => openNCDetail(nc)} title="Dettaglio">
                                                                    <Eye className="h-3.5 w-3.5 text-slate-500" />
                                                                </Button>
                                                                <Button variant="ghost" size="sm" data-testid={`btn-del-nc-${nc.nc_id}`} onClick={() => setDeleteNCTarget(nc)} title="Elimina">
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
                    </TabsContent>
                </Tabs>
            </div>

            {/* ══════ Audit Form Dialog ══════ */}
            <Dialog open={showAuditForm} onOpenChange={v => { if (!v) closeAuditForm(); else setShowAuditForm(true); }}>
                <DialogContent className="max-w-lg" data-testid="audit-form-dialog">
                    <DialogHeader>
                        <DialogTitle>{editAudit ? 'Modifica Audit' : 'Nuovo Audit'}</DialogTitle>
                        <DialogDescription>Registra un audit interno o esterno.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 mt-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Data Audit *</Label>
                                <Input data-testid="input-audit-date" type="date" value={auditForm.date} onChange={e => setAuditForm(f => ({ ...f, date: e.target.value }))} className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Tipo Audit</Label>
                                <Select value={auditForm.audit_type} onValueChange={v => setAuditForm(f => ({ ...f, audit_type: v }))}>
                                    <SelectTrigger data-testid="select-audit-type" className="mt-1"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="interno">Interno</SelectItem>
                                        <SelectItem value="esterno_ente">Ente Certificatore</SelectItem>
                                        <SelectItem value="cliente">Cliente</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Nome Auditor *</Label>
                                <Input data-testid="input-audit-auditor" value={auditForm.auditor_name} onChange={e => setAuditForm(f => ({ ...f, auditor_name: e.target.value }))} placeholder="Mario Rossi" className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Esito</Label>
                                <Select value={auditForm.outcome} onValueChange={v => setAuditForm(f => ({ ...f, outcome: v }))}>
                                    <SelectTrigger data-testid="select-audit-outcome" className="mt-1"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="positivo">Positivo</SelectItem>
                                        <SelectItem value="negativo">Negativo</SelectItem>
                                        <SelectItem value="con_osservazioni">Con Osservazioni</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Ambito / Scope</Label>
                            <Input data-testid="input-audit-scope" value={auditForm.scope} onChange={e => setAuditForm(f => ({ ...f, scope: e.target.value }))} placeholder="Es. Processo di saldatura, Controllo materiali" className="mt-1" />
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Prossimo Audit Programmato</Label>
                            <Input data-testid="input-audit-next" type="date" value={auditForm.next_audit_date} onChange={e => setAuditForm(f => ({ ...f, next_audit_date: e.target.value }))} className="mt-1" />
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Note</Label>
                            <Input data-testid="input-audit-notes" value={auditForm.notes} onChange={e => setAuditForm(f => ({ ...f, notes: e.target.value }))} placeholder="Osservazioni aggiuntive" className="mt-1" />
                        </div>
                        {/* File upload - only for new audits */}
                        {!editAudit && (
                            <div>
                                <Label className="text-xs font-medium">PDF Verbale</Label>
                                <div
                                    className={`mt-1 border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${auditFile ? 'border-[#0055FF] bg-blue-50/40' : 'border-slate-200 hover:border-slate-300'}`}
                                    onClick={() => document.getElementById('audit-file-input')?.click()}
                                    data-testid="audit-drop-zone"
                                >
                                    <input id="audit-file-input" type="file" accept=".pdf,.jpg,.jpeg,.png,.docx" className="hidden" onChange={e => { if (e.target.files?.[0]) setAuditFile(e.target.files[0]); }} />
                                    {auditFile ? (
                                        <div className="flex items-center justify-center gap-2">
                                            <File className="h-4 w-4 text-[#0055FF]" />
                                            <span className="text-sm text-slate-900 truncate max-w-[200px]">{auditFile.name}</span>
                                            <button onClick={e => { e.stopPropagation(); setAuditFile(null); }}><X className="h-4 w-4 text-slate-400 hover:text-red-500" /></button>
                                        </div>
                                    ) : (
                                        <p className="text-sm text-slate-500"><Upload className="h-4 w-4 inline mr-1" />Carica verbale audit</p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={closeAuditForm}>Annulla</Button>
                        <Button data-testid="btn-save-audit" onClick={handleSaveAudit} disabled={savingAudit} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {savingAudit && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            {editAudit ? 'Salva' : 'Crea Audit'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ NC Form Dialog ══════ */}
            <Dialog open={showNCForm} onOpenChange={v => { if (!v) { setShowNCForm(false); setNcForAudit(null); } }}>
                <DialogContent className="max-w-md" data-testid="nc-form-dialog">
                    <DialogHeader>
                        <DialogTitle>Nuova Non Conformità</DialogTitle>
                        <DialogDescription>
                            {ncForAudit ? 'Registra una NC emersa durante l\'audit.' : 'Registra una non conformità (reclamo, errore, difetto).'}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 mt-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs font-medium">Data *</Label>
                                <Input data-testid="input-nc-date" type="date" value={ncForm.date} onChange={e => setNcForm(f => ({ ...f, date: e.target.value }))} className="mt-1" />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Priorità</Label>
                                <Select value={ncForm.priority} onValueChange={v => setNcForm(f => ({ ...f, priority: v }))}>
                                    <SelectTrigger data-testid="select-nc-priority" className="mt-1"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="alta">Alta</SelectItem>
                                        <SelectItem value="media">Media</SelectItem>
                                        <SelectItem value="bassa">Bassa</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Descrizione *</Label>
                            <textarea
                                data-testid="input-nc-description"
                                value={ncForm.description}
                                onChange={e => setNcForm(f => ({ ...f, description: e.target.value }))}
                                placeholder="Descrivi la non conformità rilevata..."
                                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Origine / Fonte</Label>
                            <Input data-testid="input-nc-source" value={ncForm.source} onChange={e => setNcForm(f => ({ ...f, source: e.target.value }))} placeholder="Es. Reclamo cliente, Controllo interno, Audit" className="mt-1" />
                        </div>
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => { setShowNCForm(false); setNcForAudit(null); }}>Annulla</Button>
                        <Button data-testid="btn-save-nc" onClick={handleSaveNC} disabled={savingNC} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {savingNC && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            Registra NC
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ NC Detail Dialog ══════ */}
            <Dialog open={!!selectedNC} onOpenChange={v => { if (!v) setSelectedNC(null); }}>
                <DialogContent className="max-w-2xl" data-testid="nc-detail-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <span className="font-mono text-sm text-slate-500">{selectedNC?.nc_number}</span>
                            Dettaglio Non Conformità
                            {selectedNC && <Badge className={`${NC_STATUS_MAP[selectedNC.status]?.color || ''} border text-[10px] ml-2`}>{NC_STATUS_MAP[selectedNC.status]?.label}</Badge>}
                        </DialogTitle>
                        <DialogDescription>Analisi causa, azione correttiva e preventiva.</DialogDescription>
                    </DialogHeader>
                    {selectedNC && (
                        <div className="space-y-3 mt-2">
                            <div className="bg-slate-50 rounded-lg p-3">
                                <p className="text-sm font-medium text-slate-800">{selectedNC.description}</p>
                                <div className="flex gap-3 mt-2 text-xs text-slate-500">
                                    <span>Data: {fmtDate(selectedNC.date)}</span>
                                    {selectedNC.source && <span>Origine: {selectedNC.source}</span>}
                                    {selectedNC.audit_ref && <span>Audit: {selectedNC.audit_ref}</span>}
                                    <span>Giorni: {selectedNC.days_open ?? '--'}</span>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Label className="text-xs font-medium">Priorità</Label>
                                    <Select value={ncDetailForm.priority} onValueChange={v => setNcDetailForm(f => ({ ...f, priority: v }))}>
                                        <SelectTrigger data-testid="select-nc-detail-priority" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="alta">Alta</SelectItem>
                                            <SelectItem value="media">Media</SelectItem>
                                            <SelectItem value="bassa">Bassa</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs font-medium">Stato</Label>
                                    <Select value={ncDetailForm.status} onValueChange={v => setNcDetailForm(f => ({ ...f, status: v }))}>
                                        <SelectTrigger data-testid="select-nc-detail-status" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="aperta">Aperta</SelectItem>
                                            <SelectItem value="in_lavorazione">In Lavorazione</SelectItem>
                                            <SelectItem value="chiusa">Chiusa</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Causa (Root Cause Analysis)</Label>
                                <textarea
                                    data-testid="input-nc-cause"
                                    value={ncDetailForm.cause}
                                    onChange={e => setNcDetailForm(f => ({ ...f, cause: e.target.value }))}
                                    placeholder="Perché è successo? Analizza la causa radice..."
                                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px] focus:outline-none focus:ring-2 focus:ring-ring"
                                />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Azione Correttiva</Label>
                                <textarea
                                    data-testid="input-nc-corrective"
                                    value={ncDetailForm.corrective_action}
                                    onChange={e => setNcDetailForm(f => ({ ...f, corrective_action: e.target.value }))}
                                    placeholder="Cosa facciamo per risolvere il problema..."
                                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px] focus:outline-none focus:ring-2 focus:ring-ring"
                                />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Azione Preventiva</Label>
                                <textarea
                                    data-testid="input-nc-preventive"
                                    value={ncDetailForm.preventive_action}
                                    onChange={e => setNcDetailForm(f => ({ ...f, preventive_action: e.target.value }))}
                                    placeholder="Come evitiamo che si ripeta..."
                                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px] focus:outline-none focus:ring-2 focus:ring-ring"
                                />
                            </div>
                            <div>
                                <Label className="text-xs font-medium">Note</Label>
                                <Input data-testid="input-nc-notes" value={ncDetailForm.notes} onChange={e => setNcDetailForm(f => ({ ...f, notes: e.target.value }))} placeholder="Note aggiuntive" className="mt-1" />
                            </div>
                            {selectedNC.closure_date && (
                                <div className="bg-emerald-50 rounded-lg p-2 text-xs text-emerald-700">
                                    Chiusa il {fmtDate(selectedNC.closure_date)} da {selectedNC.closed_by || '--'}
                                </div>
                            )}
                        </div>
                    )}
                    <DialogFooter className="mt-4">
                        <div className="flex gap-2 w-full justify-between">
                            <Button variant="outline" size="sm" className="text-red-500" data-testid="btn-delete-nc-detail" onClick={() => { setDeleteNCTarget(selectedNC); setSelectedNC(null); }}>
                                <Trash2 className="h-3.5 w-3.5 mr-1" /> Elimina
                            </Button>
                            <div className="flex gap-2">
                                {selectedNC?.status !== 'chiusa' && (
                                    <Button variant="outline" size="sm" data-testid="btn-close-nc-detail" onClick={() => handleCloseNC(selectedNC)} className="text-emerald-600 border-emerald-200 hover:bg-emerald-50">
                                        <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Chiudi NC
                                    </Button>
                                )}
                                {selectedNC?.status === 'chiusa' && (
                                    <Button variant="outline" size="sm" data-testid="btn-reopen-nc-detail" onClick={() => handleReopenNC(selectedNC)} className="text-amber-600 border-amber-200 hover:bg-amber-50">
                                        <RotateCcw className="h-3.5 w-3.5 mr-1" /> Riapri
                                    </Button>
                                )}
                                <Button data-testid="btn-save-nc-detail" onClick={handleUpdateNC} disabled={savingNCDetail} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                                    {savingNCDetail && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                                    Salva Modifiche
                                </Button>
                            </div>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Delete Audit Dialog ══════ */}
            <Dialog open={!!deleteAuditTarget} onOpenChange={v => { if (!v) setDeleteAuditTarget(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-audit-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Audit</DialogTitle>
                        <DialogDescription>Le NC collegate non saranno eliminate ma scollegate.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">Eliminare l'audit del <strong>{fmtDate(deleteAuditTarget?.date)}</strong> ({deleteAuditTarget?.auditor_name})?</p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteAuditTarget(null)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete-audit" onClick={handleDeleteAudit} disabled={deletingAudit} variant="destructive">
                            {deletingAudit ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />} Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Delete NC Dialog ══════ */}
            <Dialog open={!!deleteNCTarget} onOpenChange={v => { if (!v) setDeleteNCTarget(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-nc-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Non Conformità</DialogTitle>
                        <DialogDescription>Questa azione non può essere annullata.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">Eliminare la NC <strong>{deleteNCTarget?.nc_number}</strong>?</p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteNCTarget(null)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete-nc" onClick={handleDeleteNC} disabled={deletingNC} variant="destructive">
                            {deletingNC ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />} Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}

/* ── Sub-components ── */
function KPICard({ label, value, icon: Icon, color, bg, accent, isText }) {
    return (
        <Card className="border-gray-200">
            <CardContent className="pt-4 pb-3 px-4">
                <div className="flex items-center gap-2.5">
                    <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
                        <Icon className={`h-4.5 w-4.5 ${color}`} />
                    </div>
                    <div>
                        <p className={`${isText ? 'text-sm' : 'text-xl'} font-bold ${color}`}>{value}</p>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                        {accent && <p className="text-[9px] text-red-500 font-medium">{accent}</p>}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
