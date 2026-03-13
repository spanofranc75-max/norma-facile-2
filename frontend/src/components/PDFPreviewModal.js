/**
 * PDF Preview Modal — iframe blob-based renderer.
 * Fetches PDF with Bearer token, creates blob URL, shows in iframe.
 */
import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../lib/utils';

function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    if (token) return { 'Authorization': `Bearer ${token}` };
    return {};
}

export function PDFPreviewModal({ open, onClose, pdfUrl, title }) {
    const [loading, setLoading] = useState(false);
    const [blobUrl, setBlobUrl] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!open || !pdfUrl) return;

        let objectUrl = null;
        setLoading(true);
        setError(null);
        setBlobUrl(null);

        fetch(`${API_BASE}${pdfUrl}`, {
            headers: getAuthHeaders(),
        })
            .then(r => {
                if (!r.ok) throw new Error(`Errore HTTP ${r.status}`);
                return r.blob();
            })
            .then(blob => {
                objectUrl = URL.createObjectURL(blob);
                setBlobUrl(objectUrl);
            })
            .catch(e => {
                setError(e.message);
            })
            .finally(() => {
                setLoading(false);
            });

        return () => {
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [open, pdfUrl]);

    useEffect(() => {
        if (!open && blobUrl) {
            URL.revokeObjectURL(blobUrl);
            setBlobUrl(null);
        }
    }, [open]);

    const handleDownload = async () => {
        try {
            const res = await fetch(`${API_BASE}${pdfUrl}`, { headers: getAuthHeaders() });
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'documento.pdf';
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-[900px] max-h-[95vh] flex flex-col p-0" data-testid="pdf-preview-modal">
                <DialogHeader className="px-4 py-3 border-b border-slate-200">
                    <div className="flex items-center justify-between w-full">
                        <DialogTitle className="text-sm font-semibold text-[#1E293B]">
                            {title || 'Anteprima PDF'}
                        </DialogTitle>
                        <Button variant="outline" size="sm" onClick={handleDownload}
                            className="text-xs h-8" data-testid="btn-download-pdf-modal">
                            <Download className="h-3.5 w-3.5 mr-1" /> Scarica
                        </Button>
                    </div>
                </DialogHeader>
                <div className="flex-1 overflow-hidden bg-slate-200 flex justify-center items-center"
                    style={{ minHeight: '600px', maxHeight: '75vh' }}>
                    {loading && (
                        <div className="text-center">
                            <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                            <p className="text-xs text-slate-500">Generazione anteprima...</p>
                        </div>
                    )}
                    {error && (
                        <div className="text-center px-4">
                            <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                            <p className="text-sm text-red-600 mb-1">Errore caricamento PDF</p>
                            <p className="text-xs text-slate-500">{error}</p>
                        </div>
                    )}
                    {blobUrl && (
                        <iframe
                            src={blobUrl}
                            className="w-full h-full border-0"
                            style={{ minHeight: '600px' }}
                            title="PDF Preview"
                        />
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

export function PDFPreviewButton({ pdfUrl, title, variant = 'outline', size = 'sm', className = '' }) {
    const [open, setOpen] = useState(false);

    return (
        <>
            <Button
                variant={variant}
                size={size}
                data-testid="btn-preview-pdf"
                onClick={() => setOpen(true)}
                className={`text-xs ${className}`}
            >
                <Eye className="h-3.5 w-3.5 mr-1.5" /> Anteprima
            </Button>
            <PDFPreviewModal
                open={open}
                onClose={() => setOpen(false)}
                pdfUrl={pdfUrl}
                title={title}
            />
        </>
    );
}
