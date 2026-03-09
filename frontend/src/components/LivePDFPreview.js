/**
 * LivePDFPreview — Pannello laterale con anteprima PDF live.
 * Genera il PDF dai dati correnti del form senza salvare.
 * Uses react-pdf (PDF.js) for reliable rendering.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { RefreshCw, Loader2, X, Maximize2, Minimize2, ChevronLeft, ChevronRight } from 'lucide-react';
import { API_BASE } from '../lib/utils';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

export function LivePDFPreview({ formData, totals, onClose }) {
    const [pdfData, setPdfData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(false);
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);

    const generatePreview = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const payload = {
                ...formData,
                totals,
                lines: formData.lines.filter(l => l.description?.trim()),
            };
            const res = await fetch(`${API_BASE}/invoices/preview-pdf`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error(`Errore ${res.status}`);
            const buffer = await res.arrayBuffer();
            setPdfData({ data: buffer });
            setPageNumber(1);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [formData, totals]);

    useEffect(() => {
        generatePreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div
            data-testid="live-pdf-preview-panel"
            className={`flex flex-col border-l border-slate-200 bg-slate-50 transition-all duration-300 ${expanded ? 'fixed inset-0 z-50 bg-white border-0' : ''}`}
        >
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-200 bg-white shrink-0">
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Anteprima PDF
                </span>
                <div className="flex items-center gap-1">
                    {numPages && numPages > 1 && (
                        <div className="flex items-center gap-0.5 mr-1">
                            <Button variant="ghost" size="icon" className="h-6 w-6"
                                disabled={pageNumber <= 1}
                                onClick={() => setPageNumber(p => Math.max(1, p - 1))}>
                                <ChevronLeft className="h-3 w-3" />
                            </Button>
                            <span className="text-[10px] text-slate-500">{pageNumber}/{numPages}</span>
                            <Button variant="ghost" size="icon" className="h-6 w-6"
                                disabled={pageNumber >= numPages}
                                onClick={() => setPageNumber(p => Math.min(numPages, p + 1))}>
                                <ChevronRight className="h-3 w-3" />
                            </Button>
                        </div>
                    )}
                    <Button variant="ghost" size="sm" data-testid="btn-refresh-preview"
                        onClick={generatePreview} disabled={loading} className="h-7 px-2 text-xs" title="Aggiorna anteprima">
                        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                        <span className="ml-1">Aggiorna</span>
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setExpanded(e => !e)}
                        className="h-7 w-7 p-0" title={expanded ? 'Riduci' : 'Espandi'}>
                        {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
                    </Button>
                    <Button variant="ghost" size="sm" data-testid="btn-close-preview"
                        onClick={onClose} className="h-7 w-7 p-0" title="Chiudi anteprima">
                        <X className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </div>

            <div className="flex-1 relative min-h-0 overflow-auto bg-slate-200">
                {loading && !pdfData && (
                    <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
                        <div className="text-center">
                            <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                            <p className="text-xs text-slate-500">Generazione anteprima...</p>
                        </div>
                    </div>
                )}
                {loading && pdfData && (
                    <div className="absolute top-2 right-2 z-10 bg-white/90 rounded-full p-1.5 shadow-sm">
                        <Loader2 className="h-4 w-4 animate-spin text-[#0055FF]" />
                    </div>
                )}
                {error && (
                    <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
                        <div className="text-center px-4">
                            <p className="text-sm text-red-500 mb-2">{error}</p>
                            <Button variant="outline" size="sm" onClick={generatePreview}>Riprova</Button>
                        </div>
                    </div>
                )}
                {pdfData && (
                    <div className="flex justify-center py-4">
                        <Document
                            file={pdfData}
                            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                            onLoadError={(err) => setError(err.message)}
                            loading={null}
                        >
                            <Page
                                pageNumber={pageNumber}
                                scale={expanded ? 1.5 : 0.9}
                                renderTextLayer={true}
                                renderAnnotationLayer={true}
                                loading={null}
                                className="shadow-lg"
                            />
                        </Document>
                    </div>
                )}
            </div>
        </div>
    );
}
