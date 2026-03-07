/**
 * Settings Page - Company Settings
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Save, Building2, CreditCard, FileText, ImageIcon, Upload, X, Plug, ShieldCheck, HardDrive, Download, Loader2, RefreshCw, UploadCloud, Users, UserPlus, Trash2, Shield } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useConfirm } from '../components/ConfirmProvider';
import {
    AlertDialog,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '../components/ui/alert-dialog';

export default function SettingsPage() {
    const confirm = useConfirm();
    const { user } = useAuth();
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
        bank_accounts: [],
        codice_destinatario: '',
        natura_giuridica: '',
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
                    bank_accounts: data.bank_accounts || prev.bank_accounts || [],
                    codice_destinatario: data.codice_destinatario || '',
                    natura_giuridica: data.natura_giuridica || '',
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
                        <TabsTrigger value="backup" className="gap-2" data-testid="tab-backup">
                            <HardDrive className="h-4 w-4" />
                            Backup
                        </TabsTrigger>
                        {user?.role === 'admin' && (
                            <TabsTrigger value="team" className="gap-2" data-testid="tab-team">
                                <Users className="h-4 w-4" />
                                Team
                            </TabsTrigger>
                        )}
                        {user?.role === 'admin' && (
                            <TabsTrigger value="deploy" className="gap-2" data-testid="tab-deploy">
                                <Trash2 className="h-4 w-4" />
                                Deploy
                            </TabsTrigger>
                        )}
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
                                <CardTitle>Conti Correnti Aziendali</CardTitle>
                                <CardDescription>Gestisci i tuoi conti correnti — selezionabili nei preventivi e fatture</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {settings.bank_accounts.map((acc, idx) => (
                                    <div key={acc.account_id || idx} className="border border-slate-200 rounded-lg p-3 space-y-2 relative" data-testid={`bank-account-${idx}`}>
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs font-semibold text-slate-500">Conto {idx + 1}</span>
                                            <div className="flex items-center gap-2">
                                                <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                                                    <input type="checkbox" checked={acc.predefinito || false} onChange={() => {
                                                        setSettings(s => ({
                                                            ...s,
                                                            bank_accounts: s.bank_accounts.map((a, i) => ({ ...a, predefinito: i === idx })),
                                                        }));
                                                    }} className="rounded" />
                                                    Predefinito
                                                </label>
                                                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={() => {
                                                    setSettings(s => ({ ...s, bank_accounts: s.bank_accounts.filter((_, i) => i !== idx) }));
                                                }}><Trash2 className="h-3 w-3" /></Button>
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div>
                                                <Label className="text-xs">Nome Banca</Label>
                                                <Input value={acc.bank_name} onChange={e => {
                                                    setSettings(s => ({ ...s, bank_accounts: s.bank_accounts.map((a, i) => i === idx ? { ...a, bank_name: e.target.value } : a) }));
                                                }} placeholder="Monte dei Paschi" className="h-8 text-sm" />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Intestatario</Label>
                                                <Input value={acc.intestatario || ''} onChange={e => {
                                                    setSettings(s => ({ ...s, bank_accounts: s.bank_accounts.map((a, i) => i === idx ? { ...a, intestatario: e.target.value } : a) }));
                                                }} placeholder="Steel Project Design S.r.l.s." className="h-8 text-sm" />
                                            </div>
                                        </div>
                                        <div>
                                            <Label className="text-xs">IBAN</Label>
                                            <Input value={acc.iban} onChange={e => {
                                                setSettings(s => ({ ...s, bank_accounts: s.bank_accounts.map((a, i) => i === idx ? { ...a, iban: e.target.value.toUpperCase() } : a) }));
                                            }} placeholder="IT60X0542811101000000123456" className="h-8 text-sm font-mono" />
                                        </div>
                                        <div>
                                            <Label className="text-xs">BIC/SWIFT</Label>
                                            <Input value={acc.bic_swift || ''} onChange={e => {
                                                setSettings(s => ({ ...s, bank_accounts: s.bank_accounts.map((a, i) => i === idx ? { ...a, bic_swift: e.target.value.toUpperCase() } : a) }));
                                            }} placeholder="PASCITM1XXX" className="h-8 text-sm font-mono" />
                                        </div>
                                    </div>
                                ))}
                                <Button variant="outline" className="w-full border-dashed" data-testid="btn-add-bank" onClick={() => {
                                    setSettings(s => ({
                                        ...s,
                                        bank_accounts: [...s.bank_accounts, {
                                            account_id: `ba_${Date.now()}`,
                                            bank_name: '', iban: '', bic_swift: '', intestatario: '',
                                            predefinito: s.bank_accounts.length === 0,
                                        }],
                                    }));
                                }}>
                                    <CreditCard className="h-4 w-4 mr-2" /> Aggiungi Conto Corrente
                                </Button>
                            </CardContent>
                        </Card>

                        <Card className="border-gray-200 mt-4">
                            <CardHeader className="bg-amber-50 border-b border-gray-200">
                                <CardTitle>Fatturazione Elettronica (SDI)</CardTitle>
                                <CardDescription>Dati necessari per l'invio delle fatture allo SDI</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label className="text-xs">Codice Destinatario SDI</Label>
                                        <Input
                                            data-testid="input-codice-sdi"
                                            value={settings.codice_destinatario || ''}
                                            onChange={e => setSettings(s => ({ ...s, codice_destinatario: e.target.value.toUpperCase() }))}
                                            placeholder="0000000"
                                            maxLength={7}
                                            className="font-mono"
                                        />
                                        <p className="text-[10px] text-slate-500 mt-0.5">7 caratteri — il tuo codice per ricevere fatture</p>
                                    </div>
                                    <div>
                                        <Label className="text-xs">Natura Giuridica</Label>
                                        <select
                                            data-testid="select-natura-giuridica"
                                            value={settings.natura_giuridica || ''}
                                            onChange={e => setSettings(s => ({ ...s, natura_giuridica: e.target.value }))}
                                            className="flex h-9 w-full items-center rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                        >
                                            <option value="">-- Seleziona --</option>
                                            <option value="DI">Ditta individuale</option>
                                            <option value="SNC">S.n.c.</option>
                                            <option value="SAS">S.a.s.</option>
                                            <option value="SRL">S.r.l.</option>
                                            <option value="SRLS">S.r.l.s.</option>
                                            <option value="SPA">S.p.A.</option>
                                            <option value="SAPA">S.a.p.a.</option>
                                            <option value="COOP">Cooperativa</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label className="text-xs">PEC Aziendale</Label>
                                        <Input
                                            value={settings.pec || ''}
                                            onChange={e => setSettings(s => ({ ...s, pec: e.target.value }))}
                                            placeholder="fatture@pec.azienda.it"
                                        />
                                    </div>
                                    <div>
                                        <Label className="text-xs">Regime Fiscale</Label>
                                        <select
                                            value={settings.regime_fiscale || 'RF01'}
                                            onChange={e => setSettings(s => ({ ...s, regime_fiscale: e.target.value }))}
                                            className="flex h-9 w-full items-center rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                        >
                                            <option value="RF01">RF01 - Ordinario</option>
                                            <option value="RF02">RF02 - Contribuenti minimi</option>
                                            <option value="RF04">RF04 - Agricoltura</option>
                                            <option value="RF19">RF19 - Forfettario</option>
                                        </select>
                                    </div>
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
                    <TabsContent value="backup">
                        <BackupTab />
                    </TabsContent>
                    {user?.role === 'admin' && (
                        <TabsContent value="team">
                            <TeamTab />
                        </TabsContent>
                    )}
                    {user?.role === 'admin' && (
                        <TabsContent value="deploy">
                            <DeployTab />
                        </TabsContent>
                    )}
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

function TeamTab() {
    const [members, setMembers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [roleLabels, setRoleLabels] = useState({});
    const [loading, setLoading] = useState(true);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteName, setInviteName] = useState('');
    const [inviteRole, setInviteRole] = useState('officina');
    const [sending, setSending] = useState(false);

    const fetchTeam = useCallback(async () => {
        try {
            const data = await apiRequest('/team/members');
            setMembers(data.members || []);
            setInvites(data.invites || []);
            setRoleLabels(data.roles || {});
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchTeam(); }, [fetchTeam]);

    const handleInvite = async () => {
        if (!inviteEmail) { toast.error('Inserisci un\'email'); return; }
        setSending(true);
        try {
            await apiRequest('/team/invite', { method: 'POST', body: { email: inviteEmail, role: inviteRole, name: inviteName } });
            toast.success(`Invito inviato a ${inviteEmail}`);
            setInviteEmail(''); setInviteName('');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
        finally { setSending(false); }
    };

    const handleChangeRole = async (userId, newRole) => {
        try {
            await apiRequest(`/team/members/${userId}/role`, { method: 'PUT', body: { role: newRole } });
            toast.success('Ruolo aggiornato');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
    };

    const handleRemoveMember = async (userId) => {
        if (!(await confirm('Sei sicuro di voler rimuovere questo membro?'))) return;
        try {
            await apiRequest(`/team/members/${userId}`, { method: 'DELETE' });
            toast.success('Membro rimosso');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
    };

    const handleRevokeInvite = async (inviteId) => {
        try {
            await apiRequest(`/team/invites/${inviteId}`, { method: 'DELETE' });
            toast.success('Invito revocato');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
    };

    const ROLE_OPTIONS = [
        { value: 'ufficio_tecnico', label: 'Ufficio Tecnico', desc: 'Commesse, FPC, Saldatori, Qualità' },
        { value: 'officina', label: 'Officina', desc: 'Solo produzione, no finanza' },
        { value: 'amministrazione', label: 'Amministrazione', desc: 'Fatture, costi, clienti, no WPS' },
        { value: 'guest', label: 'In Attesa', desc: 'Nessun accesso ai dati' },
    ];

    const ROLE_COLORS = {
        admin: 'bg-lime-100 text-lime-800 border-lime-300',
        ufficio_tecnico: 'bg-blue-100 text-blue-800 border-blue-300',
        officina: 'bg-amber-100 text-amber-800 border-amber-300',
        amministrazione: 'bg-violet-100 text-violet-800 border-violet-300',
        guest: 'bg-slate-100 text-slate-600 border-slate-300',
    };

    return (
        <Card className="border-gray-200">
            <CardHeader className="bg-slate-800 border-b border-gray-200 rounded-t-lg">
                <CardTitle className="text-white flex items-center gap-2">
                    <Users className="h-5 w-5" /> Gestione Team
                </CardTitle>
                <CardDescription className="text-slate-300">
                    Invita i dipendenti e assegna i ruoli. Quando faranno login con Google, avranno i permessi corretti.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {/* Invite form */}
                <div className="border border-blue-200 bg-blue-50/30 rounded-lg p-4 space-y-3">
                    <h3 className="text-sm font-bold text-blue-800 flex items-center gap-1.5">
                        <UserPlus className="h-4 w-4" /> Invita Nuovo Membro
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                        <Input placeholder="Email" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} className="text-xs h-9" data-testid="invite-email" />
                        <Input placeholder="Nome (opzionale)" value={inviteName} onChange={e => setInviteName(e.target.value)} className="text-xs h-9" />
                        <Select value={inviteRole} onValueChange={setInviteRole}>
                            <SelectTrigger className="h-9 text-xs" data-testid="invite-role"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {ROLE_OPTIONS.map(r => (
                                    <SelectItem key={r.value} value={r.value} className="text-xs">{r.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Button onClick={handleInvite} disabled={sending} className="h-9 bg-blue-600 hover:bg-blue-700 text-white text-xs" data-testid="btn-invite">
                            {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <UserPlus className="h-3.5 w-3.5 mr-1" />}
                            Invita
                        </Button>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {ROLE_OPTIONS.map(r => (
                            <div key={r.value} className="bg-white border rounded px-2 py-1.5">
                                <p className={`text-[10px] font-bold border rounded-full px-1.5 py-0.5 inline-block ${ROLE_COLORS[r.value]}`}>{r.label}</p>
                                <p className="text-[9px] text-slate-400 mt-0.5">{r.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Pending invites */}
                {invites.length > 0 && (
                    <div>
                        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Inviti in Attesa ({invites.length})</h3>
                        <div className="space-y-1.5">
                            {invites.map(inv => (
                                <div key={inv.invite_id} className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-lg px-3 py-2" data-testid={`invite-${inv.invite_id}`}>
                                    <div>
                                        <p className="text-xs font-medium text-slate-700">{inv.email} {inv.name && <span className="text-slate-400">({inv.name})</span>}</p>
                                        <span className={`text-[9px] font-bold border rounded-full px-1.5 py-0.5 ${ROLE_COLORS[inv.role]}`}>{roleLabels[inv.role] || inv.role}</span>
                                    </div>
                                    <button onClick={() => handleRevokeInvite(inv.invite_id)} className="text-slate-400 hover:text-red-500 p-1" title="Revoca invito">
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Active members */}
                <div>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Membri Attivi ({members.length})</h3>
                    {loading ? (
                        <p className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Caricamento...</p>
                    ) : (
                        <div className="space-y-1.5">
                            {members.map(m => (
                                <div key={m.user_id} className="flex items-center justify-between bg-white border rounded-lg px-3 py-2" data-testid={`member-${m.user_id}`}>
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
                                            {m.name?.charAt(0) || m.email?.charAt(0) || '?'}
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-slate-700">{m.name || m.email}</p>
                                            <p className="text-[10px] text-slate-400">{m.email}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {m.role === 'admin' ? (
                                            <span className={`text-[9px] font-bold border rounded-full px-2 py-0.5 ${ROLE_COLORS.admin}`}>
                                                <Shield className="h-2.5 w-2.5 inline mr-0.5" /> Admin
                                            </span>
                                        ) : (
                                            <>
                                                <Select value={m.role || 'guest'} onValueChange={val => handleChangeRole(m.user_id, val)}>
                                                    <SelectTrigger className="h-7 text-[10px] w-32 border-slate-200"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {ROLE_OPTIONS.map(r => (
                                                            <SelectItem key={r.value} value={r.value} className="text-xs">{r.label}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <button onClick={() => handleRemoveMember(m.user_id)} className="text-slate-400 hover:text-red-500 p-1" title="Rimuovi">
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}


function BackupTab() {
    const confirm = useConfirm();
    const [lastBackup, setLastBackup] = useState(null);
    const [stats, setStats] = useState(null);
    const [loadingStats, setLoadingStats] = useState(true);
    const [exporting, setExporting] = useState(false);
    const [restoring, setRestoring] = useState(false);
    const [restoreResult, setRestoreResult] = useState(null);
    const [pendingFile, setPendingFile] = useState(null);
    const [showModeDialog, setShowModeDialog] = useState(false);

    const API = process.env.REACT_APP_BACKEND_URL;

    useEffect(() => {
        (async () => {
            try {
                const [lastRes, statsRes] = await Promise.all([
                    apiRequest('/admin/backup/last'),
                    apiRequest('/admin/backup/stats'),
                ]);
                setLastBackup(lastRes.last_backup);
                setStats(statsRes);
            } catch { /* silent */ }
            finally { setLoadingStats(false); }
        })();
    }, []);

    const handleExport = async () => {
        setExporting(true);
        try {
            const res = await fetch(`${API}/api/admin/backup/export`, { credentials: 'include' });
            if (!res.ok) throw new Error(`Errore ${res.status}`);
            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(blob);
            // USA document corrente — NON window.top
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            const disposition = res.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?(.+?)"?$/);
            a.download = match ? match[1] : `backup_normafacile_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
            }, 1000);
            toast.success('Backup scaricato con successo!');
            const lastRes = await apiRequest('/admin/backup/last');
            setLastBackup(lastRes.last_backup);
        } catch (e) {
            console.error('Download backup error:', e.name, e.message);
            try {
                window.open(`${API}/api/admin/backup/export`, '_blank');
                toast.info('Download aperto in nuovo tab');
            } catch {
                toast.error(e.message);
            }
        }
        finally { setExporting(false); }
    };

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        setPendingFile(file);
        setShowModeDialog(true);
    };

    const executeRestore = async (mode) => {
        setShowModeDialog(false);
        const file = pendingFile;
        setPendingFile(null);
        if (!file) return;

        if (mode === 'wipe') {
            const ok = await confirm(
                'ATTENZIONE CRITICA: Scegliendo "Sostituzione Totale", TUTTI i dati attuali verranno CANCELLATI prima dell\'importazione.\n\nQuesta operazione è IRREVERSIBILE.\n\nSei assolutamente sicuro?',
                'Conferma Sostituzione Totale'
            );
            if (!ok) return;
        }

        setRestoring(true);
        setRestoreResult(null);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('mode', mode);
            const res = await fetch(`${API}/api/admin/backup/restore`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Errore restore');
            setRestoreResult(data);
            toast.success(data.message);
            // Refresh stats
            const [lastRes, statsRes] = await Promise.all([
                apiRequest('/admin/backup/last'),
                apiRequest('/admin/backup/stats'),
            ]);
            setLastBackup(lastRes.last_backup);
            setStats(statsRes);
        } catch (err) { toast.error(err.message); }
        finally { setRestoring(false); }
    };

    const cancelRestore = () => {
        setShowModeDialog(false);
        setPendingFile(null);
    };

    const fmtSize = (bytes) => {
        if (!bytes) return '\u2014';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1048576).toFixed(1)} MB`;
    };

    const fmtDate = (d) => {
        if (!d) return '\u2014';
        try { return new Date(d).toLocaleString('it-IT', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
        catch { return d; }
    };

    const COLLECTION_LABELS = {
        commesse: 'Commesse', preventivi: 'Preventivi', clients: 'Clienti',
        invoices: 'Fatture Emesse', ddt: 'DDT', fpc_projects: 'Progetti FPC',
        gate_certifications: 'Cert. Cancelli', welders: 'Saldatori',
        instruments: 'Strumenti', company_docs: 'Documenti', distinte: 'Distinte',
        rilievi: 'Rilievi', fatture_ricevute: 'Fatture Ricevute',
        consumable_batches: 'Consumabili', project_costs: 'Costi Progetto',
        audit_findings: 'Audit/NC', company_settings: 'Impostazioni',
        catalogo_profili: 'Catalogo Profili', articoli: 'Articoli',
    };

    return (
        <>
        <Card className="border-gray-200">
            <CardHeader className="bg-slate-800 border-b border-gray-200 rounded-t-lg">
                <CardTitle className="text-white flex items-center gap-2">
                    <HardDrive className="h-5 w-5" /> Backup & Restore Dati
                </CardTitle>
                <CardDescription className="text-slate-300">
                    Scarica una copia completa dei dati aziendali o ripristina da un backup precedente
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {/* Export Section */}
                <div className="border border-emerald-200 bg-emerald-50/30 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-sm font-bold text-emerald-800 flex items-center gap-1.5">
                                <Download className="h-4 w-4" /> Esporta Backup
                            </h3>
                            <p className="text-xs text-emerald-600 mt-0.5">
                                Scarica un file JSON con tutti i dati: commesse, clienti, preventivi, certificazioni, fatture e altro.
                            </p>
                        </div>
                    </div>

                    {lastBackup && (
                        <div className="bg-white border border-emerald-200 rounded-lg p-3">
                            <p className="text-xs text-slate-500">Ultimo backup: <strong className="text-slate-700">{fmtDate(lastBackup.date)}</strong></p>
                            <p className="text-xs text-slate-400 mt-0.5">
                                {lastBackup.total_records} record — {fmtSize(lastBackup.size_bytes)}
                            </p>
                        </div>
                    )}

                    {!loadingStats && stats && (
                        <div>
                            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Dati Attuali ({stats.total} record)</p>
                            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-1.5">
                                {Object.entries(stats.stats || {}).filter(([, v]) => v > 0).map(([k, v]) => (
                                    <div key={k} className="bg-white border rounded px-2 py-1.5 text-center">
                                        <p className="text-sm font-bold text-[#1E293B]">{v}</p>
                                        <p className="text-[9px] text-slate-400 leading-tight">{COLLECTION_LABELS[k] || k}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    {loadingStats && <p className="text-xs text-slate-400 flex items-center gap-1"><RefreshCw className="h-3 w-3 animate-spin" /> Calcolo statistiche...</p>}

                    <Button
                        onClick={handleExport}
                        disabled={exporting}
                        className="w-full bg-emerald-600 hover:bg-emerald-700 text-white h-10"
                        data-testid="btn-export-backup"
                    >
                        {exporting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                        {exporting ? 'Generazione backup...' : 'Esegui Backup Ora'}
                    </Button>
                </div>

                {/* Restore Section */}
                <div className="border border-amber-200 bg-amber-50/30 rounded-lg p-4 space-y-3">
                    <div>
                        <h3 className="text-sm font-bold text-amber-800 flex items-center gap-1.5">
                            <UploadCloud className="h-4 w-4" /> Ripristina da Backup
                        </h3>
                        <p className="text-xs text-amber-600 mt-0.5">
                            Importa dati da un file di backup. Dopo aver selezionato il file, potrai scegliere la modalità di importazione.
                        </p>
                    </div>

                    <label className={`flex items-center justify-center w-full h-10 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                        restoring ? 'border-amber-300 bg-amber-100' : 'border-amber-300 hover:border-amber-400 hover:bg-amber-50'
                    }`}>
                        <input type="file" accept=".json" onChange={handleFileSelect} disabled={restoring} className="hidden" data-testid="input-restore-file" />
                        {restoring ? (
                            <span className="flex items-center gap-2 text-xs text-amber-700"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Ripristino in corso...</span>
                        ) : (
                            <span className="flex items-center gap-2 text-xs text-amber-700"><UploadCloud className="h-3.5 w-3.5" /> Seleziona file backup (.json)</span>
                        )}
                    </label>

                    {restoreResult && (
                        <div className="bg-white border border-amber-200 rounded-lg p-3 text-xs" data-testid="restore-result">
                            <p className="font-semibold text-emerald-700">{restoreResult.message}</p>
                            {restoreResult.mode === 'wipe' && restoreResult.total_deleted > 0 && (
                                <p className="text-red-600 mt-1">Record eliminati prima dell'importazione: <strong>{restoreResult.total_deleted}</strong></p>
                            )}
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1 mt-2">
                                {Object.entries(restoreResult.details || {}).filter(([, v]) => v.inserted > 0 || v.updated > 0 || v.errors > 0).map(([k, v]) => (
                                    <span key={k} className="text-slate-600">
                                        {COLLECTION_LABELS[k] || k}: {v.inserted > 0 && <strong className="text-emerald-600">+{v.inserted}</strong>}
                                        {v.updated > 0 && <span className="text-blue-600 font-semibold"> {v.inserted > 0 ? '/ ' : ''}{v.updated} agg.</span>}
                                        {v.errors > 0 && <span className="text-red-500"> ({v.errors} errori)</span>}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>

        {/* Restore Mode Selection Dialog */}
        <AlertDialog open={showModeDialog} onOpenChange={(v) => { if (!v) cancelRestore(); }}>
            <AlertDialogContent className="max-w-lg" data-testid="restore-mode-dialog">
                <AlertDialogHeader>
                    <AlertDialogTitle>Scegli Modalità di Ripristino</AlertDialogTitle>
                    <AlertDialogDescription className="text-sm">
                        File selezionato: <strong>{pendingFile?.name}</strong>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="space-y-3 py-2">
                    <button
                        onClick={() => executeRestore('merge')}
                        className="w-full text-left border-2 border-blue-200 hover:border-blue-400 bg-blue-50/50 hover:bg-blue-50 rounded-lg p-4 transition-colors"
                        data-testid="btn-restore-merge"
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <RefreshCw className="h-4 w-4 text-blue-600" />
                            <span className="font-semibold text-blue-800 text-sm">Unisci / Aggiorna (Consigliato)</span>
                        </div>
                        <p className="text-xs text-blue-600 leading-relaxed">
                            I record esistenti vengono aggiornati, i nuovi vengono inseriti. Nessun dato viene cancellato. Ideale per sincronizzare o aggiornare i dati.
                        </p>
                    </button>
                    <button
                        onClick={() => executeRestore('wipe')}
                        className="w-full text-left border-2 border-red-200 hover:border-red-400 bg-red-50/50 hover:bg-red-50 rounded-lg p-4 transition-colors"
                        data-testid="btn-restore-wipe"
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <Trash2 className="h-4 w-4 text-red-600" />
                            <span className="font-semibold text-red-800 text-sm">Sostituzione Totale</span>
                        </div>
                        <p className="text-xs text-red-600 leading-relaxed">
                            TUTTI i dati attuali vengono CANCELLATI e sostituiti con quelli del backup. Operazione irreversibile. Usare solo per ripristino completo.
                        </p>
                    </button>
                </div>
                <AlertDialogFooter>
                    <AlertDialogCancel onClick={cancelRestore} data-testid="btn-restore-cancel">Annulla</AlertDialogCancel>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
        </>
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


function DeployTab() {
    const confirm = useConfirm();
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(true);
    const [cleaning, setCleaning] = useState(false);
    const [keepClients, setKeepClients] = useState(true);
    const [keepVendors, setKeepVendors] = useState(true);
    const [result, setResult] = useState(null);

    useEffect(() => {
        (async () => {
            try {
                const data = await apiRequest('/admin/cleanup/preview');
                setPreview(data);
            } catch { /* silent */ }
            finally { setLoading(false); }
        })();
    }, []);

    const handleCleanup = async () => {
        if (!(await confirm('ATTENZIONE: Questa operazione cancella TUTTE le commesse, preventivi, fatture e altri dati operativi. Sei sicuro?'))) return;
        if (!(await confirm('ULTIMA CONFERMA: Hai fatto il backup? I dati verranno eliminati permanentemente.'))) return;

        setCleaning(true);
        setResult(null);
        try {
            const data = await apiRequest('/admin/cleanup/execute', {
                method: 'POST',
                body: { confirm: true, keep_clients: keepClients, keep_vendors: keepVendors },
            });
            setResult(data);
            toast.success('Pulizia completata');
            // Refresh preview
            const p = await apiRequest('/admin/cleanup/preview');
            setPreview(p);
        } catch (e) { toast.error(e.message); }
        finally { setCleaning(false); }
    };

    return (
        <Card className="border-gray-200">
            <CardHeader className="bg-red-50 border-b border-gray-200 rounded-t-lg">
                <CardTitle className="text-red-800 flex items-center gap-2">
                    <Trash2 className="h-5 w-5" /> Preparazione Deploy / Pulizia DB
                </CardTitle>
                <CardDescription className="text-red-600">
                    Elimina i dati di test per partire con un database pulito. Fai PRIMA il backup!
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {/* Preview */}
                {loading ? (
                    <p className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Calcolo dati...</p>
                ) : preview && (
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Dati che verranno eliminati</p>
                        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-1.5">
                            {Object.entries(preview.operational_data || {}).filter(([, v]) => v > 0).map(([k, v]) => (
                                <div key={k} className="bg-red-50 border border-red-200 rounded px-2 py-1.5 text-center">
                                    <p className="text-sm font-bold text-red-700">{v}</p>
                                    <p className="text-[9px] text-red-500 leading-tight">{k}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Options */}
                <div className="space-y-3 border rounded-lg p-4 bg-amber-50 border-amber-200">
                    <h3 className="text-sm font-bold text-amber-800">Opzioni</h3>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input type="checkbox" checked={keepClients} onChange={e => setKeepClients(e.target.checked)} className="rounded" />
                        <span>Mantieni Clienti ({preview?.clients || 0})</span>
                    </label>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input type="checkbox" checked={keepVendors} onChange={e => setKeepVendors(e.target.checked)} className="rounded" />
                        <span>Mantieni Fornitori ({preview?.vendors || 0})</span>
                    </label>
                </div>

                {/* Execute */}
                <Button
                    onClick={handleCleanup}
                    disabled={cleaning}
                    variant="destructive"
                    className="w-full h-10"
                    data-testid="btn-execute-cleanup"
                >
                    {cleaning ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
                    {cleaning ? 'Pulizia in corso...' : 'Esegui Pulizia Database'}
                </Button>

                {/* Result */}
                {result && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4" data-testid="cleanup-result">
                        <p className="text-sm font-semibold text-emerald-800">{result.message}</p>
                        <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5 mt-2">
                            {Object.entries(result.deleted || {}).filter(([, v]) => v > 0).map(([k, v]) => (
                                <div key={k} className="bg-white border rounded px-2 py-1 text-center">
                                    <p className="text-sm font-bold text-slate-700">{v}</p>
                                    <p className="text-[9px] text-slate-400">{k} eliminati</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
