/**
 * VerbaliITTPage — Gestione Verbali Initial Type Testing.
 * Qualifica processi: taglio termico/meccanico, foratura, piegatura, punzonatura, raddrizzatura.
 * Filo conduttore: Riesame Tecnico (check itt_processi_qualificati).
 */
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
    RefreshCw, Plus, Trash2, FileText, CheckCircle2, XCircle,
    AlertTriangle, Award, Flame, Link2
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

const PROCESSI = [
    { value: 'taglio_termico', label: 'Taglio Termico' },
    { value: 'taglio_meccanico', label: 'Taglio Meccanico' },
    { value: 'foratura', label: 'Foratura' },
    { value: 'piegatura', label: 'Piegatura' },
    { value: 'punzonatura', label: 'Punzonatura' },
    { value: 'raddrizzatura', label: 'Raddrizzatura' },
];

function fmtDate(d) {
    if (!d) return '';
    const p = d.slice(0, 10).split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
}

function urgenzaBadge(item) {
    if (item.scaduto) return { cls: 'bg-red-600 text-white', label: `Scaduto (${Math.abs(item.giorni_rimasti)}gg)` };
    if (item.in_scadenza) return { cls: 'bg-amber-500 text-white', label: `${item.giorni_rimasti}gg` };
    if (item.giorni_rimasti !== null) return { cls: 'bg-emerald-100 text-emerald-700', label: `${item.giorni_rimasti}gg` };
    return { cls: 'bg-slate-100 text-slate-500', label: '—' };
}

