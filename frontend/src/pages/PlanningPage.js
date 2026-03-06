/**
 * Planning Cantieri — Kanban Board for workshop project tracking.
 * Uses native HTML5 Drag & Drop (no library — works with React 19).
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
    Plus, GripVertical, Calendar, Euro, User, Trash2,
    LayoutGrid, Clock, AlertTriangle, ChevronRight, FileText, Hammer,
    ChevronLeft,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useConfirm } from '../components/ConfirmProvider';

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

// ── Main Page ────────────────────────────────────────────────────

export default function PlanningPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const [columns, setColumns] = useState([]);
    const [acceptedPrevs, setAcceptedPrevs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [clients, setClients] = useState([]);
    const [draggingId, setDraggingId] = useState(null);
    const [dragOverCol, setDragOverCol] = useState(null);

    const fetchBoard = useCallback(async () => {
        try {
            const data = await apiRequest('/commesse/board/view');
            const cols = data.columns || [];
            const prevs = [];
            const cleanCols = cols.map(col => {
                const colPrevs = col.items.filter(i => i.is_preventivo);
                prevs.push(...colPrevs);
                return { ...col, items: col.items.filter(i => !i.is_preventivo) };
            });
            setColumns(cleanCols);
            setAcceptedPrevs(prevs);
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

    // ── Native DnD handlers ──────────────────────────────────────

    const handleDragStart = (e, itemId, isPreventivo = false) => {
        setDraggingId(itemId);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', itemId);
        e.dataTransfer.setData('application/x-type', isPreventivo ? 'preventivo' : 'commessa');
        if (e.target) {
            requestAnimationFrame(() => {
                e.target.style.opacity = '0.4';
            });
        }
    };

    const handleDragEnd = (e) => {
        e.target.style.opacity = '1';
        setDraggingId(null);
        setDragOverCol(null);
    };

    const handleDragOver = (e, colId) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragOverCol !== colId) setDragOverCol(colId);
    };

    const handleDragLeave = (e, colId) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
            if (dragOverCol === colId) setDragOverCol(null);
        }
    };

    const handleDrop = async (e, targetColId) => {
        e.preventDefault();
        setDragOverCol(null);
        const itemId = e.dataTransfer.getData('text/plain');
        const itemType = e.dataTransfer.getData('application/x-type');
        if (!itemId) return;

        if (itemType === 'preventivo') {
            // Dragging a preventivo → create commessa + set status
            const prev = acceptedPrevs.find(p => p.preventivo_id === itemId);
            if (!prev) return;

            // Optimistic: remove from preventivi
            setAcceptedPrevs(old => old.filter(p => p.preventivo_id !== itemId));

            try {
                const result = await apiRequest(`/commesse/from-preventivo/${itemId}`, { method: 'POST' });
                // Now move to target column if not "preventivo"
                if (targetColId !== 'preventivo') {
                    await apiRequest(`/commesse/${result.commessa_id}/status`, {
                        method: 'PATCH',
                        body: { new_status: targetColId },
                    });
                }
                toast.success('Commessa creata e spostata');
                fetchBoard(); // refresh to get real data
            } catch (err) {
                toast.error(err.message || 'Errore creazione commessa');
                fetchBoard(); // rollback
            }
            return;
        }

        // Regular commessa drag
        const srcCol = columns.find(c => c.items.some(i => i.commessa_id === itemId));
        if (!srcCol || srcCol.id === targetColId) return;

        // Optimistic update
        setColumns(prev => {
            const next = prev.map(col => ({ ...col, items: [...col.items] }));
            const src = next.find(c => c.id === srcCol.id);
            const dst = next.find(c => c.id === targetColId);
            if (!src || !dst) return prev;
            const idx = src.items.findIndex(i => i.commessa_id === itemId);
            if (idx === -1) return prev;
            const [moved] = src.items.splice(idx, 1);
            moved.status = targetColId;
            dst.items.push(moved);
            return next;
        });

        try {
            await apiRequest(`/commesse/${itemId}/status`, {
                method: 'PATCH',
                body: { new_status: targetColId },
            });
            toast.success('Stato aggiornato');
        } catch (err) {
            toast.error('Errore aggiornamento stato');
            fetchBoard();
        }
    };

    // ── Other handlers ───────────────────────────────────────────

    const handleDelete = async (commessaId) => {
        if (!(await confirm('Eliminare questa commessa?\n\nLe fatture collegate NON verranno eliminate e resteranno valide nel sistema SDI.'))) return;
        try {
            await apiRequest(`/commesse/${commessaId}`, { method: 'DELETE' });
            toast.success('Commessa eliminata (fatture intatte)');
            fetchBoard();
        } catch (e) { toast.error(e.message); }
    };

    const handleCreateFromPreventivo = async (preventivoId) => {
        try {
            const result = await apiRequest(`/commesse/from-preventivo/${preventivoId}`, { method: 'POST' });
            toast.success('Commessa creata con successo');
            fetchBoard();
            navigate(`/commesse/${result.commessa_id}`);
        } catch (e) { toast.error(e.message || 'Errore creazione commessa'); }
    };

    const totalCommesse = columns.reduce((acc, col) => acc + col.items.length, 0);
    const totalPreventivi = acceptedPrevs.length;
    const totalValue = columns.reduce((acc, col) => acc + col.items.reduce((a, i) => a + (i.value || 0), 0), 0)
        + acceptedPrevs.reduce((a, i) => a + (i.value || 0), 0);

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
                            {totalCommesse} commesse{totalPreventivi > 0 ? ` + ${totalPreventivi} preventivi accettati` : ''} &middot; Valore totale: {fmtEur(totalValue)}
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
                    <ScrollableBoard
                        columns={columns}
                        acceptedPrevs={acceptedPrevs}
                        draggingId={draggingId}
                        dragOverCol={dragOverCol}
                        onDragStart={handleDragStart}
                        onDragEnd={handleDragEnd}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onCardClick={(c) => {
                            if (c.is_preventivo) navigate(`/preventivi/${c.preventivo_id}`);
                            else navigate(`/commesse/${c.commessa_id}`);
                        }}
                        onDelete={handleDelete}
                        onCreateCommessa={handleCreateFromPreventivo}
                    />
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


// ── Scrollable Board wrapper ─────────────────────────────────────

function ScrollableBoard({ columns, acceptedPrevs, draggingId, dragOverCol,
    onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop,
    onCardClick, onDelete, onCreateCommessa }) {
    const scrollRef = useRef(null);
    const leftRef = useRef(null);
    const rightRef = useRef(null);

    const checkScroll = useCallback(() => {
        const el = scrollRef.current;
        if (!el) return;
        const showLeft = el.scrollLeft > 10;
        const showRight = el.scrollLeft < el.scrollWidth - el.clientWidth - 10;
        if (leftRef.current) leftRef.current.style.display = showLeft ? 'flex' : 'none';
        if (rightRef.current) rightRef.current.style.display = showRight ? 'flex' : 'none';
    }, []);

    useEffect(() => {
        const el = scrollRef.current;
        if (!el) return;
        checkScroll();
        const t = setTimeout(checkScroll, 200);
        el.addEventListener('scroll', checkScroll, { passive: true });
        window.addEventListener('resize', checkScroll);
        return () => {
            clearTimeout(t);
            el.removeEventListener('scroll', checkScroll);
            window.removeEventListener('resize', checkScroll);
        };
    }, [checkScroll, columns]);

    const scroll = (dir) => {
        const el = scrollRef.current;
        if (!el) return;
        el.scrollBy({ left: dir * 280, behavior: 'smooth' });
    };

    return (
        <div className="relative" data-testid="kanban-board-wrapper">
            <button
                ref={leftRef}
                data-testid="scroll-left-btn"
                onClick={() => scroll(-1)}
                style={{ display: 'none' }}
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 h-10 w-10 rounded-full bg-white/90 shadow-lg border border-slate-200 items-center justify-center hover:bg-slate-50 transition-colors"
            >
                <ChevronLeft className="h-5 w-5 text-slate-600" />
            </button>

            <button
                ref={rightRef}
                data-testid="scroll-right-btn"
                onClick={() => scroll(1)}
                style={{ display: 'none' }}
                className="absolute right-0 top-1/2 -translate-y-1/2 z-10 h-10 w-10 rounded-full bg-white/90 shadow-lg border border-slate-200 items-center justify-center hover:bg-slate-50 transition-colors"
            >
                <ChevronRight className="h-5 w-5 text-slate-600" />
            </button>

            <div
                ref={scrollRef}
                className="flex gap-3 overflow-x-auto pb-4 px-6 scroll-smooth"
                style={{ scrollbarWidth: 'thin' }}
                data-testid="kanban-board"
            >
                {columns.map(col => (
                    <KanbanColumn
                        key={col.id}
                        column={col}
                        colors={COL_COLORS[col.id] || COL_COLORS.preventivo}
                        prevItems={col.id === 'preventivo' ? acceptedPrevs : []}
                        draggingId={draggingId}
                        isDragOver={dragOverCol === col.id}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                        onDragOver={onDragOver}
                        onDragLeave={onDragLeave}
                        onDrop={onDrop}
                        onCardClick={onCardClick}
                        onDelete={onDelete}
                        onCreateCommessa={onCreateCommessa}
                    />
                ))}
            </div>
        </div>
    );
}


// ── Kanban Column ────────────────────────────────────────────────

function KanbanColumn({ column, colors, prevItems, draggingId, isDragOver,
    onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop,
    onCardClick, onDelete, onCreateCommessa }) {
    const totalCount = column.items.length + (prevItems?.length || 0);

    return (
        <div className="flex-shrink-0 w-[260px]" data-testid={`kanban-col-${column.id}`}>
            {/* Column Header */}
            <div className={`${colors.header} text-white rounded-t-lg px-3 py-2 flex items-center justify-between`}>
                <span className="text-xs font-semibold tracking-wide">{column.label}</span>
                <Badge className="bg-white/20 text-white text-[10px] font-bold">{totalCount}</Badge>
            </div>

            {/* Drop zone (covers both preventivi and commesse) */}
            <div
                onDragOver={(e) => onDragOver(e, column.id)}
                onDragLeave={(e) => onDragLeave(e, column.id)}
                onDrop={(e) => onDrop(e, column.id)}
                className={`min-h-[120px] rounded-b-lg border border-t-0 p-2 space-y-2 transition-all duration-200 ${
                    isDragOver
                        ? `${colors.light} border-2 border-dashed border-blue-400 scale-[1.01]`
                        : 'bg-slate-50/80 border-slate-200'
                }`}
                data-testid={`kanban-drop-${column.id}`}
            >
                {/* Preventivi accettati (draggable) */}
                {prevItems && prevItems.map(item => (
                    <PreventivoCard
                        key={item.commessa_id}
                        item={item}
                        onCardClick={onCardClick}
                        onCreateCommessa={onCreateCommessa}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                        isDragging={draggingId === item.preventivo_id}
                    />
                ))}

                {/* Regular commesse (draggable) */}
                {column.items.map(item => (
                    <CommessaCard
                        key={item.commessa_id}
                        item={item}
                        colors={colors}
                        isDragging={draggingId === item.commessa_id}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                        onCardClick={onCardClick}
                        onDelete={onDelete}
                    />
                ))}

                {totalCount === 0 && (
                    <div className="flex items-center justify-center py-8 text-xs text-slate-400">
                        <Clock className="h-4 w-4 mr-1.5 opacity-50" /> Nessuna commessa
                    </div>
                )}
            </div>
        </div>
    );
}


