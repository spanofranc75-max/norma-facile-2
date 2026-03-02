/**
 * Preventivo Editor — Invoicex-style Smart Quote.
 * Features: Quick Fill from client, dual discounts, acconto, sidebar tabs.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Plus, Trash2, Save, ArrowLeft, FileDown, CheckCircle2, XCircle,
    Thermometer, ShieldCheck, Settings2, ArrowRightLeft, Euro,
    CreditCard, MapPin, FileText, StickyNote, Mail, Shield, Receipt,
    Briefcase, Loader2, AlertTriangle, ArrowRight, Wrench, DoorOpen,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { PDFPreviewButton } from '../components/PDFPreviewModal';
import { AutoExpandTextarea } from '../components/AutoExpandTextarea';
import InvoiceGenerationModal from '../components/InvoiceGenerationModal';
import EmailPreviewDialog from '../components/EmailPreviewDialog';
import { DisabledTooltip } from '../components/DisabledTooltip';

const ZONES = ['A', 'B', 'C', 'D', 'E', 'F'];
const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const emptyLine = () => ({
    line_id: `ln_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    description: '', codice_articolo: '', dimensions: '', quantity: 1, unit: 'pz',
    unit_price: 0, sconto_1: 0, sconto_2: 0, vat_rate: '22', thermal_data: null, notes: '',
});

const SIDEBAR_TABS = [
    { key: 'riferimento', label: 'Riferimento', icon: FileText },
    { key: 'pagamento', label: 'Pagamento', icon: CreditCard },
    { key: 'destinazione', label: 'Destinazione', icon: MapPin },
    { key: 'note_extra', label: 'Note', icon: StickyNote },
];

export default function PreventivoEditorPage() {
    const navigate = useNavigate();
    const { prevId } = useParams();
    const isNew = !prevId || prevId === 'new';

    const [form, setForm] = useState({
        client_id: '', subject: '', validity_days: 30, notes: '', lines: [emptyLine()],
        payment_type_id: '', payment_type_label: '', destinazione_merce: '',
        iban: '', banca: '', note_pagamento: '', riferimento: '',
        acconto: 0, sconto_globale: 0, normativa: '',
        numero_disegno: '', ingegnere_disegno: '', classe_esecuzione: '', giorni_consegna: '',
    });
    const [clients, setClients] = useState([]);
    const [paymentTypes, setPaymentTypes] = useState([]);
    const [thermalRef, setThermalRef] = useState({ glass_types: [], frame_types: [], spacer_types: [] });
    const [compliance, setCompliance] = useState(null);
    const [saving, setSaving] = useState(false);
    const [checking, setChecking] = useState(false);
    const [converting, setConverting] = useState(false);
    const [showFpcDialog, setShowFpcDialog] = useState(false);
    const [excClass, setExcClass] = useState('EXC2');
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [activeLineIdx, setActiveLineIdx] = useState(null);
    const [sidebarTab, setSidebarTab] = useState('riferimento');
    const [showInvoiceModal, setShowInvoiceModal] = useState(false);
    const [linkedCommessa, setLinkedCommessa] = useState(null);
    const [emailPreviewOpen, setEmailPreviewOpen] = useState(false);
    const [creatingCommessa, setCreatingCommessa] = useState(false);
    const [workflow, setWorkflow] = useState({ status: 'bozza', number: null, created_at: null, converted_to: null, linked_invoice: null, invoicing_progress: 0, linked_invoices: [] });
    const [showSplitDialog, setShowSplitDialog] = useState(false);
    const [splitAnalysis, setSplitAnalysis] = useState(null);
    const [splitGroups, setSplitGroups] = useState({ en_1090: [], en_13241: [], non_classificati: [] });
    const [splittingCommesse, setSplittingCommesse] = useState(false);

    const isAccepted = workflow.status === 'accettato' || workflow.invoicing_progress > 0;

    // ── Auto-save form to sessionStorage ──
    const STORAGE_KEY = `preventivo_draft_${prevId || 'new'}`;
    const isRestoredRef = useRef(false);

    // Restore draft on mount (only once, before API data arrives)
    useEffect(() => {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY);
            if (saved && !isRestoredRef.current) {
                const parsed = JSON.parse(saved);
                if (parsed && parsed.subject !== undefined) {
                    setForm(parsed);
                    isRestoredRef.current = true;
                }
            }
        } catch { /* ignore parse errors */ }
    }, [STORAGE_KEY]);

    // Save draft on every form change (debounced via ref)
    const saveTimerRef = useRef(null);
    useEffect(() => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(() => {
            try {
                sessionStorage.setItem(STORAGE_KEY, JSON.stringify(form));
            } catch { /* storage full, ignore */ }
        }, 300);
        return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); };
    }, [form, STORAGE_KEY]);

    // Clear draft on successful save
    const clearDraft = useCallback(() => {
        try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
    }, [STORAGE_KEY]);

    const handleAcceptPreventivo = async () => {
        if (isNew) return;
        try {
            await apiRequest(`/preventivi/${prevId}`, { method: 'PUT', body: { status: 'accettato' } });
            setWorkflow(w => ({ ...w, status: 'accettato' }));
            toast.success('Preventivo accettato!');
        } catch (e) { toast.error(e.message); }
    };

    useEffect(() => {
        Promise.all([
            apiRequest('/clients/').catch(() => ({ clients: [] })),
            apiRequest('/certificazioni/thermal/reference-data').catch(() => ({})),
            apiRequest('/payment-types/').catch(() => ({ items: [] })),
        ]).then(([cl, th, pt]) => {
            setClients(cl.clients || []);
            setThermalRef(th);
            setPaymentTypes(pt.items || []);
        });
    }, []);

    useEffect(() => {
        if (isNew) return;
        apiRequest(`/preventivi/${prevId}`).then(data => {
            // Always update form from API for existing preventivi
            // Draft only keeps unsaved text edits, API is source of truth
            setForm(f => ({
                client_id: data.client_id || f.client_id || '',
                subject: data.subject || f.subject || '',
                validity_days: data.validity_days || f.validity_days || 30,
                notes: data.notes || f.notes || '',
                lines: data.lines?.length ? data.lines : f.lines?.length > 0 ? f.lines : [emptyLine()],
                payment_type_id: data.payment_type_id || f.payment_type_id || '',
                payment_type_label: data.payment_type_label || f.payment_type_label || '',
                destinazione_merce: data.destinazione_merce || f.destinazione_merce || '',
                iban: data.iban || f.iban || '',
                banca: data.banca || f.banca || '',
                note_pagamento: data.note_pagamento || f.note_pagamento || '',
                riferimento: data.riferimento || f.riferimento || '',
                acconto: data.acconto || f.acconto || 0,
                sconto_globale: data.sconto_globale || f.sconto_globale || 0,
                normativa: data.normativa || f.normativa || '',
                numero_disegno: data.numero_disegno || f.numero_disegno || '',
                ingegnere_disegno: data.ingegnere_disegno || f.ingegnere_disegno || '',
                classe_esecuzione: data.classe_esecuzione || f.classe_esecuzione || '',
                giorni_consegna: data.giorni_consegna || f.giorni_consegna || '',
            }));
            if (data.compliance_detail) setCompliance(data.compliance_detail);
            setWorkflow({
                status: data.status || 'bozza',
                number: data.number,
                created_at: data.created_at,
                converted_to: data.converted_to,
                linked_invoice: data.linked_invoice || null,
                invoicing_progress: data.invoicing_progress || 0,
                linked_invoices: data.linked_invoices || [],
            });
        }).catch(() => toast.error('Preventivo non trovato'));

        // Check if a commessa already exists for this preventivo
        apiRequest('/commesse/').then(data => {
            const linked = (data.items || []).find(c =>
                c.moduli?.preventivo_id === prevId || c.linked_preventivo_id === prevId
            );
            if (linked) setLinkedCommessa(linked);
        }).catch(() => {});
    }, [prevId, isNew]);

    // Quick Fill — auto-populate from client
    const handleClientChange = useCallback((clientId) => {
        setForm(f => ({ ...f, client_id: clientId }));
        if (!clientId) return;
        const client = clients.find(c => c.client_id === clientId);
        if (!client) return;
        setForm(f => ({
            ...f,
            client_id: clientId,
            payment_type_id: f.payment_type_id || client.payment_type_id || '',
            payment_type_label: f.payment_type_label || client.payment_type_label || '',
            iban: f.iban || client.iban || '',
            banca: f.banca || client.banca || '',
            destinazione_merce: f.destinazione_merce || [client.address, client.cap, client.city, client.province].filter(Boolean).join(', ') || '',
        }));
        toast.success(`Dati di ${client.business_name} importati`);
    }, [clients]);

    const updateLine = (idx, field, value) => {
        setForm(f => {
            const lines = [...f.lines];
            lines[idx] = { ...lines[idx], [field]: value };
            return { ...f, lines };
        });
    };
    const addLine = () => setForm(f => ({ ...f, lines: [...f.lines, emptyLine()] }));
    const removeLine = (idx) => setForm(f => ({ ...f, lines: f.lines.filter((_, i) => i !== idx) }));

    const openThermalDrawer = (idx) => {
        setActiveLineIdx(idx);
        if (!form.lines[idx].thermal_data) {
            updateLine(idx, 'thermal_data', {
                glass_id: 'doppio_be_argon', frame_id: 'acciaio_standard', spacer_id: 'alluminio',
                height_mm: 2100, width_mm: 1200, frame_width_mm: 80, zone: 'E',
            });
        }
        setDrawerOpen(true);
    };
    const updateThermal = (field, value) => {
        if (activeLineIdx === null) return;
        setForm(f => {
            const lines = [...f.lines];
            lines[activeLineIdx] = { ...lines[activeLineIdx], thermal_data: { ...lines[activeLineIdx].thermal_data, [field]: value } };
            return { ...f, lines };
        });
    };
    const removeThermal = (idx) => updateLine(idx, 'thermal_data', null);

    // Calculations
    const lineNet = (l) => {
        const p = parseFloat(l.unit_price) || 0;
        const s1 = parseFloat(l.sconto_1) || 0;
        const s2 = parseFloat(l.sconto_2) || 0;
        return p * (1 - s1 / 100) * (1 - s2 / 100);
    };
    const lineTotal = (l) => (parseFloat(l.quantity) || 0) * lineNet(l);
    const subtotal = form.lines.reduce((s, l) => s + lineTotal(l), 0);
    const scontoVal = subtotal * (parseFloat(form.sconto_globale) || 0) / 100;
    const imponibile = subtotal - scontoVal;
    const totalVat = form.lines.reduce((s, l) => {
        const base = lineTotal(l) * (1 - (parseFloat(form.sconto_globale) || 0) / 100);
        return s + base * (parseFloat(l.vat_rate) || 0) / 100;
    }, 0);
    const totale = imponibile + totalVat;
    const daPagare = totale - (parseFloat(form.acconto) || 0);

    const handleSave = async () => {
        if (!form.subject.trim()) { toast.error('Oggetto obbligatorio'); return; }
        setSaving(true);
        try {
            const payload = {
                ...form,
                client_id: form.client_id || null,
                lines: form.lines.map(l => ({
                    ...l, quantity: parseFloat(l.quantity) || 1, unit_price: parseFloat(l.unit_price) || 0,
                    sconto_1: parseFloat(l.sconto_1) || 0, sconto_2: parseFloat(l.sconto_2) || 0,
                })),
                acconto: parseFloat(form.acconto) || 0,
                sconto_globale: parseFloat(form.sconto_globale) || 0,
                giorni_consegna: form.giorni_consegna ? parseInt(form.giorni_consegna) : null,
                numero_disegno: form.numero_disegno || null,
                ingegnere_disegno: form.ingegnere_disegno || null,
                classe_esecuzione: form.classe_esecuzione || null,
            };
            if (isNew) {
                const res = await apiRequest('/preventivi/', { method: 'POST', body: payload });
                toast.success('Preventivo creato');
                clearDraft();
                navigate(`/preventivi/${res.preventivo_id}`, { replace: true });
            } else {
                await apiRequest(`/preventivi/${prevId}`, { method: 'PUT', body: payload });
                toast.success('Preventivo salvato');
                clearDraft();
            }
        } catch (e) { toast.error(e.message); } finally { setSaving(false); }
    };

    const handleCheckCompliance = async () => {
        if (isNew) { toast.error('Salva il preventivo prima'); return; }
        setChecking(true);
        try {
            const payload = { ...form, client_id: form.client_id || null, giorni_consegna: form.giorni_consegna ? parseInt(form.giorni_consegna) : null, lines: form.lines.map(l => ({ ...l, quantity: parseFloat(l.quantity) || 1, unit_price: parseFloat(l.unit_price) || 0 })) };
            await apiRequest(`/preventivi/${prevId}`, { method: 'PUT', body: payload });
            const result = await apiRequest(`/preventivi/${prevId}/check-compliance`, { method: 'POST' });
            setCompliance(result);
            if (result.all_compliant === true) toast.success('Tutte le voci conformi Ecobonus!');
            else if (result.all_compliant === false) toast.error('Alcune voci NON conformi!');
        } catch (e) { toast.error(e.message); } finally { setChecking(false); }
    };

    const handleDownloadPdf = async () => {
        if (isNew) return;
        try {
            const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;
            const res = await fetch(`${API_BASE}/preventivi/${prevId}/pdf`, { credentials: 'include' });
            if (!res.ok) throw new Error('Errore PDF');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `preventivo_${prevId}.pdf`; a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    const handleConvertToInvoice = async () => {
        if (isNew) return;
        if (!window.confirm('Convertire questo preventivo in Fattura?')) return;
        setConverting(true);
        try {
            const res = await apiRequest(`/preventivi/${prevId}/convert-to-invoice`, { method: 'POST' });
            toast.success(res.message);
            navigate(`/invoices/${res.invoice_id}`);
        } catch (e) { toast.error(e.message); } finally { setConverting(false); }
    };

    const handleConvertToProject = async () => {
        setShowFpcDialog(false);
        setConverting(true);
        try {
            const data = await apiRequest('/fpc/projects', {
                method: 'POST',
                body: { preventivo_id: prevId, execution_class: excClass },
            });
            toast.success('Progetto FPC creato!');
            navigate(`/tracciabilita/progetto/${data.project_id}`);
        } catch (e) { toast.error(e.message); } finally { setConverting(false); }
    };

    const handleGoToCommessa = async () => {
        if (linkedCommessa) {
            navigate(`/commesse/${linkedCommessa.commessa_id}`);
            return;
        }
        setCreatingCommessa(true);
        try {
            // Step 1: Analyze preventivo for normativa conflicts
            const analysis = await apiRequest(`/commesse/analyze-preventivo/${prevId}`);
            if (analysis.conflict) {
                // Mixed content detected — show split dialog
                setSplitAnalysis(analysis);
                setSplitGroups({
                    en_1090: analysis.groups.en_1090.map(i => i.index),
                    en_13241: analysis.groups.en_13241.map(i => i.index),
                    non_classificati: analysis.groups.non_classificati.map(i => i.index),
                });
                setShowSplitDialog(true);
                setCreatingCommessa(false);
                return;
            }
            // No conflict — create single commessa
            const res = await apiRequest(`/commesse/from-preventivo/${prevId}`, { method: 'POST' });
            toast.success(`Commessa ${res.numero || ''} creata!`);
            setLinkedCommessa(res);
            navigate(`/commesse/${res.commessa_id}`);
        } catch (e) { toast.error(e.message); } finally { setCreatingCommessa(false); }
    };

    const handleSplitConfirm = async () => {
        setSplittingCommesse(true);
        try {
            // Assign non-classified items to EN 1090 by default
            const indices1090 = [...splitGroups.en_1090, ...splitGroups.non_classificati];
            const indices13241 = [...splitGroups.en_13241];

            if (indices1090.length === 0 && indices13241.length === 0) {
                toast.error('Nessun item assegnato alle commesse');
                return;
            }

            const commesse = [];
            if (indices1090.length > 0) {
                commesse.push({ suffix: 'A', normativa: 'EN_1090', item_indices: indices1090 });
            }
            if (indices13241.length > 0) {
                commesse.push({ suffix: 'B', normativa: 'EN_13241', item_indices: indices13241 });
            }

            const res = await apiRequest(`/commesse/from-preventivo/${prevId}/split`, {
                method: 'POST',
                body: { commesse },
            });
            toast.success(res.message);
            setShowSplitDialog(false);
            // Navigate to first commessa
            if (res.commesse?.length > 0) {
                setLinkedCommessa(res.commesse[0]);
                navigate(`/commesse/${res.commesse[0].commessa_id}`);
            }
        } catch (e) { toast.error(e.message); } finally { setSplittingCommesse(false); }
    };

    const moveItem = (index, from, to) => {
        setSplitGroups(prev => ({
            ...prev,
            [from]: prev[from].filter(i => i !== index),
            [to]: [...prev[to], index],
        }));
    };

    const activeLine = activeLineIdx !== null ? form.lines[activeLineIdx] : null;
    const activeThermal = activeLine?.thermal_data;

    const handlePaymentTypeChange = (ptId) => {
        const pt = paymentTypes.find(p => p.payment_type_id === ptId);
        setForm(f => ({
            ...f,
            payment_type_id: ptId === '__none__' ? '' : ptId,
            payment_type_label: pt ? `${pt.codice} - ${pt.descrizione}` : '',
        }));
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="preventivo-editor">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate('/preventivi')}><ArrowLeft className="h-4 w-4" /></Button>
                        <div>
                            <h1 className="font-sans text-xl font-bold text-[#1E293B]">{isNew ? 'Nuovo Preventivo' : 'Modifica Preventivo'}</h1>
                            {workflow.number && <span className="text-xs font-mono text-slate-400">{workflow.number}</span>}
                        </div>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        {/* Always visible: technical tools */}
                        {!isNew && <Button data-testid="btn-download-pdf" variant="outline" onClick={handleDownloadPdf} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50 h-9 text-xs"><FileDown className="h-3.5 w-3.5 mr-1.5" /> PDF</Button>}
                        {!isNew && <PDFPreviewButton pdfUrl={`/preventivi/${prevId}/pdf`} title={`Anteprima Preventivo ${workflow.number || ''}`} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9" />}
                        {!isNew && (
                            <Button type="button" variant="outline" data-testid="btn-send-email-prev"
                                onClick={() => setEmailPreviewOpen(true)}
                                className="border-violet-400 text-violet-600 hover:bg-violet-50 h-9 text-xs"
                            >
                                <Mail className="h-3.5 w-3.5 mr-1" /> Email
                            </Button>
                        )}

                        {/* Workflow step: Accetta (only if bozza/inviato and not yet accepted) */}
                        {!isNew && !isAccepted && (
                            <Button data-testid="btn-accept-preventivo" onClick={handleAcceptPreventivo}
                                className="bg-emerald-600 text-white hover:bg-emerald-500 h-9 text-xs">
                                <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" /> Accetta Preventivo
                            </Button>
                        )}

                        {/* Workflow step: Fattura (only after acceptance) */}
                        {!isNew && isAccepted && (
                            <Button data-testid="btn-convert-invoice" onClick={() => setShowInvoiceModal(true)} disabled={converting}
                                className="bg-amber-500 text-white hover:bg-amber-400 h-9 text-xs">
                                <Receipt className="h-3.5 w-3.5 mr-1.5" /> Emetti Fattura
                            </Button>
                        )}

                        {/* Create/Go to Commessa */}
                        {!isNew && (
                            <Button data-testid="btn-go-commessa" variant="outline" onClick={handleGoToCommessa} disabled={creatingCommessa}
                                className={`h-9 text-xs ${linkedCommessa ? 'border-[#0055FF] text-[#0055FF] hover:bg-blue-50' : 'border-slate-400 text-slate-600 hover:bg-slate-50'}`}>
                                {creatingCommessa ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Briefcase className="h-3.5 w-3.5 mr-1.5" />}
                                {linkedCommessa ? `Commessa ${linkedCommessa.numero || ''}` : 'Commessa'}
                            </Button>
                        )}

                        {/* FPC Project */}
                        {!isNew && <Button data-testid="btn-convert-project" variant="outline" onClick={() => setShowFpcDialog(true)} disabled={converting} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9 text-xs"><Shield className="h-3.5 w-3.5 mr-1.5" /> FPC</Button>}

                        {/* Compliance */}
                        <DisabledTooltip show={isNew} reason="Salva il preventivo prima di verificare la compliance">
                        <Button data-testid="btn-check-compliance" variant="outline" onClick={handleCheckCompliance} disabled={checking || isNew} className="border-slate-300 text-slate-600 hover:bg-slate-50 h-9 text-xs">
                            <ShieldCheck className="h-3.5 w-3.5 mr-1.5" /> {checking ? '...' : 'Compliance'}
                        </Button>
                        </DisabledTooltip>

                        {/* Save */}
                        <Button data-testid="btn-save-preventivo" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC] h-9 text-xs"><Save className="h-3.5 w-3.5 mr-1.5" /> {saving ? 'Salvataggio...' : 'Salva'}</Button>
                    </div>
                </div>

                {/* Compliance Banner */}
                {compliance && compliance.checked_lines > 0 && (
                    <Card data-testid="compliance-banner" className={`border-2 ${compliance.all_compliant ? 'border-emerald-400 bg-emerald-50' : 'border-red-400 bg-red-50'}`}>
                        <CardContent className="py-2.5 px-5 flex items-center gap-3">
                            {compliance.all_compliant ? <><CheckCircle2 className="h-4 w-4 text-emerald-600" /><span className="text-sm font-semibold text-emerald-800">Ecobonus OK</span></> : <><XCircle className="h-4 w-4 text-red-600" /><span className="text-sm font-semibold text-red-800">Uw NON conforme</span></>}
                            <span className="text-xs text-slate-500 ml-auto">{compliance.checked_lines} voci</span>
                        </CardContent>
                    </Card>
                )}

                {/* Workflow Timeline */}
                {!isNew && workflow.number && (
                    <Card className="border-gray-200" data-testid="workflow-timeline">
                        <CardContent className="py-3 px-5">
                            <div className="flex items-center gap-0">
                                <TimelineStep active label="Preventivo" sub={workflow.number} icon={FileText} color="bg-[#0055FF]" />
                                <div className={`flex-1 h-0.5 ${isAccepted ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                                <TimelineStep active={isAccepted} label="Accettato" icon={CheckCircle2} color="bg-emerald-500" />
                                <div className={`flex-1 h-0.5 ${workflow.invoicing_progress > 0 ? 'bg-amber-400' : 'bg-slate-200'}`} />
                                <TimelineStep active={workflow.invoicing_progress > 0} label="Fatturazione" sub={workflow.invoicing_progress > 0 ? `${workflow.invoicing_progress}%` : ''} icon={Receipt} color="bg-amber-500" />
                                <div className={`flex-1 h-0.5 ${workflow.invoicing_progress >= 100 ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                                <TimelineStep active={workflow.invoicing_progress >= 100} label="Saldato" icon={Euro} color="bg-emerald-500" />
                            </div>
                            {/* Progress bar */}
                            {workflow.invoicing_progress > 0 && (
                                <div className="mt-2">
                                    <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                                        <span>Fatturato: {workflow.invoicing_progress}%</span>
                                        <span>{workflow.linked_invoices?.length || 0} fatture emesse</span>
                                    </div>
                                    <div className="w-full bg-slate-200 rounded-full h-1.5">
                                        <div
                                            className={`h-1.5 rounded-full transition-all ${workflow.invoicing_progress >= 100 ? 'bg-emerald-500' : 'bg-[#0055FF]'}`}
                                            style={{ width: `${Math.min(workflow.invoicing_progress, 100)}%` }}
                                        />
                                    </div>
                                </div>
                            )}
                            {/* Not accepted prompt */}
                            {!isAccepted && (
                                <p className="text-xs text-slate-400 mt-2 text-center">
                                    Clicca <strong>"Accetta Preventivo"</strong> per procedere alla fatturazione
                                </p>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* Main Grid: Sidebar + Content */}
                <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
                    {/* ── Left Sidebar ── */}
                    <div className="space-y-3">
                        {/* Header Card */}
                        <Card className="border-gray-200">
                            <CardContent className="p-4 space-y-3">
                                <div>
                                    <Label className="text-xs">Cliente</Label>
                                    <Select value={form.client_id || '__none__'} onValueChange={v => handleClientChange(v === '__none__' ? '' : v)}>
                                        <SelectTrigger data-testid="select-client" className="h-9"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                            {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Oggetto *</Label>
                                    <Input data-testid="input-subject" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="Fornitura serramenti" className="h-9 text-sm" />
                                </div>
                                <div>
                                    <Label className="text-xs">Validità (gg)</Label>
                                    <Input data-testid="input-validity" type="number" value={form.validity_days} onChange={e => setForm(f => ({ ...f, validity_days: parseInt(e.target.value) || 30 }))} className="h-9 text-sm font-mono" />
                                </div>
                            </CardContent>
                        </Card>

                        {/* Sidebar Tabs */}
                        <Card className="border-gray-200">
                            <div className="flex border-b border-slate-200">
                                {SIDEBAR_TABS.map(t => (
                                    <button key={t.key} onClick={() => setSidebarTab(t.key)} className={`flex-1 py-2 text-[10px] font-medium text-center border-b-2 transition-colors ${sidebarTab === t.key ? 'border-[#0055FF] text-[#0055FF]' : 'border-transparent text-slate-500'}`}>
                                        <t.icon className="h-3.5 w-3.5 mx-auto mb-0.5" />{t.label}
                                    </button>
                                ))}
                            </div>
                            <CardContent className="p-3 space-y-2.5">
                                {sidebarTab === 'riferimento' && (
                                    <div className="space-y-2.5">
                                        <div><Label className="text-xs">Riferimento / Commessa</Label><Input value={form.riferimento} onChange={e => setForm(f => ({ ...f, riferimento: e.target.value }))} placeholder="Rif. ordine..." className="h-8 text-xs" /></div>
                                        <div>
                                            <Label className="text-xs">Normativa</Label>
                                            <select
                                                data-testid="select-normativa"
                                                value={form.normativa || ''}
                                                onChange={e => setForm(f => ({ ...f, normativa: e.target.value }))}
                                                className="flex h-8 w-full items-center rounded-md border border-input bg-transparent px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                            >
                                                <option value="">-- Nessuna --</option>
                                                <option value="EN_1090">EN 1090 (Carpenteria strutturale)</option>
                                                <option value="EN_13241">EN 13241 (Porte e cancelli)</option>
                                            </select>
                                            <p className="text-[10px] text-slate-500 mt-0.5">Determina requisiti di tracciabilità materiali</p>
                                        </div>
                                        <div><Label className="text-xs">N. Disegno</Label><Input value={form.numero_disegno} onChange={e => setForm(f => ({ ...f, numero_disegno: e.target.value }))} placeholder="es. STR-01" className="h-8 text-xs" data-testid="input-numero-disegno" /></div>
                                        <div><Label className="text-xs">Redatto dall'Ing.</Label><Input value={form.ingegnere_disegno} onChange={e => setForm(f => ({ ...f, ingegnere_disegno: e.target.value }))} placeholder="Nome Cognome" className="h-8 text-xs" data-testid="input-ingegnere-disegno" /></div>
                                        <div>
                                            <Label className="text-xs">Classe di Esecuzione</Label>
                                            <select
                                                data-testid="select-classe-esecuzione"
                                                value={form.classe_esecuzione || ''}
                                                onChange={e => setForm(f => ({ ...f, classe_esecuzione: e.target.value }))}
                                                className="flex h-8 w-full items-center rounded-md border border-input bg-transparent px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                                            >
                                                <option value="">-- Nessuna --</option>
                                                <option value="EXC1">EXC1</option>
                                                <option value="EXC2">EXC2</option>
                                                <option value="EXC3">EXC3</option>
                                                <option value="EXC4">EXC4</option>
                                            </select>
                                        </div>
                                        <div><Label className="text-xs">Tempi di Consegna (giorni)</Label><Input type="text" inputMode="numeric" pattern="[0-9]*" value={form.giorni_consegna} onChange={e => { const v = e.target.value.replace(/[^0-9]/g,''); setForm(f => ({ ...f, giorni_consegna: v })); }} placeholder="es. 30" className="h-8 text-xs font-mono" data-testid="input-giorni-consegna" /></div>
                                        <div><Label className="text-xs">Sconto Globale (%)</Label><Input type="number" step="0.1" value={form.sconto_globale} onChange={e => setForm(f => ({ ...f, sconto_globale: parseFloat(e.target.value) || 0 }))} className="h-8 text-xs font-mono" /></div>
                                        <div><Label className="text-xs">Acconto</Label><Input type="number" step="0.01" value={form.acconto} onChange={e => setForm(f => ({ ...f, acconto: parseFloat(e.target.value) || 0 }))} className="h-8 text-xs font-mono" /></div>
                                    </div>
                                )}
                                {sidebarTab === 'pagamento' && (
                                    <div className="space-y-2.5">
                                        <div>
                                            <Label className="text-xs">Condizioni Pagamento</Label>
                                            <Select value={form.payment_type_id || '__none__'} onValueChange={handlePaymentTypeChange}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                                    {paymentTypes.map(pt => <SelectItem key={pt.payment_type_id} value={pt.payment_type_id}><span className="font-mono text-[10px] mr-1">{pt.codice}</span> {pt.descrizione}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div><Label className="text-xs">Banca</Label><Input value={form.banca} onChange={e => setForm(f => ({ ...f, banca: e.target.value }))} className="h-8 text-xs" /></div>
                                        <div><Label className="text-xs">IBAN</Label><Input value={form.iban} onChange={e => setForm(f => ({ ...f, iban: e.target.value.toUpperCase() }))} placeholder="IT60..." className="h-8 text-xs font-mono" /></div>
                                        <div><Label className="text-xs">Note Pagamento</Label><Textarea value={form.note_pagamento || ''} onChange={e => setForm(f => ({ ...f, note_pagamento: e.target.value }))} rows={3} className="text-xs" /></div>
                                    </div>
                                )}
                                {sidebarTab === 'destinazione' && (
                                    <div><Label className="text-xs">Destinazione Merce</Label><Textarea value={form.destinazione_merce || ''} onChange={e => setForm(f => ({ ...f, destinazione_merce: e.target.value }))} rows={4} placeholder="Indirizzo consegna..." className="text-xs" /></div>
                                )}
                                {sidebarTab === 'note_extra' && (
                                    <div><Label className="text-xs">Note Generali</Label><Textarea data-testid="input-notes" value={form.notes || ''} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={6} className="text-xs" /></div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* ── Right Content ── */}
                    <div className="space-y-4">
                        {/* Lines Table */}
                        <Card className="border-gray-200">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg flex flex-row items-center justify-between">
                                <CardTitle className="text-xs font-semibold text-white">Dettaglio Righe</CardTitle>
                                <Button data-testid="btn-add-line" size="sm" variant="ghost" onClick={addLine} className="text-white hover:text-blue-200 h-7 text-xs"><Plus className="h-3 w-3 mr-1" /> Aggiungi</Button>
                            </CardHeader>
                            <CardContent className="p-0 overflow-x-auto">
                                <Table className="table-fixed">
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="w-8 text-[10px]">#</TableHead>
                                            <TableHead className="text-[10px]">Descrizione</TableHead>
                                            <TableHead className="w-[60px] text-right text-[10px]">Q.tà</TableHead>
                                            <TableHead className="w-[60px] text-[10px]">UdM</TableHead>
                                            <TableHead className="w-[80px] text-right text-[10px]">Prezzo</TableHead>
                                            <TableHead className="w-[50px] text-right text-[10px]">Sc.1%</TableHead>
                                            <TableHead className="w-[50px] text-right text-[10px]">Sc.2%</TableHead>
                                            <TableHead className="w-[80px] text-right text-[10px]">Netto</TableHead>
                                            <TableHead className="w-[52px] text-[10px]">IVA</TableHead>
                                            <TableHead className="w-[85px] text-right text-[10px]">Totale</TableHead>
                                            <TableHead className="w-[40px] text-[10px]">Th.</TableHead>
                                            <TableHead className="w-8"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {form.lines.map((l, i) => {
                                            const net = lineNet(l);
                                            const lt = lineTotal(l);
                                            const hasTherm = !!l.thermal_data?.glass_id;
                                            const compResult = compliance?.results?.find(r => r.line_id === l.line_id);
                                            return (
                                                <TableRow key={l.line_id} data-testid={`line-${i}`}>
                                                    <TableCell className="text-[10px] text-slate-400 font-mono">{i + 1}</TableCell>
                                                    <TableCell><AutoExpandTextarea value={l.description} onChange={e => updateLine(i, 'description', e.target.value)} placeholder="Descrizione" className="text-xs" /></TableCell>
                                                    <TableCell className="px-1"><Input type="number" value={l.quantity} onChange={e => updateLine(i, 'quantity', e.target.value)} className="h-7 text-xs text-right font-mono w-full" /></TableCell>
                                                    <TableCell className="px-1">
                                                        <Select value={l.unit} onValueChange={v => updateLine(i, 'unit', v)}>
                                                            <SelectTrigger className="h-7 text-[10px] w-full"><SelectValue /></SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="pz">pz</SelectItem>
                                                                <SelectItem value="m">m</SelectItem>
                                                                <SelectItem value="mq">mq</SelectItem>
                                                                <SelectItem value="kg">kg</SelectItem>
                                                                <SelectItem value="h">h</SelectItem>
                                                                <SelectItem value="corpo">corpo</SelectItem>
                                                            </SelectContent>
                                                        </Select>
                                                    </TableCell>
                                                    <TableCell className="px-1"><Input type="number" step="0.01" value={l.unit_price} onChange={e => updateLine(i, 'unit_price', e.target.value)} className="h-7 text-xs text-right font-mono text-red-600 font-semibold w-full" /></TableCell>
                                                    <TableCell className="px-1"><Input type="number" step="0.1" value={l.sconto_1} onChange={e => updateLine(i, 'sconto_1', e.target.value)} className="h-7 text-[10px] text-right font-mono w-full" /></TableCell>
                                                    <TableCell className="px-1"><Input type="number" step="0.1" value={l.sconto_2} onChange={e => updateLine(i, 'sconto_2', e.target.value)} className="h-7 text-[10px] text-right font-mono w-full" /></TableCell>
                                                    <TableCell className="text-right font-mono text-xs text-slate-600 px-1 truncate">{fmtEur(net)}</TableCell>
                                                    <TableCell className="px-1">
                                                        <Select value={l.vat_rate} onValueChange={v => updateLine(i, 'vat_rate', v)}>
                                                            <SelectTrigger className="h-7 text-[10px] w-full"><SelectValue /></SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="22">22%</SelectItem>
                                                                <SelectItem value="10">10%</SelectItem>
                                                                <SelectItem value="4">4%</SelectItem>
                                                                <SelectItem value="0">0%</SelectItem>
                                                            </SelectContent>
                                                        </Select>
                                                    </TableCell>
                                                    <TableCell className="text-right font-mono text-xs font-semibold text-[#0055FF] px-1 truncate">{fmtEur(lt)}</TableCell>
                                                    <TableCell>
                                                        <div className="flex items-center gap-0.5">
                                                            <button data-testid={`thermal-btn-${i}`} onClick={() => openThermalDrawer(i)} className={`p-1 rounded ${hasTherm ? 'text-[#0055FF] bg-blue-50' : 'text-slate-300 hover:text-slate-500'}`}>
                                                                <Thermometer className="h-3 w-3" />
                                                            </button>
                                                            {compResult && (compResult.compliant ? <CheckCircle2 className="h-3 w-3 text-emerald-500" /> : <XCircle className="h-3 w-3 text-red-500" />)}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>{form.lines.length > 1 && <button onClick={() => removeLine(i)} className="p-1 text-slate-400 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>}</TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* Totals Card — Invoicex style */}
                        <Card className="border-gray-200" data-testid="totals-card">
                            <CardContent className="p-0">
                                <div className="grid grid-cols-2">
                                    {/* Left: Compliance detail (if any) */}
                                    <div className="p-4 border-r border-slate-200">
                                        {compliance && compliance.results?.length > 0 ? (
                                            <div className="space-y-2">
                                                <p className="text-xs font-semibold text-[#1E293B] flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5 text-[#0055FF]" /> Compliance Termica</p>
                                                {compliance.results.map((r, i) => (
                                                    <div key={i} className="flex items-center justify-between text-xs">
                                                        <span className="text-slate-600 truncate max-w-[180px]">{r.description}</span>
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-mono">Uw={r.uw}</span>
                                                            <Badge className={`text-[9px] ${r.compliant ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}`}>{r.compliant ? 'OK' : 'NO'}</Badge>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <p className="text-xs text-slate-400 py-8 text-center">Nessun dato compliance</p>
                                        )}
                                    </div>

                                    {/* Right: Totals */}
                                    <div className="p-4 space-y-1.5" data-testid="totals-summary">
                                        <TotalRow label="Totale senza IVA" value={fmtEur(subtotal)} />
                                        {form.sconto_globale > 0 && <TotalRow label={`Sconto ${form.sconto_globale}%`} value={`-${fmtEur(scontoVal)}`} className="text-red-500" />}
                                        <TotalRow label="Imponibile" value={fmtEur(imponibile)} />
                                        <TotalRow label="Totale IVA" value={fmtEur(totalVat)} />
                                        <Separator />
                                        <div className="flex justify-between items-center pt-1">
                                            <span className="text-sm font-bold text-[#1E293B]">TOTALE</span>
                                            <span className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(totale)}</span>
                                        </div>
                                        {form.acconto > 0 && <TotalRow label="Acconto" value={`-${fmtEur(form.acconto)}`} className="text-amber-600" />}
                                        {form.acconto > 0 && (
                                            <div className="flex justify-between items-center bg-slate-50 -mx-4 px-4 py-2 rounded-b-lg">
                                                <span className="text-sm font-bold text-[#1E293B]">DA PAGARE</span>
                                                <span className="font-mono text-lg font-bold text-emerald-600">{fmtEur(daPagare)}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>

            {/* Thermal Drawer */}
            <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
                <SheetContent data-testid="thermal-drawer" className="w-[400px] sm:w-[480px]">
                    <SheetHeader><SheetTitle className="flex items-center gap-2"><Settings2 className="h-5 w-5 text-[#0055FF]" /> Dettagli Tecnici</SheetTitle></SheetHeader>
                    {activeThermal && (
                        <div className="space-y-4 mt-6">
                            <p className="text-sm text-slate-500 bg-blue-50 p-3 rounded">Configura vetro, telaio e canalina per il calcolo Uw.</p>
                            <div className="grid grid-cols-2 gap-3">
                                <div><Label>Altezza (mm)</Label><Input data-testid="drawer-height" type="number" value={activeThermal.height_mm} onChange={e => updateThermal('height_mm', parseFloat(e.target.value) || 0)} /></div>
                                <div><Label>Larghezza (mm)</Label><Input data-testid="drawer-width" type="number" value={activeThermal.width_mm} onChange={e => updateThermal('width_mm', parseFloat(e.target.value) || 0)} /></div>
                            </div>
                            <div><Label>Vetro</Label><Select value={activeThermal.glass_id} onValueChange={v => updateThermal('glass_id', v)}><SelectTrigger data-testid="drawer-glass"><SelectValue /></SelectTrigger><SelectContent>{thermalRef.glass_types?.map(g => <SelectItem key={g.id} value={g.id}>{g.label} (Ug={g.ug})</SelectItem>)}</SelectContent></Select></div>
                            <div><Label>Telaio</Label><Select value={activeThermal.frame_id} onValueChange={v => updateThermal('frame_id', v)}><SelectTrigger data-testid="drawer-frame"><SelectValue /></SelectTrigger><SelectContent>{thermalRef.frame_types?.map(f => <SelectItem key={f.id} value={f.id}>{f.label} (Uf={f.uf})</SelectItem>)}</SelectContent></Select></div>
                            <div><Label>Canalina</Label><Select value={activeThermal.spacer_id} onValueChange={v => updateThermal('spacer_id', v)}><SelectTrigger data-testid="drawer-spacer"><SelectValue /></SelectTrigger><SelectContent>{thermalRef.spacer_types?.map(s => <SelectItem key={s.id} value={s.id}>{s.label} (Psi={s.psi})</SelectItem>)}</SelectContent></Select></div>
                            <div><Label>Zona Climatica</Label><Select value={activeThermal.zone} onValueChange={v => updateThermal('zone', v)}><SelectTrigger data-testid="drawer-zone"><SelectValue /></SelectTrigger><SelectContent>{ZONES.map(z => <SelectItem key={z} value={z}>Zona {z}</SelectItem>)}</SelectContent></Select></div>
                            <Separator />
                            <div className="flex gap-2">
                                <Button onClick={() => setDrawerOpen(false)} className="flex-1 bg-[#0055FF] text-white hover:bg-[#0044CC]">Conferma</Button>
                                <Button variant="outline" onClick={() => { if (activeLineIdx !== null) removeThermal(activeLineIdx); setDrawerOpen(false); }} className="text-red-500 border-red-300">Rimuovi</Button>
                            </div>
                        </div>
                    )}
                </SheetContent>
            </Sheet>

            {/* FPC Project Conversion Dialog */}
            <Dialog open={showFpcDialog} onOpenChange={setShowFpcDialog}>
                <DialogContent className="max-w-sm">
                    <DialogHeader><DialogTitle>Converti in Progetto FPC</DialogTitle></DialogHeader>
                    <p className="text-sm text-slate-500 mb-3">Seleziona la classe di esecuzione EN 1090 per questo progetto.</p>
                    <select data-testid="exc-class-select" value={excClass} onChange={e => setExcClass(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                        <option value="EXC1">EXC1 — Strutture semplici</option>
                        <option value="EXC2">EXC2 — Strutture standard (pi&ugrave; comune)</option>
                        <option value="EXC3">EXC3 — Strutture ad alta sollecitazione</option>
                        <option value="EXC4">EXC4 — Strutture speciali / ponti</option>
                    </select>
                    <DialogFooter>
                        <Button data-testid="confirm-fpc-btn" onClick={handleConvertToProject} className="bg-emerald-600 hover:bg-emerald-500">Crea Progetto</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Progressive Invoice Modal */}
            <InvoiceGenerationModal
                open={showInvoiceModal}
                onOpenChange={setShowInvoiceModal}
                prevId={prevId}
                onCreated={(res) => navigate(`/invoices/${res.invoice_id}`)}
            />
            <EmailPreviewDialog
                open={emailPreviewOpen}
                onOpenChange={setEmailPreviewOpen}
                previewUrl={`/api/preventivi/${prevId}/preview-email`}
                sendUrl={`/api/preventivi/${prevId}/send-email`}
            />

            {/* Split Commessa Dialog */}
            <Dialog open={showSplitDialog} onOpenChange={setShowSplitDialog}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="split-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-base">
                            <AlertTriangle className="h-5 w-5 text-amber-500" />
                            Preventivo con normative miste
                        </DialogTitle>
                    </DialogHeader>

                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mt-2">
                        <p className="text-sm text-amber-800">
                            Questo preventivo contiene elementi soggetti a normative diverse.
                            Un cancello non può stare nello stesso fascicolo di una tettoia.
                            <strong> Consigliamo di creare 2 commesse separate.</strong>
                        </p>
                    </div>

                    {splitAnalysis && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            {/* Commessa A — EN 1090 */}
                            <div className="border border-blue-200 rounded-lg overflow-hidden" data-testid="split-group-1090">
                                <div className="bg-blue-50 px-3 py-2 flex items-center gap-2 border-b border-blue-200">
                                    <Wrench className="h-4 w-4 text-blue-600" />
                                    <span className="text-sm font-semibold text-blue-800">Commessa A — Strutture</span>
                                    <Badge variant="outline" className="ml-auto text-[10px] border-blue-300 text-blue-600">EN 1090</Badge>
                                </div>
                                <div className="p-2 space-y-1.5 min-h-[80px]">
                                    {splitGroups.en_1090.map(idx => {
                                        const line = form.lines[idx];
                                        if (!line) return null;
                                        return (
                                            <div key={idx} className="flex items-center justify-between bg-white border rounded px-2 py-1.5 text-xs group" data-testid={`split-item-1090-${idx}`}>
                                                <span className="truncate flex-1 mr-2">{line.description || `Riga ${idx + 1}`}</span>
                                                <button onClick={() => moveItem(idx, 'en_1090', 'en_13241')} className="text-slate-400 hover:text-amber-600 opacity-0 group-hover:opacity-100 transition-opacity" title="Sposta a Cancelli">
                                                    <ArrowRight className="h-3.5 w-3.5" />
                                                </button>
                                            </div>
                                        );
                                    })}
                                    {splitGroups.non_classificati.map(idx => {
                                        const line = form.lines[idx];
                                        if (!line) return null;
                                        return (
                                            <div key={`nc-${idx}`} className="flex items-center justify-between bg-slate-50 border border-dashed border-slate-300 rounded px-2 py-1.5 text-xs group" data-testid={`split-item-other-${idx}`}>
                                                <span className="truncate flex-1 mr-2 text-slate-500">{line.description || `Riga ${idx + 1}`}</span>
                                                <span className="text-[9px] text-slate-400 mr-1">generico</span>
                                                <button onClick={() => moveItem(idx, 'non_classificati', 'en_13241')} className="text-slate-400 hover:text-amber-600 opacity-0 group-hover:opacity-100 transition-opacity" title="Sposta a Cancelli">
                                                    <ArrowRight className="h-3.5 w-3.5" />
                                                </button>
                                            </div>
                                        );
                                    })}
                                    {splitGroups.en_1090.length === 0 && splitGroups.non_classificati.length === 0 && (
                                        <p className="text-xs text-slate-400 text-center py-3">Nessun item</p>
                                    )}
                                </div>
                            </div>

                            {/* Commessa B — EN 13241 */}
                            <div className="border border-amber-200 rounded-lg overflow-hidden" data-testid="split-group-13241">
                                <div className="bg-amber-50 px-3 py-2 flex items-center gap-2 border-b border-amber-200">
                                    <DoorOpen className="h-4 w-4 text-amber-600" />
                                    <span className="text-sm font-semibold text-amber-800">Commessa B — Cancelli</span>
                                    <Badge variant="outline" className="ml-auto text-[10px] border-amber-300 text-amber-600">EN 13241</Badge>
                                </div>
                                <div className="p-2 space-y-1.5 min-h-[80px]">
                                    {splitGroups.en_13241.map(idx => {
                                        const line = form.lines[idx];
                                        if (!line) return null;
                                        return (
                                            <div key={idx} className="flex items-center justify-between bg-white border rounded px-2 py-1.5 text-xs group" data-testid={`split-item-13241-${idx}`}>
                                                <button onClick={() => moveItem(idx, 'en_13241', 'en_1090')} className="text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity mr-2" title="Sposta a Strutture">
                                                    <ArrowLeft className="h-3.5 w-3.5" />
                                                </button>
                                                <span className="truncate flex-1">{line.description || `Riga ${idx + 1}`}</span>
                                            </div>
                                        );
                                    })}
                                    {splitGroups.en_13241.length === 0 && (
                                        <p className="text-xs text-slate-400 text-center py-3">Nessun item</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    <DialogFooter className="mt-4 gap-2">
                        <Button variant="outline" onClick={() => setShowSplitDialog(false)} className="text-xs">Annulla</Button>
                        <Button
                            data-testid="btn-confirm-split"
                            onClick={handleSplitConfirm}
                            disabled={splittingCommesse}
                            className="bg-amber-500 hover:bg-amber-600 text-white text-xs"
                        >
                            {splittingCommesse ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <ArrowRightLeft className="h-3.5 w-3.5 mr-1.5" />}
                            Crea 2 Commesse Separate
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}

function TimelineStep({ active, label, sub, icon: Icon, color, onClick }) {
    return (
        <div className="flex flex-col items-center text-center min-w-[80px] cursor-pointer" onClick={onClick}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${active ? color : 'bg-slate-200'}`}>
                <Icon className={`h-3.5 w-3.5 ${active ? 'text-white' : 'text-slate-400'}`} />
            </div>
            <span className={`text-[10px] font-semibold mt-1 ${active ? 'text-[#1E293B]' : 'text-slate-400'}`}>{label}</span>
            {sub && <span className="text-[9px] font-mono text-[#0055FF]">{sub}</span>}
        </div>
    );
}

function TotalRow({ label, value, className = '' }) {
    return (
        <div className="flex justify-between text-xs">
            <span className="text-slate-500">{label}</span>
            <span className={`font-mono font-medium ${className}`}>{value}</span>
        </div>
    );
}
