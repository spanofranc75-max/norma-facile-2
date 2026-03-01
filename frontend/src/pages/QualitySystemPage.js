/**
 * QualitySystemPage — Documentazione Aziendale con Versioning
 * DMS isolato per manuali, procedure, certificazioni, template, normative, organigramma.
 * Stile coerente con Design System Norma Facile 2.0 (Shadcn Table, Card toolbar).
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest, API_BASE } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import {
    Upload, Search, FileText, Trash2, Download, FolderOpen,
    Loader2, X, File, Plus, History, RefreshCw,
} from 'lucide-react';

/* ── Constants ── */
const CATEGORIE = [
    { value: 'manuali', label: 'Manuali Qualita' },
    { value: 'procedure', label: 'Procedure' },
    { value: 'certificazioni', label: 'Certificazioni' },
    { value: 'template', label: 'Template' },
    { value: 'normative', label: 'Normative' },
    { value: 'organigramma', label: 'Organigramma' },
    { value: 'altro', label: 'Altro' },
];

const CAT_COLORS = {
    manuali: 'bg-blue-100 text-blue-800',
    procedure: 'bg-amber-100 text-amber-800',
    certificazioni: 'bg-emerald-100 text-emerald-800',
    template: 'bg-violet-100 text-violet-800',
    normative: 'bg-rose-100 text-rose-800',
    organigramma: 'bg-cyan-100 text-cyan-800',
    altro: 'bg-slate-100 text-slate-700',
};

