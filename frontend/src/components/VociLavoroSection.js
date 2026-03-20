/**
 * VociLavoroSection — Gestione Voci di Lavoro per Cantieri Misti (Matrioska)
 * Permette di aggiungere/rimuovere voci con normative diverse alla stessa commessa.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Trash2, Hammer, LayoutGrid, Clock, Pencil } from 'lucide-react';

const CATEGORIE = [
    { value: 'EN_1090', label: 'Strutturale', subtitle: 'EN 1090', desc: 'Scale, balconi, soppalchi, capannoni', color: 'bg-blue-50 border-blue-300 text-blue-900', dot: 'bg-blue-500', iconBg: 'bg-blue-600', Icon: Hammer },
    { value: 'EN_13241', label: 'Cancello', subtitle: 'EN 13241', desc: 'Cancelli, portoni, chiusure industriali', color: 'bg-amber-50 border-amber-300 text-amber-900', dot: 'bg-amber-500', iconBg: 'bg-amber-600', Icon: LayoutGrid },
    { value: 'GENERICA', label: 'Generica', subtitle: 'No marcatura', desc: 'Riparazioni, manutenzioni, piccoli lavori', color: 'bg-slate-50 border-slate-300 text-slate-800', dot: 'bg-slate-500', iconBg: 'bg-slate-600', Icon: Clock },
];

const getCat = (tipo) => CATEGORIE.find(c => c.value === tipo) || CATEGORIE[2];

export default function VociLavoroSection({ commessaId, onVociChange }) {
    const [voci, setVoci] = useState([]);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingVoce, setEditingVoce] = useState(null);
    const [form, setForm] = useState({ descrizione: '', normativa_tipo: '', classe_exc: '', tipologia_chiusura: '' });

    const fetchVoci = useCallback(async () => {
        try {
            const data = await apiRequest(`/commesse/${commessaId}/voci/`);
            setVoci(data.voci || []);
            onVociChange?.(data.voci || []);
        } catch { /* silently ignore for commesse without voci */ }
    }, [commessaId, onVociChange]);

    useEffect(() => { fetchVoci(); }, [fetchVoci]);

    const resetForm = () => { setForm({ descrizione: '', normativa_tipo: '', classe_exc: '', tipologia_chiusura: '' }); setEditingVoce(null); };

    const handleSave = async () => {
        if (!form.normativa_tipo) { toast.error('Scegli il tipo di lavoro'); return; }
        if (!form.descrizione.trim()) { toast.error('Inserisci una descrizione'); return; }
        try {
            if (editingVoce) {
                await apiRequest(`/commesse/${commessaId}/voci/${editingVoce}`, { method: 'PUT', body: form });
                toast.success('Voce aggiornata');
            } else {
                await apiRequest(`/commesse/${commessaId}/voci/`, { method: 'POST', body: form });
                toast.success('Voce aggiunta');
            }
            setDialogOpen(false);
            resetForm();
            fetchVoci();
        } catch (e) { toast.error(e.message); }
    };

    const handleDelete = async (voceId, desc) => {
        if (!window.confirm(`Eliminare la voce "${desc}"?`)) return;
        try {
            await apiRequest(`/commesse/${commessaId}/voci/${voceId}`, { method: 'DELETE' });
            toast.success('Voce eliminata');
            fetchVoci();
        } catch (e) { toast.error(e.message); }
    };

    const openEdit = (v) => {
        setForm({ descrizione: v.descrizione, normativa_tipo: v.normativa_tipo, classe_exc: v.classe_exc || '', tipologia_chiusura: v.tipologia_chiusura || '' });
        setEditingVoce(v.voce_id);
        setDialogOpen(true);
    };

    return (
        <div data-testid="voci-lavoro-section">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <div>
                    <h3 className="text-sm font-semibold text-slate-800">Voci di Lavoro</h3>
                    <p className="text-[10px] text-slate-500">Aggiungi lavorazioni con normative diverse allo stesso cantiere</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => { resetForm(); setDialogOpen(true); }} className="text-xs h-8" data-testid="btn-add-voce">
                    <Plus className="h-3.5 w-3.5 mr-1" /> Aggiungi Voce
                </Button>
            </div>

            {/* Voci list */}
            {voci.length > 0 ? (
                <div className="space-y-2">
                    {voci.map(v => {
                        const cat = getCat(v.normativa_tipo);
                        return (
                            <div key={v.voce_id} className={`flex items-center gap-3 p-3 rounded-lg border-2 ${cat.color} transition-all`} data-testid={`voce-${v.voce_id}`}>
                                <div className={`w-9 h-9 rounded-lg ${cat.iconBg} flex items-center justify-center shrink-0`}>
                                    <cat.Icon className="h-4.5 w-4.5 text-white" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-sm truncate">{v.descrizione}</span>
                                        <Badge className={`text-[9px] ${cat.dot === 'bg-blue-500' ? 'bg-blue-100 text-blue-700' : cat.dot === 'bg-amber-500' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-600'}`}>
                                            {cat.subtitle}
                                        </Badge>
                                    </div>
                                    <p className="text-[10px] opacity-60 mt-0.5">
                                        {v.normativa_tipo === 'EN_1090' && v.classe_exc && `Classe ${v.classe_exc} — `}
                                        {v.normativa_tipo === 'EN_13241' && v.tipologia_chiusura && `${v.tipologia_chiusura} — `}
                                        {cat.desc}
                                    </p>
                                </div>
                                <div className="flex items-center gap-1 shrink-0">
                                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 opacity-60 hover:opacity-100" onClick={() => openEdit(v)} data-testid={`edit-voce-${v.voce_id}`}>
                                        <Pencil className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-400 hover:text-red-600 hover:bg-red-50" onClick={() => handleDelete(v.voce_id, v.descrizione)} data-testid={`delete-voce-${v.voce_id}`}>
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="text-center py-4 text-slate-400 text-xs border border-dashed border-slate-200 rounded-lg" data-testid="voci-empty">
                    <p className="font-medium">Nessuna voce aggiuntiva</p>
                    <p className="text-[10px] mt-1">La commessa usa la sua categoria principale. Aggiungi voci per cantieri misti.</p>
                </div>
            )}

            {/* Dialog */}
            <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
                <DialogContent className="max-w-md max-w-[95vw]" data-testid="voce-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-base font-bold">{editingVoce ? 'Modifica Voce' : 'Nuova Voce di Lavoro'}</DialogTitle>
                        <DialogDescription>Scegli il tipo e descrivi la lavorazione</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        {/* Category buttons */}
                        <div>
                            <Label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Tipo di Lavoro *</Label>
                            <div className="grid grid-cols-3 gap-2 mt-2">
                                {CATEGORIE.map(cat => {
                                    const isSelected = form.normativa_tipo === cat.value;
                                    return (
                                        <button
                                            key={cat.value}
                                            type="button"
                                            data-testid={`voce-cat-${cat.value.toLowerCase()}`}
                                            onClick={() => setForm(f => ({ ...f, normativa_tipo: cat.value, classe_exc: cat.value !== 'EN_1090' ? '' : f.classe_exc, tipologia_chiusura: cat.value !== 'EN_13241' ? '' : f.tipologia_chiusura }))}
                                            className={`relative rounded-xl border-2 p-2.5 text-left transition-all duration-200 cursor-pointer
                                                ${isSelected ? `${cat.color} ring-2 ring-offset-1 shadow-md` : `border-slate-200 bg-white hover:shadow-sm`}`}
                                        >
                                            <div className={`w-7 h-7 rounded-lg ${isSelected ? cat.iconBg : 'bg-slate-300'} flex items-center justify-center mb-1.5 transition-colors`}>
                                                <cat.Icon className="h-3.5 w-3.5 text-white" />
                                            </div>
                                            <p className={`font-bold text-xs leading-tight ${isSelected ? '' : 'text-slate-600'}`}>{cat.label}</p>
                                            <p className="text-[9px] opacity-60 mt-0.5">{cat.subtitle}</p>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {form.normativa_tipo && (
                            <div className="space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                                <div>
                                    <Label className="text-xs">Descrizione *</Label>
                                    <Input
                                        data-testid="voce-descrizione"
                                        value={form.descrizione}
                                        onChange={e => setForm(f => ({ ...f, descrizione: e.target.value }))}
                                        placeholder={form.normativa_tipo === 'EN_1090' ? 'es. Soppalco capannone' : form.normativa_tipo === 'EN_13241' ? 'es. Cancello carraio' : 'es. Riparazione ringhiera'}
                                        className="h-9"
                                    />
                                </div>

                                {form.normativa_tipo === 'EN_1090' && (
                                    <div>
                                        <Label className="text-xs text-blue-700">Classe di Esecuzione</Label>
                                        <select value={form.classe_exc} onChange={e => setForm(f => ({ ...f, classe_exc: e.target.value }))} className="w-full h-9 text-sm rounded-md border border-blue-200 bg-white px-2 shadow-sm" data-testid="voce-classe-exc">
                                            <option value="">-- Non specificata --</option>
                                            <option value="EXC1">EXC1 — Strutture leggere</option>
                                            <option value="EXC2">EXC2 — Standard</option>
                                            <option value="EXC3">EXC3 — Critiche</option>
                                            <option value="EXC4">EXC4 — Eccezionali</option>
                                        </select>
                                    </div>
                                )}

                                {form.normativa_tipo === 'EN_13241' && (
                                    <div>
                                        <Label className="text-xs text-amber-700">Tipologia</Label>
                                        <select value={form.tipologia_chiusura} onChange={e => setForm(f => ({ ...f, tipologia_chiusura: e.target.value }))} className="w-full h-9 text-sm rounded-md border border-amber-200 bg-white px-2 shadow-sm" data-testid="voce-tipologia">
                                            <option value="">-- Non specificata --</option>
                                            <option value="cancello">Cancello scorrevole/battente</option>
                                            <option value="portone">Portone industriale</option>
                                            <option value="porta">Porta pedonale</option>
                                            <option value="barriera">Barriera stradale</option>
                                        </select>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                    <DialogFooter className="gap-2 mt-2">
                        <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button
                            size="sm"
                            onClick={handleSave}
                            disabled={!form.normativa_tipo || !form.descrizione.trim()}
                            data-testid="btn-save-voce"
                            className={`text-white ${form.normativa_tipo === 'EN_1090' ? 'bg-blue-600 hover:bg-blue-700' : form.normativa_tipo === 'EN_13241' ? 'bg-amber-600 hover:bg-amber-700' : 'bg-slate-700 hover:bg-slate-800'}`}
                        >
                            {editingVoce ? 'Aggiorna' : 'Aggiungi Voce'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
