import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

export default function CertificazioniTab({ settings, updateField }) {
    return (
        <>
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
        </>
    );
}
