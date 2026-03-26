/**
 * EmailPreviewDialog — Email preview with editable subject + body.
 * Supports CC with contacts quick-picker from client's address book.
 */
import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Checkbox } from './ui/checkbox';
import { toast } from 'sonner';
import { Mail, Send, Loader2, Paperclip, User, FileText, Pencil, Eye, Maximize2, Minimize2, Plus, X, Users, BookUser, AlertTriangle, ShieldCheck } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    if (token) return { 'Authorization': `Bearer ${token}` };
    return {};
}

export default function EmailPreviewDialog({ open, onOpenChange, previewUrl, sendUrl, onSent }) {
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [preview, setPreview] = useState(null);
    const [error, setError] = useState(null);
    const [editMode, setEditMode] = useState(false);
    const [editSubject, setEditSubject] = useState('');
    const [editBody, setEditBody] = useState('');
    const [expanded, setExpanded] = useState(false);
    const [selectedEmails, setSelectedEmails] = useState([]);
    const [ccInput, setCcInput] = useState('');
    const [showCcInput, setShowCcInput] = useState(false);
    const [confirmed, setConfirmed] = useState(false);
    const iframeRef = useRef(null);

    useEffect(() => {
        if (open && previewUrl) {
            setLoading(true);
            setError(null);
            setPreview(null);
            setEditMode(false);
            setExpanded(false);
            setSelectedEmails([]);
            setCcInput('');
            setShowCcInput(false);
            setConfirmed(false);
            fetch(`${API}${previewUrl}`, { headers: getAuthHeaders(), credentials: 'include' })
                .then(r => {
                    if (!r.ok) throw new Error('Errore caricamento anteprima');
                    return r.json();
                })
                .then(data => {
                    setPreview(data);
                    setEditSubject(data.subject || '');
                    // Pre-select default recipients
                    const defaults = (data.all_recipients || []).filter(r => r.default).map(r => r.email);
                    if (defaults.length === 0 && data.to_email) defaults.push(data.to_email);
                    setSelectedEmails(defaults);
                    const tmp = document.createElement('div');
                    tmp.innerHTML = data.html_body || '';
                    const ps = tmp.querySelectorAll('p');
                    let text = '';
                    ps.forEach(p => {
                        const t = p.textContent.trim();
                        if (t && !t.includes('Email inviata tramite')) text += t + '\n\n';
                    });
                    setEditBody(text.trim() || tmp.textContent.trim());
                })
                .catch(e => setError(e.message))
                .finally(() => setLoading(false));
        }
    }, [open, previewUrl]);

    useEffect(() => {
        if (!editMode && preview?.html_body && iframeRef.current) {
            const doc = iframeRef.current.contentDocument;
            if (doc) { doc.open(); doc.write(preview.html_body); doc.close(); }
        }
    }, [preview, editMode]);

    const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

    const toggleEmail = (email) => {
        setSelectedEmails(prev => prev.includes(email) ? prev.filter(e => e !== email) : [...prev, email]);
    };

    const addManualEmail = () => {
        const raw = ccInput.trim();
        if (!raw) return;
        const emails = raw.split(/[,;]\s*/).map(e => e.trim()).filter(Boolean);
        for (const email of emails) {
            if (!isValidEmail(email)) { toast.error(`Email non valida: ${email}`); continue; }
            if (selectedEmails.includes(email)) continue;
            setSelectedEmails(prev => [...prev, email]);
        }
        setCcInput('');
    };

    const handleCcKeyDown = (e) => {
        if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addManualEmail(); }
    };

    const handleSend = async () => {
        if (!sendUrl) return;
        setSending(true);
        try {
            const body = {};
            if (editMode) { body.custom_subject = editSubject; body.custom_body = editBody; }
            // Add pending input
            let finalEmails = [...selectedEmails];
            if (ccInput.trim()) {
                const pending = ccInput.trim().split(/[,;]\s*/).map(e => e.trim()).filter(e => isValidEmail(e));
                pending.forEach(e => { if (!finalEmails.includes(e)) finalEmails.push(e); });
            }
            body.to_emails = finalEmails;
            const res = await fetch(`${API}${sendUrl}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                credentials: 'include',
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || 'Invio fallito');
            }
            const result = await res.json();
            toast.success(result.message || 'Email inviata con successo');
            onSent?.();
            onOpenChange(false);
        } catch (e) { toast.error(e.message); }
        finally { setSending(false); }
    };

    const allRecipients = preview?.all_recipients || [];
    const manualEmails = selectedEmails.filter(e => !allRecipients.some(r => r.email === e));
    const sizeClass = expanded ? 'max-w-[95vw] w-[95vw] max-h-[95vh] h-[95vh]' : 'max-w-2xl max-h-[90vh]';
    const bodyHeight = expanded ? 'calc(95vh - 380px)' : '220px';

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className={`${sizeClass} flex flex-col transition-all duration-200`} data-testid="email-preview-dialog">
                <DialogHeader>
                    <div className="flex items-center justify-between">
                        <DialogTitle className="flex items-center gap-2">
                            <Mail className="h-5 w-5 text-blue-600" />
                            Anteprima Email
                        </DialogTitle>
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-slate-500 hover:text-slate-800"
                            onClick={() => setExpanded(!expanded)} data-testid="email-toggle-expand">
                            {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                        </Button>
                    </div>
                    <DialogDescription>Verifica e personalizza il contenuto prima dell'invio</DialogDescription>
                </DialogHeader>

                {loading && (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                        <span className="ml-2 text-sm text-slate-500">Caricamento anteprima...</span>
                    </div>
                )}

                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700" data-testid="email-preview-error">{error}</div>
                )}

                {preview && !loading && (
                    <div className="space-y-3 flex-1 min-h-0 flex flex-col overflow-y-auto">
                        <div className="bg-slate-50 rounded-lg p-3 space-y-2.5 text-sm border">
                            {/* Recipients — all emails with checkboxes */}
                            <div className="space-y-1.5">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-1.5">
                                        <Users className="h-3.5 w-3.5 text-slate-400" />
                                        <span className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold">Destinatari</span>
                                    </div>
                                    {!showCcInput && (
                                        <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-blue-600"
                                            onClick={() => setShowCcInput(true)} data-testid="email-add-manual-btn">
                                            <Plus className="h-3 w-3 mr-1" />Aggiungi email
                                        </Button>
                                    )}
                                </div>
                                {allRecipients.length > 0 ? (
                                    <div className="space-y-1">
                                        {allRecipients.map(r => (
                                            <label key={r.email} className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors ${
                                                selectedEmails.includes(r.email) ? 'bg-blue-50 border border-blue-200' : 'bg-white border border-slate-200 hover:bg-slate-50'
                                            }`}>
                                                <Checkbox
                                                    checked={selectedEmails.includes(r.email)}
                                                    onCheckedChange={() => toggleEmail(r.email)}
                                                    data-testid={`email-recipient-${r.type}`}
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <span className="text-xs font-medium text-slate-700">{r.label}</span>
                                                </div>
                                                <span className="text-[10px] text-slate-400 font-mono">{r.email}</span>
                                                {r.type === 'pec' && <Badge className="bg-amber-50 text-amber-700 text-[9px] px-1.5">PEC</Badge>}
                                            </label>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-xs text-amber-600 py-1">Nessun indirizzo email trovato per questo cliente</p>
                                )}
                                {/* Manual emails added */}
                                {manualEmails.map(email => (
                                    <div key={email} className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg bg-blue-50 border border-blue-200">
                                        <Checkbox checked={true} onCheckedChange={() => toggleEmail(email)} />
                                        <span className="text-xs font-mono text-slate-700 flex-1">{email}</span>
                                        <button onClick={() => setSelectedEmails(p => p.filter(e => e !== email))} className="text-red-400 hover:text-red-600 p-0.5">
                                            <X className="h-3 w-3" />
                                        </button>
                                    </div>
                                ))}
                                {/* Manual email input */}
                                {showCcInput && (
                                    <div className="flex items-center gap-1 pt-1">
                                        <Input value={ccInput} onChange={e => setCcInput(e.target.value)}
                                            onKeyDown={handleCcKeyDown}
                                            placeholder="Email aggiuntiva... (Invio per aggiungere)"
                                            className="h-7 text-sm flex-1" data-testid="email-manual-input" />
                                        <Button variant="outline" size="sm" className="h-7 px-2 text-xs"
                                            onClick={addManualEmail} disabled={!ccInput.trim()}>
                                            <Plus className="h-3 w-3" />
                                        </Button>
                                    </div>
                                )}
                            </div>

                            {/* Subject */}
                            {editMode ? (
                                <div className="flex items-center gap-2">
                                    <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    <span className="text-slate-500 w-8 shrink-0">Ogg:</span>
                                    <Input value={editSubject} onChange={e => setEditSubject(e.target.value)}
                                        className="h-7 text-sm flex-1" data-testid="email-edit-subject" />
                                </div>
                            ) : (
                                <div className="flex items-center gap-2">
                                    <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    <span className="text-slate-500 w-8 shrink-0">Ogg:</span>
                                    <span className="font-medium text-slate-800 truncate" data-testid="email-preview-subject">{preview.subject}</span>
                                </div>
                            )}
                            {preview.has_attachment && (
                                <div className="flex items-center gap-2">
                                    <Paperclip className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    <span className="text-slate-500 w-8 shrink-0">All:</span>
                                    <Badge className="bg-blue-50 text-blue-700 text-[10px]">
                                        <Paperclip className="h-2.5 w-2.5 mr-0.5" />{preview.attachment_name}
                                    </Badge>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end">
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1"
                                onClick={() => setEditMode(!editMode)} data-testid="email-toggle-edit">
                                {editMode ? <><Eye className="h-3 w-3" /> Anteprima</> : <><Pencil className="h-3 w-3" /> Modifica testo</>}
                            </Button>
                        </div>

                        {editMode ? (
                            <Textarea value={editBody} onChange={e => setEditBody(e.target.value)}
                                className="flex-1 text-sm font-mono resize-none"
                                style={{ minHeight: bodyHeight }}
                                placeholder="Scrivi il testo dell'email..." data-testid="email-edit-body" />
                        ) : (
                            <div className="flex-1 min-h-0 border rounded-lg overflow-hidden bg-white" data-testid="email-preview-body">
                                <iframe ref={iframeRef} title="Email Preview"
                                    className="w-full border-0" style={{ height: bodyHeight }}
                                    sandbox="allow-same-origin" />
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter className="gap-2 flex-col items-stretch sm:flex-col">
                    {/* Warnings */}
                    {preview && (
                        <div className="space-y-1.5">
                            {preview.company_warnings?.map((w, i) => (
                                <div key={`cw-${i}`} className="flex items-center gap-2 text-xs text-red-700 bg-red-50 p-2 rounded border border-red-200" data-testid="email-warn-company">
                                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />{w}
                                </div>
                            ))}
                            {!preview.to_email && allRecipients.length === 0 && selectedEmails.length === 0 && (
                                <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 p-2 rounded border border-amber-200" data-testid="email-warn-no-dest">
                                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />Nessun destinatario configurato
                                </div>
                            )}
                            {!preview.has_attachment && (
                                <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 p-2 rounded border border-amber-200" data-testid="email-warn-no-attach">
                                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />Nessun allegato — l'email verra inviata senza documenti
                                </div>
                            )}
                        </div>
                    )}

                    {/* Mandatory confirmation */}
                    <div className="flex items-center gap-2 py-1" data-testid="email-confirm-section">
                        <Checkbox id="email-confirm" checked={confirmed} onCheckedChange={setConfirmed} data-testid="email-confirm-checkbox" />
                        <label htmlFor="email-confirm" className="text-xs text-slate-600 cursor-pointer select-none">
                            Ho verificato destinatari, oggetto e allegati
                        </label>
                    </div>

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>Annulla</Button>
                        <Button size="sm" className="bg-[#0055FF] text-white"
                            disabled={sending || selectedEmails.length === 0 || !confirmed} onClick={handleSend}
                            data-testid="email-preview-send-btn">
                            {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <ShieldCheck className="h-4 w-4 mr-1" />}
                            {sending ? 'Invio in corso...' : selectedEmails.length > 1 ? `Conferma invio a ${selectedEmails.length}` : 'Conferma e Invia'}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
