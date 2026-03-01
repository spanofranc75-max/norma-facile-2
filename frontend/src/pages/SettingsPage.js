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
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Save, Building2, CreditCard, FileText, ImageIcon, Upload, X, Plug } from 'lucide-react';
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
        logo_url: '',
        firma_digitale: '',
        condizioni_vendita: '',
        aruba_username: '',
        aruba_password: '',
        aruba_sandbox: true,
        fic_company_id: '',
        fic_access_token: '',
    });

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const data = await apiRequest('/company/settings');
                setSettings(prev => ({
                    ...prev,
                    ...data,
                    bank_details: data.bank_details || prev.bank_details,
                    logo_url: data.logo_url || '',
                    firma_digitale: data.firma_digitale || '',
                    condizioni_vendita: data.condizioni_vendita || '',
                    aruba_username: data.aruba_username || '',
                    aruba_password: data.aruba_password || '',
                    aruba_sandbox: data.aruba_sandbox !== false,
                    fic_company_id: data.fic_company_id || '',
                    fic_access_token: data.fic_access_token || '',
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
                        <h1 className="font-sans text-3xl font-bold text-slate-900">
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
                        <TabsTrigger value="logo" className="gap-2">
                            <ImageIcon className="h-4 w-4" />
                            Logo
                        </TabsTrigger>
                        <TabsTrigger value="condizioni" className="gap-2">
                            <FileText className="h-4 w-4" />
                            Condizioni
                        </TabsTrigger>
                        <TabsTrigger value="integrazioni" className="gap-2">
                            <Plug className="h-4 w-4" />
                            Integrazioni
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="company">
                        <Card className="border-gray-200">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
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
                        <Card className="border-gray-200">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
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

                    <TabsContent value="logo">
                        <Card className="border-gray-200">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
                                <CardTitle>Logo Aziendale</CardTitle>
                                <CardDescription>
                                    Il logo verrà mostrato nella sidebar e nell'intestazione dei documenti PDF
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {settings.logo_url && (
                                    <div className="flex items-start gap-4">
                                        <div className="border rounded-lg p-2 bg-white">
                                            <img
                                                src={settings.logo_url}
                                                alt="Logo aziendale"
                                                data-testid="logo-preview"
                                                className="max-h-24 max-w-48 object-contain"
                                            />
                                        </div>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            data-testid="btn-remove-logo"
                                            onClick={() => updateField('logo_url', '')}
                                            className="text-red-600 hover:text-red-700"
                                        >
                                            <X className="h-4 w-4 mr-1" /> Rimuovi
                                        </Button>
                                    </div>
                                )}
                                <div>
                                    <Label>Carica Logo (PNG, JPG, max 500KB)</Label>
                                    <div className="mt-2">
                                        <label
                                            htmlFor="logo-upload"
                                            data-testid="logo-upload-label"
                                            className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-300 rounded-lg cursor-pointer hover:border-[#0055FF] hover:bg-blue-50 transition-colors"
                                        >
                                            <Upload className="h-5 w-5 text-slate-400" />
                                            <span className="text-sm text-slate-600">
                                                {settings.logo_url ? 'Cambia logo' : 'Seleziona un file immagine'}
                                            </span>
                                        </label>
                                        <input
                                            id="logo-upload"
                                            type="file"
                                            accept="image/png,image/jpeg,image/webp"
                                            className="hidden"
                                            data-testid="input-logo-upload"
                                            onChange={(e) => {
                                                const file = e.target.files?.[0];
                                                if (!file) return;
                                                if (file.size > 500 * 1024) {
                                                    toast.error('Il file è troppo grande (max 500KB)');
                                                    return;
                                                }
                                                const reader = new FileReader();
                                                reader.onload = (ev) => {
                                                    updateField('logo_url', ev.target.result);
                                                };
                                                reader.readAsDataURL(file);
                                                e.target.value = '';
                                            }}
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="condizioni">
                        <Card className="border-gray-200">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
                                <CardTitle>Condizioni di Vendita</CardTitle>
                                <CardDescription>
                                    Queste condizioni verranno stampate in calce a preventivi, fatture e DDT
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                    <Label htmlFor="condizioni_vendita">Testo condizioni</Label>
                                    <Textarea
                                        id="condizioni_vendita"
                                        data-testid="input-condizioni-vendita"
                                        value={settings.condizioni_vendita}
                                        onChange={(e) => updateField('condizioni_vendita', e.target.value)}
                                        placeholder="Es: Pagamento a 30 giorni data fattura. Merce viaggiante a rischio del committente. Foro competente: Tribunale di..."
                                        rows={10}
                                        className="font-mono text-sm"
                                    />
                                    <p className="text-xs text-slate-400 mt-1">
                                        Questo testo verrà aggiunto automaticamente in fondo a tutti i documenti generati.
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="integrazioni">
                        <Card className="border-gray-200">
                            <CardHeader className="bg-amber-50 border-b border-gray-200">
                                <CardTitle>Fatture in Cloud (SDI)</CardTitle>
                                <CardDescription>
                                    Credenziali per sincronizzare le fatture con Fatture in Cloud e inviarle al Sistema di Interscambio
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4 pt-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <Label htmlFor="fic_company_id">Company ID</Label>
                                        <Input
                                            id="fic_company_id"
                                            data-testid="input-fic-company-id"
                                            value={settings.fic_company_id}
                                            onChange={(e) => updateField('fic_company_id', e.target.value)}
                                            placeholder="es. 1398737"
                                        />
                                    </div>
                                    <div>
                                        <Label htmlFor="fic_access_token">Access Token</Label>
                                        <Input
                                            id="fic_access_token"
                                            type="password"
                                            data-testid="input-fic-access-token"
                                            value={settings.fic_access_token}
                                            onChange={(e) => updateField('fic_access_token', e.target.value)}
                                            placeholder="Token da Fatture in Cloud"
                                        />
                                    </div>
                                </div>
                                <p className="text-xs text-slate-400 mt-2">
                                    Trova le credenziali in Fatture in Cloud → Impostazioni → Applicazioni collegate → Token.
                                    Le credenziali vengono salvate in modo sicuro nel database.
                                </p>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}
