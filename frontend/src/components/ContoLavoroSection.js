/**
 * ContoLavoroSection — Lavorazioni esterne (verniciatura, zincatura, sabbiatura)
 * Include: DDT, rientro, verifica QC, NCR PDF, email
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { useState, useRef } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { DisabledTooltip } from './DisabledTooltip';
import EmailPreviewDialog from './EmailPreviewDialog';
import { toast } from 'sonner';
import {
    Plus, Package, CheckCircle2, AlertTriangle, Eye, Mail,
    MailCheck, Loader2, Trash2, Paintbrush,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function StatoBadge({ stato }) {
    const map = {
        da_fare: 'bg-slate-100 text-slate-600', in_corso: 'bg-blue-100 text-blue-700',
        completato: 'bg-emerald-100 text-emerald-700', da_inviare: 'bg-amber-100 text-amber-700',
        inviato: 'bg-blue-100 text-blue-700', rientrato: 'bg-purple-100 text-purple-700',
        verificato: 'bg-emerald-100 text-emerald-700', in_lavorazione: 'bg-orange-100 text-orange-700',
        da_verificare: 'bg-amber-100 text-amber-700',
    };
    return <Badge className={`text-[9px] ${map[stato] || 'bg-slate-100 text-slate-600'}`}>{(stato || '').replace(/_/g, ' ')}</Badge>;
}

export default function ContoLavoroSection({ commessaId, commessaNumero, cl, fornitori, onRefresh }) {
    const emptyClLine = () => ({ id: `l${Date.now()}`, descrizione: '', quantita: 1, unita: 'pz', peso_kg: 0 });

    const [clOpen, setClOpen] = useState(false);
    const [clForm, setClForm] = useState({ tipo: 'verniciatura', fornitore_nome: '', fornitore_id: '', ral: '', righe: [emptyClLine()], note: '', causale_trasporto: 'Conto Lavorazione' });
    const [rientroOpen, setRientroOpen] = useState(false);
    const [rientroTarget, setRientroTarget] = useState(null);
    const [rientroForm, setRientroForm] = useState({
        data_rientro: new Date().toISOString().slice(0, 10), peso_rientrato_kg: 0,
        ddt_fornitore_numero: '', ddt_fornitore_data: '', esito_qc: 'conforme',
        note_rientro: '', motivo_non_conformita: '',
    });
    const [rientroFile, setRientroFile] = useState(null);
    const [rientroLoading, setRientroLoading] = useState(false);
    const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
    const [pdfPreviewTitle, setPdfPreviewTitle] = useState('');
    const [pdfExpanded, setPdfExpanded] = useState(false);
    const [sendingEmail, setSendingEmail] = useState(null);
    const [emailPreview, setEmailPreview] = useState({ open: false, previewUrl: '', sendUrl: '' });

    // ── Handlers ──
    const handleCreateCL = async () => {
        try {
            const body = {
                tipo: clForm.tipo, fornitore_nome: clForm.fornitore_nome, fornitore_id: clForm.fornitore_id,
                ral: clForm.ral, righe: clForm.righe.filter(r => r.descrizione.trim()),
                note: clForm.note, causale_trasporto: clForm.causale_trasporto,
            };
            const res = await apiRequest(`/commesse/${commessaId}/conto-lavoro`, { method: 'POST', body });
            toast.success(res.message || 'Conto lavoro creato');
            setClOpen(false);
            setClForm({ tipo: 'verniciatura', fornitore_nome: '', fornitore_id: '', ral: '', righe: [emptyClLine()], note: '', causale_trasporto: 'Conto Lavorazione' });
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateCL = async (clId, stato) => {
        try {
            await apiRequest(`/commesse/${commessaId}/conto-lavoro/${clId}`, { method: 'PUT', body: { stato } });
            toast.success(`C/L aggiornato: ${stato}`);
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handlePreviewClPdf = (clId) => {
        const url = `${API}/api/commesse/${commessaId}/conto-lavoro/${clId}/preview-pdf`;
        setPdfPreviewTitle(`DDT Conto Lavoro ${clId}`);
        setPdfPreviewUrl(url);
    };

    const handleSendClEmail = (clId) => {
        setEmailPreview({
            open: true,
            previewUrl: `/api/commesse/${commessaId}/conto-lavoro/${clId}/preview-email`,
            sendUrl: `/api/commesse/${commessaId}/conto-lavoro/${clId}/send-email`,
        });
    };

    const openRientroModal = (c) => {
        setRientroTarget(c);
        const pesoInviato = (c.righe || []).reduce((s, r) => s + (parseFloat(r.peso_kg) || 0), 0);
        setRientroForm({
            data_rientro: new Date().toISOString().slice(0, 10), peso_rientrato_kg: pesoInviato,
            ddt_fornitore_numero: '', ddt_fornitore_data: '', esito_qc: 'conforme',
            note_rientro: '', motivo_non_conformita: '',
        });
        setRientroFile(null);
        setRientroOpen(true);
    };

    const handleSubmitRientro = async () => {
        if (!rientroTarget) return;
        setRientroLoading(true);
        try {
            let uploadedDocId = null;
            if (rientroFile) {
                const formData = new FormData();
                formData.append('file', rientroFile);
                formData.append('tipo', 'certificato_lavorazione');
                const uploadRes = await fetch(`${API}/api/commesse/${commessaId}/documenti`, {
                    method: 'POST', body: formData, credentials: 'include',
                });
                if (uploadRes.ok) {
                    const upData = await uploadRes.json();
                    uploadedDocId = upData.doc_id;
                }
            }
            const res = await apiRequest(`/commesse/${commessaId}/conto-lavoro/${rientroTarget.cl_id}/rientro`, {
                method: 'POST',
                body: { ...rientroForm, certificato_doc_id: uploadedDocId },
            });
            toast.success(res.message || 'Rientro registrato');
            setRientroOpen(false);
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
        finally { setRientroLoading(false); }
    };

    const handleVerificaCL = async (clId) => {
        try {
            const res = await apiRequest(`/commesse/${commessaId}/conto-lavoro/${clId}/verifica`, { method: 'POST' });
            toast.success(res.message || 'Conto lavoro verificato');
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleDownloadNCR = async (clId) => {
        try {
            await downloadPdfBlob(`/commesse/${commessaId}/conto-lavoro/${clId}/ncr-pdf`, `NCR_${clId}.pdf`);
        } catch (e) { toast.error(e.message); }
    };

    return (
        <>
            <div className="space-y-2" data-testid="conto-lavoro-section">
                <Button size="sm" variant="outline" onClick={() => setClOpen(true)} className="text-xs" data-testid="btn-new-cl">
                    <Plus className="h-3 w-3 mr-1" /> Nuovo C/L
                </Button>
                {cl.map(c => {
                    const pesoInviato = (c.righe || []).reduce((s, r) => s + (parseFloat(r.peso_kg) || 0), 0);
                    return (
                    <div key={c.cl_id} className="p-2.5 bg-slate-50 rounded border text-xs space-y-1.5" data-testid={`cl-${c.cl_id}`}>
                        <div className="flex items-center gap-2">
                            <Paintbrush className="h-3.5 w-3.5 text-purple-500 shrink-0" />
                            <span className="font-semibold flex-1 truncate capitalize">{c.tipo} &rarr; {c.fornitore_nome}</span>
                            <StatoBadge stato={c.stato} />
                            {c.esito_qc && c.stato !== 'da_inviare' && (
                                <Badge className={`text-[8px] ${c.esito_qc === 'conforme' ? 'bg-emerald-100 text-emerald-700' : c.esito_qc === 'non_conforme' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                                    QC: {(c.esito_qc || '').replace(/_/g,' ')}
                                </Badge>
                            )}
                            {c.stato_email === 'inviata' && <Badge className="bg-green-100 text-green-700 text-[8px]"><MailCheck className="h-2.5 w-2.5 mr-0.5" />Email</Badge>}
                        </div>
                        {c.ral && <div className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded inline-block">RAL: {c.ral}</div>}
                        {(c.righe || []).length > 0 && <div className="text-[10px] text-slate-500">{c.righe.length} materiali &mdash; {pesoInviato.toFixed(1)} kg inviati{c.peso_rientrato_kg ? ` / ${parseFloat(c.peso_rientrato_kg).toFixed(1)} kg rientrati` : ''}</div>}
                        {c.ddt_fornitore_numero && <div className="text-[10px] text-slate-500">DDT Forn.: {c.ddt_fornitore_numero} del {c.ddt_fornitore_data || ''}</div>}
                        <div className="flex items-center gap-1 flex-wrap pt-1">
                            {c.stato === 'da_inviare' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600" onClick={() => handleUpdateCL(c.cl_id, 'inviato')}>Invia</Button>}
                            {c.stato === 'inviato' && <Button size="sm" variant="ghost" className="h-6 text-[10px] text-amber-600" onClick={() => handleUpdateCL(c.cl_id, 'in_lavorazione')}>In Lav.</Button>}
                            {(c.stato === 'inviato' || c.stato === 'in_lavorazione') && (
                                <Button size="sm" variant="default" className="h-6 text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => openRientroModal(c)} data-testid={`cl-rientro-${c.cl_id}`}>
                                    <Package className="h-3 w-3 mr-0.5" /> Registra Rientro
                                </Button>
                            )}
                            {c.stato === 'rientrato' && (
                                <Button size="sm" variant="default" className="h-6 text-[10px] bg-blue-600 hover:bg-blue-700 text-white" onClick={() => handleVerificaCL(c.cl_id)} data-testid={`cl-verifica-${c.cl_id}`}>
                                    <CheckCircle2 className="h-3 w-3 mr-0.5" /> Verifica e Chiudi
                                </Button>
                            )}
                            {c.stato === 'verificato' && <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-0.5"><CheckCircle2 className="h-3 w-3" /> Chiuso</span>}
                            {c.esito_qc === 'non_conforme' && (
                                <Button size="sm" variant="ghost" className="h-6 text-[10px] text-red-600" onClick={() => handleDownloadNCR(c.cl_id)} data-testid={`cl-ncr-${c.cl_id}`}>
                                    <AlertTriangle className="h-3 w-3 mr-0.5" /> NCR PDF
                                </Button>
                            )}
                            <div className="h-4 w-px bg-slate-200 mx-0.5" />
                            <Button size="sm" variant="ghost" className="h-6 text-[10px] text-blue-600" onClick={() => handlePreviewClPdf(c.cl_id)} data-testid={`cl-preview-${c.cl_id}`}>
                                <Eye className="h-3 w-3 mr-0.5" /> PDF
                            </Button>
                            <Button size="sm" variant="ghost" className="h-6 text-[10px] text-purple-600" disabled={sendingEmail === c.cl_id} onClick={() => handleSendClEmail(c.cl_id)} data-testid={`cl-email-${c.cl_id}`}>
                                {sendingEmail === c.cl_id ? <Loader2 className="h-3 w-3 animate-spin mr-0.5" /> : <Mail className="h-3 w-3 mr-0.5" />}
                                Email
                            </Button>
                        </div>
                    </div>
                    );
                })}
            </div>

            {/* CL Create Dialog */}
            <Dialog open={clOpen} onOpenChange={setClOpen}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader><DialogTitle>Nuovo Conto Lavoro (DDT)</DialogTitle><DialogDescription>Compila i dati per la lavorazione esterna</DialogDescription></DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Tipo Lavorazione</Label>
                                <select value={clForm.tipo} onChange={e => setClForm(f => ({ ...f, tipo: e.target.value }))}
                                    className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="cl-tipo">
                                    <option value="verniciatura">Verniciatura</option>
                                    <option value="zincatura">Zincatura a caldo</option>
                                    <option value="sabbiatura">Sabbiatura</option>
                                    <option value="altro">Altro</option>
                                </select>
                            </div>
                            <div><Label className="text-xs">Fornitore</Label>
                                <select value={clForm.fornitore_id} onChange={(e) => { const val = e.target.value; const f = fornitori.find(x => x.id === val); setClForm(prev => ({ ...prev, fornitore_id: val, fornitore_nome: f?.nome || '' })); }}
                                    className="mt-1 w-full h-9 text-sm rounded-md border border-input bg-transparent px-3 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" data-testid="cl-fornitore">
                                    <option value="">Seleziona fornitore...</option>
                                    {fornitori.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                                </select>
                            </div>
                        </div>
                        {clForm.tipo === 'verniciatura' && (
                            <div><Label className="text-xs">Colore RAL</Label>
                                <Input placeholder="es. RAL 9005, RAL 7016..." value={clForm.ral} onChange={e => setClForm(f => ({ ...f, ral: e.target.value }))} className="mt-1 text-sm" data-testid="cl-ral" />
                            </div>
                        )}
                        <div><Label className="text-xs">Causale Trasporto</Label>
                            <Input value={clForm.causale_trasporto} onChange={e => setClForm(f => ({ ...f, causale_trasporto: e.target.value }))} className="mt-1 text-sm" data-testid="cl-causale" />
                        </div>
                        <div>
                            <Label className="text-xs font-semibold">Materiali da inviare</Label>
                            <div className="mt-1 border rounded-md overflow-hidden">
                                <table className="w-full text-xs">
                                    <thead><tr className="bg-slate-100 text-left">
                                        <th className="p-2 w-[40%]">Descrizione</th><th className="p-2 w-[14%]">Qtà</th>
                                        <th className="p-2 w-[14%]">U.M.</th><th className="p-2 w-[18%]">Peso (kg)</th><th className="p-2 w-[14%]"></th>
                                    </tr></thead>
                                    <tbody>
                                        {(clForm.righe || []).map((riga, idx) => (
                                            <tr key={riga.id || idx} className="border-t">
                                                <td className="p-1"><Input placeholder="es. IPE 200 L=3000mm" value={riga.descrizione} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], descrizione: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 text-xs" data-testid={`cl-riga-desc-${idx}`} /></td>
                                                <td className="p-1"><Input type="number" value={riga.quantita} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], quantita: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 text-xs" /></td>
                                                <td className="p-1">
                                                    <select value={riga.unita} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], unita: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 w-full text-xs rounded border border-input px-1">
                                                        <option value="pz">pz</option><option value="kg">kg</option><option value="m">m</option><option value="mq">mq</option>
                                                    </select>
                                                </td>
                                                <td className="p-1"><Input type="number" step="0.1" value={riga.peso_kg} onChange={e => { const nR = [...clForm.righe]; nR[idx] = { ...nR[idx], peso_kg: e.target.value }; setClForm(f => ({ ...f, righe: nR })); }} className="h-7 text-xs" /></td>
                                                <td className="p-1 text-center">
                                                    {clForm.righe.length > 1 && <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-500" onClick={() => { const nR = clForm.righe.filter((_, i) => i !== idx); setClForm(f => ({ ...f, righe: nR })); }}><Trash2 className="h-3 w-3" /></Button>}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                <Button variant="ghost" size="sm" className="w-full h-7 text-xs text-blue-600 rounded-none border-t" onClick={() => setClForm(f => ({ ...f, righe: [...f.righe, emptyClLine()] }))} data-testid="cl-add-riga">
                                    <Plus className="h-3 w-3 mr-1" /> Aggiungi riga
                                </Button>
                            </div>
                        </div>
                        <div><Label className="text-xs">Note</Label>
                            <Textarea placeholder="Note aggiuntive..." value={clForm.note} onChange={e => setClForm(f => ({ ...f, note: e.target.value }))} className="mt-1 text-sm" rows={2} data-testid="cl-note" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setClOpen(false)}>Annulla</Button>
                        <DisabledTooltip show={!clForm.fornitore_nome || clForm.righe.filter(r => r.descrizione.trim()).length === 0} reason="Seleziona un fornitore e compila almeno una riga materiale">
                        <Button size="sm" disabled={!clForm.fornitore_nome || clForm.righe.filter(r => r.descrizione.trim()).length === 0} onClick={handleCreateCL} className="bg-[#0055FF] text-white" data-testid="btn-confirm-cl">Crea DDT Conto Lavoro</Button>
                        </DisabledTooltip>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Rientro Dialog */}
            <Dialog open={rientroOpen} onOpenChange={setRientroOpen}>
                <DialogContent className="max-w-lg" data-testid="dialog-rientro-cl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-emerald-700"><Package className="h-5 w-5" /> Registra Rientro Materiale</DialogTitle>
                        <DialogDescription>{rientroTarget && <span className="capitalize">{rientroTarget.tipo} &rarr; {rientroTarget.fornitore_nome}</span>}</DialogDescription>
                    </DialogHeader>
                    {rientroTarget && (
                    <div className="space-y-3 max-h-[60vh] overflow-y-auto">
                        <div className="bg-slate-50 rounded border p-2.5 text-xs space-y-1">
                            <div className="font-semibold text-slate-600 mb-1">Dati di Invio (riferimento)</div>
                            <div>Materiali: {(rientroTarget.righe || []).map(r => r.descrizione).join(', ')}</div>
                            <div>Peso inviato: <strong>{(rientroTarget.righe || []).reduce((s, r) => s + (parseFloat(r.peso_kg) || 0), 0).toFixed(1)} kg</strong></div>
                            <div>Data invio: {rientroTarget.data_invio || 'N/D'}</div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Data Rientro</Label><Input type="date" data-testid="input-rientro-data" value={rientroForm.data_rientro} onChange={e => setRientroForm(f => ({...f, data_rientro: e.target.value}))} /></div>
                            <div><Label className="text-xs">Peso Rientrato (kg)</Label><Input type="number" step="0.1" data-testid="input-rientro-peso" value={rientroForm.peso_rientrato_kg} onChange={e => setRientroForm(f => ({...f, peso_rientrato_kg: parseFloat(e.target.value) || 0}))} /></div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">DDT Fornitore N.</Label><Input data-testid="input-rientro-ddt-num" placeholder="Numero DDT fornitore" value={rientroForm.ddt_fornitore_numero} onChange={e => setRientroForm(f => ({...f, ddt_fornitore_numero: e.target.value}))} /></div>
                            <div><Label className="text-xs">Data DDT Fornitore</Label><Input type="date" data-testid="input-rientro-ddt-data" value={rientroForm.ddt_fornitore_data} onChange={e => setRientroForm(f => ({...f, ddt_fornitore_data: e.target.value}))} /></div>
                        </div>
                        <div>
                            <Label className="text-xs">Esito Controllo Qualita'</Label>
                            <Select value={rientroForm.esito_qc} onValueChange={v => setRientroForm(f => ({...f, esito_qc: v}))}>
                                <SelectTrigger data-testid="select-rientro-qc"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="conforme">Conforme</SelectItem>
                                    <SelectItem value="non_conforme">Non Conforme</SelectItem>
                                    <SelectItem value="conforme_con_riserva">Conforme con Riserva</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {rientroForm.esito_qc === 'non_conforme' && (
                            <div><Label className="text-xs text-red-600">Motivo Non Conformita' *</Label>
                                <Textarea data-testid="input-rientro-motivo-nc" className="text-xs border-red-300" rows={2} placeholder="Descrivi il motivo..." value={rientroForm.motivo_non_conformita} onChange={e => setRientroForm(f => ({...f, motivo_non_conformita: e.target.value}))} />
                            </div>
                        )}
                        <div><Label className="text-xs">Carica DDT / Certificato Fornitore (PDF)</Label>
                            <Input type="file" accept=".pdf,.jpg,.jpeg,.png" data-testid="input-rientro-file" className="text-xs" onChange={e => setRientroFile(e.target.files?.[0] || null)} />
                            {!rientroFile && <p className="text-[10px] text-amber-600 mt-0.5">Upload consigliato per il fascicolo tecnico</p>}
                        </div>
                        <div><Label className="text-xs">Note</Label>
                            <Textarea data-testid="input-rientro-note" className="text-xs" rows={2} placeholder="Note aggiuntive..." value={rientroForm.note_rientro} onChange={e => setRientroForm(f => ({...f, note_rientro: e.target.value}))} />
                        </div>
                    </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setRientroOpen(false)}>Annulla</Button>
                        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" disabled={rientroLoading} onClick={handleSubmitRientro} data-testid="btn-confirm-rientro">
                            {rientroLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
                            Conferma Rientro
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* PDF Preview */}
            {pdfPreviewUrl && (
                <Dialog open={!!pdfPreviewUrl} onOpenChange={() => { setPdfPreviewUrl(null); setPdfExpanded(false); }}>
                    <DialogContent className={pdfExpanded ? 'max-w-[95vw] w-full h-[95vh]' : 'max-w-3xl h-[80vh]'}>
                        <DialogHeader><DialogTitle className="text-sm">{pdfPreviewTitle}</DialogTitle></DialogHeader>
                        <iframe src={pdfPreviewUrl} className="flex-1 w-full h-full min-h-0 rounded border" title="PDF Preview" />
                    </DialogContent>
                </Dialog>
            )}

            {/* Email Preview */}
            <EmailPreviewDialog
                open={emailPreview.open}
                onClose={() => setEmailPreview({ open: false, previewUrl: '', sendUrl: '' })}
                previewUrl={emailPreview.previewUrl}
                sendUrl={emailPreview.sendUrl}
                onSent={() => { setEmailPreview({ open: false, previewUrl: '', sendUrl: '' }); onRefresh?.(); }}
            />
        </>
    );
}
