/**
 * PDF Preview Modal — In-app PDF viewer.
 * Fetches PDF via authenticated request, converts to base64 data URL for display.
 */
import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../lib/utils';

export function PDFPreviewModal({ open, onClose, pdfUrl, title }) {
    const [loading, setLoading] = useState(false);
    const [dataUrl, setDataUrl] = useState(null);
    const [error, setError] = useState(null);
    const prevUrlRef = useRef(null);

    useEffect(() => {
        if (!open || !pdfUrl) return;

        let cancelled = false;
        setLoading(true);
        setError(null);
        setDataUrl(null);

        fetch(`${API_BASE}${pdfUrl}`, { credentials: 'include' })
            .then(r => {
                if (!r.ok) throw new Error(`Errore ${r.status}`);
                return r.arrayBuffer();
            })
            .then(buffer => {
                if (cancelled) return;
                const bytes = new Uint8Array(buffer);
                let binary = '';
                for (let i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                const b64 = btoa(binary);
                const url = `data:application/pdf;base64,${b64}`;
                setDataUrl(url);
                prevUrlRef.current = url;
            })
            .catch(e => {
                if (!cancelled) setError(e.message);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [open, pdfUrl]);

    const handleDownload = () => {
        const a = document.createElement('a');
        a.href = `${API_BASE}${pdfUrl}`;
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
                        <Button variant="outline" size="sm" data-testid="btn-download-pdf-modal" onClick={handleDownload} className="text-xs h-8">
                            <Download className="h-3.5 w-3.5 mr-1" /> Scarica
                        </Button>
                    </div>
                </DialogHeader>
                <div className="flex-1 min-h-[600px] bg-slate-100 relative">
                    {loading && (
                        <div className="absolute inset-0 flex items-center justify-center z-10">
                            <div className="text-center">
                                <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                                <p className="text-xs text-slate-500">Generazione anteprima...</p>
                            </div>
                        </div>
                    )}
                    {error && (
                        <div className="absolute inset-0 flex items-center justify-center z-10">
                            <div className="text-center px-4">
                                <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                                <p className="text-sm text-red-500 mb-2">{error}</p>
                            </div>
                        </div>
                    )}
                    {dataUrl && (
                        <embed
                            src={dataUrl}
                            type="application/pdf"
                            data-testid="pdf-embed"
                            className="w-full border-0"
                            style={{ minHeight: '600px', height: '75vh' }}
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
