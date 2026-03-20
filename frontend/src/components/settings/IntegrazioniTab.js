import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

export default function IntegrazioniTab({ settings, updateField }) {
    return (
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
                    Trova le credenziali in Fatture in Cloud &rarr; Impostazioni &rarr; Applicazioni collegate &rarr; Token.
                    Le credenziali vengono salvate in modo sicuro nel database.
                </p>
            </CardContent>
        </Card>
    );
}
