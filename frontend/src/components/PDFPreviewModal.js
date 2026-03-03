/**
 * PDF Preview Modal — In-app PDF viewer
 * Fetches PDF with credentials and displays via blob URL.
 */
import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2 } from 'lucide-react';
import { API_BASE } from '../lib/utils';

export function PDFPreviewModal({ open, onClose, pdfUrl, title }) {
    const [loading, setLoading] = useState(true);
    const [blobUrl, setBlobUrl] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (open && pdfUrl) {
            setLoading(true);
            setError(null);
            setBlobUrl(null);
            fetch(`${API_BASE}/api${pdfUrl}`, { credentials: 'include' })
                .then(r => {
                    if (!r.ok) throw new Error(`Errore ${r.status}`);
                    return r.blob();
                })
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    setBlobUrl(url);
                })
                .catch(e => setError(e.message))
                .finally(() => setLoading(false));
        }
        return () => {
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, pdfUrl]);

    const handleDownload = () => {
        const a = document.createElement('a');
        a.href = `${API_BASE}/api${pdfUrl}`;
        a.target = '_blank';
        a.rel = 'noopener';
        a.click();
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-[900px] max-h-[95vh] flex flex-col p-0" data-testid="pdf-preview-modal">
                <DialogHeader className="px-4 py-3 border-b border-slate-200 flex flex-row items-center justify-between">
                    <DialogTitle className="text-sm font-semibold text-[#1E293B]">
                        {title || 'Anteprima PDF'}
                    </DialogTitle>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" data-testid="btn-download-pdf" onClick={handleDownload} className="text-xs h-8">
                            <Download className="h-3.5 w-3.5 mr-1" /> Scarica
                        </Button>
                    </div>
                </DialogHeader>
                <div className="flex-1 min-h-[600px] bg-slate-100 relative">
                    {loading && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" />
                        </div>
                    )}
                    {error && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <p className="text-red-500 text-sm">{error}</p>
                        </div>
                    )}
                    {blobUrl && (
                        <iframe
                            src={blobUrl}
                            data-testid="pdf-iframe"
                            className="w-full h-full min-h-[600px] border-0"
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
                <Eye className="h-3.5 w-3.5 mr-1" /> Anteprima
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
