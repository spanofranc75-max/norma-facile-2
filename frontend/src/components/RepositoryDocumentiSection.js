/**
 * RepositoryDocumentiSection — Upload documenti, AI parsing certificati 3.1, DDT, profili
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { useState, useRef } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
    FileUp, Download, Trash2, Sparkles, Loader2, Truck,
    Package, CheckCircle2, Leaf,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function RepositoryDocumentiSection({ commessaId, docs, onRefresh, onCamRefresh }) {
    const fileRef = useRef(null);
    const [uploadType, setUploadType] = useState('certificato_31');
    const [parsing, setParsing] = useState(null);
    const [confirmLoading, setConfirmLoading] = useState(false);

    // Profile confirm states
    const [profileConfirmOpen, setProfileConfirmOpen] = useState(false);
    const [pendingProfiles, setPendingProfiles] = useState([]);
    const [selectedProfileIndices, setSelectedProfileIndices] = useState([]);
    const [pendingDocId, setPendingDocId] = useState(null);

    // DDT confirm states
    const [ddtConfirmOpen, setDdtConfirmOpen] = useState(false);
    const [ddtMatchResults, setDdtMatchResults] = useState([]);
    const [ddtMetadata, setDdtMetadata] = useState(null);
    const [ddtDocId, setDdtDocId] = useState(null);
    const [selectedDdtIndices, setSelectedDdtIndices] = useState([]);
    const [ddtConfirmLoading, setDdtConfirmLoading] = useState(false);

    // ── Handlers ──
    const handleUploadDoc = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('tipo', uploadType);
        try {
            const res = await fetch(`${API}/api/commesse/${commessaId}/documenti`, { method: 'POST', body: formData, credentials: 'include' });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            toast.success(`${file.name} caricato`);
            if (fileRef.current) fileRef.current.value = '';
            onRefresh?.();
            // Auto-parse if it's a certificate or DDT
            if (uploadType === 'certificato_31' && data.doc_id) {
                setTimeout(() => handleParseAI(data.doc_id), 500);
            } else if (uploadType === 'ddt_fornitore' && data.doc_id) {
                setTimeout(() => handleParseDDT(data.doc_id), 500);
            }
        } catch (e2) { toast.error(e2.message); }
    };

    const handleParseAI = async (docId) => {
        setParsing(docId);
        try {
            const result = await apiRequest(`/commesse/${commessaId}/documenti/${docId}/parse-certificato`, { method: 'POST' });
            if (result.profili && result.profili.length > 0) {
                setPendingProfiles(result.profili);
                setSelectedProfileIndices(result.profili.map((p, i) => (p.tipo === 'commessa_corrente' && p.stato_ddt !== 'bolla_mancante') ? i : -1).filter(i => i >= 0));
                setPendingDocId(docId);
                setProfileConfirmOpen(true);
                toast.success(`${result.profili.length} profili trovati`);
            } else {
                toast.success(result.message || 'Analisi completata');
            }
            onRefresh?.();
        } catch (e2) {
            toast.error(e2.message || 'Errore analisi AI');
        } finally { setParsing(null); }
    };

    const handleConfirmProfiles = async () => {
        if (selectedProfileIndices.length === 0) return;
        setConfirmLoading(true);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/documenti/${pendingDocId}/confirm-profiles`, {
                method: 'POST',
                body: { selected_indices: selectedProfileIndices },
            });
            toast.success(res.message || `${selectedProfileIndices.length} profili importati`);
            setProfileConfirmOpen(false);
            onRefresh?.();
            onCamRefresh?.();
        } catch (e2) { toast.error(e2.message); }
        finally { setConfirmLoading(false); }
    };

    const handleDownloadDoc = async (docId, filename) => {
        try {
            await downloadPdfBlob(`/commesse/${commessaId}/documenti/${docId}/download`, filename);
        } catch (e2) { toast.error(e2.message); }
    };

    const handleDeleteDoc = async (docId) => {
        if (!window.confirm('Eliminare questo documento?')) return;
        try {
            await apiRequest(`/commesse/${commessaId}/documenti/${docId}`, { method: 'DELETE' });
            toast.success('Documento eliminato');
            onRefresh?.();
        } catch (e2) { toast.error(e2.message); }
    };

    const handleParseDDT = async (docId) => {
        setParsing(docId);
        try {
            const result = await apiRequest(`/commesse/${commessaId}/documenti/${docId}/parse-ddt`, { method: 'POST' });
            if (result.match_results && result.match_results.length > 0) {
                setDdtMatchResults(result.match_results);
                setDdtMetadata(result.metadata);
                setDdtDocId(docId);
                const autoSelected = result.match_results.map((m, i) => i);
                setSelectedDdtIndices(autoSelected);
                setDdtConfirmOpen(true);
                toast.success(`DDT analizzato: ${result.match_results.length} materiali trovati`);
            } else {
                toast.success(result.message || 'DDT analizzato');
            }
            onRefresh?.();
        } catch (e2) {
            toast.error(e2.message || 'Errore analisi DDT');
        } finally { setParsing(null); }
    };

    const handleConfirmDDT = async () => {
        if (selectedDdtIndices.length === 0) return;
        setDdtConfirmLoading(true);
        try {
            const res = await apiRequest(`/commesse/${commessaId}/documenti/${ddtDocId}/confirm-ddt`, {
                method: 'POST',
                body: { selected_indices: selectedDdtIndices, metadata: ddtMetadata },
            });
            toast.success(res.message || `Arrivo creato con ${selectedDdtIndices.length} materiali`);
            setDdtConfirmOpen(false);
            onRefresh?.();
        } catch (e2) { toast.error(e2.message); }
        finally { setDdtConfirmLoading(false); }
    };

    return (
        <>
            <div className="space-y-2" data-testid="repository-documenti-section">
                <div className="flex items-center gap-2 flex-wrap">
                    <select value={uploadType} onChange={(e) => setUploadType(e.target.value)}
                        className="w-44 h-8 text-xs rounded-md border border-input bg-transparent px-2 py-1 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="select-upload-type">
                        <option value="certificato_31">Certificato 3.1</option>
                        <option value="conferma_ordine">Conferma Ordine</option>
                        <option value="disegno">Disegno</option>
                        <option value="certificato_verniciatura">Cert. Verniciatura</option>
                        <option value="certificato_zincatura">Cert. Zincatura</option>
                        <option value="ddt_fornitore">DDT Fornitore</option>
                        <option value="foto">Foto</option>
                        <option value="altro">Altro</option>
                    </select>
                    <input ref={fileRef} type="file" className="hidden" onChange={handleUploadDoc} data-testid="file-input" />
                    <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} className="text-xs" data-testid="btn-upload-doc">
                        <FileUp className="h-3 w-3 mr-1" /> Carica File
                    </Button>
                    {docs.length > 3 && (
                        <select data-testid="filter-doc-type" className="h-8 text-xs rounded-md border border-input bg-transparent px-2 py-1 ml-auto"
                            onChange={(e) => { const v = e.target.value; document.querySelectorAll('[data-doc-type]').forEach(el => { el.style.display = (!v || el.dataset.docType === v) ? '' : 'none'; }); }}>
                            <option value="">Tutti i tipi</option>
                            {[...new Set(docs.map(d => d.tipo))].map(t => (<option key={t} value={t}>{(t || 'altro').replace(/_/g, ' ')}</option>))}
                        </select>
                    )}
                </div>
                {docs.map(d => (
                    <div key={d.doc_id} data-doc-type={d.tipo} className="flex items-center gap-2 p-2 bg-slate-50 rounded text-xs" data-testid={`doc-${d.doc_id}`}>
                        <FileUp className="h-3.5 w-3.5 text-[#0055FF] shrink-0" />
                        <div className="flex-1 min-w-0">
                            <span className="font-medium truncate block">{d.nome_file}</span>
                            <span className="text-[10px] text-slate-400">{d.tipo?.replace(/_/g, ' ')} — {(d.size_bytes / 1024).toFixed(0)}KB</span>
                            {d.metadata_estratti?.numero_colata && (
                                <div className="mt-1 p-1.5 bg-emerald-50 rounded border border-emerald-200">
                                    <span className="block text-[10px] text-emerald-700 font-semibold">Dati Estratti con AI</span>
                                    <div className="grid grid-cols-3 gap-x-2 text-[10px] mt-1">
                                        <div><span className="text-slate-500">Colata:</span> <span className="font-mono font-semibold">{d.metadata_estratti.numero_colata}</span></div>
                                        <div><span className="text-slate-500">Qualità:</span> <span className="font-mono">{d.metadata_estratti.qualita_acciaio || '-'}</span></div>
                                        <div><span className="text-slate-500">Fornitore:</span> <span className="font-mono">{d.metadata_estratti.fornitore || '-'}</span></div>
                                    </div>
                                    {d.metadata_estratti.percentuale_riciclato != null && (
                                        <div className="mt-1 p-1 bg-emerald-100 rounded flex items-center gap-2 text-[10px]">
                                            <Leaf className="h-3 w-3 text-emerald-600" />
                                            <span className="font-semibold text-emerald-800">CAM: {d.metadata_estratti.percentuale_riciclato}% riciclato</span>
                                            {d.metadata_estratti.metodo_produttivo && <span className="text-emerald-600">({(d.metadata_estratti.metodo_produttivo || '').replace(/_/g, ' ')})</span>}
                                            {d.metadata_estratti.certificazione_ambientale && <span className="text-emerald-500">[{d.metadata_estratti.certificazione_ambientale}]</span>}
                                        </div>
                                    )}
                                    {d.metadata_estratti.normativa_riferimento && (
                                        <div className="text-[10px] mt-0.5"><span className="text-slate-500">Normativa:</span> <span className="font-mono">{d.metadata_estratti.normativa_riferimento}</span></div>
                                    )}
                                </div>
                            )}
                            {d.metadata_estratti?.profili?.length > 0 && (
                                <div className="mt-1 p-1.5 bg-blue-50 rounded border border-blue-200">
                                    <span className="block text-[10px] text-blue-700 font-semibold">{d.metadata_estratti.profili.length} profili nel certificato</span>
                                    {d.metadata_estratti.profili.map((p, idx) => (
                                        <div key={idx} className="flex items-center gap-2 text-[10px] mt-0.5 py-0.5 border-b border-blue-100 last:border-0">
                                            <span className="font-mono font-semibold text-blue-800">{p.dimensioni || '?'}</span>
                                            <span className="text-slate-500">colata: {p.numero_colata || '?'}</span>
                                            <span className="text-slate-500">{p.qualita_acciaio || ''}</span>
                                            {p.peso_kg && <span className="text-slate-400">{p.peso_kg} kg</span>}
                                        </div>
                                    ))}
                                </div>
                            )}
                            {d.tipo === 'ddt_fornitore' && d.metadata_estratti?.numero_ddt && (
                                <div className="mt-1 p-1.5 bg-amber-50 rounded border border-amber-200">
                                    <span className="block text-[10px] text-amber-700 font-semibold">DDT Analizzato con AI</span>
                                    <div className="grid grid-cols-3 gap-x-2 text-[10px] mt-1">
                                        <div><span className="text-slate-500">N. DDT:</span> <span className="font-mono font-semibold">{d.metadata_estratti.numero_ddt}</span></div>
                                        <div><span className="text-slate-500">Data:</span> <span className="font-mono">{d.metadata_estratti.data_ddt || '-'}</span></div>
                                        <div><span className="text-slate-500">Fornitore:</span> <span className="font-mono">{d.metadata_estratti.fornitore_nome || '-'}</span></div>
                                    </div>
                                    <div className="text-[10px] mt-0.5">
                                        <span className="text-slate-500">{d.metadata_estratti.materiali?.length || 0} materiali</span>
                                        {d.metadata_estratti.totale_peso_kg > 0 && <span className="text-slate-500 ml-2">| {d.metadata_estratti.totale_peso_kg} kg</span>}
                                        {d.ddt_arrivo_id && <span className="ml-2 text-emerald-600 font-medium">Arrivo creato</span>}
                                    </div>
                                </div>
                            )}
                        </div>
                        {d.tipo !== 'ddt_fornitore' && (d.nome_file?.toLowerCase().endsWith('.pdf') || d.content_type?.includes('pdf') || d.content_type?.includes('image')) && (
                            <Button size="sm" variant="ghost" className={`h-7 text-[10px] border ${d.metadata_estratti?.numero_colata ? 'text-emerald-600 border-emerald-200' : 'text-purple-600 border-purple-200'}`} disabled={parsing === d.doc_id}
                                onClick={() => handleParseAI(d.doc_id)} data-testid={`btn-parse-${d.doc_id}`}>
                                {parsing === d.doc_id ? <Loader2 className="h-3 w-3 animate-spin mr-0.5" /> : <Sparkles className="h-3 w-3 mr-0.5" />}
                                {d.metadata_estratti?.numero_colata ? 'Ri-analizza' : 'Analizza AI'}
                            </Button>
                        )}
                        {d.tipo === 'ddt_fornitore' && (d.nome_file?.toLowerCase().endsWith('.pdf') || d.content_type?.includes('pdf') || d.content_type?.includes('image')) && (
                            <Button size="sm" variant="ghost" className={`h-7 text-[10px] border ${d.metadata_estratti?.numero_ddt ? 'text-amber-600 border-amber-200' : 'text-orange-600 border-orange-200'}`} disabled={parsing === d.doc_id}
                                onClick={() => handleParseDDT(d.doc_id)} data-testid={`btn-parse-ddt-${d.doc_id}`}>
                                {parsing === d.doc_id ? <Loader2 className="h-3 w-3 animate-spin mr-0.5" /> : <Truck className="h-3 w-3 mr-0.5" />}
                                {d.metadata_estratti?.numero_ddt ? 'Ri-analizza DDT' : 'Analizza DDT'}
                            </Button>
                        )}
                        <Button size="sm" variant="ghost" className="h-7 px-1.5" onClick={() => handleDownloadDoc(d.doc_id, d.nome_file)}><Download className="h-3 w-3" /></Button>
                        <Button size="sm" variant="ghost" className="h-7 px-1.5 text-red-400 hover:text-red-600" onClick={() => handleDeleteDoc(d.doc_id)}><Trash2 className="h-3 w-3" /></Button>
                    </div>
                ))}
            </div>

            {/* DDT Confirm Dialog */}
            <Dialog open={ddtConfirmOpen} onOpenChange={setDdtConfirmOpen}>
                <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="text-base flex items-center gap-2"><Truck className="h-4 w-4 text-amber-600" /> Conferma Materiali DDT</DialogTitle>
                        <DialogDescription className="text-xs text-slate-500">
                            {ddtMetadata && <>DDT <span className="font-semibold">{ddtMetadata.numero_ddt}</span> del {ddtMetadata.data_ddt} — {ddtMetadata.fornitore_nome}</>}
                            {ddtMetadata && <><br />{ddtMatchResults.length} materiali trovati. Seleziona quelli da registrare come arrivo.</>}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                        {ddtMatchResults.map((m, idx) => {
                            const hasMatch = !!m.match_oda;
                            const isSelected = selectedDdtIndices.includes(idx);
                            return (
                                <label key={idx} className={`flex items-start gap-2 text-xs cursor-pointer p-2 rounded border transition-colors ${isSelected ? (hasMatch ? 'bg-emerald-50 border-emerald-300' : 'bg-amber-50 border-amber-300') : 'bg-slate-50 border-slate-200 opacity-60'}`} data-testid={`confirm-ddt-mat-${idx}`}>
                                    <Checkbox checked={isSelected} onCheckedChange={(checked) => { setSelectedDdtIndices(prev => checked ? [...prev, idx] : prev.filter(i => i !== idx)); }} className="mt-0.5" />
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold">{m.descrizione || '?'}</span>
                                            {m.quantita > 0 && <span className="text-slate-400">| {m.quantita} {m.unita_misura}</span>}
                                        </div>
                                        <div className="text-[10px] mt-0.5">
                                            {m.profile_base && <span className="font-mono text-blue-600 mr-2">{m.profile_base}</span>}
                                            {hasMatch && <span className="text-emerald-600 font-medium">OdA: {m.match_oda.descrizione_oda} ({m.match_oda.fornitore_oda})</span>}
                                            {!hasMatch && <span className="text-amber-600">Nessun OdA corrispondente</span>}
                                            {m.richiede_certificato && <span className="ml-2 text-purple-500">Cert. 3.1</span>}
                                        </div>
                                        {m.riferimento_ordine && <div className="text-[10px] text-slate-400">Rif. ordine: {m.riferimento_ordine}</div>}
                                    </div>
                                </label>
                            );
                        })}
                    </div>
                    <div className="flex gap-2 mt-1">
                        <button className="text-[10px] text-blue-600 hover:underline" onClick={() => setSelectedDdtIndices(ddtMatchResults.map((_, i) => i))}>Seleziona tutti</button>
                        <button className="text-[10px] text-blue-600 hover:underline" onClick={() => setSelectedDdtIndices(ddtMatchResults.map((m, i) => m.match_oda ? i : -1).filter(i => i >= 0))}>Solo con OdA</button>
                        <button className="text-[10px] text-blue-600 hover:underline" onClick={() => setSelectedDdtIndices([])}>Deseleziona tutti</button>
                    </div>
                    <DialogFooter className="mt-3">
                        <div className="flex items-center justify-between w-full">
                            <span className="text-xs text-slate-500">{selectedDdtIndices.length} di {ddtMatchResults.length} selezionati</span>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => setDdtConfirmOpen(false)} className="text-xs">Annulla</Button>
                                <Button size="sm" onClick={handleConfirmDDT} disabled={ddtConfirmLoading || selectedDdtIndices.length === 0}
                                    className="text-xs bg-amber-600 hover:bg-amber-700 text-white" data-testid="btn-conferma-ddt">
                                    {ddtConfirmLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Package className="h-3 w-3 mr-1" />}
                                    Crea Arrivo ({selectedDdtIndices.length} materiali)
                                </Button>
                            </div>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Profile Confirmation Dialog */}
            <Dialog open={profileConfirmOpen} onOpenChange={setProfileConfirmOpen}>
                <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="text-base">Conferma Profili da Importare</DialogTitle>
                        <DialogDescription className="text-xs text-slate-500">
                            L'AI ha trovato {pendingProfiles.length} profili nel certificato. Seleziona solo quelli effettivamente consegnati per questa commessa.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                        {pendingProfiles.map((p, idx) => {
                            const isMatch = p.tipo === 'commessa_corrente';
                            const isBollaMancante = p.stato_ddt === 'bolla_mancante';
                            const isSelected = selectedProfileIndices.includes(idx);
                            const bgClass = isBollaMancante ? 'bg-amber-50 border-amber-300 opacity-80' : isSelected ? 'bg-emerald-50 border-emerald-300' : 'bg-slate-50 border-slate-200 opacity-60';
                            return (
                                <label key={idx} className={`flex items-start gap-2 text-xs p-2 rounded border transition-colors cursor-pointer ${bgClass}`} data-testid={`confirm-profile-${idx}`}>
                                    <Checkbox checked={isSelected} onCheckedChange={(checked) => { setSelectedProfileIndices(prev => checked ? [...prev, idx] : prev.filter(i => i !== idx)); }} className="mt-0.5" />
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold">{p.dimensioni || 'Profilo sconosciuto'}</span>
                                            <span className="text-slate-400">| Colata: {p.numero_colata || '-'}</span>
                                            {p.peso_kg > 0 && <span className="text-slate-400">| {p.peso_kg} kg</span>}
                                        </div>
                                        <div className="text-[10px] mt-0.5">
                                            <span className="text-slate-500">{p.qualita_acciaio || ''}</span>
                                            {p.stato_ddt === 'ok' && <span className="ml-2 text-emerald-600 font-medium">DDT del {p.ddt_data}</span>}
                                            {isBollaMancante && <span className="ml-2 text-amber-600 font-medium">Nessuna bolla — archivio</span>}
                                            {isMatch && !isBollaMancante && <span className="ml-2 text-emerald-600 font-medium">Corrisponde all'OdA</span>}
                                            {p.tipo === 'archivio' && !isBollaMancante && <span className="ml-2 text-amber-600">Non in OdA</span>}
                                            {p.tipo === 'altra_commessa' && <span className="ml-2 text-blue-600">Altra commessa: {p.commessa_numero}</span>}
                                        </div>
                                    </div>
                                </label>
                            );
                        })}
                    </div>
                    <div className="flex gap-2 mt-1">
                        <button className="text-[10px] text-blue-600 hover:underline" onClick={() => setSelectedProfileIndices(pendingProfiles.map((_, i) => i))}>Seleziona tutti</button>
                        <button className="text-[10px] text-blue-600 hover:underline" onClick={() => {
                            const indices = [];
                            pendingProfiles.forEach((pp, ii) => { if (pp.tipo === 'commessa_corrente' && pp.stato_ddt !== 'bolla_mancante') indices.push(ii); });
                            setSelectedProfileIndices(indices);
                        }}>Solo con DDT + OdA</button>
                        <button className="text-[10px] text-blue-600 hover:underline" onClick={() => setSelectedProfileIndices([])}>Deseleziona tutti</button>
                    </div>
                    <DialogFooter className="mt-3">
                        <div className="flex items-center justify-between w-full">
                            <span className="text-xs text-slate-500">{selectedProfileIndices.length} di {pendingProfiles.length} selezionati</span>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => setProfileConfirmOpen(false)} className="text-xs">Annulla</Button>
                                <Button size="sm" onClick={handleConfirmProfiles} disabled={confirmLoading || selectedProfileIndices.length === 0}
                                    className="text-xs bg-[#1a3a6b]" data-testid="btn-conferma-profili">
                                    {confirmLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
                                    Conferma Importazione ({selectedProfileIndices.length})
                                </Button>
                            </div>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
