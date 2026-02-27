/**
 * Distinta Editor Page - Bill of Materials Editor
 * Table editor with auto-calculating totals.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../components/ui/table';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Save,
    ArrowLeft,
    Plus,
    Trash2,
    Import,
    Package,
    Weight,
    Euro,
    Calculator,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const CATEGORIES = [
    { value: 'profilo', label: 'Profilo' },
    { value: 'accessorio', label: 'Accessorio' },
    { value: 'ferramenta', label: 'Ferramenta' },
    { value: 'vetro', label: 'Vetro' },
    { value: 'guarnizione', label: 'Guarnizione' },
    { value: 'altro', label: 'Altro' },
];

const UNITS = [
    { value: 'pz', label: 'pz' },
    { value: 'm', label: 'm' },
    { value: 'm²', label: 'm²' },
    { value: 'kg', label: 'kg' },
];

const emptyItem = {
    item_id: '',
    category: 'profilo',
    code: '',
    name: '',
    description: '',
    length_mm: 0,
    quantity: 1,
    unit: 'pz',
    weight_per_unit: 0,
    cost_per_unit: 0,
    notes: '',
};

const formatCurrency = (value) => {
    return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency: 'EUR',
    }).format(value || 0);
};

export default function DistintaEditorPage() {
    const navigate = useNavigate();
    const { distintaId } = useParams();
    const [searchParams] = useSearchParams();
    const rilievoIdFromUrl = searchParams.get('rilievo_id');
    const isEditing = !!distintaId;

    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [rilievi, setRilievi] = useState([]);
    const [importDialogOpen, setImportDialogOpen] = useState(false);
    const [selectedRilievoForImport, setSelectedRilievoForImport] = useState('');
    
    const [formData, setFormData] = useState({
        name: '',
        rilievo_id: rilievoIdFromUrl || '',
        client_id: '',
        status: 'bozza',
        notes: '',
        items: [],
    });

    const [totals, setTotals] = useState({
        total_items: 0,
        total_length_m: 0,
        total_weight_kg: 0,
        total_cost: 0,
        by_category: {},
    });

    // Fetch rilievi for import dropdown
    useEffect(() => {
        const fetchRilievi = async () => {
            try {
                const data = await apiRequest('/rilievi/?limit=100');
                setRilievi(data.rilievi);
            } catch (error) {
                console.error('Error loading rilievi:', error);
            }
        };
        fetchRilievi();
    }, []);

    // Fetch distinta if editing
    useEffect(() => {
        if (!isEditing) return;
        
        const fetchDistinta = async () => {
            try {
                const data = await apiRequest(`/distinte/${distintaId}`);
                setFormData({
                    name: data.name,
                    rilievo_id: data.rilievo_id || '',
                    client_id: data.client_id || '',
                    status: data.status,
                    notes: data.notes || '',
                    items: data.items || [],
                });
                setTotals(data.totals || {});
            } catch (error) {
                toast.error('Distinta non trovata');
                navigate('/distinte');
            } finally {
                setLoading(false);
            }
        };
        fetchDistinta();
    }, [distintaId, isEditing, navigate]);

    // Calculate totals when items change
    const calculateTotals = useCallback(() => {
        let totalLength = 0;
        let totalWeight = 0;
        let totalCost = 0;
        const byCategory = {};

        formData.items.forEach(item => {
            const quantity = parseFloat(item.quantity) || 0;
            const lengthMm = parseFloat(item.length_mm) || 0;
            const weightPerUnit = parseFloat(item.weight_per_unit) || 0;
            const costPerUnit = parseFloat(item.cost_per_unit) || 0;
            const unit = item.unit || 'pz';

            let itemLength = 0;
            let itemWeight = 0;
            let itemCost = 0;

            if (unit === 'm') {
                itemLength = quantity;
                itemWeight = weightPerUnit * quantity;
                itemCost = costPerUnit * quantity;
            } else if (unit === 'm²') {
                const widthMm = parseFloat(item.width_mm) || 0;
                const areaSqM = (lengthMm * widthMm) / 1_000_000 * quantity;
                itemWeight = weightPerUnit * areaSqM;
                itemCost = costPerUnit * areaSqM;
            } else {
                itemLength = (lengthMm * quantity) / 1000;
                itemWeight = weightPerUnit * quantity;
                itemCost = costPerUnit * quantity;
            }

            totalLength += itemLength;
            totalWeight += itemWeight;
            totalCost += itemCost;

            const category = item.category || 'altro';
            if (!byCategory[category]) {
                byCategory[category] = { count: 0, weight: 0, cost: 0 };
            }
            byCategory[category].count += 1;
            byCategory[category].weight += itemWeight;
            byCategory[category].cost += itemCost;
        });

        setTotals({
            total_items: formData.items.length,
            total_length_m: Math.round(totalLength * 1000) / 1000,
            total_weight_kg: Math.round(totalWeight * 1000) / 1000,
            total_cost: Math.round(totalCost * 100) / 100,
            by_category: byCategory,
        });
    }, [formData.items]);

    useEffect(() => {
        calculateTotals();
    }, [formData.items, calculateTotals]);

    const updateField = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const updateItem = (index, field, value) => {
        setFormData(prev => {
            const newItems = [...prev.items];
            newItems[index] = { ...newItems[index], [field]: value };
            return { ...prev, items: newItems };
        });
    };

    const addItem = () => {
        setFormData(prev => ({
            ...prev,
            items: [...prev.items, { ...emptyItem, item_id: `temp_${Date.now()}` }],
        }));
    };

    const removeItem = (index) => {
        setFormData(prev => ({
            ...prev,
            items: prev.items.filter((_, i) => i !== index),
        }));
    };

    const handleSave = async () => {
        if (!formData.name.trim()) {
            toast.error('Inserisci il nome della distinta');
            return;
        }

        try {
            setSaving(true);
            
            if (isEditing) {
                await apiRequest(`/distinte/${distintaId}`, {
                    method: 'PUT',
                    body: JSON.stringify(formData),
                });
                toast.success('Distinta aggiornata');
            } else {
                const result = await apiRequest('/distinte/', {
                    method: 'POST',
                    body: JSON.stringify(formData),
                });
                toast.success('Distinta creata');
                navigate(`/distinte/${result.distinta_id}`);
            }
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
        }
    };

    const handleImportFromRilievo = async () => {
        if (!selectedRilievoForImport) {
            toast.error('Seleziona un rilievo');
            return;
        }

        if (!isEditing) {
            toast.error('Salva prima la distinta');
            return;
        }

        try {
            const result = await apiRequest(
                `/distinte/${distintaId}/import-rilievo/${selectedRilievoForImport}`,
                { method: 'POST' }
            );
            
            setFormData({
                ...formData,
                rilievo_id: result.rilievo_id,
                client_id: result.client_id,
                items: result.items,
            });
            setTotals(result.totals);
            
            toast.success('Materiali importati dal rilievo');
            setImportDialogOpen(false);
        } catch (error) {
            toast.error(error.message);
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 loading-spinner" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-6 max-w-6xl">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate('/distinte')}
                        >
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Indietro
                        </Button>
                        <div>
                            <h1 className="font-serif text-2xl font-bold text-slate-900">
                                {isEditing ? 'Modifica Distinta' : 'Nuova Distinta'}
                            </h1>
                        </div>
                    </div>
                    <div className="flex gap-3">
                        {isEditing && (
                            <Button
                                variant="outline"
                                onClick={() => setImportDialogOpen(true)}
                            >
                                <Import className="h-4 w-4 mr-2" />
                                Importa da Rilievo
                            </Button>
                        )}
                        <Button
                            data-testid="btn-save-distinta"
                            onClick={handleSave}
                            disabled={saving}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            <Save className="h-4 w-4 mr-2" />
                            {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </div>
                </div>

                {/* Info Section */}
                <Card className="border-slate-200">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-lg font-semibold">Informazioni</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-3 gap-4">
                            <div className="col-span-2">
                                <Label htmlFor="name">Nome Distinta *</Label>
                                <Input
                                    id="name"
                                    data-testid="input-distinta-name"
                                    value={formData.name}
                                    onChange={(e) => updateField('name', e.target.value)}
                                    placeholder="Es: Serramenti appartamento Rossi"
                                />
                            </div>
                            <div>
                                <Label>Rilievo Collegato</Label>
                                <Select
                                    value={formData.rilievo_id || "none"}
                                    onValueChange={(v) => updateField('rilievo_id', v === "none" ? "" : v)}
                                >
                                    <SelectTrigger data-testid="select-rilievo">
                                        <SelectValue placeholder="Nessuno" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="none">Nessuno</SelectItem>
                                        {rilievi.map(r => (
                                            <SelectItem key={r.rilievo_id} value={r.rilievo_id}>
                                                {r.project_name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="col-span-3">
                                <Label htmlFor="notes">Note</Label>
                                <Textarea
                                    id="notes"
                                    value={formData.notes}
                                    onChange={(e) => updateField('notes', e.target.value)}
                                    placeholder="Note sulla distinta..."
                                    rows={2}
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Materials Table */}
                <Card className="border-slate-200">
                    <CardHeader className="flex flex-row items-center justify-between pb-4">
                        <CardTitle className="text-lg font-semibold">Materiali</CardTitle>
                        <Button
                            data-testid="btn-add-item"
                            onClick={addItem}
                            variant="outline"
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            Aggiungi Riga
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-900 hover:bg-slate-900">
                                    <TableHead className="text-white font-semibold w-[100px]">Cat.</TableHead>
                                    <TableHead className="text-white font-semibold w-[80px]">Codice</TableHead>
                                    <TableHead className="text-white font-semibold">Nome</TableHead>
                                    <TableHead className="text-white font-semibold w-[80px] text-right">Lung. mm</TableHead>
                                    <TableHead className="text-white font-semibold w-[60px] text-right">Q.tà</TableHead>
                                    <TableHead className="text-white font-semibold w-[60px]">Unità</TableHead>
                                    <TableHead className="text-white font-semibold w-[80px] text-right">Peso/u</TableHead>
                                    <TableHead className="text-white font-semibold w-[80px] text-right">Costo/u</TableHead>
                                    <TableHead className="text-white font-semibold w-[90px] text-right">Totale</TableHead>
                                    <TableHead className="w-[40px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {formData.items.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={10} className="text-center py-12 text-slate-500">
                                            <Package className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                                            <p>Nessun materiale ancora</p>
                                            <Button
                                                className="mt-4"
                                                variant="outline"
                                                onClick={addItem}
                                            >
                                                <Plus className="h-4 w-4 mr-2" />
                                                Aggiungi Prima Riga
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    formData.items.map((item, index) => {
                                        // Calculate line total
                                        const qty = parseFloat(item.quantity) || 0;
                                        const cost = parseFloat(item.cost_per_unit) || 0;
                                        const lineTotal = qty * cost;
                                        
                                        return (
                                            <TableRow key={item.item_id || index} className="hover:bg-slate-50">
                                                <TableCell className="p-1">
                                                    <Select
                                                        value={item.category}
                                                        onValueChange={(v) => updateItem(index, 'category', v)}
                                                    >
                                                        <SelectTrigger className="h-8 text-sm">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {CATEGORIES.map(c => (
                                                                <SelectItem key={c.value} value={c.value}>
                                                                    {c.label}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        value={item.code}
                                                        onChange={(e) => updateItem(index, 'code', e.target.value)}
                                                        className="h-8 text-sm"
                                                        placeholder="COD"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        value={item.name}
                                                        onChange={(e) => updateItem(index, 'name', e.target.value)}
                                                        className="h-8 text-sm"
                                                        placeholder="Nome materiale"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        type="number"
                                                        value={item.length_mm}
                                                        onChange={(e) => updateItem(index, 'length_mm', e.target.value)}
                                                        className="h-8 text-sm text-right"
                                                        min="0"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        type="number"
                                                        value={item.quantity}
                                                        onChange={(e) => updateItem(index, 'quantity', e.target.value)}
                                                        className="h-8 text-sm text-right"
                                                        min="0"
                                                        step="0.01"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Select
                                                        value={item.unit}
                                                        onValueChange={(v) => updateItem(index, 'unit', v)}
                                                    >
                                                        <SelectTrigger className="h-8 text-sm w-16">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {UNITS.map(u => (
                                                                <SelectItem key={u.value} value={u.value}>
                                                                    {u.label}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        type="number"
                                                        value={item.weight_per_unit}
                                                        onChange={(e) => updateItem(index, 'weight_per_unit', e.target.value)}
                                                        className="h-8 text-sm text-right"
                                                        min="0"
                                                        step="0.01"
                                                        placeholder="kg"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input
                                                        type="number"
                                                        value={item.cost_per_unit}
                                                        onChange={(e) => updateItem(index, 'cost_per_unit', e.target.value)}
                                                        className="h-8 text-sm text-right"
                                                        min="0"
                                                        step="0.01"
                                                        placeholder="€"
                                                    />
                                                </TableCell>
                                                <TableCell className="p-1 text-right font-medium bg-slate-50">
                                                    {formatCurrency(lineTotal)}
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => removeItem(index)}
                                                        className="h-8 w-8 p-0 text-slate-400 hover:text-red-600"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* Totals */}
                <Card className="border-slate-200">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-lg font-semibold flex items-center gap-2">
                            <Calculator className="h-5 w-5" />
                            Riepilogo
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-4 gap-6">
                            <div className="text-center p-4 bg-slate-50 rounded-lg">
                                <Package className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                                <p className="text-2xl font-bold text-slate-900">{totals.total_items}</p>
                                <p className="text-sm text-slate-500">Articoli</p>
                            </div>
                            <div className="text-center p-4 bg-slate-50 rounded-lg">
                                <div className="h-6 w-6 mx-auto mb-2 text-slate-600 font-bold">m</div>
                                <p className="text-2xl font-bold text-slate-900">
                                    {totals.total_length_m?.toFixed(2)}
                                </p>
                                <p className="text-sm text-slate-500">Lunghezza Tot.</p>
                            </div>
                            <div className="text-center p-4 bg-slate-50 rounded-lg">
                                <Weight className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                                <p className="text-2xl font-bold text-slate-900">
                                    {totals.total_weight_kg?.toFixed(2)}
                                </p>
                                <p className="text-sm text-slate-500">Peso (kg)</p>
                            </div>
                            <div className="text-center p-4 bg-amber-50 rounded-lg border border-amber-200">
                                <Euro className="h-6 w-6 mx-auto mb-2 text-amber-700" />
                                <p className="text-2xl font-bold text-amber-700">
                                    {formatCurrency(totals.total_cost)}
                                </p>
                                <p className="text-sm text-amber-600">Costo Totale</p>
                            </div>
                        </div>

                        {/* Category Breakdown */}
                        {Object.keys(totals.by_category || {}).length > 0 && (
                            <>
                                <Separator className="my-6" />
                                <h4 className="font-semibold text-slate-900 mb-3">Per Categoria</h4>
                                <div className="grid grid-cols-3 gap-4">
                                    {Object.entries(totals.by_category || {}).map(([category, data]) => (
                                        <div key={category} className="p-3 border border-slate-200 rounded-lg">
                                            <p className="font-medium text-slate-900 capitalize">{category}</p>
                                            <div className="flex justify-between text-sm text-slate-500 mt-1">
                                                <span>{data.count} art.</span>
                                                <span>{data.weight?.toFixed(2)} kg</span>
                                                <span>{formatCurrency(data.cost)}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Import from Rilievo Dialog */}
            <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="font-serif">Importa da Rilievo</DialogTitle>
                        <DialogDescription>
                            Seleziona un rilievo per importare automaticamente i materiali 
                            basati sulle dimensioni degli schizzi.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <Label>Rilievo</Label>
                        <Select
                            value={selectedRilievoForImport}
                            onValueChange={setSelectedRilievoForImport}
                        >
                            <SelectTrigger data-testid="select-import-rilievo">
                                <SelectValue placeholder="Seleziona rilievo..." />
                            </SelectTrigger>
                            <SelectContent>
                                {rilievi.map(r => (
                                    <SelectItem key={r.rilievo_id} value={r.rilievo_id}>
                                        {r.project_name} - {r.client_name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <p className="text-sm text-slate-500 mt-2">
                            Nota: I materiali verranno aggiunti a quelli esistenti.
                        </p>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
                            Annulla
                        </Button>
                        <Button
                            onClick={handleImportFromRilievo}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            <Import className="h-4 w-4 mr-2" />
                            Importa
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
