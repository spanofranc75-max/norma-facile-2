/**
 * Preventivo Editor - Smart Quote with Thermal Compliance
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Sheet, SheetContent, SheetHeader, SheetTitle,
} from '../components/ui/sheet';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Plus, Trash2, Save, ArrowLeft, FileDown, CheckCircle2, XCircle,
    Thermometer, ShieldCheck, Settings2, ArrowRightLeft,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const ZONES = ['A', 'B', 'C', 'D', 'E', 'F'];
const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const emptyLine = () => ({
    line_id: `ln_${Date.now().toString(36)}`,
    description: '', dimensions: '', quantity: 1, unit: 'pz', unit_price: 0, vat_rate: '22',
    thermal_data: null, notes: '',
});

export default function PreventivoEditorPage() {
    const navigate = useNavigate();
    const { prevId } = useParams();
    const isNew = !prevId || prevId === 'new';

    const [form, setForm] = useState({
        client_id: '', subject: '', validity_days: 30, payment_terms: '30gg', notes: '', lines: [emptyLine()],
    });
    const [clients, setClients] = useState([]);
    const [thermalRef, setThermalRef] = useState({ glass_types: [], frame_types: [], spacer_types: [] });
    const [compliance, setCompliance] = useState(null);
    const [saving, setSaving] = useState(false);
    const [checking, setChecking] = useState(false);
    const [converting, setConverting] = useState(false);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [activeLineIdx, setActiveLineIdx] = useState(null);
    const [workflow, setWorkflow] = useState({ status: 'bozza', number: null, created_at: null, converted_to: null, linked_invoice: null });

    // Fetch clients + thermal ref
    useEffect(() => {
        Promise.all([
            apiRequest('/clients/').catch(() => ({ clients: [] })),
            apiRequest('/certificazioni/thermal/reference-data').catch(() => ({})),
        ]).then(([cl, th]) => {
            setClients(cl.clients || []);
            setThermalRef(th);
        });
    }, []);

    // Load existing preventivo
    useEffect(() => {
        if (isNew) return;
        apiRequest(`/preventivi/${prevId}`).then(data => {
            setForm({
                client_id: data.client_id || '',
                subject: data.subject || '',
                validity_days: data.validity_days || 30,
                payment_terms: data.payment_terms || '30gg',
                notes: data.notes || '',
                lines: data.lines?.length ? data.lines : [emptyLine()],
            });
            if (data.compliance_detail) setCompliance(data.compliance_detail);
            setWorkflow({
                status: data.status || 'bozza',
                number: data.number,
                created_at: data.created_at,
                converted_to: data.converted_to,
                linked_invoice: data.linked_invoice || null,
            });
        }).catch(() => toast.error('Preventivo non trovato'));
    }, [prevId, isNew]);

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
        // Initialize thermal_data if not set
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
            lines[activeLineIdx] = {
                ...lines[activeLineIdx],
                thermal_data: { ...lines[activeLineIdx].thermal_data, [field]: value },
            };
            return { ...f, lines };
        });
    };

    const removeThermal = (idx) => updateLine(idx, 'thermal_data', null);

    // Subtotal calculation
    const subtotal = form.lines.reduce((sum, l) => sum + (l.quantity || 0) * (l.unit_price || 0), 0);
    const totalVat = form.lines.reduce((sum, l) => {
        const base = (l.quantity || 0) * (l.unit_price || 0);
        const rate = parseFloat(l.vat_rate) || 0;
        return sum + base * rate / 100;
    }, 0);
    const total = subtotal + totalVat;

    const handleSave = async () => {
        if (!form.subject.trim()) { toast.error('Oggetto obbligatorio'); return; }
        setSaving(true);
        try {
            const payload = {
                ...form,
                client_id: form.client_id || null,
                lines: form.lines.map(l => ({
                    ...l,
                    quantity: parseFloat(l.quantity) || 1,
                    unit_price: parseFloat(l.unit_price) || 0,
                })),
            };
            if (isNew) {
                const res = await apiRequest('/preventivi/', { method: 'POST', body: payload });
                toast.success('Preventivo creato');
                navigate(`/preventivi/${res.preventivo_id}`, { replace: true });
            } else {
                await apiRequest(`/preventivi/${prevId}`, { method: 'PUT', body: payload });
                toast.success('Preventivo salvato');
            }
        } catch (e) { toast.error(e.message); } finally { setSaving(false); }
    };

    const handleCheckCompliance = async () => {
        if (isNew) { toast.error('Salva il preventivo prima di verificare la compliance'); return; }
        setChecking(true);
        try {
            // Save first, then check
            const payload = {
                ...form,
                client_id: form.client_id || null,
                lines: form.lines.map(l => ({
                    ...l,
                    quantity: parseFloat(l.quantity) || 1,
                    unit_price: parseFloat(l.unit_price) || 0,
                })),
            };
            await apiRequest(`/preventivi/${prevId}`, { method: 'PUT', body: payload });
            const result = await apiRequest(`/preventivi/${prevId}/check-compliance`, { method: 'POST' });
            setCompliance(result);
            if (result.all_compliant === true) toast.success('Tutte le voci conformi Ecobonus!');
            else if (result.all_compliant === false) toast.error('Alcune voci NON conformi!');
            else toast('Nessuna voce con dati termici da verificare');
        } catch (e) { toast.error(e.message); } finally { setChecking(false); }
    };

    const handleDownloadPdf = async () => {
        if (isNew) return;
        try {
            const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;
            const res = await fetch(`${API_BASE}/preventivi/${prevId}/pdf`, { credentials: 'include' });
            if (!res.ok) throw new Error('Errore generazione PDF');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `preventivo_${prevId}.pdf`; a.click();
            URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch (e) { toast.error(e.message); }
    };

    const handleConvertToInvoice = async () => {
        if (isNew) return;
        if (!window.confirm('Convertire questo preventivo in Fattura? Il preventivo sara marcato come "Accettato".')) return;
        setConverting(true);
        try {
            const res = await apiRequest(`/preventivi/${prevId}/convert-to-invoice`, { method: 'POST' });
            toast.success(res.message);
            navigate(`/invoices/${res.invoice_id}`);
        } catch (e) { toast.error(e.message || 'Errore nella conversione'); } finally { setConverting(false); }
    };

    const activeLine = activeLineIdx !== null ? form.lines[activeLineIdx] : null;
    const activeThermal = activeLine?.thermal_data;

    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="preventivo-editor">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate('/preventivi')}><ArrowLeft className="h-4 w-4" /></Button>
                        <h1 className="font-sans text-xl font-bold text-[#1E293B]">{isNew ? 'Nuovo Preventivo' : 'Modifica Preventivo'}</h1>
                    </div>
                    <div className="flex gap-2">
                        <Button data-testid="btn-check-compliance" variant="outline" onClick={handleCheckCompliance} disabled={checking || isNew} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50">
                            <ShieldCheck className="h-4 w-4 mr-2" /> {checking ? 'Verifica...' : 'Verifica Compliance'}
                        </Button>
                        {!isNew && (
                            <Button data-testid="btn-download-pdf" variant="outline" onClick={handleDownloadPdf} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50">
                                <FileDown className="h-4 w-4 mr-2" /> PDF
                            </Button>
                        )}
                        {!isNew && (
                            <Button data-testid="btn-convert-invoice" variant="outline" onClick={handleConvertToInvoice} disabled={converting} className="border-amber-500 text-amber-600 hover:bg-amber-50">
                                <ArrowRightLeft className="h-4 w-4 mr-2" /> {converting ? 'Conversione...' : 'Converti in Fattura'}
                            </Button>
                        )}
                        <Button data-testid="btn-save-preventivo" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Save className="h-4 w-4 mr-2" /> {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </div>
                </div>

                {/* Compliance Banner */}
                {compliance && compliance.checked_lines > 0 && (
                    <Card data-testid="compliance-banner" className={`border-2 ${compliance.all_compliant ? 'border-emerald-400 bg-emerald-50' : 'border-red-400 bg-red-50'}`}>
                        <CardContent className="py-3 px-5 flex items-center gap-3">
                            {compliance.all_compliant ? (
                                <>
                                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                    <span className="font-semibold text-emerald-800">Ecobonus 2026 OK — Tutte le voci conformi</span>
                                </>
                            ) : (
                                <>
                                    <XCircle className="h-5 w-5 text-red-600" />
                                    <span className="font-semibold text-red-800">Uw troppo alto! Alcune voci non conformi Ecobonus</span>
                                </>
                            )}
                            <span className="text-xs text-slate-500 ml-auto">{compliance.checked_lines} voci verificate</span>
                        </CardContent>
                    </Card>
                )}

                {/* Workflow Timeline */}
                {!isNew && workflow.number && (
                    <Card className="border-gray-200" data-testid="workflow-timeline">
                        <CardContent className="py-4 px-5">
                            <div className="flex items-center gap-0">
                                {/* Step 1: Preventivo */}
                                <div className="flex flex-col items-center text-center min-w-[100px]">
                                    <div className="w-9 h-9 rounded-full bg-[#0055FF] flex items-center justify-center">
                                        <FileDown className="h-4 w-4 text-white" />
                                    </div>
                                    <span className="text-xs font-semibold text-[#1E293B] mt-1.5">Preventivo</span>
                                    <span className="text-[10px] text-[#0055FF] font-mono">{workflow.number}</span>
                                </div>
                                {/* Connector */}
                                <div className={`flex-1 h-0.5 ${workflow.status === 'accettato' ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                                {/* Step 2: Accettato */}
                                <div className="flex flex-col items-center text-center min-w-[100px]">
                                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${workflow.status === 'accettato' ? 'bg-emerald-500' : 'bg-slate-200'}`}>
                                        <CheckCircle2 className={`h-4 w-4 ${workflow.status === 'accettato' ? 'text-white' : 'text-slate-400'}`} />
                                    </div>
                                    <span className={`text-xs font-semibold mt-1.5 ${workflow.status === 'accettato' ? 'text-emerald-700' : 'text-slate-400'}`}>Accettato</span>
                                </div>
                                {/* Connector */}
                                <div className={`flex-1 h-0.5 ${workflow.linked_invoice ? 'bg-[#0055FF]' : 'bg-slate-200'}`} />
                                {/* Step 3: Fattura */}
                                <div className="flex flex-col items-center text-center min-w-[100px]">
                                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${workflow.linked_invoice ? 'bg-[#0055FF] cursor-pointer' : 'bg-slate-200'}`} onClick={() => workflow.linked_invoice && navigate(`/invoices/${workflow.linked_invoice.invoice_id}`)}>
                                        <ArrowRightLeft className={`h-4 w-4 ${workflow.linked_invoice ? 'text-white' : 'text-slate-400'}`} />
                                    </div>
                                    <span className={`text-xs font-semibold mt-1.5 ${workflow.linked_invoice ? 'text-[#0055FF]' : 'text-slate-400'}`}>Fattura</span>
                                    {workflow.linked_invoice && (
                                        <button onClick={() => navigate(`/invoices/${workflow.linked_invoice.invoice_id}`)} className="text-[10px] text-[#0055FF] font-mono hover:underline">{workflow.linked_invoice.document_number}</button>
                                    )}
                                </div>
                                {/* Connector */}
                                <div className={`flex-1 h-0.5 ${workflow.linked_invoice?.status === 'pagata' ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                                {/* Step 4: Pagata */}
                                <div className="flex flex-col items-center text-center min-w-[100px]">
                                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${workflow.linked_invoice?.status === 'pagata' ? 'bg-emerald-500' : 'bg-slate-200'}`}>
                                        <Euro className={`h-4 w-4 ${workflow.linked_invoice?.status === 'pagata' ? 'text-white' : 'text-slate-400'}`} />
                                    </div>
                                    <span className={`text-xs font-semibold mt-1.5 ${workflow.linked_invoice?.status === 'pagata' ? 'text-emerald-700' : 'text-slate-400'}`}>Pagata</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Form Header */}
                <Card className="border-gray-200">
                    <CardHeader className="bg-blue-50 border-b border-gray-200 py-3 px-5">
                        <CardTitle className="text-sm font-semibold text-[#1E293B]">Dati Preventivo</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 pb-3 px-5">
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <div>
                                <Label>Cliente</Label>
                                <Select value={form.client_id} onValueChange={v => setForm(f => ({ ...f, client_id: v }))}>
                                    <SelectTrigger data-testid="select-client"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                    <SelectContent>
                                        {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Oggetto *</Label>
                                <Input data-testid="input-subject" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="es. Fornitura serramenti" />
                            </div>
                            <div>
                                <Label>Validita (giorni)</Label>
                                <Input data-testid="input-validity" type="number" value={form.validity_days} onChange={e => setForm(f => ({ ...f, validity_days: parseInt(e.target.value) || 30 }))} />
                            </div>
                            <div>
                                <Label>Pagamento</Label>
                                <Select value={form.payment_terms} onValueChange={v => setForm(f => ({ ...f, payment_terms: v }))}>
                                    <SelectTrigger data-testid="select-payment"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="immediato">Immediato</SelectItem>
                                        <SelectItem value="30gg">30 giorni</SelectItem>
                                        <SelectItem value="60gg">60 giorni</SelectItem>
                                        <SelectItem value="90gg">90 giorni</SelectItem>
                                        <SelectItem value="fine_mese">Fine mese</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Lines Table */}
                <Card className="border-gray-200">
                    <CardHeader className="bg-[#1E293B] py-3 px-5 rounded-t-lg flex flex-row items-center justify-between">
                        <CardTitle className="text-sm font-semibold text-white">Voci Preventivo</CardTitle>
                        <Button data-testid="btn-add-line" size="sm" variant="ghost" onClick={addLine} className="text-white hover:text-blue-200 h-7 text-xs">
                            <Plus className="h-3 w-3 mr-1" /> Aggiungi Voce
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0 overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-50">
                                    <TableHead className="w-8">#</TableHead>
                                    <TableHead className="min-w-[180px]">Descrizione</TableHead>
                                    <TableHead className="w-24">Dimensioni</TableHead>
                                    <TableHead className="w-16 text-right">Q.ta</TableHead>
                                    <TableHead className="w-24 text-right">Prezzo</TableHead>
                                    <TableHead className="w-16">IVA</TableHead>
                                    <TableHead className="w-24 text-right">Totale</TableHead>
                                    <TableHead className="w-20">Termico</TableHead>
                                    <TableHead className="w-10"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {form.lines.map((l, i) => {
                                    const lineTotal = (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0);
                                    const hasTherm = !!l.thermal_data?.glass_id;
                                    const compResult = compliance?.results?.find(r => r.line_id === l.line_id);
                                    return (
                                        <TableRow key={l.line_id} data-testid={`line-${i}`}>
                                            <TableCell className="text-xs text-slate-400 font-mono">{i + 1}</TableCell>
                                            <TableCell>
                                                <Input value={l.description} onChange={e => updateLine(i, 'description', e.target.value)} placeholder="Descrizione voce" className="h-8 text-sm" />
                                            </TableCell>
                                            <TableCell>
                                                <Input value={l.dimensions || ''} onChange={e => updateLine(i, 'dimensions', e.target.value)} placeholder="LxH" className="h-8 text-sm" />
                                            </TableCell>
                                            <TableCell>
                                                <Input type="number" value={l.quantity} onChange={e => updateLine(i, 'quantity', e.target.value)} className="h-8 text-sm text-right" />
                                            </TableCell>
                                            <TableCell>
                                                <Input type="number" step="0.01" value={l.unit_price} onChange={e => updateLine(i, 'unit_price', e.target.value)} className="h-8 text-sm text-right" />
                                            </TableCell>
                                            <TableCell>
                                                <Select value={l.vat_rate} onValueChange={v => updateLine(i, 'vat_rate', v)}>
                                                    <SelectTrigger className="h-8 text-xs w-16"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="22">22%</SelectItem>
                                                        <SelectItem value="10">10%</SelectItem>
                                                        <SelectItem value="4">4%</SelectItem>
                                                        <SelectItem value="0">0%</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-sm font-medium text-[#0055FF]">{fmtEur(lineTotal)}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center gap-1">
                                                    <button data-testid={`thermal-btn-${i}`} onClick={() => openThermalDrawer(i)} className={`p-1.5 rounded ${hasTherm ? 'text-[#0055FF] bg-blue-50' : 'text-slate-300 hover:text-slate-500'}`}>
                                                        <Thermometer className="h-3.5 w-3.5" />
                                                    </button>
                                                    {compResult && (
                                                        compResult.compliant ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <XCircle className="h-3.5 w-3.5 text-red-500" />
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {form.lines.length > 1 && (
                                                    <button onClick={() => removeLine(i)} className="p-1 text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* Totals + Notes */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    <Card className="border-gray-200">
                        <CardHeader className="bg-blue-50 border-b py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B]">Note</CardTitle>
                        </CardHeader>
                        <CardContent className="p-4">
                            <Textarea data-testid="input-notes" value={form.notes || ''} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Note aggiuntive..." rows={4} />
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200" data-testid="totals-card">
                        <CardHeader className="bg-blue-50 border-b py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B]">Riepilogo</CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 space-y-2">
                            <div className="flex justify-between text-sm"><span className="text-slate-500">Imponibile</span><span className="font-mono">{fmtEur(subtotal)}</span></div>
                            <div className="flex justify-between text-sm"><span className="text-slate-500">IVA</span><span className="font-mono">{fmtEur(totalVat)}</span></div>
                            <Separator />
                            <div className="flex justify-between"><span className="font-semibold text-[#1E293B]">TOTALE</span><span className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(total)}</span></div>
                        </CardContent>
                    </Card>
                </div>

                {/* Compliance Detail */}
                {compliance && compliance.results?.length > 0 && (
                    <Card className="border-gray-200" data-testid="compliance-detail">
                        <CardHeader className="bg-blue-50 border-b py-3 px-5">
                            <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                <ShieldCheck className="h-4 w-4 text-[#0055FF]" /> Dettaglio Compliance Termica
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-slate-50">
                                        <TableHead>Voce</TableHead>
                                        <TableHead>Vetro</TableHead>
                                        <TableHead>Telaio</TableHead>
                                        <TableHead className="text-center">Uw</TableHead>
                                        <TableHead className="text-center">Zona</TableHead>
                                        <TableHead className="text-center">Limite</TableHead>
                                        <TableHead className="text-center">Esito</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {compliance.results.map((r, i) => (
                                        <TableRow key={i}>
                                            <TableCell className="text-sm">{r.description}</TableCell>
                                            <TableCell className="text-xs text-slate-500">{r.glass_label}</TableCell>
                                            <TableCell className="text-xs text-slate-500">{r.frame_label}</TableCell>
                                            <TableCell className="text-center font-mono font-bold text-sm">{r.uw}</TableCell>
                                            <TableCell className="text-center font-mono text-sm">{r.zone}</TableCell>
                                            <TableCell className="text-center font-mono text-sm">{r.limit}</TableCell>
                                            <TableCell className="text-center">
                                                <Badge className={r.compliant ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}>
                                                    {r.compliant ? 'CONFORME' : 'NON CONFORME'}
                                                </Badge>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* Thermal Details Drawer */}
            <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
                <SheetContent data-testid="thermal-drawer" className="w-[400px] sm:w-[480px]">
                    <SheetHeader>
                        <SheetTitle className="flex items-center gap-2">
                            <Settings2 className="h-5 w-5 text-[#0055FF]" /> Dettagli Tecnici
                        </SheetTitle>
                    </SheetHeader>
                    {activeThermal && (
                        <div className="space-y-4 mt-6">
                            <p className="text-sm text-slate-500 bg-blue-50 p-3 rounded">
                                Configura vetro, telaio e canalina per calcolare la trasmittanza termica Uw di questa voce.
                            </p>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Label>Altezza (mm)</Label>
                                    <Input data-testid="drawer-height" type="number" value={activeThermal.height_mm} onChange={e => updateThermal('height_mm', parseFloat(e.target.value) || 0)} />
                                </div>
                                <div>
                                    <Label>Larghezza (mm)</Label>
                                    <Input data-testid="drawer-width" type="number" value={activeThermal.width_mm} onChange={e => updateThermal('width_mm', parseFloat(e.target.value) || 0)} />
                                </div>
                            </div>
                            <div>
                                <Label>Vetro</Label>
                                <Select value={activeThermal.glass_id} onValueChange={v => updateThermal('glass_id', v)}>
                                    <SelectTrigger data-testid="drawer-glass"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {thermalRef.glass_types?.map(g => <SelectItem key={g.id} value={g.id}>{g.label} (Ug={g.ug})</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Telaio / Profilo</Label>
                                <Select value={activeThermal.frame_id} onValueChange={v => updateThermal('frame_id', v)}>
                                    <SelectTrigger data-testid="drawer-frame"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {thermalRef.frame_types?.map(f => <SelectItem key={f.id} value={f.id}>{f.label} (Uf={f.uf})</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Canalina Distanziale</Label>
                                <Select value={activeThermal.spacer_id} onValueChange={v => updateThermal('spacer_id', v)}>
                                    <SelectTrigger data-testid="drawer-spacer"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {thermalRef.spacer_types?.map(s => <SelectItem key={s.id} value={s.id}>{s.label} (Psi={s.psi})</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Zona Climatica</Label>
                                <Select value={activeThermal.zone} onValueChange={v => updateThermal('zone', v)}>
                                    <SelectTrigger data-testid="drawer-zone"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {ZONES.map(z => <SelectItem key={z} value={z}>Zona {z}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Separator />
                            <div className="flex gap-2">
                                <Button onClick={() => setDrawerOpen(false)} className="flex-1 bg-[#0055FF] text-white hover:bg-[#0044CC]">Conferma</Button>
                                <Button variant="outline" onClick={() => { if (activeLineIdx !== null) removeThermal(activeLineIdx); setDrawerOpen(false); }} className="text-red-500 border-red-300 hover:bg-red-50">Rimuovi</Button>
                            </div>
                        </div>
                    )}
                </SheetContent>
            </Sheet>
        </DashboardLayout>
    );
}
