import { useState, useEffect } from 'react';
import { apiRequest } from '../../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Bell, Save, Loader2 } from 'lucide-react';

export default function NotificheTab() {
    const [prefs, setPrefs] = useState({
        email_alerts_enabled: true,
        alert_email: '',
        preavviso_giorni: 7,
        alert_scadenze_pagamento: true,
        alert_qualita: true,
    });
    const [userEmail, setUserEmail] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const data = await apiRequest('/notifications/preferences');
                setPrefs({
                    email_alerts_enabled: data.email_alerts_enabled ?? true,
                    alert_email: data.alert_email || '',
                    preavviso_giorni: data.preavviso_giorni ?? 7,
                    alert_scadenze_pagamento: data.alert_scadenze_pagamento ?? true,
                    alert_qualita: data.alert_qualita ?? true,
                });
                setUserEmail(data.user_email || '');
            } catch { /* ignore */ }
            setLoading(false);
        })();
    }, []);

    const save = async () => {
        setSaving(true);
        try {
            await apiRequest('/notifications/preferences', {
                method: 'PUT',
                body: JSON.stringify(prefs),
            });
            toast.success('Preferenze notifiche salvate');
        } catch { toast.error('Errore nel salvataggio'); }
        setSaving(false);
    };

    if (loading) return <Card><CardContent className="py-8 text-center text-slate-400">Caricamento...</CardContent></Card>;

    return (
        <Card className="border-gray-200">
            <CardHeader className="bg-amber-50 border-b border-gray-200">
                <CardTitle className="flex items-center gap-2"><Bell className="h-5 w-5" /> Preferenze Notifiche Email</CardTitle>
                <CardDescription>Configura quando e come ricevere gli alert via email</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
                {/* Master toggle */}
                <div className="flex items-center justify-between bg-slate-50 rounded-lg p-4" data-testid="notif-master-toggle">
                    <div>
                        <p className="font-medium text-sm text-slate-800">Abilita notifiche email</p>
                        <p className="text-xs text-slate-500">Ricevi gli alert automatici via email</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            checked={prefs.email_alerts_enabled}
                            onChange={(e) => setPrefs(p => ({...p, email_alerts_enabled: e.target.checked}))}
                            className="sr-only peer"
                            data-testid="notif-enabled-checkbox"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                </div>

                {prefs.email_alerts_enabled && (
                    <div className="space-y-4">
                        {/* Email address */}
                        <div>
                            <Label htmlFor="alert_email">Email per le notifiche</Label>
                            <Input
                                id="alert_email"
                                type="email"
                                value={prefs.alert_email}
                                onChange={(e) => setPrefs(p => ({...p, alert_email: e.target.value}))}
                                placeholder={userEmail || 'usa email account'}
                                data-testid="notif-email-input"
                            />
                            <p className="text-xs text-slate-400 mt-1">Lascia vuoto per usare l'email del tuo account ({userEmail})</p>
                        </div>

                        {/* Pre-warning days */}
                        <div>
                            <Label htmlFor="preavviso_giorni">Giorni di preavviso scadenze</Label>
                            <Select
                                value={String(prefs.preavviso_giorni)}
                                onValueChange={(v) => setPrefs(p => ({...p, preavviso_giorni: parseInt(v)}))}
                            >
                                <SelectTrigger data-testid="notif-preavviso-select">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="3">3 giorni</SelectItem>
                                    <SelectItem value="5">5 giorni</SelectItem>
                                    <SelectItem value="7">7 giorni (default)</SelectItem>
                                    <SelectItem value="14">14 giorni</SelectItem>
                                    <SelectItem value="30">30 giorni</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Alert types */}
                        <div className="space-y-3">
                            <Label>Tipi di alert attivi</Label>
                            <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3" data-testid="notif-scadenze-toggle">
                                <div>
                                    <p className="text-sm font-medium text-slate-700">Scadenze pagamento</p>
                                    <p className="text-xs text-slate-400">Fatture in scadenza, scadute, clienti in ritardo</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={prefs.alert_scadenze_pagamento}
                                        onChange={(e) => setPrefs(p => ({...p, alert_scadenze_pagamento: e.target.checked}))}
                                        className="sr-only peer"
                                        data-testid="notif-scadenze-checkbox"
                                    />
                                    <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>
                            <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3" data-testid="notif-qualita-toggle">
                                <div>
                                    <p className="text-sm font-medium text-slate-700">Scadenze qualita</p>
                                    <p className="text-xs text-slate-400">Qualifiche saldatori, tarature strumenti</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={prefs.alert_qualita}
                                        onChange={(e) => setPrefs(p => ({...p, alert_qualita: e.target.checked}))}
                                        className="sr-only peer"
                                        data-testid="notif-qualita-checkbox"
                                    />
                                    <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>
                        </div>
                    </div>
                )}

                <div className="flex justify-end pt-2">
                    <Button onClick={save} disabled={saving} data-testid="save-notif-prefs-btn">
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />}
                        Salva Preferenze
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