// ── Preventivo Accettato Card (non-draggable) ────────────────────

function PreventivoCard({ item, onCardClick, onCreateCommessa, onDragStart, onDragEnd, isDragging }) {
    const [creating, setCreating] = useState(false);

    const handleCreate = async (e) => {
        e.stopPropagation();
        setCreating(true);
        try {
            await onCreateCommessa(item.preventivo_id);
        } finally {
            setCreating(false);
        }
    };

    return (
        <div
            draggable="true"
            onDragStart={(e) => onDragStart(e, item.preventivo_id, true)}
            onDragEnd={onDragEnd}
            className={`rounded-lg border-2 border-dashed border-emerald-300 bg-emerald-50/60 shadow-sm hover:shadow-md transition-all cursor-grab active:cursor-grabbing select-none ${
                isDragging ? 'opacity-40 scale-95' : ''
            }`}
            data-testid={`kanban-card-prev-${item.preventivo_id}`}
            onClick={() => onCardClick(item)}
        >
            <div className="p-3">
                <div className="flex items-start gap-2">
                    <FileText className="h-4 w-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-[#1E293B] truncate">{item.title}</p>
                    </div>
                </div>
                <div className="mt-2">
                    <Badge className="text-[9px] bg-emerald-100 text-emerald-800 font-semibold">Preventivo Accettato</Badge>
                    {item.numero && <span className="ml-1.5 text-[9px] font-mono text-slate-400">{item.numero}</span>}
                </div>
                {item.client_name && (
                    <div className="flex items-center gap-1.5 mt-2 text-xs text-slate-500">
                        <User className="h-3 w-3" /><span className="truncate">{item.client_name}</span>
                    </div>
                )}
                {item.value > 0 && (
                    <div className="flex items-center gap-1 mt-2 text-xs font-mono font-semibold text-[#1E293B]">
                        <Euro className="h-3 w-3 text-slate-400" />{fmtEur(item.value)}
                    </div>
                )}
                <button
                    data-testid={`btn-create-commessa-${item.preventivo_id}`}
                    onClick={handleCreate}
                    disabled={creating}
                    className="mt-2 w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-[11px] font-semibold bg-[#0055FF] hover:bg-[#0044CC] text-white transition-colors disabled:opacity-50"
                >
                    <Hammer className="h-3 w-3" />
                    {creating ? 'Creazione...' : 'Crea Commessa'}
                </button>
            </div>
        </div>
    );
}


