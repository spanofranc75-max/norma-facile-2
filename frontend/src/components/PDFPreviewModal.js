/**
 * PDF Preview Modal — JavaScript-based PDF renderer.
 * Uses react-pdf (PDF.js) to render PDF pages on canvas.
 * Does NOT depend on browser PDF plugins, iframe, embed, or blob URLs.
 */
import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2, AlertTriangle, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';
import { API_BASE } from '../lib/utils';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

export function PDFPreviewModal({ open, onClose, pdfUrl, title }) {
    const [loading, setLoading] = useState(false);
    const [pdfData, setPdfData] = useState(null);
    const [error, setError] = useState(null);
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.2);
    const containerRef = useRef(null);

    useEffect(() => {
        if (!open || !pdfUrl) return;

        let cancelled = false;
        setLoading(true);
        setError(null);
        setPdfData(null);
        setPageNumber(1);
        setNumPages(null);

        fetch(`${API_BASE}${pdfUrl}`, { credentials: 'include' })
            .then(r => {
                if (!r.ok) throw new Error(`Errore HTTP ${r.status}`);
                return r.arrayBuffer();
            })
            .then(buffer => {
                if (!cancelled) {
                    setPdfData({ data: buffer });
                }
            })
            .catch(e => {
                if (!cancelled) setError(e.message);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [open, pdfUrl]);

    const onDocumentLoadSuccess = ({ numPages: n }) => {
        setNumPages(n);
    };

    const handleDownload = async () => {
        try {
            const res = await fetch(`${API_BASE}${pdfUrl}`, { credentials: 'include' });
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `documento.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            window.open(`${API_BASE}${pdfUrl}`, '_blank');
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
                        <div className="flex items-center gap-2">
                            {numPages && numPages > 1 && (
                                <div className="flex items-center gap-1 mr-2">
                                    <Button variant="ghost" size="icon" className="h-7 w-7"
                                        disabled={pageNumber <= 1}
                                        onClick={() => setPageNumber(p => Math.max(1, p - 1))}
                                        data-testid="pdf-prev-page">
                                        <ChevronLeft className="h-4 w-4" />
                                    </Button>
                                    <span className="text-xs text-slate-500 min-w-[60px] text-center">
                                        {pageNumber} / {numPages}
                                    </span>
                                    <Button variant="ghost" size="icon" className="h-7 w-7"
                                        disabled={pageNumber >= numPages}
                                        onClick={() => setPageNumber(p => Math.min(numPages, p + 1))}
                                        data-testid="pdf-next-page">
                                        <ChevronRight className="h-4 w-4" />
                                    </Button>
                                </div>
                            )}
                            <Button variant="ghost" size="icon" className="h-7 w-7"
                                onClick={() => setScale(s => Math.max(0.5, s - 0.2))}
                                data-testid="pdf-zoom-out">
                                <ZoomOut className="h-4 w-4" />
                            </Button>
                            <span className="text-xs text-slate-500 w-10 text-center">{Math.round(scale * 100)}%</span>
                            <Button variant="ghost" size="icon" className="h-7 w-7"
                                onClick={() => setScale(s => Math.min(3, s + 0.2))}
                                data-testid="pdf-zoom-in">
                                <ZoomIn className="h-4 w-4" />
                            </Button>
                            <Button variant="outline" size="sm" onClick={handleDownload}
                                className="text-xs h-8 ml-2" data-testid="btn-download-pdf-modal">
                                <Download className="h-3.5 w-3.5 mr-1" /> Scarica
                            </Button>
                        </div>
                    </div>
                </DialogHeader>
                <div ref={containerRef}
                    className="flex-1 overflow-auto bg-slate-200 flex justify-center"
                    style={{ minHeight: '600px', maxHeight: '75vh' }}>
                    {loading && (
                        <div className="flex items-center justify-center w-full">
                            <div className="text-center">
                                <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                                <p className="text-xs text-slate-500">Generazione anteprima...</p>
                            </div>
                        </div>
                    )}
                    {error && (
                        <div className="flex items-center justify-center w-full">
                            <div className="text-center px-4">
                                <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                                <p className="text-sm text-red-600 mb-1">Errore caricamento PDF</p>
                                <p className="text-xs text-slate-500">{error}</p>
                            </div>
                        </div>
                    )}
                    {pdfData && (
                        <Document
                            file={pdfData}
                            onLoadSuccess={onDocumentLoadSuccess}
                            onLoadError={(err) => setError(err.message)}
                            loading={null}
                            className="py-4"
                        >
                            <Page
                                pageNumber={pageNumber}
                                scale={scale}
                                renderTextLayer={true}
                                renderAnnotationLayer={true}
                                loading={null}
                                className="shadow-lg"
                            />
                        </Document>
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
