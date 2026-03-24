/**
 * Settings Page - Company Settings (Refactored)
 * Each tab is now a separate component in /components/settings/
 */
import { useState, useEffect } from 'react';
import { apiRequest } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { Save, Building2, CreditCard, FileText, ImageIcon, Upload, Plug, ShieldCheck, HardDrive, Users, Trash2, Bell, Shield, Bug } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

import CompanyTab from '../components/settings/CompanyTab';
import BankTab from '../components/settings/BankTab';
import LogoTab from '../components/settings/LogoTab';
import CondizioniTab from '../components/settings/CondizioniTab';
import IntegrazioniTab from '../components/settings/IntegrazioniTab';
import CertificazioniTab from '../components/settings/CertificazioniTab';
import MigrazioneTab from '../components/settings/MigrazioneTab';
import TeamTab from '../components/settings/TeamTab';
import BackupTab from '../components/settings/BackupTab';
import DeployTab from '../components/settings/DeployTab';
import NotificheTab from '../components/settings/NotificheTab';
import DocumentiAziendaTab from '../components/settings/DocumentiAziendaTab';
import AllegatiPosTab from '../components/settings/AllegatiPosTab';
import FigureAziendaliTab from '../components/settings/FigureAziendaliTab';
import DiagnosticaTab from '../components/settings/DiagnosticaTab';

export default function SettingsPage() {
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
        figure_aziendali: [],
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
                    figure_aziendali: data.figure_aziendali || [],
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
                        <TabsTrigger value="notifiche" className="gap-2" data-testid="tab-notifiche">
                            <Bell className="h-4 w-4" />
                            Notifiche
                        </TabsTrigger>
                        <TabsTrigger value="documenti" className="gap-2" data-testid="tab-documenti">
                            <Shield className="h-4 w-4" />
                            Documenti
                        </TabsTrigger>
                        <TabsTrigger value="sicurezza" className="gap-2" data-testid="tab-sicurezza">
                            <Users className="h-4 w-4" />
                            Sicurezza
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
                        {user?.role === 'admin' && (
                            <TabsTrigger value="diagnostica" className="gap-2" data-testid="tab-diagnostica">
                                <Bug className="h-4 w-4" />
                                Diagnostica
                            </TabsTrigger>
                        )}
                    </TabsList>

                    <TabsContent value="company">
                        <CompanyTab settings={settings} updateField={updateField} />
                    </TabsContent>
                    <TabsContent value="bank">
                        <BankTab settings={settings} setSettings={setSettings} />
                    </TabsContent>
                    <TabsContent value="logo">
                        <LogoTab settings={settings} updateField={updateField} />
                    </TabsContent>
                    <TabsContent value="condizioni">
                        <CondizioniTab settings={settings} updateField={updateField} />
                    </TabsContent>
                    <TabsContent value="integrazioni">
                        <IntegrazioniTab settings={settings} updateField={updateField} />
                    </TabsContent>
                    <TabsContent value="certificazioni">
                        <CertificazioniTab settings={settings} updateField={updateField} />
                    </TabsContent>
                    <TabsContent value="migrazione">
                        <MigrazioneTab />
                    </TabsContent>
                    <TabsContent value="backup">
                        <BackupTab />
                    </TabsContent>
                    <TabsContent value="notifiche">
                        <NotificheTab />
                    </TabsContent>
                    <TabsContent value="documenti">
                        <div className="space-y-6">
                            <DocumentiAziendaTab />
                            <div className="border-t border-slate-200 pt-6">
                                <AllegatiPosTab />
                            </div>
                        </div>
                    </TabsContent>
                    <TabsContent value="sicurezza">
                        <FigureAziendaliTab settings={settings} setSettings={setSettings} />
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
                    {user?.role === 'admin' && (
                        <TabsContent value="diagnostica">
                            <DiagnosticaTab />
                        </TabsContent>
                    )}
                </Tabs>
            </div>
        </DashboardLayout>
    );
}
