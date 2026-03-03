/**
 * FinancialSettingsPage — Company Cost Configuration.
 * The "Magic Number": your real hourly cost including everything.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Save, Calculator, Users, Building2, FileText, AlertTriangle } from 'lucide-react';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

export default function FinancialSettingsPage() {
    const [data, setData] = useState(null);
    const [form, setForm] = useState({
        stipendi_lordi: 0,
        contributi_inps_inail: 0,
        affitto_utenze: 0,
        commercialista_software: 0,
        altri_costi_fissi: 0,
        ore_lavorabili_anno: 1600,
        n_dipendenti: 1,
    });
    const [saving, setSaving] = useState(false);

    const fetch = useCallback(async () => {
        try {
            const d = await apiRequest('/costs/company-costs');
            setData(d);
            setForm({
                stipendi_lordi: d.stipendi_lordi || 0,
                contributi_inps_inail: d.contributi_inps_inail || 0,
                affitto_utenze: d.affitto_utenze || 0,
                commercialista_software: d.commercialista_software || 0,
                altri_costi_fissi: d.altri_costi_fissi || 0,
                ore_lavorabili_anno: d.ore_lavorabili_anno || 1600,
                n_dipendenti: d.n_dipendenti || 1,
            });
        } catch { /* silent */ }
    }, []);

    useEffect(() => { fetch(); }, [fetch]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const result = await apiRequest('/costs/company-costs', { method: 'PUT', body: form });
            setData(result);
            toast.success(`Costo orario aggiornato: ${fmtEur(result.costo_orario_pieno)}/ora`);
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const setField = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

    // Live calculation
    const costoPersonale = (form.stipendi_lordi || 0) + (form.contributi_inps_inail || 0);
    const speseGenerali = (form.affitto_utenze || 0) + (form.commercialista_software || 0) + (form.altri_costi_fissi || 0);
    const costoTotale = costoPersonale + speseGenerali;
    const oreLavorabili = form.ore_lavorabili_anno || 1;
    const costoOrario = costoTotale / oreLavorabili;

    return (
        <DashboardLayout>
            <div className="space-y-6 max-w-4xl" data-testid="financial-settings-page">
                {/* Header */}
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Configurazione Finanziaria</h1>
                    <p className="text-sm text-slate-500 mt-0.5">Calcola il costo orario reale della tua azienda</p>
                </div>

                {/* THE MAGIC NUMBER */}
                <Card className="border-2 border-slate-800 bg-slate-900 text-white overflow-hidden" data-testid="magic-number-card">
                    <CardContent className="p-8 text-center">
                        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Il Tuo Costo Orario Reale</p>
                        <p className="text-6xl font-black font-mono tracking-tight" data-testid="hourly-cost-display">
                            {fmtEur(costoOrario)}
                            <span className="text-2xl font-normal text-slate-400">/ora</span>
                        </p>
                        <div className="flex items-center justify-center gap-1 mt-3">
                            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                            <p className="text-xs text-slate-400">Se vendi a meno di questo, perdi soldi.</p>
                        </div>
                        <div className="flex justify-center gap-8 mt-5 pt-4 border-t border-slate-700">
                            <div>
                                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Costo Annuo</p>
                                <p className="text-lg font-bold font-mono">{fmtEur(costoTotale)}</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Personale</p>
                                <p className="text-lg font-bold font-mono text-blue-400">{fmtEur(costoPersonale)}</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Overhead</p>
                                <p className="text-lg font-bold font-mono text-amber-400">{fmtEur(speseGenerali)}</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Ore/Anno</p>
                                <p className="text-lg font-bold font-mono">{oreLavorabili.toLocaleString('it-IT')}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Left: Personale */}
                    <Card className="border-slate-200">
                        <CardContent className="p-5 space-y-4">
                            <div className="flex items-center gap-2 mb-1">
                                <Users className="h-4 w-4 text-blue-500" />
                                <h2 className="text-sm font-bold text-slate-700">Costi Personale (Annuali)</h2>
                            </div>
                            <div>
                                <Label className="text-xs text-slate-500">Stipendi Lordi Totali</Label>
                                <Input
                                    type="number" step="100" min="0"
                                    value={form.stipendi_lordi || ''}
                                    onChange={e => setField('stipendi_lordi', parseFloat(e.target.value) || 0)}
                                    data-testid="input-stipendi"
                                    className="font-mono"
                                    placeholder="es. 80000"
                                />
                            </div>
                            <div>
                                <Label className="text-xs text-slate-500">Contributi INPS / INAIL</Label>
                                <Input
                                    type="number" step="100" min="0"
                                    value={form.contributi_inps_inail || ''}
                                    onChange={e => setField('contributi_inps_inail', parseFloat(e.target.value) || 0)}
                                    data-testid="input-contributi"
                                    className="font-mono"
                                    placeholder="es. 25000"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Label className="text-xs text-slate-500">N. Dipendenti</Label>
                                    <Input
                                        type="number" min="1" max="100"
                                        value={form.n_dipendenti || ''}
                                        onChange={e => setField('n_dipendenti', parseInt(e.target.value) || 1)}
                                        data-testid="input-dipendenti"
                                        className="font-mono"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs text-slate-500">Ore Lavorabili / Anno</Label>
                                    <Input
                                        type="number" min="100" max="50000" step="100"
                                        value={form.ore_lavorabili_anno || ''}
                                        onChange={e => setField('ore_lavorabili_anno', parseInt(e.target.value) || 1600)}
                                        data-testid="input-ore"
                                        className="font-mono"
                                        placeholder="es. 3200"
                                    />
                                    <p className="text-[10px] text-slate-400 mt-1">{form.n_dipendenti || 1} dip. x ~{Math.round((form.ore_lavorabili_anno || 1600) / (form.n_dipendenti || 1))} ore/dip.</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Right: Overhead */}
                    <Card className="border-slate-200">
                        <CardContent className="p-5 space-y-4">
                            <div className="flex items-center gap-2 mb-1">
                                <Building2 className="h-4 w-4 text-amber-500" />
                                <h2 className="text-sm font-bold text-slate-700">Spese Generali (Annuali)</h2>
                            </div>
                            <div>
                                <Label className="text-xs text-slate-500">Affitto + Utenze (Luce, Gas, Acqua)</Label>
                                <Input
                                    type="number" step="100" min="0"
                                    value={form.affitto_utenze || ''}
                                    onChange={e => setField('affitto_utenze', parseFloat(e.target.value) || 0)}
                                    data-testid="input-affitto"
                                    className="font-mono"
                                    placeholder="es. 18000"
                                />
                            </div>
                            <div>
                                <Label className="text-xs text-slate-500">Commercialista + Software</Label>
                                <Input
                                    type="number" step="100" min="0"
                                    value={form.commercialista_software || ''}
                                    onChange={e => setField('commercialista_software', parseFloat(e.target.value) || 0)}
                                    data-testid="input-commercialista"
                                    className="font-mono"
                                    placeholder="es. 6000"
                                />
                            </div>
                            <div>
                                <Label className="text-xs text-slate-500">Altri Costi Fissi (Assicuraz., Auto, ecc.)</Label>
                                <Input
                                    type="number" step="100" min="0"
                                    value={form.altri_costi_fissi || ''}
                                    onChange={e => setField('altri_costi_fissi', parseFloat(e.target.value) || 0)}
                                    data-testid="input-altri"
                                    className="font-mono"
                                    placeholder="es. 8000"
                                />
                            </div>
                            <div className="pt-2 border-t border-slate-100">
                                <div className="flex justify-between text-xs">
                                    <span className="text-slate-500">Totale Overhead</span>
                                    <span className="font-bold font-mono text-amber-600">{fmtEur(speseGenerali)}</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Save */}
                <div className="flex justify-end">
                    <Button onClick={handleSave} disabled={saving} data-testid="btn-save-costs" className="bg-slate-800 hover:bg-slate-700 text-white">
                        {saving ? 'Salvataggio...' : <><Save className="h-4 w-4 mr-1.5" /> Salva Configurazione</>}
                    </Button>
                </div>

                {/* Simulation */}
                <Card className="border-slate-200 bg-slate-50">
                    <CardContent className="p-5">
                        <div className="flex items-center gap-2 mb-3">
                            <Calculator className="h-4 w-4 text-slate-500" />
                            <h2 className="text-sm font-bold text-slate-700">Come si calcola</h2>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-center">
                            <div className="bg-white rounded-lg p-3 border border-slate-200">
                                <p className="text-[10px] text-slate-400 uppercase mb-1">Costo Totale Annuo</p>
                                <p className="text-sm font-bold font-mono">{fmtEur(costoTotale)}</p>
                                <p className="text-[10px] text-slate-400 mt-1">Personale + Overhead</p>
                            </div>
                            <div className="flex items-center justify-center text-slate-300 text-2xl font-light">/</div>
                            <div className="bg-white rounded-lg p-3 border border-slate-200">
                                <p className="text-[10px] text-slate-400 uppercase mb-1">Ore Lavorabili</p>
                                <p className="text-sm font-bold font-mono">{oreLavorabili.toLocaleString('it-IT')} h</p>
                                <p className="text-[10px] text-slate-400 mt-1">{form.n_dipendenti} dip. operativi</p>
                            </div>
                        </div>
                        <div className="text-center mt-3 pt-3 border-t border-slate-200">
                            <p className="text-[10px] text-slate-400 uppercase">= Costo Orario Pieno</p>
                            <p className="text-3xl font-black font-mono text-slate-800">{fmtEur(costoOrario)}<span className="text-sm font-normal text-slate-400">/ora</span></p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
