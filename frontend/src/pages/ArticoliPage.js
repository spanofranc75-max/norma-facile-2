/**
 * Catalogo Articoli - Product/Service Catalog Page
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import { Combobox } from '../components/ui/combobox';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
    Plus, Search, Pencil, Trash2, Package, History, Download, Upload,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const CATEGORIE = [
    { value: 'materiale', label: 'Materiale' },
    { value: 'lavorazione', label: 'Lavorazione' },
    { value: 'servizio', label: 'Servizio' },
    { value: 'accessorio', label: 'Accessorio' },
    { value: 'trasporto', label: 'Trasporto' },
    { value: 'altro', label: 'Altro' },
];

const UNITA = [
    { value: 'pz', label: 'pz' },
    { value: 'ml', label: 'ml' },
    { value: 'mq', label: 'mq' },
    { value: 'kg', label: 'kg' },
    { value: 'h', label: 'h' },
    { value: 'corpo', label: 'corpo' },
    { value: 'lt', label: 'lt' },
];

const IVA_RATES = [
    { value: '22', label: '22%' },
    { value: '10', label: '10%' },
    { value: '4', label: '4%' },
    { value: '0', label: '0%' },
    { value: 'N4', label: 'Esente (N4)' },
    { value: 'N3', label: 'Non imp. (N3)' },
];

const CAT_COLORS = {
    materiale: 'bg-blue-100 text-blue-800',
    lavorazione: 'bg-amber-100 text-amber-800',
    servizio: 'bg-green-100 text-green-800',
    accessorio: 'bg-purple-100 text-purple-800',
    trasporto: 'bg-orange-100 text-orange-800',
    altro: 'bg-slate-100 text-slate-700',
};

const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const emptyForm = {
    codice: '',
    descrizione: '',
    categoria: 'materiale',
    unita_misura: 'pz',
    prezzo_unitario: 0,
    aliquota_iva: '22',
    fornitore_nome: '',
    note: '',
};

export default function ArticoliPage() {
    const [articoli, setArticoli] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');
    const [filterCat, setFilterCat] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [historyOpen, setHistoryOpen] = useState(false);
    const [selectedArticolo, setSelectedArticolo] = useState(null);
    const [form, setForm] = useState({ ...emptyForm });
    const [saving, setSaving] = useState(false);

    const fetchArticoli = useCallback(async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (searchQ) params.append('q', searchQ);
            if (filterCat) params.append('categoria', filterCat);
            const data = await apiRequest(`/articoli/?${params}`);
            setArticoli(data.articoli || []);
            setTotal(data.total || 0);
        } catch {
            toast.error('Errore caricamento articoli');
        } finally {
            setLoading(false);
        }
    }, [searchQ, filterCat]);

    useEffect(() => {
        const timer = setTimeout(fetchArticoli, 300);
        return () => clearTimeout(timer);
    }, [fetchArticoli]);

    const openNew = () => {
        setSelectedArticolo(null);
        setForm({ ...emptyForm });
        setDialogOpen(true);
    };

    const openEdit = (art) => {
        setSelectedArticolo(art);
        setForm({
            codice: art.codice,
            descrizione: art.descrizione,
            categoria: art.categoria,
            unita_misura: art.unita_misura,
            prezzo_unitario: art.prezzo_unitario,
            aliquota_iva: art.aliquota_iva,
            fornitore_nome: art.fornitore_nome || '',
            note: art.note || '',
        });
        setDialogOpen(true);
    };

    const openHistory = (art) => {
        setSelectedArticolo(art);
        setHistoryOpen(true);
    };

    const handleSave = async () => {
        if (!form.codice || !form.descrizione) {
            toast.error('Codice e descrizione sono obbligatori');
            return;
        }
        setSaving(true);
        try {
            if (selectedArticolo) {
                await apiRequest(`/articoli/${selectedArticolo.articolo_id}`, {
                    method: 'PUT',
                    body: JSON.stringify(form),
                });
                toast.success('Articolo aggiornato');
            } else {
                await apiRequest('/articoli/', {
                    method: 'POST',
                    body: JSON.stringify(form),
                });
                toast.success('Articolo creato');
            }
            setDialogOpen(false);
            fetchArticoli();
        } catch (err) {
            toast.error(err.message || 'Errore salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (art) => {
        if (!window.confirm(`Eliminare l'articolo "${art.codice}"?`)) return;
        try {
            await apiRequest(`/articoli/${art.articolo_id}`, { method: 'DELETE' });
            toast.success('Articolo eliminato');
            fetchArticoli();
        } catch {
            toast.error('Errore eliminazione');
        }
    };

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">
                            Catalogo Articoli
                        </h1>
                        <p className="text-slate-600">{total} articol{total !== 1 ? 'i' : 'o'} in archivio</p>
                    </div>
                    <Button
                        data-testid="btn-new-articolo"
                        onClick={openNew}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Nuovo Articolo
                    </Button>
                </div>

                {/* Filters */}
                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-4">
                            <div className="relative flex-1 max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input
                                    data-testid="search-articoli"
                                    placeholder="Cerca per codice, descrizione, fornitore..."
                                    value={searchQ}
                                    onChange={(e) => setSearchQ(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                            <Select
                                value={filterCat || '__all__'}
                                onValueChange={(v) => setFilterCat(v === '__all__' ? '' : v)}
                            >
                                <SelectTrigger data-testid="filter-categoria" className="w-[180px]">
                                    <SelectValue placeholder="Categoria" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">Tutte le categorie</SelectItem>
                                    {CATEGORIE.map(c => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Codice</TableHead>
                                    <TableHead className="text-white font-semibold">Descrizione</TableHead>
                                    <TableHead className="text-white font-semibold">Categoria</TableHead>
                                    <TableHead className="text-white font-semibold">U.M.</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Prezzo</TableHead>
                                    <TableHead className="text-white font-semibold">IVA</TableHead>
                                    <TableHead className="text-white font-semibold">Fornitore</TableHead>
                                    <TableHead className="w-[120px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-8">
                                            <div className="w-6 h-6 loading-spinner mx-auto" />
                                        </TableCell>
                                    </TableRow>
                                ) : articoli.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="p-0">
                                            <EmptyState
                                                type="articoli"
                                                title="Nessun articolo in catalogo"
                                                description="Aggiungi articoli per velocizzare la creazione delle fatture."
                                                actionLabel="Aggiungi il primo Articolo"
                                                onAction={openNew}
                                            />
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    articoli.map((art) => (
                                        <TableRow
                                            key={art.articolo_id}
                                            data-testid={`articolo-row-${art.articolo_id}`}
                                            className="hover:bg-slate-50"
                                        >
                                            <TableCell className="font-mono font-medium text-[#0055FF]">
                                                {art.codice}
                                            </TableCell>
                                            <TableCell className="max-w-[280px] truncate">
                                                {art.descrizione}
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={CAT_COLORS[art.categoria] || CAT_COLORS.altro}>
                                                    {CATEGORIE.find(c => c.value === art.categoria)?.label || art.categoria}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-slate-600">{art.unita_misura}</TableCell>
                                            <TableCell className="text-right font-mono font-semibold">
                                                {formatCurrency(art.prezzo_unitario)}
                                            </TableCell>
                                            <TableCell>{art.aliquota_iva}%</TableCell>
                                            <TableCell className="text-slate-600 text-sm">
                                                {art.fornitore_nome || '-'}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex gap-1">
                                                    <Button
                                                        variant="ghost" size="sm"
                                                        onClick={() => openHistory(art)}
                                                        title="Storico prezzi"
                                                        data-testid={`btn-history-${art.articolo_id}`}
                                                    >
                                                        <History className="h-4 w-4 text-slate-500" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost" size="sm"
                                                        onClick={() => openEdit(art)}
                                                        data-testid={`btn-edit-${art.articolo_id}`}
                                                    >
                                                        <Pencil className="h-4 w-4 text-slate-500" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost" size="sm"
                                                        onClick={() => handleDelete(art)}
                                                        data-testid={`btn-delete-${art.articolo_id}`}
                                                    >
                                                        <Trash2 className="h-4 w-4 text-red-500" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            {/* Create/Edit Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>
                            {selectedArticolo ? 'Modifica Articolo' : 'Nuovo Articolo'}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label>Codice *</Label>
                                <Input
                                    data-testid="input-codice"
                                    value={form.codice}
                                    onChange={(e) => setForm(f => ({ ...f, codice: e.target.value.toUpperCase() }))}
                                    placeholder="ART-001"
                                />
                            </div>
                            <div>
                                <Label>Categoria</Label>
                                <Select
                                    value={form.categoria}
                                    onValueChange={(v) => setForm(f => ({ ...f, categoria: v }))}
                                >
                                    <SelectTrigger data-testid="select-categoria">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {CATEGORIE.map(c => (
                                            <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div>
                            <Label>Descrizione *</Label>
                            <Textarea
                                data-testid="input-descrizione"
                                value={form.descrizione}
                                onChange={(e) => setForm(f => ({ ...f, descrizione: e.target.value }))}
                                placeholder="Descrizione articolo/servizio..."
                                rows={2}
                            />
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                            <div>
                                <Label>U.M.</Label>
                                <Select
                                    value={form.unita_misura}
                                    onValueChange={(v) => setForm(f => ({ ...f, unita_misura: v }))}
                                >
                                    <SelectTrigger data-testid="select-unita">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {UNITA.map(u => (
                                            <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Prezzo unitario</Label>
                                <Input
                                    data-testid="input-prezzo"
                                    type="number" step="0.01" min="0"
                                    value={form.prezzo_unitario}
                                    onChange={(e) => setForm(f => ({ ...f, prezzo_unitario: parseFloat(e.target.value) || 0 }))}
                                />
                            </div>
                            <div>
                                <Label>IVA</Label>
                                <Select
                                    value={form.aliquota_iva}
                                    onValueChange={(v) => setForm(f => ({ ...f, aliquota_iva: v }))}
                                >
                                    <SelectTrigger data-testid="select-iva">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {IVA_RATES.map(r => (
                                            <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div>
                            <Label>Fornitore</Label>
                            <Input
                                data-testid="input-fornitore"
                                value={form.fornitore_nome}
                                onChange={(e) => setForm(f => ({ ...f, fornitore_nome: e.target.value }))}
                                placeholder="Nome fornitore (opzionale)"
                            />
                        </div>
                        <div>
                            <Label>Note</Label>
                            <Input
                                data-testid="input-note"
                                value={form.note}
                                onChange={(e) => setForm(f => ({ ...f, note: e.target.value }))}
                                placeholder="Note interne..."
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialogOpen(false)}>
                            Annulla
                        </Button>
                        <Button
                            data-testid="btn-save-articolo"
                            onClick={handleSave}
                            disabled={saving}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            {saving ? 'Salvataggio...' : (selectedArticolo ? 'Aggiorna' : 'Crea')}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Price History Dialog */}
            <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <History className="h-5 w-5" />
                            Storico Prezzi — {selectedArticolo?.codice}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                        {(selectedArticolo?.storico_prezzi || []).length === 0 ? (
                            <p className="text-sm text-slate-500 text-center py-4">Nessuno storico disponibile</p>
                        ) : (
                            [...(selectedArticolo?.storico_prezzi || [])].reverse().map((entry, i) => (
                                <div key={i} className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-md">
                                    <div>
                                        <p className="font-mono font-semibold text-[#0055FF]">
                                            {formatCurrency(entry.prezzo)}
                                        </p>
                                        <p className="text-xs text-slate-500">{entry.fonte || 'manuale'}</p>
                                    </div>
                                    <p className="text-sm text-slate-600">
                                        {entry.data ? new Date(entry.data).toLocaleDateString('it-IT') : '-'}
                                    </p>
                                </div>
                            ))
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
