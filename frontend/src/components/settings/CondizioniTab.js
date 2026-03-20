import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

export default function CondizioniTab({ settings, updateField }) {
    return (
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
                        Questo testo verra aggiunto automaticamente in fondo a tutti i documenti generati.
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}
