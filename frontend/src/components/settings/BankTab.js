import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { CreditCard, Trash2 } from 'lucide-react';

export default function BankTab({ settings, setSettings }) {
    return (
        <>
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
        </>
    );
}
