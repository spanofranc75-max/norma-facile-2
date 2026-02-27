/**
 * Tipi Pagamento — Gestione condizioni di pagamento personalizzabili.
 * CRUD table with installment checkboxes grid.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Plus, Pencil, Trash2, CreditCard, Wand2 } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const TIPO_OPTIONS = [
    { value: 'BON', label: 'Bonifico', color: 'bg-blue-100 text-blue-800' },
    { value: 'RIB', label: 'Ri.Ba', color: 'bg-amber-100 text-amber-800' },
    { value: 'CON', label: 'Contanti', color: 'bg-emerald-100 text-emerald-800' },
    { value: 'ELE', label: 'Elettronico', color: 'bg-violet-100 text-violet-800' },
];

const GG_FIELDS = [
    { key: 'immediato', label: 'Imm.' },
    { key: 'gg_30', label: '30' },
    { key: 'gg_60', label: '60' },
    { key: 'gg_90', label: '90' },
    { key: 'gg_120', label: '120' },
    { key: 'gg_150', label: '150' },
    { key: 'gg_180', label: '180' },
    { key: 'gg_210', label: '210' },
    { key: 'gg_240', label: '240' },
    { key: 'gg_270', label: '270' },
    { key: 'gg_300', label: '300' },
    { key: 'gg_330', label: '330' },
    { key: 'gg_360', label: '360' },
    { key: 'fine_mese', label: 'FM' },
    { key: 'iva_30gg', label: 'IVA30' },
];

const emptyForm = {
    codice: '', tipo: 'BON', descrizione: '',
    immediato: false, gg_30: false, gg_60: false, gg_90: false,
    gg_120: false, gg_150: false, gg_180: false, gg_210: false,
    gg_240: false, gg_270: false, gg_300: false, gg_330: false,
    gg_360: false, fine_mese: false, iva_30gg: false,
    note_documento: '', spese_incasso: 0, banca_necessaria: false,
};

export default function PaymentTypesPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyForm);

    const fetchItems = useCallback(async () => {
        try {
            const data = await apiRequest('/payment-types/');
            setItems(data.items || []);
        } catch (e) {
            toast.error('Errore nel caricamento');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchItems(); }, [fetchItems]);

    const handleSeedDefaults = async () => {
        try {
            const res = await apiRequest('/payment-types/seed-defaults', { method: 'POST' });
            toast.success(res.message);
            fetchItems();
        } catch (e) {
            toast.error(e.message);
        }
    };

    const openCreate = () => { setForm(emptyForm); setEditing(null); setDialogOpen(true); };
    const openEdit = (item) => {
        setForm({ ...emptyForm, ...item });
        setEditing(item.payment_type_id);
        setDialogOpen(true);
    };

    const handleSave = async () => {
        if (!form.codice || !form.descrizione) {
            toast.error('Codice e Descrizione obbligatori');
            return;
        }
        try {
            if (editing) {
                await apiRequest(`/payment-types/${editing}`, { method: 'PUT', body: form });
                toast.success('Tipo pagamento aggiornato');
            } else {
                await apiRequest('/payment-types/', { method: 'POST', body: form });
                toast.success('Tipo pagamento creato');
            }
            setDialogOpen(false);
            fetchItems();
        } catch (e) {
            toast.error(e.message);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Eliminare questo tipo pagamento?')) return;
        try {
            await apiRequest(`/payment-types/${id}`, { method: 'DELETE' });
            toast.success('Eliminato');
            fetchItems();
        } catch (e) {
            toast.error(e.message);
        }
    };

    const setField = (key, val) => setForm(f => ({ ...f, [key]: val }));
    const getTipoBadge = (tipo) => TIPO_OPTIONS.find(t => t.value === tipo) || TIPO_OPTIONS[0];

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="payment-types-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <CreditCard className="h-6 w-6 text-[#0055FF]" /> Tipi Pagamento
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Gestisci le condizioni di pagamento personalizzate</p>
                    </div>
                    <div className="flex gap-2">
                        {items.length === 0 && (
                            <Button data-testid="btn-seed" variant="outline" onClick={handleSeedDefaults} className="h-10 border-amber-400 text-amber-600 hover:bg-amber-50">
                                <Wand2 className="h-4 w-4 mr-2" /> Carica Predefiniti
                            </Button>
                        )}
                        <Button data-testid="btn-new-pt" onClick={openCreate} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white">
                            <Plus className="h-4 w-4 mr-2" /> Nuovo Tipo
                        </Button>
                    </div>
                </div>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                            </div>
                        ) : items.length === 0 ? (
                            <EmptyState
                                type="invoices"
                                title="Nessun tipo pagamento"
                                description="Crea i tuoi tipi pagamento personalizzati o carica quelli predefiniti per iniziare."
                                actionLabel="Crea il primo Tipo"
                                onAction={openCreate}
                            />
                        ) : (
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-[#1E293B]">
                                            <TableHead className="text-white font-medium">Codice</TableHead>
                                            <TableHead className="text-white font-medium">Tipo</TableHead>
                                            <TableHead className="text-white font-medium">Descrizione</TableHead>
                                            {GG_FIELDS.map(f => (
                                                <TableHead key={f.key} className="text-white font-medium text-center px-1.5 text-[11px]">{f.label}</TableHead>
                                            ))}
                                            <TableHead className="text-white font-medium text-center px-1.5 text-[11px]">FM</TableHead>
                                            <TableHead className="w-[80px]"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {items.map((item) => {
                                            const badge = getTipoBadge(item.tipo);
                                            return (
                                                <TableRow key={item.payment_type_id} data-testid={`pt-row-${item.payment_type_id}`} className="hover:bg-slate-50">
                                                    <TableCell className="font-mono font-semibold text-sm">{item.codice}</TableCell>
                                                    <TableCell><Badge className={`${badge.color} text-[10px]`}>{badge.label}</Badge></TableCell>
                                                    <TableCell className="text-sm max-w-[200px] truncate">{item.descrizione}</TableCell>
                                                    {GG_FIELDS.map(f => (
                                                        <TableCell key={f.key} className="text-center px-1">
                                                            {item[f.key] ? (
                                                                <div className="w-4 h-4 rounded-sm bg-[#0055FF] mx-auto" />
                                                            ) : (
                                                                <div className="w-4 h-4 rounded-sm border border-slate-300 mx-auto" />
                                                            )}
                                                        </TableCell>
                                                    ))}
                                                    <TableCell className="text-center px-1">
                                                        {item.fine_mese ? <div className="w-4 h-4 rounded-sm bg-[#0055FF] mx-auto" /> : <div className="w-4 h-4 rounded-sm border border-slate-300 mx-auto" />}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex gap-1">
                                                            <Button variant="ghost" size="sm" onClick={() => openEdit(item)} data-testid={`edit-pt-${item.payment_type_id}`}>
                                                                <Pencil className="h-3.5 w-3.5" />
                                                            </Button>
                                                            <Button variant="ghost" size="sm" onClick={() => handleDelete(item.payment_type_id)} className="text-red-500 hover:text-red-700" data-testid={`del-pt-${item.payment_type_id}`}>
                                                                <Trash2 className="h-3.5 w-3.5" />
                                                            </Button>
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Create/Edit Dialog */}
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogContent className="sm:max-w-[600px]" data-testid="pt-dialog">
                        <DialogHeader>
                            <DialogTitle className="text-[#1E293B] flex items-center gap-2">
                                <CreditCard className="h-5 w-5 text-[#0055FF]" />
                                {editing ? 'Modifica Tipo Pagamento' : 'Nuovo Tipo Pagamento'}
                            </DialogTitle>
                            <DialogDescription>Configura codice, tipo e scadenze per questa condizione di pagamento.</DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4">
                            {/* Row 1: Codice + Tipo */}
                            <div className="grid grid-cols-3 gap-3">
                                <div>
                                    <Label>Codice *</Label>
                                    <Input data-testid="pt-codice" value={form.codice} onChange={e => setField('codice', e.target.value.toUpperCase())} placeholder="BB30" className="font-mono" />
                                </div>
                                <div>
                                    <Label>Tipo</Label>
                                    <Select value={form.tipo} onValueChange={v => setField('tipo', v)}>
                                        <SelectTrigger data-testid="pt-tipo"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {TIPO_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label>Spese Incasso</Label>
                                    <Input type="number" step="0.01" value={form.spese_incasso} onChange={e => setField('spese_incasso', parseFloat(e.target.value) || 0)} className="font-mono" />
                                </div>
                            </div>

                            {/* Descrizione */}
                            <div>
                                <Label>Descrizione *</Label>
                                <Input data-testid="pt-descrizione" value={form.descrizione} onChange={e => setField('descrizione', e.target.value)} placeholder="Bonifico Bancario 30 gg" />
                            </div>

                            {/* Scadenze Grid */}
                            <div>
                                <Label className="text-sm font-semibold text-[#1E293B]">Scadenze da Generare</Label>
                                <div className="grid grid-cols-5 gap-2 mt-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                                    {GG_FIELDS.map(f => (
                                        <label key={f.key} className="flex items-center gap-2 cursor-pointer text-sm">
                                            <Checkbox
                                                data-testid={`pt-cb-${f.key}`}
                                                checked={form[f.key]}
                                                onCheckedChange={v => setField(f.key, v)}
                                            />
                                            <span className="text-slate-700">{f.label === 'Imm.' ? 'Immediato' : f.label === 'FM' ? 'Fine Mese' : f.label === 'IVA30' ? 'IVA 30gg' : `${f.label} gg`}</span>
                                        </label>
                                    ))}
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <Checkbox checked={form.banca_necessaria} onCheckedChange={v => setField('banca_necessaria', v)} />
                                        <span className="text-slate-700">Banca Nec.</span>
                                    </label>
                                </div>
                            </div>

                            {/* Note documento */}
                            <div>
                                <Label>Note su Documento</Label>
                                <Input value={form.note_documento} onChange={e => setField('note_documento', e.target.value)} placeholder="Note da stampare in fattura" />
                            </div>
                        </div>

                        <DialogFooter>
                            <Button variant="outline" onClick={() => setDialogOpen(false)}>Annulla</Button>
                            <Button data-testid="pt-save" onClick={handleSave} className="bg-[#0055FF] hover:bg-[#0044CC] text-white">
                                {editing ? 'Aggiorna' : 'Crea'}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </DashboardLayout>
    );
}
