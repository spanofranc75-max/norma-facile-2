/**
 * DNSHSection — Archivio DNSH / Requisiti Ambientali PNRR.
 * AI Vision analizza documenti per diciture materiale riciclato, sostenibilità, CAM.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Leaf, Upload, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function DNSHSection({ commessaId }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const fileRef = useRef(null);

    const fetchData = useCallback(async () => {
        try {
            const res = await apiRequest(`/sicurezza/dnsh/${commessaId}`);
            setItems(res.dnsh_data || []);
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleAnalyze = async (file) => {
        setAnalyzing(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('commessa_id', commessaId);

            const res = await fetch(`${API}/api/sicurezza/dnsh/analyze`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            if (!res.ok) throw new Error('Analisi fallita');
            const data = await res.json();
            const analysis = data.analysis || {};

            // Save if we got results
            if (analysis.ha_riferimenti_dnsh !== undefined) {
                await apiRequest('/sicurezza/dnsh/save', {
                    method: 'POST',
                    body: { commessa_id: commessaId, ...analysis },
                });
                toast.success(analysis.ha_riferimenti_dnsh ? 'Riferimenti DNSH trovati!' : 'Nessun riferimento DNSH nel documento');
                fetchData();
            }
        } catch (e) {
            toast.error(e.message);
        } finally {
            setAnalyzing(false);
            if (fileRef.current) fileRef.current.value = '';
        }
    };

    if (loading) return <div className="text-center py-4"><Loader2 className="h-4 w-4 animate-spin mx-auto text-slate-400" /></div>;

    const hasDnsh = items.some(i => i.ha_riferimenti_dnsh);

    return (
        <div className="space-y-3" data-testid="dnsh-section">
            {/* Status */}
            <div className={`flex items-center gap-2 p-2.5 rounded-lg text-xs font-medium ${hasDnsh ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-50 text-slate-500 border border-slate-200'}`}>
                {hasDnsh ? <CheckCircle2 className="h-4 w-4" /> : <Leaf className="h-4 w-4" />}
                {hasDnsh ? `${items.filter(i => i.ha_riferimenti_dnsh).length} documento/i con riferimenti DNSH` : 'Nessun dato DNSH. Analizza un certificato o DDT.'}
            </div>

            {/* Upload + Analyze */}
            <input ref={fileRef} type="file" accept="image/*,.pdf" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleAnalyze(f); }}
                data-testid="dnsh-file-input"
            />
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={analyzing} className="w-full" data-testid="btn-analyze-dnsh">
                {analyzing ? <><Loader2 className="h-3 w-3 animate-spin mr-1" /> Analisi AI in corso...</> : <><Upload className="h-3 w-3 mr-1" /> Analizza Documento per DNSH</>}
            </Button>

            {/* Results */}
            {items.length > 0 && (
                <div className="space-y-2">
                    {items.map(d => (
                        <div key={d.dnsh_id} className={`border rounded-lg p-3 bg-white ${d.ha_riferimenti_dnsh ? 'border-emerald-200' : 'border-slate-200'}`} data-testid={`dnsh-${d.dnsh_id}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <Badge className={`${d.ha_riferimenti_dnsh ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'} text-[10px]`}>
                                    {d.ha_riferimenti_dnsh ? 'DNSH OK' : 'No DNSH'}
                                </Badge>
                                {d.conformita_cam && <Badge className="bg-blue-100 text-blue-700 text-[10px]">CAM</Badge>}
                                {d.percentuale_riciclato && <Badge className="bg-green-100 text-green-700 text-[10px]">{d.percentuale_riciclato} riciclato</Badge>}
                            </div>
                            {d.certificazioni_ambientali?.length > 0 && (
                                <div className="flex gap-1 flex-wrap mb-1">
                                    {d.certificazioni_ambientali.map((c, i) => (
                                        <span key={i} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{c}</span>
                                    ))}
                                </div>
                            )}
                            {d.note && <p className="text-xs text-slate-500 mt-1">{d.note}</p>}
                            <p className="text-[10px] text-slate-400 mt-1">{new Date(d.created_at).toLocaleDateString('it-IT')}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
