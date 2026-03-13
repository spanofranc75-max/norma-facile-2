/**
 * EmailPreviewDialog — Shows email preview with editable subject + body before sending.
 * Supports expand/collapse to fullscreen for better PDF/content visibility.
 */
import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { toast } from 'sonner';
import { Mail, Send, Loader2, Paperclip, User, FileText, Pencil, Eye, Maximize2, Minimize2 } from 'lucide-react';

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
    const iframeRef = useRef(null);

    useEffect(() => {
        if (open && previewUrl) {
            setLoading(true);
            setError(null);
            setPreview(null);
            setEditMode(false);
            setExpanded(false);
            fetch(`${API}${previewUrl}`, {
                headers: getAuthHeaders(),
            })
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
            if (doc) {
                doc.open();
                doc.write(preview.html_body);
                doc.close();
            }
        }
    }, [preview, editMode]);

    const handleSend = async () => {
        if (!sendUrl) return;
        setSending(true);
        try {
            const body = editMode
                ? { custom_subject: editSubject, custom_body: editBody }
                : {};
            const res = await fetch(`${API}${sendUrl}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
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
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSending(false);
        }
    };

    const sizeClass = expanded
        ? 'max-w-[95vw] w-[95vw] max-h-[95vh] h-[95vh]'
        : 'max-w-2xl max-h-[90vh]';

    const bodyHeight = expanded ? 'calc(95vh - 260px)' : '300px';

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className={`${sizeClass} flex flex-col transition-all duration-200`} data-testid="email-preview-dialog">
                <DialogHeader>
                    <div className="flex items-center justify-between">
                        <DialogTitle className="flex items-center gap-2">
                            <Mail className="h-5 w-5 text-blue-600" />
                            Anteprima Email
                        </DialogTitle>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-slate-500 hover:text-slate-800"
                            onClick={() => setExpanded(!expanded)}
                            data-testid="email-toggle-expand"
                        >
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
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700" data-testid="email-preview-error">
                        {error}
                    </div>
                )}

                {preview && !loading && (
                    <div className="space-y-3 flex-1 min-h-0 flex flex-col overflow-y-auto">
                        {/* Email metadata */}
                        <div className="bg-slate-50 rounded-lg p-3 space-y-2 text-sm border">
                            <div className="flex items-center gap-2">
                                <User className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                <span className="text-slate-500 w-8 shrink-0">A:</span>
                                <span className="font-medium text-slate-800 truncate" data-testid="email-preview-to">
                                    {preview.to_name ? `${preview.to_name} <${preview.to_email}>` : preview.to_email || 'Nessun destinatario'}
                                </span>
                                {!preview.to_email && <Badge className="bg-amber-100 text-amber-700 text-[9px]">Mancante</Badge>}
                            </div>
                            {editMode ? (
                                <div className="flex items-center gap-2">
                                    <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    <span className="text-slate-500 w-8 shrink-0">Ogg:</span>
                                    <Input value={editSubject} onChange={e => setEditSubject(e.target.value)} className="h-7 text-sm flex-1" data-testid="email-edit-subject" />
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
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={() => setEditMode(!editMode)} data-testid="email-toggle-edit">
                                {editMode ? <><Eye className="h-3 w-3" /> Anteprima</> : <><Pencil className="h-3 w-3" /> Modifica testo</>}
                            </Button>
                        </div>

                        {editMode ? (
                            <Textarea
                                value={editBody}
                                onChange={e => setEditBody(e.target.value)}
                                className="flex-1 text-sm font-mono resize-none"
                                style={{ minHeight: bodyHeight }}
                                placeholder="Scrivi il testo dell'email..."
                                data-testid="email-edit-body"
                            />
                        ) : (
                            <div className="flex-1 min-h-0 border rounded-lg overflow-hidden bg-white" data-testid="email-preview-body">
                                <iframe
                                    ref={iframeRef}
                                    title="Email Preview"
                                    className="w-full border-0"
                                    style={{ height: bodyHeight }}
                                    sandbox="allow-same-origin"
                                />
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter className="gap-2">
                    <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>Annulla</Button>
                    <Button
                        size="sm"
                        className="bg-[#0055FF] text-white"
                        disabled={sending || !preview?.to_email}
                        onClick={handleSend}
                        data-testid="email-preview-send-btn"
                    >
                        {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
                        {sending ? 'Invio in corso...' : 'Invia Email'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
