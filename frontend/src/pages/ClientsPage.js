/**
 * Clients List Page — Scheda Cliente/Fornitore Avanzata
 * Tab-based form: Anagrafica, Indirizzo, Contatti, Pagamento, Note
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
    Plus, Search, Pencil, Trash2, Building2, User, Users2, Ruler,
    FolderOpen, Phone, Mail, Globe, CreditCard, UserPlus, X, Clock,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const CLIENT_TYPES = {
    cliente: { label: 'Cliente', color: 'bg-blue-100 text-blue-800' },
    fornitore: { label: 'Fornitore', color: 'bg-amber-100 text-amber-800' },
    cliente_fornitore: { label: 'Cli/For', color: 'bg-emerald-100 text-emerald-800' },
};

const TABS = [
    { key: 'anagrafica', label: 'Anagrafica' },
    { key: 'indirizzo', label: 'Indirizzo' },
    { key: 'contatti', label: 'Contatti' },
    { key: 'pagamento', label: 'Pagamento' },
    { key: 'note', label: 'Note' },
    { key: 'email_log', label: 'Email Inviate' },
];

const CONTACT_TYPES = ['Titolare', 'Commerciale', 'Amministrativo', 'Tecnico', 'Logistica', 'Altro'];

const emptyClient = {
    business_name: '', client_type: 'cliente', persona_fisica: false,
    titolo: '', cognome: '', nome: '',
    codice_fiscale: '', partita_iva: '', codice_sdi: '0000000', pec: '',
    address: '', cap: '', city: '', province: '', country: 'IT',
    phone: '', cellulare: '', fax: '', email: '', sito_web: '',
    contacts: [],
    payment_type_id: '', payment_type_label: '', iban: '', banca: '',
    notes: '',
};

const emptyContact = {
    tipo: 'Commerciale', nome: '', telefono: '', email: '',
    include_preventivi: false, include_fatture: false, include_solleciti: false,
    include_ordini: false, include_ddt: false, note: '',
};

export default function ClientsPage() {
    const navigate = useNavigate();
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingClient, setEditingClient] = useState(null);
    const [formData, setFormData] = useState(emptyClient);
    const [saving, setSaving] = useState(false);
    const [emailLog, setEmailLog] = useState([]);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [clientToDelete, setClientToDelete] = useState(null);
    const [activeTab, setActiveTab] = useState('anagrafica');
    const [paymentTypes, setPaymentTypes] = useState([]);
    const [contactDialogOpen, setContactDialogOpen] = useState(false);
    const [editingContactIdx, setEditingContactIdx] = useState(null);
    const [contactForm, setContactForm] = useState(emptyContact);

    const fetchClients = useCallback(async () => {
        try {
            const data = await apiRequest(`/clients/?search=${searchQuery}&limit=100`);
            setClients(data.clients || []);
        } catch (e) { toast.error('Errore caricamento clienti'); }
        finally { setLoading(false); }
    }, [searchQuery]);

    const fetchPaymentTypes = useCallback(async () => {
        try {
            const data = await apiRequest('/payment-types/');
            setPaymentTypes(data.items || []);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => { fetchClients(); }, [fetchClients]);
    useEffect(() => { fetchPaymentTypes(); }, [fetchPaymentTypes]);

    const updateField = (key, val) => setFormData(f => ({ ...f, [key]: val }));

    const handleOpenDialog = (client) => {
        if (client) {
            setEditingClient(client);
            setFormData({ ...emptyClient, ...client });
        } else {
            setEditingClient(null);
            setFormData(emptyClient);
        }
        setActiveTab('anagrafica');
        setDialogOpen(true);
    };

    const handleSave = async (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        if (!formData.business_name) { toast.error('Ragione Sociale obbligatoria'); return; }
        setSaving(true);
        try {
            // Clean empty strings to null for Optional fields
            const payload = { ...formData };
            ['codice_fiscale', 'partita_iva', 'pec', 'phone', 'cellulare', 'fax', 'email', 'sito_web', 'payment_type_id', 'payment_type_label', 'iban', 'banca', 'notes'].forEach(k => {
                if (payload[k] === '') payload[k] = null;
            });

            if (editingClient) {
                await apiRequest(`/clients/${editingClient.client_id}`, { method: 'PUT', body: payload });
                toast.success('Cliente aggiornato');
            } else {
                const result = await apiRequest('/clients/', { method: 'POST', body: payload });
                console.log('[ClientsPage] Client created:', result?.client_id);
                toast.success('Cliente creato con successo');
            }
            setDialogOpen(false);
            fetchClients();
        } catch (err) {
            console.error('[ClientsPage] Save failed:', err);
            toast.error(err.message || 'Errore durante il salvataggio');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!clientToDelete) return;
        try {
            await apiRequest(`/clients/${clientToDelete.client_id}`, { method: 'DELETE' });
            toast.success('Cliente eliminato');
            setDeleteDialogOpen(false);
            fetchClients();
        } catch (e) { toast.error(e.message); }
    };

    // Contact management
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
        const newContacts = formData.contacts.filter((_, i) => i !== idx);
        updateField('contacts', newContacts);
    };

    const handlePaymentTypeChange = (ptId) => {
        const pt = paymentTypes.find(p => p.payment_type_id === ptId);
        setFormData(f => ({
            ...f,
            payment_type_id: ptId,
            payment_type_label: pt ? `${pt.codice} - ${pt.descrizione}` : '',
        }));
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="clients-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Users2 className="h-6 w-6 text-[#0055FF]" /> Clienti
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Anagrafica clienti con contatti e condizioni pagamento</p>
                    </div>
                    <Button data-testid="btn-new-client" onClick={() => handleOpenDialog(null)} className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white">
                        <Plus className="h-4 w-4 mr-2" /> Nuovo
                    </Button>
                </div>

                {/* Search */}
                <Card className="border-gray-200">
                    <CardContent className="p-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                            <Input data-testid="search-clients" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Cerca per ragione sociale, P.IVA o C.F." className="pl-10" />
                        </div>
                    </CardContent>
                </Card>

                {/* Table */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-medium">Ragione Sociale</TableHead>
                                    <TableHead className="text-white font-medium">Tipo</TableHead>
                                    <TableHead className="text-white font-medium">P. IVA</TableHead>
                                    <TableHead className="text-white font-medium">Città</TableHead>
                                    <TableHead className="text-white font-medium">Telefono</TableHead>
                                    <TableHead className="text-white font-medium">Pagamento</TableHead>
                                    <TableHead className="w-[120px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow><TableCell colSpan={7} className="text-center py-8"><div className="w-6 h-6 loading-spinner mx-auto" /></TableCell></TableRow>
                                ) : clients.length === 0 ? (
                                    <TableRow><TableCell colSpan={7} className="p-0">
                                        <EmptyState type="clients" title="Nessun cliente registrato" description="Aggiungi il tuo primo cliente per iniziare a creare rilievi, preventivi e fatture." actionLabel="Crea il primo Cliente" onAction={() => handleOpenDialog(null)} />
                                    </TableCell></TableRow>
                                ) : (
                                    clients.map((client) => {
                                        const ct = CLIENT_TYPES[client.client_type] || CLIENT_TYPES.cliente;
                                        return (
                                            <TableRow key={client.client_id} data-testid={`client-row-${client.client_id}`} className="hover:bg-slate-50 cursor-pointer" onClick={() => handleOpenDialog(client)}>
                                                <TableCell className="font-medium">{client.business_name}</TableCell>
                                                <TableCell><Badge className={`${ct.color} text-[10px]`}>{ct.label}</Badge></TableCell>
                                                <TableCell className="font-mono text-sm">{client.partita_iva || '-'}</TableCell>
                                                <TableCell className="text-sm">{client.city ? `${client.city} (${client.province})` : '-'}</TableCell>
                                                <TableCell className="text-sm">{client.phone || client.cellulare || '-'}</TableCell>
                                                <TableCell className="text-xs text-slate-500 max-w-[150px] truncate">{client.payment_type_label || '-'}</TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                                        <Button variant="ghost" size="sm" data-testid={`fascicolo-client-${client.client_id}`} onClick={() => navigate(`/fascicolo/${client.client_id}`)} title="Fascicolo" className="text-[#0055FF] hover:bg-blue-50">
                                                            <FolderOpen className="h-4 w-4" />
                                                        </Button>
                                                        <Button variant="ghost" size="sm" data-testid={`rilievo-client-${client.client_id}`} onClick={() => navigate(`/rilievi/new?client_id=${client.client_id}`)} title="Nuovo Rilievo">
                                                            <Ruler className="h-4 w-4" />
                                                        </Button>
                                                        <Button variant="ghost" size="sm" onClick={() => handleOpenDialog(client)} data-testid={`edit-client-${client.client_id}`}>
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        <Button variant="ghost" size="sm" onClick={() => { setClientToDelete(client); setDeleteDialogOpen(true); }} className="text-red-600 hover:text-red-700 hover:bg-red-50">
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

            {/* ── Create/Edit Dialog ── Tab-based Form ── */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="sm:max-w-[750px] max-h-[90vh] flex flex-col" data-testid="client-dialog">
                    <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); handleSave(e); }} className="flex flex-col flex-1 overflow-hidden">
                    <DialogHeader>
                        <DialogTitle className="font-sans text-xl text-[#1E293B]">
                            {editingClient ? 'Modifica Scheda' : 'Nuova Scheda Cliente/Fornitore'}
                        </DialogTitle>
                        <DialogDescription>Compila i dati anagrafici, contatti e condizioni di pagamento.</DialogDescription>
                    </DialogHeader>

                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-slate-200 -mx-6 px-6 overflow-x-auto">
                        {TABS.map(t => (
                            <button
                                key={t.key}
                                type="button"
                                data-testid={`tab-${t.key}`}
                                onClick={() => {
                                    setActiveTab(t.key);
                                    if (t.key === 'email_log' && editingClient) {
                                        apiRequest(`/clients/${editingClient.client_id}/email-log`)
                                            .then(data => setEmailLog(data.emails || []))
                                            .catch(() => setEmailLog([]));
                                    }
                                }}
                                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
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
                        {/* ── TAB: Anagrafica ── */}
                        {activeTab === 'anagrafica' && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="col-span-2">
                                        <Label>Ragione Sociale *</Label>
                                        <Input data-testid="input-business-name" value={formData.business_name} onChange={e => updateField('business_name', e.target.value)} placeholder="Nome azienda" />
                                    </div>
                                    <div>
                                        <Label>Tipo</Label>
                                        <Select value={formData.client_type} onValueChange={v => updateField('client_type', v)}>
                                            <SelectTrigger data-testid="select-client-type"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="cliente">Cliente</SelectItem>
                                                <SelectItem value="fornitore">Fornitore</SelectItem>
                                                <SelectItem value="cliente_fornitore">Cliente/Fornitore</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 py-1">
                                    <Checkbox data-testid="cb-persona-fisica" checked={formData.persona_fisica} onCheckedChange={v => updateField('persona_fisica', v)} />
                                    <Label className="text-sm cursor-pointer">Persona Fisica</Label>
                                </div>

                                {formData.persona_fisica && (
                                    <div className="grid grid-cols-4 gap-3">
                                        <div><Label>Titolo</Label><Input value={formData.titolo} onChange={e => updateField('titolo', e.target.value)} placeholder="Sig." /></div>
                                        <div><Label>Cognome</Label><Input value={formData.cognome} onChange={e => updateField('cognome', e.target.value)} /></div>
                                        <div className="col-span-2"><Label>Nome</Label><Input value={formData.nome} onChange={e => updateField('nome', e.target.value)} /></div>
                                    </div>
                                )}

                                <Separator />
                                <div className="grid grid-cols-2 gap-3">
                                    <div><Label>Partita IVA</Label><Input data-testid="input-piva" value={formData.partita_iva} onChange={e => updateField('partita_iva', e.target.value)} placeholder="IT12345678901" /></div>
                                    <div><Label>Codice Fiscale</Label><Input data-testid="input-cf" value={formData.codice_fiscale} onChange={e => updateField('codice_fiscale', e.target.value.toUpperCase())} placeholder="RSSMRA80A01H501U" /></div>
                                    <div><Label>Codice SDI</Label><Input data-testid="input-sdi" value={formData.codice_sdi} onChange={e => updateField('codice_sdi', e.target.value.toUpperCase())} placeholder="0000000" maxLength={7} /></div>
                                    <div><Label>PEC</Label><Input data-testid="input-pec" type="email" value={formData.pec} onChange={e => updateField('pec', e.target.value)} placeholder="azienda@pec.it" /></div>
                                </div>
                            </div>
                        )}

                        {/* ── TAB: Indirizzo ── */}
                        {activeTab === 'indirizzo' && (
                            <div className="space-y-4">
                                <div><Label>Via / Piazza / Località</Label><Input data-testid="input-address" value={formData.address} onChange={e => updateField('address', e.target.value)} placeholder="Via Roma 1" /></div>
                                <div className="grid grid-cols-4 gap-3">
                                    <div><Label>CAP</Label><Input data-testid="input-cap" value={formData.cap} onChange={e => updateField('cap', e.target.value)} placeholder="00100" maxLength={5} /></div>
                                    <div className="col-span-2"><Label>Comune</Label><Input data-testid="input-city" value={formData.city} onChange={e => updateField('city', e.target.value)} placeholder="Roma" /></div>
                                    <div><Label>Prov.</Label><Input data-testid="input-province" value={formData.province} onChange={e => updateField('province', e.target.value.toUpperCase())} placeholder="RM" maxLength={2} /></div>
                                </div>
                                <div className="w-48"><Label>Paese</Label><Input value={formData.country} onChange={e => updateField('country', e.target.value.toUpperCase())} placeholder="IT" maxLength={2} /></div>
                            </div>
                        )}

                        {/* ── TAB: Contatti ── */}
                        {activeTab === 'contatti' && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-3">
                                    <div><Label><Phone className="inline h-3.5 w-3.5 mr-1" />Telefono</Label><Input data-testid="input-phone" value={formData.phone} onChange={e => updateField('phone', e.target.value)} placeholder="+39 06 1234567" /></div>
                                    <div><Label><Phone className="inline h-3.5 w-3.5 mr-1" />Cellulare</Label><Input value={formData.cellulare} onChange={e => updateField('cellulare', e.target.value)} placeholder="+39 333 1234567" /></div>
                                    <div><Label>Fax</Label><Input value={formData.fax} onChange={e => updateField('fax', e.target.value)} /></div>
                                    <div><Label><Mail className="inline h-3.5 w-3.5 mr-1" />Email</Label><Input data-testid="input-email" type="email" value={formData.email} onChange={e => updateField('email', e.target.value)} placeholder="info@azienda.it" /></div>
                                    <div className="col-span-2"><Label><Globe className="inline h-3.5 w-3.5 mr-1" />Sito Web</Label><Input value={formData.sito_web} onChange={e => updateField('sito_web', e.target.value)} placeholder="https://www.azienda.it" /></div>
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
                                                                {c.include_solleciti && <span className="w-2 h-2 rounded-full bg-red-400" title="Solleciti" />}
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

                        {/* ── TAB: Pagamento ── */}
                        {activeTab === 'pagamento' && (
                            <div className="space-y-4">
                                <div>
                                    <Label className="flex items-center gap-1"><CreditCard className="h-3.5 w-3.5" /> Condizioni Pagamento</Label>
                                    <Select value={formData.payment_type_id || '__none__'} onValueChange={(v) => handlePaymentTypeChange(v === '__none__' ? '' : v)}>
                                        <SelectTrigger data-testid="select-payment-type"><SelectValue placeholder="Seleziona tipo pagamento..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                            {paymentTypes.map(pt => (
                                                <SelectItem key={pt.payment_type_id} value={pt.payment_type_id}>
                                                    <span className="font-mono text-xs mr-2">{pt.codice}</span> {pt.descrizione}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {paymentTypes.length === 0 && (
                                        <p className="text-xs text-amber-500 mt-1">Nessun tipo pagamento configurato. <button onClick={() => navigate('/impostazioni/pagamenti')} className="underline text-[#0055FF]">Crea tipi pagamento</button></p>
                                    )}
                                </div>
                                <Separator />
                                <div className="grid grid-cols-2 gap-3">
                                    <div><Label>Banca</Label><Input value={formData.banca} onChange={e => updateField('banca', e.target.value)} placeholder="Nome banca" /></div>
                                    <div><Label>IBAN</Label><Input data-testid="input-iban" value={formData.iban} onChange={e => updateField('iban', e.target.value.toUpperCase())} placeholder="IT60X0542811101000000123456" className="font-mono text-sm" /></div>
                                </div>
                            </div>
                        )}

                        {/* ── TAB: Note ── */}
                        {activeTab === 'note' && (
                            <div>
                                <Label>Note Generali</Label>
                                <Textarea data-testid="input-notes" value={formData.notes} onChange={e => updateField('notes', e.target.value)} placeholder="Note aggiuntive..." rows={8} />
                            </div>
                        )}

                        {activeTab === 'email_log' && (
                            <div data-testid="email-log-tab">
                                {!editingClient ? (
                                    <p className="text-sm text-slate-400 text-center py-8">Salva il cliente prima per vedere lo storico email.</p>
                                ) : emailLog.length === 0 ? (
                                    <div className="text-center py-8">
                                        <Mail className="h-8 w-8 mx-auto text-slate-300 mb-2" />
                                        <p className="text-sm text-slate-400">Nessuna email inviata a questo cliente.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {emailLog.map((e, i) => (
                                            <div key={i} className="flex items-center gap-3 px-3 py-2.5 bg-slate-50 rounded-lg border border-slate-100" data-testid={`email-log-${i}`}>
                                                <Mail className="h-4 w-4 text-violet-500 shrink-0" />
                                                <div className="min-w-0 flex-1">
                                                    <p className="text-sm font-medium text-[#1E293B] truncate">{e.type} {e.number}</p>
                                                    <p className="text-xs text-slate-400">Inviato a: {e.to}</p>
                                                </div>
                                                <div className="text-right shrink-0">
                                                    <p className="text-xs text-slate-400 flex items-center gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {e.sent_at ? new Date(e.sent_at).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button type="submit" data-testid="btn-save-client" disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* ── Contact Person Dialog ── */}
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
                        <DialogTitle className="font-sans">Elimina Cliente</DialogTitle>
                        <DialogDescription>Sei sicuro di voler eliminare <strong>{clientToDelete?.business_name}</strong>? Questa azione non può essere annullata.</DialogDescription>
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
