/**
 * PDF Preview Modal — genera PDF nel browser con jsPDF (nessuna chiamata backend).
 */
import { useState, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../lib/utils';
import { generatePreventivoFrontend } from '../services/pdfGenerator';

function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    if (token) return { 'Authorization': 'Bearer ' + token };
    return {};
}

async function fetchPreventivoData(prevId) {
    const res = await fetch(API_BASE + '/preventivi/' + prevId, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Errore caricamento preventivo: ' + res.status);
    return res.json();
}

async function fetchCompanyData() {
    try {
        const res = await fetch(API_BASE + '/settings/company', { headers: getAuthHeaders() });
        if (!res.ok) return {};
        return res.json();
    } catch { return {}; }
}

async function fetchClientData(clientId) {
    if (!clientId) return {};
    try {
        const res = await fetch(API_BASE + '/clients/' + clientId, { headers: getAuthHeaders() });
        if (!res.ok) return {};
        return res.json();
    } catch { return {}; }
}

export function PDFPreviewModal({ open, onClose, pdfUrl, title, preventivoId }) {
    const [loading, setLoading] = useState(false);
    const [blobUrl, setBlobUrl] = useState(null);
    const [error, setError] = useState(null);

    const generateAndShow = useCallback(async () => {
        if (!open) return;
        setLoading(true);
        setError(null);
        setBlobUrl(null);
        try {
            // Estrae l'ID dal pdfUrl se preventivoId non è passato direttamente
            const id = preventivoId || (pdfUrl && pdfUrl.match(/\/preventivi\/([^\/]+)\/pdf/)?.[1]);
            if (!id) throw new Error('ID preventivo non trovato');

            const [prev, company] = await Promise.all([
                fetchPreventivoData(id),
                fetchCompanyData(),
            ]);
            const client = await fetchClientData(prev.client_id);
            const doc = generatePreventivoFrontend(prev, company, client);
            const pdfBlob = doc.output('blob');
            const url = URL.createObjectURL(pdfBlob);
            setBlobUrl(url);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [open, pdfUrl, preventivoId]);

    // Genera quando si apre il modal
    useState(() => {
        if (open) generateAndShow();
    });

    // Cleanup blob URL quando si chiude
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
                            disabled={!blobUrl}
                            className="text-xs h-8" data-testid="btn-download-pdf-modal">
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
                    {error && (
                        <div className="text-center px-4">
                            <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                            <p className="text-sm text-red-600 mb-1">Errore generazione PDF</p>
                            <p className="text-xs text-slate-500">{error}</p>
                            <Button size="sm" className="mt-3" onClick={generateAndShow}>Riprova</Button>
                        </div>
                    )}
                    {blobUrl && (
                        <iframe
                            src={blobUrl}
                            className="w-full border-0"
                            style={{ height: '75vh' }}
                            title="PDF Preview"
                        />
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
