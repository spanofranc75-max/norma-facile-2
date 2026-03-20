/**
 * DopFrazionataSection — Gestione DoP Frazionate per consegne parziali.
 * Permette di creare DoP con suffissi (/A, /B, /C) legate a DDT specifici.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { FileStack, Plus, Download, Trash2, Loader2 } from 'lucide-react';

export default function DopFrazionataSection({ commessaId, onRefresh }) {
    const [dops, setDops] = useState([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [showCreate, setShowCreate] = useState(false);
    const [descrizione, setDescrizione] = useState('');
    const [note, setNote] = useState('');
    const [ddtList, setDdtList] = useState([]);
    const [selectedDdts, setSelectedDdts] = useState([]);
    const [generatingPdf, setGeneratingPdf] = useState(null);

    const API = process.env.REACT_APP_BACKEND_URL;

    const fetchDops = useCallback(async () => {
        try {
            const data = await apiRequest(`/fascicolo-tecnico/${commessaId}/dop-frazionate`);
            setDops(data.dop_frazionate || []);
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, [commessaId]);

    const fetchDDTs = useCallback(async () => {
        try {
            const data = await apiRequest(`/ddt?commessa_id=${commessaId}`);
            setDdtList((data.items || data.ddt || []).filter(d => d.ddt_type === 'vendita'));
        } catch { /* silent */ }
    }, [commessaId]);

    useEffect(() => { fetchDops(); }, [fetchDops]);

    const handleOpenCreate = () => {
        fetchDDTs();
        setShowCreate(true);
        setDescrizione('');
        setNote('');
        setSelectedDdts([]);
    };

    const handleCreate = async () => {
        setCreating(true);
        try {
            const res = await apiRequest(`/fascicolo-tecnico/${commessaId}/dop-frazionata`, {
                method: 'POST',
                body: { ddt_ids: selectedDdts, descrizione, note },
            });
            toast.success(res.message);
            setShowCreate(false);
            fetchDops();
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
        finally { setCreating(false); }
    };

    const handleDelete = async (dopId) => {
        if (!window.confirm('Eliminare questa DoP frazionata?')) return;
        try {
            await apiRequest(`/fascicolo-tecnico/${commessaId}/dop-frazionata/${dopId}`, { method: 'DELETE' });
            toast.success('DoP eliminata');
            fetchDops();
        } catch (e) { toast.error(e.message); }
    };

    const handlePdf = async (dopId, dopNumero) => {
        setGeneratingPdf(dopId);
        try {
            await downloadPdfBlob(`${API}/api/fascicolo-tecnico/${commessaId}/dop-frazionata/${dopId}/pdf`, `DoP_${dopNumero.replace('/', '_')}.pdf`);
            fetchDops();
        } catch (e) { toast.error(e.message); }
        finally { setGeneratingPdf(null); }
    };

    const toggleDdt = (ddtId) => {
        setSelectedDdts(prev => prev.includes(ddtId) ? prev.filter(d => d !== ddtId) : [...prev, ddtId]);
    };

    return (
        <Card className="border-indigo-200" data-testid="dop-frazionata-section">
            <CardHeader className="bg-indigo-50 border-b border-indigo-200 py-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2 text-indigo-800">
                        <FileStack className="h-4 w-4" /> DoP Frazionate
                        {dops.length > 0 && <Badge variant="outline" className="text-[10px] bg-indigo-100 border-indigo-300">{dops.length}</Badge>}
                    </CardTitle>
                    <Button size="sm" variant="outline" className="h-7 text-xs border-indigo-300 text-indigo-700" onClick={handleOpenCreate} data-testid="btn-new-dop">
                        <Plus className="h-3 w-3 mr-1" /> Nuova DoP
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="p-3">
                {loading ? (
                    <p className="text-xs text-slate-400 text-center py-4"><Loader2 className="h-4 w-4 animate-spin inline mr-1" />Caricamento...</p>
                ) : dops.length === 0 ? (
                    <p className="text-xs text-slate-400 text-center py-4">Nessuna DoP frazionata. Clicca "Nuova DoP" per crearne una.</p>
                ) : (
                    <div className="space-y-2">
                        {dops.map(dop => (
                            <div key={dop.dop_id} className="flex items-center justify-between p-2 border rounded-lg bg-white hover:bg-slate-50" data-testid={`dop-${dop.dop_id}`}>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono font-bold text-sm text-indigo-800">{dop.dop_numero}</span>
                                        <Badge variant="outline" className={`text-[9px] ${dop.stato === 'emessa' ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-amber-50 text-amber-700 border-amber-300'}`}>
                                            {dop.stato === 'emessa' ? 'Emessa' : 'Bozza'}
                                        </Badge>
                                    </div>
                                    <p className="text-[10px] text-slate-500 truncate">{dop.descrizione}</p>
                                    <p className="text-[10px] text-slate-400">{dop.materiali_tracciati?.length || 0} materiali — {dop.ddt_ids?.length || 0} DDT</p>
                                </div>
                                <div className="flex gap-1.5">
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-indigo-600" onClick={() => handlePdf(dop.dop_id, dop.dop_numero)} disabled={generatingPdf === dop.dop_id} data-testid={`btn-pdf-dop-${dop.dop_id}`}>
                                        {generatingPdf === dop.dop_id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3 mr-0.5" />}
                                        PDF
                                    </Button>
                                    {dop.stato !== 'emessa' && (
                                        <Button size="sm" variant="ghost" className="h-7 text-[10px] text-red-500" onClick={() => handleDelete(dop.dop_id)} data-testid={`btn-delete-dop-${dop.dop_id}`}>
                                            <Trash2 className="h-3 w-3" />
                                        </Button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>

            {/* Create Dialog */}
            <Dialog open={showCreate} onOpenChange={setShowCreate}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-base">Nuova DoP Frazionata</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label className="text-xs">Descrizione consegna</Label>
                            <Input value={descrizione} onChange={e => setDescrizione(e.target.value)} placeholder="Es: Consegna parziale travi principali" className="h-8 text-sm" data-testid="input-dop-descrizione" />
                        </div>
                        <div>
                            <Label className="text-xs">DDT associati (seleziona le consegne)</Label>
                            <div className="max-h-32 overflow-y-auto border rounded p-1.5 space-y-1">
                                {ddtList.length === 0 ? (
                                    <p className="text-[10px] text-slate-400 text-center py-2">Nessun DDT di vendita trovato</p>
                                ) : ddtList.map(ddt => (
                                    <label key={ddt.ddt_id} className={`flex items-center gap-2 text-xs cursor-pointer p-1 rounded ${selectedDdts.includes(ddt.ddt_id) ? 'bg-indigo-50' : ''}`}>
                                        <input type="checkbox" checked={selectedDdts.includes(ddt.ddt_id)} onChange={() => toggleDdt(ddt.ddt_id)} className="rounded" />
                                        <span className="font-mono font-semibold">{ddt.number}</span>
                                        <span className="text-slate-500 truncate">{ddt.client_name}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs">Note (opzionale)</Label>
                            <Input value={note} onChange={e => setNote(e.target.value)} placeholder="Note aggiuntive..." className="h-8 text-sm" />
                        </div>
                    </div>
                    <DialogFooter className="mt-3">
                        <Button variant="outline" size="sm" onClick={() => setShowCreate(false)} className="text-xs">Annulla</Button>
                        <Button size="sm" onClick={handleCreate} disabled={creating} className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="btn-confirm-dop">
                            {creating ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Plus className="h-3 w-3 mr-1" />}
                            Crea DoP
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
