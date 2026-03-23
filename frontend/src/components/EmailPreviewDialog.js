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
    const [ccEmails, setCcEmails] = useState([]);
    const [ccInput, setCcInput] = useState('');
    const [showCc, setShowCc] = useState(false);
    const [confirmed, setConfirmed] = useState(false);
    const iframeRef = useRef(null);

    useEffect(() => {
        if (open && previewUrl) {
            setLoading(true);
            setError(null);
            setPreview(null);
            setEditMode(false);
            setExpanded(false);
            setCcEmails([]);
            setCcInput('');
            setShowCc(false);
            setConfirmed(false);
            fetch(`${API}${previewUrl}`, { headers: getAuthHeaders(), credentials: 'include' })
                .then(r => {
                    if (!r.ok) throw new Error('Errore caricamento anteprima');
                    return r.json();
                })
                .then(data => {
                    setPreview(data);
                    setEditSubject(data.subject || '');
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

    const addCcEmail = (emailToAdd) => {
        const raw = emailToAdd || ccInput.trim();
        if (!raw) return;
        const emails = raw.split(/[,;]\s*/).map(e => e.trim()).filter(Boolean);
        const newValid = [];
        for (const email of emails) {
            if (!isValidEmail(email)) { toast.error(`Email non valida: ${email}`); continue; }
            if (ccEmails.includes(email)) { toast.error(`${email} gia' aggiunto`); continue; }
            if (preview?.to_email && email === preview.to_email) { toast.error(`${email} e' il destinatario principale`); continue; }
            newValid.push(email);
        }
        if (newValid.length > 0) setCcEmails(prev => [...prev, ...newValid]);
        if (!emailToAdd) setCcInput('');
    };

    const removeCcEmail = (email) => setCcEmails(prev => prev.filter(e => e !== email));

    const handleCcKeyDown = (e) => {
        if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addCcEmail(); }
    };

    const handleSend = async () => {
        if (!sendUrl) return;
        setSending(true);
        try {
            const body = {};
            if (editMode) { body.custom_subject = editSubject; body.custom_body = editBody; }

            // Auto-confirm any email still typed in the CC input (user forgot to press Enter)
            let finalCc = [...ccEmails];
            if (ccInput.trim()) {
                const pendingEmails = ccInput.trim().split(/[,;]\s*/).map(e => e.trim()).filter(e => isValidEmail(e));
                pendingEmails.forEach(e => { if (!finalCc.includes(e)) finalCc.push(e); });
            }
            if (finalCc.length > 0) body.cc = finalCc;
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

    const suggestedContacts = (preview?.suggested_contacts || []).filter(c => !ccEmails.includes(c.email));
    const sizeClass = expanded ? 'max-w-[95vw] w-[95vw] max-h-[95vh] h-[95vh]' : 'max-w-2xl max-h-[90vh]';
    const bodyHeight = expanded ? 'calc(95vh - 320px)' : '240px';

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
                        <div className="bg-slate-50 rounded-lg p-3 space-y-2 text-sm border">
                            {/* TO */}
                            <div className="flex items-center gap-2">
                                <User className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                <span className="text-slate-500 w-8 shrink-0">A:</span>
                                <span className="font-medium text-slate-800 truncate" data-testid="email-preview-to">
                                    {preview.to_name ? `${preview.to_name} <${preview.to_email}>` : preview.to_email || 'Nessun destinatario'}
                                </span>
                                {!preview.to_email && <Badge className="bg-amber-100 text-amber-700 text-[9px]">Mancante</Badge>}
                                {!showCc && (
                                    <Button variant="ghost" size="sm"
                                        className="h-6 px-2 text-[11px] text-blue-600 hover:text-blue-800 hover:bg-blue-50 ml-auto"
                                        onClick={() => setShowCc(true)} data-testid="email-add-cc-btn">
                                        <Plus className="h-3 w-3 mr-1" />CC
                                    </Button>
                                )}
                            </div>

                            {/* CC */}
                            {showCc && (
                                <div className="space-y-2" data-testid="email-cc-section">
                                    <div className="flex items-start gap-2">
                                        <Users className="h-3.5 w-3.5 text-slate-400 shrink-0 mt-1.5" />
                                        <span className="text-slate-500 w-8 shrink-0 mt-1">CC:</span>
                                        <div className="flex-1 space-y-1.5">
                                            {ccEmails.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {ccEmails.map(email => (
                                                        <Badge key={email} className="bg-blue-50 text-blue-700 text-[11px] gap-1 pr-1"
                                                            data-testid={`email-cc-badge`}>
                                                            {email}
                                                            <button onClick={() => removeCcEmail(email)}
                                                                className="hover:bg-blue-200 rounded-full p-0.5 ml-0.5"
                                                                data-testid={`email-cc-remove`}>
                                                                <X className="h-2.5 w-2.5" />
                                                            </button>
                                                        </Badge>
                                                    ))}
                                                </div>
                                            )}
                                            <div className="flex items-center gap-1">
                                                <Input value={ccInput} onChange={e => setCcInput(e.target.value)}
                                                    onKeyDown={handleCcKeyDown}
                                                    placeholder="Aggiungi email e premi Invio..."
                                                    className="h-7 text-sm flex-1" data-testid="email-cc-input" />
                                                <Button variant="outline" size="sm" className="h-7 px-2 text-xs"
                                                    onClick={() => addCcEmail()} disabled={!ccInput.trim()}
                                                    data-testid="email-cc-add-btn">
                                                    <Plus className="h-3 w-3" />
                                                </Button>
                                            </div>

                                            {/* Suggested contacts from client's address book */}
                                            {suggestedContacts.length > 0 && (
                                                <div className="pt-1" data-testid="email-cc-suggestions">
                                                    <div className="flex items-center gap-1 mb-1">
                                                        <BookUser className="h-3 w-3 text-slate-400" />
                                                        <span className="text-[10px] text-slate-400 uppercase tracking-wide">Rubrica</span>
                                                    </div>
                                                    <div className="flex flex-wrap gap-1">
                                                        {suggestedContacts.map(contact => (
                                                            <button key={contact.email}
                                                                onClick={() => addCcEmail(contact.email)}
                                                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-slate-100 text-slate-600 hover:bg-blue-50 hover:text-blue-700 transition-colors border border-slate-200 hover:border-blue-200"
                                                                data-testid={`email-cc-suggest`}>
                                                                <Plus className="h-2.5 w-2.5" />
                                                                {contact.name || contact.email}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

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
                            {!preview.to_email && (
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
                            disabled={sending || !preview?.to_email || !confirmed} onClick={handleSend}
                            data-testid="email-preview-send-btn">
                            {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <ShieldCheck className="h-4 w-4 mr-1" />}
                            {sending ? 'Invio in corso...' : ccEmails.length > 0 ? `Conferma invio a ${1 + ccEmails.length}` : 'Conferma e Invia'}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
