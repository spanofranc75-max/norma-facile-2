/**
 * CAMSection — Criteri Ambientali Minimi (DM 256/2022)
 * Manages CAM material lots, compliance calculation, PDF/Green Certificate generation.
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { useState } from 'react';
import { apiRequest, downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { useConfirm } from '../components/ConfirmProvider';
import { toast } from 'sonner';
import {
    Plus, Trash2, Download, RefreshCw, CheckCircle2,
    AlertTriangle, Sparkles, Leaf,
} from 'lucide-react';

export default function CAMSection({ commessaId, commessaNumero, camLotti, camCalcolo, docs, onRefreshCam }) {
    const confirm = useConfirm();
    const [camLoading, setCamLoading] = useState(false);
    const [camLottoOpen, setCamLottoOpen] = useState(false);
    const [editingCamLotto, setEditingCamLotto] = useState(null);
    const [camLottoForm, setCamLottoForm] = useState({
        descrizione: '', fornitore: '', numero_colata: '', peso_kg: 0, qualita_acciaio: '',
        percentuale_riciclato: 75, metodo_produttivo: 'forno_elettrico_non_legato',
        tipo_certificazione: 'dichiarazione_produttore', numero_certificazione: '',
        ente_certificatore: '', uso_strutturale: true, commessa_id: commessaId,
    });

    const resetForm = () => {
        setCamLottoForm({ descrizione: '', fornitore: '', numero_colata: '', peso_kg: 0, qualita_acciaio: '', percentuale_riciclato: 75, metodo_produttivo: 'forno_elettrico_non_legato', tipo_certificazione: 'dichiarazione_produttore', numero_certificazione: '', ente_certificatore: '', uso_strutturale: true, commessa_id: commessaId });
        setEditingCamLotto(null);
    };

    const handleCreateCamLotto = async () => {
        if (!camLottoForm.descrizione.trim()) { toast.error('Inserisci una descrizione'); return; }
        try {
            const payload = { ...camLottoForm, peso_kg: parseFloat(camLottoForm.peso_kg) || 0, percentuale_riciclato: parseFloat(camLottoForm.percentuale_riciclato) || 0, commessa_id: commessaId };
            if (editingCamLotto) {
                await apiRequest(`/cam/lotti/${editingCamLotto}`, { method: 'PUT', body: payload });
                toast.success('Lotto CAM aggiornato');
            } else {
                await apiRequest('/cam/lotti', { method: 'POST', body: payload });
                toast.success('Lotto CAM creato');
            }
            setCamLottoOpen(false);
            resetForm();
            onRefreshCam?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleCalcolaCAM = async () => {
        setCamLoading(true);
        try {
            await apiRequest(`/cam/calcola/${commessaId}`, { method: 'POST' });
            toast.success('Calcolo CAM aggiornato');
            onRefreshCam?.();
        } catch (e) { toast.error(e.message); }
        finally { setCamLoading(false); }
    };

    const handleDownloadCamPdf = async () => {
        try {
            await downloadPdfBlob(`/cam/dichiarazione-pdf/${commessaId}`, `Dichiarazione_CAM_${commessaNumero || commessaId}.pdf`);
            toast.success('Dichiarazione CAM generata');
        } catch (e) { toast.error(e.message); }
    };

    const handleDownloadGreenCert = async () => {
        try {
            await downloadPdfBlob(`/cam/green-certificate/${commessaId}`, `Green_Certificate_${commessaNumero || commessaId}.pdf`);
            toast.success('Green Certificate generato');
        } catch (e) { toast.error(e.message); }
    };

    const handleImportCamFromCert = async (docId) => {
        setCamLoading(true);
        try {
            await apiRequest(`/cam/import-da-certificato/${docId}?commessa_id=${commessaId}&peso_kg=0`, { method: 'POST' });
            toast.success('Dati CAM importati dal certificato');
            onRefreshCam?.();
        } catch (e) { toast.error(e.message); }
        finally { setCamLoading(false); }
    };

    const openEditCamLotto = (lotto) => {
        setCamLottoForm({
            descrizione: lotto.descrizione || '', fornitore: lotto.fornitore || '', numero_colata: lotto.numero_colata || '',
            peso_kg: lotto.peso_kg || 0, qualita_acciaio: lotto.qualita_acciaio || '',
            percentuale_riciclato: lotto.percentuale_riciclato || 0, metodo_produttivo: lotto.metodo_produttivo || 'forno_elettrico_non_legato',
            tipo_certificazione: lotto.tipo_certificazione || 'dichiarazione_produttore', numero_certificazione: lotto.numero_certificazione || '',
            ente_certificatore: lotto.ente_certificatore || '', uso_strutturale: lotto.uso_strutturale !== false, commessa_id: commessaId,
        });
        setEditingCamLotto(lotto.lotto_id);
        setCamLottoOpen(true);
    };

    const importableDocs = (docs || []).filter(d => d.metadata_estratti?.numero_colata && !camLotti.find(l => l.numero_colata === d.metadata_estratti.numero_colata));

    return (
        <>
            <div className="space-y-3" data-testid="cam-section">
                {/* Summary Card */}
                {camCalcolo && camCalcolo.righe?.length > 0 && (
                    <div className={`p-3 rounded-lg border-2 ${camCalcolo.conforme_cam ? 'bg-emerald-50 border-emerald-400' : 'bg-red-50 border-red-400'}`} data-testid="cam-summary">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                {camCalcolo.conforme_cam ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <AlertTriangle className="h-5 w-5 text-red-600" />}
                                <span className={`text-sm font-bold ${camCalcolo.conforme_cam ? 'text-emerald-800' : 'text-red-800'}`}>{camCalcolo.conforme_cam ? 'CONFORME CAM' : 'NON CONFORME CAM'}</span>
                            </div>
                            <Badge className={camCalcolo.conforme_cam ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>DM 256/2022</Badge>
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-center">
                            <div className="bg-white/60 rounded p-1.5"><p className="text-[10px] text-slate-500">Peso Totale</p><p className="text-xs font-bold text-slate-800">{(camCalcolo.peso_totale_kg || 0).toLocaleString('it-IT')} kg</p></div>
                            <div className="bg-white/60 rounded p-1.5"><p className="text-[10px] text-slate-500">Peso Riciclato</p><p className="text-xs font-bold text-slate-800">{(camCalcolo.peso_riciclato_kg || 0).toLocaleString('it-IT')} kg</p></div>
                            <div className="bg-white/60 rounded p-1.5"><p className="text-[10px] text-slate-500">% Riciclato</p><p className={`text-sm font-bold ${camCalcolo.conforme_cam ? 'text-emerald-700' : 'text-red-700'}`}>{(camCalcolo.percentuale_riciclato_totale || 0).toFixed(1)}%</p></div>
                            <div className="bg-white/60 rounded p-1.5"><p className="text-[10px] text-slate-500">Soglia Min.</p><p className="text-xs font-bold text-slate-600">{camCalcolo.soglia_minima_richiesta || 0}%</p></div>
                        </div>
                    </div>
                )}

                {/* Action buttons */}
                <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="outline" onClick={() => { resetForm(); setCamLottoOpen(true); }} className="text-xs" data-testid="btn-new-cam-lotto"><Plus className="h-3 w-3 mr-1" /> Aggiungi Materiale</Button>
                    <Button size="sm" variant="outline" onClick={handleCalcolaCAM} disabled={camLoading} className="text-xs" data-testid="btn-calcola-cam"><RefreshCw className={`h-3 w-3 mr-1 ${camLoading ? 'animate-spin' : ''}`} /> Ricalcola</Button>
                    {camLotti.length > 0 && <Button size="sm" onClick={handleDownloadCamPdf} className="text-xs bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-cam-pdf"><Download className="h-3 w-3 mr-1" /> Dichiarazione CAM PDF</Button>}
                    {camLotti.length > 0 && <Button size="sm" variant="outline" onClick={handleDownloadGreenCert} className="text-xs border-green-500 text-green-700 hover:bg-green-50" data-testid="btn-green-certificate"><Leaf className="h-3 w-3 mr-1" /> Green Certificate</Button>}
                    {camLotti.length > 0 && (
                        <Button size="sm" variant="outline" className="text-xs border-red-300 text-red-600 hover:bg-red-50 ml-auto" data-testid="btn-delete-all-cam"
                            onClick={async () => {
                                if (!(await confirm(`Eliminare tutti i ${camLotti.length} lotti CAM di questa commessa?`))) return;
                                try { await apiRequest(`/cam/lotti/commessa/${commessaId}`, { method: 'DELETE' }); toast.success('Tutti i lotti CAM eliminati'); onRefreshCam?.(); } catch (err) { toast.error(err.message || 'Errore eliminazione'); }
                            }}>
                            <Trash2 className="h-3 w-3 mr-1" /> Elimina Tutti
                        </Button>
                    )}
                </div>

                {/* Import from AI-analyzed certificates */}
                {importableDocs.length > 0 && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs" data-testid="cam-import-certs">
                        <p className="font-semibold text-amber-800 mb-1.5 flex items-center gap-1"><Sparkles className="h-3.5 w-3.5" /> Certificati analizzati importabili</p>
                        <div className="space-y-1">
                            {importableDocs.map(d => (
                                <div key={d.doc_id} className="flex items-center justify-between bg-white rounded p-1.5 border border-amber-100">
                                    <span className="text-slate-700 truncate flex-1">{d.nome_file} — <span className="font-mono">{d.metadata_estratti.numero_colata}</span>{d.metadata_estratti.percentuale_riciclato != null && <Badge className="ml-1 bg-emerald-50 text-emerald-700 text-[9px]">{d.metadata_estratti.percentuale_riciclato}% ric.</Badge>}</span>
                                    <Button size="sm" variant="ghost" className="h-6 text-[10px] text-amber-700" onClick={() => handleImportCamFromCert(d.doc_id)} disabled={camLoading} data-testid={`btn-import-cam-${d.doc_id}`}><Plus className="h-3 w-3 mr-0.5" /> Importa</Button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Material list */}
                {camLotti.map(lotto => (
                    <div key={lotto.lotto_id} className={`p-2 rounded border text-xs ${lotto.conforme_cam ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`} data-testid={`cam-lotto-${lotto.lotto_id}`}>
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2 cursor-pointer flex-1" onClick={() => openEditCamLotto(lotto)}>
                                {lotto.conforme_cam ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                                <span className="font-semibold text-slate-800">{lotto.descrizione}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <Badge className={`text-[9px] ${lotto.conforme_cam ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>{lotto.percentuale_riciclato}% ric. (soglia {lotto.soglia_minima_cam}%)</Badge>
                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-400 hover:text-red-600 hover:bg-red-50" data-testid={`delete-cam-lotto-${lotto.lotto_id}`}
                                    onClick={async (e) => {
                                        e.stopPropagation();
                                        if (!(await confirm(`Eliminare il lotto CAM "${lotto.descrizione}"?`))) return;
                                        try { await apiRequest(`/cam/lotti/${lotto.lotto_id}`, { method: 'DELETE' }); toast.success('Lotto CAM eliminato'); onRefreshCam?.(); } catch (err) { toast.error(err.message || 'Errore eliminazione'); }
                                    }}>
                                    <Trash2 className="h-3 w-3" />
                                </Button>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-[10px] cursor-pointer" onClick={() => openEditCamLotto(lotto)}>
                            <div><span className="text-slate-500 block">Fornitore</span><span className="font-mono">{lotto.fornitore || '-'}</span></div>
                            <div><span className="text-slate-500 block">Colata</span><span className="font-mono">{lotto.numero_colata || '-'}</span></div>
                            <div><span className="text-slate-500 block">Peso</span><span className="font-mono">{lotto.peso_kg} kg</span></div>
                            <div><span className="text-slate-500 block">Metodo</span><span className="font-mono">{(lotto.metodo_produttivo || '').replace(/_/g, ' ')}</span></div>
                            <div><span className="text-slate-500 block">Cert.</span><span className="font-mono">{(lotto.tipo_certificazione || '').replace(/_/g, ' ')}</span></div>
                        </div>
                    </div>
                ))}

                {camLotti.length === 0 && (
                    <div className="text-center py-4 text-slate-400 text-xs" data-testid="cam-empty">
                        <Leaf className="h-6 w-6 mx-auto mb-1 opacity-50" />
                        <p>Nessun materiale CAM registrato</p>
                        <p className="text-[10px] mt-1">Aggiungi materiali o importa dai certificati analizzati con AI</p>
                    </div>
                )}
            </div>

            {/* CAM Lotto Dialog */}
            <Dialog open={camLottoOpen} onOpenChange={(open) => { setCamLottoOpen(open); if (!open) resetForm(); }}>
                <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="cam-lotto-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><Leaf className="h-5 w-5 text-emerald-600" />{editingCamLotto ? 'Modifica Lotto CAM' : 'Nuovo Lotto Materiale CAM'}</DialogTitle>
                        <DialogDescription>Inserisci i dati del materiale per il calcolo CAM</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Descrizione *</Label><Input value={camLottoForm.descrizione} onChange={e => setCamLottoForm(f => ({ ...f, descrizione: e.target.value }))} placeholder="es. IPE 200, HEB 160" className="mt-1 h-8 text-sm" data-testid="cam-descrizione" /></div>
                            <div><Label className="text-xs">Qualità acciaio</Label><Input value={camLottoForm.qualita_acciaio} onChange={e => setCamLottoForm(f => ({ ...f, qualita_acciaio: e.target.value }))} placeholder="es. S275JR" className="mt-1 h-8 text-sm" data-testid="cam-qualita" /></div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Fornitore</Label><Input value={camLottoForm.fornitore} onChange={e => setCamLottoForm(f => ({ ...f, fornitore: e.target.value }))} placeholder="Acciaieria" className="mt-1 h-8 text-sm" data-testid="cam-fornitore" /></div>
                            <div><Label className="text-xs">N. Colata</Label><Input value={camLottoForm.numero_colata} onChange={e => setCamLottoForm(f => ({ ...f, numero_colata: e.target.value }))} placeholder="Heat number" className="mt-1 h-8 text-sm" data-testid="cam-colata" /></div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Peso (kg) *</Label><Input type="number" value={camLottoForm.peso_kg} onChange={e => setCamLottoForm(f => ({ ...f, peso_kg: e.target.value }))} className="mt-1 h-8 text-sm" data-testid="cam-peso" /></div>
                            <div><Label className="text-xs">% Riciclato *</Label><Input type="number" min="0" max="100" value={camLottoForm.percentuale_riciclato} onChange={e => setCamLottoForm(f => ({ ...f, percentuale_riciclato: e.target.value }))} className="mt-1 h-8 text-sm" data-testid="cam-perc-riciclato" /></div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">Metodo produttivo</Label>
                                <Select value={camLottoForm.metodo_produttivo} onValueChange={v => setCamLottoForm(f => ({ ...f, metodo_produttivo: v }))}><SelectTrigger className="mt-1 h-8 text-xs" data-testid="cam-metodo"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="forno_elettrico_non_legato">Forno Elettrico (non legato) - soglia 75%</SelectItem><SelectItem value="forno_elettrico_legato">Forno Elettrico (legato) - soglia 60%</SelectItem><SelectItem value="ciclo_integrale">Ciclo Integrale (altoforno) - soglia 12%</SelectItem></SelectContent></Select>
                            </div>
                            <div><Label className="text-xs">Certificazione</Label>
                                <Select value={camLottoForm.tipo_certificazione} onValueChange={v => setCamLottoForm(f => ({ ...f, tipo_certificazione: v }))}><SelectTrigger className="mt-1 h-8 text-xs" data-testid="cam-certificazione"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="epd">EPD (ISO 14025, EN 15804)</SelectItem><SelectItem value="remade_in_italy">ReMade in Italy</SelectItem><SelectItem value="dichiarazione_produttore">Dichiarazione Produttore</SelectItem><SelectItem value="altra_accreditata">Altra certificazione</SelectItem><SelectItem value="nessuna">Nessuna</SelectItem></SelectContent></Select>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label className="text-xs">N. Certificazione</Label><Input value={camLottoForm.numero_certificazione} onChange={e => setCamLottoForm(f => ({ ...f, numero_certificazione: e.target.value }))} className="mt-1 h-8 text-sm" data-testid="cam-num-cert" /></div>
                            <div><Label className="text-xs">Ente certificatore</Label><Input value={camLottoForm.ente_certificatore} onChange={e => setCamLottoForm(f => ({ ...f, ente_certificatore: e.target.value }))} placeholder="es. ICMQ, Bureau Veritas" className="mt-1 h-8 text-sm" data-testid="cam-ente" /></div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Checkbox checked={camLottoForm.uso_strutturale} onCheckedChange={v => setCamLottoForm(f => ({ ...f, uso_strutturale: v }))} id="cam-strutturale" data-testid="cam-strutturale" />
                            <Label htmlFor="cam-strutturale" className="text-xs">Uso strutturale (soglie più restrittive)</Label>
                        </div>
                        <div className="p-2 bg-slate-50 rounded text-[10px] text-slate-500"><strong>Soglie CAM (DM 256/2022):</strong>{' Forno el. non legato \u2265 75% | Forno el. legato \u2265 60% | Ciclo integrale \u2265 12%'}</div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setCamLottoOpen(false)}>Annulla</Button>
                        <Button size="sm" onClick={handleCreateCamLotto} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-save-cam-lotto">{editingCamLotto ? 'Aggiorna' : 'Crea Lotto'}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
