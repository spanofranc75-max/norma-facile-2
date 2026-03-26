/**
 * QuickNewClientDialog - Dialog rapido per creare un cliente dal rilievo.
 * Campi minimi: nome/ragione sociale, telefono, indirizzo. 
 * I dati completi verranno inseriti quando il cliente accetta il preventivo.
 */
import { useState } from 'react';
import { apiRequest } from '../lib/utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Checkbox } from './ui/checkbox';
import { toast } from 'sonner';
import { UserPlus, Loader2, Building2, User } from 'lucide-react';

export default function QuickNewClientDialog({ open, onOpenChange, onCreated }) {
    const [saving, setSaving] = useState(false);
    const [isPersonaFisica, setIsPersonaFisica] = useState(false);
    const [form, setForm] = useState({
        business_name: '',
        cognome: '',
        nome: '',
        cellulare: '',
        email: '',
        address: '',
        city: '',
        province: '',
        notes: '',
    });

    const update = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

    const handleSave = async () => {
        const businessName = isPersonaFisica
            ? [form.cognome, form.nome].filter(Boolean).join(' ')
            : form.business_name;
        if (!businessName.trim()) {
            toast.error(isPersonaFisica ? 'Inserisci almeno il cognome' : 'Inserisci la ragione sociale');
            return;
        }
        setSaving(true);
        try {
            const payload = {
                business_name: businessName.trim(),
                client_type: 'cliente',
                persona_fisica: isPersonaFisica,
                cognome: isPersonaFisica ? form.cognome : null,
                nome: isPersonaFisica ? form.nome : null,
                cellulare: form.cellulare || null,
                email: form.email || null,
                address: form.address,
                city: form.city,
                province: form.province,
                notes: form.notes ? `[Dati parziali da rilievo] ${form.notes}` : '[Dati parziali da rilievo]',
                status: 'active',
            };
            const result = await apiRequest('/clients/', { method: 'POST', body: payload });
            toast.success(`Cliente "${businessName}" creato`);
            onCreated?.(result);
            onOpenChange(false);
            // Reset form
            setForm({ business_name: '', cognome: '', nome: '', cellulare: '', email: '', address: '', city: '', province: '', notes: '' });
            setIsPersonaFisica(false);
        } catch (err) {
            toast.error(err.message || 'Errore creazione cliente');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md" data-testid="quick-new-client-dialog">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-base">
                        <UserPlus className="h-4 w-4 text-blue-600" />
                        Nuovo Cliente Rapido
                    </DialogTitle>
                    <DialogDescription>
                        Inserisci i dati essenziali. Potrai completare l'anagrafica in seguito.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-3 py-2">
                    {/* Tipo persona */}
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="persona_fisica"
                            checked={isPersonaFisica}
                            onCheckedChange={setIsPersonaFisica}
                            data-testid="chk-persona-fisica"
                        />
                        <Label htmlFor="persona_fisica" className="text-sm cursor-pointer flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5" />Persona Fisica
                        </Label>
                    </div>

                    {isPersonaFisica ? (
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <Label className="text-xs">Cognome *</Label>
                                <Input value={form.cognome} onChange={e => update('cognome', e.target.value)}
                                    placeholder="Rossi" className="h-10 text-sm" data-testid="input-cognome" autoFocus />
                            </div>
                            <div>
                                <Label className="text-xs">Nome</Label>
                                <Input value={form.nome} onChange={e => update('nome', e.target.value)}
                                    placeholder="Mario" className="h-10 text-sm" data-testid="input-nome" />
                            </div>
                        </div>
                    ) : (
                        <div>
                            <Label className="text-xs flex items-center gap-1">
                                <Building2 className="h-3 w-3" />Ragione Sociale *
                            </Label>
                            <Input value={form.business_name} onChange={e => update('business_name', e.target.value)}
                                placeholder="Es: Carpenteria Rossi S.r.l." className="h-10 text-sm"
                                data-testid="input-business-name" autoFocus />
                        </div>
                    )}

                    <div>
                        <Label className="text-xs">Cellulare</Label>
                        <Input type="tel" value={form.cellulare} onChange={e => update('cellulare', e.target.value)}
                            placeholder="+39 333 1234567" className="h-10 text-sm" data-testid="input-cellulare" />
                    </div>

                    <div>
                        <Label className="text-xs">Email</Label>
                        <Input type="email" value={form.email} onChange={e => update('email', e.target.value)}
                            placeholder="info@azienda.it" className="h-10 text-sm" data-testid="input-email" />
                    </div>

                    <div>
                        <Label className="text-xs">Indirizzo</Label>
                        <Input value={form.address} onChange={e => update('address', e.target.value)}
                            placeholder="Via Roma, 1" className="h-10 text-sm" data-testid="input-address" />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <Label className="text-xs">Comune</Label>
                            <Input value={form.city} onChange={e => update('city', e.target.value)}
                                placeholder="Modena" className="h-10 text-sm" data-testid="input-city" />
                        </div>
                        <div>
                            <Label className="text-xs">Provincia</Label>
                            <Input value={form.province} onChange={e => update('province', e.target.value)}
                                placeholder="MO" maxLength={2} className="h-10 text-sm uppercase" data-testid="input-province" />
                        </div>
                    </div>

                    <div>
                        <Label className="text-xs">Note</Label>
                        <Input value={form.notes} onChange={e => update('notes', e.target.value)}
                            placeholder="Note rapide..." className="h-10 text-sm" data-testid="input-quick-notes" />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
                        Annulla
                    </Button>
                    <Button className="bg-[#0055FF] text-white" onClick={handleSave} disabled={saving}
                        data-testid="btn-save-quick-client">
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <UserPlus className="h-4 w-4 mr-1" />}
                        {saving ? 'Salvataggio...' : 'Crea Cliente'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
