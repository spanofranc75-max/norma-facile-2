/**
 * QualitySystemPage — Documentazione Aziendale
 * DMS isolato per manuali, procedure, certificazioni, template, normative, organigramma.
 * Stile coerente con Design System Norma Facile 2.0.
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
    Loader2, X, File, Plus,
} from 'lucide-react';

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
    if (!kb) return '—';
    if (kb < 1024) return `${kb} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
}

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fileExt(filename) {
    return (filename || '').split('.').pop()?.toUpperCase() || 'FILE';
}

export default function QualitySystemPage() {
    const [docs, setDocs] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [searchQ, setSearchQ] = useState('');
    const [filterCat, setFilterCat] = useState('');
    const [showUpload, setShowUpload] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);

    // Upload form
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadTitle, setUploadTitle] = useState('');
    const [uploadCategory, setUploadCategory] = useState('manuali');
    const [uploadTags, setUploadTags] = useState('');

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
                                    <TableHead className="text-white font-semibold text-right">Dimensione</TableHead>
                                    <TableHead className="w-[100px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-12">
                                            <div className="w-6 h-6 loading-spinner mx-auto" />
                                        </TableCell>
                                    </TableRow>
                                ) : docs.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-16">
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
                                    docs.map(doc => {
                                        const ext = fileExt(doc.filename);
                                        const catLabel = CATEGORIE.find(c => c.value === doc.category)?.label || doc.category;
                                        const catColor = CAT_COLORS[doc.category] || CAT_COLORS.altro;
                                        return (
                                            <TableRow
                                                key={doc.doc_id}
                                                data-testid={`doc-row-${doc.doc_id}`}
                                                className="hover:bg-slate-50"
                                            >
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
                                                <TableCell className="text-slate-600 text-sm">
                                                    {formatDate(doc.upload_date)}
                                                </TableCell>
                                                <TableCell>
                                                    <span className="text-xs font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                                        {ext}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-sm text-slate-600">
                                                    {formatSize(doc.size_kb)}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1 justify-end">
                                                        <Button
                                                            variant="ghost" size="sm"
                                                            data-testid={`btn-download-${doc.doc_id}`}
                                                            onClick={() => handleDownload(doc)}
                                                            title="Scarica"
                                                        >
                                                            <Download className="h-4 w-4 text-slate-500" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost" size="sm"
                                                            data-testid={`btn-delete-${doc.doc_id}`}
                                                            onClick={() => setDeleteTarget(doc)}
                                                            title="Elimina"
                                                        >
                                                            <Trash2 className="h-4 w-4 text-slate-500 hover:text-red-500" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            {/* ── Upload Dialog ── */}
            <Dialog open={showUpload} onOpenChange={v => { if (!v) closeUpload(); else setShowUpload(true); }}>
                <DialogContent className="max-w-md" data-testid="upload-dialog">
                    <DialogHeader>
                        <DialogTitle>Carica Documento</DialogTitle>
                        <DialogDescription>
                            Seleziona un file e compila i dettagli per aggiungerlo all'archivio.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 mt-2">
                        {/* Drop zone */}
                        <div
                            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                                uploadFile ? 'border-[#0055FF] bg-blue-50/40' : 'border-slate-200 hover:border-slate-300'
                            }`}
                            onClick={() => document.getElementById('cdoc-file-input')?.click()}
                            data-testid="drop-zone"
                        >
                            <input
                                id="cdoc-file-input"
                                type="file"
                                className="hidden"
                                onChange={e => {
                                    const f = e.target.files?.[0];
                                    if (f) {
                                        setUploadFile(f);
                                        if (!uploadTitle) setUploadTitle(f.name.replace(/\.[^.]+$/, ''));
                                    }
                                }}
                            />
                            {uploadFile ? (
                                <div className="flex items-center justify-center gap-2">
                                    <File className="h-5 w-5 text-[#0055FF]" />
                                    <span className="text-sm font-medium text-slate-900 truncate max-w-[250px]">{uploadFile.name}</span>
                                    <button onClick={e => { e.stopPropagation(); setUploadFile(null); }} className="text-slate-400 hover:text-red-500">
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

            {/* ── Delete Confirm ── */}
            <Dialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Documento</DialogTitle>
                        <DialogDescription>Questa azione non puo essere annullata.</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">
                        Sei sicuro di voler eliminare <strong>{deleteTarget?.title}</strong>?
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