// ── Commessa Card (draggable via native HTML5 DnD) ───────────────

function CommessaCard({ item, colors, isDragging, onDragStart, onDragEnd, onCardClick, onDelete }) {
    return (
        <div
            draggable="true"
            onDragStart={(e) => onDragStart(e, item.commessa_id)}
            onDragEnd={onDragEnd}
            className={`rounded-lg border bg-white shadow-sm transition-all cursor-grab active:cursor-grabbing select-none ${
                isDragging ? 'opacity-40 ring-2 ' + colors.ring + ' scale-95' : 'hover:shadow-md'
            }`}
            data-testid={`kanban-card-${item.commessa_id}`}
        >
            <div className="p-3">
                {/* Title row */}
                <div className="flex items-start gap-2">
                    <GripVertical className="h-4 w-4 text-slate-300 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                        <p
                            className="text-sm font-semibold text-[#1E293B] truncate cursor-pointer hover:text-[#0055FF] transition-colors"
                            onClick={(e) => { e.stopPropagation(); onCardClick(item); }}
                        >
                            {item.title}
                        </p>
                    </div>
                </div>

                {/* Client */}
                {item.client_name && (
                    <div className="flex items-center gap-1.5 mt-2 text-xs text-slate-500">
                        <User className="h-3 w-3" /><span className="truncate">{item.client_name}</span>
                    </div>
                )}

                {/* Value + Deadline */}
                <div className="flex items-center justify-between mt-2">
                    {item.value > 0 && (
                        <div className="flex items-center gap-1 text-xs font-mono font-semibold text-[#1E293B]">
                            <Euro className="h-3 w-3 text-slate-400" />{fmtEur(item.value)}
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

                {/* Priority + Actions */}
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                    <div className="flex items-center gap-1.5">
                        <Badge className={`text-[9px] ${PRIORITY_BADGE[item.priority] || PRIORITY_BADGE.media}`}>
                            {item.priority || 'media'}
                        </Badge>
                        {item.stato && item.stato !== 'bozza' && (
                            <Badge className="text-[8px] bg-blue-50 text-blue-700 font-normal">{item.stato?.replace(/_/g, ' ')}</Badge>
                        )}
                        {item.numero && (
                            <span className={`text-[9px] font-mono ${item.generica ? 'text-amber-600 font-semibold' : 'text-slate-400'}`}>
                                {item.generica ? 'GEN' : item.numero}
                            </span>
                        )}
                    </div>
                    <div className="flex gap-1.5">
                        <button
                            onClick={(e) => { e.stopPropagation(); onCardClick(item); }}
                            className="p-1 rounded text-slate-400 hover:text-[#0055FF] hover:bg-blue-50 transition-colors"
                            title="Apri Hub Commessa"
                            data-testid={`btn-open-${item.commessa_id}`}
                        >
                            <ChevronRight className="h-4 w-4" />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); onDelete(item.commessa_id); }}
                            className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                            title="Elimina commessa (le fatture NON vengono toccate)"
                            data-testid={`btn-delete-${item.commessa_id}`}
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}


