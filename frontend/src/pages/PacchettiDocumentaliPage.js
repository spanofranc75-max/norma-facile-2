import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import {
    FileInput, Upload, Package, CheckCircle2, AlertTriangle, XCircle,
    Clock, Shield, Eye, Loader2, Plus, Search, Filter, RefreshCw,
    FileText, ChevronRight,
} from 'lucide-react';

const STATUS_CONFIG = {
    attached: { label: 'Presente', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
    missing: { label: 'Mancante', color: 'bg-red-100 text-red-800', icon: XCircle },
    expired: { label: 'Scaduto', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
    in_scadenza: { label: 'In scadenza', color: 'bg-amber-100 text-amber-800', icon: Clock },
    pending: { label: 'Da verificare', color: 'bg-gray-100 text-gray-600', icon: Clock },
    valido: { label: 'Valido', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
    scaduto: { label: 'Scaduto', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
    non_verificato: { label: 'Non verificato', color: 'bg-gray-100 text-gray-600', icon: Eye },
};

const PRIVACY_BADGE = {
    cliente_condivisibile: 'bg-blue-50 text-blue-700',
    interno: 'bg-gray-100 text-gray-600',
    riservato: 'bg-amber-50 text-amber-700',
    sensibile: 'bg-red-50 text-red-700',
};

const ENTITY_LABELS = { azienda: 'Azienda', persona: 'Persona', mezzo: 'Mezzo', cantiere: 'Cantiere' };

// ── Upload Form ──
function UploadForm({ tipiDoc, onUploaded }) {
    const [form, setForm] = useState({ document_type_code: '', entity_type: 'azienda', owner_label: '', title: '', issue_date: '', expiry_date: '', privacy_level: 'cliente_condivisibile', verified: false });
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);

    const handleUpload = async () => {
        if (!form.document_type_code) { toast.error('Seleziona il tipo documento'); return; }
        setUploading(true);
        try {
            const fd = new FormData();
            Object.entries(form).forEach(([k, v]) => fd.append(k, v));
            if (file) fd.append('file', file);
            const API = process.env.REACT_APP_BACKEND_URL;
            const res = await fetch(`${API}/api/documenti`, { method: 'POST', body: fd, credentials: 'include' });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Errore upload');
            const doc = await res.json();
            toast.success(`Documento caricato: ${doc.title}`);
            setForm(f => ({ ...f, title: '', issue_date: '', expiry_date: '', owner_label: '' }));
            setFile(null);
            onUploaded?.();
        } catch (err) { toast.error(err.message); }
        finally { setUploading(false); }
    };

    const selectedTipo = tipiDoc.find(t => t.code === form.document_type_code);

    return (
        <Card className="border-dashed border-2 border-blue-200" data-testid="upload-form">
            <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2"><Upload className="h-4 w-4" /> Carica Documento</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <Label className="text-xs">Tipo documento *</Label>
                        <Select value={form.document_type_code} onValueChange={v => { const t = tipiDoc.find(x => x.code === v); setForm(f => ({ ...f, document_type_code: v, entity_type: t?.entity_type || 'azienda', privacy_level: t?.privacy_level || 'cliente_condivisibile' })); }}>
                            <SelectTrigger data-testid="select-tipo-doc"><SelectValue placeholder="Seleziona tipo..." /></SelectTrigger>
                            <SelectContent>{tipiDoc.map(t => <SelectItem key={t.code} value={t.code}>{t.label} ({ENTITY_LABELS[t.entity_type]})</SelectItem>)}</SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label className="text-xs">Intestatario</Label>
                        <Input placeholder="Nome / Azienda" value={form.owner_label} onChange={e => setForm(f => ({ ...f, owner_label: e.target.value }))} data-testid="input-owner" />
                    </div>
                    <div>
                        <Label className="text-xs">Titolo</Label>
                        <Input placeholder="Titolo documento" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} data-testid="input-title" />
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <div>
                        <Label className="text-xs">Data emissione</Label>
                        <Input type="date" value={form.issue_date} onChange={e => setForm(f => ({ ...f, issue_date: e.target.value }))} data-testid="input-issue-date" />
                    </div>
                    <div>
                        <Label className="text-xs">Data scadenza</Label>
                        <Input type="date" value={form.expiry_date} onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} data-testid="input-expiry-date" />
                    </div>
                    <div>
                        <Label className="text-xs">File</Label>
                        <Input type="file" onChange={e => setFile(e.target.files?.[0] || null)} data-testid="input-file" />
                    </div>
                    <div className="flex items-end">
                        <Button onClick={handleUpload} disabled={uploading} className="bg-[#0055FF] text-white hover:bg-[#0044CC] w-full" data-testid="btn-upload">
                            {uploading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                            Carica
                        </Button>
                    </div>
                </div>
                {selectedTipo && (
                    <div className="flex gap-2 text-xs">
                        <Badge className={PRIVACY_BADGE[selectedTipo.privacy_level] || ''}>{selectedTipo.privacy_level}</Badge>
                        {selectedTipo.has_expiry && <Badge variant="outline">Scade ogni {selectedTipo.validity_days}gg</Badge>}
                        <Badge variant="outline">{ENTITY_LABELS[selectedTipo.entity_type]}</Badge>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ── Document List ──
function DocumentList({ documenti, tipiMap }) {
    if (!documenti.length) return <p className="text-sm text-slate-400 py-8 text-center">Nessun documento in archivio. Carica il primo documento sopra.</p>;
    return (
        <div className="space-y-2" data-testid="documenti-list">
            {documenti.map(d => {
                const sc = STATUS_CONFIG[d.status] || STATUS_CONFIG.pending;
                const Icon = sc.icon;
                const tipo = tipiMap[d.document_type_code];
                return (
                    <div key={d.doc_id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 bg-white hover:border-blue-200 transition-colors" data-testid={`doc-${d.doc_id}`}>
                        <Icon className={`h-4 w-4 flex-shrink-0 ${d.status === 'valido' || d.status === 'attached' ? 'text-emerald-600' : d.status === 'scaduto' || d.status === 'expired' ? 'text-red-500' : 'text-amber-500'}`} />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{d.title || d.file_name || d.document_type_code}</p>
                            <p className="text-xs text-slate-400">{tipo?.label || d.document_type_code} {d.owner_label ? `- ${d.owner_label}` : ''}</p>
                        </div>
                        <Badge className={`text-[10px] ${sc.color}`}>{sc.label}</Badge>
                        {d.expiry_date && <span className="text-xs text-slate-400">{d.expiry_date.slice(0, 10)}</span>}
                        <Badge className={`text-[10px] ${PRIVACY_BADGE[d.privacy_level] || ''}`}>{d.privacy_level}</Badge>
                    </div>
                );
            })}
        </div>
    );
}

// ── Package Checklist ──
function PackageChecklist({ pack, tipiMap, onVerifica }) {
    if (!pack) return null;
    const s = pack.summary || {};
    const statusColor = pack.status === 'pronto_invio' ? 'border-emerald-300 bg-emerald-50/30' : pack.status === 'incompleto' ? 'border-amber-300 bg-amber-50/30' : 'border-gray-200';

    return (
        <Card className={statusColor} data-testid={`pack-${pack.pack_id}`}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Package className="h-4 w-4" />
                        {pack.label || pack.template_code}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Badge className={pack.status === 'pronto_invio' ? 'bg-emerald-100 text-emerald-800' : pack.status === 'incompleto' ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-600'}>{pack.status}</Badge>
                        <Button size="sm" variant="outline" onClick={() => onVerifica(pack.pack_id)} data-testid={`btn-verifica-${pack.pack_id}`}>
                            <RefreshCw className="h-3 w-3 mr-1" /> Verifica
                        </Button>
                    </div>
                </div>
                {s.total_required > 0 && (
                    <div className="flex gap-3 text-xs mt-2">
                        <span className="text-emerald-700">{s.attached} presenti</span>
                        <span className="text-red-700">{s.missing} mancanti</span>
                        <span className="text-red-600">{s.expired} scaduti</span>
                        <span className="text-amber-600">{s.in_scadenza} in scadenza</span>
                        {s.sensibile > 0 && <span className="text-red-500">{s.sensibile} sensibili</span>}
                    </div>
                )}
            </CardHeader>
            <CardContent>
                <div className="space-y-1">
                    {(pack.items || []).map((item, i) => {
                        const sc = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
                        const Icon = sc.icon;
                        const tipo = tipiMap[item.document_type_code];
                        return (
                            <div key={i} className={`flex items-center gap-2 p-2 rounded text-sm ${item.blocking ? 'bg-red-50' : ''}`}>
                                <Icon className={`h-3.5 w-3.5 flex-shrink-0 ${item.status === 'attached' ? 'text-emerald-600' : item.status === 'missing' || item.status === 'expired' ? 'text-red-500' : 'text-amber-500'}`} />
                                <span className="flex-1">{tipo?.label || item.document_type_code}
                                    {item.entity_label ? <span className="text-slate-400 ml-1">({item.entity_label})</span> : ''}
                                </span>
                                <Badge className={`text-[10px] ${sc.color}`}>{sc.label}</Badge>
                                {item.required && <Badge className="text-[10px] bg-blue-50 text-blue-700">obb.</Badge>}
                                {item.blocking && <Badge className="text-[10px] bg-red-50 text-red-700">blocco</Badge>}
                                {item.document_title && <span className="text-xs text-slate-400 truncate max-w-[150px]">{item.document_title}</span>}
                            </div>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}

// ── Main Page ──
export default function PacchettiDocumentaliPage() {
    const [tab, setTab] = useState('archivio');
    const [tipiDoc, setTipiDoc] = useState([]);
    const [documenti, setDocumenti] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [pacchetti, setPacchetti] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filterEntity, setFilterEntity] = useState('');
    const [filterStatus, setFilterStatus] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    // New package form
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [packLabel, setPackLabel] = useState('');
    const [creating, setCreating] = useState(false);

    const tipiMap = Object.fromEntries(tipiDoc.map(t => [t.code, t]));

    const loadData = useCallback(async () => {
        try {
            const [tipi, docs, tpls, packs] = await Promise.all([
                apiRequest('/documenti/tipi'),
                apiRequest('/documenti'),
                apiRequest('/pacchetti-documentali/templates'),
                apiRequest('/pacchetti-documentali'),
            ]);
            setTipiDoc(tipi);
            setDocumenti(docs);
            setTemplates(tpls);
            setPacchetti(packs);
        } catch (err) { toast.error('Errore caricamento dati'); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleCreatePack = async () => {
        if (!selectedTemplate) { toast.error('Seleziona un template'); return; }
        setCreating(true);
        try {
            const pack = await apiRequest('/pacchetti-documentali', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_code: selectedTemplate, label: packLabel || selectedTemplate }),
            });
            toast.success(`Pacchetto creato: ${pack.pack_id}`);
            setPacchetti(p => [pack, ...p]);
            setSelectedTemplate('');
            setPackLabel('');
            // Auto-verify
            const verified = await apiRequest(`/pacchetti-documentali/${pack.pack_id}/verifica`, { method: 'POST' });
            setPacchetti(p => p.map(pk => pk.pack_id === verified.pack_id ? { ...pk, ...verified } : pk));
        } catch (err) { toast.error(err.message); }
        finally { setCreating(false); }
    };

    const handleVerifica = async (packId) => {
        try {
            const result = await apiRequest(`/pacchetti-documentali/${packId}/verifica`, { method: 'POST' });
            setPacchetti(p => p.map(pk => pk.pack_id === result.pack_id ? { ...pk, ...result } : pk));
            toast.success('Verifica completata');
        } catch (err) { toast.error(err.message); }
    };

    // Filter documents
    const filteredDocs = documenti.filter(d => {
        if (filterEntity && d.entity_type !== filterEntity) return false;
        if (filterStatus && d.status !== filterStatus) return false;
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            return (d.title || '').toLowerCase().includes(q) ||
                   (d.owner_label || '').toLowerCase().includes(q) ||
                   (d.document_type_code || '').toLowerCase().includes(q);
        }
        return true;
    });

    if (loading) return <DashboardLayout><div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" /></div></DashboardLayout>;

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="pacchetti-documentali-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Pacchetti Documentali</h1>
                        <p className="text-sm text-slate-500">{documenti.length} documenti in archivio, {pacchetti.length} pacchetti</p>
                    </div>
                </div>

                <Tabs value={tab} onValueChange={setTab}>
                    <TabsList>
                        <TabsTrigger value="archivio" className="gap-2" data-testid="tab-archivio">
                            <FileInput className="h-4 w-4" /> Archivio
                        </TabsTrigger>
                        <TabsTrigger value="pacchetti" className="gap-2" data-testid="tab-pacchetti">
                            <Package className="h-4 w-4" /> Pacchetti
                        </TabsTrigger>
                    </TabsList>

                    {/* ── TAB: Archivio Documenti ── */}
                    <TabsContent value="archivio" className="space-y-4">
                        <UploadForm tipiDoc={tipiDoc} onUploaded={loadData} />
                        <div className="flex items-center gap-3">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input className="pl-9" placeholder="Cerca per titolo, intestatario, tipo..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} data-testid="search-docs" />
                            </div>
                            <Select value={filterEntity} onValueChange={v => setFilterEntity(v === 'all' ? '' : v)}>
                                <SelectTrigger className="w-[150px]" data-testid="filter-entity"><SelectValue placeholder="Entita" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutte</SelectItem>
                                    <SelectItem value="azienda">Azienda</SelectItem>
                                    <SelectItem value="persona">Persona</SelectItem>
                                    <SelectItem value="mezzo">Mezzo</SelectItem>
                                    <SelectItem value="cantiere">Cantiere</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={filterStatus} onValueChange={v => setFilterStatus(v === 'all' ? '' : v)}>
                                <SelectTrigger className="w-[140px]" data-testid="filter-status"><SelectValue placeholder="Stato" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Tutti</SelectItem>
                                    <SelectItem value="valido">Valido</SelectItem>
                                    <SelectItem value="in_scadenza">In scadenza</SelectItem>
                                    <SelectItem value="scaduto">Scaduto</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <DocumentList documenti={filteredDocs} tipiMap={tipiMap} />
                    </TabsContent>

                    {/* ── TAB: Pacchetti ── */}
                    <TabsContent value="pacchetti" className="space-y-4">
                        <Card className="border-dashed border-2 border-violet-200" data-testid="new-pack-form">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-base flex items-center gap-2"><Plus className="h-4 w-4" /> Nuovo Pacchetto</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    <div>
                                        <Label className="text-xs">Template *</Label>
                                        <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                                            <SelectTrigger data-testid="select-template"><SelectValue placeholder="Seleziona template..." /></SelectTrigger>
                                            <SelectContent>{templates.map(t => <SelectItem key={t.code} value={t.code}>{t.label} ({t.rules.length} regole)</SelectItem>)}</SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label className="text-xs">Nome pacchetto</Label>
                                        <Input placeholder="es. Cantiere Milano Nord" value={packLabel} onChange={e => setPackLabel(e.target.value)} data-testid="input-pack-label" />
                                    </div>
                                    <div className="flex items-end">
                                        <Button onClick={handleCreatePack} disabled={creating} className="bg-violet-600 text-white hover:bg-violet-700 w-full" data-testid="btn-crea-pacchetto">
                                            {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Package className="h-4 w-4 mr-2" />}
                                            Crea e Verifica
                                        </Button>
                                    </div>
                                </div>
                                {selectedTemplate && (
                                    <div className="mt-3 text-xs text-slate-500">
                                        {templates.find(t => t.code === selectedTemplate)?.description}
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {pacchetti.length === 0 ? (
                            <p className="text-sm text-slate-400 py-8 text-center">Nessun pacchetto creato. Usa il form sopra per creare il primo.</p>
                        ) : (
                            pacchetti.map(pack => (
                                <PackageChecklist key={pack.pack_id} pack={pack} tipiMap={tipiMap} onVerifica={handleVerifica} />
                            ))
                        )}
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}
