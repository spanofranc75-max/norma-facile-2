/**
 * Diario di Produzione — Registro lavoro integrato nelle fasi.
 * Ogni fase è espandibile e mostra le sessioni di lavoro.
 * Supporta: più giornate, più operatori per sessione, tracciamento ore.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Trash2, Clock, Users, BarChart3, Edit2, ChevronDown, ChevronRight, Play, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const FASE_COLORS = {
    taglio: { bg: 'bg-red-50 border-red-200', badge: 'bg-red-100 text-red-700', bar: 'bg-red-500' },
    foratura: { bg: 'bg-orange-50 border-orange-200', badge: 'bg-orange-100 text-orange-700', bar: 'bg-orange-500' },
    assemblaggio: { bg: 'bg-blue-50 border-blue-200', badge: 'bg-blue-100 text-blue-700', bar: 'bg-blue-500' },
    saldatura: { bg: 'bg-amber-50 border-amber-200', badge: 'bg-amber-100 text-amber-700', bar: 'bg-amber-500' },
    pulizia: { bg: 'bg-teal-50 border-teal-200', badge: 'bg-teal-100 text-teal-700', bar: 'bg-teal-500' },
    preparazione_superfici: { bg: 'bg-purple-50 border-purple-200', badge: 'bg-purple-100 text-purple-700', bar: 'bg-purple-500' },
};

const StatoBadge = ({ stato }) => {
    const styles = {
        da_fare: 'bg-slate-100 text-slate-600',
        in_corso: 'bg-blue-100 text-blue-700',
        completato: 'bg-emerald-100 text-emerald-700',
    };
    const labels = { da_fare: 'Da fare', in_corso: 'In corso', completato: 'Completato' };
    return <Badge className={`text-[9px] px-1.5 py-0 ${styles[stato] || styles.da_fare}`}>{labels[stato] || stato}</Badge>;
};

export default function DiarioProduzione({ commessaId, fasi = [], onUpdateFase, onRefresh }) {
    const [entries, setEntries] = useState([]);
    const [riepilogo, setRiepilogo] = useState(null);
    const [teamMembers, setTeamMembers] = useState([]);
    const [expandedFasi, setExpandedFasi] = useState({});
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editEntry, setEditEntry] = useState(null);
    const [targetFase, setTargetFase] = useState(null);
    const [form, setForm] = useState({ data: '', ore: '', operatoriIds: [], note: '' });
    const [loading, setLoading] = useState(false);
    const [showRiepilogo, setShowRiepilogo] = useState(false);

    const fetchEntries = useCallback(async () => {
        try {
            const res = await apiRequest(`/commesse/${commessaId}/diario`);
            setEntries(res.entries || []);
        } catch (e) { console.error(e); }
    }, [commessaId]);

    const fetchRiepilogo = useCallback(async () => {
        try {
            const res = await apiRequest(`/commesse/${commessaId}/diario/riepilogo`);
            setRiepilogo(res);
        } catch (e) { console.error(e); }
    }, [commessaId]);

    const fetchTeam = useCallback(async () => {
        try {
            const res = await apiRequest('/team/members');
            setTeamMembers((res.members || []).filter(m => m.role !== 'guest'));
        } catch (e) { console.error(e); }
    }, []);

    useEffect(() => { fetchEntries(); fetchRiepilogo(); fetchTeam(); }, [fetchEntries, fetchRiepilogo, fetchTeam]);

    const entriesByFase = (faseTipo) => entries.filter(e => e.fase === faseTipo).sort((a, b) => b.data.localeCompare(a.data));

    const totalOreFase = (faseTipo) => {
        return entries.filter(e => e.fase === faseTipo).reduce((s, e) => s + (e.ore_totali || e.ore || 0), 0);
    };

    const toggleExpand = (tipo) => setExpandedFasi(prev => ({ ...prev, [tipo]: !prev[tipo] }));

    const openNewSession = (fase) => {
        setEditEntry(null);
        setTargetFase(fase);
        setForm({ data: new Date().toISOString().split('T')[0], ore: '', operatoriIds: [], note: '' });
        setDialogOpen(true);
    };

    const openEditSession = (entry) => {
        setEditEntry(entry);
        setTargetFase({ tipo: entry.fase });
        const ids = (entry.operatori || []).map(o => o.id);
        setForm({ data: entry.data, ore: String(entry.ore), operatoriIds: ids, note: entry.note || '' });
        setDialogOpen(true);
    };

    const toggleOperatore = (userId) => {
        setForm(f => {
            const ids = f.operatoriIds.includes(userId)
                ? f.operatoriIds.filter(id => id !== userId)
                : [...f.operatoriIds, userId];
            return { ...f, operatoriIds: ids };
        });
    };

    const handleSave = async () => {
        if (!form.ore || form.operatoriIds.length === 0 || !targetFase) return;
        setLoading(true);
        try {
            const operatori = form.operatoriIds.map(id => {
                const m = teamMembers.find(t => t.user_id === id);
                return { id, nome: m?.name || m?.email || '' };
            });
            const payload = {
                data: form.data,
                fase: targetFase.tipo,
                ore: parseFloat(form.ore),
                operatori,
                note: form.note,
            };
            if (editEntry) {
                await apiRequest(`/commesse/${commessaId}/diario/${editEntry.entry_id}`, {
                    method: 'PUT', body: JSON.stringify(payload),
                });
                toast.success('Sessione aggiornata');
            } else {
                await apiRequest(`/commesse/${commessaId}/diario`, {
                    method: 'POST', body: JSON.stringify(payload),
                });
                toast.success('Sessione registrata');
            }
            setDialogOpen(false);
            fetchEntries();
            fetchRiepilogo();
        } catch (e) { toast.error(e.message); }
        setLoading(false);
    };

    const handleDelete = async (entryId) => {
        if (!window.confirm('Eliminare questa sessione di lavoro?')) return;
        try {
            await apiRequest(`/commesse/${commessaId}/diario/${entryId}`, { method: 'DELETE' });
            toast.success('Sessione eliminata');
            fetchEntries();
            fetchRiepilogo();
        } catch (e) { toast.error(e.message); }
    };

    const handleStartFase = async (tipo) => {
        if (onUpdateFase) await onUpdateFase(tipo, 'in_corso');
    };

    const handleCompleteFase = async (tipo) => {
        if (onUpdateFase) await onUpdateFase(tipo, 'completato', { completed_at: new Date().toISOString() });
    };

    const handleOrePreventivate = async (faseTipo, ore) => {
        try {
            await apiRequest(`/commesse/${commessaId}/produzione/${faseTipo}/ore-preventivate`, {
                method: 'PUT', body: JSON.stringify({ ore_preventivate: parseFloat(ore) || 0 }),
            });
            fetchRiepilogo();
            if (onRefresh) onRefresh();
        } catch (e) { console.error(e); }
    };

    return (
        <div className="space-y-3" data-testid="diario-produzione">
            {/* Phase cards */}
            {fasi.map(f => {
                const colors = FASE_COLORS[f.tipo] || FASE_COLORS.taglio;
                const isExpanded = expandedFasi[f.tipo];
                const faseEntries = entriesByFase(f.tipo);
                const totOre = totalOreFase(f.tipo);
                const orePrev = f.ore_preventivate || 0;
                const isOver = orePrev > 0 && totOre > orePrev;
                const pct = orePrev > 0 ? Math.min((totOre / orePrev) * 100, 100) : 0;

                return (
                    <div key={f.tipo} className={`rounded-lg border ${colors.bg} overflow-hidden`} data-testid={`fase-card-${f.tipo}`}>
                        {/* Phase header */}
                        <div
                            className="flex items-center gap-2 p-3 cursor-pointer select-none"
                            onClick={() => toggleExpand(f.tipo)}
                        >
                            {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
                            <span className="font-semibold text-sm flex-1">{f.label || f.tipo}</span>

                            {/* Hours progress */}
                            {totOre > 0 && (
                                <div className="flex items-center gap-1.5 mr-2">
                                    <Clock className="h-3 w-3 text-slate-400" />
                                    <span className={`text-xs font-mono font-bold ${isOver ? 'text-red-600' : 'text-slate-700'}`}>
                                        {totOre}h
                                    </span>
                                    {orePrev > 0 && (
                                        <>
                                            <span className="text-[10px] text-slate-400">/ {orePrev}h</span>
                                            <div className="w-16 bg-slate-200 rounded-full h-1.5">
                                                <div className={`h-1.5 rounded-full ${isOver ? 'bg-red-500' : colors.bar}`} style={{ width: `${pct}%` }} />
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {faseEntries.length > 0 && (
                                <span className="text-[10px] text-slate-400 mr-1">{faseEntries.length} sessioni</span>
                            )}

                            <StatoBadge stato={f.stato} />

                            {/* Action buttons */}
                            <div className="flex gap-1 ml-1" onClick={e => e.stopPropagation()}>
                                {f.stato === 'da_fare' && (
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-blue-600 hover:bg-blue-100" onClick={() => handleStartFase(f.tipo)} data-testid={`fase-avvia-${f.tipo}`}>
                                        <Play className="h-3 w-3 mr-0.5" /> Avvia
                                    </Button>
                                )}
                                {(f.stato === 'in_corso' || f.stato === 'da_fare') && (
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-emerald-600 hover:bg-emerald-100" onClick={() => openNewSession(f)} data-testid={`fase-registra-${f.tipo}`}>
                                        <Plus className="h-3 w-3 mr-0.5" /> Registra Lavoro
                                    </Button>
                                )}
                                {f.stato === 'in_corso' && (
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-emerald-700 hover:bg-emerald-100" onClick={() => handleCompleteFase(f.tipo)} data-testid={`fase-completa-${f.tipo}`}>
                                        <CheckCircle2 className="h-3 w-3 mr-0.5" /> Completa
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Expanded: work sessions */}
                        {isExpanded && (
                            <div className="px-3 pb-3 space-y-2">
                                {/* Ore preventivate inline */}
                                <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
                                    <span>Ore preventivate:</span>
                                    <Input
                                        type="number"
                                        className="h-6 w-20 text-[11px] text-center"
                                        value={f.ore_preventivate || ''}
                                        placeholder="—"
                                        onBlur={e => handleOrePreventivate(f.tipo, e.target.value)}
                                        onChange={() => {}}
                                        data-testid={`ore-prev-${f.tipo}`}
                                    />
                                    <span>h</span>
                                    {f.data_prevista && (
                                        <span className="ml-auto">Scadenza: {new Date(f.data_prevista).toLocaleDateString('it-IT')}</span>
                                    )}
                                </div>

                                {faseEntries.length === 0 ? (
                                    <p className="text-xs text-slate-400 italic py-3 text-center">
                                        Nessuna sessione registrata. Clicca "Registra Lavoro" per iniziare.
                                    </p>
                                ) : (
                                    <div className="space-y-1.5">
                                        {faseEntries.map(e => (
                                            <div key={e.entry_id} className="flex items-start gap-2 p-2 bg-white/70 rounded border border-white text-xs" data-testid={`sessione-${e.entry_id}`}>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-0.5">
                                                        <span className="font-medium text-slate-700">
                                                            {new Date(e.data + 'T00:00').toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })}
                                                        </span>
                                                        <span className="font-bold text-slate-800">
                                                            <Clock className="h-3 w-3 inline mr-0.5" />{e.ore}h
                                                        </span>
                                                        {(e.operatori || []).length > 1 && (
                                                            <span className="text-[10px] text-slate-400">
                                                                ({e.ore_totali || e.ore}h persona)
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-1 flex-wrap">
                                                        <Users className="h-3 w-3 text-slate-400 shrink-0" />
                                                        {(e.operatori || []).map((op, i) => (
                                                            <Badge key={i} variant="secondary" className="text-[9px] px-1 py-0 bg-slate-100">
                                                                {op.nome}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                    {e.note && <p className="text-[10px] text-slate-400 mt-0.5 italic">{e.note}</p>}
                                                </div>
                                                <div className="flex gap-0.5 shrink-0">
                                                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => openEditSession(e)}>
                                                        <Edit2 className="h-3 w-3 text-slate-400" />
                                                    </Button>
                                                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handleDelete(e.entry_id)}>
                                                        <Trash2 className="h-3 w-3 text-red-400" />
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Phase total */}
                                {faseEntries.length > 0 && (
                                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-200/50">
                                        <span>{faseEntries.length} sessioni registrate</span>
                                        <span className="font-bold text-slate-700">Totale: {totOre}h persona</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}

            {/* Riepilogo toggle */}
            <Button
                size="sm"
                variant="outline"
                className="w-full text-xs h-8"
                onClick={() => setShowRiepilogo(!showRiepilogo)}
                data-testid="diario-toggle-riepilogo"
            >
                <BarChart3 className="h-3 w-3 mr-1" />
                {showRiepilogo ? 'Nascondi Riepilogo' : 'Mostra Riepilogo Costi'}
            </Button>

            {showRiepilogo && riepilogo && (
                <div className="p-3 bg-slate-50 rounded-lg border space-y-3">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        <StatCard label="Ore Persona" value={`${riepilogo.totale_ore_totali}h`} color="blue" />
                        <StatCard label="Preventivate" value={riepilogo.totale_ore_preventivate > 0 ? `${riepilogo.totale_ore_preventivate}h` : '—'} color="slate" />
                        <StatCard label="Costo Effettivo" value={`€ ${riepilogo.costo_effettivo.toLocaleString('it-IT')}`} color="amber" />
                        <StatCard
                            label="Scostamento"
                            value={riepilogo.scostamento !== null ? `${riepilogo.scostamento > 0 ? '+' : ''}€ ${riepilogo.scostamento.toLocaleString('it-IT')}` : '—'}
                            color={riepilogo.scostamento > 0 ? 'red' : riepilogo.scostamento < 0 ? 'green' : 'slate'}
                        />
                    </div>
                    {riepilogo.per_operatore.length > 0 && (
                        <div>
                            <h4 className="text-[10px] font-semibold mb-1 flex items-center gap-1"><Users className="h-3 w-3" /> Per Operatore</h4>
                            <div className="flex flex-wrap gap-2">
                                {riepilogo.per_operatore.map(op => (
                                    <div key={op.nome} className="text-[10px] bg-white px-2 py-1 rounded border">
                                        <span className="font-medium">{op.nome}</span>
                                        <span className="ml-1 text-slate-500">{op.ore}h in {op.sessioni} sessioni</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    {riepilogo.costo_orario > 0 && (
                        <p className="text-[9px] text-slate-400">Costo orario: € {riepilogo.costo_orario.toFixed(2)}/h</p>
                    )}
                </div>
            )}

            {/* Session Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-base">
                            {editEntry ? 'Modifica Sessione' : 'Registra Sessione di Lavoro'}
                            {targetFase && <Badge className={`ml-2 text-[10px] ${(FASE_COLORS[targetFase.tipo] || FASE_COLORS.taglio).badge}`}>{targetFase.label || targetFase.tipo}</Badge>}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Data</label>
                            <Input
                                type="date"
                                value={form.data}
                                onChange={e => setForm(f => ({ ...f, data: e.target.value }))}
                                className="h-9"
                                data-testid="diario-input-data"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Ore lavorate (durata sessione)</label>
                            <Input
                                type="number"
                                step="0.5"
                                min="0"
                                max="24"
                                value={form.ore}
                                onChange={e => setForm(f => ({ ...f, ore: e.target.value }))}
                                className="h-9"
                                data-testid="diario-input-ore"
                            />
                            {form.ore && form.operatoriIds.length > 1 && (
                                <p className="text-[10px] text-blue-600 mt-1">
                                    {form.ore}h x {form.operatoriIds.length} operatori = {(parseFloat(form.ore) * form.operatoriIds.length).toFixed(1)}h persona totali
                                </p>
                            )}
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">
                                Operatori ({form.operatoriIds.length} selezionati)
                            </label>
                            <div className="max-h-40 overflow-y-auto border rounded-md p-2 space-y-1">
                                {teamMembers.map(m => (
                                    <label
                                        key={m.user_id}
                                        className="flex items-center gap-2 p-1.5 rounded hover:bg-slate-50 cursor-pointer"
                                    >
                                        <Checkbox
                                            checked={form.operatoriIds.includes(m.user_id)}
                                            onCheckedChange={() => toggleOperatore(m.user_id)}
                                            data-testid={`op-check-${m.user_id}`}
                                        />
                                        <span className="text-sm">{m.name || m.email}</span>
                                        {m.role && <span className="text-[9px] text-slate-400">{m.role}</span>}
                                    </label>
                                ))}
                                {teamMembers.length === 0 && (
                                    <p className="text-xs text-slate-400 italic">Nessun membro del team trovato</p>
                                )}
                            </div>
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Note (opzionale)</label>
                            <Input
                                value={form.note}
                                onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                                className="h-9"
                                placeholder="Es: Taglio travi IPE 200, ritardo materiale..."
                                data-testid="diario-input-note"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button
                            size="sm"
                            className="bg-[#0055FF]"
                            onClick={handleSave}
                            disabled={loading || form.operatoriIds.length === 0 || !form.ore}
                            data-testid="diario-save-btn"
                        >
                            {editEntry ? 'Salva Modifiche' : 'Registra Sessione'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function StatCard({ label, value, color }) {
    const colors = {
        blue: 'bg-blue-50 text-blue-700 border-blue-200',
        slate: 'bg-slate-50 text-slate-700 border-slate-200',
        amber: 'bg-amber-50 text-amber-700 border-amber-200',
        red: 'bg-red-50 text-red-700 border-red-200',
        green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    };
    return (
        <div className={`p-2.5 rounded border ${colors[color] || colors.slate}`}>
            <p className="text-[9px] uppercase tracking-wide opacity-70">{label}</p>
            <p className="text-base font-bold">{value}</p>
        </div>
    );
}
