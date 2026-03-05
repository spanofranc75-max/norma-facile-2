import { useState } from 'react';
import { apiRequest } from '../lib/utils';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Loader2, UserPlus } from 'lucide-react';

export function ClientQuickCreateModal({ open, onOpenChange, onCreated }) {
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({ business_name: '', address: '', phone: '', email: '' });

    const handleSave = async () => {
        if (!form.business_name.trim()) {
            toast.error('Il nome è obbligatorio');
            return;
        }
        setSaving(true);
        try {
            const payload = {
                business_name: form.business_name.trim(),
                client_type: 'cliente',
            };
            if (form.address.trim()) payload.address = form.address.trim();
            if (form.phone.trim()) payload.phone = form.phone.trim();
            if (form.email.trim()) payload.email = form.email.trim();

            const created = await apiRequest('/clients/', { method: 'POST', body: payload });
            toast.success(`Cliente "${created.business_name}" creato`);
            setForm({ business_name: '', address: '', phone: '', email: '' });
            onOpenChange(false);
            onCreated?.(created);
        } catch (err) {
            toast.error(err.message || 'Errore creazione cliente');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md" data-testid="client-quick-create-modal">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <UserPlus className="h-5 w-5 text-blue-600" />
                        Nuovo Cliente Rapido
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-3 py-2">
                    <div>
                        <Label>Nome Azienda / Privato <span className="text-red-500">*</span></Label>
                        <Input
                            data-testid="quick-client-name"
                            value={form.business_name}
                            onChange={e => setForm(p => ({ ...p, business_name: e.target.value }))}
                            placeholder="Es: Condominio Mimosa"
                            autoFocus
                        />
                    </div>
                    <div>
                        <Label>Indirizzo</Label>
                        <Input
                            data-testid="quick-client-address"
                            value={form.address}
                            onChange={e => setForm(p => ({ ...p, address: e.target.value }))}
                            placeholder="Via Roma 1, Bologna"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <Label>Telefono</Label>
                            <Input
                                data-testid="quick-client-phone"
                                value={form.phone}
                                onChange={e => setForm(p => ({ ...p, phone: e.target.value }))}
                                placeholder="+39 051..."
                            />
                        </div>
                        <div>
                            <Label>Email</Label>
                            <Input
                                data-testid="quick-client-email"
                                value={form.email}
                                onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                                placeholder="info@..."
                            />
                        </div>
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
                        Annulla
                    </Button>
                    <Button
                        data-testid="quick-client-save"
                        onClick={handleSave}
                        disabled={saving || !form.business_name.trim()}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserPlus className="h-4 w-4 mr-2" />}
                        Crea Cliente
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
