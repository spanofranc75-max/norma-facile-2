/**
 * EmissioneDetailPanel — Vista dettagliata di una singola emissione.
 * Mostra: Cosa serve | Cosa c'e | Cosa manca/blocca
 * Permette collegamento evidenze e visualizzazione Evidence Gate.
 */
import { useState, useCallback, useEffect } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
    Shield, FileOutput, Lock, Unlock, Loader2,
    AlertTriangle, CheckCircle2, Clock, X,
    Link2, Upload, ExternalLink, RefreshCw,
    Package, FileText, Wrench, HardHat, Thermometer, Eye,
} from 'lucide-react';

const STATUS_COLORS = {
    verified:       'bg-emerald-100 text-emerald-700 border-emerald-200',
    linked:         'bg-blue-100 text-blue-700 border-blue-200',
    uploaded:       'bg-amber-100 text-amber-700 border-amber-200',
    missing:        'bg-red-100 text-red-700 border-red-200',
    failed:         'bg-red-200 text-red-800 border-red-300',
    not_applicable: 'bg-slate-50 text-slate-400 border-slate-200',
    required:       'bg-slate-100 text-slate-600 border-slate-200',
};

const STATUS_ICONS = {
    verified: CheckCircle2, linked: Link2, uploaded: Upload,
    missing: AlertTriangle, failed: X, not_applicable: Clock,
};

const CHECK_ICONS = {
    EMISSION_SCOPE: Package, BRANCH_STATUS: Shield, EMISSION_NOT_ISSUED: FileOutput,
    MATERIAL_BATCHES: Package, CERT_31: FileText, WPS_WPQR: Wrench,
    WELDER_QUALIFICATION: HardHat, WELDING_REGISTER: FileText,
    VT_INSPECTION: Eye, FINAL_CONTROL: CheckCircle2,
    TECHNICAL_REVIEW: FileText, SUBCONTRACT_DOC: ExternalLink,
    TOOLING_STATUS: Wrench, PRODUCT_IDENTIFICATION: Package,
    USER_MANUAL: FileText, TEST_EVIDENCE: Thermometer,
    SAFETY_DEVICE_DOC: Shield, INSTALLATION_EVIDENCE: HardHat,
    NO_NORMATIVE_REQUIRED: CheckCircle2,
};

const CHECK_LABELS = {
    EMISSION_SCOPE: 'Scope emissione', BRANCH_STATUS: 'Stato ramo',
    EMISSION_NOT_ISSUED: 'Non ancora emessa', MATERIAL_BATCHES: 'Lotti materiale',
    CERT_31: 'Certificati 3.1', WPS_WPQR: 'WPS / WPQR',
    WELDER_QUALIFICATION: 'Saldatori qualificati', WELDING_REGISTER: 'Registro saldatura',
    VT_INSPECTION: 'Controllo VT', FINAL_CONTROL: 'Controllo Finale',
    TECHNICAL_REVIEW: 'Riesame Tecnico', SUBCONTRACT_DOC: 'Doc. terzista/zinc.',
    TOOLING_STATUS: 'Strumenti / ITT', PRODUCT_IDENTIFICATION: 'Identificazione prodotto',
    USER_MANUAL: 'Manuale uso', TEST_EVIDENCE: 'Evidenze collaudo',
    SAFETY_DEVICE_DOC: 'Doc. dispositivi', INSTALLATION_EVIDENCE: 'Evidenza posa',
    NO_NORMATIVE_REQUIRED: 'Nessun requisito',
};

const STATUS_LABELS = {
    verified: 'Verificato', linked: 'Collegato', uploaded: 'Caricato',
    missing: 'Mancante', failed: 'Fallito', not_applicable: 'Non applicabile',
};

