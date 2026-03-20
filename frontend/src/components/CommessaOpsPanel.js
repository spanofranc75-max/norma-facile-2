/**
 * CommessaOpsPanel — Orchestrator for all operational panels of a commessa.
 * Delegates to autonomous sub-components:
 *   ApprovvigionamentoSection, ProduzioneSection, ConsegneSection,
 *   ContoLavoroSection, TracciabilitaSection, CAMSection,
 *   RepositoryDocumentiSection, FascicoloTecnicoSection, GateCertificationPanel
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    ShoppingCart, Factory, Truck, Paintbrush, FileUp,
    ChevronDown, ChevronUp, FileText, Leaf, Shield,
} from 'lucide-react';

// Sub-components
import ApprovvigionamentoSection from './ApprovvigionamentoSection';
import ProduzioneSection from './ProduzioneSection';
import ConsegneSection from './ConsegneSection';
import ContoLavoroSection from './ContoLavoroSection';
import TracciabilitaSection from './TracciabilitaSection';
import CAMSection from './CAMSection';
import RepositoryDocumentiSection from './RepositoryDocumentiSection';
import FascicoloTecnicoSection from './FascicoloTecnicoSection';
import GateCertificationPanel from './GateCertificationPanel';

// ── Collapsible Section wrapper ──
function Section({ title, icon: Icon, count, defaultOpen, children }) {
    const [open, setOpen] = useState(defaultOpen || false);
    return (
        <Card className="border-gray-200">
            <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors rounded-t-lg" data-testid={`section-${title.toLowerCase().replace(/\s/g, '-')}`}>
                <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-[#0055FF]" />
                    <span className="text-sm font-semibold text-[#1E293B]">{title}</span>
                    {count > 0 && <Badge className="bg-[#0055FF]/10 text-[#0055FF] text-[9px]">{count}</Badge>}
                </div>
                {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
            </button>
            {open && <CardContent className="pt-0 pb-3 px-4">{children}</CardContent>}
        </Card>
    );
}

export default function CommessaOpsPanel({ commessaId, commessaNumero, normativaTipo, vociLavoro = [], onRefresh }) {
    const [ops, setOps] = useState(null);
    const [docs, setDocs] = useState([]);
    const [materialBatches, setMaterialBatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [fornitori, setFornitori] = useState([]);
    const [camLotti, setCamLotti] = useState([]);
    const [camCalcolo, setCamCalcolo] = useState(null);

    // Calcola le categorie effettive (unione della commessa + voci)
    const allCategorie = new Set([normativaTipo]);
    vociLavoro.forEach(v => { if (v.normativa_tipo) allCategorie.add(v.normativa_tipo); });
    const hasEN1090 = allCategorie.has('EN_1090');
    const hasEN13241 = allCategorie.has('EN_13241');
    const isOnlyGenerica = allCategorie.size === 1 && allCategorie.has('GENERICA');

    // Load fornitori from anagrafica
    useEffect(() => {
        apiRequest('/clients/?client_type=fornitore&limit=100').then(data => {
            setFornitori((data.clients || []).map(c => ({ id: c.client_id, nome: c.business_name })));
        }).catch(() => {});
    }, []);

    // Main data fetch
    const fetchData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const [o, d, batches] = await Promise.all([
                apiRequest(`/commesse/${commessaId}/ops`),
                apiRequest(`/commesse/${commessaId}/documenti`),
                apiRequest(`/fpc/batches?commessa_id=${commessaId}`).catch(() => ({ batches: [] })),
            ]);
            setOps(o);
            setDocs(d.documents || []);
            setMaterialBatches(batches.batches || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [commessaId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // CAM data fetch
    const fetchCamData = useCallback(async () => {
        if (!commessaId) return;
        try {
            const [lottiRes, calcoloRes] = await Promise.all([
                apiRequest(`/cam/lotti?commessa_id=${commessaId}`).catch(() => ({ lotti: [] })),
                apiRequest(`/cam/calcolo/${commessaId}`).catch(() => null),
            ]);
            setCamLotti(lottiRes.lotti || []);
            setCamCalcolo(calcoloRes);
        } catch (e) { console.error('CAM fetch error', e); }
    }, [commessaId]);

    useEffect(() => { fetchCamData(); }, [fetchCamData]);

    if (loading) return <div className="text-center py-6 text-sm text-slate-400">Caricamento dati operativi...</div>;

    // Derived data
    const approv = ops?.approvvigionamento || { richieste: [], ordini: [], arrivi: [] };
    const fasi = ops?.fasi_produzione || [];
    const progPct = ops?.produzione_progress?.percentage || 0;
    const cl = ops?.conto_lavoro || [];
    const consegne = ops?.consegne || [];

    // Unified refresh callback
    const handleRefresh = () => { fetchData(); onRefresh?.(); };
    const handleRefreshWithCam = () => { fetchData(); fetchCamData(); onRefresh?.(); };

    return (
        <div className="space-y-3" data-testid="commessa-ops">
            {/* ── APPROVVIGIONAMENTO — visibile se c'è almeno una categoria non-GENERICA ── */}
            {!isOnlyGenerica && (
                <Section title="Approvvigionamento" icon={ShoppingCart} count={(approv.richieste?.length || 0) + (approv.ordini?.length || 0)} defaultOpen>
                    <ApprovvigionamentoSection commessaId={commessaId} commessaNumero={commessaNumero} approv={approv} fornitori={fornitori} onRefresh={handleRefresh} />
                </Section>
            )}

            {/* ── PRODUZIONE — sempre visibile ── */}
            <Section title="Produzione" icon={Factory} count={fasi.length} defaultOpen={isOnlyGenerica}>
                <ProduzioneSection commessaId={commessaId} commessaNumero={commessaNumero} fasi={fasi} progPct={progPct} normativaTipo={normativaTipo} vociLavoro={vociLavoro} onRefresh={handleRefresh} />
            </Section>

            {/* ── CONSEGNE — visibile se c'è almeno una categoria non-GENERICA ── */}
            {!isOnlyGenerica && (
                <Section title="Consegne al Cliente" icon={Truck} count={consegne.length}>
                    <ConsegneSection commessaId={commessaId} commessaNumero={commessaNumero} consegne={consegne} onRefresh={handleRefresh} />
                </Section>
            )}

            {/* ── CONTO LAVORO — visibile per tutti (verniciatura/zincatura serve sempre) ── */}
            <Section title="Conto Lavoro" icon={Paintbrush} count={cl.length}>
                <ContoLavoroSection commessaId={commessaId} commessaNumero={commessaNumero} cl={cl} fornitori={fornitori} onRefresh={handleRefresh} />
            </Section>

            {/* ── TRACCIABILITÀ MATERIALI — se almeno una voce è EN 1090 ── */}
            {hasEN1090 && (
                <Section title="Tracciabilità Materiali" icon={FileText} count={materialBatches.length + docs.filter(d => d.metadata_estratti?.numero_colata).length}>
                    <TracciabilitaSection commessaId={commessaId} materialBatches={materialBatches} docs={docs} onRefresh={handleRefresh} />
                </Section>
            )}

            {/* ── CAM — se almeno una voce è EN 1090 ── */}
            {hasEN1090 && (
                <Section title="CAM - Criteri Ambientali Minimi" icon={Leaf} count={camLotti.length}>
                    <CAMSection commessaId={commessaId} commessaNumero={commessaNumero} camLotti={camLotti} camCalcolo={camCalcolo} docs={docs} onRefreshCam={handleRefreshWithCam} />
                </Section>
            )}

            {/* ── FASCICOLO TECNICO — se almeno una voce è EN 1090 ── */}
            {hasEN1090 && (
                <Section title="Fascicolo Tecnico EN 1090" icon={FileText} count={6}>
                    <FascicoloTecnicoSection commessaId={commessaId} />
                </Section>
            )}

            {/* ── CERTIFICAZIONE CANCELLI — se almeno una voce è EN 13241 ── */}
            {hasEN13241 && (
                <Section title="Certificazione Cancello EN 13241" icon={Shield} count={0}>
                    <GateCertificationPanel commessaId={commessaId} commessa={{ numero: commessaNumero }} />
                </Section>
            )}

            {/* ── REPOSITORY DOCUMENTI — sempre visibile ── */}
            <Section title="Repository Documenti" icon={FileUp} count={docs.length} defaultOpen>
                <RepositoryDocumentiSection commessaId={commessaId} docs={docs} onRefresh={handleRefreshWithCam} onCamRefresh={fetchCamData} />
            </Section>
        </div>
    );
}