export default function VerbaliITTPage() {
    const [verbali, setVerbali] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({
        processo: '', macchina: '', materiale: '',
        spessore_min_mm: '', spessore_max_mm: '', diametro_mm: '',
        norma_riferimento: 'EN 1090-2',
        data_prova: '', data_scadenza: '',
        esito_globale: false, note: '',
        prove: [],
    });
    const [saving, setSaving] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const d = await apiRequest('/verbali-itt');
            setVerbali(d.verbali || []);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleSave = async () => {
        if (!form.processo || !form.macchina || !form.materiale || !form.data_prova || !form.data_scadenza) {
            toast.error('Compilare tutti i campi obbligatori');
            return;
        }
        setSaving(true);
        try {
            const body = {
                ...form,
                spessore_min_mm: form.spessore_min_mm ? parseFloat(form.spessore_min_mm) : null,
                spessore_max_mm: form.spessore_max_mm ? parseFloat(form.spessore_max_mm) : null,
                diametro_mm: form.diametro_mm ? parseFloat(form.diametro_mm) : null,
            };
            await apiRequest('/verbali-itt', { method: 'POST', body });
            toast.success('Verbale ITT creato');
            setShowForm(false);
            setForm({ processo: '', macchina: '', materiale: '', spessore_min_mm: '', spessore_max_mm: '', diametro_mm: '', norma_riferimento: 'EN 1090-2', data_prova: '', data_scadenza: '', esito_globale: false, note: '', prove: [] });
            fetchData();
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Eliminare questo verbale ITT?')) return;
        try {
            await apiRequest(`/verbali-itt/${id}`, { method: 'DELETE' });
            toast.success('Verbale eliminato');
            fetchData();
        } catch (e) { toast.error(e.message); }
    };

    const handlePdf = async (id, proc) => {
        try {
            await downloadPdfBlob(`/verbali-itt/${id}/pdf`, `Verbale_ITT_${proc}.pdf`);
        } catch (e) { toast.error(e.message); }
    };

    const addProva = () => {
        setForm(f => ({ ...f, prove: [...f.prove, { parametro: '', valore_atteso: '', valore_misurato: '', conforme: true }] }));
    };
    const updateProva = (idx, field, val) => {
        setForm(f => {
            const prove = [...f.prove];
            prove[idx] = { ...prove[idx], [field]: val };
            return { ...f, prove };
        });
    };
    const removeProva = (idx) => {
        setForm(f => ({ ...f, prove: f.prove.filter((_, i) => i !== idx) }));
    };

    // KPI
    const validi = verbali.filter(v => v.esito_globale && !v.scaduto);
    const scaduti = verbali.filter(v => v.scaduto);
    const processiCoperti = [...new Set(validi.map(v => v.processo))];

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="verbali-itt-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                            Verbali ITT
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Initial Type Testing — Qualifica processi produttivi EN 1090-2
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={fetchData} className="border-slate-200 text-slate-600">
                            <RefreshCw className="h-4 w-4 mr-1.5" /> Aggiorna
                        </Button>
                        <Button size="sm" onClick={() => setShowForm(!showForm)}
                            className="bg-slate-800 text-white hover:bg-slate-900" data-testid="btn-nuovo-itt">
                            <Plus className="h-4 w-4 mr-1.5" /> Nuovo ITT
                        </Button>
                    </div>
                </div>

                {/* Filo conduttore alert */}
                <Card className="border-indigo-200 bg-indigo-50/50">
                    <CardContent className="p-3 flex items-start gap-3">
                        <Link2 className="h-5 w-5 text-indigo-600 shrink-0 mt-0.5" />
                        <div>
                            <p className="text-sm font-semibold text-indigo-800">Filo Conduttore: Riesame Tecnico</p>
                            <p className="text-xs text-indigo-600 mt-0.5">
                                Il Riesame Tecnico verifica automaticamente che i processi di taglio termico, taglio meccanico
                                e foratura siano qualificati con ITT validi. Senza ITT, la produzione non puo partire.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* KPI */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <Award className="h-4 w-4 text-slate-600" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Totale</span>
                            </div>
                            <p className="text-2xl font-bold text-slate-800 font-mono" data-testid="kpi-totale">{verbali.length}</p>
                        </CardContent>
                    </Card>
                    <Card className="border-emerald-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Validi</span>
                            </div>
                            <p className="text-2xl font-bold text-emerald-700 font-mono" data-testid="kpi-validi">{validi.length}</p>
                        </CardContent>
                    </Card>
                    <Card className={scaduti.length > 0 ? 'border-red-200' : 'border-slate-200'}>
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <AlertTriangle className={`h-4 w-4 ${scaduti.length > 0 ? 'text-red-600' : 'text-slate-400'}`} />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Scaduti</span>
                            </div>
                            <p className={`text-2xl font-bold font-mono ${scaduti.length > 0 ? 'text-red-600' : 'text-slate-800'}`} data-testid="kpi-scaduti">{scaduti.length}</p>
                        </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                        <CardContent className="p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <Flame className="h-4 w-4 text-indigo-600" />
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Processi Coperti</span>
                            </div>
                            <p className="text-2xl font-bold text-indigo-700 font-mono" data-testid="kpi-processi">{processiCoperti.length}/6</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Form */}
                {showForm && (
                    <Card className="border-slate-300 shadow-sm" data-testid="form-nuovo-itt">
                        <CardContent className="p-4 space-y-3">
                            <h3 className="text-sm font-bold text-slate-800">Nuovo Verbale ITT</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Processo *</Label>
                                    <Select value={form.processo} onValueChange={v => setForm(f => ({ ...f, processo: v }))}>
                                        <SelectTrigger className="h-8 text-xs" data-testid="select-processo"><SelectValue placeholder="Scegli..." /></SelectTrigger>
                                        <SelectContent>
                                            {PROCESSI.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Macchina *</Label>
                                    <Input value={form.macchina} onChange={e => setForm(f => ({ ...f, macchina: e.target.value }))}
                                        placeholder="es. Sega MEP" className="h-8 text-xs" data-testid="input-macchina" />
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Materiale *</Label>
                                    <Input value={form.materiale} onChange={e => setForm(f => ({ ...f, materiale: e.target.value }))}
                                        placeholder="es. S275JR" className="h-8 text-xs" data-testid="input-materiale" />
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Norma Rif.</Label>
                                    <Input value={form.norma_riferimento} onChange={e => setForm(f => ({ ...f, norma_riferimento: e.target.value }))}
                                        className="h-8 text-xs" />
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Spessore Min (mm)</Label>
                                    <Input type="number" step="0.1" value={form.spessore_min_mm} onChange={e => setForm(f => ({ ...f, spessore_min_mm: e.target.value }))}
                                        className="h-8 text-xs" />
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Spessore Max (mm)</Label>
                                    <Input type="number" step="0.1" value={form.spessore_max_mm} onChange={e => setForm(f => ({ ...f, spessore_max_mm: e.target.value }))}
                                        className="h-8 text-xs" />
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Data Prova *</Label>
                                    <Input type="date" value={form.data_prova} onChange={e => setForm(f => ({ ...f, data_prova: e.target.value }))}
                                        className="h-8 text-xs" data-testid="input-data-prova" />
                                </div>
                                <div>
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Scadenza *</Label>
                                    <Input type="date" value={form.data_scadenza} onChange={e => setForm(f => ({ ...f, data_scadenza: e.target.value }))}
                                        className="h-8 text-xs" data-testid="input-data-scadenza" />
                                </div>
                            </div>

                            {/* Prove */}
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <Label className="text-[10px] text-slate-500 uppercase tracking-wider">Prove Effettuate</Label>
                                    <Button variant="ghost" size="sm" onClick={addProva} className="text-xs text-slate-600 h-6 px-2" data-testid="btn-add-prova">
                                        <Plus className="h-3 w-3 mr-1" /> Aggiungi Prova
                                    </Button>
                                </div>
                                {form.prove.map((p, idx) => (
                                    <div key={idx} className="grid grid-cols-5 gap-2 mb-1.5 items-center">
                                        <Input value={p.parametro} onChange={e => updateProva(idx, 'parametro', e.target.value)}
                                            placeholder="Parametro" className="h-7 text-xs" />
                                        <Input value={p.valore_atteso} onChange={e => updateProva(idx, 'valore_atteso', e.target.value)}
                                            placeholder="Val. atteso" className="h-7 text-xs" />
                                        <Input value={p.valore_misurato} onChange={e => updateProva(idx, 'valore_misurato', e.target.value)}
                                            placeholder="Val. misurato" className="h-7 text-xs" />
                                        <Select value={p.conforme ? 'si' : 'no'} onValueChange={v => updateProva(idx, 'conforme', v === 'si')}>
                                            <SelectTrigger className="h-7 text-xs"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="si">Conforme</SelectItem>
                                                <SelectItem value="no">Non conforme</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <Button variant="ghost" size="sm" onClick={() => removeProva(idx)} className="h-7 w-7 p-0 text-red-400 hover:text-red-600">
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                ))}
                            </div>

                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" checked={form.esito_globale}
                                        onChange={e => setForm(f => ({ ...f, esito_globale: e.target.checked }))}
                                        className="rounded border-slate-300" data-testid="check-esito" />
                                    <span className="text-xs font-medium text-slate-700">Esito globale: CONFORME</span>
                                </label>
                            </div>

                            <Textarea value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                                placeholder="Note..." className="text-xs h-16" />

                            <div className="flex gap-2 justify-end">
                                <Button variant="outline" size="sm" onClick={() => setShowForm(false)} className="text-xs">Annulla</Button>
                                <Button size="sm" onClick={handleSave} disabled={saving}
                                    className="bg-slate-800 text-white hover:bg-slate-900 text-xs" data-testid="btn-salva-itt">
                                    {saving ? 'Salvataggio...' : 'Salva Verbale'}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Table */}
                <Card className="border-slate-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-700">
                                    <TableHead className="text-white text-[11px] font-semibold">Processo</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Macchina</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Materiale</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Spessore</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Data Prova</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Scadenza</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Esito</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Stato</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[80px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {verbali.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={9} className="text-center py-10 text-slate-400 text-sm">
                                            Nessun verbale ITT registrato. Clicca "Nuovo ITT" per iniziare.
                                        </TableCell>
                                    </TableRow>
                                ) : verbali.map((v, idx) => {
                                    const ub = urgenzaBadge(v);
                                    const spess = v.spessore_min_mm != null && v.spessore_max_mm != null
                                        ? `${v.spessore_min_mm}-${v.spessore_max_mm} mm`
                                        : v.spessore_min_mm != null ? `${v.spessore_min_mm} mm` : '—';
                                    return (
                                        <TableRow key={v.itt_id}
                                            className={`${v.scaduto ? 'bg-red-50/50' : (idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50')} hover:bg-blue-50/40 transition-colors`}
                                            data-testid={`itt-row-${v.itt_id}`}
                                        >
                                            <TableCell>
                                                <Badge variant="outline" className="text-[10px] px-1.5 border-slate-200 text-slate-700">
                                                    {(v.processo || '').replace(/_/g, ' ')}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-xs text-slate-700">{v.macchina}</TableCell>
                                            <TableCell className="text-xs text-slate-600">{v.materiale}</TableCell>
                                            <TableCell className="text-xs text-slate-600 font-mono">{spess}</TableCell>
                                            <TableCell className="text-xs text-slate-600">{fmtDate(v.data_prova)}</TableCell>
                                            <TableCell className="text-xs font-medium text-slate-700">{fmtDate(v.data_scadenza)}</TableCell>
                                            <TableCell>
                                                {v.esito_globale
                                                    ? <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                                    : <XCircle className="h-4 w-4 text-red-500" />
                                                }
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={`text-[10px] px-1.5 py-0.5 ${ub.cls}`}>{ub.label}</Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex gap-1">
                                                    <Button variant="ghost" size="sm" onClick={() => handlePdf(v.itt_id, v.processo)}
                                                        className="h-7 w-7 p-0 text-slate-400 hover:text-slate-700" title="Scarica PDF"
                                                        data-testid={`pdf-btn-${v.itt_id}`}>
                                                        <FileText className="h-3.5 w-3.5" />
                                                    </Button>
                                                    <Button variant="ghost" size="sm" onClick={() => handleDelete(v.itt_id)}
                                                        className="h-7 w-7 p-0 text-slate-400 hover:text-red-600" title="Elimina"
                                                        data-testid={`del-btn-${v.itt_id}`}>
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>
                </Card>
            </div>
        </DashboardLayout>
    );
}
