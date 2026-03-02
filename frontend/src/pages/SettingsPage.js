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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Save, Building2, CreditCard, FileText, ImageIcon, Upload, X, Plug, ShieldCheck } from 'lucide-react';
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
        responsabile_nome: '',
        ruolo_firmatario: '',
        ente_certificatore: '',
        ente_certificatore_numero: '',
        certificato_en1090_numero: '',
        classe_esecuzione_default: '',
        certificato_en13241_numero: '',
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
                    responsabile_nome: data.responsabile_nome || '',
                    ruolo_firmatario: data.ruolo_firmatario || '',
                    ente_certificatore: data.ente_certificatore || '',
                    ente_certificatore_numero: data.ente_certificatore_numero || '',
                    certificato_en1090_numero: data.certificato_en1090_numero || '',
                    classe_esecuzione_default: data.classe_esecuzione_default || '',
                    certificato_en13241_numero: data.certificato_en13241_numero || '',
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
                        <TabsTrigger value="certificazioni" className="gap-2">
                            <ShieldCheck className="h-4 w-4" />
                            Certificazioni
                        </TabsTrigger>
                        <TabsTrigger value="migrazione" className="gap-2">
                            <Upload className="h-4 w-4" />
                            Migrazione
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

                        {/* Firma Digitale */}
                        <Card className="border-gray-200 mt-4">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
                                <CardTitle>Firma Digitale</CardTitle>
                                <CardDescription>Immagine della firma che verrà inserita automaticamente nei PDF generati (Fascicolo Tecnico, DOP, ecc.)</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                {settings.firma_digitale && (
                                    <div className="mb-3 flex items-center gap-4">
                                        <div className="border rounded p-2 bg-white">
                                            <img
                                                src={settings.firma_digitale}
                                                alt="Firma digitale"
                                                style={{ maxHeight: '60px', maxWidth: '200px' }}
                                            />
                                        </div>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="text-red-600"
                                            data-testid="btn-remove-firma"
                                            onClick={() => updateField('firma_digitale', '')}
                                        >
                                            Rimuovi firma
                                        </Button>
                                    </div>
                                )}
                                    <Label>Carica Firma (PNG, JPG, max 500KB)</Label>
                                    <div className="flex items-center gap-2 mt-1">
                                        <label className="cursor-pointer inline-flex items-center gap-2 px-3 py-2 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 text-sm">
                                            <span>{settings.firma_digitale ? 'Cambia firma' : 'Seleziona un file immagine'}</span>
                                            <input
                                                type="file"
                                                accept="image/png,image/jpeg"
                                                className="hidden"
                                                data-testid="input-firma-upload"
                                                onChange={(e) => {
                                                    const file = e.target.files[0];
                                                    if (!file) return;
                                                    if (file.size > 500 * 1024) {
                                                        toast.error('Il file è troppo grande (max 500KB)');
                                                        return;
                                                    }
                                                    const reader = new FileReader();
                                                    reader.onload = (ev) => {
                                                        updateField('firma_digitale', ev.target.result);
                                                    };
                                                    reader.readAsDataURL(file);
                                                    e.target.value = '';
                                                }}
                                            />
                                        </label>
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

                    <TabsContent value="certificazioni">
                        <Card className="border-gray-200">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
                                <CardTitle>Numeri di Certificazione</CardTitle>
                                <CardDescription>
                                    Inserisci i numeri di certificazione rilasciati dall'ente notificato
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6 pt-4">
                                {/* EN 1090-1 */}
                                <div className="p-4 rounded-lg border-2 border-blue-200 bg-blue-50/30">
                                    <div className="flex items-center gap-2 mb-3">
                                        <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                                        <h3 className="font-semibold text-slate-800">EN 1090-1 (Strutture in acciaio)</h3>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <Label htmlFor="cert_en1090">Numero Certificazione</Label>
                                            <Input
                                                id="cert_en1090"
                                                data-testid="input-cert-en1090"
                                                value={settings.certificato_en1090_numero}
                                                onChange={(e) => updateField('certificato_en1090_numero', e.target.value)}
                                                placeholder="Es: 0474 - CPR - 2478"
                                            />
                                        </div>
                                        <div>
                                            <Label htmlFor="classe_esecuzione_default">Classe Esecuzione Default</Label>
                                            <Select
                                                value={settings.classe_esecuzione_default || ''}
                                                onValueChange={(v) => updateField('classe_esecuzione_default', v)}
                                            >
                                                <SelectTrigger id="classe_esecuzione_default" data-testid="select-classe-esecuzione">
                                                    <SelectValue placeholder="Seleziona classe" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="EXC1">EXC1</SelectItem>
                                                    <SelectItem value="EXC2">EXC2</SelectItem>
                                                    <SelectItem value="EXC3">EXC3</SelectItem>
                                                    <SelectItem value="EXC4">EXC4</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                </div>

                                {/* EN 13241 */}
                                <div className="p-4 rounded-lg border-2 border-amber-200 bg-amber-50/30">
                                    <div className="flex items-center gap-2 mb-3">
                                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                                        <h3 className="font-semibold text-slate-800">EN 13241 (Porte e cancelli industriali)</h3>
                                    </div>
                                    <div>
                                        <Label htmlFor="cert_en13241">Numero Certificazione</Label>
                                        <Input
                                            id="cert_en13241"
                                            data-testid="input-cert-en13241"
                                            value={settings.certificato_en13241_numero}
                                            onChange={(e) => updateField('certificato_en13241_numero', e.target.value)}
                                            placeholder="Es: 1234-CPR-9012"
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Certificazione EN 1090 - Dati ente */}
                        <Card className="border-gray-200 mt-4">
                            <CardHeader className="bg-blue-50 border-b border-gray-200">
                                <CardTitle>Dati Ente Certificatore</CardTitle>
                                <CardDescription>Dati dell'ente certificatore e del responsabile. Vengono auto-compilati nel Fascicolo Tecnico.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4 pt-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <Label htmlFor="responsabile_nome">Responsabile / Redatto da</Label>
                                        <Input id="responsabile_nome" value={settings.responsabile_nome} onChange={e => updateField('responsabile_nome', e.target.value)} placeholder="Nome Cognome dell'amministratore" data-testid="input-responsabile-nome-cert" />
                                    </div>
                                    <div>
                                        <Label htmlFor="ruolo_firmatario">Ruolo Firmatario</Label>
                                        <Input id="ruolo_firmatario" value={settings.ruolo_firmatario} onChange={e => updateField('ruolo_firmatario', e.target.value)} placeholder="es. Legale Rappresentante" data-testid="input-ruolo-firmatario-cert" />
                                    </div>
                                    <div>
                                        <Label htmlFor="ente_certificatore">Ente Certificatore</Label>
                                        <Input id="ente_certificatore" value={settings.ente_certificatore} onChange={e => updateField('ente_certificatore', e.target.value)} placeholder="es. Rina Service" data-testid="input-ente-certificatore-cert" />
                                    </div>
                                    <div>
                                        <Label htmlFor="ente_certificatore_numero">Numero Ente</Label>
                                        <Input id="ente_certificatore_numero" value={settings.ente_certificatore_numero} onChange={e => updateField('ente_certificatore_numero', e.target.value)} placeholder="es. 0474" data-testid="input-ente-numero-cert" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Tab Migrazione */}
                    <TabsContent value="migrazione">
                        <MigrazioneTab />
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}


