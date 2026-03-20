import { useState, useEffect } from 'react';
import { apiRequest } from '../../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { Trash2, Loader2 } from 'lucide-react';
import { useConfirm } from '../ConfirmProvider';

export default function DeployTab() {
    const confirm = useConfirm();
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(true);
    const [cleaning, setCleaning] = useState(false);
    const [keepClients, setKeepClients] = useState(true);
    const [keepVendors, setKeepVendors] = useState(true);
    const [result, setResult] = useState(null);

    useEffect(() => {
        (async () => {
            try {
                const data = await apiRequest('/admin/cleanup/preview');
                setPreview(data);
            } catch { /* silent */ }
            finally { setLoading(false); }
        })();
    }, []);

    const handleCleanup = async () => {
        if (!(await confirm('ATTENZIONE: Questa operazione cancella TUTTE le commesse, preventivi, fatture e altri dati operativi. Sei sicuro?'))) return;
        if (!(await confirm('ULTIMA CONFERMA: Hai fatto il backup? I dati verranno eliminati permanentemente.'))) return;

        setCleaning(true);
        setResult(null);
        try {
            const data = await apiRequest('/admin/cleanup/execute', {
                method: 'POST',
                body: { confirm: true, keep_clients: keepClients, keep_vendors: keepVendors },
            });
            setResult(data);
            toast.success('Pulizia completata');
            const p = await apiRequest('/admin/cleanup/preview');
            setPreview(p);
        } catch (e) { toast.error(e.message); }
        finally { setCleaning(false); }
    };

    return (
        <Card className="border-gray-200">
            <CardHeader className="bg-red-50 border-b border-gray-200 rounded-t-lg">
                <CardTitle className="text-red-800 flex items-center gap-2">
                    <Trash2 className="h-5 w-5" /> Preparazione Deploy / Pulizia DB
                </CardTitle>
                <CardDescription className="text-red-600">
                    Elimina i dati di test per partire con un database pulito. Fai PRIMA il backup!
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {/* Preview */}
                {loading ? (
                    <p className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Calcolo dati...</p>
                ) : preview && (
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Dati che verranno eliminati</p>
                        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-1.5">
                            {Object.entries(preview.operational_data || {}).filter(([, v]) => v > 0).map(([k, v]) => (
                                <div key={k} className="bg-red-50 border border-red-200 rounded px-2 py-1.5 text-center">
                                    <p className="text-sm font-bold text-red-700">{v}</p>
                                    <p className="text-[9px] text-red-500 leading-tight">{k}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Options */}
                <div className="space-y-3 border rounded-lg p-4 bg-amber-50 border-amber-200">
                    <h3 className="text-sm font-bold text-amber-800">Opzioni</h3>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input type="checkbox" checked={keepClients} onChange={e => setKeepClients(e.target.checked)} className="rounded" />
                        <span>Mantieni Clienti ({preview?.clients || 0})</span>
                    </label>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input type="checkbox" checked={keepVendors} onChange={e => setKeepVendors(e.target.checked)} className="rounded" />
                        <span>Mantieni Fornitori ({preview?.vendors || 0})</span>
                    </label>
                </div>

                {/* Execute */}
                <Button
                    onClick={handleCleanup}
                    disabled={cleaning}
                    variant="destructive"
                    className="w-full h-10"
                    data-testid="btn-execute-cleanup"
                >
                    {cleaning ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
                    {cleaning ? 'Pulizia in corso...' : 'Esegui Pulizia Database'}
                </Button>

                {/* Result */}
                {result && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4" data-testid="cleanup-result">
                        <p className="text-sm font-semibold text-emerald-800">{result.message}</p>
                        <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5 mt-2">
                            {Object.entries(result.deleted || {}).filter(([, v]) => v > 0).map(([k, v]) => (
                                <div key={k} className="bg-white border rounded px-2 py-1 text-center">
                                    <p className="text-sm font-bold text-slate-700">{v}</p>
                                    <p className="text-[9px] text-slate-400">{k} eliminati</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
