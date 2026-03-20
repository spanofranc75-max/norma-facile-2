/**
 * Diario di Produzione — Time tracking per commessa.
 * Calendario mensile + registrazione ore operatori per fase.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Calendar } from '../components/ui/calendar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Plus, Trash2, Clock, Users, BarChart3, Edit2, CalendarDays } from 'lucide-react';
import { it } from 'date-fns/locale';

const FASI_LABELS = {
    taglio: 'Taglio',
    foratura: 'Foratura',
    assemblaggio: 'Assemblaggio',
    saldatura: 'Saldatura',
    pulizia: 'Pulizia / Sbavatura',
    preparazione_superfici: 'Prep. Superfici',
};

const FASE_COLORS = {
    taglio: 'bg-red-100 text-red-700',
    foratura: 'bg-orange-100 text-orange-700',
    assemblaggio: 'bg-blue-100 text-blue-700',
    saldatura: 'bg-amber-100 text-amber-700',
    pulizia: 'bg-teal-100 text-teal-700',
    preparazione_superfici: 'bg-purple-100 text-purple-700',
};

export default function DiarioProduzione({ commessaId, fasi = [] }) {
    const [entries, setEntries] = useState([]);
    const [riepilogo, setRiepilogo] = useState(null);
    const [teamMembers, setTeamMembers] = useState([]);
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editEntry, setEditEntry] = useState(null);
    const [form, setForm] = useState({ operatore_id: '', operatore_nome: '', fase: '', ore: '', note: '' });
    const [loading, setLoading] = useState(false);
    const [view, setView] = useState('calendar'); // 'calendar' | 'riepilogo'

    const meseStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}`;

    const fetchEntries = useCallback(async () => {
        try {
            const res = await apiRequest(`/commesse/${commessaId}/diario?mese=${meseStr}`);
            setEntries(res.entries || []);
        } catch (e) { console.error(e); }
    }, [commessaId, meseStr]);

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

    useEffect(() => { fetchEntries(); }, [fetchEntries]);
    useEffect(() => { fetchRiepilogo(); }, [fetchRiepilogo]);
    useEffect(() => { fetchTeam(); }, [fetchTeam]);

    const dateStr = (d) => {
        const dd = new Date(d);
        return `${dd.getFullYear()}-${String(dd.getMonth() + 1).padStart(2, '0')}-${String(dd.getDate()).padStart(2, '0')}`;
    };

    const selectedDateStr = dateStr(selectedDate);
    const dayEntries = entries.filter(e => e.data === selectedDateStr);

    // Days that have entries (for calendar highlights)
    const daysWithEntries = new Set(entries.map(e => e.data));

    const openNewEntry = () => {
        setEditEntry(null);
        setForm({ operatore_id: '', operatore_nome: '', fase: '', ore: '', note: '' });
        setDialogOpen(true);
    };

    const openEditEntry = (entry) => {
        setEditEntry(entry);
        setForm({
            operatore_id: entry.operatore_id,
            operatore_nome: entry.operatore_nome,
            fase: entry.fase,
            ore: String(entry.ore),
            note: entry.note || '',
        });
        setDialogOpen(true);
    };

    const handleOperatorChange = (userId) => {
        const member = teamMembers.find(m => m.user_id === userId);
        setForm(f => ({ ...f, operatore_id: userId, operatore_nome: member?.name || member?.email || '' }));
    };

    const handleSave = async () => {
        if (!form.operatore_id || !form.fase || !form.ore) return;
        setLoading(true);
        try {
            const payload = {
                data: selectedDateStr,
                operatore_id: form.operatore_id,
                operatore_nome: form.operatore_nome,
                fase: form.fase,
                ore: parseFloat(form.ore),
                note: form.note,
            };
            if (editEntry) {
                await apiRequest(`/commesse/${commessaId}/diario/${editEntry.entry_id}`, {
                    method: 'PUT', body: JSON.stringify(payload),
                });
            } else {
                await apiRequest(`/commesse/${commessaId}/diario`, {
                    method: 'POST', body: JSON.stringify(payload),
                });
            }
            setDialogOpen(false);
            fetchEntries();
            fetchRiepilogo();
        } catch (e) { console.error(e); }
        setLoading(false);
    };

    const handleDelete = async (entryId) => {
        if (!window.confirm('Eliminare questa voce?')) return;
        try {
            await apiRequest(`/commesse/${commessaId}/diario/${entryId}`, { method: 'DELETE' });
            fetchEntries();
            fetchRiepilogo();
        } catch (e) { console.error(e); }
    };

    const handleOrePreventivate = async (faseTipo, ore) => {
        try {
            await apiRequest(`/commesse/${commessaId}/produzione/${faseTipo}/ore-preventivate`, {
                method: 'PUT', body: JSON.stringify({ ore_preventivate: parseFloat(ore) || 0 }),
            });
            fetchRiepilogo();
        } catch (e) { console.error(e); }
    };

    const totalDayHours = dayEntries.reduce((s, e) => s + (e.ore || 0), 0);

    return (
        <div className="space-y-4" data-testid="diario-produzione">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex gap-1">
                    <Button
                        size="sm" variant={view === 'calendar' ? 'default' : 'outline'}
                        className={`text-xs h-7 ${view === 'calendar' ? 'bg-[#0055FF]' : ''}`}
                        onClick={() => setView('calendar')}
                        data-testid="diario-view-calendar"
                    >
                        <CalendarDays className="h-3 w-3 mr-1" /> Calendario
                    </Button>
                    <Button
                        size="sm" variant={view === 'riepilogo' ? 'default' : 'outline'}
                        className={`text-xs h-7 ${view === 'riepilogo' ? 'bg-[#0055FF]' : ''}`}
                        onClick={() => setView('riepilogo')}
                        data-testid="diario-view-riepilogo"
                    >
                        <BarChart3 className="h-3 w-3 mr-1" /> Riepilogo
                    </Button>
                </div>
            </div>

            {view === 'calendar' && (
                <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-4">
                    {/* Calendar */}
                    <div>
                        <Calendar
                            mode="single"
                            selected={selectedDate}
                            onSelect={(d) => d && setSelectedDate(d)}
                            month={currentMonth}
                            onMonthChange={setCurrentMonth}
                            locale={it}
                            className="rounded-md border"
                            modifiers={{ hasEntry: (d) => daysWithEntries.has(dateStr(d)) }}
                            modifiersClassNames={{ hasEntry: 'bg-blue-100 font-bold text-blue-700' }}
                        />
                    </div>

                    {/* Day detail */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold">
                                {selectedDate.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })}
                                {totalDayHours > 0 && (
                                    <span className="ml-2 text-xs font-normal text-slate-500">
                                        ({totalDayHours}h totali)
                                    </span>
                                )}
                            </h4>
                            <Button size="sm" className="text-xs h-7 bg-[#0055FF]" onClick={openNewEntry} data-testid="diario-add-entry">
                                <Plus className="h-3 w-3 mr-1" /> Registra Ore
                            </Button>
                        </div>

                        {dayEntries.length === 0 ? (
                            <p className="text-xs text-slate-400 italic py-4 text-center">Nessuna registrazione per questo giorno</p>
                        ) : (
                            <div className="space-y-2">
                                {dayEntries.map(e => (
                                    <div key={e.entry_id} className="flex items-center gap-2 p-2.5 bg-slate-50 rounded border text-xs" data-testid={`diario-entry-${e.entry_id}`}>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-1.5 mb-1">
                                                <Badge className={`text-[9px] px-1.5 py-0 ${FASE_COLORS[e.fase] || 'bg-slate-100 text-slate-700'}`}>
                                                    {FASI_LABELS[e.fase] || e.fase}
                                                </Badge>
                                                <span className="font-medium">{e.operatore_nome}</span>
                                            </div>
                                            <div className="flex items-center gap-2 text-slate-500">
                                                <Clock className="h-3 w-3" />
                                                <span className="font-semibold text-slate-700">{e.ore}h</span>
                                                {e.note && <span className="truncate">— {e.note}</span>}
                                            </div>
                                        </div>
                                        <div className="flex gap-1 shrink-0">
                                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => openEditEntry(e)}>
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
                    </div>
                </div>
            )}

            {view === 'riepilogo' && riepilogo && (
                <div className="space-y-4">
                    {/* Totals */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <StatCard label="Ore Effettive" value={`${riepilogo.totale_ore}h`} color="blue" />
                        <StatCard label="Ore Preventivate" value={riepilogo.totale_ore_preventivate > 0 ? `${riepilogo.totale_ore_preventivate}h` : '—'} color="slate" />
                        <StatCard label="Costo Effettivo" value={`€ ${riepilogo.costo_effettivo.toLocaleString('it-IT')}`} color="amber" />
                        <StatCard
                            label="Scostamento"
                            value={riepilogo.scostamento !== null ? `${riepilogo.scostamento > 0 ? '+' : ''}€ ${riepilogo.scostamento.toLocaleString('it-IT')}` : '—'}
                            color={riepilogo.scostamento > 0 ? 'red' : riepilogo.scostamento < 0 ? 'green' : 'slate'}
                        />
                    </div>

                    {/* Per Phase */}
                    <div>
                        <h4 className="text-xs font-semibold mb-2 flex items-center gap-1"><BarChart3 className="h-3.5 w-3.5" /> Per Fase</h4>
                        <div className="space-y-1.5">
                            {(fasi.length > 0 ? fasi : Object.keys(FASI_LABELS).map(k => ({ tipo: k, label: FASI_LABELS[k] }))).map(f => {
                                const stats = riepilogo.per_fase.find(p => p.label === (f.label || f.tipo)) || { ore_effettive: 0, ore_preventivate: f.ore_preventivate || 0 };
                                const pct = stats.ore_preventivate > 0 ? Math.min((stats.ore_effettive / stats.ore_preventivate) * 100, 150) : 0;
                                const isOver = stats.ore_preventivate > 0 && stats.ore_effettive > stats.ore_preventivate;
                                return (
                                    <div key={f.tipo} className="flex items-center gap-2 text-xs p-2 bg-slate-50 rounded">
                                        <Badge className={`text-[9px] px-1.5 py-0 w-24 justify-center ${FASE_COLORS[f.tipo] || 'bg-slate-100'}`}>
                                            {f.label || f.tipo}
                                        </Badge>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-1.5">
                                                <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                                                    <div
                                                        className={`h-1.5 rounded-full transition-all ${isOver ? 'bg-red-500' : 'bg-[#0055FF]'}`}
                                                        style={{ width: `${Math.min(pct, 100)}%` }}
                                                    />
                                                </div>
                                                <span className={`font-mono text-[10px] w-14 text-right ${isOver ? 'text-red-600 font-bold' : ''}`}>
                                                    {stats.ore_effettive}h
                                                </span>
                                            </div>
                                        </div>
                                        <span className="text-[10px] text-slate-400 w-8 text-center">/</span>
                                        <Input
                                            type="number"
                                            className="h-6 w-16 text-[10px] text-center"
                                            value={f.ore_preventivate || stats.ore_preventivate || ''}
                                            placeholder="Prev."
                                            onBlur={e => handleOrePreventivate(f.tipo, e.target.value)}
                                            onChange={() => {}}
                                            data-testid={`ore-prev-${f.tipo}`}
                                        />
                                        <span className="text-[10px] text-slate-400">h prev.</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Per Operator */}
                    {riepilogo.per_operatore.length > 0 && (
                        <div>
                            <h4 className="text-xs font-semibold mb-2 flex items-center gap-1"><Users className="h-3.5 w-3.5" /> Per Operatore</h4>
                            <div className="space-y-1">
                                {riepilogo.per_operatore.map(op => (
                                    <div key={op.nome} className="flex items-center justify-between text-xs p-2 bg-slate-50 rounded">
                                        <span className="font-medium">{op.nome}</span>
                                        <span className="font-mono text-slate-600">{op.ore}h</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {riepilogo.costo_orario > 0 && (
                        <p className="text-[10px] text-slate-400 italic">
                            Costo orario aziendale: € {riepilogo.costo_orario.toFixed(2)}/h
                        </p>
                    )}
                </div>
            )}

            {/* Entry Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-base">
                            {editEntry ? 'Modifica Registrazione' : 'Nuova Registrazione'}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Data</label>
                            <p className="text-sm font-medium">{selectedDate.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Operatore</label>
                            <Select value={form.operatore_id} onValueChange={handleOperatorChange}>
                                <SelectTrigger className="h-9" data-testid="diario-select-operatore">
                                    <SelectValue placeholder="Seleziona operatore" />
                                </SelectTrigger>
                                <SelectContent>
                                    {teamMembers.map(m => (
                                        <SelectItem key={m.user_id} value={m.user_id}>
                                            {m.name || m.email}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Fase</label>
                            <Select value={form.fase} onValueChange={v => setForm(f => ({ ...f, fase: v }))}>
                                <SelectTrigger className="h-9" data-testid="diario-select-fase">
                                    <SelectValue placeholder="Seleziona fase" />
                                </SelectTrigger>
                                <SelectContent>
                                    {(fasi.length > 0 ? fasi : Object.entries(FASI_LABELS).map(([k, v]) => ({ tipo: k, label: v }))).map(f => (
                                        <SelectItem key={f.tipo} value={f.tipo}>
                                            {f.label || f.tipo}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Ore lavorate</label>
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
                        </div>
                        <div>
                            <label className="text-xs font-medium text-slate-600 mb-1 block">Note (opzionale)</label>
                            <Input
                                value={form.note}
                                onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                                className="h-9"
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
                            disabled={loading || !form.operatore_id || !form.fase || !form.ore}
                            data-testid="diario-save-btn"
                        >
                            {editEntry ? 'Salva Modifiche' : 'Registra'}
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
        <div className={`p-3 rounded-lg border ${colors[color] || colors.slate}`}>
            <p className="text-[10px] uppercase tracking-wide opacity-70">{label}</p>
            <p className="text-lg font-bold">{value}</p>
        </div>
    );
}
