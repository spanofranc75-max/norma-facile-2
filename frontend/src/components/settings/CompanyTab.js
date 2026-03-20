import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

export default function CompanyTab({ settings, updateField }) {
    return (
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
                        <Label htmlFor="city">Citta</Label>
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
    );
}
