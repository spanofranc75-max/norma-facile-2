/**
 * Fornitori (Suppliers) Page — Stessa logica della Scheda Cliente
 * Tab-based form: Anagrafica, Indirizzo, Contatti, Pagamento, Note
 * Filtra solo fornitori e cliente_fornitore.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Plus, Search, Pencil, Trash2, Factory, Phone, Mail, Globe,
    CreditCard, UserPlus, X, FolderOpen,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const TYPE_BADGES = {
    fornitore: { label: 'Fornitore', color: 'bg-amber-100 text-amber-800' },
    cliente_fornitore: { label: 'Cli/For', color: 'bg-emerald-100 text-emerald-800' },
    cliente: { label: 'Cliente', color: 'bg-blue-100 text-blue-800' },
};

const TABS = [
    { key: 'anagrafica', label: 'Anagrafica' },
    { key: 'indirizzo', label: 'Indirizzo' },
    { key: 'contatti', label: 'Contatti' },
    { key: 'pagamento', label: 'Pagamento' },
    { key: 'note', label: 'Note' },
];

const CONTACT_TYPES = ['Titolare', 'Commerciale', 'Amministrativo', 'Tecnico', 'Logistica', 'Altro'];

const emptySupplier = {
    business_name: '', client_type: 'fornitore', persona_fisica: false,
    titolo: '', cognome: '', nome: '',
    codice_fiscale: '', partita_iva: '', codice_sdi: '0000000', pec: '',
    address: '', cap: '', city: '', province: '', country: 'IT',
    phone: '', cellulare: '', fax: '', email: '', sito_web: '',
    contacts: [],
    payment_type_id: '', payment_type_label: '', iban: '', banca: '',
    supplier_payment_type_id: '', supplier_payment_type_label: '', supplier_iban: '', supplier_banca: '',
    notes: '',
};

const emptyContact = {
    tipo: 'Commerciale', nome: '', telefono: '', email: '',
    include_preventivi: false, include_fatture: false, include_solleciti: false,
    include_ordini: false, include_ddt: false, note: '',
};

export default function FornitoriPage() {
    const navigate = useNavigate();
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingSupplier, setEditingSupplier] = useState(null);
    const [formData, setFormData] = useState(emptySupplier);
    const [saving, setSaving] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [supplierToDelete, setSupplierToDelete] = useState(null);
    const [activeTab, setActiveTab] = useState('anagrafica');
    const [paymentTypes, setPaymentTypes] = useState([]);
    const [contactDialogOpen, setContactDialogOpen] = useState(false);
    const [editingContactIdx, setEditingContactIdx] = useState(null);
    const [contactForm, setContactForm] = useState(emptyContact);

    const fetchSuppliers = useCallback(async () => {
        try {
            const data = await apiRequest(`/clients/?client_type=fornitore&search=${searchQuery}&limit=100`);
            setSuppliers(data.clients || []);
        } catch (e) { toast.error('Errore caricamento fornitori'); }
        finally { setLoading(false); }
    }, [searchQuery]);

    const fetchPaymentTypes = useCallback(async () => {
        try {
            const data = await apiRequest('/payment-types/');
            setPaymentTypes(data.items || []);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => { fetchSuppliers(); }, [fetchSuppliers]);
    useEffect(() => { fetchPaymentTypes(); }, [fetchPaymentTypes]);

    const updateField = (key, val) => setFormData(f => ({ ...f, [key]: val }));

    const handleOpenDialog = async (supplier) => {
        if (supplier) {
            setEditingSupplier(supplier);
            setActiveTab('anagrafica');
            setDialogOpen(true);
            // Fetch full supplier details to ensure all fields (including payment) are loaded
            try {
                const fullData = await apiRequest(`/clients/${supplier.client_id}`);
                setFormData({ ...emptySupplier, ...fullData });
            } catch {
                // Fallback to list data if detail fetch fails
                setFormData({ ...emptySupplier, ...supplier });
            }
        } else {
            setEditingSupplier(null);
            setFormData(emptySupplier);
            setActiveTab('anagrafica');
            setDialogOpen(true);
        }
    };

    const handleSave = async () => {
        if (!formData.business_name) { toast.error('Ragione Sociale obbligatoria'); return; }
        setSaving(true);
        try {
            // Clean empty strings to null for Optional fields
            const payload = { ...formData };
            ['codice_fiscale', 'partita_iva', 'pec', 'phone', 'cellulare', 'fax', 'email', 'sito_web', 'payment_type_id', 'payment_type_label', 'iban', 'banca', 'supplier_payment_type_id', 'supplier_payment_type_label', 'supplier_iban', 'supplier_banca', 'notes'].forEach(k => {
                if (payload[k] === '') payload[k] = null;
            });

            if (editingSupplier) {
                await apiRequest(`/clients/${editingSupplier.client_id}`, { method: 'PUT', body: payload });
                toast.success('Fornitore aggiornato');
            } else {
                await apiRequest('/clients/', { method: 'POST', body: payload });
                toast.success('Fornitore creato');
            }
            setDialogOpen(false);
            fetchSuppliers();
        } catch (e) {
            console.error('[FornitoriPage] Save error:', e, 'Message:', e?.message);
            const msg = e?.message || 'Errore salvataggio';
            toast.error(msg, { duration: 6000 });
        }
        finally { setSaving(false); }
    };

    const handleDelete = async () => {
        if (!supplierToDelete) return;
        try {
            await apiRequest(`/clients/${supplierToDelete.client_id}`, { method: 'DELETE' });
            toast.success('Fornitore eliminato');
            setDeleteDialogOpen(false);
            fetchSuppliers();
        } catch (e) { toast.error(e.message); }
    };

    const openContactDialog = (idx) => {
        if (idx !== null && idx !== undefined) {
            setEditingContactIdx(idx);
            setContactForm({ ...emptyContact, ...formData.contacts[idx] });
        } else {
            setEditingContactIdx(null);
            setContactForm(emptyContact);
        }
        setContactDialogOpen(true);
    };

    const saveContact = () => {
        if (!contactForm.nome && !contactForm.email) { toast.error('Nome o Email obbligatorio'); return; }
        const newContacts = [...(formData.contacts || [])];
        if (editingContactIdx !== null) {
            newContacts[editingContactIdx] = contactForm;
        } else {
            newContacts.push(contactForm);
        }
        updateField('contacts', newContacts);
        setContactDialogOpen(false);
    };

    const removeContact = (idx) => {
        updateField('contacts', formData.contacts.filter((_, i) => i !== idx));
    };

    const handlePaymentTypeChange = (ptId, isSupplier = false) => {
        const pt = paymentTypes.find(p => p.payment_type_id === ptId);
        const prefix = isSupplier ? 'supplier_' : '';
        setFormData(f => ({
            ...f,
            [`${prefix}payment_type_id`]: ptId === '__none__' ? '' : ptId,
            [`${prefix}payment_type_label`]: pt ? `${pt.codice} - ${pt.descrizione}` : '',
        }));
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="fornitori-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h1 className="font-sans text-xl sm:text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Factory className="h-5 w-5 sm:h-6 sm:w-6 text-[#0055FF]" /> Fornitori
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Anagrafica fornitori con contatti e condizioni pagamento</p>
                    </div>
                    <Button data-testid="btn-new-supplier" onClick={() => handleOpenDialog(null)} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white w-full sm:w-auto">
                        <Plus className="h-4 w-4 mr-2" /> Nuovo Fornitore
                    </Button>
                </div>

                {/* Search */}
                <Card className="border-gray-200">
                    <CardContent className="p-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                            <Input data-testid="search-suppliers" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Cerca per ragione sociale, P.IVA o C.F." className="pl-10" />
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-medium">Ragione Sociale</TableHead>
                                    <TableHead className="text-white font-medium hidden sm:table-cell">Tipo</TableHead>
                                    <TableHead className="text-white font-medium hidden md:table-cell">P. IVA</TableHead>
                                    <TableHead className="text-white font-medium hidden md:table-cell">Citta</TableHead>
                                    <TableHead className="text-white font-medium hidden lg:table-cell">Telefono</TableHead>
                                    <TableHead className="text-white font-medium hidden lg:table-cell">Pagamento</TableHead>
                                    <TableHead className="w-[100px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow><TableCell colSpan={7} className="text-center py-8"><div className="w-6 h-6 loading-spinner mx-auto" /></TableCell></TableRow>
                                ) : suppliers.length === 0 ? (
                                    <TableRow><TableCell colSpan={7} className="p-0">
                                        <EmptyState type="distinte" title="Nessun fornitore registrato" description="Aggiungi il tuo primo fornitore per gestire acquisti e lavorazioni esterne." actionLabel="Aggiungi Fornitore" onAction={() => handleOpenDialog(null)} />
                                    </TableCell></TableRow>
                                ) : (
                                    suppliers.map((s) => {
                                        const tb = TYPE_BADGES[s.client_type] || TYPE_BADGES.fornitore;
                                        return (
                                            <TableRow key={s.client_id} data-testid={`supplier-row-${s.client_id}`} className="hover:bg-slate-50 cursor-pointer" onClick={() => handleOpenDialog(s)}>
                                                <TableCell className="font-medium">{s.business_name}</TableCell>
                                                <TableCell className="hidden sm:table-cell"><Badge className={`${tb.color} text-[10px]`}>{tb.label}</Badge></TableCell>
                                                <TableCell className="font-mono text-sm hidden md:table-cell">{s.partita_iva || '-'}</TableCell>
                                                <TableCell className="text-sm hidden md:table-cell">{s.city ? `${s.city} (${s.province})` : '-'}</TableCell>
                                                <TableCell className="text-sm hidden lg:table-cell">{s.phone || s.cellulare || '-'}</TableCell>
                                                <TableCell className="text-xs text-slate-500 max-w-[150px] truncate hidden lg:table-cell">{s.supplier_payment_type_label || s.payment_type_label || '-'}</TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                                        <Button variant="ghost" size="sm" onClick={() => navigate(`/fascicolo/${s.client_id}`)} title="Fascicolo" className="text-[#0055FF] hover:bg-blue-50">
                                                            <FolderOpen className="h-4 w-4" />
                                                        </Button>
                                                        <Button variant="ghost" size="sm" onClick={() => handleOpenDialog(s)} data-testid={`edit-supplier-${s.client_id}`}>
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        <Button variant="ghost" size="sm" onClick={() => { setSupplierToDelete(s); setDeleteDialogOpen(true); }} className="text-red-600 hover:text-red-700 hover:bg-red-50">
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
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Create/Edit Dialog — Tab-based Form */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="sm:max-w-[750px] max-w-[95vw] max-h-[90vh] flex flex-col" data-testid="supplier-dialog">
                    <DialogHeader>
                        <DialogTitle className="font-sans text-xl text-[#1E293B]">
                            {editingSupplier ? 'Modifica Fornitore' : 'Nuovo Fornitore'}
                        </DialogTitle>
                        <DialogDescription>Compila i dati anagrafici, contatti e condizioni di pagamento.</DialogDescription>
                    </DialogHeader>

                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-slate-200 -mx-6 px-6">
                        {TABS.map(t => (
                            <button
                                key={t.key}
                                data-testid={`tab-${t.key}`}
                                onClick={() => setActiveTab(t.key)}
                                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                                    activeTab === t.key
                                        ? 'border-[#0055FF] text-[#0055FF]'
                                        : 'border-transparent text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                {t.label}
                            </button>
                        ))}
                    </div>

                    {/* Tab Content */}
                    <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-[300px]">
                        {/* TAB: Anagrafica */}
                        {activeTab === 'anagrafica' && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="sm:col-span-2">
                                        <Label>Ragione Sociale *</Label>
                                        <Input data-testid="input-business-name" value={formData.business_name} onChange={e => updateField('business_name', e.target.value)} placeholder="Nome azienda fornitrice" />
                                    </div>
                                    <div>
                                        <Label>Tipo</Label>
                                        <Select value={formData.client_type} onValueChange={v => updateField('client_type', v)}>
                                            <SelectTrigger data-testid="select-supplier-type"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="fornitore">Fornitore</SelectItem>
                                                <SelectItem value="cliente_fornitore">Cliente/Fornitore</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 py-1">
                                    <Checkbox checked={formData.persona_fisica} onCheckedChange={v => updateField('persona_fisica', v)} />
                                    <Label className="text-sm cursor-pointer">Persona Fisica</Label>
                                </div>

                                {formData.persona_fisica && (
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                        <div><Label>Titolo</Label><Input value={formData.titolo} onChange={e => updateField('titolo', e.target.value)} placeholder="Sig." /></div>
                                        <div><Label>Cognome</Label><Input value={formData.cognome} onChange={e => updateField('cognome', e.target.value)} /></div>
                                        <div className="col-span-2"><Label>Nome</Label><Input value={formData.nome} onChange={e => updateField('nome', e.target.value)} /></div>
                                    </div>
                                )}

                                <Separator />
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div><Label>Partita IVA</Label><Input data-testid="input-piva" value={formData.partita_iva} onChange={e => updateField('partita_iva', e.target.value)} placeholder="IT12345678901" /></div>
                                    <div><Label>Codice Fiscale</Label><Input data-testid="input-cf" value={formData.codice_fiscale} onChange={e => updateField('codice_fiscale', e.target.value.toUpperCase())} placeholder="RSSMRA80A01H501U" /></div>
                                    <div><Label>Codice SDI</Label><Input value={formData.codice_sdi} onChange={e => updateField('codice_sdi', e.target.value.toUpperCase())} placeholder="0000000" maxLength={7} /></div>
                                    <div><Label>PEC</Label><Input type="email" value={formData.pec} onChange={e => updateField('pec', e.target.value)} placeholder="fornitore@pec.it" /></div>
                                </div>
                            </div>
                        )}

                        {/* TAB: Indirizzo */}
                        {activeTab === 'indirizzo' && (
                            <div className="space-y-4">
                                <div><Label>Via / Piazza / Localita</Label><Input data-testid="input-address" value={formData.address} onChange={e => updateField('address', e.target.value)} placeholder="Via Roma 1" /></div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <div><Label>CAP</Label><Input value={formData.cap} onChange={e => updateField('cap', e.target.value)} placeholder="00100" maxLength={5} /></div>
                                    <div className="col-span-2"><Label>Comune</Label><Input value={formData.city} onChange={e => updateField('city', e.target.value)} placeholder="Roma" /></div>
                                    <div><Label>Prov.</Label><Input value={formData.province} onChange={e => updateField('province', e.target.value.toUpperCase())} placeholder="RM" maxLength={2} /></div>
                                </div>
                                <div className="w-48"><Label>Paese</Label><Input value={formData.country} onChange={e => updateField('country', e.target.value.toUpperCase())} placeholder="IT" maxLength={2} /></div>
                            </div>
                        )}

                        {/* TAB: Contatti */}
                        {activeTab === 'contatti' && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div><Label><Phone className="inline h-3.5 w-3.5 mr-1" />Telefono</Label><Input data-testid="input-phone" value={formData.phone} onChange={e => updateField('phone', e.target.value)} placeholder="+39 06 1234567" /></div>
                                    <div><Label><Phone className="inline h-3.5 w-3.5 mr-1" />Cellulare</Label><Input value={formData.cellulare} onChange={e => updateField('cellulare', e.target.value)} placeholder="+39 333 1234567" /></div>
                                    <div><Label>Fax</Label><Input value={formData.fax} onChange={e => updateField('fax', e.target.value)} /></div>
                                    <div><Label><Mail className="inline h-3.5 w-3.5 mr-1" />Email</Label><Input data-testid="input-email" type="email" value={formData.email} onChange={e => updateField('email', e.target.value)} placeholder="info@fornitore.it" /></div>
                                    <div className="col-span-1 sm:col-span-2"><Label><Globe className="inline h-3.5 w-3.5 mr-1" />Sito Web</Label><Input value={formData.sito_web} onChange={e => updateField('sito_web', e.target.value)} placeholder="https://www.fornitore.it" /></div>
                                </div>

                                <Separator />

                                {/* Persone di Riferimento */}
                                <div className="flex items-center justify-between">
                                    <Label className="text-sm font-semibold text-[#1E293B]">Persone di Riferimento</Label>
                                    <Button data-testid="btn-add-contact" variant="outline" size="sm" onClick={() => openContactDialog(null)} className="h-8 text-xs">
                                        <UserPlus className="h-3.5 w-3.5 mr-1" /> Aggiungi Contatto
                                    </Button>
                                </div>

                                {(formData.contacts || []).length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">Nessun contatto aggiuntivo</p>
                                ) : (
                                    <div className="border rounded-lg overflow-hidden">
                                        <Table>
                                            <TableHeader>
                                                <TableRow className="bg-slate-100">
                                                    <TableHead className="text-xs">Tipo</TableHead>
                                                    <TableHead className="text-xs">Nome</TableHead>
                                                    <TableHead className="text-xs">Telefono</TableHead>
                                                    <TableHead className="text-xs">Email</TableHead>
                                                    <TableHead className="text-xs text-center">Doc.</TableHead>
                                                    <TableHead className="w-[60px]"></TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {formData.contacts.map((c, idx) => (
                                                    <TableRow key={idx} className="hover:bg-slate-50">
                                                        <TableCell className="text-xs"><Badge variant="outline" className="text-[10px]">{c.tipo}</Badge></TableCell>
                                                        <TableCell className="text-sm font-medium">{c.nome}</TableCell>
                                                        <TableCell className="text-xs font-mono">{c.telefono}</TableCell>
                                                        <TableCell className="text-xs">{c.email}</TableCell>
                                                        <TableCell className="text-center">
                                                            <div className="flex gap-0.5 justify-center">
                                                                {c.include_preventivi && <span className="w-2 h-2 rounded-full bg-blue-400" title="Preventivi" />}
                                                                {c.include_fatture && <span className="w-2 h-2 rounded-full bg-emerald-400" title="Fatture" />}
                                                                {c.include_ddt && <span className="w-2 h-2 rounded-full bg-amber-400" title="DDT" />}
                                                            </div>
                                                        </TableCell>
                                                        <TableCell>
                                                            <div className="flex gap-0.5">
                                                                <Button variant="ghost" size="sm" onClick={() => openContactDialog(idx)} className="h-7 w-7 p-0"><Pencil className="h-3 w-3" /></Button>
                                                                <Button variant="ghost" size="sm" onClick={() => removeContact(idx)} className="h-7 w-7 p-0 text-red-500"><X className="h-3 w-3" /></Button>
                                                            </div>
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* TAB: Pagamento */}
                        {activeTab === 'pagamento' && (
                            <div className="space-y-5">
                                {/* Condizioni Pagamento FORNITORE */}
                                <div className="space-y-3">
                                    <h4 className="text-xs font-bold text-amber-700 uppercase tracking-wider flex items-center gap-1.5">
                                        <Factory className="h-3.5 w-3.5" /> Condizioni Pagamento Fornitore
                                    </h4>
                                    <div>
                                        <Label className="flex items-center gap-1"><CreditCard className="h-3.5 w-3.5" /> Tipo Pagamento</Label>
                                        <Select value={formData.supplier_payment_type_id || '__none__'} onValueChange={v => handlePaymentTypeChange(v, true)}>
                                            <SelectTrigger data-testid="select-supplier-payment-type"><SelectValue placeholder="Seleziona tipo pagamento..." /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                                {paymentTypes.map(pt => (
                                                    <SelectItem key={pt.payment_type_id} value={pt.payment_type_id}>
                                                        <span className="font-mono text-xs mr-2">{pt.codice}</span> {pt.descrizione}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div><Label>Banca Fornitore</Label><Input value={formData.supplier_banca || ''} onChange={e => updateField('supplier_banca', e.target.value)} placeholder="Nome banca" /></div>
                                        <div><Label>IBAN Fornitore</Label><Input data-testid="input-supplier-iban" value={formData.supplier_iban || ''} onChange={e => updateField('supplier_iban', e.target.value.toUpperCase())} placeholder="IT60X0542811101000000123456" className="font-mono text-sm" /></div>
                                    </div>
                                </div>

                                {/* Condizioni Pagamento CLIENTE — solo se cliente_fornitore */}
                                {formData.client_type === 'cliente_fornitore' && (
                                    <>
                                        <Separator />
                                        <div className="space-y-3">
                                            <h4 className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                                                <CreditCard className="h-3.5 w-3.5" /> Condizioni Pagamento Cliente
                                            </h4>
                                            <div>
                                                <Label>Tipo Pagamento Cliente</Label>
                                                <Select value={formData.payment_type_id || '__none__'} onValueChange={v => handlePaymentTypeChange(v, false)}>
                                                    <SelectTrigger data-testid="select-client-payment-type"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                                        {paymentTypes.map(pt => (
                                                            <SelectItem key={pt.payment_type_id} value={pt.payment_type_id}>
                                                                <span className="font-mono text-xs mr-2">{pt.codice}</span> {pt.descrizione}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div className="grid grid-cols-2 gap-3">
                                                <div><Label>Banca Cliente</Label><Input value={formData.banca || ''} onChange={e => updateField('banca', e.target.value)} placeholder="Nome banca" /></div>
                                                <div><Label>IBAN Cliente</Label><Input value={formData.iban || ''} onChange={e => updateField('iban', e.target.value.toUpperCase())} placeholder="IT60X0542811101000000123456" className="font-mono text-sm" /></div>
                                            </div>
                                        </div>
                                    </>
                                )}

                                {paymentTypes.length === 0 && (
                                    <p className="text-xs text-amber-500 mt-1">Nessun tipo pagamento configurato. <button onClick={() => navigate('/impostazioni/pagamenti')} className="underline text-[#0055FF]">Crea tipi pagamento</button></p>
                                )}
                            </div>
                        )}

                        {/* TAB: Note */}
                        {activeTab === 'note' && (
                            <div>
                                <Label>Note Generali</Label>
                                <Textarea data-testid="input-notes" value={formData.notes} onChange={e => updateField('notes', e.target.value)} placeholder="Note sul fornitore..." rows={8} />
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button data-testid="btn-save-supplier" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Contact Person Dialog */}
            <Dialog open={contactDialogOpen} onOpenChange={setContactDialogOpen}>
                <DialogContent className="sm:max-w-[500px]" data-testid="contact-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-[#1E293B]">
                            {editingContactIdx !== null ? 'Modifica Contatto' : 'Nuovo Contatto'}
                        </DialogTitle>
                        <DialogDescription>Dettaglio persona di riferimento e preferenze invio documenti.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Tipo</Label>
                                <Select value={contactForm.tipo} onValueChange={v => setContactForm(f => ({ ...f, tipo: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {CONTACT_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div><Label>Nome</Label><Input value={contactForm.nome} onChange={e => setContactForm(f => ({ ...f, nome: e.target.value }))} /></div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Telefono</Label><Input value={contactForm.telefono} onChange={e => setContactForm(f => ({ ...f, telefono: e.target.value }))} /></div>
                            <div><Label>Email</Label><Input type="email" value={contactForm.email} onChange={e => setContactForm(f => ({ ...f, email: e.target.value }))} /></div>
                        </div>

                        <Separator />
                        <Label className="text-sm font-semibold">Includi nell'invio email per:</Label>
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { key: 'include_preventivi', label: 'Preventivi' },
                                { key: 'include_fatture', label: 'Fatture' },
                                { key: 'include_solleciti', label: 'Solleciti Pagamento' },
                                { key: 'include_ordini', label: 'Ordini' },
                                { key: 'include_ddt', label: 'DDT' },
                            ].map(f => (
                                <label key={f.key} className="flex items-center gap-2 cursor-pointer text-sm">
                                    <Checkbox checked={contactForm[f.key]} onCheckedChange={v => setContactForm(prev => ({ ...prev, [f.key]: v }))} />
                                    <span className="text-slate-700">{f.label}</span>
                                </label>
                            ))}
                        </div>

                        <div><Label>Note</Label><Input value={contactForm.note} onChange={e => setContactForm(f => ({ ...f, note: e.target.value }))} /></div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setContactDialogOpen(false)}>Annulla</Button>
                        <Button onClick={saveContact} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">Conferma</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="font-sans">Elimina Fornitore</DialogTitle>
                        <DialogDescription>Sei sicuro di voler eliminare <strong>{supplierToDelete?.business_name}</strong>? Questa azione non puo essere annullata.</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Annulla</Button>
                        <Button data-testid="btn-confirm-delete" variant="destructive" onClick={handleDelete}>Elimina</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
