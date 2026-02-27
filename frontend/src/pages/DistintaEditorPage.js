/**
 * Distinta Editor Page - Smart BOM for Fabbri
 * Profile selection with auto-calculated weight and surface.
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
    SelectGroup,
    SelectItem,
    SelectLabel,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Dialog, DialogContent, DialogDescription, DialogFooter,
    DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import {
    Save, ArrowLeft, Plus, Trash2, Import, Package,
    Weight, Calculator, FileDown, BarChart3, Ruler,
    Scissors, ChevronDown, ChevronUp, Settings2,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const formatNumber = (v, dec = 2) =>
    new Intl.NumberFormat('it-IT', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(v || 0);
const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const emptyItem = () => ({
    item_id: '',
    category: 'profilo',
    code: '',
    name: '',
    profile_id: '',
    profile_label: '',
    length_mm: 0,
    quantity: 1,
    weight_per_meter: 0,
    surface_per_meter: 0,
    cost_per_unit: 0,
    notes: '',
});

export default function DistintaEditorPage() {
    const navigate = useNavigate();
    const { distintaId } = useParams();
    const [searchParams] = useSearchParams();
    const rilievoIdFromUrl = searchParams.get('rilievo_id');
    const isEditing = !!distintaId;

    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [profiles, setProfiles] = useState([]);
    const [profileTypes, setProfileTypes] = useState([]);
    const [clients, setClients] = useState([]);
    const [rilievi, setRilievi] = useState([]);
    const [importDialogOpen, setImportDialogOpen] = useState(false);
    const [selectedRilievoForImport, setSelectedRilievoForImport] = useState('');
    const [rilievoImportData, setRilievoImportData] = useState(null);
    const [loadingImportData, setLoadingImportData] = useState(false);
    const [targetRowIdx, setTargetRowIdx] = useState(null);
    const [barResults, setBarResults] = useState(null);
    const [barDialogOpen, setBarDialogOpen] = useState(false);
    const [optimizerResult, setOptimizerResult] = useState(null);
    const [optimizerOpen, setOptimizerOpen] = useState(false);
    const [optimizerLoading, setOptimizerLoading] = useState(false);
    const [optimizerParams, setOptimizerParams] = useState({ bar_length_mm: 6000, kerf_mm: 3 });
    const [expandedProfiles, setExpandedProfiles] = useState({});

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
        total_surface_mq: 0,
        total_cost: 0,
    });

    // Fetch profiles catalog
    useEffect(() => {
        const fetchProfiles = async () => {
            try {
                const data = await apiRequest('/distinte/profiles');
                setProfiles(data.profiles || []);
                setProfileTypes(data.types || []);
            } catch { /* ignore */ }
        };
        fetchProfiles();
    }, []);

    // Fetch clients
    useEffect(() => {
        const fetchClients = async () => {
            try {
                const data = await apiRequest('/clients/');
                setClients(data.clients || []);
            } catch { /* ignore */ }
        };
        fetchClients();
    }, []);

    // Fetch rilievi
    useEffect(() => {
        const fetchRilievi = async () => {
            try {
                const data = await apiRequest('/rilievi/');
                setRilievi(data.rilievi || []);
            } catch { /* ignore */ }
        };
        fetchRilievi();
    }, []);

    // Calculate totals from items
    const recalculateTotals = useCallback((items) => {
        let tl = 0, tw = 0, ts = 0, tc = 0;
        items.forEach(it => {
            const lm = (it.length_mm || 0) / 1000;
            const q = it.quantity || 1;
            const rw = lm * q * (it.weight_per_meter || 0);
            const rs = lm * q * (it.surface_per_meter || 0);
            const rc = (it.cost_per_unit || 0) * q;
            tl += lm * q;
            tw += rw;
            ts += rs;
            tc += rc;
        });
        setTotals({
            total_items: items.length,
            total_length_m: Math.round(tl * 1000) / 1000,
            total_weight_kg: Math.round(tw * 1000) / 1000,
            total_surface_mq: Math.round(ts * 1000) / 1000,
            total_cost: Math.round(tc * 100) / 100,
        });
    }, []);

    // Fetch existing distinta
    useEffect(() => {
        if (!isEditing) return;
        const fetchDistinta = async () => {
            try {
                const data = await apiRequest(`/distinte/${distintaId}`);
                setFormData({
                    name: data.name || '',
                    rilievo_id: data.rilievo_id || '',
                    client_id: data.client_id || '',
                    status: data.status || 'bozza',
                    notes: data.notes || '',
                    items: data.items || [],
                });
                recalculateTotals(data.items || []);
            } catch {
                toast.error('Errore nel caricamento della distinta');
                navigate('/distinte');
            } finally {
                setLoading(false);
            }
        };
        fetchDistinta();
    }, [isEditing, distintaId, navigate, recalculateTotals]);

    // Item manipulation
    const addItem = () => {
        const items = [...formData.items, emptyItem()];
        setFormData(prev => ({ ...prev, items }));
        recalculateTotals(items);
    };

    const removeItem = (index) => {
        const items = formData.items.filter((_, i) => i !== index);
        setFormData(prev => ({ ...prev, items }));
        recalculateTotals(items);
    };

    const updateItem = (index, field, value) => {
        const items = [...formData.items];
        items[index] = { ...items[index], [field]: value };
        setFormData(prev => ({ ...prev, items }));
        recalculateTotals(items);
    };

    const selectProfile = (index, profileId) => {
        const profile = profiles.find(p => p.profile_id === profileId);
        if (!profile) return;
        const items = [...formData.items];
        items[index] = {
            ...items[index],
            profile_id: profile.profile_id,
            profile_label: profile.label,
            name: profile.label,
            weight_per_meter: profile.weight_per_meter,
            surface_per_meter: profile.surface_per_meter,
        };
        setFormData(prev => ({ ...prev, items }));
        recalculateTotals(items);
    };

    // Row calculations
    const getRowWeight = (item) => {
        const lm = (item.length_mm || 0) / 1000;
        return lm * (item.quantity || 1) * (item.weight_per_meter || 0);
    };
    const getRowSurface = (item) => {
        const lm = (item.length_mm || 0) / 1000;
        return lm * (item.quantity || 1) * (item.surface_per_meter || 0);
    };

    // Save
    const handleSave = async () => {
        if (!formData.name.trim()) {
            toast.error('Inserisci il nome della distinta');
            return;
        }
        setSaving(true);
        try {
            const payload = {
                name: formData.name,
                rilievo_id: formData.client_id ? formData.rilievo_id : formData.rilievo_id,
                client_id: formData.client_id || null,
                notes: formData.notes,
                items: formData.items.map(it => ({
                    ...it,
                    length_mm: parseFloat(it.length_mm) || 0,
                    quantity: parseFloat(it.quantity) || 1,
                    weight_per_meter: parseFloat(it.weight_per_meter) || 0,
                    surface_per_meter: parseFloat(it.surface_per_meter) || 0,
                    cost_per_unit: parseFloat(it.cost_per_unit) || 0,
                })),
            };
            if (isEditing) {
                payload.status = formData.status;
                await apiRequest(`/distinte/${distintaId}`, { method: 'PUT', body: payload });
                toast.success('Distinta aggiornata');
            } else {
                const res = await apiRequest('/distinte/', { method: 'POST', body: payload });
                toast.success('Distinta creata');
                navigate(`/distinte/${res.distinta_id}`);
            }
        } catch (err) {
            toast.error(err.message || 'Errore nel salvataggio');
        } finally {
            setSaving(false);
        }
    };

    // Calcola Barre
    const handleCalcolaBarre = async () => {
        if (!isEditing) {
            toast.error('Salva la distinta prima di calcolare le barre');
            return;
        }
        try {
            await handleSave();
            const data = await apiRequest(`/distinte/${distintaId}/calcola-barre`, { method: 'POST' });
            setBarResults(data);
            setBarDialogOpen(true);
        } catch (err) {
            toast.error(err.message || 'Errore nel calcolo barre');
        }
    };

    // Download Lista Taglio PDF
    const handleDownloadPdf = async () => {
        if (!isEditing) {
            toast.error('Salva la distinta prima di scaricare il PDF');
            return;
        }
        try {
            await handleSave();
            const backendUrl = process.env.REACT_APP_BACKEND_URL;
            window.open(`${backendUrl}/api/distinte/${distintaId}/lista-taglio-pdf`, '_blank');
        } catch (err) {
            toast.error(err.message || 'Errore nel download PDF');
        }
    };

    // Import from rilievo
    const handleImportFromRilievo = async () => {
        if (!isEditing || !selectedRilievoForImport) return;
        try {
            const data = await apiRequest(
                `/distinte/${distintaId}/import-rilievo/${selectedRilievoForImport}`,
                { method: 'POST' }
            );
            setFormData({
                name: data.name || formData.name,
                rilievo_id: data.rilievo_id || '',
                client_id: data.client_id || '',
                status: data.status || 'bozza',
                notes: data.notes || '',
                items: data.items || [],
            });
            recalculateTotals(data.items || []);
            toast.success('Rilievo collegato alla distinta');
        } catch (err) {
            toast.error(err.message || 'Errore nell\'importazione');
        }
    };

    const handleSelectRilievoForImport = async (rilievoId) => {
        setSelectedRilievoForImport(rilievoId);
        if (!rilievoId) { setRilievoImportData(null); return; }
        setLoadingImportData(true);
        try {
            const data = await apiRequest(`/distinte/rilievo-data/${rilievoId}`);
            setRilievoImportData(data);
        } catch {
            setRilievoImportData(null);
        } finally {
            setLoadingImportData(false);
        }
    };

    const handleApplyDimension = (valueMm) => {
        if (targetRowIdx === null || targetRowIdx >= formData.items.length) {
            // No row selected — add new row with this dimension
            const newItem = { ...emptyItem(), length_mm: valueMm };
            const items = [...formData.items, newItem];
            setFormData(prev => ({ ...prev, items }));
            recalculateTotals(items);
            toast.success(`${valueMm} mm aggiunto come nuova riga`);
        } else {
            updateItem(targetRowIdx, 'length_mm', valueMm);
            toast.success(`${valueMm} mm applicato alla riga ${targetRowIdx + 1}`);
        }
        setTargetRowIdx(null);
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                </div>
            </DashboardLayout>
        );
    }

    // Group profiles by type for dropdown
    const profilesByType = {};
    profiles.forEach(p => {
        if (!profilesByType[p.type]) profilesByType[p.type] = [];
        profilesByType[p.type].push(p);
    });

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="distinta-editor">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button data-testid="btn-back" variant="outline" onClick={() => navigate('/distinte')} className="h-10">
                            <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                        </Button>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B]">
                            {isEditing ? 'Modifica Distinta' : 'Nuova Distinta Materiali'}
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        {isEditing && (
                            <>
                                <Button data-testid="btn-calcola-barre" variant="outline" onClick={handleCalcolaBarre} className="h-10 border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                    <BarChart3 className="h-4 w-4 mr-2" /> Calcola Barre
                                </Button>
                                <Button data-testid="btn-download-pdf" variant="outline" onClick={handleDownloadPdf} className="h-10 border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                    <FileDown className="h-4 w-4 mr-2" /> Stampa Lista Taglio
                                </Button>
                            </>
                        )}
                        <Button data-testid="btn-save" onClick={handleSave} disabled={saving} className="h-10 bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Save className="h-4 w-4 mr-2" /> {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </div>
                </div>

                {/* Info Card */}
                <Card className="border-gray-200">
                    <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                        <CardTitle className="text-lg font-semibold">Informazioni Progetto</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="grid grid-cols-4 gap-4">
                            <div>
                                <Label>Nome Distinta *</Label>
                                <Input data-testid="input-name" value={formData.name} onChange={(e) => setFormData(p => ({ ...p, name: e.target.value }))} placeholder="es. Cancello Via Roma" className="mt-1" />
                            </div>
                            <div>
                                <Label>Cliente</Label>
                                <Select value={formData.client_id || 'none'} onValueChange={(v) => setFormData(p => ({ ...p, client_id: v === 'none' ? '' : v }))}>
                                    <SelectTrigger data-testid="select-client" className="mt-1"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="none">Nessun cliente</SelectItem>
                                        {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Rilievo Collegato</Label>
                                <div className="flex gap-2 mt-1">
                                    <Select value={formData.rilievo_id || 'none'} onValueChange={(v) => setFormData(p => ({ ...p, rilievo_id: v === 'none' ? '' : v }))}>
                                        <SelectTrigger data-testid="select-rilievo"><SelectValue placeholder="Nessuno" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="none">Nessun rilievo</SelectItem>
                                            {rilievi.map(r => <SelectItem key={r.rilievo_id} value={r.rilievo_id}>{r.project_name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                    {isEditing && (
                                        <Button data-testid="btn-import-rilievo" variant="outline" onClick={() => setImportDialogOpen(true)} className="shrink-0" title="Importa da Rilievo">
                                            <Import className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                            </div>
                            {isEditing && (
                                <div>
                                    <Label>Stato</Label>
                                    <Select value={formData.status} onValueChange={(v) => setFormData(p => ({ ...p, status: v }))}>
                                        <SelectTrigger data-testid="select-status" className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="bozza">Bozza</SelectItem>
                                            <SelectItem value="confermata">Confermata</SelectItem>
                                            <SelectItem value="ordinata">Ordinata</SelectItem>
                                            <SelectItem value="completata">Completata</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}
                        </div>
                        {formData.notes !== undefined && (
                            <div className="mt-4">
                                <Label>Note</Label>
                                <Textarea data-testid="input-notes" value={formData.notes || ''} onChange={(e) => setFormData(p => ({ ...p, notes: e.target.value }))} placeholder="Note aggiuntive..." rows={2} className="mt-1" />
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Materials Grid */}
                <Card className="border-gray-200">
                    <CardHeader className="flex flex-row items-center justify-between pb-4 bg-blue-50 border-b border-gray-200">
                        <CardTitle className="text-lg font-semibold">Materiali</CardTitle>
                        <Button data-testid="btn-add-item" onClick={addItem} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Plus className="h-4 w-4 mr-2" /> Aggiungi Riga
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="overflow-x-auto">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-[#1E293B] hover:bg-[#1E293B]">
                                        <TableHead className="text-white font-medium w-[40px]">#</TableHead>
                                        <TableHead className="text-white font-medium w-[280px]">Profilo</TableHead>
                                        <TableHead className="text-white font-medium w-[110px] text-right">Lung. (mm)</TableHead>
                                        <TableHead className="text-white font-medium w-[80px] text-right">Q.ta</TableHead>
                                        <TableHead className="text-white font-medium w-[110px] text-right">Peso/m (kg)</TableHead>
                                        <TableHead className="text-white font-medium w-[110px] text-right">Sup./m (mq)</TableHead>
                                        <TableHead className="text-white font-medium w-[100px] text-right">Peso (kg)</TableHead>
                                        <TableHead className="text-white font-medium w-[100px] text-right">Sup. (mq)</TableHead>
                                        <TableHead className="text-white font-medium w-[40px]"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {formData.items.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={9} className="text-center py-12 text-slate-400">
                                                <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                                <p>Nessun materiale. Clicca "Aggiungi Riga" per iniziare.</p>
                                            </TableCell>
                                        </TableRow>
                                    ) : formData.items.map((item, idx) => {
                                        const rowW = getRowWeight(item);
                                        const rowS = getRowSurface(item);
                                        return (
                                            <TableRow key={idx} className="hover:bg-blue-50/30">
                                                <TableCell className="p-1 text-center font-mono text-sm text-slate-400">{idx + 1}</TableCell>
                                                <TableCell className="p-1">
                                                    <Select value={item.profile_id || 'custom'} onValueChange={(v) => v === 'custom' ? updateItem(idx, 'profile_id', '') : selectProfile(idx, v)}>
                                                        <SelectTrigger data-testid={`select-profile-${idx}`} className="h-8 text-sm">
                                                            <SelectValue placeholder="Seleziona profilo..." />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="custom">-- Manuale --</SelectItem>
                                                            {profileTypes.map(pt => (
                                                                <SelectGroup key={pt.value}>
                                                                    <SelectLabel className="text-[#0055FF] font-semibold">{pt.label}</SelectLabel>
                                                                    {(profilesByType[pt.value] || []).map(p => (
                                                                        <SelectItem key={p.profile_id} value={p.profile_id}>
                                                                            {p.label} ({p.weight_per_meter} kg/m)
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectGroup>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                    {!item.profile_id && (
                                                        <Input data-testid={`input-name-${idx}`} value={item.name} onChange={(e) => updateItem(idx, 'name', e.target.value)} placeholder="Nome manuale" className="mt-1 h-7 text-sm" />
                                                    )}
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input data-testid={`input-length-${idx}`} type="number" value={item.length_mm || ''} onChange={(e) => updateItem(idx, 'length_mm', parseFloat(e.target.value) || 0)} className="h-8 text-right font-mono text-sm" />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input data-testid={`input-qty-${idx}`} type="number" value={item.quantity || ''} onChange={(e) => updateItem(idx, 'quantity', parseFloat(e.target.value) || 1)} className="h-8 text-right font-mono text-sm" min={1} />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input type="number" value={item.weight_per_meter || ''} onChange={(e) => updateItem(idx, 'weight_per_meter', parseFloat(e.target.value) || 0)} className="h-8 text-right font-mono text-sm" disabled={!!item.profile_id} step="0.01" />
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Input type="number" value={item.surface_per_meter || ''} onChange={(e) => updateItem(idx, 'surface_per_meter', parseFloat(e.target.value) || 0)} className="h-8 text-right font-mono text-sm" disabled={!!item.profile_id} step="0.001" />
                                                </TableCell>
                                                <TableCell className="p-1 text-right font-mono font-semibold text-[#0055FF] bg-slate-50">
                                                    {formatNumber(rowW, 2)}
                                                </TableCell>
                                                <TableCell className="p-1 text-right font-mono font-semibold text-[#0055FF] bg-slate-50">
                                                    {formatNumber(rowS, 3)}
                                                </TableCell>
                                                <TableCell className="p-1">
                                                    <Button data-testid={`btn-remove-${idx}`} variant="ghost" size="icon" onClick={() => removeItem(idx)} className="h-7 w-7 text-red-500 hover:text-red-700 hover:bg-red-50">
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        </div>
                    </CardContent>
                </Card>

                {/* Riepilogo */}
                <Card className="border-gray-200">
                    <CardHeader className="pb-4 bg-blue-50 border-b border-gray-200">
                        <CardTitle className="text-lg font-semibold flex items-center gap-2">
                            <Calculator className="h-5 w-5" /> Riepilogo
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="grid grid-cols-5 gap-6">
                            <div className="text-center p-4 bg-slate-50 rounded-lg">
                                <Package className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                                <p data-testid="total-items" className="text-2xl font-mono font-bold text-[#0055FF]">{totals.total_items}</p>
                                <p className="text-sm text-slate-500">Articoli</p>
                            </div>
                            <div className="text-center p-4 bg-slate-50 rounded-lg">
                                <Ruler className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                                <p data-testid="total-length" className="text-2xl font-mono font-bold text-[#0055FF]">{formatNumber(totals.total_length_m, 2)}</p>
                                <p className="text-sm text-slate-500">Lunghezza (m)</p>
                            </div>
                            <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
                                <Weight className="h-6 w-6 mx-auto mb-2 text-[#0055FF]" />
                                <p data-testid="total-weight" className="text-2xl font-mono font-bold text-[#0055FF]">{formatNumber(totals.total_weight_kg, 2)}</p>
                                <p className="text-sm text-blue-600">Peso Totale (kg)</p>
                            </div>
                            <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
                                <BarChart3 className="h-6 w-6 mx-auto mb-2 text-[#0055FF]" />
                                <p data-testid="total-surface" className="text-2xl font-mono font-bold text-[#0055FF]">{formatNumber(totals.total_surface_mq, 3)}</p>
                                <p className="text-sm text-blue-600">Superficie (mq)</p>
                            </div>
                            <div className="text-center p-4 bg-slate-50 rounded-lg">
                                <Calculator className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                                <p data-testid="total-cost" className="text-2xl font-mono font-bold text-[#0055FF]">{formatCurrency(totals.total_cost)}</p>
                                <p className="text-sm text-slate-500">Costo Totale</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Bar Calculation Dialog */}
            <Dialog open={barDialogOpen} onOpenChange={setBarDialogOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="font-sans text-xl text-[#1E293B] flex items-center gap-2">
                            <BarChart3 className="h-5 w-5 text-[#0055FF]" /> Calcolo Barre (6m)
                        </DialogTitle>
                        <DialogDescription>
                            Quante barre da 6 metri servono per ogni profilo.
                        </DialogDescription>
                    </DialogHeader>
                    {barResults && (
                        <div className="space-y-4">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-[#1E293B] hover:bg-[#1E293B]">
                                        <TableHead className="text-white font-medium">Profilo</TableHead>
                                        <TableHead className="text-white font-medium text-right">Lung. Tot.</TableHead>
                                        <TableHead className="text-white font-medium text-right">Barre 6m</TableHead>
                                        <TableHead className="text-white font-medium text-right">Sfrido</TableHead>
                                        <TableHead className="text-white font-medium text-right">%</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {barResults.results.map((r, i) => (
                                        <TableRow key={i}>
                                            <TableCell className="font-medium">{r.profile_label}</TableCell>
                                            <TableCell className="text-right font-mono">{formatNumber(r.total_length_m)} m</TableCell>
                                            <TableCell className="text-right font-mono font-bold text-[#0055FF]">{r.bars_needed}</TableCell>
                                            <TableCell className="text-right font-mono text-sm">{formatNumber(r.waste_mm, 0)} mm</TableCell>
                                            <TableCell className={`text-right font-mono text-sm ${r.waste_percent > 30 ? 'text-red-500' : 'text-emerald-600'}`}>
                                                {formatNumber(r.waste_percent, 1)}%
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                            <Separator />
                            <div className="flex justify-between items-center text-lg font-bold">
                                <span className="text-[#1E293B]">Totale Barre da Acquistare:</span>
                                <span data-testid="total-bars" className="font-mono text-[#0055FF]">{barResults.total_bars}</span>
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setBarDialogOpen(false)}>Chiudi</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Import from Rilievo — Split Screen Dialog */}
            <Dialog open={importDialogOpen} onOpenChange={(open) => { setImportDialogOpen(open); if (!open) { setRilievoImportData(null); setSelectedRilievoForImport(''); setTargetRowIdx(null); } }}>
                <DialogContent className="sm:max-w-[900px] max-h-[85vh] overflow-hidden" data-testid="import-rilievo-dialog">
                    <DialogHeader>
                        <DialogTitle className="font-sans text-xl text-[#1E293B] flex items-center gap-2">
                            <Import className="h-5 w-5 text-[#0055FF]" /> Importa da Rilievo
                        </DialogTitle>
                        <DialogDescription>
                            Seleziona un rilievo, poi clicca una misura per applicarla a una riga della distinta.
                        </DialogDescription>
                    </DialogHeader>

                    {/* Rilievo Selector */}
                    <div className="flex gap-3 items-end">
                        <div className="flex-1">
                            <Select value={selectedRilievoForImport} onValueChange={handleSelectRilievoForImport}>
                                <SelectTrigger data-testid="import-rilievo-select"><SelectValue placeholder="Seleziona rilievo..." /></SelectTrigger>
                                <SelectContent>
                                    {rilievi.map(r => (
                                        <SelectItem key={r.rilievo_id} value={r.rilievo_id}>{r.project_name} - {r.client_name || 'N/A'}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <Button data-testid="btn-confirm-import" onClick={handleImportFromRilievo} disabled={!selectedRilievoForImport || !isEditing} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Import className="h-4 w-4 mr-2" /> Collega
                        </Button>
                    </div>

                    {/* Split Screen Content */}
                    {loadingImportData ? (
                        <div className="flex items-center justify-center py-12"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" /></div>
                    ) : rilievoImportData ? (
                        <div className="grid grid-cols-2 gap-4 overflow-y-auto max-h-[50vh] mt-2">
                            {/* LEFT: Rilievo Data */}
                            <div className="space-y-3 border-r pr-4" data-testid="rilievo-panel">
                                <div className="bg-blue-50 rounded-lg p-3">
                                    <h3 className="text-sm font-semibold text-[#1E293B]">{rilievoImportData.project_name}</h3>
                                    {rilievoImportData.location && <p className="text-xs text-slate-500 mt-1">{rilievoImportData.location}</p>}
                                </div>

                                {/* Notes */}
                                {rilievoImportData.notes && (
                                    <div>
                                        <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Note Tecniche</p>
                                        <div className="bg-slate-50 rounded p-2 text-xs text-[#1E293B] whitespace-pre-wrap max-h-[120px] overflow-y-auto">{rilievoImportData.notes}</div>
                                    </div>
                                )}

                                {/* Sketches */}
                                {rilievoImportData.sketches?.length > 0 && (
                                    <div>
                                        <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Schizzi ({rilievoImportData.sketches.length})</p>
                                        {rilievoImportData.sketches.map((s, i) => (
                                            <div key={i} className="bg-slate-50 rounded p-2 mb-2">
                                                <span className="text-xs font-medium text-[#1E293B]">{s.name}</span>
                                                {Object.keys(s.dimensions || {}).length > 0 && (
                                                    <div className="flex flex-wrap gap-1 mt-1">
                                                        {Object.entries(s.dimensions).map(([k, v]) => (
                                                            <span key={k} className="text-[10px] bg-blue-100 text-[#0055FF] px-1.5 py-0.5 rounded font-mono">{k}: {v}</span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Parsed Dimensions — Clickable chips */}
                                <div>
                                    <p className="text-xs font-semibold text-slate-500 uppercase mb-2">
                                        Misure Trovate ({rilievoImportData.dimensions?.length || 0})
                                    </p>
                                    {rilievoImportData.dimensions?.length > 0 ? (
                                        <div className="flex flex-wrap gap-2" data-testid="dimensions-chips">
                                            {rilievoImportData.dimensions.map(d => (
                                                <button
                                                    key={d.dim_id}
                                                    data-testid={`dim-chip-${d.dim_id}`}
                                                    onClick={() => handleApplyDimension(d.value_mm)}
                                                    className="flex items-center gap-1.5 bg-white border-2 border-[#0055FF] text-[#0055FF] hover:bg-[#0055FF] hover:text-white rounded-lg px-3 py-1.5 text-sm font-mono font-semibold transition-colors cursor-pointer"
                                                >
                                                    <Ruler className="h-3.5 w-3.5" />
                                                    {d.label}
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-xs text-slate-400 italic">Nessuna misura strutturata trovata. Usa le note per inserire dimensioni (es. "H=2200", "1500x900").</p>
                                    )}
                                </div>
                            </div>

                            {/* RIGHT: Target BOM rows */}
                            <div className="space-y-3" data-testid="bom-target-panel">
                                <p className="text-xs font-semibold text-slate-500 uppercase">
                                    Riga Destinazione {targetRowIdx !== null ? `(Riga ${targetRowIdx + 1} selezionata)` : '(clicca una riga o aggiungi nuova)'}
                                </p>
                                <div className="space-y-1 max-h-[300px] overflow-y-auto">
                                    {formData.items.length === 0 ? (
                                        <p className="text-xs text-slate-400 italic py-4 text-center">Nessuna riga. Clicca una misura per aggiungerne una.</p>
                                    ) : (
                                        formData.items.map((item, i) => (
                                            <button
                                                key={i}
                                                data-testid={`target-row-${i}`}
                                                onClick={() => setTargetRowIdx(targetRowIdx === i ? null : i)}
                                                className={`w-full text-left flex items-center justify-between px-3 py-2 rounded border text-sm transition-colors ${targetRowIdx === i ? 'border-[#0055FF] bg-blue-50 ring-1 ring-[#0055FF]' : 'border-gray-200 hover:border-blue-300'}`}
                                            >
                                                <div className="flex items-center gap-2 min-w-0">
                                                    <span className="text-xs text-slate-400 font-mono w-5">{i + 1}</span>
                                                    <span className="text-[#1E293B] truncate">{item.name || item.profile_label || 'Voce vuota'}</span>
                                                </div>
                                                <span className="font-mono text-xs text-[#0055FF] shrink-0 ml-2">{item.length_mm || 0} mm</span>
                                            </button>
                                        ))
                                    )}
                                </div>
                                <p className="text-[10px] text-slate-400">
                                    Seleziona una riga, poi clicca una misura a sinistra per applicarla. Senza selezione, viene creata una nuova riga.
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-slate-400">
                            <Ruler className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                            <p className="text-sm">Seleziona un rilievo per vedere le misure disponibili</p>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setImportDialogOpen(false)}>Chiudi</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
