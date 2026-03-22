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
    AlertCircle, ShieldAlert, FileText,
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
                </Tabs>
            </div>
        </DashboardLayout>
    );
}
