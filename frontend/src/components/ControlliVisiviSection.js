/**
 * ControlliVisiviSection — Gestione Controlli Visivi per una commessa.
 * Obbligatori per EN 1090 e EN 13241 prima di generare il Pacco Documenti.
 * Se esito NOK → crea automaticamente NC + alert admin.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
    Eye, ThumbsUp, ThumbsDown, Plus, Loader2, AlertTriangle, CheckCircle2, Camera,
} from 'lucide-react';

export default function ControlliVisiviSection({ commessaId, vociLavoro = [], normativaTipo }) {
    const [controlli, setControlli] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [completeness, setCompleteness] = useState(null);

    // Form
    const [selVoce, setSelVoce] = useState('__principale__');
    const [esito, setEsito] = useState(null);
    const [note, setNote] = useState('');

    // Build voce list (obbligatorie only: EN_1090 and EN_13241)
    const vociObbligatorie = [];
    if (['EN_1090', 'EN_13241'].includes(normativaTipo)) {
        vociObbligatorie.push({ voce_id: '__principale__', descrizione: 'Commessa principale', normativa_tipo: normativaTipo });
    }
    vociLavoro.forEach(v => {
        if (['EN_1090', 'EN_13241'].includes(v.normativa_tipo)) {
            vociObbligatorie.push(v);
        }
    });

    const fetchData = useCallback(async () => {
        try {
            const [ctrl, check] = await Promise.all([
                apiRequest(`/controlli-visivi/${commessaId}`),
                apiRequest(`/controlli-visivi/${commessaId}/check`).catch(() => null),
            ]);
            setControlli(ctrl.controlli || []);
            setCompleteness(check);
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleCreate = async () => {
        if (esito === null) { toast.error('Seleziona esito OK o NOK'); return; }
        setCreating(true);
        try {
            const voce = vociObbligatorie.find(v => v.voce_id === selVoce) || {};
            await apiRequest('/controlli-visivi', {
                method: 'POST',
                body: {
                    commessa_id: commessaId,
                    voce_id: selVoce === '__principale__' ? '' : selVoce,
                    normativa_tipo: voce.normativa_tipo || normativaTipo,
                    esito,
                    note,
                },
            });
            toast.success(esito ? 'Controllo visivo OK' : 'Controllo NOK — NC creata automaticamente');
            setShowCreate(false);
            setEsito(null);
            setNote('');
            fetchData();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setCreating(false);
        }
    };

    if (loading) return <div className="text-center py-4"><Loader2 className="h-4 w-4 animate-spin mx-auto text-slate-400" /></div>;

    const isComplete = completeness?.completo;

    return (
        <div className="space-y-3" data-testid="controlli-visivi-section">
            {/* Status banner */}
            {completeness && (
                <div className={`flex items-center gap-2 p-2.5 rounded-lg text-xs font-medium ${isComplete ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`} data-testid="ctrl-status-banner">
                    {isComplete ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                    {completeness.messaggio}
                </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500">{controlli.length} controllo/i eseguito/i</p>
                {vociObbligatorie.length > 0 && (
                    <Button size="sm" variant="outline" onClick={() => setShowCreate(!showCreate)} data-testid="btn-add-ctrl">
                        <Plus className="h-3 w-3 mr-1" /> Nuovo Controllo
                    </Button>
                )}
            </div>

            {/* Create form */}
            {showCreate && (
                <div className="border border-blue-200 bg-blue-50 rounded-lg p-3 space-y-3" data-testid="ctrl-create-form">
                    <p className="text-sm font-semibold text-blue-800">Controllo Visivo Finale</p>

                    {/* Voce selector */}
                    {vociObbligatorie.length > 1 && (
                        <select value={selVoce} onChange={e => setSelVoce(e.target.value)}
                            className="w-full text-xs border rounded-md px-2 py-1.5 bg-white" data-testid="ctrl-voce-select">
                            {vociObbligatorie.map(v => (
                                <option key={v.voce_id} value={v.voce_id}>{v.descrizione} ({v.normativa_tipo})</option>
                            ))}
                        </select>
                    )}

                    {/* Esito buttons */}
                    <div className="flex gap-3">
                        <button onClick={() => setEsito(true)} data-testid="ctrl-esito-ok"
                            className={`flex-1 h-14 rounded-xl flex items-center justify-center gap-2 text-lg font-bold transition-all
                                ${esito === true ? 'bg-emerald-500 text-white ring-2 ring-emerald-400 shadow-lg' : 'bg-white border-2 border-slate-200 text-slate-400 hover:border-emerald-300'}`}>
                            <ThumbsUp className="h-5 w-5" /> OK
                        </button>
                        <button onClick={() => setEsito(false)} data-testid="ctrl-esito-nok"
                            className={`flex-1 h-14 rounded-xl flex items-center justify-center gap-2 text-lg font-bold transition-all
                                ${esito === false ? 'bg-red-500 text-white ring-2 ring-red-400 shadow-lg' : 'bg-white border-2 border-slate-200 text-slate-400 hover:border-red-300'}`}>
                            <ThumbsDown className="h-5 w-5" /> NOK
                        </button>
                    </div>

                    <Textarea placeholder="Note (dettagli ispezione)" value={note}
                        onChange={e => setNote(e.target.value)} className="text-xs min-h-[60px]" data-testid="ctrl-note" />

                    <div className="flex gap-2 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => { setShowCreate(false); setEsito(null); }}>Annulla</Button>
                        <Button size="sm" onClick={handleCreate} disabled={creating || esito === null} data-testid="btn-confirm-ctrl">
                            {creating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Eye className="h-3 w-3 mr-1" />}
                            Registra
                        </Button>
                    </div>
                </div>
            )}

            {/* Controls list */}
            {controlli.length === 0 ? (
                <p className="text-xs text-slate-400 text-center py-3">Nessun controllo visivo registrato.</p>
            ) : (
                <div className="space-y-2">
                    {controlli.map(c => (
                        <div key={c.controllo_id} className="flex items-center gap-3 p-2.5 bg-white border rounded-lg" data-testid={`ctrl-${c.controllo_id}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${c.esito ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                                {c.esito ? <ThumbsUp className="h-4 w-4" /> : <ThumbsDown className="h-4 w-4" />}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-xs font-semibold text-slate-700 truncate">
                                    {c.voce_id ? `Voce: ${c.voce_id}` : 'Commessa principale'} — {c.normativa_tipo}
                                </p>
                                {c.note && <p className="text-xs text-slate-400 truncate">{c.note}</p>}
                                <p className="text-[10px] text-slate-400">{new Date(c.created_at).toLocaleDateString('it-IT')} {c.operatore_nome && `— ${c.operatore_nome}`}</p>
                            </div>
                            <Badge className={`${c.esito ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'} text-[10px] shrink-0`}>
                                {c.esito ? 'OK' : 'NOK'}
                            </Badge>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
