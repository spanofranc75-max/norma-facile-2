/**
 * RegistroNCSection — Registro Non Conformità per una commessa.
 * Mostra tutte le NC (auto-generate da checklist/controlli visivi NOK).
 * Permette: aggiornare stato, aggiungere azione correttiva, chiudere NC.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
    AlertTriangle, CheckCircle2, Clock, Loader2,
    ChevronDown, ChevronUp, FileWarning,
} from 'lucide-react';

const STATO_BADGE = {
    aperta: { label: 'Aperta', cls: 'bg-red-100 text-red-700', icon: AlertTriangle },
    in_corso: { label: 'In Corso', cls: 'bg-amber-100 text-amber-700', icon: Clock },
    chiusa: { label: 'Chiusa', cls: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
};

export default function RegistroNCSection({ commessaId }) {
    const [ncs, setNcs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState(null);
    const [updating, setUpdating] = useState(null);

    // Edit state per NC
    const [editState, setEditState] = useState({});

    const fetchNCs = useCallback(async () => {
        try {
            const res = await apiRequest(`/registro-nc/${commessaId}`);
            setNcs(res.non_conformita || []);
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { fetchNCs(); }, [fetchNCs]);

    const handleUpdate = async (ncId, updates) => {
        setUpdating(ncId);
        try {
            await apiRequest(`/registro-nc/${ncId}`, {
                method: 'PATCH',
                body: updates,
            });
            toast.success(updates.stato === 'chiusa' ? 'NC chiusa' : 'NC aggiornata');
            fetchNCs();
            setExpandedId(null);
            setEditState(prev => { const n = { ...prev }; delete n[ncId]; return n; });
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUpdating(null);
        }
    };

    if (loading) return <div className="text-center py-4"><Loader2 className="h-4 w-4 animate-spin mx-auto text-slate-400" /></div>;

    const aperte = ncs.filter(n => n.stato === 'aperta').length;
    const inCorso = ncs.filter(n => n.stato === 'in_corso').length;
    const chiuse = ncs.filter(n => n.stato === 'chiusa').length;

    return (
        <div className="space-y-3" data-testid="registro-nc-section">
            {/* Summary bar */}
            {ncs.length > 0 && (
                <div className="flex items-center gap-3 text-xs" data-testid="nc-summary">
                    {aperte > 0 && <span className="flex items-center gap-1 text-red-600 font-medium"><span className="w-2 h-2 rounded-full bg-red-500" />{aperte} aperte</span>}
                    {inCorso > 0 && <span className="flex items-center gap-1 text-amber-600 font-medium"><span className="w-2 h-2 rounded-full bg-amber-400" />{inCorso} in corso</span>}
                    {chiuse > 0 && <span className="flex items-center gap-1 text-emerald-600 font-medium"><span className="w-2 h-2 rounded-full bg-emerald-500" />{chiuse} chiuse</span>}
                </div>
            )}

            {/* NC list */}
            {ncs.length === 0 ? (
                <div className="text-center py-4">
                    <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                    <p className="text-xs text-slate-400">Nessuna Non Conformità registrata.</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {ncs.map(nc => {
                        const badge = STATO_BADGE[nc.stato] || STATO_BADGE.aperta;
                        const BadgeIcon = badge.icon;
                        const expanded = expandedId === nc.nc_id;
                        const edit = editState[nc.nc_id] || {};

                        return (
                            <div key={nc.nc_id} className={`border rounded-lg p-3 bg-white ${nc.stato === 'aperta' ? 'border-red-200' : nc.stato === 'in_corso' ? 'border-amber-200' : 'border-slate-200'}`}
                                data-testid={`nc-${nc.nc_id}`}>
                                <div className="flex items-start gap-3 cursor-pointer" onClick={() => setExpandedId(expanded ? null : nc.nc_id)}>
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${badge.cls}`}>
                                        <BadgeIcon className="h-4 w-4" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-xs font-semibold text-slate-800">{nc.descrizione}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <Badge className={`${badge.cls} text-[10px]`}>{badge.label}</Badge>
                                            <span className="text-[10px] text-slate-400">{nc.tipo}</span>
                                            {nc.operatore_nome && <span className="text-[10px] text-slate-400">— {nc.operatore_nome}</span>}
                                        </div>
                                        <p className="text-[10px] text-slate-400 mt-0.5">{new Date(nc.created_at).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' })}</p>
                                    </div>
                                    <div className="shrink-0">
                                        {expanded ? <ChevronUp className="h-3 w-3 text-slate-400" /> : <ChevronDown className="h-3 w-3 text-slate-400" />}
                                    </div>
                                </div>

                                {expanded && (
                                    <div className="mt-3 pt-3 border-t space-y-2">
                                        {nc.azione_correttiva && (
                                            <div className="bg-blue-50 rounded-md p-2">
                                                <p className="text-[10px] font-semibold text-blue-700">Azione Correttiva:</p>
                                                <p className="text-xs text-blue-600">{nc.azione_correttiva}</p>
                                            </div>
                                        )}
                                        {nc.note_chiusura && (
                                            <div className="bg-emerald-50 rounded-md p-2">
                                                <p className="text-[10px] font-semibold text-emerald-700">Note Chiusura:</p>
                                                <p className="text-xs text-emerald-600">{nc.note_chiusura}</p>
                                            </div>
                                        )}

                                        {nc.stato !== 'chiusa' && (
                                            <div className="space-y-2 pt-1">
                                                <Textarea placeholder="Azione correttiva..."
                                                    value={edit.azione_correttiva || nc.azione_correttiva || ''}
                                                    onChange={e => setEditState(prev => ({ ...prev, [nc.nc_id]: { ...edit, azione_correttiva: e.target.value } }))}
                                                    className="text-xs min-h-[50px]" data-testid={`nc-azione-${nc.nc_id}`} />

                                                <div className="flex gap-2">
                                                    {nc.stato === 'aperta' && (
                                                        <Button size="sm" variant="outline"
                                                            disabled={updating === nc.nc_id}
                                                            onClick={() => handleUpdate(nc.nc_id, { stato: 'in_corso', azione_correttiva: edit.azione_correttiva || nc.azione_correttiva })}
                                                            data-testid={`nc-in-corso-${nc.nc_id}`}>
                                                            <Clock className="h-3 w-3 mr-1" /> In Corso
                                                        </Button>
                                                    )}
                                                    <Button size="sm"
                                                        disabled={updating === nc.nc_id}
                                                        onClick={() => handleUpdate(nc.nc_id, {
                                                            stato: 'chiusa',
                                                            azione_correttiva: edit.azione_correttiva || nc.azione_correttiva,
                                                            note_chiusura: edit.note_chiusura || 'Azione completata',
                                                        })}
                                                        className="bg-emerald-600 hover:bg-emerald-500"
                                                        data-testid={`nc-chiudi-${nc.nc_id}`}>
                                                        {updating === nc.nc_id ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
                                                        Chiudi NC
                                                    </Button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
