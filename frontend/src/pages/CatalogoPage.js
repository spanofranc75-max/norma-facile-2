/**
 * Catalogo Profili Personalizzato - Custom Warehouse
 * Searchable table of standard + custom profiles with add/edit/bulk price update.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import {
    Plus, Search, TrendingUp, Edit2, Trash2, Package, Warehouse,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const CATEGORIES = [
    { value: 'ferro', label: 'Ferro' },
    { value: 'alluminio', label: 'Alluminio' },
    { value: 'accessori', label: 'Accessori' },
    { value: 'verniciatura', label: 'Verniciatura' },
    { value: 'altro', label: 'Altro' },
];

const fmtNum = (v, d = 2) => v != null ? Number(v).toFixed(d) : '-';
const fmtEur = (v) => v != null ? `${Number(v).toFixed(2)} EUR/m` : '-';

const emptyProfile = {
    code: '', description: '', category: 'ferro',
    weight_m: '', surface_m: '', price_m: '', supplier: '', notes: '',
};

export default function CatalogoPage() {
    const [profiles, setProfiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [filterCat, setFilterCat] = useState('all');
    const [filterSource, setFilterSource] = useState('all');

    // Add/Edit dialog
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [form, setForm] = useState({ ...emptyProfile });
    const [saving, setSaving] = useState(false);

    // Bulk price dialog
    const [bulkOpen, setBulkOpen] = useState(false);
    const [bulkPct, setBulkPct] = useState('');
    const [bulkCat, setBulkCat] = useState('all');

    const fetchProfiles = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/catalogo/merged/all');
            setProfiles(data.profiles || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchProfiles(); }, [fetchProfiles]);

    const filtered = profiles.filter(p => {
        if (filterCat !== 'all' && p.category !== filterCat) return false;
        if (filterSource !== 'all' && p.source !== filterSource) return false;
        if (search) {
            const s = search.toLowerCase();
            return (p.code + ' ' + p.description + ' ' + (p.supplier || '')).toLowerCase().includes(s);
        }
        return true;
    });

    const openAdd = () => {
        setEditingId(null);
        setForm({ ...emptyProfile });
        setDialogOpen(true);
    };

    const openEdit = (p) => {
        setEditingId(p.profile_id);
        setForm({
            code: p.code, description: p.description, category: p.category,
            weight_m: String(p.weight_m || ''), surface_m: String(p.surface_m || ''),
            price_m: p.price_m != null ? String(p.price_m) : '',
            supplier: p.supplier || '', notes: p.notes || '',
        });
        setDialogOpen(true);
    };

    const handleSave = async () => {
        if (!form.code.trim() || !form.description.trim()) {
            toast.error('Codice e Descrizione obbligatori');
            return;
        }
        setSaving(true);
        try {
            const payload = {
                code: form.code.trim(),
                description: form.description.trim(),
                category: form.category,
                weight_m: parseFloat(form.weight_m) || 0,
                surface_m: parseFloat(form.surface_m) || 0,
                price_m: form.price_m ? parseFloat(form.price_m) : null,
                supplier: form.supplier.trim() || null,
                notes: form.notes.trim() || null,
            };
            if (editingId) {
                await apiRequest(`/catalogo/${editingId}`, { method: 'PUT', body: payload });
                toast.success('Profilo aggiornato');
            } else {
                await apiRequest('/catalogo/', { method: 'POST', body: payload });
                toast.success('Profilo creato');
            }
            setDialogOpen(false);
            fetchProfiles();
        } catch (e) {
            toast.error(e.message || 'Errore nel salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (p) => {
        if (!window.confirm(`Eliminare il profilo "${p.code}"?`)) return;
        try {
            await apiRequest(`/catalogo/${p.profile_id}`, { method: 'DELETE' });
            toast.success('Profilo eliminato');
            fetchProfiles();
        } catch (e) {
            toast.error(e.message || 'Errore');
        }
    };

    const handleBulkUpdate = async () => {
        const pct = parseFloat(bulkPct);
        if (isNaN(pct) || pct === 0) {
            toast.error('Inserire una percentuale valida');
            return;
        }
        try {
            const payload = { percentage: pct };
            if (bulkCat !== 'all') payload.category = bulkCat;
            const res = await apiRequest('/catalogo/bulk-price-update', { method: 'POST', body: payload });
            toast.success(res.message);
            setBulkOpen(false);
            setBulkPct('');
            fetchProfiles();
        } catch (e) {
            toast.error(e.message || 'Errore');
        }
    };

    const customCount = profiles.filter(p => p.source === 'custom').length;
    const standardCount = profiles.filter(p => p.source === 'standard').length;

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="catalogo-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">Catalogo Profili</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            {standardCount} standard + {customCount} personalizzati
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            data-testid="btn-bulk-price"
                            variant="outline"
                            onClick={() => setBulkOpen(true)}
                            className="border-amber-500 text-amber-600 hover:bg-amber-50"
                        >
                            <TrendingUp className="h-4 w-4 mr-2" /> Aggiorna Prezzi
                        </Button>
                        <Button
                            data-testid="btn-add-profile"
                            onClick={openAdd}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            <Plus className="h-4 w-4 mr-2" /> Nuovo Profilo
                        </Button>
                    </div>
                </div>

                {/* Filters */}
                <Card className="border-gray-200">
                    <CardContent className="pt-4 pb-3 px-4">
                        <div className="flex gap-3 items-end">
                            <div className="flex-1">
                                <div className="relative">
                                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                    <Input
                                        data-testid="search-profiles"
                                        placeholder="Cerca per codice, descrizione o fornitore..."
                                        value={search}
                                        onChange={e => setSearch(e.target.value)}
                                        className="pl-10"
                                    />
                                </div>
                            </div>
                            <Select value={filterCat} onValueChange={setFilterCat}>
                                <SelectTrigger data-testid="filter-category" className="w-40">
                                    <SelectValue placeholder="Categoria" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutte</SelectItem>
                                    {CATEGORIES.map(c => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Select value={filterSource} onValueChange={setFilterSource}>
                                <SelectTrigger data-testid="filter-source" className="w-40">
                                    <SelectValue placeholder="Origine" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti</SelectItem>
                                    <SelectItem value="standard">Standard</SelectItem>
                                    <SelectItem value="custom">Personalizzati</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardHeader className="bg-[#1E293B] py-3 px-5 rounded-t-lg">
                        <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                            <Warehouse className="h-4 w-4" /> Profili ({filtered.length})
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" />
                            </div>
                        ) : filtered.length === 0 ? (
                            <div className="text-center py-12 text-slate-400">
                                <Package className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                                <p className="text-sm">Nessun profilo trovato</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="font-semibold text-[#1E293B]">Codice</TableHead>
                                            <TableHead className="font-semibold text-[#1E293B]">Descrizione</TableHead>
                                            <TableHead className="font-semibold text-[#1E293B]">Categoria</TableHead>
                                            <TableHead className="text-right font-semibold text-[#1E293B]">Peso (kg/m)</TableHead>
                                            <TableHead className="text-right font-semibold text-[#1E293B]">Sup. (m2/m)</TableHead>
                                            <TableHead className="text-right font-semibold text-[#1E293B]">Prezzo</TableHead>
                                            <TableHead className="font-semibold text-[#1E293B]">Fornitore</TableHead>
                                            <TableHead className="w-20"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {filtered.map(p => (
                                            <TableRow key={p.profile_id} data-testid={`profile-row-${p.profile_id}`}>
                                                <TableCell className="font-mono text-sm text-[#0055FF] font-medium">{p.code}</TableCell>
                                                <TableCell className="text-sm text-[#1E293B]">{p.description}</TableCell>
                                                <TableCell>
                                                    <Badge className={p.source === 'custom' ? 'bg-blue-100 text-[#0055FF]' : 'bg-slate-100 text-slate-600'}>
                                                        {p.category}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-sm">{fmtNum(p.weight_m, 3)}</TableCell>
                                                <TableCell className="text-right font-mono text-sm">{fmtNum(p.surface_m, 3)}</TableCell>
                                                <TableCell className="text-right font-mono text-sm">{fmtEur(p.price_m)}</TableCell>
                                                <TableCell className="text-sm text-slate-500">{p.supplier || '-'}</TableCell>
                                                <TableCell>
                                                    {p.source === 'custom' && (
                                                        <div className="flex gap-1">
                                                            <button
                                                                data-testid={`edit-${p.profile_id}`}
                                                                onClick={() => openEdit(p)}
                                                                className="p-1.5 text-slate-400 hover:text-[#0055FF] rounded"
                                                            >
                                                                <Edit2 className="h-3.5 w-3.5" />
                                                            </button>
                                                            <button
                                                                data-testid={`delete-${p.profile_id}`}
                                                                onClick={() => handleDelete(p)}
                                                                className="p-1.5 text-slate-400 hover:text-red-500 rounded"
                                                            >
                                                                <Trash2 className="h-3.5 w-3.5" />
                                                            </button>
                                                        </div>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Add/Edit Profile Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="sm:max-w-[500px]" data-testid="profile-dialog">
                    <DialogHeader>
                        <DialogTitle>{editingId ? 'Modifica Profilo' : 'Nuovo Profilo Personalizzato'}</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Codice *</Label>
                                <Input data-testid="input-code" value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} placeholder="TUB-40" />
                            </div>
                            <div>
                                <Label>Categoria</Label>
                                <Select value={form.category} onValueChange={v => setForm(f => ({ ...f, category: v }))}>
                                    <SelectTrigger data-testid="input-category"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div>
                            <Label>Descrizione *</Label>
                            <Input data-testid="input-description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Tubolare 40x40x3 Zincato" />
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label>Peso (kg/m)</Label>
                                <Input data-testid="input-weight" type="number" step="0.001" value={form.weight_m} onChange={e => setForm(f => ({ ...f, weight_m: e.target.value }))} />
                            </div>
                            <div>
                                <Label>Sup. (m2/m)</Label>
                                <Input data-testid="input-surface" type="number" step="0.001" value={form.surface_m} onChange={e => setForm(f => ({ ...f, surface_m: e.target.value }))} />
                            </div>
                            <div>
                                <Label>Prezzo (EUR/m)</Label>
                                <Input data-testid="input-price" type="number" step="0.01" value={form.price_m} onChange={e => setForm(f => ({ ...f, price_m: e.target.value }))} />
                            </div>
                        </div>
                        <div>
                            <Label>Fornitore</Label>
                            <Input data-testid="input-supplier" value={form.supplier} onChange={e => setForm(f => ({ ...f, supplier: e.target.value }))} placeholder="es. Commerciale Acciai" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button data-testid="btn-save-profile" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {saving ? 'Salvataggio...' : (editingId ? 'Aggiorna' : 'Crea Profilo')}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Bulk Price Update Dialog */}
            <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
                <DialogContent className="sm:max-w-[400px]" data-testid="bulk-price-dialog">
                    <DialogHeader>
                        <DialogTitle>Aggiornamento Prezzi in Blocco</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-2">
                        <p className="text-sm text-slate-500">
                            Aggiorna i prezzi di tutti i profili personalizzati con una variazione percentuale.
                            Utile quando il prezzo dell'acciaio cambia.
                        </p>
                        <div>
                            <Label>Variazione %</Label>
                            <Input
                                data-testid="input-bulk-pct"
                                type="number"
                                step="0.1"
                                value={bulkPct}
                                onChange={e => setBulkPct(e.target.value)}
                                placeholder="es. 5.0 per +5%, -3.0 per -3%"
                            />
                        </div>
                        <div>
                            <Label>Categoria (opzionale)</Label>
                            <Select value={bulkCat} onValueChange={setBulkCat}>
                                <SelectTrigger data-testid="input-bulk-cat"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutte le categorie</SelectItem>
                                    {CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setBulkOpen(false)}>Annulla</Button>
                        <Button data-testid="btn-apply-bulk" onClick={handleBulkUpdate} className="bg-amber-500 text-white hover:bg-amber-600">
                            <TrendingUp className="h-4 w-4 mr-2" /> Applica
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
