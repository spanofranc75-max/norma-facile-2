/**
 * PDF Preview Modal — In-app PDF viewer
 * Loads PDF directly from API URL using same-origin cookies.
 */
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2 } from 'lucide-react';
import { API_BASE } from '../lib/utils';

export function PDFPreviewModal({ open, onClose, pdfUrl, title }) {
    const [loading, setLoading] = useState(true);

    const fullUrl = `${API_BASE}${pdfUrl}`;

    const handleDownload = () => {
        const a = document.createElement('a');
        a.href = fullUrl;
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
                    {open && (
                        <iframe
                            src={fullUrl}
                            data-testid="pdf-iframe"
                            className="w-full h-full min-h-[600px] border-0"
                            title="PDF Preview"
                            onLoad={() => setLoading(false)}
                            onError={() => setLoading(false)}
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
