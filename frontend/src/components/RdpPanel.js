/**
 * RdpPanel — Richiesta di Preventivo a Fornitore
 * 
 * Mostra nel Preventivo:
 * 1. Lista RdP inviate con stato
 * 2. Dialog per creare nuova RdP (selezione articoli + fornitore)
 * 3. Form per inserire risposta fornitore
 * 4. Calcolo ricarico e applicazione prezzi al preventivo
 * 5. Conversione in OdA quando la commessa esiste
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { useConfirm } from '../components/ConfirmProvider';
import { toast } from 'sonner';
import {
    Send, Package, Check, ChevronDown, ChevronUp, Trash2, FileDown,
    ArrowRightLeft, Loader2, Plus, ReceiptText
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_COLORS = {
    inviata: 'bg-blue-100 text-blue-800',
    risposta_ricevuta: 'bg-amber-100 text-amber-800',
    applicata: 'bg-emerald-100 text-emerald-800',
    convertita_oda: 'bg-purple-100 text-purple-800',
};

const STATUS_LABELS = {
    inviata: 'Inviata',
    risposta_ricevuta: 'Risposta Ricevuta',
    applicata: 'Prezzi Applicati',
    convertita_oda: 'Convertita in OdA',
};

export default function RdpPanel({ prevId, lines = [], suppliers = [], onPricesUpdated, apiRequest }) {
    const confirm = useConfirm();
    const [rdpList, setRdpList] = useState([]);
    const [loading, setLoading] = useState(false);
    const [showCreate, setShowCreate] = useState(false);
    const [expandedRdp, setExpandedRdp] = useState(null);
    const [converting, setConverting] = useState(null);

    // Create dialog state
    const [selectedLines, setSelectedLines] = useState([]);
    const [supplierName, setSupplierName] = useState('');
    const [supplierId, setSupplierId] = useState('');
    const [rdpNote, setRdpNote] = useState('');
    const [creating, setCreating] = useState(false);

    // Response entry state
    const [responseData, setResponseData] = useState({});
    const [defaultMarkup, setDefaultMarkup] = useState(30);

    const fetchRdpList = useCallback(async () => {
        if (!prevId) return;
        try {
            const data = await apiRequest(`/preventivi/${prevId}/rdp`);
            setRdpList(data.rdp_list || []);
        } catch (e) {
            console.error('Fetch RdP error:', e);
        }
    }, [prevId, apiRequest]);

    useEffect(() => { fetchRdpList(); }, [fetchRdpList]);

    // ── Create RdP ──
    const handleCreate = async () => {
        if (selectedLines.length === 0) return toast.error('Seleziona almeno una riga');
        if (!supplierName.trim()) return toast.error('Inserisci il nome del fornitore');
        setCreating(true);
        try {
            const items = selectedLines.map(idx => ({
                line_index: idx,
                description: lines[idx]?.description || '',
                quantity: parseFloat(lines[idx]?.quantity) || 1,
                unit: lines[idx]?.unit || 'kg',
            }));
            await apiRequest(`/preventivi/${prevId}/rdp`, {
                method: 'POST',
                body: JSON.stringify({
                    supplier_id: supplierId,
                    supplier_name: supplierName.trim(),
                    items,
                    note: rdpNote,
                }),
            });
            toast.success(`RdP creata per ${supplierName}`);
            setShowCreate(false);
            setSelectedLines([]);
            setSupplierName('');
            setSupplierId('');
            setRdpNote('');
            fetchRdpList();
        } catch (e) { toast.error(e.message); }
        finally { setCreating(false); }
    };

    // ── Record Response ──
    const handleRecordResponse = async (rdp) => {
        const prices = rdp.items.map(item => ({
            line_index: item.line_index,
            unit_price: parseFloat(responseData[`${rdp.rdp_id}_${item.line_index}`] || item.supplier_price || 0),
        }));
        try {
            await apiRequest(`/preventivi/${prevId}/rdp/${rdp.rdp_id}/response`, {
                method: 'PUT',
                body: JSON.stringify({ prices }),
            });
            toast.success('Prezzi fornitore salvati');
            fetchRdpList();
        } catch (e) { toast.error(e.message); }
    };

    // ── Apply Prices with Markup ──
    const handleApplyPrices = async (rdp) => {
        const markup_rules = rdp.items
            .filter(it => it.supplier_price > 0)
            .map(it => ({
                line_index: it.line_index,
                supplier_price: it.supplier_price,
                markup_pct: parseFloat(responseData[`markup_${rdp.rdp_id}_${it.line_index}`] ?? defaultMarkup),
            }));
        if (markup_rules.length === 0) return toast.error('Nessun prezzo fornitore da applicare');
        try {
            const res = await apiRequest(`/preventivi/${prevId}/rdp/${rdp.rdp_id}/apply-prices`, {
                method: 'POST',
                body: JSON.stringify({ markup_rules }),
            });
            toast.success(res.message);
            fetchRdpList();
            onPricesUpdated?.();
        } catch (e) { toast.error(e.message); }
    };

    // ── Convert to OdA ──
    const handleConvertOda = async (rdp) => {
        setConverting(rdp.rdp_id);
        try {
            const res = await apiRequest(`/preventivi/${prevId}/rdp/${rdp.rdp_id}/convert-oda`, { method: 'POST' });
            toast.success(res.message);
            fetchRdpList();
        } catch (e) { toast.error(e.message); }
        finally { setConverting(null); }
    };

    // ── Delete ──
    const handleDelete = async (rdpId) => {
        if (!(await confirm('Eliminare questa RdP?'))) return;
        try {
            await apiRequest(`/preventivi/${prevId}/rdp/${rdpId}`, { method: 'DELETE' });
            toast.success('RdP eliminata');
            fetchRdpList();
        } catch (e) { toast.error(e.message); }
    };

    // ── Download PDF ──
    const handleDownloadPdf = async (rdp) => {
        try {
            const resp = await fetch(`${API}/api/preventivi/${prevId}/rdp/${rdp.rdp_id}/pdf`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!resp.ok) throw new Error('Errore download');
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `RdP_${rdp.supplier_name.replace(/\s+/g, '_')}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    const toggleLine = (idx) => {
        setSelectedLines(prev =>
            prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
        );
    };

    if (!prevId) return null;

    return (
        <div data-testid="rdp-panel" className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Send className="h-4 w-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-slate-700">Richieste Preventivo Fornitori (RdP)</h3>
                    {rdpList.length > 0 && (
                        <Badge variant="secondary" className="text-xs">{rdpList.length}</Badge>
                    )}
                </div>
                <Button data-testid="btn-create-rdp" size="sm" variant="outline" onClick={() => setShowCreate(true)} className="h-8 text-xs gap-1.5">
                    <Plus className="h-3.5 w-3.5" /> Chiedi Prezzi
                </Button>
            </div>

            {/* RdP List */}
            {rdpList.length === 0 ? (
                <div className="text-center py-6 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
                    <Send className="h-8 w-8 mx-auto text-slate-300 mb-2" />
                    <p className="text-sm text-slate-400">Nessuna richiesta di preventivo inviata</p>
                    <p className="text-xs text-slate-300 mt-1">Clicca "Chiedi Prezzi" per richiedere un'offerta al fornitore</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {rdpList.map(rdp => (
                        <div key={rdp.rdp_id} data-testid={`rdp-card-${rdp.rdp_id}`} className="border rounded-lg bg-white overflow-hidden">
                            {/* Card Header */}
                            <div className="flex items-center justify-between px-3 py-2 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors"
                                onClick={() => setExpandedRdp(expandedRdp === rdp.rdp_id ? null : rdp.rdp_id)}>
                                <div className="flex items-center gap-2">
                                    <Package className="h-4 w-4 text-slate-500" />
                                    <span className="text-sm font-semibold">{rdp.supplier_name}</span>
                                    <Badge className={`text-[10px] ${STATUS_COLORS[rdp.status] || 'bg-gray-100'}`}>
                                        {STATUS_LABELS[rdp.status] || rdp.status}
                                    </Badge>
                                    <span className="text-xs text-slate-400">{rdp.items?.length || 0} articoli</span>
                                    {rdp.total_offered > 0 && (
                                        <span className="text-xs font-mono font-semibold text-emerald-700">
                                            {rdp.total_offered.toLocaleString('it-IT', { minimumFractionDigits: 2 })} EUR
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDownloadPdf(rdp); }} className="h-7 w-7 p-0" title="Scarica PDF">
                                        <FileDown className="h-3.5 w-3.5" />
                                    </Button>
                                    {rdp.status !== 'convertita_oda' && (
                                        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDelete(rdp.rdp_id); }} className="h-7 w-7 p-0 text-red-400 hover:text-red-600">
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    )}
                                    {expandedRdp === rdp.rdp_id ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                                </div>
                            </div>

                            {/* Expanded Content */}
                            {expandedRdp === rdp.rdp_id && (
                                <div className="px-3 py-3 border-t space-y-3">
                                    {/* Items Table with response entry */}
                                    <table className="w-full text-xs">
                                        <thead>
                                            <tr className="border-b">
                                                <th className="text-left py-1 px-1 font-semibold text-slate-500">Articolo</th>
                                                <th className="text-right py-1 px-1 font-semibold text-slate-500 w-16">Q.ta</th>
                                                <th className="text-right py-1 px-1 font-semibold text-slate-500 w-24">Prezzo Forn.</th>
                                                <th className="text-center py-1 px-1 font-semibold text-slate-500 w-20">Ricarico %</th>
                                                <th className="text-right py-1 px-1 font-semibold text-slate-500 w-24">Prezzo Cliente</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {(rdp.items || []).map((item, idx) => {
                                                const supPrice = parseFloat(responseData[`${rdp.rdp_id}_${item.line_index}`] ?? item.supplier_price ?? 0);
                                                const markup = parseFloat(responseData[`markup_${rdp.rdp_id}_${item.line_index}`] ?? defaultMarkup);
                                                const clientPrice = supPrice > 0 ? supPrice * (1 + markup / 100) : 0;
                                                return (
                                                    <tr key={idx} className="border-b border-slate-100">
                                                        <td className="py-1.5 px-1 text-slate-700">{item.description}</td>
                                                        <td className="text-right py-1.5 px-1 text-slate-600">{item.quantity} {item.unit}</td>
                                                        <td className="py-1.5 px-1">
                                                            <Input
                                                                data-testid={`rdp-price-${item.line_index}`}
                                                                type="number" step="0.01" min="0"
                                                                className="h-7 text-xs text-right w-full"
                                                                placeholder="0,00"
                                                                value={responseData[`${rdp.rdp_id}_${item.line_index}`] ?? item.supplier_price ?? ''}
                                                                onChange={(e) => setResponseData(prev => ({
                                                                    ...prev,
                                                                    [`${rdp.rdp_id}_${item.line_index}`]: e.target.value,
                                                                }))}
                                                                disabled={rdp.status === 'convertita_oda'}
                                                            />
                                                        </td>
                                                        <td className="py-1.5 px-1">
                                                            <Input
                                                                data-testid={`rdp-markup-${item.line_index}`}
                                                                type="number" step="1" min="0"
                                                                className="h-7 text-xs text-center w-full"
                                                                placeholder="30"
                                                                value={responseData[`markup_${rdp.rdp_id}_${item.line_index}`] ?? defaultMarkup}
                                                                onChange={(e) => setResponseData(prev => ({
                                                                    ...prev,
                                                                    [`markup_${rdp.rdp_id}_${item.line_index}`]: e.target.value,
                                                                }))}
                                                                disabled={rdp.status === 'convertita_oda' || rdp.status === 'applicata'}
                                                            />
                                                        </td>
                                                        <td className="text-right py-1.5 px-1 font-mono text-slate-700 font-semibold">
                                                            {clientPrice > 0 ? clientPrice.toFixed(2) : '-'}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>

                                    {/* Default Markup */}
                                    <div className="flex items-center gap-2 text-xs text-slate-500">
                                        <span>Ricarico default:</span>
                                        <Input type="number" className="h-7 w-16 text-xs text-center" value={defaultMarkup}
                                            onChange={(e) => setDefaultMarkup(parseFloat(e.target.value) || 0)} />
                                        <span>%</span>
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex gap-2 pt-1">
                                        {(rdp.status === 'inviata' || rdp.status === 'risposta_ricevuta') && (
                                            <Button data-testid={`btn-save-response-${rdp.rdp_id}`} size="sm" variant="outline" onClick={() => handleRecordResponse(rdp)} className="h-8 text-xs gap-1.5">
                                                <Check className="h-3.5 w-3.5" /> Salva Prezzi Fornitore
                                            </Button>
                                        )}
                                        {rdp.status === 'risposta_ricevuta' && (
                                            <Button data-testid={`btn-apply-prices-${rdp.rdp_id}`} size="sm" onClick={() => handleApplyPrices(rdp)} className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white">
                                                <ArrowRightLeft className="h-3.5 w-3.5" /> Aggiorna Preventivo
                                            </Button>
                                        )}
                                        {(rdp.status === 'applicata' || rdp.status === 'risposta_ricevuta') && (
                                            <Button data-testid={`btn-convert-oda-${rdp.rdp_id}`} size="sm" variant="outline" onClick={() => handleConvertOda(rdp)} disabled={converting === rdp.rdp_id}
                                                className="h-8 text-xs gap-1.5 border-purple-300 text-purple-700 hover:bg-purple-50">
                                                {converting === rdp.rdp_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ReceiptText className="h-3.5 w-3.5" />}
                                                Genera OdA
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* ── Create RdP Dialog ── */}
            <Dialog open={showCreate} onOpenChange={setShowCreate}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Richiedi Prezzi a Fornitore</DialogTitle>
                        <DialogDescription>Seleziona gli articoli e il fornitore a cui chiedere l'offerta</DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 max-h-[55vh] overflow-y-auto">
                        {/* Supplier */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-slate-600">Fornitore</label>
                            {suppliers.length > 0 ? (
                                <select data-testid="rdp-supplier-select"
                                    className="w-full border rounded-md px-3 py-2 text-sm"
                                    value={supplierId}
                                    onChange={(e) => {
                                        setSupplierId(e.target.value);
                                        const sel = suppliers.find(s => s.client_id === e.target.value);
                                        if (sel) setSupplierName(sel.business_name);
                                    }}>
                                    <option value="">-- Seleziona fornitore --</option>
                                    {suppliers.map(s => (
                                        <option key={s.client_id} value={s.client_id}>{s.business_name}</option>
                                    ))}
                                </select>
                            ) : null}
                            <Input data-testid="rdp-supplier-name" placeholder="Nome fornitore (manuale)" value={supplierName}
                                onChange={(e) => setSupplierName(e.target.value)} className="text-sm" />
                        </div>

                        {/* Lines selection */}
                        <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-semibold text-slate-600">Articoli da quotare</label>
                                <button className="text-xs text-blue-600 hover:underline" onClick={() => {
                                    if (selectedLines.length === lines.length) setSelectedLines([]);
                                    else setSelectedLines(lines.map((_, i) => i));
                                }}>
                                    {selectedLines.length === lines.length ? 'Deseleziona tutti' : 'Seleziona tutti'}
                                </button>
                            </div>
                            <div className="space-y-1 max-h-48 overflow-y-auto border rounded-md p-2">
                                {lines.map((line, idx) => (
                                    <label key={idx} className="flex items-start gap-2 py-1 px-1 rounded hover:bg-slate-50 cursor-pointer">
                                        <input type="checkbox" className="mt-0.5" checked={selectedLines.includes(idx)} onChange={() => toggleLine(idx)} />
                                        <span className="text-xs text-slate-700 leading-tight">
                                            <strong>{line.description || `Riga ${idx+1}`}</strong>
                                            {line.quantity ? ` — ${line.quantity} ${line.unit || 'pz'}` : ''}
                                        </span>
                                    </label>
                                ))}
                            </div>
                        </div>

                        {/* Note */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-slate-600">Note per il fornitore</label>
                            <textarea data-testid="rdp-note" className="w-full border rounded-md px-3 py-2 text-sm resize-none h-16"
                                placeholder="Es: Consegna entro 2 settimane, certificato 3.1 obbligatorio..."
                                value={rdpNote} onChange={(e) => setRdpNote(e.target.value)} />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowCreate(false)}>Annulla</Button>
                        <Button data-testid="btn-confirm-rdp" onClick={handleCreate} disabled={creating || selectedLines.length === 0 || !supplierName.trim()}
                            className="gap-1.5 bg-blue-600 hover:bg-blue-700 text-white">
                            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            Genera RdP ({selectedLines.length} articoli)
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
