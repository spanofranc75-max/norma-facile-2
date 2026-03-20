/**
 * SfridiSection — Gestione Sfridi (materiale avanzato) per una commessa.
 * Mostra sfridi creati da questa commessa, con link cliccabile al certificato 3.1.
 * Permette: creare nuovo sfrido, prelevare da magazzino, marcare esaurito.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    Plus, PackagePlus, PackageMinus, FileText, ExternalLink,
    Archive, Loader2, ChevronDown, ChevronUp,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function SfridiSection({ commessaId, docs = [] }) {
    const [sfridi, setSfridi] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [expandedId, setExpandedId] = useState(null);

    // Form state
    const [form, setForm] = useState({ tipo_materiale: '', quantita: '', numero_colata: '', certificato_doc_id: '', note: '' });

    // Prelievo state
    const [prelievoForm, setPrelievoForm] = useState({ commessa_id_destinazione: '', quantita_prelevata: '', note: '' });
    const [prelevandoId, setPrelevandoId] = useState(null);

    const fetchSfridi = useCallback(async () => {
        try {
            const res = await apiRequest(`/sfridi/commessa/${commessaId}`);
            setSfridi(res.sfridi || []);
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { fetchSfridi(); }, [fetchSfridi]);

    // Get cert 3.1 documents for the dropdown
    const certDocs = docs.filter(d => d.tipo === 'certificato_31' || d.tipo === 'certificato');

    const handleCreate = async () => {
        if (!form.tipo_materiale || !form.quantita) {
            toast.error('Tipo materiale e quantità obbligatori');
            return;
        }
        setCreating(true);
        try {
            await apiRequest('/sfridi', {
                method: 'POST',
                body: {
                    commessa_id: commessaId,
                    tipo_materiale: form.tipo_materiale,
                    quantita: form.quantita,
                    numero_colata: form.numero_colata,
                    certificato_doc_id: form.certificato_doc_id,
                    note: form.note,
                },
            });
            toast.success('Sfrido registrato a magazzino');
            setShowCreate(false);
            setForm({ tipo_materiale: '', quantita: '', numero_colata: '', certificato_doc_id: '', note: '' });
            fetchSfridi();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setCreating(false);
        }
    };

    const handlePrelievo = async (sfridoId) => {
        if (!prelievoForm.commessa_id_destinazione || !prelievoForm.quantita_prelevata) {
            toast.error('Commessa destinazione e quantità obbligatori');
            return;
        }
        try {
            await apiRequest(`/sfridi/${sfridoId}/preleva`, {
                method: 'POST',
                body: prelievoForm,
            });
            toast.success('Prelievo registrato');
            setPrelevandoId(null);
            setPrelievoForm({ commessa_id_destinazione: '', quantita_prelevata: '', note: '' });
            fetchSfridi();
        } catch (e) {
            toast.error(e.message);
        }
    };

    const handleEsaurito = async (sfridoId) => {
        try {
            await apiRequest(`/sfridi/${sfridoId}/esaurito`, { method: 'PATCH' });
            toast.success('Sfrido marcato come esaurito');
            fetchSfridi();
        } catch (e) {
            toast.error(e.message);
        }
    };

    // Open cert in new tab (clickable link integration)
    const openCertificato = async (docId, commessaOrigine) => {
        try {
            const cid = commessaOrigine || commessaId;
            const res = await fetch(`${API}/api/commesse/${cid}/documenti/${docId}/download`, { credentials: 'include' });
            if (!res.ok) throw new Error('Download fallito');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        } catch {
            toast.error('Impossibile aprire il certificato');
        }
    };

    if (loading) return <div className="text-center py-4 text-xs text-slate-400"><Loader2 className="h-4 w-4 animate-spin mx-auto" /></div>;

    const STATO_BADGE = {
        disponibile: { label: 'Disponibile', cls: 'bg-emerald-100 text-emerald-700' },
        parziale: { label: 'Parziale', cls: 'bg-amber-100 text-amber-700' },
        esaurito: { label: 'Esaurito', cls: 'bg-slate-200 text-slate-500' },
    };

    return (
        <div className="space-y-3" data-testid="sfridi-section">
            {/* Header + Add button */}
            <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500">{sfridi.length} sfrido/i a magazzino</p>
                <Button size="sm" variant="outline" onClick={() => setShowCreate(!showCreate)} data-testid="btn-add-sfrido">
                    <Plus className="h-3 w-3 mr-1" /> Registra Sfrido
                </Button>
            </div>

            {/* Create form */}
            {showCreate && (
                <div className="border border-blue-200 bg-blue-50 rounded-lg p-3 space-y-2" data-testid="sfrido-create-form">
                    <p className="text-sm font-semibold text-blue-800">Nuovo Sfrido a Magazzino</p>
                    <div className="grid grid-cols-2 gap-2">
                        <Input placeholder="Tipo materiale (es. IPE 200)" value={form.tipo_materiale}
                            onChange={e => setForm(f => ({ ...f, tipo_materiale: e.target.value }))}
                            data-testid="sfrido-tipo" className="text-xs" />
                        <Input placeholder="Quantita' (es. 3 barre)" value={form.quantita}
                            onChange={e => setForm(f => ({ ...f, quantita: e.target.value }))}
                            data-testid="sfrido-quantita" className="text-xs" />
                        <Input placeholder="N. Colata (opzionale)" value={form.numero_colata}
                            onChange={e => setForm(f => ({ ...f, numero_colata: e.target.value }))}
                            data-testid="sfrido-colata" className="text-xs" />
                        <select value={form.certificato_doc_id}
                            onChange={e => setForm(f => ({ ...f, certificato_doc_id: e.target.value }))}
                            className="text-xs border rounded-md px-2 py-1 bg-white" data-testid="sfrido-cert-select">
                            <option value="">-- Certificato 3.1 --</option>
                            {certDocs.map(d => (
                                <option key={d.doc_id} value={d.doc_id}>{d.nome_file || d.doc_id}</option>
                            ))}
                        </select>
                    </div>
                    <Input placeholder="Note (opzionale)" value={form.note}
                        onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                        className="text-xs" />
                    <div className="flex gap-2 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => setShowCreate(false)}>Annulla</Button>
                        <Button size="sm" onClick={handleCreate} disabled={creating} data-testid="btn-confirm-sfrido">
                            {creating ? <Loader2 className="h-3 w-3 animate-spin" /> : <PackagePlus className="h-3 w-3 mr-1" />}
                            Registra
                        </Button>
                    </div>
                </div>
            )}

            {/* Sfridi list */}
            {sfridi.length === 0 ? (
                <p className="text-xs text-slate-400 text-center py-4">Nessuno sfrido registrato per questa commessa.</p>
            ) : (
                <div className="space-y-2">
                    {sfridi.map(s => {
                        const badge = STATO_BADGE[s.stato] || STATO_BADGE.disponibile;
                        const expanded = expandedId === s.sfrido_id;
                        return (
                            <div key={s.sfrido_id} className="border rounded-lg p-3 bg-white" data-testid={`sfrido-${s.sfrido_id}`}>
                                <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpandedId(expanded ? null : s.sfrido_id)}>
                                    <div className="min-w-0">
                                        <p className="text-sm font-semibold text-slate-800 truncate">{s.tipo_materiale}</p>
                                        <p className="text-xs text-slate-500">{s.quantita} {s.numero_colata && `— Colata: ${s.numero_colata}`}</p>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                        <Badge className={`${badge.cls} text-[10px]`}>{badge.label}</Badge>
                                        {expanded ? <ChevronUp className="h-3 w-3 text-slate-400" /> : <ChevronDown className="h-3 w-3 text-slate-400" />}
                                    </div>
                                </div>

                                {expanded && (
                                    <div className="mt-3 pt-3 border-t space-y-2">
                                        {/* Clickable certificate link */}
                                        {s.certificato_info && s.certificato_info.doc_id && (
                                            <button
                                                onClick={() => openCertificato(s.certificato_info.doc_id, s.certificato_info.commessa_origine)}
                                                className="flex items-center gap-2 text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                data-testid={`sfrido-cert-link-${s.sfrido_id}`}
                                            >
                                                <FileText className="h-3 w-3" />
                                                Certificato 3.1: {s.certificato_info.nome_file || 'Apri'}
                                                <ExternalLink className="h-3 w-3" />
                                            </button>
                                        )}

                                        {s.note && <p className="text-xs text-slate-500">Note: {s.note}</p>}

                                        {/* Prelievi history */}
                                        {s.prelievi?.length > 0 && (
                                            <div>
                                                <p className="text-xs font-semibold text-slate-600 mb-1">Prelievi:</p>
                                                {s.prelievi.map((p, i) => (
                                                    <p key={i} className="text-xs text-slate-400 ml-2">
                                                        {p.quantita} per commessa {p.commessa_id} — {new Date(p.data).toLocaleDateString('it-IT')}
                                                    </p>
                                                ))}
                                            </div>
                                        )}

                                        {/* Actions */}
                                        {s.stato !== 'esaurito' && (
                                            <div className="flex gap-2 pt-1">
                                                <Button size="sm" variant="outline" onClick={() => setPrelevandoId(prelevandoId === s.sfrido_id ? null : s.sfrido_id)} data-testid={`btn-preleva-${s.sfrido_id}`}>
                                                    <PackageMinus className="h-3 w-3 mr-1" /> Preleva
                                                </Button>
                                                <Button size="sm" variant="ghost" onClick={() => handleEsaurito(s.sfrido_id)} className="text-red-600 hover:text-red-700" data-testid={`btn-esaurito-${s.sfrido_id}`}>
                                                    <Archive className="h-3 w-3 mr-1" /> Esaurito
                                                </Button>
                                            </div>
                                        )}

                                        {/* Prelievo form */}
                                        {prelevandoId === s.sfrido_id && (
                                            <div className="border-t pt-2 mt-2 space-y-2" data-testid={`prelievo-form-${s.sfrido_id}`}>
                                                <Input placeholder="ID Commessa destinazione" value={prelievoForm.commessa_id_destinazione}
                                                    onChange={e => setPrelievoForm(f => ({ ...f, commessa_id_destinazione: e.target.value }))}
                                                    className="text-xs" />
                                                <Input placeholder="Quantita' prelevata" value={prelievoForm.quantita_prelevata}
                                                    onChange={e => setPrelievoForm(f => ({ ...f, quantita_prelevata: e.target.value }))}
                                                    className="text-xs" />
                                                <div className="flex gap-2 justify-end">
                                                    <Button size="sm" variant="ghost" onClick={() => setPrelevandoId(null)}>Annulla</Button>
                                                    <Button size="sm" onClick={() => handlePrelievo(s.sfrido_id)} data-testid={`btn-confirm-prelievo-${s.sfrido_id}`}>Conferma Prelievo</Button>
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
