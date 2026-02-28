/**
 * EmailPreviewDialog — Shows email preview before sending.
 * Fetches preview from backend, displays subject/to/body, then sends on confirm.
 */
import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { Mail, Send, Loader2, Paperclip, User, FileText } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function EmailPreviewDialog({ open, onOpenChange, previewUrl, sendUrl, onSent }) {
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [preview, setPreview] = useState(null);
    const [error, setError] = useState(null);
    const iframeRef = useRef(null);

    useEffect(() => {
        if (open && previewUrl) {
            setLoading(true);
            setError(null);
            setPreview(null);
            fetch(`${API}${previewUrl}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            })
            .then(r => {
                if (!r.ok) throw new Error('Errore caricamento anteprima');
                return r.json();
            })
            .then(data => setPreview(data))
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
        }
    }, [open, previewUrl]);

    // Write HTML to iframe when preview loads
    useEffect(() => {
        if (preview?.html_body && iframeRef.current) {
            const doc = iframeRef.current.contentDocument;
            if (doc) {
                doc.open();
                doc.write(preview.html_body);
                doc.close();
            }
        }
    }, [preview]);

    const handleSend = async () => {
        if (!sendUrl) return;
        setSending(true);
        try {
            const res = await fetch(`${API}${sendUrl}`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
                    'Content-Type': 'application/json',
                },
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

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col" data-testid="email-preview-dialog">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Mail className="h-5 w-5 text-blue-600" />
                        Anteprima Email
                    </DialogTitle>
                    <DialogDescription>Verifica il contenuto prima dell'invio</DialogDescription>
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
                    <div className="space-y-3 flex-1 min-h-0 flex flex-col">
                        {/* Email metadata */}
                        <div className="bg-slate-50 rounded-lg p-3 space-y-2 text-sm border">
                            <div className="flex items-center gap-2">
                                <User className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                <span className="text-slate-500 w-8">A:</span>
                                <span className="font-medium text-slate-800" data-testid="email-preview-to">
                                    {preview.to_name ? `${preview.to_name} <${preview.to_email}>` : preview.to_email || 'Nessun destinatario'}
                                </span>
                                {!preview.to_email && <Badge className="bg-amber-100 text-amber-700 text-[9px]">Mancante</Badge>}
                            </div>
                            <div className="flex items-center gap-2">
                                <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                <span className="text-slate-500 w-8">Ogg:</span>
                                <span className="font-medium text-slate-800" data-testid="email-preview-subject">{preview.subject}</span>
                            </div>
                            {preview.has_attachment && (
                                <div className="flex items-center gap-2">
                                    <Paperclip className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    <span className="text-slate-500 w-8">All:</span>
                                    <Badge className="bg-blue-50 text-blue-700 text-[10px]">
                                        <Paperclip className="h-2.5 w-2.5 mr-0.5" />{preview.attachment_name}
                                    </Badge>
                                </div>
                            )}
                        </div>

                        {/* Email body preview */}
                        <div className="flex-1 min-h-0 border rounded-lg overflow-hidden bg-white" data-testid="email-preview-body">
                            <iframe
                                ref={iframeRef}
                                title="Email Preview"
                                className="w-full border-0"
                                style={{ height: '340px' }}
                                sandbox="allow-same-origin"
                            />
                        </div>
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
