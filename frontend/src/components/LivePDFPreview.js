/**
 * LivePDFPreview — Pannello laterale con anteprima PDF live.
 * Genera il PDF dai dati correnti del form senza salvare.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { RefreshCw, Loader2, X, Maximize2, Minimize2 } from 'lucide-react';
import { API_BASE } from '../lib/utils';

export function LivePDFPreview({ formData, totals, onClose }) {
    const [blobUrl, setBlobUrl] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(false);
    const prevBlobRef = useRef(null);

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
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            const b64 = btoa(binary);
            const url = `data:application/pdf;base64,${b64}`;
            if (prevBlobRef.current) URL.revokeObjectURL(prevBlobRef.current);
            prevBlobRef.current = url;
            setBlobUrl(url);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [formData, totals]);

    // Generate on mount
    useEffect(() => {
        generatePreview();
        return () => {
            if (prevBlobRef.current) URL.revokeObjectURL(prevBlobRef.current);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div
            data-testid="live-pdf-preview-panel"
            className={`flex flex-col border-l border-slate-200 bg-slate-50 transition-all duration-300 ${expanded ? 'fixed inset-0 z-50 bg-white border-0' : ''}`}
        >
            {/* Toolbar */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-200 bg-white shrink-0">
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Anteprima PDF
                </span>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="sm"
                        data-testid="btn-refresh-preview"
                        onClick={generatePreview}
                        disabled={loading}
                        className="h-7 px-2 text-xs"
                        title="Aggiorna anteprima"
                    >
                        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                        <span className="ml-1">Aggiorna</span>
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpanded(e => !e)}
                        className="h-7 w-7 p-0"
                        title={expanded ? 'Riduci' : 'Espandi'}
                    >
                        {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        data-testid="btn-close-preview"
                        onClick={onClose}
                        className="h-7 w-7 p-0"
                        title="Chiudi anteprima"
                    >
                        <X className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </div>

            {/* PDF Content */}
            <div className="flex-1 relative min-h-0">
                {loading && !blobUrl && (
                    <div className="absolute inset-0 flex items-center justify-center bg-slate-50">
                        <div className="text-center">
                            <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                            <p className="text-xs text-slate-500">Generazione anteprima...</p>
                        </div>
                    </div>
                )}
                {loading && blobUrl && (
                    <div className="absolute top-2 right-2 z-10 bg-white/90 rounded-full p-1.5 shadow-sm">
                        <Loader2 className="h-4 w-4 animate-spin text-[#0055FF]" />
                    </div>
                )}
                {error && (
                    <div className="absolute inset-0 flex items-center justify-center bg-slate-50">
                        <div className="text-center px-4">
                            <p className="text-sm text-red-500 mb-2">{error}</p>
                            <Button variant="outline" size="sm" onClick={generatePreview}>
                                Riprova
                            </Button>
                        </div>
                    </div>
                )}
                {blobUrl && (
                    <embed
                        src={blobUrl}
                        type="application/pdf"
                        data-testid="live-pdf-iframe"
                        className="w-full h-full border-0"
                        style={{ minHeight: expanded ? '100vh' : '700px' }}
                    />
                )}
            </div>
        </div>
    );
}
