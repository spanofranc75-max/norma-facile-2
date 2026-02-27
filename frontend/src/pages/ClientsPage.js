/**
 * Clients List Page - Anagrafica Clienti
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
    Plus,
    Search,
    Pencil,
    Trash2,
    Building2,
    User,
    Landmark,
    Ruler,
    FolderOpen,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const CLIENT_TYPES = {
    azienda: { label: 'Azienda', icon: Building2 },
    privato: { label: 'Privato', icon: User },
    pa: { label: 'P.A.', icon: Landmark },
};

const emptyClient = {
    business_name: '',
    client_type: 'azienda',
    codice_fiscale: '',
    partita_iva: '',
    codice_sdi: '0000000',
    pec: '',
    address: '',
    cap: '',
    city: '',
    province: '',
    country: 'IT',
    phone: '',
    email: '',
    notes: '',
};

export default function ClientsPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [clients, setClients] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingClient, setEditingClient] = useState(null);
    const [formData, setFormData] = useState(emptyClient);
    const [saving, setSaving] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [clientToDelete, setClientToDelete] = useState(null);

    const fetchClients = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (search) params.append('search', search);
            const data = await apiRequest(`/clients/?${params}`);
            setClients(data.clients);
            setTotal(data.total);
        } catch (error) {
            toast.error('Errore nel caricamento clienti');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchClients();
    }, [search]);

    const handleOpenDialog = (client = null) => {
        if (client) {
            setEditingClient(client);
            setFormData(client);
        } else {
            setEditingClient(null);
            setFormData(emptyClient);
        }
        setDialogOpen(true);
    };

    const handleSave = async () => {
        if (!formData.business_name.trim()) {
            toast.error('Inserisci la ragione sociale');
            return;
        }

        try {
            setSaving(true);
            if (editingClient) {
                await apiRequest(`/clients/${editingClient.client_id}`, {
                    method: 'PUT',
                    body: JSON.stringify(formData),
                });
                toast.success('Cliente aggiornato');
            } else {
                await apiRequest('/clients/', {
                    method: 'POST',
                    body: JSON.stringify(formData),
                });
                toast.success('Cliente creato');
            }
            setDialogOpen(false);
            fetchClients();
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!clientToDelete) return;
        try {
            await apiRequest(`/clients/${clientToDelete.client_id}`, {
                method: 'DELETE',
            });
            toast.success('Cliente eliminato');
            setDeleteDialogOpen(false);
            setClientToDelete(null);
            fetchClients();
        } catch (error) {
            toast.error(error.message);
        }
    };

    const updateField = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">
                            Anagrafica Clienti
                        </h1>
                        <p className="text-slate-600">
                            {total} client{total !== 1 ? 'i' : 'e'} registrat{total !== 1 ? 'i' : 'o'}
                        </p>
                    </div>
                    <Button
                        data-testid="btn-new-client"
                        onClick={() => handleOpenDialog()}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Nuovo Cliente
                    </Button>
                </div>

                {/* Search */}
                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                            <Input
                                data-testid="search-clients"
                                placeholder="Cerca per nome, P.IVA o C.F..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Ragione Sociale</TableHead>
                                    <TableHead className="text-white font-semibold">Tipo</TableHead>
                                    <TableHead className="text-white font-semibold">P.IVA / C.F.</TableHead>
                                    <TableHead className="text-white font-semibold">Località</TableHead>
                                    <TableHead className="text-white font-semibold">Cod. SDI</TableHead>
                                    <TableHead className="w-[100px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-8">
                                            <div className="w-6 h-6 loading-spinner mx-auto" />
                                        </TableCell>
                                    </TableRow>
                                ) : clients.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="p-0">
                                            <EmptyState
                                                type="clients"
                                                title="Nessun cliente registrato"
                                                description="Aggiungi il tuo primo cliente per iniziare a creare rilievi, preventivi e fatture."
                                                actionLabel="Crea il primo Cliente"
                                                onAction={() => handleOpenDialog()}
                                            />
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    clients.map((client) => {
                                        const TypeIcon = CLIENT_TYPES[client.client_type]?.icon || Building2;
                                        return (
                                            <TableRow
                                                key={client.client_id}
                                                data-testid={`client-row-${client.client_id}`}
                                                className="hover:bg-slate-50"
                                            >
                                                <TableCell className="font-medium">
                                                    {client.business_name}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="outline" className="gap-1">
                                                        <TypeIcon className="h-3 w-3" />
                                                        {CLIENT_TYPES[client.client_type]?.label}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="font-mono text-sm">
                                                    {client.partita_iva || client.codice_fiscale || '-'}
                                                </TableCell>
                                                <TableCell>
                                                    {client.city ? `${client.city} (${client.province})` : '-'}
                                                </TableCell>
                                                <TableCell className="font-mono text-sm">
                                                    {client.codice_sdi}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            data-testid={`rilievo-client-${client.client_id}`}
                                                            onClick={() => navigate(`/rilievi/new?client_id=${client.client_id}`)}
                                                            title="Nuovo Rilievo"
                                                        >
                                                            <Ruler className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            data-testid={`edit-client-${client.client_id}`}
                                                            onClick={() => handleOpenDialog(client)}
                                                        >
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            data-testid={`delete-client-${client.client_id}`}
                                                            onClick={() => {
                                                                setClientToDelete(client);
                                                                setDeleteDialogOpen(true);
                                                            }}
                                                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            {/* Create/Edit Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="font-sans">
                            {editingClient ? 'Modifica Cliente' : 'Nuovo Cliente'}
                        </DialogTitle>
                        <DialogDescription>
                            Inserisci i dati del cliente
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        {/* Basic Info */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="col-span-2">
                                <Label htmlFor="business_name">Ragione Sociale *</Label>
                                <Input
                                    id="business_name"
                                    data-testid="input-business-name"
                                    value={formData.business_name}
                                    onChange={(e) => updateField('business_name', e.target.value)}
                                    placeholder="Nome azienda o persona"
                                />
                            </div>
                            <div>
                                <Label htmlFor="client_type">Tipo Cliente</Label>
                                <Select
                                    value={formData.client_type}
                                    onValueChange={(v) => updateField('client_type', v)}
                                >
                                    <SelectTrigger data-testid="select-client-type">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="azienda">Azienda</SelectItem>
                                        <SelectItem value="privato">Privato</SelectItem>
                                        <SelectItem value="pa">Pubblica Amministrazione</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Fiscal Data */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="partita_iva">Partita IVA</Label>
                                <Input
                                    id="partita_iva"
                                    data-testid="input-piva"
                                    value={formData.partita_iva}
                                    onChange={(e) => updateField('partita_iva', e.target.value)}
                                    placeholder="IT12345678901"
                                />
                            </div>
                            <div>
                                <Label htmlFor="codice_fiscale">Codice Fiscale</Label>
                                <Input
                                    id="codice_fiscale"
                                    data-testid="input-cf"
                                    value={formData.codice_fiscale}
                                    onChange={(e) => updateField('codice_fiscale', e.target.value.toUpperCase())}
                                    placeholder="RSSMRA80A01H501U"
                                />
                            </div>
                            <div>
                                <Label htmlFor="codice_sdi">Codice SDI</Label>
                                <Input
                                    id="codice_sdi"
                                    data-testid="input-sdi"
                                    value={formData.codice_sdi}
                                    onChange={(e) => updateField('codice_sdi', e.target.value.toUpperCase())}
                                    placeholder="0000000"
                                    maxLength={7}
                                />
                            </div>
                            <div>
                                <Label htmlFor="pec">PEC</Label>
                                <Input
                                    id="pec"
                                    type="email"
                                    data-testid="input-pec"
                                    value={formData.pec}
                                    onChange={(e) => updateField('pec', e.target.value)}
                                    placeholder="azienda@pec.it"
                                />
                            </div>
                        </div>

                        {/* Address */}
                        <div className="grid grid-cols-4 gap-4">
                            <div className="col-span-4">
                                <Label htmlFor="address">Indirizzo</Label>
                                <Input
                                    id="address"
                                    data-testid="input-address"
                                    value={formData.address}
                                    onChange={(e) => updateField('address', e.target.value)}
                                    placeholder="Via Roma 1"
                                />
                            </div>
                            <div>
                                <Label htmlFor="cap">CAP</Label>
                                <Input
                                    id="cap"
                                    data-testid="input-cap"
                                    value={formData.cap}
                                    onChange={(e) => updateField('cap', e.target.value)}
                                    placeholder="00100"
                                    maxLength={5}
                                />
                            </div>
                            <div className="col-span-2">
                                <Label htmlFor="city">Città</Label>
                                <Input
                                    id="city"
                                    data-testid="input-city"
                                    value={formData.city}
                                    onChange={(e) => updateField('city', e.target.value)}
                                    placeholder="Roma"
                                />
                            </div>
                            <div>
                                <Label htmlFor="province">Prov.</Label>
                                <Input
                                    id="province"
                                    data-testid="input-province"
                                    value={formData.province}
                                    onChange={(e) => updateField('province', e.target.value.toUpperCase())}
                                    placeholder="RM"
                                    maxLength={2}
                                />
                            </div>
                        </div>

                        {/* Contact */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="phone">Telefono</Label>
                                <Input
                                    id="phone"
                                    data-testid="input-phone"
                                    value={formData.phone}
                                    onChange={(e) => updateField('phone', e.target.value)}
                                    placeholder="+39 06 1234567"
                                />
                            </div>
                            <div>
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    data-testid="input-email"
                                    value={formData.email}
                                    onChange={(e) => updateField('email', e.target.value)}
                                    placeholder="info@azienda.it"
                                />
                            </div>
                        </div>

                        {/* Notes */}
                        <div>
                            <Label htmlFor="notes">Note</Label>
                            <Textarea
                                id="notes"
                                data-testid="input-notes"
                                value={formData.notes}
                                onChange={(e) => updateField('notes', e.target.value)}
                                placeholder="Note aggiuntive..."
                                rows={3}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDialogOpen(false)}
                        >
                            Annulla
                        </Button>
                        <Button
                            data-testid="btn-save-client"
                            onClick={handleSave}
                            disabled={saving}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="font-sans">Elimina Cliente</DialogTitle>
                        <DialogDescription>
                            Sei sicuro di voler eliminare <strong>{clientToDelete?.business_name}</strong>?
                            Questa azione non può essere annullata.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeleteDialogOpen(false)}
                        >
                            Annulla
                        </Button>
                        <Button
                            data-testid="btn-confirm-delete"
                            variant="destructive"
                            onClick={handleDelete}
                        >
                            Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
