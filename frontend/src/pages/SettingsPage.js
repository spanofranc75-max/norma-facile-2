/**
 * Settings Page - Company Settings
 */
import { useState, useEffect } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { Save, Building2, CreditCard, User } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

export default function SettingsPage() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState({
        business_name: '',
        legal_name: '',
        partita_iva: '',
        codice_fiscale: '',
        regime_fiscale: 'RF01',
        address: '',
        cap: '',
        city: '',
        province: '',
        country: 'IT',
        phone: '',
        email: '',
        pec: '',
        website: '',
        bank_details: {
            bank_name: '',
            iban: '',
            bic_swift: '',
        },
    });

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const data = await apiRequest('/company/settings');
                setSettings(prev => ({
                    ...prev,
                    ...data,
                    bank_details: data.bank_details || prev.bank_details,
                }));
            } catch (error) {
                console.error('Error loading settings:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchSettings();
    }, []);

    const updateField = (field, value) => {
        setSettings(prev => ({ ...prev, [field]: value }));
    };

    const updateBankField = (field, value) => {
        setSettings(prev => ({
            ...prev,
            bank_details: { ...prev.bank_details, [field]: value },
        }));
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await apiRequest('/company/settings', {
                method: 'PUT',
                body: JSON.stringify(settings),
            });
            toast.success('Impostazioni salvate');
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
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
            <div className="space-y-6 max-w-4xl">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-serif text-3xl font-bold text-slate-900">
                            Impostazioni
                        </h1>
                        <p className="text-slate-600">
                            Configura i dati aziendali per le fatture
                        </p>
                    </div>
                    <Button
                        data-testid="btn-save-settings"
                        onClick={handleSave}
                        disabled={saving}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Save className="h-4 w-4 mr-2" />
                        {saving ? 'Salvataggio...' : 'Salva'}
                    </Button>
                </div>

                <Tabs defaultValue="company" className="space-y-6">
                    <TabsList className="bg-slate-100">
                        <TabsTrigger value="company" className="gap-2">
                            <Building2 className="h-4 w-4" />
                            Azienda
                        </TabsTrigger>
                        <TabsTrigger value="bank" className="gap-2">
                            <CreditCard className="h-4 w-4" />
                            Banca
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="company">
                        <Card className="border-slate-200">
                            <CardHeader>
                                <CardTitle>Dati Aziendali</CardTitle>
                                <CardDescription>
                                    Questi dati appariranno nell'intestazione delle fatture
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="col-span-2">
                                        <Label htmlFor="business_name">Ragione Sociale *</Label>
                                        <Input
                                            id="business_name"
                                            data-testid="input-business-name"
                                            value={settings.business_name}
                                            onChange={(e) => updateField('business_name', e.target.value)}
                                            placeholder="Nome azienda"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="partita_iva">Partita IVA *</Label>
                                        <Input
                                            id="partita_iva"
                                            data-testid="input-piva"
                                            value={settings.partita_iva}
                                            onChange={(e) => updateField('partita_iva', e.target.value)}
                                            placeholder="IT12345678901"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="codice_fiscale">Codice Fiscale *</Label>
                                        <Input
                                            id="codice_fiscale"
                                            data-testid="input-cf"
                                            value={settings.codice_fiscale}
                                            onChange={(e) => updateField('codice_fiscale', e.target.value.toUpperCase())}
                                            placeholder="12345678901"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-4 gap-4">
                                    <div className="col-span-4">
                                        <Label htmlFor="address">Indirizzo</Label>
                                        <Input
                                            id="address"
                                            data-testid="input-address"
                                            value={settings.address}
                                            onChange={(e) => updateField('address', e.target.value)}
                                            placeholder="Via Roma 1"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="cap">CAP</Label>
                                        <Input
                                            id="cap"
                                            data-testid="input-cap"
                                            value={settings.cap}
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
                                            value={settings.city}
                                            onChange={(e) => updateField('city', e.target.value)}
                                            placeholder="Roma"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="province">Prov.</Label>
                                        <Input
                                            id="province"
                                            data-testid="input-province"
                                            value={settings.province}
                                            onChange={(e) => updateField('province', e.target.value.toUpperCase())}
                                            placeholder="RM"
                                            maxLength={2}
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <Label htmlFor="phone">Telefono</Label>
                                        <Input
                                            id="phone"
                                            data-testid="input-phone"
                                            value={settings.phone}
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
                                            value={settings.email}
                                            onChange={(e) => updateField('email', e.target.value)}
                                            placeholder="info@azienda.it"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="pec">PEC</Label>
                                        <Input
                                            id="pec"
                                            type="email"
                                            data-testid="input-pec"
                                            value={settings.pec}
                                            onChange={(e) => updateField('pec', e.target.value)}
                                            placeholder="azienda@pec.it"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="website">Sito Web</Label>
                                        <Input
                                            id="website"
                                            data-testid="input-website"
                                            value={settings.website}
                                            onChange={(e) => updateField('website', e.target.value)}
                                            placeholder="www.azienda.it"
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="bank">
                        <Card className="border-slate-200">
                            <CardHeader>
                                <CardTitle>Coordinate Bancarie</CardTitle>
                                <CardDescription>
                                    Questi dati appariranno in fondo alle fatture
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                    <Label htmlFor="bank_name">Nome Banca</Label>
                                    <Input
                                        id="bank_name"
                                        data-testid="input-bank-name"
                                        value={settings.bank_details.bank_name}
                                        onChange={(e) => updateBankField('bank_name', e.target.value)}
                                        placeholder="Banca XYZ"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="iban">IBAN</Label>
                                    <Input
                                        id="iban"
                                        data-testid="input-iban"
                                        value={settings.bank_details.iban}
                                        onChange={(e) => updateBankField('iban', e.target.value.toUpperCase())}
                                        placeholder="IT60X0542811101000000123456"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="bic_swift">BIC/SWIFT</Label>
                                    <Input
                                        id="bic_swift"
                                        data-testid="input-bic"
                                        value={settings.bank_details.bic_swift}
                                        onChange={(e) => updateBankField('bic_swift', e.target.value.toUpperCase())}
                                        placeholder="BNLIITRR"
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}
