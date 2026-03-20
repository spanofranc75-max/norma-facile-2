/**
 * AttrezzaturePage — Scadenzario Attrezzature (saldatrici + chiavi dinamometriche).
 * Se taratura scaduta → alert admin automatico.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
    Wrench, Plus, Trash2, AlertTriangle, CheckCircle2, Clock,
    Loader2, Edit3, X,
} from 'lucide-react';

const TIPO_LABELS = {
    saldatrice: { label: 'Saldatrice', icon: '🔥', color: 'from-orange-600 to-orange-400' },
    chiave_dinamometrica: { label: 'Chiave Dinamometrica', icon: '🔧', color: 'from-blue-600 to-blue-400' },
    altro: { label: 'Altro', icon: '🛠️', color: 'from-slate-600 to-slate-400' },
};

export default function AttrezzaturePage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [tarCheck, setTarCheck] = useState(null);

    const [form, setForm] = useState({
        tipo: 'chiave_dinamometrica', modello: '', numero_serie: '', marca: '',
        data_taratura: '', prossima_taratura: '', note: '',
    });

    const fetchData = useCallback(async () => {
        try {
            const [res, check] = await Promise.all([
                apiRequest('/attrezzature'),
                apiRequest('/attrezzature/check-taratura').catch(() => null),
            ]);
            setItems(res.attrezzature || []);
            setTarCheck(check);
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleCreate = async () => {
        if (!form.modello || !form.data_taratura || !form.prossima_taratura) {
            toast.error('Modello e date taratura obbligatori');
            return;
        }
        setCreating(true);
        try {
            await apiRequest('/attrezzature', { method: 'POST', body: form });
            toast.success('Attrezzatura registrata');
            setShowCreate(false);
            resetForm();
            fetchData();
        } catch (e) { toast.error(e.message); }
        finally { setCreating(false); }
    };

    const handleUpdate = async (attrId) => {
        try {
            await apiRequest(`/attrezzature/${attrId}`, { method: 'PATCH', body: form });
            toast.success('Attrezzatura aggiornata');
            setEditingId(null);
            resetForm();
            fetchData();
        } catch (e) { toast.error(e.message); }
    };

    const handleDelete = async (attrId) => {
        if (!window.confirm('Eliminare questa attrezzatura?')) return;
        try {
            await apiRequest(`/attrezzature/${attrId}`, { method: 'DELETE' });
            toast.success('Eliminata');
            fetchData();
        } catch (e) { toast.error(e.message); }
    };

    const startEdit = (item) => {
        setForm({
            tipo: item.tipo, modello: item.modello, numero_serie: item.numero_serie || '',
            marca: item.marca || '', data_taratura: item.data_taratura,
            prossima_taratura: item.prossima_taratura, note: item.note || '',
        });
        setEditingId(item.attr_id);
    };

    const resetForm = () => {
        setForm({ tipo: 'chiave_dinamometrica', modello: '', numero_serie: '', marca: '', data_taratura: '', prossima_taratura: '', note: '' });
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
            </DashboardLayout>
        );
    }

    const scadute = items.filter(i => i.scaduta);
    const inScadenza = items.filter(i => i.in_scadenza);
    const valide = items.filter(i => !i.scaduta && !i.in_scadenza);

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="attrezzature-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-slate-900">Scadenzario Attrezzature</h1>
                        <p className="text-sm text-slate-500 mt-1">Tarature saldatrici e chiavi dinamometriche</p>
                    </div>
                    <Button onClick={() => { setShowCreate(!showCreate); setEditingId(null); resetForm(); }} data-testid="btn-add-attr">
                        <Plus className="h-4 w-4 mr-1" /> Nuova Attrezzatura
                    </Button>
                </div>

                {/* Alert banner for expired calibrations */}
                {scadute.length > 0 && (
                    <Card className="border-red-200 bg-red-50" data-testid="taratura-alert">
                        <CardContent className="py-3 px-4">
                            <div className="flex items-center gap-2 text-red-700">
                                <AlertTriangle className="h-5 w-5" />
                                <span className="font-bold">{scadute.length} attrezzatura/e con taratura SCADUTA</span>
                            </div>
                            <div className="mt-2 space-y-1">
                                {scadute.map(s => (
                                    <p key={s.attr_id} className="text-xs text-red-600">
                                        {TIPO_LABELS[s.tipo]?.icon} {s.modello} (S/N: {s.numero_serie || 'N/D'}) — scaduta da {Math.abs(s.giorni_rimasti)} giorni
                                    </p>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Create/Edit form */}
                {(showCreate || editingId) && (
                    <Card className="border-blue-200" data-testid="attr-form">
                        <CardHeader className="py-3">
                            <CardTitle className="text-sm">{editingId ? 'Modifica Attrezzatura' : 'Nuova Attrezzatura'}</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                                <select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))}
                                    className="border rounded-md px-3 py-2 text-sm" data-testid="attr-tipo">
                                    <option value="chiave_dinamometrica">Chiave Dinamometrica</option>
                                    <option value="saldatrice">Saldatrice</option>
                                    <option value="altro">Altro</option>
                                </select>
                                <Input placeholder="Modello" value={form.modello}
                                    onChange={e => setForm(f => ({ ...f, modello: e.target.value }))} data-testid="attr-modello" />
                                <Input placeholder="N. Serie" value={form.numero_serie}
                                    onChange={e => setForm(f => ({ ...f, numero_serie: e.target.value }))} data-testid="attr-serie" />
                                <Input placeholder="Marca" value={form.marca}
                                    onChange={e => setForm(f => ({ ...f, marca: e.target.value }))} />
                                <div>
                                    <label className="text-xs text-slate-500 block mb-1">Ultima taratura</label>
                                    <Input type="date" value={form.data_taratura}
                                        onChange={e => setForm(f => ({ ...f, data_taratura: e.target.value }))} data-testid="attr-data-tar" />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500 block mb-1">Prossima taratura</label>
                                    <Input type="date" value={form.prossima_taratura}
                                        onChange={e => setForm(f => ({ ...f, prossima_taratura: e.target.value }))} data-testid="attr-prossima-tar" />
                                </div>
                            </div>
                            <Input placeholder="Note" value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} />
                            <div className="flex gap-2 justify-end">
                                <Button variant="ghost" onClick={() => { setShowCreate(false); setEditingId(null); resetForm(); }}>Annulla</Button>
                                <Button onClick={() => editingId ? handleUpdate(editingId) : handleCreate()}
                                    disabled={creating} data-testid="btn-confirm-attr">
                                    {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : editingId ? 'Salva Modifiche' : 'Registra'}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Items grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {items.map(item => {
                        const tipo = TIPO_LABELS[item.tipo] || TIPO_LABELS.altro;
                        return (
                            <Card key={item.attr_id} className={`border ${item.scaduta ? 'border-red-300 bg-red-50/30' : item.in_scadenza ? 'border-amber-300 bg-amber-50/30' : 'border-gray-200'}`}
                                data-testid={`attr-${item.attr_id}`}>
                                <CardContent className="pt-4 pb-3">
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="text-2xl">{tipo.icon}</span>
                                            <div>
                                                <p className="font-semibold text-sm text-slate-800">{item.modello}</p>
                                                <p className="text-xs text-slate-500">{tipo.label}</p>
                                            </div>
                                        </div>
                                        <div className="flex gap-1">
                                            <button onClick={() => startEdit(item)} className="p-1 hover:bg-slate-100 rounded" data-testid={`btn-edit-${item.attr_id}`}>
                                                <Edit3 className="h-3 w-3 text-slate-400" />
                                            </button>
                                            <button onClick={() => handleDelete(item.attr_id)} className="p-1 hover:bg-red-50 rounded" data-testid={`btn-del-${item.attr_id}`}>
                                                <Trash2 className="h-3 w-3 text-red-400" />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="space-y-1 text-xs mt-3">
                                        {item.numero_serie && <p className="text-slate-500">S/N: <span className="text-slate-700 font-medium">{item.numero_serie}</span></p>}
                                        {item.marca && <p className="text-slate-500">Marca: <span className="text-slate-700">{item.marca}</span></p>}
                                        <p className="text-slate-500">Taratura: <span className="text-slate-700">{item.data_taratura}</span></p>
                                        <p className="text-slate-500">Prossima: <span className="font-bold text-slate-800">{item.prossima_taratura}</span></p>
                                    </div>

                                    <div className="mt-3">
                                        {item.scaduta ? (
                                            <Badge className="bg-red-100 text-red-700 text-[10px]" data-testid={`badge-scaduta-${item.attr_id}`}>
                                                <AlertTriangle className="h-3 w-3 mr-1" /> Scaduta da {Math.abs(item.giorni_rimasti)}gg
                                            </Badge>
                                        ) : item.in_scadenza ? (
                                            <Badge className="bg-amber-100 text-amber-700 text-[10px]">
                                                <Clock className="h-3 w-3 mr-1" /> Scade tra {item.giorni_rimasti}gg
                                            </Badge>
                                        ) : (
                                            <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">
                                                <CheckCircle2 className="h-3 w-3 mr-1" /> Valida ({item.giorni_rimasti}gg)
                                            </Badge>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>

                {items.length === 0 && !showCreate && (
                    <div className="text-center py-12">
                        <Wrench className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                        <p className="text-slate-500">Nessuna attrezzatura registrata.</p>
                        <p className="text-sm text-slate-400 mt-1">Aggiungi saldatrici e chiavi dinamometriche per monitorare le tarature.</p>
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