// ── Create Commessa Modal ────────────────────────────────────────

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
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <Label className="text-xs">Classe EXC (EN 1090)</Label>
                            <select
                                value={form.classe_exc}
                                onChange={e => setForm(f => ({ ...f, classe_exc: e.target.value }))}
                                className="w-full h-9 text-sm rounded-md border border-input bg-transparent px-2 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                data-testid="select-classe-exc"
                            >
                                <option value="">-- Non spec. --</option>
                                <option value="EXC1">EXC1</option>
                                <option value="EXC2">EXC2</option>
                                <option value="EXC3">EXC3</option>
                                <option value="EXC4">EXC4</option>
                            </select>
                        </div>
                        <div>
                            <Label className="text-xs">Tipologia Chiusura</Label>
                            <select
                                value={form.tipologia_chiusura}
                                onChange={e => setForm(f => ({ ...f, tipologia_chiusura: e.target.value }))}
                                className="w-full h-9 text-sm rounded-md border border-input bg-transparent px-2 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                data-testid="select-tipologia-chiusura"
                            >
                                <option value="">-- Non spec. --</option>
                                <option value="cancello">Cancello</option>
                                <option value="ringhiera">Ringhiera</option>
                                <option value="porta">Porta</option>
                                <option value="scala">Scala</option>
                                <option value="struttura">Struttura</option>
                                <option value="recinzione">Recinzione</option>
                                <option value="pensilina">Pensilina</option>
                                <option value="altro">Altro</option>
                            </select>
                        </div>
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