function MigrazioneTab() {
    const [stato, setStato] = useState(null);
    const [loading, setLoading] = useState(false);
    const [migrating, setMigrating] = useState(false);
    const [result, setResult] = useState(null);

    useEffect(() => {
        fetchStato();
    }, []);

    const fetchStato = async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/migrazione/stato');
            setStato(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleMigrazione = async () => {
        setMigrating(true);
        setResult(null);
        try {
            const data = await apiRequest('/migrazione/importa', { method: 'POST' });
            setResult(data);
            toast.success(data.message);
            fetchStato();
        } catch (e) {
            setResult({ message: e.message || 'Errore durante la migrazione' });
            toast.error('Errore durante la migrazione');
        } finally {
            setMigrating(false);
        }
    };

    const totale = stato ? (stato.anagrafica + stato.preventivi + stato.fatture_vendita + stato.fatture_acquisto) : 0;

    return (
        <Card className="border-gray-200">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Upload className="h-5 w-5 text-[#0055FF]" />
                    Importa da Vecchia App
                </CardTitle>
                <CardDescription>
                    Importa preventivi, fatture e anagrafica dalla vecchia versione di Norma Facile. L'importazione salta automaticamente i duplicati.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                {stato && totale > 0 && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4" data-testid="migration-status">
                        <p className="text-sm font-semibold text-emerald-800 mb-2">Dati importati:</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            <StatBox label="Anagrafica" value={stato.anagrafica} />
                            <StatBox label="Preventivi" value={stato.preventivi} />
                            <StatBox label="Fatture Vendita" value={stato.fatture_vendita} />
                            <StatBox label="Fatture Acquisto" value={stato.fatture_acquisto} />
                        </div>
                    </div>
                )}

                {stato && totale === 0 && !loading && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                        <p className="text-sm text-amber-800">Nessun dato importato. Clicca il bottone per avviare la migrazione dalla vecchia app.</p>
                    </div>
                )}

                <div className="flex items-center gap-3">
                    <Button
                        onClick={handleMigrazione}
                        disabled={migrating}
                        className="bg-[#0055FF] hover:bg-[#0044CC]"
                        data-testid="btn-importa-vecchia-app"
                    >
                        <Upload className={`h-4 w-4 mr-2 ${migrating ? 'animate-bounce' : ''}`} />
                        {migrating ? 'Importazione in corso...' : 'Importa da Vecchia App'}
                    </Button>
                    {totale > 0 && (
                        <p className="text-xs text-gray-500">Puoi rieseguire senza rischi: i duplicati vengono saltati.</p>
                    )}
                </div>

                {result && (
                    <div className={`rounded-lg p-4 text-sm ${result.results ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border border-red-200'}`} data-testid="migration-result">
                        <p className="font-medium mb-1">{result.message}</p>
                        {result.results && (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                                <span className="text-blue-700">Anagrafica: <strong>{result.results.anagrafica}</strong></span>
                                <span className="text-blue-700">Preventivi: <strong>{result.results.preventivi}</strong></span>
                                <span className="text-blue-700">Fatt. Vendita: <strong>{result.results.fatture_vendita}</strong></span>
                                <span className="text-blue-700">Fatt. Acquisto: <strong>{result.results.fatture_acquisto}</strong></span>
                            </div>
                        )}
                        {result.results?.errors?.length > 0 && (
                            <div className="mt-2 text-red-600 text-xs">
                                {result.results.errors.map((e, i) => <p key={i}>{e}</p>)}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function StatBox({ label, value }) {
    return (
        <div className="text-center bg-white rounded-md p-2 border border-emerald-100">
            <p className="text-lg font-bold text-[#1E293B]">{value}</p>
            <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        </div>
    );
}
