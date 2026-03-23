import { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import {
    FileInput, Upload, Package, CheckCircle2, AlertTriangle, XCircle,
    Clock, Shield, Eye, Loader2, Plus, Search, RefreshCw,
    Send, Mail, ArrowLeft, Paperclip, History, ChevronRight,
    AlertCircle, ShieldAlert, FileText, UserCheck, Save, Trash2, Play,
    Edit, Info,
} from 'lucide-react';

const STATUS_CONFIG = {
    attached: { label: 'Presente', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
    missing: { label: 'Mancante', color: 'bg-red-100 text-red-800', icon: XCircle },
    expired: { label: 'Scaduto', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
    in_scadenza: { label: 'In scadenza', color: 'bg-amber-100 text-amber-800', icon: Clock },
    pending: { label: 'Da verificare', color: 'bg-gray-100 text-gray-600', icon: Clock },
    valido: { label: 'Valido', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
    scaduto: { label: 'Scaduto', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
    non_verificato: { label: 'Non verificato', color: 'bg-gray-100 text-gray-600', icon: Eye },
};

const PACK_STATUS_CONFIG = {
    draft: { label: 'Bozza', color: 'bg-gray-100 text-gray-600' },
    in_preparazione: { label: 'In preparazione', color: 'bg-blue-100 text-blue-700' },
    pronto_invio: { label: 'Pronto invio', color: 'bg-emerald-100 text-emerald-800' },
    inviato: { label: 'Inviato', color: 'bg-violet-100 text-violet-800' },
    incompleto: { label: 'Incompleto', color: 'bg-amber-100 text-amber-800' },
    annullato: { label: 'Annullato', color: 'bg-red-100 text-red-700' },
};

const PRIVACY_BADGE = {
    cliente_condivisibile: 'bg-blue-50 text-blue-700',
    interno: 'bg-gray-100 text-gray-600',
    riservato: 'bg-amber-50 text-amber-700',
    sensibile: 'bg-red-50 text-red-700',
};

const ENTITY_LABELS = { azienda: 'Azienda', persona: 'Persona', mezzo: 'Mezzo', cantiere: 'Cantiere' };

// ── Upload Form ──
function UploadForm({ tipiDoc, onUploaded }) {
    const [form, setForm] = useState({ document_type_code: '', entity_type: 'azienda', owner_label: '', title: '', issue_date: '', expiry_date: '', privacy_level: 'cliente_condivisibile', verified: false });
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);

    const handleUpload = async () => {
        if (!form.document_type_code) { toast.error('Seleziona il tipo documento'); return; }
        setUploading(true);
        try {
            const fd = new FormData();
            Object.entries(form).forEach(([k, v]) => fd.append(k, v));
            if (file) fd.append('file', file);
            const API = process.env.REACT_APP_BACKEND_URL;
            const res = await fetch(`${API}/api/documenti`, { method: 'POST', body: fd, credentials: 'include' });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Errore upload');
            const doc = await res.json();
            toast.success(`Documento caricato: ${doc.title}`);
            setForm(f => ({ ...f, title: '', issue_date: '', expiry_date: '', owner_label: '' }));
            setFile(null);
            onUploaded?.();
        } catch (err) { toast.error(err.message); }
        finally { setUploading(false); }
    };

    const selectedTipo = tipiDoc.find(t => t.code === form.document_type_code);

    return (
        <Card className="border-dashed border-2 border-blue-200" data-testid="upload-form">
            <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2"><Upload className="h-4 w-4" /> Carica Documento</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <Label className="text-xs">Tipo documento *</Label>
                        <Select value={form.document_type_code} onValueChange={v => { const t = tipiDoc.find(x => x.code === v); setForm(f => ({ ...f, document_type_code: v, entity_type: t?.entity_type || 'azienda', privacy_level: t?.privacy_level || 'cliente_condivisibile' })); }}>
                            <SelectTrigger data-testid="select-tipo-doc"><SelectValue placeholder="Seleziona tipo..." /></SelectTrigger>
                            <SelectContent>{tipiDoc.map(t => <SelectItem key={t.code} value={t.code}>{t.label} ({ENTITY_LABELS[t.entity_type]})</SelectItem>)}</SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label className="text-xs">Intestatario</Label>
                        <Input placeholder="Nome / Azienda" value={form.owner_label} onChange={e => setForm(f => ({ ...f, owner_label: e.target.value }))} data-testid="input-owner" />
                    </div>
                    <div>
                        <Label className="text-xs">Titolo</Label>
                        <Input placeholder="Titolo documento" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} data-testid="input-title" />
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <div>
                        <Label className="text-xs">Data emissione</Label>
                        <Input type="date" value={form.issue_date} onChange={e => setForm(f => ({ ...f, issue_date: e.target.value }))} data-testid="input-issue-date" />
                    </div>
                    <div>
                        <Label className="text-xs">Data scadenza</Label>
                        <Input type="date" value={form.expiry_date} onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} data-testid="input-expiry-date" />
                    </div>
                    <div>
                        <Label className="text-xs">File</Label>
                        <Input type="file" onChange={e => setFile(e.target.files?.[0] || null)} data-testid="input-file" />
                    </div>
                    <div className="flex items-end">
                        <Button onClick={handleUpload} disabled={uploading} className="bg-[#0055FF] text-white hover:bg-[#0044CC] w-full" data-testid="btn-upload">
                            {uploading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                            Carica
                        </Button>
                    </div>
                </div>
                {selectedTipo && (
                    <div className="flex gap-2 text-xs">
                        <Badge className={PRIVACY_BADGE[selectedTipo.privacy_level] || ''}>{selectedTipo.privacy_level}</Badge>
                        {selectedTipo.has_expiry && <Badge variant="outline">Scade ogni {selectedTipo.validity_days}gg</Badge>}
                        <Badge variant="outline">{ENTITY_LABELS[selectedTipo.entity_type]}</Badge>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ── Document List ──
function DocumentList({ documenti, tipiMap }) {
    if (!documenti.length) return <p className="text-sm text-slate-400 py-8 text-center">Nessun documento in archivio. Carica il primo documento sopra.</p>;
    return (
        <div className="space-y-2" data-testid="documenti-list">
            {documenti.map(d => {
                const sc = STATUS_CONFIG[d.status] || STATUS_CONFIG.pending;
                const Icon = sc.icon;
                const tipo = tipiMap[d.document_type_code];
                return (
                    <div key={d.doc_id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 bg-white hover:border-blue-200 transition-colors" data-testid={`doc-${d.doc_id}`}>
                        <Icon className={`h-4 w-4 flex-shrink-0 ${d.status === 'valido' || d.status === 'attached' ? 'text-emerald-600' : d.status === 'scaduto' || d.status === 'expired' ? 'text-red-500' : 'text-amber-500'}`} />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{d.title || d.file_name || d.document_type_code}</p>
                            <p className="text-xs text-slate-400">{tipo?.label || d.document_type_code} {d.owner_label ? `- ${d.owner_label}` : ''}</p>
                        </div>
                        <Badge className={`text-[10px] ${sc.color}`}>{sc.label}</Badge>
                        {d.expiry_date && <span className="text-xs text-slate-400">{d.expiry_date.slice(0, 10)}</span>}
                        <Badge className={`text-[10px] ${PRIVACY_BADGE[d.privacy_level] || ''}`}>{d.privacy_level}</Badge>
                    </div>
                );
            })}
        </div>
    );
}

// ── Package Card (list view) ──
function PackageCard({ pack, tipiMap, onVerifica, onOpen }) {
    const s = pack.summary || {};
    const ps = PACK_STATUS_CONFIG[pack.status] || PACK_STATUS_CONFIG.draft;
    const borderColor = pack.status === 'pronto_invio' ? 'border-emerald-300 bg-emerald-50/30'
        : pack.status === 'inviato' ? 'border-violet-300 bg-violet-50/30'
        : pack.status === 'incompleto' ? 'border-amber-300 bg-amber-50/30'
        : 'border-gray-200';

    return (
        <Card className={`${borderColor} cursor-pointer hover:shadow-md transition-shadow`} data-testid={`pack-${pack.pack_id}`} onClick={() => onOpen(pack.pack_id)}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Package className="h-4 w-4" />
                        {pack.label || pack.template_code}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Badge className={ps.color}>{ps.label}</Badge>
                        <Button size="sm" variant="outline" onClick={e => { e.stopPropagation(); onVerifica(pack.pack_id); }} data-testid={`btn-verifica-${pack.pack_id}`}>
                            <RefreshCw className="h-3 w-3 mr-1" /> Verifica
                        </Button>
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                    </div>
                </div>
                {s.total_required > 0 && (
                    <div className="flex gap-3 text-xs mt-2">
                        <span className="text-emerald-700">{s.attached} presenti</span>
                        <span className="text-red-700">{s.missing} mancanti</span>
                        <span className="text-red-600">{s.expired} scaduti</span>
                        <span className="text-amber-600">{s.in_scadenza} in scadenza</span>
                        {s.sensibile > 0 && <span className="text-red-500">{s.sensibile} sensibili</span>}
                    </div>
                )}
            </CardHeader>
        </Card>
    );
}

// ── Package Detail View (D4+D5) ──
function PackageDetailView({ packId, tipiMap, onBack }) {
    const [pack, setPack] = useState(null);
    const [preview, setPreview] = useState(null);
    const [invii, setInvii] = useState([]);
    const [loading, setLoading] = useState(true);
    const [preparing, setPreparing] = useState(false);
    const [sending, setSending] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    // Editable email fields
    const [emailTo, setEmailTo] = useState('');
    const [emailCc, setEmailCc] = useState('');
    const [emailSubject, setEmailSubject] = useState('');
    const [emailBody, setEmailBody] = useState('');

    const loadDetail = useCallback(async () => {
        setLoading(true);
        try {
            const [p, hist] = await Promise.all([
                apiRequest(`/pacchetti-documentali/${packId}`),
                apiRequest(`/pacchetti-documentali/${packId}/invii`),
            ]);
            setPack(p);
            setInvii(hist);
            // Pre-fill recipient from pack
            const r = p.recipient || {};
            setEmailTo((r.to || []).join(', '));
            setEmailCc((r.cc || []).join(', '));
        } catch (err) { toast.error('Errore caricamento pacchetto'); }
        finally { setLoading(false); }
    }, [packId]);

    useEffect(() => { loadDetail(); }, [loadDetail]);

    const handlePrepare = async () => {
        setPreparing(true);
        try {
            const result = await apiRequest(`/pacchetti-documentali/${packId}/prepara-invio`, { method: 'POST' });
            setPreview(result);
            setPack(prev => ({ ...prev, status: result.pack_status, summary: result.summary, items: result.items || prev?.items }));
            setEmailSubject(result.email_draft?.subject || '');
            setEmailBody(result.email_draft?.body || '');
            // Update recipient if empty
            if (!emailTo && result.recipient?.to?.length) {
                setEmailTo(result.recipient.to.join(', '));
            }
            if (!emailCc && result.recipient?.cc?.length) {
                setEmailCc(result.recipient.cc.join(', '));
            }
            toast.success('Preview email preparata');
        } catch (err) { toast.error(err.message || 'Errore preparazione'); }
        finally { setPreparing(false); }
    };

    const handleSend = async () => {
        setShowConfirm(false);
        const toList = emailTo.split(',').map(e => e.trim()).filter(Boolean);
        const ccList = emailCc.split(',').map(e => e.trim()).filter(Boolean);
        if (!toList.length) { toast.error('Inserisci almeno un destinatario'); return; }
        if (!emailSubject) { toast.error('Inserisci l\'oggetto dell\'email'); return; }

        // Save recipient to pack first
        await apiRequest(`/pacchetti-documentali/${packId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient: { to: toList, cc: ccList } }),
        }).catch(() => {});

        setSending(true);
        try {
            const result = await apiRequest(`/pacchetti-documentali/${packId}/invia`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ to: toList, cc: ccList, subject: emailSubject, body: emailBody }),
            });
            if (result.success) {
                toast.success('Email inviata con successo!');
                setPack(prev => ({ ...prev, status: 'inviato' }));
                setInvii(prev => [result.send_log, ...prev]);
            } else {
                toast.error('Invio fallito. Controlla i log.');
                if (result.send_log) setInvii(prev => [result.send_log, ...prev]);
            }
        } catch (err) { toast.error(err.message || 'Errore invio email'); }
        finally { setSending(false); }
    };

    if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" /></div>;
    if (!pack) return <p className="text-center text-slate-400 py-8">Pacchetto non trovato</p>;

    const s = pack.summary || {};
    const ps = PACK_STATUS_CONFIG[pack.status] || PACK_STATUS_CONFIG.draft;
    const hasWarnings = preview?.warnings?.length > 0;
    const hasSensitive = (preview?.attachments || []).some(a => a.privacy_level === 'sensibile');

    return (
        <div className="space-y-5" data-testid="pack-detail-view">
            {/* Header */}
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={onBack} data-testid="btn-back-to-list">
                    <ArrowLeft className="h-4 w-4 mr-1" /> Lista
                </Button>
                <div className="flex-1">
                    <h2 className="text-lg font-bold text-slate-900">{pack.label || pack.template_code}</h2>
                    <p className="text-xs text-slate-400">ID: {pack.pack_id}</p>
                </div>
                <Badge className={ps.color}>{ps.label}</Badge>
                <SaveAsProfileButton packId={packId} />
            </div>

            {/* Summary bar */}
            {s.total_required > 0 && (
                <div className="flex gap-4 text-sm p-3 rounded-lg bg-slate-50 border">
                    <span className="text-emerald-700 font-medium">{s.attached} presenti</span>
                    <span className="text-red-700 font-medium">{s.missing} mancanti</span>
                    <span className="text-red-600 font-medium">{s.expired} scaduti</span>
                    <span className="text-amber-600 font-medium">{s.in_scadenza} in scadenza</span>
                    {s.sensibile > 0 && <span className="text-red-500 font-medium">{s.sensibile} sensibili</span>}
                </div>
            )}

            {/* Checklist items */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2"><FileText className="h-4 w-4" /> Checklist Documenti</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-1">
                        {(pack.items || []).map((item, i) => {
                            const sc = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
                            const Icon = sc.icon;
                            const tipo = tipiMap[item.document_type_code];
                            return (
                                <div key={i} className={`flex items-center gap-2 p-2 rounded text-sm ${item.blocking ? 'bg-red-50' : ''}`} data-testid={`item-${i}`}>
                                    <Icon className={`h-3.5 w-3.5 flex-shrink-0 ${item.status === 'attached' ? 'text-emerald-600' : item.status === 'missing' || item.status === 'expired' ? 'text-red-500' : 'text-amber-500'}`} />
                                    <span className="flex-1">{tipo?.label || item.document_type_code}
                                        {item.entity_label ? <span className="text-slate-400 ml-1">({item.entity_label})</span> : ''}
                                    </span>
                                    <Badge className={`text-[10px] ${sc.color}`}>{sc.label}</Badge>
                                    {item.required && <Badge className="text-[10px] bg-blue-50 text-blue-700">obb.</Badge>}
                                    {item.blocking && <Badge className="text-[10px] bg-red-50 text-red-700">blocco</Badge>}
                                    {item.document_title && <span className="text-xs text-slate-400 truncate max-w-[150px]">{item.document_title}</span>}
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* D4: Prepara Invio */}
            <Card className="border-blue-200">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm flex items-center gap-2"><Mail className="h-4 w-4" /> Prepara e Invia Email</CardTitle>
                        <Button size="sm" onClick={handlePrepare} disabled={preparing} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-prepara-invio">
                            {preparing ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCw className="h-3 w-3 mr-1" />}
                            Prepara Invio
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Recipient fields */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                            <Label className="text-xs">Destinatari (To) *</Label>
                            <Input placeholder="email@cliente.it, altro@cliente.it" value={emailTo} onChange={e => setEmailTo(e.target.value)} data-testid="input-email-to" />
                        </div>
                        <div>
                            <Label className="text-xs">CC</Label>
                            <Input placeholder="cc@cliente.it" value={emailCc} onChange={e => setEmailCc(e.target.value)} data-testid="input-email-cc" />
                        </div>
                    </div>

                    {/* Subject + Body (show after prepare) */}
                    {preview && (
                        <>
                            <div>
                                <Label className="text-xs">Oggetto</Label>
                                <Input value={emailSubject} onChange={e => setEmailSubject(e.target.value)} data-testid="input-email-subject" />
                            </div>
                            <div>
                                <Label className="text-xs">Testo email</Label>
                                <Textarea rows={6} value={emailBody} onChange={e => setEmailBody(e.target.value)} className="text-sm" data-testid="input-email-body" />
                            </div>

                            {/* Attachments list */}
                            {preview.attachments?.length > 0 && (
                                <div>
                                    <Label className="text-xs mb-2 block">Allegati ({preview.attachments.length})</Label>
                                    <div className="space-y-1 max-h-40 overflow-y-auto">
                                        {preview.attachments.map((att, i) => (
                                            <div key={i} className="flex items-center gap-2 p-2 rounded bg-slate-50 text-sm">
                                                <Paperclip className="h-3.5 w-3.5 text-slate-400" />
                                                <span className="flex-1 truncate">{att.file_name || att.title}</span>
                                                <Badge className={`text-[10px] ${PRIVACY_BADGE[att.privacy_level] || ''}`}>{att.privacy_level}</Badge>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Warnings */}
                            {hasWarnings && (
                                <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 space-y-1" data-testid="warnings-box">
                                    <div className="flex items-center gap-2 text-amber-800 font-medium text-sm">
                                        <AlertCircle className="h-4 w-4" /> Attenzione
                                    </div>
                                    {preview.warnings.map((w, i) => (
                                        <p key={i} className="text-xs text-amber-700 pl-6">{w}</p>
                                    ))}
                                </div>
                            )}

                            {hasSensitive && (
                                <div className="p-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2" data-testid="sensitive-warning">
                                    <ShieldAlert className="h-4 w-4 text-red-600" />
                                    <p className="text-xs text-red-700">Stai per inviare documenti contrassegnati come <strong>sensibili</strong>. Verifica che i destinatari siano autorizzati.</p>
                                </div>
                            )}

                            <Separator />

                            {/* Send button */}
                            <div className="flex justify-end">
                                <Button
                                    onClick={() => setShowConfirm(true)}
                                    disabled={sending || !emailTo.trim()}
                                    className="bg-emerald-600 text-white hover:bg-emerald-700"
                                    data-testid="btn-invia-email"
                                >
                                    {sending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                                    Invia Email
                                </Button>
                            </div>
                        </>
                    )}

                    {!preview && (
                        <p className="text-xs text-slate-400 text-center py-2">Clicca "Prepara Invio" per generare la preview dell'email con l'elenco allegati.</p>
                    )}
                </CardContent>
            </Card>

            {/* Send History */}
            {invii.length > 0 && (
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center gap-2"><History className="h-4 w-4" /> Storico Invii ({invii.length})</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {invii.map((inv, i) => (
                                <div key={inv.send_id || i} className="flex items-center gap-3 p-2 rounded bg-slate-50 text-sm" data-testid={`invio-${inv.send_id}`}>
                                    {inv.status === 'sent'
                                        ? <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                        : <XCircle className="h-4 w-4 text-red-500" />
                                    }
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium truncate">{inv.subject}</p>
                                        <p className="text-[11px] text-slate-400">A: {(inv.email_to || []).join(', ')}</p>
                                    </div>
                                    <Badge className={inv.status === 'sent' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}>
                                        {inv.status === 'sent' ? 'Inviato' : 'Fallito'}
                                    </Badge>
                                    <span className="text-[11px] text-slate-400">{inv.attachment_count} allegati</span>
                                    <span className="text-[11px] text-slate-400">{inv.sent_at ? new Date(inv.sent_at).toLocaleString('it-IT') : ''}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Confirm dialog */}
            <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
                <DialogContent data-testid="confirm-send-dialog">
                    <DialogHeader>
                        <DialogTitle>Conferma invio email</DialogTitle>
                        <DialogDescription>
                            Stai per inviare {preview?.attachments?.length || 0} allegati a {emailTo}.
                            {hasWarnings && <span className="block mt-1 text-amber-600">Ci sono avvertimenti attivi. Sei sicuro?</span>}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" onClick={() => setShowConfirm(false)} data-testid="btn-cancel-send">Annulla</Button>
                        <Button onClick={handleSend} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-confirm-send">
                            <Send className="h-4 w-4 mr-2" /> Conferma Invio
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

// ── Profile Management (D6) ──
function ProfiliTab({ tipiDoc, onProfileApplied }) {
    const [profili, setProfili] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(null); // profile_id or 'new'
    const [form, setForm] = useState({ client_name: '', description: '', notes: '', warnings: [], rules: [] });
    const [saving, setSaving] = useState(false);
    const [applyDialog, setApplyDialog] = useState(null); // profile to apply
    const [applyCommessa, setApplyCommessa] = useState('');
    const [applyLabel, setApplyLabel] = useState('');
    const [commesse, setCommesse] = useState([]);

    const tipiMap = Object.fromEntries((tipiDoc || []).map(t => [t.code, t]));

    const loadProfili = useCallback(async () => {
        try {
            const data = await apiRequest('/profili-committente');
            setProfili(data);
        } catch { toast.error('Errore caricamento profili'); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { loadProfili(); }, [loadProfili]);

    const startNew = () => {
        setForm({ client_name: '', description: '', notes: '', warnings: [], rules: [] });
        setEditing('new');
    };

    const startEdit = (p) => {
        setForm({
            client_name: p.client_name || '',
            description: p.description || '',
            notes: p.notes || '',
            warnings: p.warnings || [],
            rules: p.rules || [],
        });
        setEditing(p.profile_id);
    };

    const addRule = () => {
        setForm(f => ({ ...f, rules: [...f.rules, { document_type_code: '', entity_type: 'azienda', required: true }] }));
    };

    const updateRule = (idx, field, val) => {
        setForm(f => {
            const rules = [...f.rules];
            rules[idx] = { ...rules[idx], [field]: val };
            return { ...f, rules };
        });
    };

    const removeRule = (idx) => {
        setForm(f => ({ ...f, rules: f.rules.filter((_, i) => i !== idx) }));
    };

    const handleSave = async () => {
        if (!form.client_name.trim()) { toast.error('Nome committente obbligatorio'); return; }
        if (form.rules.length === 0) { toast.error('Aggiungi almeno una regola'); return; }
        setSaving(true);
        try {
            if (editing === 'new') {
                await apiRequest('/profili-committente', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(form),
                });
                toast.success('Profilo creato');
            } else {
                await apiRequest(`/profili-committente/${editing}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(form),
                });
                toast.success('Profilo aggiornato');
            }
            setEditing(null);
            loadProfili();
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const handleDelete = async (profileId) => {
        if (!window.confirm('Eliminare questo profilo?')) return;
        try {
            await apiRequest(`/profili-committente/${profileId}`, { method: 'DELETE' });
            toast.success('Profilo eliminato');
            loadProfili();
        } catch (e) { toast.error(e.message); }
    };

    const openApply = async (profilo) => {
        setApplyDialog(profilo);
        setApplyCommessa('');
        setApplyLabel(`${profilo.client_name} — ${new Date().toISOString().slice(0, 10)}`);
        try {
            const c = await apiRequest('/commesse');
            setCommesse(c.filter(x => x.stato !== 'chiuso').slice(0, 50));
        } catch { setCommesse([]); }
    };

    const handleApply = async () => {
        if (!applyCommessa) { toast.error('Seleziona una commessa'); return; }
        try {
            const result = await apiRequest(`/profili-committente/${applyDialog.profile_id}/applica`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ commessa_id: applyCommessa, label: applyLabel }),
            });
            toast.success(`Pacchetto creato: ${result.pack?.label}`);
            setApplyDialog(null);
            loadProfili();
            if (onProfileApplied) onProfileApplied();
        } catch (e) { toast.error(e.message); }
    };

    if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>;

    // Edit / New form
    if (editing) {
        return (
            <div className="space-y-4" data-testid="profilo-editor">
                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="sm" onClick={() => setEditing(null)} data-testid="btn-back-profili">
                        <ArrowLeft className="h-4 w-4 mr-1" /> Indietro
                    </Button>
                    <h3 className="text-base font-bold text-slate-800">
                        {editing === 'new' ? 'Nuovo Profilo Committente' : 'Modifica Profilo'}
                    </h3>
                </div>

                <Card>
                    <CardContent className="pt-4 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Nome Committente *</Label>
                                <Input value={form.client_name} onChange={e => setForm(f => ({ ...f, client_name: e.target.value }))}
                                    placeholder="es. Impresa Edile Rossi S.r.l." data-testid="input-client-name" />
                            </div>
                            <div>
                                <Label className="text-xs">Descrizione</Label>
                                <Input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                    placeholder="es. Committente cantieri residenziali" data-testid="input-description" />
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs">Note operative</Label>
                            <Textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                                rows={2} placeholder="Note per l'utilizzo di questo profilo..." data-testid="input-notes" />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">Regole Documentali ({form.rules.length})</CardTitle>
                            <Button size="sm" variant="outline" onClick={addRule} data-testid="btn-add-rule">
                                <Plus className="h-3 w-3 mr-1" /> Aggiungi Regola
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {form.rules.length === 0 && (
                            <p className="text-xs text-slate-400 py-4 text-center">Nessuna regola. Aggiungi i documenti richiesti da questo committente.</p>
                        )}
                        {form.rules.map((rule, idx) => (
                            <div key={idx} className="flex items-center gap-2 p-2 rounded border border-slate-100 bg-slate-50" data-testid={`rule-${idx}`}>
                                <Select value={rule.document_type_code}
                                    onValueChange={v => updateRule(idx, 'document_type_code', v)}>
                                    <SelectTrigger className="flex-1 h-8 text-xs" data-testid={`rule-doctype-${idx}`}>
                                        <SelectValue placeholder="Tipo documento..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {tipiDoc.map(t => (
                                            <SelectItem key={t.code} value={t.code}>{t.label} ({ENTITY_LABELS[t.entity_type]})</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <Select value={rule.entity_type}
                                    onValueChange={v => updateRule(idx, 'entity_type', v)}>
                                    <SelectTrigger className="w-[110px] h-8 text-xs">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="azienda">Azienda</SelectItem>
                                        <SelectItem value="persona">Persona</SelectItem>
                                        <SelectItem value="mezzo">Mezzo</SelectItem>
                                        <SelectItem value="cantiere">Cantiere</SelectItem>
                                    </SelectContent>
                                </Select>
                                <Button size="sm" variant={rule.required ? 'default' : 'outline'}
                                    className={`h-8 text-[10px] ${rule.required ? 'bg-red-600 hover:bg-red-700' : ''}`}
                                    onClick={() => updateRule(idx, 'required', !rule.required)}>
                                    {rule.required ? 'Obbligatorio' : 'Opzionale'}
                                </Button>
                                <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-400 hover:text-red-600"
                                    onClick={() => removeRule(idx)} data-testid={`btn-remove-rule-${idx}`}>
                                    <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                            </div>
                        ))}
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setEditing(null)}>Annulla</Button>
                    <Button onClick={handleSave} disabled={saving} className="bg-violet-600 text-white hover:bg-violet-700"
                        data-testid="btn-save-profilo">
                        {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                        {editing === 'new' ? 'Crea Profilo' : 'Salva Modifiche'}
                    </Button>
                </div>
            </div>
        );
    }

    // List view
    return (
        <div className="space-y-4" data-testid="profili-list">
            <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">{profili.length} profili committente</p>
                <Button size="sm" onClick={startNew} className="bg-violet-600 text-white hover:bg-violet-700"
                    data-testid="btn-nuovo-profilo">
                    <Plus className="h-4 w-4 mr-1" /> Nuovo Profilo
                </Button>
            </div>

            {profili.length === 0 ? (
                <Card className="border-dashed border-2 border-violet-200">
                    <CardContent className="py-12 text-center">
                        <UserCheck className="h-10 w-10 text-violet-300 mx-auto mb-3" />
                        <p className="text-sm text-slate-500">Nessun profilo committente creato.</p>
                        <p className="text-xs text-slate-400 mt-1">Crea un profilo per precompilare automaticamente i pacchetti per i clienti ricorrenti.</p>
                    </CardContent>
                </Card>
            ) : (
                profili.map(p => (
                    <Card key={p.profile_id} className="hover:shadow-md transition-shadow border-slate-200"
                        data-testid={`profilo-${p.profile_id}`}>
                        <CardHeader className="pb-2">
                            <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                    <CardTitle className="text-base flex items-center gap-2">
                                        <UserCheck className="h-4 w-4 text-violet-600" />
                                        {p.client_name}
                                    </CardTitle>
                                    <CardDescription className="text-xs mt-0.5">{p.description}</CardDescription>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="text-[10px]">{p.rules?.length || 0} regole</Badge>
                                    {p.usage_count > 0 && (
                                        <Badge className="text-[10px] bg-violet-100 text-violet-700">Usato {p.usage_count}x</Badge>
                                    )}
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                            {/* Rules preview */}
                            <div className="flex gap-1.5 flex-wrap mb-3">
                                {(p.rules || []).slice(0, 6).map((r, i) => (
                                    <Badge key={i} variant="outline" className={`text-[9px] ${r.required ? 'border-red-200 text-red-700 bg-red-50' : 'border-slate-200 text-slate-600'}`}>
                                        {tipiMap[r.document_type_code]?.label || r.document_type_code}
                                    </Badge>
                                ))}
                                {(p.rules || []).length > 6 && (
                                    <Badge variant="outline" className="text-[9px]">+{p.rules.length - 6}</Badge>
                                )}
                            </div>
                            {p.notes && (
                                <p className="text-[10px] text-slate-500 flex items-start gap-1 mb-2">
                                    <Info className="h-3 w-3 mt-0.5 shrink-0" /> {p.notes}
                                </p>
                            )}
                            {p.warnings?.length > 0 && (
                                <div className="mb-2">
                                    {p.warnings.map((w, i) => (
                                        <p key={i} className="text-[10px] text-amber-600 flex items-start gap-1">
                                            <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" /> {w}
                                        </p>
                                    ))}
                                </div>
                            )}
                            {/* Actions */}
                            <Separator className="my-2" />
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Button size="sm" variant="outline" className="h-7 text-[10px]"
                                        onClick={() => startEdit(p)} data-testid={`btn-edit-${p.profile_id}`}>
                                        <Edit className="h-3 w-3 mr-1" /> Modifica
                                    </Button>
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-red-500 hover:text-red-700"
                                        onClick={() => handleDelete(p.profile_id)} data-testid={`btn-delete-${p.profile_id}`}>
                                        <Trash2 className="h-3 w-3 mr-1" /> Elimina
                                    </Button>
                                </div>
                                <Button size="sm" className="h-7 text-[10px] bg-emerald-600 text-white hover:bg-emerald-700"
                                    onClick={() => openApply(p)} data-testid={`btn-apply-${p.profile_id}`}>
                                    <Play className="h-3 w-3 mr-1" /> Applica a Commessa
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))
            )}

            {/* Apply Dialog */}
            <Dialog open={!!applyDialog} onOpenChange={(o) => !o && setApplyDialog(null)}>
                <DialogContent data-testid="apply-profile-dialog">
                    <DialogHeader>
                        <DialogTitle>Applica Profilo: {applyDialog?.client_name}</DialogTitle>
                        <DialogDescription>
                            Seleziona la commessa per creare un pacchetto precompilato con {applyDialog?.rules?.length || 0} regole.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <div>
                            <Label className="text-xs">Commessa *</Label>
                            <Select value={applyCommessa} onValueChange={setApplyCommessa}>
                                <SelectTrigger data-testid="select-apply-commessa">
                                    <SelectValue placeholder="Seleziona commessa..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {commesse.map(c => (
                                        <SelectItem key={c.commessa_id} value={c.commessa_id}>
                                            {c.numero} — {c.title || c.client_name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs">Nome Pacchetto</Label>
                            <Input value={applyLabel} onChange={e => setApplyLabel(e.target.value)}
                                data-testid="input-apply-label" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setApplyDialog(null)}>Annulla</Button>
                        <Button onClick={handleApply} className="bg-emerald-600 text-white hover:bg-emerald-700"
                            data-testid="btn-confirm-apply">
                            <Play className="h-4 w-4 mr-2" /> Crea Pacchetto
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

// ── Save as Profile Button (used in PackageDetailView) ──
function SaveAsProfileButton({ packId }) {
    const [showDialog, setShowDialog] = useState(false);
    const [clientName, setClientName] = useState('');
    const [description, setDescription] = useState('');
    const [saving, setSaving] = useState(false);

    const handleSave = async () => {
        if (!clientName.trim()) { toast.error('Nome committente obbligatorio'); return; }
        setSaving(true);
        try {
            await apiRequest(`/profili-committente/da-pacchetto/${packId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ client_name: clientName, description }),
            });
            toast.success('Profilo salvato');
            setShowDialog(false);
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    return (
        <>
            <Button size="sm" variant="outline" className="h-7 text-[10px] border-violet-300 text-violet-700"
                onClick={() => setShowDialog(true)} data-testid="btn-save-as-profile">
                <UserCheck className="h-3 w-3 mr-1" /> Salva come Profilo
            </Button>
            <Dialog open={showDialog} onOpenChange={setShowDialog}>
                <DialogContent data-testid="save-profile-dialog">
                    <DialogHeader>
                        <DialogTitle>Salva come Profilo Committente</DialogTitle>
                        <DialogDescription>
                            Il sistema creera un profilo riutilizzabile basato sulle regole di questo pacchetto.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <div>
                            <Label className="text-xs">Nome Committente *</Label>
                            <Input value={clientName} onChange={e => setClientName(e.target.value)}
                                placeholder="es. Impresa Edile Rossi" data-testid="input-profile-client" />
                        </div>
                        <div>
                            <Label className="text-xs">Descrizione</Label>
                            <Input value={description} onChange={e => setDescription(e.target.value)}
                                placeholder="es. Cantieri residenziali Nord Italia" data-testid="input-profile-desc" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDialog(false)}>Annulla</Button>
                        <Button onClick={handleSave} disabled={saving} className="bg-violet-600 text-white hover:bg-violet-700"
                            data-testid="btn-confirm-save-profile">
                            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Salva Profilo
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}



// ── Main Page ──
export default function PacchettiDocumentaliPage() {
    const [tab, setTab] = useState('archivio');
    const [tipiDoc, setTipiDoc] = useState([]);
    const [documenti, setDocumenti] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [pacchetti, setPacchetti] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filterEntity, setFilterEntity] = useState('');
    const [filterStatus, setFilterStatus] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    // New package form
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [packLabel, setPackLabel] = useState('');
    const [creating, setCreating] = useState(false);

    // Detail view
    const [selectedPackId, setSelectedPackId] = useState(null);

    const tipiMap = Object.fromEntries(tipiDoc.map(t => [t.code, t]));

    const loadData = useCallback(async () => {
        try {
            const [tipi, docs, tpls, packs] = await Promise.all([
                apiRequest('/documenti/tipi'),
                apiRequest('/documenti'),
                apiRequest('/pacchetti-documentali/templates'),
                apiRequest('/pacchetti-documentali'),
            ]);
            setTipiDoc(tipi);
            setDocumenti(docs);
            setTemplates(tpls);
            setPacchetti(packs);
        } catch (err) { toast.error('Errore caricamento dati'); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleCreatePack = async () => {
        if (!selectedTemplate) { toast.error('Seleziona un template'); return; }
        setCreating(true);
        try {
            const pack = await apiRequest('/pacchetti-documentali', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_code: selectedTemplate, label: packLabel || selectedTemplate }),
            });
            toast.success(`Pacchetto creato: ${pack.pack_id}`);
            setPacchetti(p => [pack, ...p]);
            setSelectedTemplate('');
            setPackLabel('');
            // Auto-verify
            const verified = await apiRequest(`/pacchetti-documentali/${pack.pack_id}/verifica`, { method: 'POST' });
            setPacchetti(p => p.map(pk => pk.pack_id === verified.pack_id ? { ...pk, ...verified } : pk));
        } catch (err) { toast.error(err.message); }
        finally { setCreating(false); }
    };

    const handleVerifica = async (packId) => {
        try {
            const result = await apiRequest(`/pacchetti-documentali/${packId}/verifica`, { method: 'POST' });
            setPacchetti(p => p.map(pk => pk.pack_id === result.pack_id ? { ...pk, ...result } : pk));
            toast.success('Verifica completata');
        } catch (err) { toast.error(err.message); }
    };

    // Filter documents
    const filteredDocs = documenti.filter(d => {
        if (filterEntity && d.entity_type !== filterEntity) return false;
        if (filterStatus && d.status !== filterStatus) return false;
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            return (d.title || '').toLowerCase().includes(q) ||
                   (d.owner_label || '').toLowerCase().includes(q) ||
                   (d.document_type_code || '').toLowerCase().includes(q);
        }
        return true;
    });

    if (loading) return <DashboardLayout><div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" /></div></DashboardLayout>;

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="pacchetti-documentali-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Pacchetti Documentali</h1>
                        <p className="text-sm text-slate-500">{documenti.length} documenti in archivio, {pacchetti.length} pacchetti</p>
                    </div>
                </div>

                <Tabs value={tab} onValueChange={v => { setTab(v); setSelectedPackId(null); }}>
                    <TabsList>
                        <TabsTrigger value="archivio" className="gap-2" data-testid="tab-archivio">
                            <FileInput className="h-4 w-4" /> Archivio
                        </TabsTrigger>
                        <TabsTrigger value="pacchetti" className="gap-2" data-testid="tab-pacchetti">
                            <Package className="h-4 w-4" /> Pacchetti
                        </TabsTrigger>
                        <TabsTrigger value="profili" className="gap-2" data-testid="tab-profili">
                            <UserCheck className="h-4 w-4" /> Profili Committente
                        </TabsTrigger>
                    </TabsList>

                    {/* ── TAB: Archivio Documenti ── */}
                    <TabsContent value="archivio" className="space-y-4">
                        <UploadForm tipiDoc={tipiDoc} onUploaded={loadData} />
                        <div className="flex items-center gap-3">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input className="pl-9" placeholder="Cerca per titolo, intestatario, tipo..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} data-testid="search-docs" />
                            </div>
                            <Select value={filterEntity} onValueChange={v => setFilterEntity(v === 'all' ? '' : v)}>
                                <SelectTrigger className="w-[150px]" data-testid="filter-entity"><SelectValue placeholder="Entita" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutte</SelectItem>
                                    <SelectItem value="azienda">Azienda</SelectItem>
                                    <SelectItem value="persona">Persona</SelectItem>
                                    <SelectItem value="mezzo">Mezzo</SelectItem>
                                    <SelectItem value="cantiere">Cantiere</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={filterStatus} onValueChange={v => setFilterStatus(v === 'all' ? '' : v)}>
                                <SelectTrigger className="w-[140px]" data-testid="filter-status"><SelectValue placeholder="Stato" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti</SelectItem>
                                    <SelectItem value="valido">Valido</SelectItem>
                                    <SelectItem value="in_scadenza">In scadenza</SelectItem>
                                    <SelectItem value="scaduto">Scaduto</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <DocumentList documenti={filteredDocs} tipiMap={tipiMap} />
                    </TabsContent>

                    {/* ── TAB: Pacchetti ── */}
                    <TabsContent value="pacchetti" className="space-y-4">
                        {selectedPackId ? (
                            <PackageDetailView
                                packId={selectedPackId}
                                tipiMap={tipiMap}
                                onBack={() => { setSelectedPackId(null); loadData(); }}
                            />
                        ) : (
                            <>
                                <Card className="border-dashed border-2 border-violet-200" data-testid="new-pack-form">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-base flex items-center gap-2"><Plus className="h-4 w-4" /> Nuovo Pacchetto</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            <div>
                                                <Label className="text-xs">Template *</Label>
                                                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                                                    <SelectTrigger data-testid="select-template"><SelectValue placeholder="Seleziona template..." /></SelectTrigger>
                                                    <SelectContent>{templates.map(t => <SelectItem key={t.code} value={t.code}>{t.label} ({t.rules.length} regole)</SelectItem>)}</SelectContent>
                                                </Select>
                                            </div>
                                            <div>
                                                <Label className="text-xs">Nome pacchetto</Label>
                                                <Input placeholder="es. Cantiere Milano Nord" value={packLabel} onChange={e => setPackLabel(e.target.value)} data-testid="input-pack-label" />
                                            </div>
                                            <div className="flex items-end">
                                                <Button onClick={handleCreatePack} disabled={creating} className="bg-violet-600 text-white hover:bg-violet-700 w-full" data-testid="btn-crea-pacchetto">
                                                    {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Package className="h-4 w-4 mr-2" />}
                                                    Crea e Verifica
                                                </Button>
                                            </div>
                                        </div>
                                        {selectedTemplate && (
                                            <div className="mt-3 text-xs text-slate-500">
                                                {templates.find(t => t.code === selectedTemplate)?.description}
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>

                                {pacchetti.length === 0 ? (
                                    <p className="text-sm text-slate-400 py-8 text-center">Nessun pacchetto creato. Usa il form sopra per creare il primo.</p>
                                ) : (
                                    pacchetti.map(pack => (
                                        <PackageCard key={pack.pack_id} pack={pack} tipiMap={tipiMap} onVerifica={handleVerifica} onOpen={setSelectedPackId} />
                                    ))
                                )}
                            </>
                        )}
                    </TabsContent>

                    {/* ── TAB: Profili Committente (D6) ── */}
                    <TabsContent value="profili" className="space-y-4">
                        <ProfiliTab tipiDoc={tipiDoc} onProfileApplied={loadData} />
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}
