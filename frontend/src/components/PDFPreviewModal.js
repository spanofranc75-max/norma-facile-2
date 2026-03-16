/**
 * PDF Preview Modal — genera PDF nel browser con jsPDF.
 * Zero chiamate backend per il PDF.
 */
import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../lib/utils';
import { generatePreventivoFrontend } from '../services/pdfGenerator';

function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

export function PDFPreviewModal({ open, onClose, pdfUrl, title, preventivoId }) {
    const [loading, setLoading] = useState(false);
    const [blobUrl, setBlobUrl] = useState(null);
    const [error, setError] = useState(null);

    const extractId = (url) => {
        if (!url) return null;
        const m = url.match(/\/preventivi\/([^\/]+)\/pdf/);
        return m ? m[1] : null;
    };

    const generate = useCallback(async () => {
        const id = preventivoId || extractId(pdfUrl);
        if (!id) { setError('ID preventivo non trovato'); return; }
        setLoading(true);
        setError(null);
        setBlobUrl(null);
        try {
            const [prevRes, compRes] = await Promise.all([
                fetch(API_BASE + '/preventivi/' + id, { headers: getAuthHeaders() }),
                fetch(API_BASE + '/settings/company', { headers: getAuthHeaders() }),
            ]);
            if (!prevRes.ok) throw new Error('Errore caricamento preventivo: ' + prevRes.status);
            const prev = await prevRes.json();
            const company = compRes.ok ? await compRes.json() : {};
            let client = {};
            if (prev.client_id) {
                const cRes = await fetch(API_BASE + '/clients/' + prev.client_id, { headers: getAuthHeaders() });
                if (cRes.ok) client = await cRes.json();
            }
            const doc = generatePreventivoFrontend(prev, company, client);
            const blob = doc.output('blob');
            const url = URL.createObjectURL(blob);
            setBlobUrl(url);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [pdfUrl, preventivoId]);

    useEffect(() => {
        if (open) generate();
        return () => { if (blobUrl) { URL.revokeObjectURL(blobUrl); setBlobUrl(null); } };
    }, [open]);

    const handleClose = () => {
        if (blobUrl) URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
        onClose();
    };

    const handleDownload = () => {
        if (!blobUrl) return;
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = (title || 'preventivo') + '.pdf';
        a.click();
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
            <DialogContent className="sm:max-w-[900px] max-h-[95vh] flex flex-col p-0" data-testid="pdf-preview-modal">
                <DialogHeader className="px-4 py-3 border-b border-slate-200 shrink-0">
                    <div className="flex items-center justify-between w-full">
                        <DialogTitle className="text-sm font-semibold text-[#1E293B]">
                            {title || 'Anteprima PDF'}
                        </DialogTitle>
                        <Button variant="outline" size="sm" onClick={handleDownload}
                            disabled={!blobUrl} className="text-xs h-8" data-testid="btn-download-pdf-modal">
                            <Download className="h-3.5 w-3.5 mr-1" /> Scarica
                        </Button>
                    </div>
                </DialogHeader>
                <div className="flex-1 overflow-hidden bg-slate-200 flex justify-center items-center" style={{ minHeight: '70vh' }}>
                    {loading && (
                        <div className="text-center">
                            <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                            <p className="text-xs text-slate-500">Generazione PDF...</p>
                        </div>
                    )}
                    {error && !loading && (
                        <div className="text-center px-4">
                            <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                            <p className="text-sm text-red-600 mb-1">Errore generazione PDF</p>
                            <p className="text-xs text-slate-500">{error}</p>
                            <Button size="sm" className="mt-3 text-xs" onClick={generate}>Riprova</Button>
                        </div>
                    )}
                    {blobUrl && !loading && (
                        <iframe src={blobUrl} className="w-full border-0"
                            style={{ height: '75vh' }} title="PDF Preview" />
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

export function PDFPreviewButton({ pdfUrl, title, preventivoId, variant = 'outline', size = 'sm', className = '' }) {
    const [open, setOpen] = useState(false);
    return (
        <>
            <Button variant={variant} size={size} data-testid="btn-preview-pdf"
                onClick={() => setOpen(true)} className={'text-xs ' + className}>
                <Eye className="h-3.5 w-3.5 mr-1.5" /> Anteprima
            </Button>
            <PDFPreviewModal open={open} onClose={() => setOpen(false)}
                pdfUrl={pdfUrl} title={title} preventivoId={preventivoId} />
        </>
    );
        }
