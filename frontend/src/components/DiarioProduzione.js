/**
 * Diario di Produzione Adattivo — Registro lavoro integrato nelle fasi.
 * MATRIOSKA: Se la commessa ha più voci di lavoro, l'operaio seleziona
 * su quale voce sta lavorando tramite bottoni grandi e colorati.
 * I campi del diario si adattano alla categoria normativa della voce selezionata.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Textarea } from '../components/ui/textarea';
import {
    Plus, Trash2, Clock, Users, BarChart3, Edit2,
    ChevronDown, ChevronRight, Play, CheckCircle2, UserPlus,
    Hammer, LayoutGrid, Timer, Camera, FileText, Shield,
} from 'lucide-react';
import { toast } from 'sonner';

const FASE_COLORS = {
    taglio: { bg: 'bg-red-50 border-red-200', badge: 'bg-red-100 text-red-700', bar: 'bg-red-500' },
    foratura: { bg: 'bg-orange-50 border-orange-200', badge: 'bg-orange-100 text-orange-700', bar: 'bg-orange-500' },
    assemblaggio: { bg: 'bg-blue-50 border-blue-200', badge: 'bg-blue-100 text-blue-700', bar: 'bg-blue-500' },
    saldatura: { bg: 'bg-amber-50 border-amber-200', badge: 'bg-amber-100 text-amber-700', bar: 'bg-amber-500' },
    pulizia: { bg: 'bg-teal-50 border-teal-200', badge: 'bg-teal-100 text-teal-700', bar: 'bg-teal-500' },
    preparazione_superfici: { bg: 'bg-purple-50 border-purple-200', badge: 'bg-purple-100 text-purple-700', bar: 'bg-purple-500' },
};

const VOCE_CATEGORIE = {
    EN_1090: { label: 'Strutturale', subtitle: 'EN 1090', color: 'border-blue-400 bg-blue-50 text-blue-900', ring: 'ring-blue-400', iconBg: 'bg-blue-600', Icon: Hammer },
    EN_13241: { label: 'Cancello', subtitle: 'EN 13241', color: 'border-amber-400 bg-amber-50 text-amber-900', ring: 'ring-amber-400', iconBg: 'bg-amber-600', Icon: LayoutGrid },
    GENERICA: { label: 'Generica', subtitle: 'No CE', color: 'border-slate-400 bg-slate-50 text-slate-800', ring: 'ring-slate-400', iconBg: 'bg-slate-600', Icon: Timer },
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

export default function DiarioProduzione({ commessaId, fasi = [], vociLavoro = [], normativaTipo, onUpdateFase, onRefresh }) {
    const [entries, setEntries] = useState([]);
    const [riepilogo, setRiepilogo] = useState(null);
    const [operatori, setOperatori] = useState([]);
    const [expandedFasi, setExpandedFasi] = useState({});
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editEntry, setEditEntry] = useState(null);
    const [targetFase, setTargetFase] = useState(null);
    const [form, setForm] = useState({
        data: '', ore: '', selectedOps: [], note: '',
        voce_id: '', numero_colata: '', wps_usata: '', note_collaudo: '',
    });
    const [loading, setLoading] = useState(false);
    const [showRiepilogo, setShowRiepilogo] = useState(false);
    const [newOpName, setNewOpName] = useState('');
    const [addingOp, setAddingOp] = useState(false);
    const [pinEditing, setPinEditing] = useState(null);
    const [pinValue, setPinValue] = useState('');

    // Build the effective list of selectable voci (parent category + child voci)
    const selectableVoci = buildSelectableVoci(normativaTipo, vociLavoro);
    const hasMultipleVoci = selectableVoci.length > 1;

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

    const fetchOperatori = useCallback(async () => {
        try {
            const res = await apiRequest(`/commesse/${commessaId}/operatori`);
            setOperatori(res.operatori || []);
        } catch (e) { console.error(e); }
    }, [commessaId]);

    useEffect(() => { fetchEntries(); fetchRiepilogo(); fetchOperatori(); }, [fetchEntries, fetchRiepilogo, fetchOperatori]);

    const entriesByFase = (faseTipo) => entries.filter(e => e.fase === faseTipo).sort((a, b) => b.data.localeCompare(a.data));
    const totalOreFase = (faseTipo) => entries.filter(e => e.fase === faseTipo).reduce((s, e) => s + (e.ore_totali || e.ore || 0), 0);
    const toggleExpand = (tipo) => setExpandedFasi(prev => ({ ...prev, [tipo]: !prev[tipo] }));

    const getSelectedVoceCategory = () => {
        if (!form.voce_id) return normativaTipo || 'GENERICA';
        if (form.voce_id === '__principale__') return normativaTipo;
        const voce = vociLavoro.find(v => v.voce_id === form.voce_id);
        return voce?.normativa_tipo || normativaTipo || 'GENERICA';
    };

    const openNewSession = (fase) => {
        setEditEntry(null);
        setTargetFase(fase);
        const defaultVoce = selectableVoci.length === 1 ? selectableVoci[0].id : '';
        setForm({
            data: new Date().toISOString().split('T')[0], ore: '', selectedOps: [], note: '',
            voce_id: defaultVoce, numero_colata: '', wps_usata: '', note_collaudo: '',
        });
        setDialogOpen(true);
    };

    const openEditSession = (entry) => {
        setEditEntry(entry);
        setTargetFase({ tipo: entry.fase });
        const ids = (entry.operatori || []).map(o => o.id);
        setForm({
            data: entry.data, ore: String(entry.ore), selectedOps: ids, note: entry.note || '',
            voce_id: entry.voce_id || '',
            numero_colata: entry.numero_colata || '',
            wps_usata: entry.wps_usata || '',
            note_collaudo: entry.note_collaudo || '',
        });
        setDialogOpen(true);
    };

    const toggleOperatore = (opId) => {
        setForm(f => {
            const ops = f.selectedOps.includes(opId)
                ? f.selectedOps.filter(id => id !== opId)
                : [...f.selectedOps, opId];
            return { ...f, selectedOps: ops };
        });
    };

    const handleAddOperatore = async () => {
        const name = newOpName.trim();
        if (!name) return;
        setAddingOp(true);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/operatori`, {
                method: 'POST', body: JSON.stringify({ nome: name }),
            });
            setOperatori(prev => [...prev, res].sort((a, b) => a.nome.localeCompare(b.nome)));
            setForm(f => ({ ...f, selectedOps: [...f.selectedOps, res.op_id] }));
            setNewOpName('');
            toast.success(`${name} aggiunto`);
        } catch (e) { toast.error(e.message); }
        setAddingOp(false);
    };

    const handleDeleteOperatore = async (opId) => {
        if (!window.confirm('Eliminare questo operatore?')) return;
        try {
            await apiRequest(`/commesse/${commessaId}/operatori/${opId}`, { method: 'DELETE' });
            setOperatori(prev => prev.filter(o => o.op_id !== opId));
            setForm(f => ({ ...f, selectedOps: f.selectedOps.filter(id => id !== opId) }));
            toast.success('Operatore rimosso');
        } catch (e) { toast.error(e.message); }
    };

    const handleSetPin = async (opId) => {
        if (pinValue.length !== 4 || !/^\d{4}$/.test(pinValue)) { toast.error('PIN: 4 cifre'); return; }
        try {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            await apiRequest(`/officina/pin/set`, {
                method: 'POST',
                body: JSON.stringify({ operatore_id: opId, pin: pinValue, admin_id: user.user_id }),
            });
            toast.success('PIN impostato');
            setPinEditing(null);
            setPinValue('');
        } catch (e) { toast.error(e.message); }
    };

    const handleSave = async () => {
        if (!form.ore || form.selectedOps.length === 0 || !targetFase) return;
        if (hasMultipleVoci && !form.voce_id) { toast.error('Seleziona la voce di lavoro'); return; }
        setLoading(true);
        try {
            const ops = form.selectedOps.map(id => {
                const op = operatori.find(o => o.op_id === id);
                return { id, nome: op?.nome || '' };
            });
            const payload = {
                data: form.data,
                fase: targetFase.tipo,
                ore: parseFloat(form.ore),
                operatori: ops,
                note: form.note,
                voce_id: form.voce_id || null,
                numero_colata: form.numero_colata || null,
                wps_usata: form.wps_usata || null,
                note_collaudo: form.note_collaudo || null,
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

    const selectedCategory = getSelectedVoceCategory();

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
                        <div className="flex items-center gap-1.5 sm:gap-2 p-2.5 sm:p-3 cursor-pointer select-none" onClick={() => toggleExpand(f.tipo)}>
                            {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
                            <span className="font-semibold text-xs sm:text-sm flex-1 truncate">{f.label || f.tipo}</span>

                            {totOre > 0 && (
                                <div className="hidden sm:flex items-center gap-1.5 mr-2">
                                    <Clock className="h-3 w-3 text-slate-400" />
                                    <span className={`text-xs font-mono font-bold ${isOver ? 'text-red-600' : 'text-slate-700'}`}>{totOre}h</span>
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
                            {totOre > 0 && (
                                <span className={`sm:hidden text-[10px] font-bold px-1.5 py-0.5 rounded ${isOver ? 'bg-red-100 text-red-700' : 'bg-white/70 text-slate-700'}`}>{totOre}h</span>
                            )}

                            <span className="hidden sm:inline text-[10px] text-slate-400 mr-1">{faseEntries.length > 0 && `${faseEntries.length} sess.`}</span>
                            <StatoBadge stato={f.stato} />

                            <div className="hidden sm:flex gap-1 ml-1" onClick={e => e.stopPropagation()}>
                                {f.stato === 'da_fare' && (
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-blue-600 hover:bg-blue-100" onClick={() => handleStartFase(f.tipo)}>
                                        <Play className="h-3 w-3 mr-0.5" /> Avvia
                                    </Button>
                                )}
                                {(f.stato === 'in_corso' || f.stato === 'da_fare') && (
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-emerald-600 hover:bg-emerald-100" onClick={() => openNewSession(f)}>
                                        <Plus className="h-3 w-3 mr-0.5" /> Registra
                                    </Button>
                                )}
                                {f.stato === 'in_corso' && (
                                    <Button size="sm" variant="ghost" className="h-7 text-[10px] text-emerald-700 hover:bg-emerald-100" onClick={() => handleCompleteFase(f.tipo)}>
                                        <CheckCircle2 className="h-3 w-3 mr-0.5" /> Completa
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Expanded: work sessions */}
                        {isExpanded && (
                            <div className="px-2.5 sm:px-3 pb-3 space-y-2">
                                {/* Mobile action buttons */}
                                <div className="flex sm:hidden gap-1.5 flex-wrap" onClick={e => e.stopPropagation()}>
                                    {f.stato === 'da_fare' && (
                                        <Button size="sm" variant="outline" className="h-8 text-[11px] text-blue-600 flex-1" onClick={() => handleStartFase(f.tipo)}>
                                            <Play className="h-3.5 w-3.5 mr-1" /> Avvia Fase
                                        </Button>
                                    )}
                                    {(f.stato === 'in_corso' || f.stato === 'da_fare') && (
                                        <Button size="sm" className="h-8 text-[11px] bg-[#0055FF] text-white flex-1" onClick={() => openNewSession(f)}>
                                            <Plus className="h-3.5 w-3.5 mr-1" /> Registra Lavoro
                                        </Button>
                                    )}
                                    {f.stato === 'in_corso' && (
                                        <Button size="sm" variant="outline" className="h-8 text-[11px] text-emerald-700 flex-1" onClick={() => handleCompleteFase(f.tipo)}>
                                            <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Completa
                                        </Button>
                                    )}
                                </div>

                                {/* Mobile hours progress */}
                                {totOre > 0 && orePrev > 0 && (
                                    <div className="sm:hidden flex items-center gap-2 text-[10px] text-slate-500">
                                        <span>{totOre}h / {orePrev}h prev.</span>
                                        <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                                            <div className={`h-1.5 rounded-full ${isOver ? 'bg-red-500' : colors.bar}`} style={{ width: `${pct}%` }} />
                                        </div>
                                    </div>
                                )}

                                <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
                                    <span>Ore preventivate:</span>
                                    <Input type="number" className="h-6 w-20 text-[11px] text-center" value={f.ore_preventivate || ''} placeholder="—"
                                        onBlur={e => handleOrePreventivate(f.tipo, e.target.value)} onChange={() => {}} />
                                    <span>h</span>
                                </div>

                                {faseEntries.length === 0 ? (
                                    <p className="text-xs text-slate-400 italic py-3 text-center">Nessuna sessione registrata.</p>
                                ) : (
                                    <div className="space-y-1.5">
                                        {faseEntries.map(e => {
                                            const voceInfo = getVoceLabel(e.voce_id, vociLavoro, normativaTipo);
                                            return (
                                                <div key={e.entry_id} className="flex items-start gap-2 p-2 bg-white/70 rounded border border-white text-xs">
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2 flex-wrap mb-0.5">
                                                            <span className="font-medium text-slate-700">
                                                                {new Date(e.data + 'T00:00').toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })}
                                                            </span>
                                                            <span className="font-bold text-slate-800"><Clock className="h-3 w-3 inline mr-0.5" />{e.ore}h</span>
                                                            {(e.operatori || []).length > 1 && (
                                                                <span className="text-[10px] text-slate-400">({e.ore_totali || e.ore}h pers.)</span>
                                                            )}
                                                        </div>
                                                        {/* Voce di lavoro badge */}
                                                        {voceInfo && hasMultipleVoci && (
                                                            <div className="mb-0.5">
                                                                <Badge className={`text-[8px] px-1 py-0 ${voceInfo.badgeClass}`}>
                                                                    {voceInfo.label}
                                                                </Badge>
                                                            </div>
                                                        )}
                                                        <div className="flex items-center gap-1 flex-wrap">
                                                            <Users className="h-3 w-3 text-slate-400 shrink-0" />
                                                            {(e.operatori || []).map((op, i) => (
                                                                <Badge key={i} variant="secondary" className="text-[9px] px-1 py-0 bg-slate-100">{op.nome}</Badge>
                                                            ))}
                                                        </div>
                                                        {/* Category-specific info displayed on entries */}
                                                        {e.numero_colata && (
                                                            <p className="text-[10px] text-blue-600 mt-0.5"><FileText className="h-2.5 w-2.5 inline mr-0.5" />Colata: {e.numero_colata}</p>
                                                        )}
                                                        {e.wps_usata && (
                                                            <p className="text-[10px] text-blue-600 mt-0.5"><Shield className="h-2.5 w-2.5 inline mr-0.5" />WPS: {e.wps_usata}</p>
                                                        )}
                                                        {e.note_collaudo && (
                                                            <p className="text-[10px] text-amber-600 mt-0.5"><Camera className="h-2.5 w-2.5 inline mr-0.5" />Collaudo: {e.note_collaudo}</p>
                                                        )}
                                                        {e.note && <p className="text-[10px] text-slate-400 mt-0.5 italic truncate">{e.note}</p>}
                                                    </div>
                                                    <div className="flex gap-0.5 shrink-0">
                                                        <Button size="sm" variant="ghost" className="h-7 w-7 sm:h-6 sm:w-6 p-0" onClick={() => openEditSession(e)}><Edit2 className="h-3.5 sm:h-3 w-3.5 sm:w-3 text-slate-400" /></Button>
                                                        <Button size="sm" variant="ghost" className="h-7 w-7 sm:h-6 sm:w-6 p-0" onClick={() => handleDelete(e.entry_id)}><Trash2 className="h-3.5 sm:h-3 w-3.5 sm:w-3 text-red-400" /></Button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}

                                {faseEntries.length > 0 && (
                                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-200/50">
                                        <span>{faseEntries.length} sessioni</span>
                                        <span className="font-bold text-slate-700">Totale: {totOre}h persona</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}

            {/* Riepilogo */}
            <Button size="sm" variant="outline" className="w-full text-xs h-8" onClick={() => setShowRiepilogo(!showRiepilogo)} data-testid="btn-riepilogo">
                <BarChart3 className="h-3 w-3 mr-1" /> {showRiepilogo ? 'Nascondi Riepilogo' : 'Mostra Riepilogo Costi'}
            </Button>

            {showRiepilogo && riepilogo && (
                <div className="p-2.5 sm:p-3 bg-slate-50 rounded-lg border space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                        <StatCard label="Ore Persona" value={`${riepilogo.totale_ore_totali}h`} color="blue" />
                        <StatCard label="Preventivate" value={riepilogo.totale_ore_preventivate > 0 ? `${riepilogo.totale_ore_preventivate}h` : '—'} color="slate" />
                        <StatCard label="Costo Effettivo" value={`€ ${riepilogo.costo_effettivo.toLocaleString('it-IT')}`} color="amber" />
                        <StatCard label="Scostamento" value={riepilogo.scostamento !== null ? `${riepilogo.scostamento > 0 ? '+' : ''}€ ${riepilogo.scostamento.toLocaleString('it-IT')}` : '—'}
                            color={riepilogo.scostamento > 0 ? 'red' : riepilogo.scostamento < 0 ? 'green' : 'slate'} />
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
                    {riepilogo.costo_orario > 0 && <p className="text-[9px] text-slate-400">Costo orario: € {riepilogo.costo_orario.toFixed(2)}/h</p>}
                </div>
            )}

            {/* Session Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-md w-[95vw] sm:w-full max-h-[90vh] overflow-y-auto" data-testid="session-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-sm sm:text-base">
                            {editEntry ? 'Modifica Sessione' : 'Registra Lavoro'}
                            {targetFase && <Badge className={`ml-2 text-[10px] ${(FASE_COLORS[targetFase.tipo] || FASE_COLORS.taglio).badge}`}>{targetFase.label || targetFase.tipo}</Badge>}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        {/* ── VOCE SELECTOR — solo se cantiere misto ── */}
                        {hasMultipleVoci && (
                            <div data-testid="voce-selector">
                                <label className="text-xs font-semibold text-slate-600 mb-2 block">
                                    Su quale voce stai lavorando? *
                                </label>
                                <div className="grid grid-cols-1 gap-2">
                                    {selectableVoci.map(v => {
                                        const cat = VOCE_CATEGORIE[v.normativa_tipo] || VOCE_CATEGORIE.GENERICA;
                                        const CatIcon = cat.Icon;
                                        const isSelected = form.voce_id === v.id;
                                        return (
                                            <button
                                                key={v.id}
                                                type="button"
                                                data-testid={`voce-btn-${v.id}`}
                                                onClick={() => setForm(f => ({ ...f, voce_id: v.id, numero_colata: '', wps_usata: '', note_collaudo: '' }))}
                                                className={`flex items-center gap-3 p-3 rounded-xl border-2 text-left transition-all min-h-[56px]
                                                    ${isSelected ? `${cat.color} ring-2 ring-offset-1 ${cat.ring} shadow-md` : 'border-slate-200 bg-white hover:shadow-sm hover:border-slate-300'}`}
                                            >
                                                <div className={`w-10 h-10 rounded-lg ${isSelected ? cat.iconBg : 'bg-slate-300'} flex items-center justify-center shrink-0 transition-colors`}>
                                                    <CatIcon className="h-5 w-5 text-white" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className={`font-bold text-sm leading-tight ${isSelected ? '' : 'text-slate-700'}`}>{v.descrizione}</p>
                                                    <p className="text-[10px] opacity-60 mt-0.5">{cat.label} — {cat.subtitle}</p>
                                                </div>
                                                {isSelected && <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* Date + Hours */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="text-xs font-medium text-slate-600 mb-1 block">Data</label>
                                <Input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} className="h-10 sm:h-9 text-base sm:text-sm" data-testid="session-date" />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-slate-600 mb-1 block">Ore lavorate</label>
                                <Input type="number" step="0.5" min="0" max="24" value={form.ore} inputMode="decimal"
                                    onChange={e => setForm(f => ({ ...f, ore: e.target.value }))} className="h-10 sm:h-9 text-base sm:text-sm" data-testid="session-hours" />
                            </div>
                        </div>
                        {form.ore && form.selectedOps.length > 1 && (
                            <p className="text-[11px] text-blue-600 -mt-1">
                                {form.ore}h x {form.selectedOps.length} operatori = {(parseFloat(form.ore) * form.selectedOps.length).toFixed(1)}h persona
                            </p>
                        )}

                        {/* ── CATEGORY-SPECIFIC FIELDS ── */}
                        {selectedCategory === 'EN_1090' && (
                            <div className="space-y-2 p-3 bg-blue-50 rounded-lg border border-blue-200 animate-in fade-in slide-in-from-top-2 duration-200" data-testid="fields-en1090">
                                <p className="text-[10px] font-semibold text-blue-700 uppercase tracking-wide flex items-center gap-1">
                                    <Hammer className="h-3 w-3" /> Dati Strutturale EN 1090
                                </p>
                                <div>
                                    <label className="text-xs font-medium text-blue-800 mb-1 block">N. Colata / Certificato 3.1</label>
                                    <Input value={form.numero_colata} onChange={e => setForm(f => ({ ...f, numero_colata: e.target.value }))}
                                        placeholder="es. 12345-A" className="h-9 border-blue-200 bg-white" data-testid="field-colata" />
                                </div>
                                <div>
                                    <label className="text-xs font-medium text-blue-800 mb-1 block">WPS utilizzata</label>
                                    <Input value={form.wps_usata} onChange={e => setForm(f => ({ ...f, wps_usata: e.target.value }))}
                                        placeholder="es. WPS-001 MAG 135" className="h-9 border-blue-200 bg-white" data-testid="field-wps" />
                                </div>
                            </div>
                        )}

                        {selectedCategory === 'EN_13241' && (
                            <div className="space-y-2 p-3 bg-amber-50 rounded-lg border border-amber-200 animate-in fade-in slide-in-from-top-2 duration-200" data-testid="fields-en13241">
                                <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide flex items-center gap-1">
                                    <LayoutGrid className="h-3 w-3" /> Dati Cancello EN 13241
                                </p>
                                <div>
                                    <label className="text-xs font-medium text-amber-800 mb-1 block">Note collaudo / sicurezza</label>
                                    <Textarea value={form.note_collaudo} onChange={e => setForm(f => ({ ...f, note_collaudo: e.target.value }))}
                                        placeholder="es. Fotocellule installate, coste sensibili testate OK..."
                                        className="min-h-[60px] border-amber-200 bg-white text-sm" data-testid="field-collaudo" />
                                </div>
                            </div>
                        )}

                        {/* GENERICA: no extra fields — just hours and materials */}
                        {selectedCategory === 'GENERICA' && hasMultipleVoci && (
                            <div className="p-2 bg-slate-50 rounded-lg border border-slate-200 text-center" data-testid="fields-generica">
                                <p className="text-[10px] text-slate-500">Solo ore e note — nessun dato tecnico richiesto</p>
                            </div>
                        )}

                        {/* Operators */}
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">
                                Operatori ({form.selectedOps.length} selezionati)
                            </label>
                            <div className="border rounded-md">
                                <div className="flex items-center gap-1 p-2 border-b bg-slate-50">
                                    <UserPlus className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    <Input
                                        value={newOpName}
                                        onChange={e => setNewOpName(e.target.value)}
                                        placeholder="Nuovo operatore..."
                                        className="h-8 sm:h-7 text-sm sm:text-xs border-0 bg-transparent shadow-none focus-visible:ring-0"
                                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAddOperatore(); } }}
                                        data-testid="new-op-input"
                                    />
                                    <Button size="sm" variant="ghost" className="h-8 sm:h-7 text-[11px] sm:text-[10px] text-[#0055FF] shrink-0 px-2"
                                        onClick={handleAddOperatore} disabled={addingOp || !newOpName.trim()}>
                                        <Plus className="h-3 w-3" /> Aggiungi
                                    </Button>
                                </div>
                                <div className="max-h-48 sm:max-h-40 overflow-y-auto p-1.5 space-y-0.5">
                                    {operatori.length === 0 && (
                                        <p className="text-xs text-slate-400 italic py-2 text-center">Nessun operatore. Aggiungine uno sopra.</p>
                                    )}
                                    {operatori.map(op => (
                                        <div key={op.op_id} className="flex items-center gap-2 p-2 sm:p-1.5 rounded hover:bg-slate-50 group">
                                            <label className="flex items-center gap-2 flex-1 cursor-pointer min-w-0">
                                                <Checkbox
                                                    checked={form.selectedOps.includes(op.op_id)}
                                                    onCheckedChange={() => toggleOperatore(op.op_id)}
                                                />
                                                <span className="text-sm truncate">{op.nome}</span>
                                                {op.mansione && <span className="text-[9px] text-slate-400">{op.mansione}</span>}
                                            </label>
                                            {/* PIN management */}
                                            {pinEditing === op.op_id ? (
                                                <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
                                                    <Input
                                                        value={pinValue}
                                                        onChange={e => setPinValue(e.target.value.replace(/\D/g, '').slice(0, 4))}
                                                        placeholder="PIN"
                                                        className="h-6 w-14 text-[10px] text-center font-mono"
                                                        maxLength={4}
                                                        inputMode="numeric"
                                                        autoFocus
                                                        onKeyDown={e => { if (e.key === 'Enter') handleSetPin(op.op_id); }}
                                                        data-testid={`pin-input-${op.op_id}`}
                                                    />
                                                    <Button size="sm" variant="ghost" className="h-6 px-1 text-[9px] text-green-600" onClick={() => handleSetPin(op.op_id)}>OK</Button>
                                                    <Button size="sm" variant="ghost" className="h-6 px-1 text-[9px]" onClick={() => { setPinEditing(null); setPinValue(''); }}>X</Button>
                                                </div>
                                            ) : (
                                                <button
                                                    className="shrink-0 text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 hover:bg-blue-100 hover:text-blue-700 transition-colors"
                                                    onClick={e => { e.stopPropagation(); setPinEditing(op.op_id); setPinValue(''); }}
                                                    title="Imposta PIN officina"
                                                    data-testid={`pin-btn-${op.op_id}`}
                                                >
                                                    PIN
                                                </button>
                                            )}
                                            <Button size="sm" variant="ghost" className="h-6 w-6 sm:h-5 sm:w-5 p-0 opacity-0 group-hover:opacity-100 sm:opacity-0 shrink-0"
                                                onClick={e => { e.preventDefault(); handleDeleteOperatore(op.op_id); }}>
                                                <Trash2 className="h-3 w-3 text-red-300" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Notes */}
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Note (opzionale)</label>
                            <Input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} className="h-10 sm:h-9 text-base sm:text-sm"
                                placeholder="Es: Taglio travi IPE 200..." data-testid="session-notes" />
                        </div>
                    </div>
                    <DialogFooter className="flex-row gap-2">
                        <Button variant="outline" size="sm" className="flex-1 sm:flex-none h-10 sm:h-9" onClick={() => setDialogOpen(false)}>Annulla</Button>
                        <Button size="sm" className="bg-[#0055FF] flex-1 sm:flex-none h-10 sm:h-9" onClick={handleSave}
                            disabled={loading || form.selectedOps.length === 0 || !form.ore || (hasMultipleVoci && !form.voce_id)} data-testid="session-save-btn">
                            {editEntry ? 'Salva' : 'Registra'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

/** Build the list of selectable voci for the diary selector */
function buildSelectableVoci(normativaTipo, vociLavoro) {
    const voci = [];
    // Always include the parent commessa's category as the "implicit" voce
    if (normativaTipo) {
        voci.push({
            id: '__principale__',
            descrizione: normativaTipo === 'EN_1090' ? 'Lavorazione principale (Strutturale)'
                : normativaTipo === 'EN_13241' ? 'Lavorazione principale (Cancello)'
                : 'Lavorazione principale (Generica)',
            normativa_tipo: normativaTipo,
        });
    }
    // Add child voci
    (vociLavoro || []).forEach(v => {
        voci.push({ id: v.voce_id, descrizione: v.descrizione, normativa_tipo: v.normativa_tipo });
    });
    return voci;
}

/** Get display label for a voce entry */
function getVoceLabel(voceId, vociLavoro, normativaTipo) {
    if (!voceId) return null;
    if (voceId === '__principale__') {
        const cat = VOCE_CATEGORIE[normativaTipo] || VOCE_CATEGORIE.GENERICA;
        return { label: `Principale (${cat.subtitle})`, badgeClass: normativaTipo === 'EN_1090' ? 'bg-blue-100 text-blue-700' : normativaTipo === 'EN_13241' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600' };
    }
    const voce = (vociLavoro || []).find(v => v.voce_id === voceId);
    if (!voce) return null;
    const cat = VOCE_CATEGORIE[voce.normativa_tipo] || VOCE_CATEGORIE.GENERICA;
    return {
        label: `${voce.descrizione} (${cat.subtitle})`,
        badgeClass: voce.normativa_tipo === 'EN_1090' ? 'bg-blue-100 text-blue-700' : voce.normativa_tipo === 'EN_13241' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600',
    };
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
