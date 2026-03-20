/**
 * ConsegneSection — Consegne al cliente (DDT + DoP + CE package)
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { useState } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Truck, Plus, Download, Loader2 } from 'lucide-react';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

export default function ConsegneSection({ commessaId, commessaNumero, consegne, onRefresh }) {
    const [consegnaLoading, setConsegnaLoading] = useState(false);
    const [consegnaDialogOpen, setConsegnaDialogOpen] = useState(false);
    const [consegnaForm, setConsegnaForm] = useState({ ddt_number: '', peso_kg: 0, num_colli: 1, note: '' });
    const [preventivoLines, setPreventivoLines] = useState([]);
    const [selectedLineIndices, setSelectedLineIndices] = useState([]);

    const openConsegnaDialog = async () => {
        try {
            const commData = await apiRequest(`/commesse/${commessaId}`);
            const prevId = commData?.preventivo_id || commData?.moduli?.preventivo_id || commData?.linked_preventivo_id;
            if (prevId) {
                const prev = await apiRequest(`/preventivi/${prevId}`);
                const lines = prev?.lines || [];
                setPreventivoLines(lines);
                setSelectedLineIndices(lines.map((_, i) => i));
            } else {
                setPreventivoLines([]);
                setSelectedLineIndices([]);
            }
        } catch { setPreventivoLines([]); setSelectedLineIndices([]); }
        setConsegnaForm({ ddt_number: '', peso_kg: 0, num_colli: 1, note: '' });
        setConsegnaDialogOpen(true);
    };

    const handleCreaConsegna = async () => {
        setConsegnaLoading(true);
        try {
            const body = {
                ddt_number: consegnaForm.ddt_number || null,
                peso_kg: consegnaForm.peso_kg || 0,
                num_colli: consegnaForm.num_colli || 1,
                note: consegnaForm.note || '',
                selected_line_indices: preventivoLines.length > 0 ? selectedLineIndices : null,
            };
            const result = await apiRequest(`/commesse/${commessaId}/consegne`, { method: 'POST', body });
            toast.success(result.message || 'Consegna creata');
            setConsegnaDialogOpen(false);
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
        finally { setConsegnaLoading(false); }
    };

    const handleDownloadPacchetto = async (consegnaId) => {
        try {
            await downloadPdfBlob(`/commesse/${commessaId}/consegne/${consegnaId}/pacchetto-pdf`, `Pacchetto_Consegna_${consegnaId}.pdf`);
            toast.success('Pacchetto DDT + DoP + CE scaricato');
        } catch (e) { toast.error(e.message); }
    };

    return (
        <>
            <div className="space-y-2" data-testid="consegne-section">
                <div className="flex gap-2 flex-wrap mb-2">
                    <Button size="sm" variant="outline" className="text-xs" onClick={openConsegnaDialog} data-testid="btn-new-consegna">
                        <Plus className="h-3 w-3 mr-1" /> Nuova Consegna
                    </Button>
                </div>
                {consegne.length === 0 && <p className="text-xs text-slate-400 italic">Nessuna consegna registrata.</p>}
                {consegne.map(c => (
                    <div key={c.consegna_id} className="flex items-center gap-2 p-2 bg-white rounded border text-xs">
                        <Truck className="h-3.5 w-3.5 text-[#0055FF] shrink-0" />
                        <span className="font-medium">{c.ddt_number || c.consegna_id}</span>
                        <span className="text-slate-400">{new Date(c.data_consegna).toLocaleDateString('it-IT')}</span>
                        {c.peso_kg > 0 && <Badge variant="secondary" className="text-[9px]">{c.peso_kg} kg</Badge>}
                        <div className="flex-1" />
                        <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => handleDownloadPacchetto(c.consegna_id)}>
                            <Download className="h-3 w-3 mr-0.5" /> PDF
                        </Button>
                    </div>
                ))}
            </div>

            {/* Consegna Dialog */}
            <Dialog open={consegnaDialogOpen} onOpenChange={setConsegnaDialogOpen}>
                <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Truck className="h-5 w-5 text-[#0055FF]" /> Nuova Consegna
                        </DialogTitle>
                        {commessaNumero && <DialogDescription>Commessa {commessaNumero}</DialogDescription>}
                    </DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label className="text-xs">N° DDT</Label>
                                <Input value={consegnaForm.ddt_number} onChange={e => setConsegnaForm(f => ({ ...f, ddt_number: e.target.value }))} className="h-8 text-sm" placeholder="Auto" data-testid="consegna-ddt" />
                            </div>
                            <div>
                                <Label className="text-xs">Peso (kg)</Label>
                                <Input type="number" value={consegnaForm.peso_kg} onChange={e => setConsegnaForm(f => ({ ...f, peso_kg: parseFloat(e.target.value) || 0 }))} className="h-8 text-sm" />
                            </div>
                            <div>
                                <Label className="text-xs">N° Colli</Label>
                                <Input type="number" value={consegnaForm.num_colli} onChange={e => setConsegnaForm(f => ({ ...f, num_colli: parseInt(e.target.value) || 1 }))} className="h-8 text-sm" />
                            </div>
                        </div>
                        {preventivoLines.length > 0 && (
                            <div>
                                <Label className="text-xs font-medium mb-1 block">Righe del preventivo da includere nel DDT:</Label>
                                <div className="border rounded-md max-h-40 overflow-y-auto p-2 space-y-1">
                                    {preventivoLines.map((line, idx) => (
                                        <label key={idx} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 p-1 rounded">
                                            <Checkbox checked={selectedLineIndices.includes(idx)} onCheckedChange={checked => {
                                                setSelectedLineIndices(prev => checked ? [...prev, idx] : prev.filter(i => i !== idx));
                                            }} />
                                            <span className="flex-1 truncate">{line.descrizione || line.description || `Riga ${idx + 1}`}</span>
                                            <span className="text-slate-400">{line.quantita || line.qty || ''} {line.unita_misura || ''}</span>
                                            {(line.importo || line.total) && <span className="font-medium">{fmtEur(line.importo || line.total)}</span>}
                                        </label>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div>
                            <Label className="text-xs">Note</Label>
                            <Textarea value={consegnaForm.note} onChange={e => setConsegnaForm(f => ({ ...f, note: e.target.value }))} className="h-16 text-sm" />
                        </div>
                    </div>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" size="sm" onClick={() => setConsegnaDialogOpen(false)}>Annulla</Button>
                        <Button size="sm" className="bg-[#0055FF] text-white" onClick={handleCreaConsegna} disabled={consegnaLoading} data-testid="btn-conferma-consegna">
                            {consegnaLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Truck className="h-3 w-3 mr-1" />}
                            Crea Consegna
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
