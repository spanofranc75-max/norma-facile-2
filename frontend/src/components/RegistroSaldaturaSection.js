/**
 * RegistroSaldaturaSection — Registro Saldatura per Commessa (EN 1090 FPC Fase 2).
 * Log di tutte le saldature: giunto, saldatore, WPS, data, esito VT.
 * Filtro saldatori per processo/patentino valido.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { toast } from 'sonner';
import {
    Flame, Plus, Trash2, Edit2, CheckCircle, XCircle,
    Clock, Loader2, User, FileText, AlertTriangle, RefreshCw,
} from 'lucide-react';

const PROCESSI = [
    { value: '135', label: '135 — MIG/MAG' },
    { value: '111', label: '111 — SMAW (Elettrodo)' },
    { value: '141', label: '141 — TIG' },
    { value: '136', label: '136 — Filo Animato' },
    { value: '121', label: '121 — Arco Sommerso' },
];

const ESITI = [
    { value: 'da_eseguire', label: 'Da eseguire', color: 'bg-slate-100 text-slate-700', icon: Clock },
    { value: 'conforme', label: 'Conforme', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
    { value: 'non_conforme', label: 'Non conforme', color: 'bg-red-100 text-red-700', icon: XCircle },
];

const emptyForm = {
    giunto: '',
    posizione_dwg: '',
    saldatore_id: '',
    wps_id: '',
    processo: '135',
    data_esecuzione: new Date().toISOString().slice(0, 10),
    esito_vt: 'da_eseguire',
    note: '',
};

export default function RegistroSaldaturaSection({ commessaId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [form, setForm] = useState({ ...emptyForm });
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(null);

    // Saldatori idonei e WPS disponibili
    const [saldatoriIdonei, setSaldatoriIdonei] = useState([]);
    const [wpsList, setWpsList] = useState([]);
    const [loadingSaldatori, setLoadingSaldatori] = useState(false);

    const load = useCallback(async () => {
        try {
            const res = await apiRequest(`/registro-saldatura/${commessaId}`);
            setData(res);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { load(); }, [load]);

    // Carica WPS globali
    useEffect(() => {
        (async () => {
            try {
                const res = await apiRequest('/wps/');
                setWpsList(Array.isArray(res) ? res : res.items || []);
            } catch { setWpsList([]); }
        })();
    }, []);

    // Carica saldatori idonei quando cambia il processo selezionato nel form
    const fetchSaldatoriIdonei = useCallback(async (processo) => {
        setLoadingSaldatori(true);
        try {
            const res = await apiRequest(`/registro-saldatura/${commessaId}/saldatori-idonei?processo=${processo}`);
            setSaldatoriIdonei(res.saldatori || []);
        } catch {
            setSaldatoriIdonei([]);
        } finally {
            setLoadingSaldatori(false);
        }
    }, [commessaId]);

    const openNew = () => {
        setEditingId(null);
        setForm({ ...emptyForm });
        setDialogOpen(true);
        fetchSaldatoriIdonei('135');
    };

    const openEdit = (riga) => {
        setEditingId(riga.riga_id);
        setForm({
            giunto: riga.giunto || '',
            posizione_dwg: riga.posizione_dwg || '',
            saldatore_id: riga.saldatore_id || '',
            wps_id: riga.wps_id || '',
            processo: riga.processo || '135',
            data_esecuzione: riga.data_esecuzione || '',
            esito_vt: riga.esito_vt || 'da_eseguire',
            note: riga.note || '',
        });
        setDialogOpen(true);
        fetchSaldatoriIdonei(riga.processo || '135');
    };

    const handleSave = async () => {
        if (!form.giunto.trim()) { toast.error('Inserisci ID giunto'); return; }
        if (!form.saldatore_id) { toast.error('Seleziona un saldatore'); return; }
        setSaving(true);
        try {
            if (editingId) {
                await apiRequest(`/registro-saldatura/${commessaId}/${editingId}`, {
                    method: 'PUT',
                    body: form,
                });
                toast.success('Riga aggiornata');
            } else {
                const res = await apiRequest(`/registro-saldatura/${commessaId}`, {
                    method: 'POST',
                    body: form,
                });
                if (!res.processo_validato) {
                    toast.warning('Riga aggiunta — Attenzione: patentino non verificato per questo processo');
                } else {
                    toast.success('Riga aggiunta al registro');
                }
            }
            setDialogOpen(false);
            load();
        } catch (e) {
            toast.error(e.message || 'Errore salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (rigaId) => {
        setDeleting(rigaId);
        try {
            await apiRequest(`/registro-saldatura/${commessaId}/${rigaId}`, { method: 'DELETE' });
            toast.success('Riga eliminata');
            load();
        } catch (e) {
            toast.error(e.message || 'Errore eliminazione');
        } finally {
            setDeleting(null);
        }
    };

    const handleProcessoChange = (val) => {
        setForm(prev => ({ ...prev, processo: val, saldatore_id: '' }));
        fetchSaldatoriIdonei(val);
    };

    if (loading) {
        return (
            <Card className="border-gray-200">
                <CardContent className="py-8 flex items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-orange-500" />
                </CardContent>
            </Card>
        );
    }

    const righe = data?.righe || [];
    const stats = data?.stats || {};

    return (
        <Card className="border-gray-200" data-testid="registro-saldatura-section">
            <CardHeader className="bg-gradient-to-r from-orange-600 to-amber-600 py-2.5 px-4 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                        <Flame className="h-3.5 w-3.5" /> Registro Saldatura
                        {righe.length > 0 && (
                            <Badge className="bg-white/20 text-white text-[10px] ml-1">{righe.length} righe</Badge>
                        )}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Button size="sm" variant="ghost" onClick={load} className="text-white hover:bg-white/10 h-7 w-7 p-0" data-testid="registro-refresh">
                            <RefreshCw className="h-3 w-3" />
                        </Button>
                        <Button size="sm" onClick={openNew} className="bg-white text-orange-700 hover:bg-orange-50 text-[11px] h-7 px-2.5" data-testid="registro-add-btn">
                            <Plus className="h-3 w-3 mr-1" /> Nuova Riga
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-3">
                {/* Stats */}
                {righe.length > 0 && (
                    <div className="grid grid-cols-4 gap-2" data-testid="registro-stats">
                        <StatBox label="Totale" value={stats.totale} color="text-slate-700" bg="bg-slate-50" />
                        <StatBox label="Conformi" value={stats.conformi} color="text-emerald-700" bg="bg-emerald-50" />
                        <StatBox label="Non conf." value={stats.non_conformi} color="text-red-700" bg="bg-red-50" />
                        <StatBox label="Da eseguire" value={stats.da_eseguire} color="text-amber-700" bg="bg-amber-50" />
                    </div>
                )}

                {/* Tabella */}
                {righe.length === 0 ? (
                    <div className="text-center py-6 text-sm text-slate-400" data-testid="registro-empty">
                        <Flame className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                        Nessuna saldatura registrata per questa commessa.
                        <br />
                        <span className="text-xs">Clicca "Nuova Riga" per iniziare.</span>
                    </div>
                ) : (
                    <div className="overflow-x-auto" data-testid="registro-table">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b text-left text-slate-500">
                                    <th className="pb-2 pr-2 font-medium">Giunto</th>
                                    <th className="pb-2 pr-2 font-medium">Saldatore</th>
                                    <th className="pb-2 pr-2 font-medium">Processo</th>
                                    <th className="pb-2 pr-2 font-medium">WPS</th>
                                    <th className="pb-2 pr-2 font-medium">Data</th>
                                    <th className="pb-2 pr-2 font-medium">Esito VT</th>
                                    <th className="pb-2 font-medium w-16"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {righe.map(r => {
                                    const esito = ESITI.find(e => e.value === r.esito_vt) || ESITI[0];
                                    const EIcon = esito.icon;
                                    return (
                                        <tr key={r.riga_id} className="hover:bg-slate-50 transition-colors" data-testid={`registro-riga-${r.riga_id}`}>
                                            <td className="py-2 pr-2">
                                                <span className="font-mono font-semibold text-slate-800">{r.giunto}</span>
                                                {r.posizione_dwg && <span className="block text-[10px] text-slate-400">{r.posizione_dwg}</span>}
                                            </td>
                                            <td className="py-2 pr-2">
                                                <span className="text-slate-700">{r.saldatore_nome || '?'}</span>
                                                {r.saldatore_punzone && <span className="ml-1 text-[10px] text-slate-400">({r.saldatore_punzone})</span>}
                                            </td>
                                            <td className="py-2 pr-2">
                                                <Badge className="bg-slate-100 text-slate-600 text-[10px]">
                                                    {r.processo || r.wps_processo}
                                                </Badge>
                                            </td>
                                            <td className="py-2 pr-2 text-slate-500">{r.wps_id || '—'}</td>
                                            <td className="py-2 pr-2 text-slate-500">{r.data_esecuzione || '—'}</td>
                                            <td className="py-2 pr-2">
                                                <Badge className={`${esito.color} text-[10px] gap-1`}>
                                                    <EIcon className="h-2.5 w-2.5" /> {esito.label}
                                                </Badge>
                                            </td>
                                            <td className="py-2 text-right">
                                                <div className="flex items-center gap-1 justify-end">
                                                    <button onClick={() => openEdit(r)} className="p-1 hover:bg-blue-50 rounded text-slate-400 hover:text-blue-600 transition-colors" data-testid={`registro-edit-${r.riga_id}`}>
                                                        <Edit2 className="h-3 w-3" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(r.riga_id)}
                                                        disabled={deleting === r.riga_id}
                                                        className="p-1 hover:bg-red-50 rounded text-slate-400 hover:text-red-600 transition-colors"
                                                        data-testid={`registro-delete-${r.riga_id}`}
                                                    >
                                                        {deleting === r.riga_id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>

            {/* Dialog Nuova/Modifica Riga */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="sm:max-w-md" data-testid="registro-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-[#1E293B]">
                            <Flame className="h-5 w-5 text-orange-500" />
                            {editingId ? 'Modifica Riga Saldatura' : 'Nuova Riga Saldatura'}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        {/* Giunto + Posizione */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Giunto *</Label>
                                <Input
                                    value={form.giunto}
                                    onChange={e => setForm(prev => ({ ...prev, giunto: e.target.value }))}
                                    placeholder="G1, G2..."
                                    className="mt-1 text-sm"
                                    data-testid="registro-input-giunto"
                                />
                            </div>
                            <div>
                                <Label className="text-xs">Posizione Disegno</Label>
                                <Input
                                    value={form.posizione_dwg}
                                    onChange={e => setForm(prev => ({ ...prev, posizione_dwg: e.target.value }))}
                                    placeholder="Pos.4 STR02"
                                    className="mt-1 text-sm"
                                    data-testid="registro-input-posizione"
                                />
                            </div>
                        </div>

                        {/* Processo */}
                        <div>
                            <Label className="text-xs">Processo di Saldatura *</Label>
                            <Select value={form.processo} onValueChange={handleProcessoChange}>
                                <SelectTrigger className="mt-1 text-sm" data-testid="registro-select-processo">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {PROCESSI.map(p => (
                                        <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Saldatore (filtrato per processo) */}
                        <div>
                            <Label className="text-xs flex items-center gap-1.5">
                                <User className="h-3 w-3" /> Saldatore Idoneo *
                                {loadingSaldatori && <Loader2 className="h-3 w-3 animate-spin text-orange-500" />}
                            </Label>
                            {saldatoriIdonei.length === 0 && !loadingSaldatori ? (
                                <div className="mt-1 p-2 bg-amber-50 rounded text-xs text-amber-700 flex items-center gap-1.5" data-testid="registro-no-saldatori">
                                    <AlertTriangle className="h-3.5 w-3.5" />
                                    Nessun saldatore con patentino valido per processo {form.processo}
                                </div>
                            ) : (
                                <Select value={form.saldatore_id} onValueChange={v => setForm(prev => ({ ...prev, saldatore_id: v }))}>
                                    <SelectTrigger className="mt-1 text-sm" data-testid="registro-select-saldatore">
                                        <SelectValue placeholder="Seleziona saldatore..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {saldatoriIdonei.map(s => (
                                            <SelectItem key={s.welder_id} value={s.welder_id}>
                                                {s.name} {s.punzone ? `(${s.punzone})` : ''} — {s.patentino} {s.scadenza ? `[scad. ${s.scadenza}]` : ''}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                        </div>

                        {/* WPS */}
                        <div>
                            <Label className="text-xs flex items-center gap-1.5">
                                <FileText className="h-3 w-3" /> WPS (opzionale)
                            </Label>
                            {wpsList.length === 0 ? (
                                <p className="mt-1 text-[10px] text-slate-400">Nessuna WPS disponibile — aggiungine una dalla sezione WPS</p>
                            ) : (
                                <Select value={form.wps_id || 'none'} onValueChange={v => setForm(prev => ({ ...prev, wps_id: v === 'none' ? '' : v }))}>
                                    <SelectTrigger className="mt-1 text-sm" data-testid="registro-select-wps">
                                        <SelectValue placeholder="Seleziona WPS..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="none">— Nessuna WPS —</SelectItem>
                                        {wpsList.map(w => (
                                            <SelectItem key={w.wps_id} value={w.wps_id}>
                                                {w.number || w.wps_id} — Proc. {w.process}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                        </div>

                        {/* Data + Esito VT */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Data Esecuzione</Label>
                                <Input
                                    type="date"
                                    value={form.data_esecuzione}
                                    onChange={e => setForm(prev => ({ ...prev, data_esecuzione: e.target.value }))}
                                    className="mt-1 text-sm"
                                    data-testid="registro-input-data"
                                />
                            </div>
                            <div>
                                <Label className="text-xs">Esito VT</Label>
                                <Select value={form.esito_vt} onValueChange={v => setForm(prev => ({ ...prev, esito_vt: v }))}>
                                    <SelectTrigger className="mt-1 text-sm" data-testid="registro-select-esito">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ESITI.map(e => (
                                            <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Note */}
                        <div>
                            <Label className="text-xs">Note</Label>
                            <Textarea
                                value={form.note}
                                onChange={e => setForm(prev => ({ ...prev, note: e.target.value }))}
                                placeholder="Note aggiuntive..."
                                className="mt-1 text-sm h-14"
                                data-testid="registro-input-note"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button size="sm" disabled={saving} onClick={handleSave}
                            className="bg-orange-600 text-white hover:bg-orange-700"
                            data-testid="registro-save-btn"
                        >
                            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <CheckCircle className="h-3.5 w-3.5 mr-1.5" />}
                            {editingId ? 'Aggiorna' : 'Salva'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}

function StatBox({ label, value, color, bg }) {
    return (
        <div className={`text-center p-1.5 rounded-lg ${bg}`}>
            <p className="text-[9px] text-slate-500">{label}</p>
            <p className={`text-sm font-bold ${color}`}>{value ?? 0}</p>
        </div>
    );
}