export default function EmissioneDetailPanel({ emissione, ramoId, onClose, onRefresh }) {
    const [gate, setGate] = useState(null);
    const [loading, setLoading] = useState(false);
    const [linkOpen, setLinkOpen] = useState(null); // check code for linking
    const [linkIds, setLinkIds] = useState('');
    const [linking, setLinking] = useState(false);

    const fetchGate = useCallback(async () => {
        setLoading(true);
        try {
            const g = await apiRequest(`/emissioni/${ramoId}/${emissione.emissione_id}/gate`);
            setGate(g);
        } catch (e) {
            toast.error(e.message || 'Errore verifica gate');
        } finally {
            setLoading(false);
        }
    }, [ramoId, emissione.emissione_id]);

    useEffect(() => { fetchGate(); }, [fetchGate]);

    const handleLinkEvidence = async (field) => {
        if (!linkIds.trim()) return;
        setLinking(true);
        const ids = linkIds.split(',').map(s => s.trim()).filter(Boolean);
        try {
            await apiRequest(`/emissioni/${ramoId}/${emissione.emissione_id}`, {
                method: 'PATCH',
                body: JSON.stringify({ [field]: ids }),
            });
            toast.success('Evidenza collegata');
            setLinkOpen(null);
            setLinkIds('');
            fetchGate();
            onRefresh?.();
        } catch (e) {
            toast.error(e.message || 'Errore collegamento');
        } finally {
            setLinking(false);
        }
    };

    const handleEmetti = async () => {
        try {
            await apiRequest(`/emissioni/${ramoId}/${emissione.emissione_id}/emetti`, { method: 'POST' });
            toast.success('Emissione emessa con successo!');
            onRefresh?.();
            onClose?.();
        } catch (e) {
            toast.error(e.message || 'Emissione bloccata');
        }
    };

    const checks = gate?.checks || [];
    const required = checks.filter(c => c.required);
    const satisfied = required.filter(c => ['verified', 'linked', 'uploaded'].includes(c.status));
    const missingChecks = required.filter(c => !['verified', 'linked', 'uploaded', 'not_applicable'].includes(c.status));
    const naChecks = checks.filter(c => c.status === 'not_applicable');

    // Map check codes to linkable fields
    const linkableFields = {
        MATERIAL_BATCHES: 'batch_ids', CERT_31: 'batch_ids',
        EMISSION_SCOPE: 'line_ids', SUBCONTRACT_DOC: 'document_ids',
        USER_MANUAL: 'document_ids', TEST_EVIDENCE: 'document_ids',
        SAFETY_DEVICE_DOC: 'document_ids', INSTALLATION_EVIDENCE: 'document_ids',
    };

    return (
        <Card className="border-2 border-blue-200 shadow-lg" data-testid="emissione-detail-panel">
            <CardHeader className="bg-gradient-to-r from-slate-800 to-slate-700 py-2.5 px-4 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                        <FileOutput className="h-3.5 w-3.5" />
                        {emissione.codice_emissione}
                        {emissione.descrizione && <span className="font-normal text-slate-300">— {emissione.descrizione}</span>}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-white hover:bg-white/10" onClick={fetchGate} disabled={loading}>
                            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-white hover:bg-white/10" onClick={onClose}>
                            <X className="h-3 w-3" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-3 space-y-3">
                {loading && !gate && (
                    <div className="flex items-center justify-center py-6">
                        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                    </div>
                )}

                {gate && (
                    <>
                        {/* Status banner */}
                        <div className={`flex items-center justify-between p-2.5 rounded-lg ${gate.emittable ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`} data-testid="gate-status-banner">
                            <div className="flex items-center gap-2">
                                {gate.emittable ? <Unlock className="h-4 w-4 text-emerald-600" /> : <Lock className="h-4 w-4 text-red-600" />}
                                <span className={`text-sm font-semibold ${gate.emittable ? 'text-emerald-700' : 'text-red-700'}`}>
                                    {gate.emittable ? 'Emissione EMETTIBILE' : 'Emissione BLOCCATA'}
                                </span>
                                <Badge className={`text-[10px] ${gate.emittable ? 'bg-emerald-200 text-emerald-800' : 'bg-red-200 text-red-800'}`}>
                                    {gate.completion_percent}% completo
                                </Badge>
                            </div>
                            {gate.emittable && (
                                <Button size="sm" className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-700" onClick={handleEmetti} data-testid="btn-emetti-emissione">
                                    Emetti
                                </Button>
                            )}
                        </div>

                        {/* Progress bar */}
                        <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full transition-all duration-500 ${gate.completion_percent >= 80 ? 'bg-emerald-500' : gate.completion_percent >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                                style={{ width: `${gate.completion_percent}%` }} />
                        </div>

                        {/* 3-column layout: Cosa serve | Cosa c'e | Cosa manca */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                            {/* COSA SERVE */}
                            <div className="space-y-1.5">
                                <h4 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Cosa serve</h4>
                                {required.map(c => {
                                    const Icon = CHECK_ICONS[c.code] || FileText;
                                    return (
                                        <div key={c.code} className="flex items-center gap-1.5 p-1.5 rounded bg-slate-50 text-[11px]">
                                            <Icon className="h-3 w-3 text-slate-400 shrink-0" />
                                            <span className="text-slate-700">{CHECK_LABELS[c.code] || c.code}</span>
                                        </div>
                                    );
                                })}
                                {naChecks.length > 0 && (
                                    <div className="pt-1 border-t">
                                        <span className="text-[9px] text-slate-400 uppercase">Non applicabili ({naChecks.length})</span>
                                        {naChecks.map(c => (
                                            <div key={c.code} className="flex items-center gap-1 p-1 text-[10px] text-slate-400">
                                                <Clock className="h-2.5 w-2.5" />
                                                {CHECK_LABELS[c.code] || c.code}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* COSA C'E */}
                            <div className="space-y-1.5">
                                <h4 className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider">Cosa c'e</h4>
                                {satisfied.length === 0 && (
                                    <p className="text-[10px] text-slate-400 py-2">Nessuna evidenza ancora collegata</p>
                                )}
                                {satisfied.map(c => {
                                    const Icon = STATUS_ICONS[c.status] || CheckCircle2;
                                    return (
                                        <div key={c.code} className={`flex items-center gap-1.5 p-1.5 rounded border text-[11px] ${STATUS_COLORS[c.status]}`}>
                                            <Icon className="h-3 w-3 shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <span className="font-medium">{CHECK_LABELS[c.code] || c.code}</span>
                                                <span className="ml-1 text-[9px] opacity-70">({STATUS_LABELS[c.status]})</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* COSA MANCA */}
                            <div className="space-y-1.5">
                                <h4 className="text-[10px] font-semibold text-red-600 uppercase tracking-wider">Cosa manca</h4>
                                {missingChecks.length === 0 && (
                                    <p className="text-[10px] text-emerald-600 py-2">Tutto presente!</p>
                                )}
                                {missingChecks.map(c => {
                                    const Icon = CHECK_ICONS[c.code] || AlertTriangle;
                                    const canLink = linkableFields[c.code];
                                    return (
                                        <div key={c.code} className="flex items-center gap-1.5 p-1.5 rounded border bg-red-50 border-red-200 text-[11px] text-red-700">
                                            <Icon className="h-3 w-3 shrink-0" />
                                            <span className="flex-1">{CHECK_LABELS[c.code] || c.code}</span>
                                            {canLink && (
                                                <Button size="sm" variant="ghost" className="h-5 px-1 text-[9px] text-red-600 hover:text-red-800"
                                                    onClick={() => { setLinkOpen(c.code); setLinkIds(''); }}
                                                    data-testid={`btn-link-${c.code}`}>
                                                    <Link2 className="h-2.5 w-2.5 mr-0.5" /> collega
                                                </Button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Blockers detail */}
                        {gate.blockers?.length > 0 && (
                            <div className="p-2.5 rounded border border-red-200 bg-red-50/50 space-y-1" data-testid="blockers-detail">
                                <h4 className="text-[10px] font-semibold text-red-600 uppercase tracking-wider flex items-center gap-1">
                                    <Lock className="h-3 w-3" /> Blocchi attivi ({gate.blockers.length})
                                </h4>
                                {gate.blockers.map((b, i) => (
                                    <div key={i} className="flex items-start gap-1.5 text-[11px] text-red-700">
                                        <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                                        <div>
                                            <span className="font-mono text-[9px] bg-red-100 px-1 py-0.5 rounded mr-1">{b.code}</span>
                                            {b.message}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Warnings detail */}
                        {gate.warnings?.length > 0 && (
                            <div className="p-2.5 rounded border border-amber-200 bg-amber-50/50 space-y-1" data-testid="warnings-detail">
                                <h4 className="text-[10px] font-semibold text-amber-600 uppercase tracking-wider flex items-center gap-1">
                                    <AlertTriangle className="h-3 w-3" /> Avvisi ({gate.warnings.length})
                                </h4>
                                {gate.warnings.map((w, i) => (
                                    <div key={i} className="flex items-start gap-1.5 text-[11px] text-amber-700">
                                        <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                                        {w.message}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Scope summary */}
                        <div className="flex flex-wrap gap-2 pt-1 border-t text-[10px] text-slate-500">
                            {emissione.batch_ids?.length > 0 && <span>{emissione.batch_ids.length} lotti</span>}
                            {emissione.ddt_ids?.length > 0 && <span>{emissione.ddt_ids.length} DDT</span>}
                            {emissione.line_ids?.length > 0 && <span>{emissione.line_ids.length} righe</span>}
                            {emissione.voce_lavoro_ids?.length > 0 && <span>{emissione.voce_lavoro_ids.length} voci</span>}
                            {emissione.document_ids?.length > 0 && <span>{emissione.document_ids.length} documenti</span>}
                        </div>
                    </>
                )}
            </CardContent>

            {/* Dialog: Collega evidenza */}
            <Dialog open={!!linkOpen} onOpenChange={() => setLinkOpen(null)}>
                <DialogContent className="max-w-sm" data-testid="dialog-link-evidence">
                    <DialogHeader>
                        <DialogTitle className="text-sm">Collega evidenza: {CHECK_LABELS[linkOpen] || linkOpen}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <Input
                            placeholder="ID risorse (separati da virgola)"
                            value={linkIds}
                            onChange={(e) => setLinkIds(e.target.value)}
                            data-testid="input-link-ids"
                        />
                        <p className="text-[11px] text-slate-500">
                            Inserisci gli ID delle risorse da collegare. Es: bat_xxx, ddt_xxx, doc_xxx
                        </p>
                    </div>
                    <DialogFooter>
                        <Button size="sm" variant="outline" onClick={() => setLinkOpen(null)}>Annulla</Button>
                        <Button size="sm" onClick={() => handleLinkEvidence(linkableFields[linkOpen])} disabled={linking} data-testid="btn-conferma-link">
                            {linking ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Link2 className="h-3 w-3 mr-1" />}
                            Collega
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
