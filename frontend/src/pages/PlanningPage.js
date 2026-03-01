/**
 * Planning Cantieri — Kanban Board for workshop project tracking.
 * Uses @hello-pangea/dnd for drag-and-drop.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
    Plus, GripVertical, Calendar, Euro, User, Trash2,
    LayoutGrid, Clock, AlertTriangle, ChevronRight,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const COL_COLORS = {
    preventivo:         { header: 'bg-violet-600',  ring: 'ring-violet-200',  dot: 'bg-violet-500', light: 'bg-violet-50' },
    approvvigionamento: { header: 'bg-amber-600',   ring: 'ring-amber-200',   dot: 'bg-amber-500',  light: 'bg-amber-50' },
    lavorazione:        { header: 'bg-blue-600',    ring: 'ring-blue-200',    dot: 'bg-blue-500',   light: 'bg-blue-50' },
    conto_lavoro:       { header: 'bg-orange-600',  ring: 'ring-orange-200',  dot: 'bg-orange-500', light: 'bg-orange-50' },
    pronto_consegna:    { header: 'bg-emerald-600', ring: 'ring-emerald-200', dot: 'bg-emerald-500',light: 'bg-emerald-50' },
    montaggio:          { header: 'bg-teal-600',    ring: 'ring-teal-200',    dot: 'bg-teal-500',   light: 'bg-teal-50' },
    completato:         { header: 'bg-slate-600',   ring: 'ring-slate-200',   dot: 'bg-slate-500',  light: 'bg-slate-50' },
};

const PRIORITY_BADGE = {
    alta:   'bg-red-100 text-red-800',
    media:  'bg-amber-100 text-amber-800',
    bassa:  'bg-slate-100 text-slate-600',
};

function isOverdue(deadline) {
    if (!deadline) return false;
    return new Date(deadline) < new Date();
}

function formatDeadline(d) {
    if (!d) return null;
    try { return new Date(d).toLocaleDateString('it-IT', { day: '2-digit', month: 'short' }); }
    catch { return d; }
}

export default function PlanningPage() {
    const navigate = useNavigate();
    const [columns, setColumns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [clients, setClients] = useState([]);

    const fetchBoard = useCallback(async () => {
        try {
            const data = await apiRequest('/commesse/board/view');
            setColumns(data.columns || []);
        } catch (e) {
            toast.error('Errore caricamento planning');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchBoard(); }, [fetchBoard]);
    useEffect(() => {
        apiRequest('/clients/').then(d => setClients(d.clients || [])).catch(() => {});
    }, []);

    const handleDragEnd = async (result) => {
        const { draggableId, destination, source } = result;
        if (!destination) return;
        if (destination.droppableId === source.droppableId && destination.index === source.index) return;

        const newStatus = destination.droppableId;
        const commessaId = draggableId;

        // Optimistic update
        setColumns(prev => {
            const next = prev.map(col => ({ ...col, items: [...col.items] }));
            const srcCol = next.find(c => c.id === source.droppableId);
            const dstCol = next.find(c => c.id === newStatus);
            if (!srcCol || !dstCol) return prev;
            const [moved] = srcCol.items.splice(source.index, 1);
            moved.status = newStatus;
            dstCol.items.splice(destination.index, 0, moved);
            return next;
        });

        try {
            await apiRequest(`/commesse/${commessaId}/status`, {
                method: 'PATCH',
                body: { new_status: newStatus },
            });
        } catch (e) {
            toast.error('Errore aggiornamento stato');
            fetchBoard(); // rollback
        }
    };

    const handleDelete = async (commessaId) => {
        if (!window.confirm('Eliminare questa commessa?')) return;
        try {
            await apiRequest(`/commesse/${commessaId}`, { method: 'DELETE' });
            toast.success('Commessa eliminata');
            fetchBoard();
        } catch (e) { toast.error(e.message); }
    };

    const totalCommesse = columns.reduce((acc, col) => acc + col.items.length, 0);
    const totalValue = columns.reduce((acc, col) => acc + col.items.reduce((a, i) => a + (i.value || 0), 0), 0);

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="planning-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                            <LayoutGrid className="h-6 w-6 text-[#0055FF]" /> Planning Cantieri
                        </h1>
                        <p className="text-sm text-slate-500 mt-1">
                            {totalCommesse} commesse in corso &middot; Valore totale: {fmtEur(totalValue)}
                        </p>
                    </div>
                    <Button
                        data-testid="btn-new-commessa"
                        onClick={() => setCreateOpen(true)}
                        className="h-10 bg-[#0055FF] hover:bg-[#0044CC] text-white"
                    >
                        <Plus className="h-4 w-4 mr-2" /> Nuova Commessa
                    </Button>
                </div>

                {/* Kanban Board */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                    </div>
                ) : (
                    <DragDropContext onDragEnd={handleDragEnd}>
                        <div className="flex gap-3 overflow-x-auto pb-4 -mx-2 px-2" data-testid="kanban-board">
                            {columns.map(col => (
                                <KanbanColumn
                                    key={col.id}
                                    column={col}
                                    colors={COL_COLORS[col.id] || COL_COLORS.preventivo}
                                    onCardClick={(c) => navigate(`/commesse/${c.commessa_id}`)}
                                    onDelete={handleDelete}
                                />
                            ))}
                        </div>
                    </DragDropContext>
                )}

                {/* Create Modal */}
                <CreateCommessaModal
                    open={createOpen}
                    onOpenChange={setCreateOpen}
                    clients={clients}
                    onCreated={fetchBoard}
                />
            </div>
        </DashboardLayout>
    );
}


