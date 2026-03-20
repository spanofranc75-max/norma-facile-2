/**
 * ProduzioneSection — Fasi produzione + Diario di Produzione
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { useState } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Factory, Play, CheckCircle2 } from 'lucide-react';
import DiarioProduzione from './DiarioProduzione';

export default function ProduzioneSection({ commessaId, commessaNumero, fasi, progPct, normativaTipo, vociLavoro = [], onRefresh }) {
    const [faseComplOpen, setFaseComplOpen] = useState(false);
    const [faseComplTarget, setFaseComplTarget] = useState(null);
    const [faseComplForm, setFaseComplForm] = useState({ started_at: '', completed_at: '', operator_name: '' });

    const handleInitProduzione = async () => {
        try {
            await apiRequest(`/commesse/${commessaId}/produzione/init`, { method: 'POST' });
            toast.success('Fasi produzione inizializzate');
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const handleUpdateFase = async (tipo, stato, extra = {}) => {
        try {
            await apiRequest(`/commesse/${commessaId}/produzione/${tipo}`, { method: 'PUT', body: { stato, ...extra } });
            toast.success('Fase aggiornata');
            onRefresh?.();
        } catch (e) { toast.error(e.message); }
    };

    const openFaseCompletaModal = (fase) => {
        const now = new Date().toISOString().slice(0, 16);
        setFaseComplTarget(fase);
        setFaseComplForm({
            started_at: fase.data_inizio ? fase.data_inizio.slice(0, 16) : now,
            completed_at: now,
            operator_name: fase.operator_name || '',
        });
        setFaseComplOpen(true);
    };

    const handleConfirmCompleta = async () => {
        if (!faseComplTarget) return;
        await handleUpdateFase(faseComplTarget.tipo, 'completato', {
            started_at: faseComplForm.started_at,
            completed_at: faseComplForm.completed_at,
            operator_name: faseComplForm.operator_name,
        });
        setFaseComplOpen(false);
    };

    return (
        <>
            <div className="space-y-3" data-testid="produzione-section">
                {fasi.length === 0 ? (
                    <div className="text-center py-4">
                        <p className="text-xs text-slate-400 mb-2">Nessuna fase. Inizializza le fasi di produzione.</p>
                        <Button size="sm" onClick={handleInitProduzione} data-testid="btn-init-prod">
                            <Factory className="h-3 w-3 mr-1" /> Inizializza Produzione
                        </Button>
                    </div>
                ) : (
                    <>
                        <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                            <div className="flex-1 bg-slate-200 rounded-full h-2">
                                <div className="bg-[#0055FF] h-2 rounded-full transition-all" style={{ width: `${progPct}%` }} />
                            </div>
                            <span className="font-mono text-[10px]">{progPct}%</span>
                        </div>
                        {/* Diario di Produzione integrato */}
                        <DiarioProduzione
                            commessaId={commessaId}
                            commessaNumero={commessaNumero}
                            fasi={fasi}
                            normativaTipo={normativaTipo}
                            vociLavoro={vociLavoro}
                            onFaseUpdate={(tipo, stato, extra) => handleUpdateFase(tipo, stato, extra)}
                            onFaseComplete={openFaseCompletaModal}
                            onRefresh={onRefresh}
                        />
                    </>
                )}
            </div>

            {/* Fase Completamento Dialog */}
            <Dialog open={faseComplOpen} onOpenChange={setFaseComplOpen}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle className="text-sm">Completa Fase: {faseComplTarget?.label || faseComplTarget?.tipo}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-2 py-2">
                        <div>
                            <Label className="text-xs">Inizio effettivo</Label>
                            <Input type="datetime-local" value={faseComplForm.started_at} onChange={e => setFaseComplForm(f => ({ ...f, started_at: e.target.value }))} className="h-8 text-sm" />
                        </div>
                        <div>
                            <Label className="text-xs">Fine effettiva</Label>
                            <Input type="datetime-local" value={faseComplForm.completed_at} onChange={e => setFaseComplForm(f => ({ ...f, completed_at: e.target.value }))} className="h-8 text-sm" />
                        </div>
                        <div>
                            <Label className="text-xs">Operatore responsabile</Label>
                            <Input value={faseComplForm.operator_name} onChange={e => setFaseComplForm(f => ({ ...f, operator_name: e.target.value }))} className="h-8 text-sm" placeholder="Nome operatore" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setFaseComplOpen(false)}>Annulla</Button>
                        <Button size="sm" className="bg-emerald-600 text-white" onClick={handleConfirmCompleta}>
                            <CheckCircle2 className="h-3 w-3 mr-1" /> Completa
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
