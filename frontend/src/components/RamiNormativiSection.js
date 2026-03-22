/**
 * RamiNormativiSection — Rami normativi + Emissioni documentali.
 * Mostra la gerarchia: Commessa Madre → Rami → Emissioni.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
    GitBranch, FileOutput, Plus, Shield, Award, Hammer,
    Lock, Unlock, ChevronDown, ChevronRight, Loader2,
    AlertTriangle, CheckCircle2, Clock, Eye,
} from 'lucide-react';
import EmissioneDetailPanel from './EmissioneDetailPanel';

const NORM_CONFIG = {
    EN_1090:  { label: 'EN 1090', color: 'bg-blue-100 text-blue-800 border-blue-300', icon: Shield, accent: 'border-l-blue-500' },
    EN_13241: { label: 'EN 13241', color: 'bg-amber-100 text-amber-800 border-amber-300', icon: Award, accent: 'border-l-amber-500' },
    GENERICA: { label: 'Generica', color: 'bg-slate-100 text-slate-700 border-slate-300', icon: Hammer, accent: 'border-l-slate-400' },
};

const STATO_EMISSIONE = {
    draft:            { label: 'Bozza',          color: 'bg-slate-100 text-slate-600' },
    in_preparazione:  { label: 'In preparazione', color: 'bg-amber-100 text-amber-700' },
    bloccata:         { label: 'Bloccata',        color: 'bg-red-100 text-red-700' },
    emettibile:       { label: 'Emettibile',      color: 'bg-emerald-100 text-emerald-700' },
    emessa:           { label: 'Emessa',           color: 'bg-emerald-200 text-emerald-800' },
    annullata:        { label: 'Annullata',        color: 'bg-slate-200 text-slate-500' },
};

export default function RamiNormativiSection({ commessaId }) {
    const [gerarchia, setGerarchia] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expandedRami, setExpandedRami] = useState({});
    const [newRamoOpen, setNewRamoOpen] = useState(false);
    const [newRamoNorm, setNewRamoNorm] = useState('');
    const [creatingRamo, setCreatingRamo] = useState(false);
    const [newEmOpen, setNewEmOpen] = useState(null); // ramo_id
    const [newEmDesc, setNewEmDesc] = useState('');
    const [creatingEm, setCreatingEm] = useState(false);
    const [gateResult, setGateResult] = useState({}); // emissione_id → gate
    const [checkingGate, setCheckingGate] = useState({});
    const [selectedEmissione, setSelectedEmissione] = useState(null); // {emissione, ramoId}

    const fetchGerarchia = useCallback(async () => {
        try {
            const data = await apiRequest(`/commesse/${commessaId}/gerarchia`);
            setGerarchia(data);
            if (data?.rami?.length > 0) {
                const expanded = {};
                data.rami.forEach(r => { expanded[r.ramo_id] = true; });
                setExpandedRami(expanded);
            }
        } catch {
            // No branches yet — that's fine
            setGerarchia({ rami: [], has_branches: false });
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchGerarchia(); }, [fetchGerarchia]);

    const handleCreateRamo = async () => {
        if (!newRamoNorm) return;
        setCreatingRamo(true);
        try {
            await apiRequest(`/commesse-normative/${commessaId}`, {
                method: 'POST',
                body: JSON.stringify({ normativa: newRamoNorm }),
            });
            toast.success(`Ramo ${newRamoNorm} creato`);
            setNewRamoOpen(false);
            setNewRamoNorm('');
            fetchGerarchia();
        } catch (e) {
            toast.error(e.message || 'Errore creazione ramo');
        } finally {
            setCreatingRamo(false);
        }
    };

    const handleCreateEmissione = async (ramoId) => {
        if (!newEmDesc.trim()) {
            toast.error('Inserisci una descrizione');
            return;
        }
        setCreatingEm(true);
        try {
            const em = await apiRequest(`/emissioni/${ramoId}`, {
                method: 'POST',
                body: JSON.stringify({ descrizione: newEmDesc }),
            });
            toast.success(`Emissione ${em.codice_emissione} creata`);
            setNewEmOpen(null);
            setNewEmDesc('');
            fetchGerarchia();
        } catch (e) {
            toast.error(e.message || 'Errore creazione emissione');
        } finally {
            setCreatingEm(false);
        }
    };

    const handleCheckGate = async (ramoId, emissioneId) => {
        setCheckingGate(prev => ({ ...prev, [emissioneId]: true }));
        try {
            const gate = await apiRequest(`/emissioni/${ramoId}/${emissioneId}/gate`);
            setGateResult(prev => ({ ...prev, [emissioneId]: gate }));
        } catch (e) {
            toast.error(e.message || 'Errore verifica gate');
        } finally {
            setCheckingGate(prev => ({ ...prev, [emissioneId]: false }));
        }
    };

    const toggleRamo = (ramoId) => {
        setExpandedRami(prev => ({ ...prev, [ramoId]: !prev[ramoId] }));
    };

    if (loading) return null;

    const rami = gerarchia?.rami || [];
    const existingNorms = new Set(rami.filter(r => !r.is_virtual).map(r => r.normativa));

    return (
        <Card className="border-gray-200" data-testid="card-rami-normativi">
            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                        <GitBranch className="h-3.5 w-3.5" />
                        Rami Normativi {rami.length > 0 && <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{rami.length}</Badge>}
                    </CardTitle>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 text-[10px] text-white hover:text-white hover:bg-white/10"
                        onClick={() => setNewRamoOpen(true)}
                        data-testid="btn-nuovo-ramo"
                    >
                        <Plus className="h-3 w-3 mr-1" /> Nuovo ramo
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-2">
                {rami.length === 0 && (
                    <p className="text-xs text-slate-400 text-center py-4">
                        Nessun ramo normativo. Crea un ramo per separare i flussi EN 1090 / EN 13241 / Generica.
                    </p>
                )}

                {rami.map(ramo => {
                    const cfg = NORM_CONFIG[ramo.normativa] || NORM_CONFIG.GENERICA;
                    const Icon = cfg.icon;
                    const expanded = expandedRami[ramo.ramo_id];
                    const emissioni = ramo.emissioni || [];

                    return (
                        <div key={ramo.ramo_id || ramo.normativa} className={`border rounded-lg ${cfg.accent} border-l-4`} data-testid={`ramo-${ramo.normativa}`}>
                            {/* Ramo Header */}
                            <button
                                className="w-full flex items-center justify-between p-3 hover:bg-slate-50/50 transition-colors"
                                onClick={() => ramo.ramo_id && toggleRamo(ramo.ramo_id)}
                            >
                                <div className="flex items-center gap-2">
                                    {ramo.ramo_id ? (expanded ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" /> : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />) : <ChevronRight className="h-3.5 w-3.5 text-slate-300" />}
                                    <Icon className="h-4 w-4" />
                                    <span className="text-sm font-medium">{ramo.codice_ramo}</span>
                                    <Badge className={`text-[10px] px-1.5 py-0 ${cfg.color}`}>{cfg.label}</Badge>
                                    {ramo.is_virtual && <Badge variant="outline" className="text-[10px] px-1 py-0 text-slate-400">legacy</Badge>}
                                    {ramo.line_ids?.length > 0 && <span className="text-[10px] text-slate-400">{ramo.line_ids.length} righe</span>}
                                </div>
                                <div className="flex items-center gap-2">
                                    {ramo.n_emissioni > 0 && (
                                        <div className="flex items-center gap-1.5 text-[10px]">
                                            {ramo.n_emesse > 0 && <span className="text-emerald-600">{ramo.n_emesse} emesse</span>}
                                            {ramo.n_bloccate > 0 && <span className="text-red-600">{ramo.n_bloccate} bloccate</span>}
                                            {ramo.n_draft > 0 && <span className="text-slate-400">{ramo.n_draft} bozze</span>}
                                        </div>
                                    )}
                                </div>
                            </button>

                            {/* Emissioni (expanded) */}
                            {expanded && ramo.ramo_id && (
                                <div className="border-t px-3 pb-3 pt-2 space-y-1.5 bg-slate-50/30">
                                    {emissioni.length === 0 && (
                                        <p className="text-[11px] text-slate-400 py-1">Nessuna emissione. Crea la prima quando hai materiali/DDT pronti.</p>
                                    )}
                                    {emissioni.map(em => {
                                        const stCfg = STATO_EMISSIONE[em.stato] || STATO_EMISSIONE.draft;
                                        const gate = gateResult[em.emissione_id] || em.evidence_gate;
                                        const isChecking = checkingGate[em.emissione_id];

                                        return (
                                            <div key={em.emissione_id} className="flex items-center justify-between p-2 bg-white rounded border text-xs cursor-pointer hover:bg-slate-50 transition-colors" data-testid={`emissione-${em.codice_emissione}`}
                                                onClick={() => setSelectedEmissione({ emissione: em, ramoId: ramo.ramo_id })}>
                                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                                    <FileOutput className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                                    <span className="font-mono font-medium">{em.codice_emissione}</span>
                                                    <Badge className={`text-[10px] px-1.5 py-0 ${stCfg.color}`}>{stCfg.label}</Badge>
                                                    {em.descrizione && <span className="text-slate-500 truncate">{em.descrizione}</span>}
                                                </div>
                                                <div className="flex items-center gap-1.5 shrink-0">
                                                    {/* Completion percent bar */}
                                                    {em.last_completion_percent !== undefined && em.last_completion_percent !== null && (
                                                        <div className="flex items-center gap-1">
                                                            <div className="w-12 h-1 bg-slate-200 rounded-full overflow-hidden">
                                                                <div className={`h-full rounded-full ${em.last_completion_percent >= 80 ? 'bg-emerald-500' : em.last_completion_percent >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                                                                    style={{ width: `${em.last_completion_percent}%` }} />
                                                            </div>
                                                            <span className="text-[9px] font-mono text-slate-400">{em.last_completion_percent}%</span>
                                                        </div>
                                                    )}
                                                    {/* Contatori risorse collegate */}
                                                    {(em.batch_ids?.length > 0 || em.ddt_ids?.length > 0) && (
                                                        <span className="text-[10px] text-slate-400">
                                                            {em.batch_ids?.length || 0}B {em.ddt_ids?.length || 0}D
                                                        </span>
                                                    )}
                                                    {/* Evidence Gate button */}
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        className="h-6 px-1.5 text-[10px]"
                                                        onClick={() => handleCheckGate(ramo.ramo_id, em.emissione_id)}
                                                        disabled={isChecking}
                                                        data-testid={`btn-gate-${em.codice_emissione}`}
                                                    >
                                                        {isChecking ? <Loader2 className="h-3 w-3 animate-spin" /> : (
                                                            gate?.emittable ? <Unlock className="h-3 w-3 text-emerald-500" /> : <Lock className="h-3 w-3 text-red-500" />
                                                        )}
                                                    </Button>
                                                </div>
                                            </div>
                                        );
                                    })}

                                    {/* Gate details (if any checked) */}
                                    {emissioni.map(em => {
                                        const gate = gateResult[em.emissione_id];
                                        if (!gate) return null;
                                        return (
                                            <div key={`gate-${em.emissione_id}`} className="p-2.5 rounded border bg-white text-[11px] space-y-2">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-1.5 font-medium">
                                                        <Eye className="h-3 w-3" />
                                                        Evidence Gate: {em.codice_emissione}
                                                        {gate.emittable ? (
                                                            <Badge className="bg-emerald-100 text-emerald-700 text-[10px] px-1 py-0">EMETTIBILE</Badge>
                                                        ) : (
                                                            <Badge className="bg-red-100 text-red-700 text-[10px] px-1 py-0">BLOCCATA</Badge>
                                                        )}
                                                    </div>
                                                    {gate.completion_percent !== undefined && (
                                                        <div className="flex items-center gap-1.5">
                                                            <div className="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                                                <div className={`h-full rounded-full transition-all ${gate.completion_percent >= 80 ? 'bg-emerald-500' : gate.completion_percent >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                                                                    style={{ width: `${gate.completion_percent}%` }} />
                                                            </div>
                                                            <span className="font-mono text-[10px] text-slate-500">{gate.completion_percent}%</span>
                                                        </div>
                                                    )}
                                                </div>
                                                {/* Checks grid */}
                                                {gate.checks && gate.checks.length > 0 && (
                                                    <div className="flex flex-wrap gap-1">
                                                        {gate.checks.map((c) => {
                                                            const isPassing = ['linked', 'uploaded', 'verified'].includes(c.status);
                                                            const isNA = c.status === 'not_applicable';
                                                            return (
                                                                <span key={c.code} className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] ${
                                                                    isNA ? 'bg-slate-50 text-slate-400' :
                                                                    isPassing ? 'bg-emerald-50 text-emerald-700' :
                                                                    'bg-red-50 text-red-700'
                                                                }`} title={c.message}>
                                                                    {isNA ? <Clock className="h-2.5 w-2.5" /> : isPassing ? <CheckCircle2 className="h-2.5 w-2.5" /> : <AlertTriangle className="h-2.5 w-2.5" />}
                                                                    {c.code.replace(/_/g, ' ').toLowerCase()}
                                                                    {c.status === 'uploaded' && <span className="text-[8px] opacity-70">(upload)</span>}
                                                                </span>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                                {/* Blockers */}
                                                {gate.blockers?.length > 0 && (
                                                    <div className="space-y-0.5 border-t pt-1.5">
                                                        <span className="text-[10px] font-medium text-red-600">Blocchi:</span>
                                                        {gate.blockers.map((b, i) => (
                                                            <div key={i} className="flex items-start gap-1 text-red-600">
                                                                <Lock className="h-3 w-3 mt-0.5 shrink-0" />
                                                                <span>{b.message}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                                {/* Warnings */}
                                                {gate.warnings?.length > 0 && (
                                                    <div className="space-y-0.5 border-t pt-1.5">
                                                        <span className="text-[10px] font-medium text-amber-600">Avvisi:</span>
                                                        {gate.warnings.map((w, i) => (
                                                            <div key={i} className="flex items-start gap-1 text-amber-600">
                                                                <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                                                                <span>{w.message}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}

                                    {/* Add emission button */}
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 text-[11px] w-full mt-1"
                                        onClick={() => { setNewEmOpen(ramo.ramo_id); setNewEmDesc(''); }}
                                        data-testid={`btn-nuova-emissione-${ramo.normativa}`}
                                    >
                                        <Plus className="h-3 w-3 mr-1" /> Nuova emissione
                                    </Button>
                                </div>
                            )}
                        </div>
                    );
                })}
            </CardContent>

            {/* Pannello dettaglio emissione */}
            {selectedEmissione && (
                <div className="px-3 pb-3">
                    <EmissioneDetailPanel
                        emissione={selectedEmissione.emissione}
                        ramoId={selectedEmissione.ramoId}
                        onClose={() => setSelectedEmissione(null)}
                        onRefresh={() => { fetchGerarchia(); setSelectedEmissione(null); }}
                    />
                </div>
            )}

            {/* Dialog: Nuovo Ramo */}
            <Dialog open={newRamoOpen} onOpenChange={setNewRamoOpen}>
                <DialogContent className="max-w-sm" data-testid="dialog-nuovo-ramo">
                    <DialogHeader>
                        <DialogTitle className="text-sm">Nuovo Ramo Normativo</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <Select value={newRamoNorm} onValueChange={setNewRamoNorm}>
                            <SelectTrigger data-testid="select-normativa-ramo">
                                <SelectValue placeholder="Seleziona normativa" />
                            </SelectTrigger>
                            <SelectContent>
                                {!existingNorms.has('EN_1090') && <SelectItem value="EN_1090">EN 1090 - Strutture</SelectItem>}
                                {!existingNorms.has('EN_13241') && <SelectItem value="EN_13241">EN 13241 - Chiusure</SelectItem>}
                                {!existingNorms.has('GENERICA') && <SelectItem value="GENERICA">Generica</SelectItem>}
                            </SelectContent>
                        </Select>
                    </div>
                    <DialogFooter>
                        <Button size="sm" variant="outline" onClick={() => setNewRamoOpen(false)}>Annulla</Button>
                        <Button size="sm" onClick={handleCreateRamo} disabled={!newRamoNorm || creatingRamo} data-testid="btn-conferma-ramo">
                            {creatingRamo ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                            Crea ramo
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog: Nuova Emissione */}
            <Dialog open={!!newEmOpen} onOpenChange={() => setNewEmOpen(null)}>
                <DialogContent className="max-w-sm" data-testid="dialog-nuova-emissione">
                    <DialogHeader>
                        <DialogTitle className="text-sm">Nuova Emissione Documentale</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <Input
                            placeholder="Descrizione (es. Prima fornitura travi)"
                            value={newEmDesc}
                            onChange={(e) => setNewEmDesc(e.target.value)}
                            data-testid="input-desc-emissione"
                        />
                        <p className="text-[11px] text-slate-500">
                            L'emissione nasce in bozza. Potrai collegare batch, DDT e documenti in seguito.
                        </p>
                    </div>
                    <DialogFooter>
                        <Button size="sm" variant="outline" onClick={() => setNewEmOpen(null)}>Annulla</Button>
                        <Button size="sm" onClick={() => handleCreateEmissione(newEmOpen)} disabled={creatingEm} data-testid="btn-conferma-emissione">
                            {creatingEm ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                            Crea emissione
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
