import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import {
    FileSearch, Loader2, Plus, ArrowLeft, CheckCircle2, XCircle, AlertTriangle,
    Shield, Brain, Send, ChevronRight, ChevronDown, ChevronUp, FileText,
    AlertCircle, Crosshair, HelpCircle, Sparkles,
} from 'lucide-react';

const SEVERITY_COLORS = { alta: 'bg-red-100 text-red-800', media: 'bg-amber-100 text-amber-800', bassa: 'bg-blue-100 text-blue-700' };
const BLOCKING_COLORS = { hard_block: 'bg-red-100 text-red-800', warning: 'bg-amber-100 text-amber-800', none: 'bg-gray-100 text-gray-600' };
const CATEGORY_LABELS = { contrattuale: 'Contrattuale', tecnico: 'Tecnico', documentale: 'Documentale', sicurezza: 'Sicurezza', logistico_temporale: 'Logistico' };
const STATUS_LABELS = { uploaded: 'Caricato', analyzed: 'Analizzato', analysis_ready: 'Pronto', in_review: 'In revisione', approved: 'Approvato', archived: 'Archiviato' };
const STATUS_COLORS = { uploaded: 'bg-gray-100 text-gray-600', analyzed: 'bg-blue-100 text-blue-700', analysis_ready: 'bg-blue-100 text-blue-700', in_review: 'bg-amber-100 text-amber-800', approved: 'bg-emerald-100 text-emerald-800' };

