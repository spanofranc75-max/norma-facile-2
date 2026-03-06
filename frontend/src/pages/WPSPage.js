/**
 * WPSPage — Welding Procedure Specification management for EN 1090.
 * Auto-suggests WPS parameters and matches qualified welders.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import DashboardLayout from '../components/DashboardLayout';
import { apiRequest } from '../lib/utils';
import { toast } from 'sonner';
import {
    Flame, Plus, Search, Save, Trash2, FileText, Users, ChevronDown, ChevronUp,
    AlertTriangle, CheckCircle, Shield, Thermometer, Droplets,
} from 'lucide-react';
import { useConfirm } from '../components/ConfirmProvider';

export default function WPSPage({ user }) {
    const confirm = useConfirm();
    const [refData, setRefData] = useState(null);
    const [wpsList, setWpsList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showGenerator, setShowGenerator] = useState(false);
    const [suggestion, setSuggestion] = useState(null);
    const [suggesting, setSuggesting] = useState(false);
    const [saving, setSaving] = useState(false);

    const [form, setForm] = useState({
        process: '135', material_group: '1.2', thickness: 10,
        joint_type: 'BW', exec_class: 'EXC2', title: '',
    });

    const loadData = useCallback(async () => {
        try {
            const [ref, list] = await Promise.all([
                apiRequest('/wps/reference-data'),
                apiRequest('/wps/'),
            ]);
            setRefData(ref);
            setWpsList(list.items || []);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleSuggest = async () => {
        setSuggesting(true);
        setSuggestion(null);
        try {
            const params = new URLSearchParams({
                process: form.process, material_group: form.material_group,
                thickness: form.thickness, joint_type: form.joint_type,
                exec_class: form.exec_class,
            });
            const data = await apiRequest(`/wps/suggest?${params}`);
            setSuggestion(data);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSuggesting(false);
        }
    };

    const handleSave = async () => {
        if (!form.title.trim()) { toast.error('Inserisci un titolo per la WPS'); return; }
        setSaving(true);
        try {
            const payload = {
                title: form.title,
                process: form.process,
                material_group: form.material_group,
                base_material: suggestion?.material?.materials?.[0] || null,
                thickness_min: Math.max(1, form.thickness - 5),
                thickness_max: form.thickness + 5,
                joint_type: form.joint_type,
                positions: ['PA'],
                exec_class: form.exec_class,
                filler_material: suggestion?.suggestion?.filler_material || null,
                filler_standard: suggestion?.suggestion?.filler_standard || null,
                shielding_gas: suggestion?.suggestion?.shielding_gas || null,
                preheat_temp: suggestion?.suggestion?.preheat?.temp_min || null,
                interpass_temp_max: suggestion?.suggestion?.interpass?.temp_max || null,
            };
            await apiRequest('/wps/', { method: 'POST', body: payload });
            toast.success('WPS creata con successo');
            setSuggestion(null);
            setShowGenerator(false);
            setForm(f => ({ ...f, title: '' }));
            loadData();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (wpsId) => {
        if (!(await confirm('Eliminare questa WPS?'))) return;
        try {
            await apiRequest(`/wps/${wpsId}`, { method: 'DELETE' });
            toast.success('WPS eliminata');
            loadData();
        } catch (e) {
            toast.error(e.message);
        }
    };

    const handleStatusChange = async (wpsId, newStatus) => {
        try {
            await apiRequest(`/wps/${wpsId}`, { method: 'PUT', body: { status: newStatus } });
            toast.success(`Stato aggiornato: ${newStatus}`);
            loadData();
        } catch (e) {
            toast.error(e.message);
        }
    };

    if (loading) return <DashboardLayout user={user}><div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-[#0055FF] border-t-transparent rounded-full" /></div></DashboardLayout>;

    return (
        <DashboardLayout user={user}>
            <div className="max-w-6xl mx-auto space-y-6" data-testid="wps-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Flame className="h-6 w-6 text-[#0055FF]" /> WPS — Procedure di Saldatura
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">Genera e gestisci le specifiche di saldatura EN 1090</p>
                    </div>
                    <Button
                        data-testid="btn-new-wps"
                        className="bg-[#0055FF] text-white"
                        onClick={() => setShowGenerator(!showGenerator)}
                    >
                        {showGenerator ? <ChevronUp className="h-4 w-4 mr-1" /> : <Plus className="h-4 w-4 mr-1" />}
                        {showGenerator ? 'Chiudi' : 'Nuova WPS'}
                    </Button>
                </div>

                {/* Generator */}
                {showGenerator && (
                    <Card className="border-[#0055FF]/30 shadow-md" data-testid="wps-generator">
                        <CardHeader className="bg-gradient-to-r from-[#0055FF]/5 to-transparent border-b py-3">
                            <CardTitle className="text-sm font-semibold text-[#1E293B]">
                                <Search className="h-4 w-4 inline mr-2 text-[#0055FF]" />
                                Generatore WPS Automatico
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-4 space-y-4">
                            {/* Input row */}
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                <div>
                                    <Label className="text-xs">Processo</Label>
                                    <select data-testid="wps-process" className="w-full border rounded px-2 py-1.5 text-sm bg-white" value={form.process} onChange={e => setForm(f => ({ ...f, process: e.target.value }))}>
                                        {refData && Object.entries(refData.processes).map(([k, v]) => (
                                            <option key={k} value={k}>{k} — {v.short}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <Label className="text-xs">Gruppo Materiale</Label>
                                    <select data-testid="wps-material" className="w-full border rounded px-2 py-1.5 text-sm bg-white" value={form.material_group} onChange={e => setForm(f => ({ ...f, material_group: e.target.value }))}>
                                        {refData && Object.entries(refData.material_groups).map(([k, v]) => (
                                            <option key={k} value={k}>{k} — {v.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <Label className="text-xs">Spessore (mm)</Label>
                                    <Input data-testid="wps-thickness" type="number" min={0.5} step={0.5} value={form.thickness} onChange={e => setForm(f => ({ ...f, thickness: parseFloat(e.target.value) || 1 }))} className="text-sm" />
                                </div>
                                <div>
                                    <Label className="text-xs">Tipo Giunto</Label>
                                    <select data-testid="wps-joint" className="w-full border rounded px-2 py-1.5 text-sm bg-white" value={form.joint_type} onChange={e => setForm(f => ({ ...f, joint_type: e.target.value }))}>
                                        {refData && refData.joint_types.map(jt => (
                                            <option key={jt.code} value={jt.code}>{jt.code} — {jt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <Label className="text-xs">Classe Esecuzione</Label>
                                    <select data-testid="wps-exc" className="w-full border rounded px-2 py-1.5 text-sm bg-white" value={form.exec_class} onChange={e => setForm(f => ({ ...f, exec_class: e.target.value }))}>
                                        {refData && Object.entries(refData.exec_classes).map(([k, v]) => (
                                            <option key={k} value={k}>{k} — {v.description}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <Button data-testid="btn-suggest" onClick={handleSuggest} disabled={suggesting} className="bg-[#0055FF] text-white">
                                    {suggesting ? <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" /> : <Search className="h-4 w-4 mr-1" />}
                                    Genera Suggerimento
                                </Button>
                            </div>

                            {/* Suggestion Result */}
                            {suggestion && (
                                <div className="space-y-4 pt-2 border-t" data-testid="wps-suggestion">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        {/* Filler & Gas */}
                                        <Card className="border-slate-200">
                                            <CardContent className="pt-4 space-y-3">
                                                <h4 className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-1"><Droplets className="h-3.5 w-3.5" /> Materiale d'Apporto</h4>
                                                <div>
                                                    <p className="text-sm font-medium">{suggestion.suggestion.filler_material}</p>
                                                    {suggestion.suggestion.filler_standard && <p className="text-xs text-slate-400">{suggestion.suggestion.filler_standard}</p>}
                                                </div>
                                                {suggestion.suggestion.shielding_gas && (
                                                    <div>
                                                        <p className="text-xs text-slate-500 font-medium">Gas di protezione:</p>
                                                        <p className="text-sm">{suggestion.suggestion.shielding_gas}</p>
                                                    </div>
                                                )}
                                            </CardContent>
                                        </Card>

                                        {/* Temperatures */}
                                        <Card className="border-slate-200">
                                            <CardContent className="pt-4 space-y-3">
                                                <h4 className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-1"><Thermometer className="h-3.5 w-3.5" /> Temperature</h4>
                                                <div>
                                                    <p className="text-xs text-slate-500">Preriscaldo:</p>
                                                    <p className={`text-sm font-medium ${suggestion.suggestion.preheat.temp_min ? 'text-amber-600' : 'text-emerald-600'}`}>
                                                        {suggestion.suggestion.preheat.note}
                                                    </p>
                                                </div>
                                                <div>
                                                    <p className="text-xs text-slate-500">Interpass max:</p>
                                                    <p className="text-sm font-medium">{suggestion.suggestion.interpass.note}</p>
                                                </div>
                                            </CardContent>
                                        </Card>

                                        {/* NDT & Exec Class */}
                                        <Card className="border-slate-200">
                                            <CardContent className="pt-4 space-y-3">
                                                <h4 className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-1"><Shield className="h-3.5 w-3.5" /> Controlli {suggestion.exec_class.code}</h4>
                                                <div>
                                                    <p className="text-xs text-slate-500">CND richiesti:</p>
                                                    <p className="text-sm font-bold text-[#0055FF]">{suggestion.suggestion.ndt_percentage}% dei giunti</p>
                                                </div>
                                                <div>
                                                    <p className="text-xs text-slate-500">Livello controllo:</p>
                                                    <p className="text-sm font-medium capitalize">{suggestion.exec_class.min_process_control}</p>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </div>

                                    {/* Qualified Welders */}
                                    <Card className="border-slate-200">
                                        <CardContent className="pt-4">
                                            <h4 className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-1 mb-3">
                                                <Users className="h-3.5 w-3.5" /> Saldatori Qualificati ({suggestion.qualified_welders.length})
                                            </h4>
                                            {suggestion.qualified_welders.length === 0 ? (
                                                <div className="flex items-center gap-2 text-amber-600 text-sm">
                                                    <AlertTriangle className="h-4 w-4" />
                                                    Nessun saldatore qualificato trovato per questo processo/materiale
                                                </div>
                                            ) : (
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                    {suggestion.qualified_welders.map((w) => (
                                                        <div key={w.welder_id} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-sm" data-testid={`wps-welder-${w.welder_id}`}>
                                                            <CheckCircle className={`h-4 w-4 shrink-0 ${w.qual_status === 'attivo' ? 'text-emerald-500' : 'text-amber-500'}`} />
                                                            <span className="font-medium">{w.name}</span>
                                                            <Badge variant="outline" className="text-[10px]">{w.stamp_id}</Badge>
                                                            <span className="text-xs text-slate-400 ml-auto">
                                                                {w.qual_status === 'in_scadenza' ? `Scade tra ${w.days_until_expiry}gg` : 'Attivo'}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>

                                    {/* Save */}
                                    <div className="flex items-center gap-3 pt-2">
                                        <Input
                                            data-testid="wps-title"
                                            placeholder="Titolo WPS (es. WPS Recinzione S355 MAG)"
                                            value={form.title}
                                            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                                            className="flex-1"
                                        />
                                        <Button data-testid="btn-save-wps" onClick={handleSave} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                                            <Save className="h-4 w-4 mr-1" /> Salva WPS
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* WPS List */}
                <Card data-testid="wps-list">
                    <CardHeader className="bg-slate-50 border-b py-3">
                        <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                            <FileText className="h-4 w-4 text-[#0055FF]" /> WPS Archiviate ({wpsList.length})
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        {wpsList.length === 0 ? (
                            <div className="text-center py-12 text-slate-400">
                                <Flame className="h-10 w-10 mx-auto mb-3 opacity-30" />
                                <p className="text-sm">Nessuna WPS creata. Usa il generatore per creare la prima.</p>
                            </div>
                        ) : (
                            <div className="divide-y">
                                {wpsList.map(wps => {
                                    const proc = refData?.processes?.[wps.process];
                                    const mat = refData?.material_groups?.[wps.material_group];
                                    const statusColors = {
                                        bozza: 'bg-slate-100 text-slate-600',
                                        approvata: 'bg-emerald-100 text-emerald-700',
                                        revisionata: 'bg-amber-100 text-amber-700',
                                        obsoleta: 'bg-red-100 text-red-700',
                                    };
                                    return (
                                        <div key={wps.wps_id} className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 transition-colors" data-testid={`wps-item-${wps.wps_id}`}>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm font-bold text-[#0055FF]">{wps.wps_number}</span>
                                                    <span className="text-sm font-medium truncate">{wps.title}</span>
                                                </div>
                                                <p className="text-xs text-slate-400 mt-0.5">
                                                    {proc?.short || wps.process} | {mat?.label || wps.material_group} | {wps.thickness_min}-{wps.thickness_max}mm | {wps.joint_type} | {wps.exec_class}
                                                </p>
                                            </div>
                                            <select
                                                className="text-xs border rounded px-2 py-1 bg-white"
                                                value={wps.status}
                                                data-testid={`wps-status-${wps.wps_id}`}
                                                onChange={e => handleStatusChange(wps.wps_id, e.target.value)}
                                            >
                                                <option value="bozza">Bozza</option>
                                                <option value="approvata">Approvata</option>
                                                <option value="revisionata">Revisionata</option>
                                                <option value="obsoleta">Obsoleta</option>
                                            </select>
                                            <Badge className={`text-[10px] ${statusColors[wps.status] || statusColors.bozza}`}>{wps.status}</Badge>
                                            <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700 h-7 w-7 p-0" onClick={() => handleDelete(wps.wps_id)} data-testid={`wps-delete-${wps.wps_id}`}>
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