// ── Kanban Column ───────────────────────────────────────────────

function KanbanColumn({ column, colors, onCardClick, onDelete }) {
    return (
        <div className="flex-shrink-0 w-[260px]" data-testid={`kanban-col-${column.id}`}>
            {/* Column Header */}
            <div className={`${colors.header} text-white rounded-t-lg px-3 py-2 flex items-center justify-between`}>
                <span className="text-xs font-semibold tracking-wide">{column.label}</span>
                <Badge className="bg-white/20 text-white text-[10px] font-bold">{column.items.length}</Badge>
            </div>

            {/* Droppable area */}
            <Droppable droppableId={column.id}>
                {(provided, snapshot) => (
                    <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        className={`min-h-[200px] rounded-b-lg border border-t-0 p-2 space-y-2 transition-colors ${
                            snapshot.isDraggingOver ? colors.light + ' border-blue-300' : 'bg-slate-50/80 border-slate-200'
                        }`}
                    >
                        {column.items.map((item, index) => (
                            <Draggable key={item.commessa_id} draggableId={item.commessa_id} index={index}>
                                {(prov, snap) => (
                                    <div
                                        ref={prov.innerRef}
                                        {...prov.draggableProps}
                                        className={`rounded-lg border bg-white shadow-sm transition-shadow ${
                                            snap.isDragging ? 'shadow-lg ring-2 ' + colors.ring : 'hover:shadow-md'
                                        }`}
                                        data-testid={`kanban-card-${item.commessa_id}`}
                                    >
                                        <div className="p-3">
                                            {/* Drag handle + title */}
                                            <div className="flex items-start gap-2">
                                                <div {...prov.dragHandleProps} className="mt-0.5 cursor-grab active:cursor-grabbing">
                                                    <GripVertical className="h-3.5 w-3.5 text-slate-300" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p
                                                        className="text-sm font-semibold text-[#1E293B] truncate cursor-pointer hover:text-[#0055FF] transition-colors"
                                                        onClick={() => onCardClick(item)}
                                                    >
                                                        {item.title}
                                                    </p>
                                                </div>
                                            </div>

                                            {/* Client */}
                                            {item.client_name && (
                                                <div className="flex items-center gap-1.5 mt-2 text-xs text-slate-500">
                                                    <User className="h-3 w-3" />
                                                    <span className="truncate">{item.client_name}</span>
                                                </div>
                                            )}

                                            {/* Value + Deadline */}
                                            <div className="flex items-center justify-between mt-2">
                                                {item.value > 0 && (
                                                    <div className="flex items-center gap-1 text-xs font-mono font-semibold text-[#1E293B]">
                                                        <Euro className="h-3 w-3 text-slate-400" />
                                                        {fmtEur(item.value)}
                                                    </div>
                                                )}
                                                {item.deadline && (
                                                    <div className={`flex items-center gap-1 text-[10px] font-medium ${
                                                        isOverdue(item.deadline) ? 'text-red-600' : 'text-slate-400'
                                                    }`}>
                                                        {isOverdue(item.deadline) ? <AlertTriangle className="h-3 w-3" /> : <Calendar className="h-3 w-3" />}
                                                        {formatDeadline(item.deadline)}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Priority + Stato + Actions */}
                                            <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                                                <div className="flex items-center gap-1.5">
                                                    <Badge className={`text-[9px] ${PRIORITY_BADGE[item.priority] || PRIORITY_BADGE.media}`}>
                                                        {item.priority || 'media'}
                                                    </Badge>
                                                    {item.stato && item.stato !== 'bozza' && (
                                                        <Badge className="text-[8px] bg-blue-50 text-blue-700 font-normal">{item.stato?.replace(/_/g, ' ')}</Badge>
                                                    )}
                                                    {item.numero && (
                                                        <span className="text-[9px] font-mono text-slate-400">{item.numero}</span>
                                                    )}
                                                </div>
                                                <div className="flex gap-1">
                                                    <button
                                                        onClick={() => onCardClick(item)}
                                                        className="text-slate-400 hover:text-[#0055FF] transition-colors"
                                                        title="Apri Hub Commessa"
                                                    >
                                                        <ChevronRight className="h-3.5 w-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => onDelete(item.commessa_id)}
                                                        className="text-slate-300 hover:text-red-500 transition-colors"
                                                        title="Elimina"
                                                    >
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </Draggable>
                        ))}
                        {provided.placeholder}
                        {column.items.length === 0 && (
                            <div className="flex items-center justify-center py-8 text-xs text-slate-400">
                                <Clock className="h-4 w-4 mr-1.5 opacity-50" /> Nessuna commessa
                            </div>
                        )}
                    </div>
                )}
            </Droppable>
        </div>
    );
}


// ── Create Commessa Modal ───────────────────────────────────────

function CreateCommessaModal({ open, onOpenChange, clients, onCreated }) {
    const [form, setForm] = useState({
        title: '', client_id: '', description: '',
        value: '', deadline: '', priority: 'media',
        classe_exc: '', tipologia_chiusura: '',
    });
    const [saving, setSaving] = useState(false);

    const handleSubmit = async () => {
        if (!form.title.trim()) { toast.error('Inserire un titolo'); return; }
        setSaving(true);
        try {
            await apiRequest('/commesse/', {
                method: 'POST',
                body: {
                    ...form,
                    value: parseFloat(form.value) || 0,
                    deadline: form.deadline || null,
                },
            });
            toast.success('Commessa creata');
            onOpenChange(false);
            setForm({ title: '', client_id: '', description: '', value: '', deadline: '', priority: 'media', classe_exc: '', tipologia_chiusura: '' });
            onCreated();
        } catch (e) {
            toast.error(e.message || 'Errore creazione');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="text-lg font-bold text-[#1E293B]">Nuova Commessa</DialogTitle>
                    <p className="text-sm text-slate-500">Crea una nuova commessa per il planning cantieri</p>
                </DialogHeader>
                <div className="space-y-3 mt-2">
                    <div>
                        <Label className="text-xs">Titolo *</Label>
                        <Input
                            data-testid="input-commessa-title"
                            value={form.title}
                            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                            placeholder="es. Cancello carraio Villa Rossi"
                            className="h-9"
                        />
                    </div>
                    <div>
                        <Label className="text-xs">Cliente</Label>
                        <Select value={form.client_id || '__none__'} onValueChange={v => setForm(f => ({ ...f, client_id: v === '__none__' ? '' : v }))}>
                            <SelectTrigger data-testid="select-client" className="h-9"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                {clients.map(c => (
                                    <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <Label className="text-xs">Valore (EUR)</Label>
                            <Input
                                data-testid="input-commessa-value"
                                type="number"
                                value={form.value}
                                onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
                                placeholder="0.00"
                                className="h-9"
                            />
                        </div>
                        <div>
                            <Label className="text-xs">Scadenza</Label>
                            <Input
                                data-testid="input-commessa-deadline"
                                type="date"
                                value={form.deadline}
                                onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))}
                                className="h-9"
                            />
                        </div>
                    </div>
                    <div>
                        <Label className="text-xs">Priorità</Label>
                        <Select value={form.priority} onValueChange={v => setForm(f => ({ ...f, priority: v }))}>
                            <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="alta">Alta</SelectItem>
                                <SelectItem value="media">Media</SelectItem>
                                <SelectItem value="bassa">Bassa</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label className="text-xs">Descrizione</Label>
                        <Textarea
                            data-testid="input-commessa-desc"
                            value={form.description}
                            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                            placeholder="Dettagli sulla commessa..."
                            rows={2}
                            className="text-sm"
                        />
                    </div>
                    <Button
                        data-testid="btn-save-commessa"
                        onClick={handleSubmit}
                        disabled={saving}
                        className="w-full bg-[#0055FF] hover:bg-[#0044CC] text-white"
                    >
                        {saving ? 'Salvataggio...' : 'Crea Commessa'}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