// ─── Package List ───
function PackageList({ packages, onSelect, onNew }) {
    if (!packages.length) return (
        <div className="text-center py-12 space-y-3">
            <FileSearch className="h-10 w-10 mx-auto text-slate-300" />
            <p className="text-sm text-slate-400">Nessuna verifica committenza avviata.</p>
            <Button onClick={onNew} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-new-package-empty">
                <Plus className="h-4 w-4 mr-2" /> Nuova Verifica
            </Button>
        </div>
    );
    return (
        <div className="space-y-2" data-testid="packages-list">
            {packages.map(pkg => {
                const sc = STATUS_COLORS[pkg.status] || STATUS_COLORS.uploaded;
                return (
                    <div key={pkg.package_id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 bg-white hover:border-blue-200 cursor-pointer transition-colors" onClick={() => onSelect(pkg)} data-testid={`pkg-${pkg.package_id}`}>
                        <FileSearch className="h-4 w-4 text-[#0055FF] flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{pkg.title}</p>
                            <p className="text-xs text-slate-400">{pkg.document_refs?.length || 0} documenti - {pkg.commessa_id}</p>
                        </div>
                        <Badge className={`text-[10px] ${sc}`}>{STATUS_LABELS[pkg.status] || pkg.status}</Badge>
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                    </div>
                );
            })}
        </div>
    );
}

// ─── Obligation Item ───
function ObligationItem({ obl, onToggle }) {
    const confirmed = obl.confirmed;
    return (
        <div className={`p-3 rounded-lg border transition-colors ${confirmed ? 'border-emerald-200 bg-emerald-50/30' : 'border-gray-200 bg-white'}`} data-testid={`obl-${obl.code}`}>
            <div className="flex items-start gap-2">
                <button onClick={() => onToggle(obl.code)} className="mt-0.5 flex-shrink-0" data-testid={`toggle-${obl.code}`}>
                    {confirmed ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <div className="h-4 w-4 rounded-full border-2 border-gray-300" />}
                </button>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{obl.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{obl.description}</p>
                    {obl.source_excerpt && <p className="text-xs text-slate-400 mt-1 italic border-l-2 border-slate-200 pl-2">"{obl.source_excerpt}"</p>}
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                        <Badge className={`text-[10px] ${SEVERITY_COLORS[obl.severity] || ''}`}>{obl.severity}</Badge>
                        <Badge className={`text-[10px] ${BLOCKING_COLORS[obl.blocking_level] || ''}`}>{obl.blocking_level === 'hard_block' ? 'bloccante' : obl.blocking_level}</Badge>
                        <Badge className="text-[10px] bg-violet-50 text-violet-700">{CATEGORY_LABELS[obl.category] || obl.category}</Badge>
                        <span className="text-[10px] text-slate-400">conf. {Math.round((obl.confidence || 0) * 100)}%</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─── Anomaly Item ───
function AnomalyItem({ anom, onToggle }) {
    return (
        <div className={`p-3 rounded-lg border transition-colors ${anom.confirmed ? 'border-amber-200 bg-amber-50/30' : 'border-gray-200 bg-white'}`} data-testid={`anom-${anom.code}`}>
            <div className="flex items-start gap-2">
                <button onClick={() => onToggle(anom.code)} className="mt-0.5 flex-shrink-0" data-testid={`toggle-anom-${anom.code}`}>
                    {anom.confirmed ? <AlertTriangle className="h-4 w-4 text-amber-600" /> : <div className="h-4 w-4 rounded-full border-2 border-gray-300" />}
                </button>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-amber-900">{anom.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{anom.description}</p>
                    {anom.source_excerpt && <p className="text-xs text-slate-400 mt-1 italic border-l-2 border-amber-200 pl-2">"{anom.source_excerpt}"</p>}
                    <div className="flex gap-1.5 mt-1.5">
                        <Badge className={`text-[10px] ${SEVERITY_COLORS[anom.severity] || ''}`}>{anom.severity}</Badge>
                        <Badge className="text-[10px] bg-slate-100 text-slate-600">{anom.recommended_action}</Badge>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─── Mismatch Item ───
function MismatchItem({ mm, onToggle }) {
    return (
        <div className={`p-3 rounded-lg border transition-colors ${mm.confirmed ? 'border-red-200 bg-red-50/30' : 'border-gray-200 bg-white'}`} data-testid={`mm-${mm.code}`}>
            <div className="flex items-start gap-2">
                <button onClick={() => onToggle(mm.code)} className="mt-0.5 flex-shrink-0" data-testid={`toggle-mm-${mm.code}`}>
                    {mm.confirmed ? <Crosshair className="h-4 w-4 text-red-600" /> : <div className="h-4 w-4 rounded-full border-2 border-gray-300" />}
                </button>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-red-900">{mm.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{mm.description}</p>
                    <div className="flex gap-1.5 mt-1.5">
                        <Badge className={`text-[10px] ${SEVERITY_COLORS[mm.severity] || ''}`}>{mm.severity}</Badge>
                        <Badge className="text-[10px] bg-slate-100 text-slate-600">{mm.recommended_action}</Badge>
                        {mm.compared_against?.map(c => <Badge key={c} className="text-[10px] bg-blue-50 text-blue-700">vs {c}</Badge>)}
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─── Analysis Detail View ───
function AnalysisDetailView({ analysis: initialAnalysis, onBack, onRefresh }) {
    const [analysis, setAnalysis] = useState(initialAnalysis);
    const [reviewing, setReviewing] = useState(false);
    const [approving, setApproving] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [expandedSections, setExpandedSections] = useState({ obblighi: true, anomalie: true, mismatch: true, domande: true });

    const toggleSection = (s) => setExpandedSections(p => ({ ...p, [s]: !p[s] }));

    const toggleObligation = (code) => {
        setAnalysis(prev => ({
            ...prev,
            extracted_obligations: prev.extracted_obligations.map(o =>
                o.code === code ? { ...o, confirmed: !o.confirmed } : o
            ),
        }));
    };
    const toggleAnomaly = (code) => {
        setAnalysis(prev => ({
            ...prev,
            anomalies: prev.anomalies.map(a => a.code === code ? { ...a, confirmed: !a.confirmed } : a),
        }));
    };
    const toggleMismatch = (code) => {
        setAnalysis(prev => ({
            ...prev,
            mismatches: prev.mismatches.map(m => m.code === code ? { ...m, confirmed: !m.confirmed } : m),
        }));
    };
    const setAnswer = (qid, answer) => {
        setAnalysis(prev => ({
            ...prev,
            open_questions: prev.open_questions.map(q => q.qid === qid ? { ...q, answer } : q),
        }));
    };

    const handleReview = async () => {
        setReviewing(true);
        try {
            const reviewData = {
                obligations_review: analysis.extracted_obligations.map(o => ({ code: o.code, confirmed: o.confirmed || false, note: o.review_note || '' })),
                anomalies_review: analysis.anomalies.map(a => ({ code: a.code, confirmed: a.confirmed || false, note: a.review_note || '' })),
                mismatches_review: analysis.mismatches.map(m => ({ code: m.code, confirmed: m.confirmed || false, note: m.review_note || '' })),
                questions_answers: analysis.open_questions.map(q => ({ qid: q.qid, answer: q.answer || '' })),
            };
            const result = await apiRequest(`/committenza/analisi/${analysis.analysis_id}/review`, {
                method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reviewData),
            });
            setAnalysis(result);
            toast.success('Review salvata');
        } catch (err) { toast.error(err.message); }
        finally { setReviewing(false); }
    };

    const handleApprove = async () => {
        setApproving(true);
        try {
            const result = await apiRequest(`/committenza/analisi/${analysis.analysis_id}/approve`, { method: 'POST' });
            setAnalysis(result);
            toast.success('Analisi approvata');
        } catch (err) { toast.error(err.message); }
        finally { setApproving(false); }
    };

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const result = await apiRequest(`/committenza/analisi/${analysis.analysis_id}/genera-obblighi`, { method: 'POST' });
            toast.success(`Obblighi generati: ${result.created} nuovi, ${result.updated} aggiornati`);
        } catch (err) { toast.error(err.message); }
        finally { setGenerating(false); }
    };

    const s = analysis.summary || {};
    const isApproved = analysis.status === 'approved';
    const confirmedObls = (analysis.extracted_obligations || []).filter(o => o.confirmed).length;
    const totalObls = (analysis.extracted_obligations || []).length;

    return (
        <div className="space-y-4" data-testid="analysis-detail">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={onBack} data-testid="btn-back"><ArrowLeft className="h-4 w-4 mr-1" /> Indietro</Button>
                <div className="flex-1">
                    <h2 className="text-lg font-bold text-slate-900">Risultato Analisi</h2>
                    <p className="text-xs text-slate-400">{analysis.analysis_id} - Confidenza: {Math.round((analysis.overall_confidence || 0) * 100)}%</p>
                </div>
                <Badge className={`${STATUS_COLORS[analysis.status] || ''}`}>{STATUS_LABELS[analysis.status] || analysis.status}</Badge>
            </div>

            {/* Summary */}
            <Card className="border-blue-200">
                <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Brain className="h-4 w-4 text-[#0055FF]" /> Sintesi AI</CardTitle></CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        {[['Contratto', s.contract_present], ['Specifiche tecniche', s.technical_specs_present], ['Documenti sicurezza', s.safety_docs_present], ['Richieste documentali', s.document_request_present]].map(([label, val]) => (
                            <div key={label} className="flex items-center gap-2 text-sm">
                                {val ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-slate-300" />}
                                <span className={val ? 'text-slate-900' : 'text-slate-400'}>{label}</span>
                            </div>
                        ))}
                        {s.overall_risk_level && (
                            <div className="flex items-center gap-2">
                                <Shield className={`h-4 w-4 ${s.overall_risk_level === 'alto' ? 'text-red-500' : s.overall_risk_level === 'medio' ? 'text-amber-500' : 'text-emerald-500'}`} />
                                <span className="text-sm">Rischio: <strong>{s.overall_risk_level}</strong></span>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Obligations */}
            <Card>
                <CardHeader className="pb-2 cursor-pointer" onClick={() => toggleSection('obblighi')}>
                    <CardTitle className="text-sm flex items-center gap-2">
                        <Shield className="h-4 w-4" /> Obblighi estratti ({totalObls})
                        <Badge className="text-[10px] bg-emerald-100 text-emerald-800">{confirmedObls} confermati</Badge>
                        {expandedSections.obblighi ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
                    </CardTitle>
                </CardHeader>
                {expandedSections.obblighi && (
                    <CardContent className="space-y-2">{(analysis.extracted_obligations || []).map(o => <ObligationItem key={o.code} obl={o} onToggle={toggleObligation} />)}</CardContent>
                )}
            </Card>

            {/* Anomalies */}
            {(analysis.anomalies || []).length > 0 && (
                <Card className="border-amber-200">
                    <CardHeader className="pb-2 cursor-pointer" onClick={() => toggleSection('anomalie')}>
                        <CardTitle className="text-sm flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-amber-600" /> Anomalie ({analysis.anomalies.length})
                            {expandedSections.anomalie ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
                        </CardTitle>
                    </CardHeader>
                    {expandedSections.anomalie && (
                        <CardContent className="space-y-2">{analysis.anomalies.map(a => <AnomalyItem key={a.code} anom={a} onToggle={toggleAnomaly} />)}</CardContent>
                    )}
                </Card>
            )}

            {/* Mismatches */}
            {(analysis.mismatches || []).length > 0 && (
                <Card className="border-red-200">
                    <CardHeader className="pb-2 cursor-pointer" onClick={() => toggleSection('mismatch')}>
                        <CardTitle className="text-sm flex items-center gap-2">
                            <Crosshair className="h-4 w-4 text-red-600" /> Mismatch col preventivo ({analysis.mismatches.length})
                            {expandedSections.mismatch ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
                        </CardTitle>
                    </CardHeader>
                    {expandedSections.mismatch && (
                        <CardContent className="space-y-2">{analysis.mismatches.map(m => <MismatchItem key={m.code} mm={m} onToggle={toggleMismatch} />)}</CardContent>
                    )}
                </Card>
            )}

            {/* Open Questions */}
            {(analysis.open_questions || []).length > 0 && (
                <Card>
                    <CardHeader className="pb-2 cursor-pointer" onClick={() => toggleSection('domande')}>
                        <CardTitle className="text-sm flex items-center gap-2">
                            <HelpCircle className="h-4 w-4" /> Domande residue ({analysis.open_questions.length})
                            {expandedSections.domande ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
                        </CardTitle>
                    </CardHeader>
                    {expandedSections.domande && (
                        <CardContent className="space-y-3">
                            {analysis.open_questions.map(q => (
                                <div key={q.qid} className="space-y-1" data-testid={`question-${q.qid}`}>
                                    <p className="text-sm font-medium">{q.question}</p>
                                    <div className="flex gap-1.5">
                                        <Badge className={`text-[10px] ${q.impact === 'alto' ? 'bg-red-100 text-red-800' : q.impact === 'medio' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-700'}`}>impatto {q.impact}</Badge>
                                    </div>
                                    <Textarea rows={2} placeholder="Risposta..." value={q.answer || ''} onChange={e => setAnswer(q.qid, e.target.value)} className="text-sm" data-testid={`answer-${q.qid}`} />
                                </div>
                            ))}
                        </CardContent>
                    )}
                </Card>
            )}

            {/* Action buttons */}
            <Separator />
            <div className="flex items-center gap-3 justify-end">
                {!isApproved && (
                    <>
                        <Button variant="outline" onClick={handleReview} disabled={reviewing} data-testid="btn-save-review">
                            {reviewing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                            Salva Revisione
                        </Button>
                        <Button onClick={handleApprove} disabled={approving} className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-approve">
                            {approving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                            Approva Analisi
                        </Button>
                    </>
                )}
                {isApproved && (
                    <Button onClick={handleGenerate} disabled={generating} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-genera-obblighi">
                        {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                        Genera Obblighi nel Registro
                    </Button>
                )}
            </div>
        </div>
    );
}

// ─── Package Detail (select docs + launch analysis) ───
function PackageDetailView({ pkg: initialPkg, archiveDocs, docCategories, onAnalysisReady, onBack }) {
    const [pkg, setPkg] = useState(initialPkg);
    const [addingDoc, setAddingDoc] = useState(false);
    const [selectedDocId, setSelectedDocId] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('altro');
    const [analyzing, setAnalyzing] = useState(false);

    const handleAddDoc = async () => {
        if (!selectedDocId) { toast.error('Seleziona un documento'); return; }
        setAddingDoc(true);
        try {
            const result = await apiRequest(`/committenza/packages/${pkg.package_id}/documents`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doc_id: selectedDocId, category: selectedCategory }),
            });
            setPkg(result);
            setSelectedDocId('');
            toast.success('Documento aggiunto');
        } catch (err) { toast.error(err.message); }
        finally { setAddingDoc(false); }
    };

    const handleRemoveDoc = async (docId) => {
        try {
            const result = await apiRequest(`/committenza/packages/${pkg.package_id}/documents/${docId}`, { method: 'DELETE' });
            setPkg(result);
            toast.success('Documento rimosso');
        } catch (err) { toast.error(err.message); }
    };

    const handleAnalyze = async () => {
        if (!pkg.document_refs?.length) { toast.error('Aggiungi almeno un documento'); return; }
        setAnalyzing(true);
        try {
            const result = await apiRequest(`/committenza/analizza/${pkg.package_id}`, { method: 'POST' });
            if (result.error) { toast.error(result.error); return; }
            toast.success('Analisi completata');
            onAnalysisReady(result);
        } catch (err) { toast.error(err.message); }
        finally { setAnalyzing(false); }
    };

    const availableDocs = archiveDocs.filter(d => !(pkg.document_refs || []).some(r => r.doc_id === d.doc_id));

    return (
        <div className="space-y-4" data-testid="package-detail">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={onBack} data-testid="btn-back-pkg"><ArrowLeft className="h-4 w-4 mr-1" /> Indietro</Button>
                <div className="flex-1">
                    <h2 className="text-lg font-bold text-slate-900">{pkg.title}</h2>
                    <p className="text-xs text-slate-400">{pkg.package_id} - {pkg.document_refs?.length || 0} documenti</p>
                </div>
                <Badge className={`${STATUS_COLORS[pkg.status] || ''}`}>{STATUS_LABELS[pkg.status] || pkg.status}</Badge>
            </div>

            {/* Documents in package */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2"><FileText className="h-4 w-4" /> Documenti selezionati</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                    {(pkg.document_refs || []).map(ref => (
                        <div key={ref.doc_id} className="flex items-center gap-2 p-2 rounded bg-slate-50 text-sm" data-testid={`ref-${ref.doc_id}`}>
                            <FileText className="h-3.5 w-3.5 text-slate-400" />
                            <span className="flex-1 truncate">{ref.title || ref.file_name}</span>
                            <Badge className="text-[10px] bg-violet-50 text-violet-700">{ref.category}</Badge>
                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={() => handleRemoveDoc(ref.doc_id)} data-testid={`remove-${ref.doc_id}`}>
                                <XCircle className="h-3.5 w-3.5" />
                            </Button>
                        </div>
                    ))}
                    {!pkg.document_refs?.length && <p className="text-xs text-slate-400 py-2">Nessun documento. Aggiungi dal repository.</p>}
                </CardContent>
            </Card>

            {/* Add document from archive */}
            <Card className="border-dashed border-2 border-blue-200">
                <CardContent className="p-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 items-end">
                        <div>
                            <Label className="text-xs">Documento dall'archivio</Label>
                            <Select value={selectedDocId} onValueChange={setSelectedDocId}>
                                <SelectTrigger data-testid="select-archive-doc"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                <SelectContent>
                                    {availableDocs.map(d => <SelectItem key={d.doc_id} value={d.doc_id}>{d.title || d.file_name || d.doc_id}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs">Categoria</Label>
                            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                                <SelectTrigger data-testid="select-doc-category"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {docCategories.map(c => <SelectItem key={c.code} value={c.code}>{c.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <Button onClick={handleAddDoc} disabled={addingDoc} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-add-doc">
                            {addingDoc ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />} Aggiungi
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Launch analysis */}
            <div className="flex justify-end">
                <Button onClick={handleAnalyze} disabled={analyzing || !pkg.document_refs?.length} className="bg-violet-600 text-white hover:bg-violet-700" data-testid="btn-analyze">
                    {analyzing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Brain className="h-4 w-4 mr-2" />}
                    Analizza Documenti
                </Button>
            </div>
        </div>
    );
}

// ─── Main Page Component ───
export default function VerificaCommittenzaPage({ commessaId }) {
    const [packages, setPackages] = useState([]);
    const [analyses, setAnalyses] = useState([]);
    const [archiveDocs, setArchiveDocs] = useState([]);
    const [docCategories, setDocCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState('list'); // list | package | analysis
    const [selectedPkg, setSelectedPkg] = useState(null);
    const [selectedAnalysis, setSelectedAnalysis] = useState(null);
    const [creating, setCreating] = useState(false);
    const [newTitle, setNewTitle] = useState('');

    const loadData = useCallback(async () => {
        try {
            const qParam = commessaId ? `?commessa_id=${commessaId}` : '';
            const [pkgs, anls, docs, cats] = await Promise.all([
                apiRequest(`/committenza/packages${qParam}`),
                apiRequest(`/committenza/analisi${qParam}`),
                apiRequest('/documenti'),
                apiRequest('/committenza/categorie'),
            ]);
            setPackages(pkgs);
            setAnalyses(anls);
            setArchiveDocs(docs);
            setDocCategories(cats);
        } catch (err) { toast.error('Errore caricamento dati'); }
        finally { setLoading(false); }
    }, [commessaId]);

    useEffect(() => { loadData(); }, [loadData]);

    const handleNew = async () => {
        if (!commessaId) { toast.error('Commessa non specificata'); return; }
        setCreating(true);
        try {
            const pkg = await apiRequest('/committenza/packages', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ commessa_id: commessaId, title: newTitle || '' }),
            });
            setPackages(p => [pkg, ...p]);
            setSelectedPkg(pkg);
            setView('package');
            setNewTitle('');
            toast.success('Package creato');
        } catch (err) { toast.error(err.message); }
        finally { setCreating(false); }
    };

    const handleAnalysisReady = (analysis) => {
        setSelectedAnalysis(analysis);
        setAnalyses(p => [analysis, ...p]);
        setView('analysis');
    };

    const handleSelectPkg = async (pkg) => {
        if (pkg.analysis_id) {
            // Has analysis — go to analysis view
            try {
                const analysis = await apiRequest(`/committenza/analisi/${pkg.analysis_id}`);
                setSelectedAnalysis(analysis);
                setView('analysis');
            } catch (err) {
                // No analysis found, go to package view
                setSelectedPkg(pkg);
                setView('package');
            }
        } else {
            setSelectedPkg(pkg);
            setView('package');
        }
    };

    if (loading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-[#0055FF]" /></div>;

    return (
        <div className="space-y-4" data-testid="verifica-committenza-section">
            {view === 'list' && (
                <>
                    <div className="flex items-center justify-between">
                        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                            <FileSearch className="h-4 w-4 text-[#0055FF]" /> Verifica Committenza
                        </h3>
                        <div className="flex items-center gap-2">
                            <Input placeholder="Titolo verifica..." value={newTitle} onChange={e => setNewTitle(e.target.value)} className="w-48 h-8 text-sm" data-testid="input-new-title" />
                            <Button size="sm" onClick={handleNew} disabled={creating} className="bg-[#0055FF] text-white hover:bg-[#0044CC]" data-testid="btn-new-package">
                                {creating ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Plus className="h-3 w-3 mr-1" />} Nuova
                            </Button>
                        </div>
                    </div>
                    <PackageList packages={packages} onSelect={handleSelectPkg} onNew={handleNew} />

                    {/* Show analyses that are approved */}
                    {analyses.filter(a => a.status === 'approved').length > 0 && (
                        <div className="mt-4">
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Analisi approvate</p>
                            {analyses.filter(a => a.status === 'approved').map(a => (
                                <div key={a.analysis_id} className="flex items-center gap-3 p-2 rounded border border-emerald-200 bg-emerald-50/30 cursor-pointer hover:bg-emerald-50 mb-1"
                                    onClick={() => { setSelectedAnalysis(a); setView('analysis'); }}
                                    data-testid={`approved-${a.analysis_id}`}>
                                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                    <span className="text-sm flex-1">{a.analysis_id}</span>
                                    <span className="text-xs text-slate-400">{a.extracted_obligations?.length || 0} obblighi</span>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
            {view === 'package' && selectedPkg && (
                <PackageDetailView
                    pkg={selectedPkg}
                    archiveDocs={archiveDocs}
                    docCategories={docCategories}
                    onAnalysisReady={handleAnalysisReady}
                    onBack={() => { setView('list'); loadData(); }}
                />
            )}
            {view === 'analysis' && selectedAnalysis && (
                <AnalysisDetailView
                    analysis={selectedAnalysis}
                    onBack={() => { setView('list'); loadData(); }}
                    onRefresh={loadData}
                />
            )}
        </div>
    );
}
