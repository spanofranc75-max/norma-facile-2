import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Upload, X } from 'lucide-react';
import { toast } from 'sonner';

export default function LogoTab({ settings, updateField }) {
    return (
        <>
            <Card className="border-gray-200">
                <CardHeader className="bg-blue-50 border-b border-gray-200">
                    <CardTitle>Logo Aziendale</CardTitle>
                    <CardDescription>
                        Il logo verra mostrato nella sidebar e nell'intestazione dei documenti PDF
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
                                        toast.error('Il file e troppo grande (max 500KB)');
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
                    <CardDescription>Immagine della firma che verra inserita automaticamente nei PDF generati (Fascicolo Tecnico, DOP, ecc.)</CardDescription>
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
                                            toast.error('Il file e troppo grande (max 500KB)');
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
        </>
    );
}
