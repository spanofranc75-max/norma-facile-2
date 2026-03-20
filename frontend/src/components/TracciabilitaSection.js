/**
 * TracciabilitaSection — Tracciabilità Materiali EN 1090
 * Shows material batches and AI-extracted certificate data.
 * Extracted from CommessaOpsPanel for maintainability.
 */
import { downloadPdfBlob } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { FileText, Download, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function TracciabilitaSection({ commessaId, materialBatches, docs, onRefresh }) {
    const tracedDocs = (docs || []).filter(d => d.metadata_estratti?.numero_colata);

    const handleUpdateAcciaieria = async (batchId, val) => {
        try {
            await fetch(`${API}/api/commesse/${commessaId}/material-batches/${batchId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ acciaieria: val }),
            });
            toast.success('Acciaieria salvata');
            onRefresh?.();
        } catch {
            toast.error('Errore salvataggio');
        }
    };

    return (
        <div className="space-y-2" data-testid="tracciabilita-section">
            {materialBatches.length > 0 && (
                <div className="flex justify-end mb-2">
                    <Button size="sm" variant="outline" data-testid="btn-scheda-rintracciabilita" className="text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                        onClick={async () => {
                            try {
                                await downloadPdfBlob(`/commesse/${commessaId}/scheda-rintracciabilita-pdf`, `Scheda_Rintracciabilita_${commessaId}.pdf`);
                                toast.success('Scheda Rintracciabilità scaricata');
                            } catch (e) { toast.error(e.message); }
                        }}>
                        <Download className="h-3.5 w-3.5 mr-1" /> Scheda Rintracciabilità PDF
                    </Button>
                </div>
            )}

            {/* From material_batches collection */}
            {materialBatches.map(b => (
                <div key={b.batch_id} className={`p-2 rounded border text-xs ${b.ddt_presente === false ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`} data-testid={`batch-${b.batch_id}`}>
                    <div className="flex items-center gap-2 mb-1">
                        {b.ddt_presente === false
                            ? <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                            : <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        }
                        <span className={`font-semibold ${b.ddt_presente === false ? 'text-amber-800' : 'text-emerald-800'}`}>{b.dimensions || b.material_type || 'Materiale'}</span>
                        <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">EN 1090</Badge>
                        {b.ddt_presente === false && <Badge className="bg-amber-100 text-amber-700 text-[9px]">Senza DDT</Badge>}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
                        <div><span className="text-slate-500 block">N. Colata</span><span className="font-mono font-bold text-emerald-700">{b.heat_number || '-'}</span></div>
                        <div><span className="text-slate-500 block">Qualità</span><span className="font-mono">{b.material_type || '-'}</span></div>
                        <div><span className="text-slate-500 block">Fornitore</span><span className="font-mono">{b.supplier_name || '-'}</span></div>
                        <div><span className="text-slate-500 block">Profilo</span><span className="font-mono">{b.dimensions || '-'}</span></div>
                        <div><span className="text-slate-500 block">N. Certificato</span><span className="font-mono">{b.numero_certificato || '-'}</span></div>
                        <div><span className="text-slate-500 block">DDT N.</span><span className="font-mono">{b.ddt_numero || '-'}</span></div>
                        <div><span className="text-slate-500 block">Posizione</span><span className="font-mono">{b.posizione || '-'}</span></div>
                        <div><span className="text-slate-500 block">N. Pezzi</span><span className="font-mono">{b.n_pezzi || '-'}</span></div>
                        <div>
                            <span className="text-slate-500 block">Acciaieria</span>
                            <input
                                defaultValue={b.acciaieria || ''}
                                placeholder="es. AFV Beltrame"
                                className="font-mono text-[10px] w-full border border-slate-200 rounded px-1 h-5 bg-white focus:border-emerald-400 focus:outline-none transition-colors"
                                data-testid={`acciaieria-${b.batch_id}`}
                                onBlur={(e) => {
                                    const val = e.target.value.trim();
                                    if (val === (b.acciaieria || '')) return;
                                    handleUpdateAcciaieria(b.batch_id, val);
                                }}
                            />
                        </div>
                    </div>
                </div>
            ))}

            {/* From documents with extracted metadata */}
            {tracedDocs.map(d => (
                <div key={d.doc_id} className="p-2 bg-blue-50 rounded border border-blue-200 text-xs" data-testid={`traced-${d.doc_id}`}>
                    <div className="flex items-center gap-2 mb-1">
                        <Sparkles className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                        <span className="font-semibold text-blue-800">{d.nome_file}</span>
                        <Badge className="bg-blue-100 text-blue-700 text-[9px]">AI OCR</Badge>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
                        <div><span className="text-slate-500 block">N. Colata</span><span className="font-mono font-bold text-blue-700">{d.metadata_estratti.numero_colata}</span></div>
                        <div><span className="text-slate-500 block">Qualità</span><span className="font-mono">{d.metadata_estratti.qualita_acciaio || '-'}</span></div>
                        <div><span className="text-slate-500 block">Fornitore</span><span className="font-mono">{d.metadata_estratti.fornitore || '-'}</span></div>
                        <div><span className="text-slate-500 block">Normativa</span><span className="font-mono">{d.metadata_estratti.normativa_riferimento || d.metadata_estratti.normativa || '-'}</span></div>
                    </div>
                </div>
            ))}

            {materialBatches.length === 0 && tracedDocs.length === 0 && (
                <div className="text-center py-4 text-slate-400 text-xs">
                    <FileText className="h-6 w-6 mx-auto mb-1 opacity-50" />
                    <p>Nessun materiale tracciato</p>
                    <p className="text-[10px] mt-1">Carica un certificato 3.1 e clicca "Analizza AI" per estrarre i dati</p>
                </div>
            )}
        </div>
    );
}