function formatSize(kb) {
    if (!kb) return '--';
    if (kb < 1024) return `${kb} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
}

function formatDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fileExt(filename) {
    return (filename || '').split('.').pop()?.toUpperCase() || 'FILE';
}

/* ═══════════════════════════════════════════════════════ */

export default function QualitySystemPage() {
    const [docs, setDocs] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');
    const [filterCat, setFilterCat] = useState('');

    // Dialogs
    const [showUpload, setShowUpload] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [revisionTarget, setRevisionTarget] = useState(null);
    const [revisionUploading, setRevisionUploading] = useState(false);
    const [revisionFile, setRevisionFile] = useState(null);
    const [historyTarget, setHistoryTarget] = useState(null);
    const [historyData, setHistoryData] = useState(null);
    const [historyLoading, setHistoryLoading] = useState(false);

    // Upload form
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadTitle, setUploadTitle] = useState('');
    const [uploadCategory, setUploadCategory] = useState('manuali');
    const [uploadTags, setUploadTags] = useState('');

    /* ── Data fetch ── */
    const fetchDocs = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterCat) params.set('category', filterCat);
            if (searchQ.trim()) params.set('search', searchQ.trim());
            const qs = params.toString();
            const res = await apiRequest(`/company/documents/${qs ? `?${qs}` : ''}`);
            setDocs(res.items || []);
            setTotal(res.total || 0);
        } catch {
            toast.error('Errore caricamento documenti');
        } finally {
            setLoading(false);
        }
    }, [filterCat, searchQ]);

    useEffect(() => {
        const timer = setTimeout(fetchDocs, 300);
        return () => clearTimeout(timer);
    }, [fetchDocs]);

    /* ── Upload new doc ── */
    const handleUpload = async () => {
        if (!uploadFile) { toast.error('Seleziona un file'); return; }
        if (!uploadTitle.trim()) { toast.error('Inserisci un titolo'); return; }
        setUploading(true);
        try {
            const fd = new FormData();
            fd.append('file', uploadFile);
            fd.append('title', uploadTitle.trim());
            fd.append('category', uploadCategory);
            fd.append('tags', uploadTags);
            const res = await fetch(`${API_BASE}/company/documents/`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Errore upload');
            }
            toast.success('Documento caricato');
            closeUpload();
            fetchDocs();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUploading(false);
        }
    };

    /* ── Upload revision ── */
    const handleRevisionUpload = async () => {
        if (!revisionFile || !revisionTarget) return;
        setRevisionUploading(true);
        try {
            const fd = new FormData();
            fd.append('file', revisionFile);
            fd.append('note', '');
            const res = await fetch(`${API_BASE}/company/documents/${revisionTarget.doc_id}/revision`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Errore upload revisione');
            }
            const data = await res.json();
            toast.success(`Revisione v${data.version} caricata`);
            setRevisionTarget(null);
            setRevisionFile(null);
            fetchDocs();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setRevisionUploading(false);
        }
    };

    /* ── Version history ── */
    const openHistory = async (doc) => {
        setHistoryTarget(doc);
        setHistoryLoading(true);
        setHistoryData(null);
        try {
            const data = await apiRequest(`/company/documents/${doc.doc_id}/versions`);
            setHistoryData(data);
        } catch {
            toast.error('Errore caricamento storico');
            setHistoryTarget(null);
        } finally {
            setHistoryLoading(false);
        }
    };

    const downloadVersion = async (docId, versionNum, filename) => {
        try {
            const res = await fetch(`${API_BASE}/company/documents/${docId}/versions/${versionNum}/download`, {
                credentials: 'include',
            });
            if (!res.ok) throw new Error('Errore download');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename; a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            toast.error(e.message);
        }
    };

    /* ── Download current ── */
    const handleDownload = async (doc) => {
        try {
            const res = await fetch(`${API_BASE}/company/documents/${doc.doc_id}/download`, { credentials: 'include' });
            if (!res.ok) throw new Error('Errore download');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = doc.filename; a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            toast.error(e.message);
        }
    };

    /* ── Delete ── */
    const handleDelete = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        try {
            await apiRequest(`/company/documents/${deleteTarget.doc_id}`, { method: 'DELETE' });
            toast.success('Documento eliminato');
            setDeleteTarget(null);
            fetchDocs();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setDeleting(false);
        }
    };

    const closeUpload = () => {
        setShowUpload(false);
        setUploadFile(null);
        setUploadTitle('');
        setUploadCategory('manuali');
        setUploadTags('');
    };

    /* ═══════════════════════════════ RENDER ═══════════════════════════════ */
    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="quality-system-page">
                {/* ── Header ── */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900">
                            Documentazione Aziendale
                        </h1>
                        <p className="text-slate-600">
                            {total} document{total !== 1 ? 'i' : 'o'} in archivio
                        </p>
                    </div>
                    <Button
                        data-testid="btn-upload-doc"
                        onClick={() => setShowUpload(true)}
                        className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                    >
                        <Upload className="h-4 w-4 mr-2" />
                        Carica Documento
                    </Button>
                </div>

                {/* ── Toolbar Filtri ── */}
                <Card className="border-gray-200">
                    <CardContent className="pt-6">
                        <div className="flex gap-4">
                            <div className="relative flex-1 max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input
                                    data-testid="search-docs"
                                    placeholder="Cerca per nome, tag, tipo file..."
                                    value={searchQ}
                                    onChange={e => setSearchQ(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                            <Select
                                value={filterCat || '__all__'}
                                onValueChange={v => setFilterCat(v === '__all__' ? '' : v)}
                            >
                                <SelectTrigger data-testid="filter-category" className="w-[200px]">
                                    <SelectValue placeholder="Categoria" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">Tutte le categorie</SelectItem>
                                    {CATEGORIE.map(c => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* ── Tabella Documenti ── */}
                <Card className="border-gray-200">
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-[#1E293B]">
                                    <TableHead className="text-white font-semibold">Nome Documento</TableHead>
                                    <TableHead className="text-white font-semibold">Categoria</TableHead>
                                    <TableHead className="text-white font-semibold">Data</TableHead>
                                    <TableHead className="text-white font-semibold">Tipo</TableHead>
                                    <TableHead className="text-white font-semibold text-center">Rev.</TableHead>
                                    <TableHead className="text-white font-semibold text-right">Dimensione</TableHead>
                                    <TableHead className="w-[140px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center py-12">
                                            <div className="w-6 h-6 loading-spinner mx-auto" />
                                        </TableCell>
                                    </TableRow>
                                ) : docs.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center py-16">
                                            <div className="flex flex-col items-center">
                                                <FileText className="h-10 w-10 text-slate-300 mb-3" />
                                                <p className="text-sm font-medium text-slate-500">Nessun documento trovato</p>
                                                <p className="text-xs text-slate-400 mt-1">
                                                    {searchQ || filterCat
                                                        ? 'Prova a modificare i filtri di ricerca'
                                                        : 'Carica il primo documento per iniziare'}
                                                </p>
                                                {!searchQ && !filterCat && (
                                                    <Button
                                                        data-testid="btn-empty-upload"
                                                        onClick={() => setShowUpload(true)}
                                                        className="mt-4 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                                        size="sm"
                                                    >
                                                        <Upload className="h-3.5 w-3.5 mr-1.5" />
                                                        Carica Documento
                                                    </Button>
                                                )}
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    docs.map(doc => (
                                        <DocRow
                                            key={doc.doc_id}
                                            doc={doc}
                                            onDownload={() => handleDownload(doc)}
                                            onDelete={() => setDeleteTarget(doc)}
                                            onRevision={() => { setRevisionTarget(doc); setRevisionFile(null); }}
                                            onHistory={() => openHistory(doc)}
                                        />
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            {/* ══════ Upload Dialog ══════ */}
            <Dialog open={showUpload} onOpenChange={v => { if (!v) closeUpload(); else setShowUpload(true); }}>
                <DialogContent className="max-w-md" data-testid="upload-dialog">
                    <DialogHeader>
                        <DialogTitle>Carica Documento</DialogTitle>
                        <DialogDescription>Seleziona un file e compila i dettagli.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 mt-2">
                        <DropZone
                            file={uploadFile}
                            onFileChange={f => { setUploadFile(f); if (f && !uploadTitle) setUploadTitle(f.name.replace(/\.[^.]+$/, '')); }}
                            onClear={() => setUploadFile(null)}
                            inputId="cdoc-file-input"
                        />
                        <div>
                            <Label className="text-xs font-medium">Titolo *</Label>
                            <Input
                                data-testid="input-upload-title"
                                value={uploadTitle}
                                onChange={e => setUploadTitle(e.target.value)}
                                placeholder="es. Manuale Qualita EN 1090-1"
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Categoria</Label>
                            <Select value={uploadCategory} onValueChange={setUploadCategory}>
                                <SelectTrigger data-testid="select-upload-category" className="mt-1">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {CATEGORIE.map(c => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs font-medium">Tag (separati da virgola)</Label>
                            <Input
                                data-testid="input-upload-tags"
                                value={uploadTags}
                                onChange={e => setUploadTags(e.target.value)}
                                placeholder="es. EN 1090, ISO 9001, saldatura"
                                className="mt-1"
                            />
                        </div>
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={closeUpload}>Annulla</Button>
                        <Button
                            data-testid="btn-confirm-upload"
                            onClick={handleUpload}
                            disabled={uploading || !uploadFile || !uploadTitle.trim()}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            {uploading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
                            {uploading ? 'Caricamento...' : 'Carica'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Revision Upload Dialog ══════ */}
            <Dialog open={!!revisionTarget} onOpenChange={v => { if (!v) { setRevisionTarget(null); setRevisionFile(null); } }}>
                <DialogContent className="max-w-md" data-testid="revision-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <RefreshCw className="h-5 w-5 text-[#0055FF]" />
                            Nuova Revisione
                        </DialogTitle>
                        <DialogDescription>
                            Carica una nuova versione di <strong>{revisionTarget?.title}</strong>.
                            La versione corrente (v{revisionTarget?.version}) viene archiviata automaticamente.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="mt-2">
                        <DropZone
                            file={revisionFile}
                            onFileChange={setRevisionFile}
                            onClear={() => setRevisionFile(null)}
                            inputId="revision-file-input"
                        />
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => { setRevisionTarget(null); setRevisionFile(null); }}>Annulla</Button>
                        <Button
                            data-testid="btn-confirm-revision"
                            onClick={handleRevisionUpload}
                            disabled={revisionUploading || !revisionFile}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            {revisionUploading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                            {revisionUploading ? 'Caricamento...' : 'Carica Revisione'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ══════ Version History Dialog ══════ */}
            <Dialog open={!!historyTarget} onOpenChange={v => { if (!v) { setHistoryTarget(null); setHistoryData(null); } }}>
                <DialogContent className="max-w-lg" data-testid="history-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <History className="h-5 w-5 text-slate-600" />
                            Storico Revisioni
                        </DialogTitle>
                        <DialogDescription>{historyTarget?.title}</DialogDescription>
                    </DialogHeader>
                    <div className="mt-2">
                        {historyLoading ? (
                            <div className="flex justify-center py-8">
                                <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                            </div>
                        ) : historyData?.versions?.length ? (
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-slate-100">
                                        <TableHead className="font-semibold text-slate-700">Versione</TableHead>
                                        <TableHead className="font-semibold text-slate-700">File</TableHead>
                                        <TableHead className="font-semibold text-slate-700">Data</TableHead>
                                        <TableHead className="font-semibold text-slate-700">Autore</TableHead>
                                        <TableHead className="font-semibold text-slate-700 text-right">Dim.</TableHead>
                                        <TableHead className="w-[50px]"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {historyData.versions.map((v, i) => (
                                        <TableRow key={v.version} className={i === 0 ? 'bg-blue-50/40' : ''}>
                                            <TableCell>
                                                <span className="inline-flex items-center gap-1.5">
                                                    <span className="font-mono font-bold text-[#0055FF]">v{v.version}</span>
                                                    {i === 0 && (
                                                        <Badge className="bg-[#0055FF] text-white text-[9px] px-1.5 py-0">corrente</Badge>
                                                    )}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-sm text-slate-600 truncate max-w-[150px]" title={v.filename}>
                                                {v.filename}
                                            </TableCell>
                                            <TableCell className="text-sm text-slate-600">
                                                {formatDate(v.upload_date)}
                                            </TableCell>
                                            <TableCell className="text-sm text-slate-500 truncate max-w-[100px]">
                                                {v.uploaded_by || '--'}
                                            </TableCell>
                                            <TableCell className="text-right text-sm font-mono text-slate-500">
                                                {formatSize(v.size_kb)}
                                            </TableCell>
                                            <TableCell>
                                                <Button
                                                    variant="ghost" size="sm"
                                                    data-testid={`btn-dl-v${v.version}`}
                                                    onClick={() => downloadVersion(historyData.doc_id, v.version, v.filename)}
                                                    title={`Scarica v${v.version}`}
                                                >
                                                    <Download className="h-4 w-4 text-slate-500" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-6">Nessuna revisione precedente</p>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* ══════ Delete Confirm ══════ */}
            <Dialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Documento</DialogTitle>
                        <DialogDescription>Questa azione non puo essere annullata.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">
                        Sei sicuro di voler eliminare <strong>{deleteTarget?.title}</strong>
                        {deleteTarget?.version_count > 1 && (
                            <span> e tutte le {deleteTarget.version_count - 1} revisioni precedenti</span>
                        )}
                        ?
                    </p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteTarget(null)}>Annulla</Button>
                        <Button
                            data-testid="btn-confirm-delete"
                            onClick={handleDelete}
                            disabled={deleting}
                            variant="destructive"
                        >
                            {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
                            Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}

/* ══════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ══════════════════════════════════════════════════════════════ */

function DocRow({ doc, onDownload, onDelete, onRevision, onHistory }) {
    const ext = fileExt(doc.filename);
    const catLabel = CATEGORIE.find(c => c.value === doc.category)?.label || doc.category;
    const catColor = CAT_COLORS[doc.category] || CAT_COLORS.altro;
    const hasMultipleVersions = (doc.version_count || 1) > 1;

    return (
        <TableRow data-testid={`doc-row-${doc.doc_id}`} className="hover:bg-slate-50">
            <TableCell>
                <div className="flex items-center gap-2.5">
                    <div className="flex-shrink-0 w-8 h-8 rounded bg-slate-100 flex items-center justify-center">
                        <FileText className="h-4 w-4 text-slate-500" />
                    </div>
                    <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate max-w-[300px]" title={doc.title}>
                            {doc.title}
                        </p>
                        {doc.tags?.length > 0 && (
                            <div className="flex gap-1 mt-0.5">
                                {doc.tags.slice(0, 3).map((t, i) => (
                                    <span key={i} className="text-[10px] px-1.5 py-0 rounded bg-slate-100 text-slate-500">{t}</span>
                                ))}
                                {doc.tags.length > 3 && (
                                    <span className="text-[10px] text-slate-400">+{doc.tags.length - 3}</span>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </TableCell>
            <TableCell>
                <Badge className={catColor}>{catLabel}</Badge>
            </TableCell>
            <TableCell className="text-slate-600 text-sm">{formatDate(doc.upload_date)}</TableCell>
            <TableCell>
                <span className="text-xs font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{ext}</span>
            </TableCell>
            <TableCell className="text-center">
                <button
                    data-testid={`btn-version-${doc.doc_id}`}
                    onClick={hasMultipleVersions ? onHistory : undefined}
                    className={`inline-flex items-center gap-1 text-xs font-mono font-bold px-2 py-0.5 rounded-full transition-colors ${
                        hasMultipleVersions
                            ? 'bg-[#0055FF]/10 text-[#0055FF] hover:bg-[#0055FF]/20 cursor-pointer'
                            : 'bg-slate-100 text-slate-500'
                    }`}
                    title={hasMultipleVersions ? 'Vedi storico revisioni' : `Versione ${doc.version}`}
                >
                    v{doc.version}
                    {hasMultipleVersions && <History className="h-3 w-3" />}
                </button>
            </TableCell>
            <TableCell className="text-right font-mono text-sm text-slate-600">{formatSize(doc.size_kb)}</TableCell>
            <TableCell>
                <div className="flex gap-0.5 justify-end">
                    <Button
                        variant="ghost" size="sm"
                        data-testid={`btn-revision-${doc.doc_id}`}
                        onClick={onRevision}
                        title="Carica nuova revisione"
                    >
                        <RefreshCw className="h-4 w-4 text-slate-500" />
                    </Button>
                    <Button
                        variant="ghost" size="sm"
                        data-testid={`btn-download-${doc.doc_id}`}
                        onClick={onDownload}
                        title="Scarica"
                    >
                        <Download className="h-4 w-4 text-slate-500" />
                    </Button>
                    <Button
                        variant="ghost" size="sm"
                        data-testid={`btn-delete-${doc.doc_id}`}
                        onClick={onDelete}
                        title="Elimina"
                    >
                        <Trash2 className="h-4 w-4 text-slate-500 hover:text-red-500" />
                    </Button>
                </div>
            </TableCell>
        </TableRow>
    );
}

function DropZone({ file, onFileChange, onClear, inputId }) {
    return (
        <div
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                file ? 'border-[#0055FF] bg-blue-50/40' : 'border-slate-200 hover:border-slate-300'
            }`}
            onClick={() => document.getElementById(inputId)?.click()}
            data-testid="drop-zone"
        >
            <input
                id={inputId}
                type="file"
                className="hidden"
                onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) onFileChange(f);
                }}
            />
            {file ? (
                <div className="flex items-center justify-center gap-2">
                    <File className="h-5 w-5 text-[#0055FF]" />
                    <span className="text-sm font-medium text-slate-900 truncate max-w-[250px]">{file.name}</span>
                    <button onClick={e => { e.stopPropagation(); onClear(); }} className="text-slate-400 hover:text-red-500">
                        <X className="h-4 w-4" />
                    </button>
                </div>
            ) : (
                <div>
                    <Plus className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">Clicca per selezionare un file</p>
                    <p className="text-xs text-slate-400 mt-1">PDF, DOC, XLS, DWG, immagini (max 50 MB)</p>
                </div>
            )}
        </div>
    );
}
