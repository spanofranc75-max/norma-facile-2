/**
 * QualitySystemPage — Archivio Documentale Aziendale
 * Storage isolato per manuali 1090, procedure, certificati ISO, template, normative.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest, API_BASE } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
    Upload, Search, FileText, Trash2, Download, FolderOpen,
    BookOpen, ClipboardList, Award, FileCode, Scale, Layers,
    Loader2, X, File, Plus,
} from 'lucide-react';

const CATEGORIES = [
    { key: 'all', label: 'Tutti', icon: Layers },
    { key: 'manuali', label: 'Manuali Qualita', icon: BookOpen },
    { key: 'procedure', label: 'Procedure', icon: ClipboardList },
    { key: 'certificazioni', label: 'Certificazioni', icon: Award },
    { key: 'template', label: 'Template', icon: FileCode },
    { key: 'normative', label: 'Normative', icon: Scale },
    { key: 'altro', label: 'Altro', icon: FolderOpen },
];

const CATEGORY_COLORS = {
    manuali: 'bg-blue-100 text-blue-700 border-blue-200',
    procedure: 'bg-amber-100 text-amber-700 border-amber-200',
    certificazioni: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    template: 'bg-violet-100 text-violet-700 border-violet-200',
    normative: 'bg-rose-100 text-rose-700 border-rose-200',
    altro: 'bg-slate-100 text-slate-600 border-slate-200',
};

const FILE_ICONS = {
    'application/pdf': { color: 'text-red-500', label: 'PDF' },
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { color: 'text-blue-600', label: 'DOCX' },
    'application/msword': { color: 'text-blue-600', label: 'DOC' },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { color: 'text-green-600', label: 'XLSX' },
    'image/png': { color: 'text-purple-500', label: 'PNG' },
    'image/jpeg': { color: 'text-purple-500', label: 'JPG' },
};

function formatFileSize(kb) {
    if (!kb) return '—';
    if (kb < 1024) return `${kb} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
}

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function QualitySystemPage() {
    const [docs, setDocs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeCategory, setActiveCategory] = useState('all');
    const [search, setSearch] = useState('');
    const [showUpload, setShowUpload] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState(null);
    const [deleting, setDeleting] = useState(false);

    // Upload form state
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadTitle, setUploadTitle] = useState('');
    const [uploadCategory, setUploadCategory] = useState('manuali');
    const [uploadTags, setUploadTags] = useState('');

    const fetchDocs = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (activeCategory !== 'all') params.set('category', activeCategory);
            if (search.trim()) params.set('search', search.trim());
            const qs = params.toString();
            const res = await apiRequest(`/company/documents/${qs ? `?${qs}` : ''}`);
            setDocs(res.items || []);
        } catch (e) {
            toast.error('Errore caricamento documenti');
        } finally {
            setLoading(false);
        }
    }, [activeCategory, search]);

    useEffect(() => { fetchDocs(); }, [fetchDocs]);

    const handleUpload = async () => {
        if (!uploadFile) { toast.error('Seleziona un file'); return; }
        if (!uploadTitle.trim()) { toast.error('Inserisci un titolo'); return; }
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', uploadFile);
            formData.append('title', uploadTitle.trim());
            formData.append('category', uploadCategory);
            formData.append('tags', uploadTags);

            const res = await fetch(`${API_BASE}/company/documents/`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Errore upload');
            }
            toast.success('Documento caricato');
            setShowUpload(false);
            resetUploadForm();
            fetchDocs();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUploading(false);
        }
    };

    const handleDownload = async (doc) => {
        try {
            const res = await fetch(`${API_BASE}/company/documents/${doc.doc_id}/download`, {
                credentials: 'include',
            });
            if (!res.ok) throw new Error('Errore download');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = doc.filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            toast.error(e.message);
        }
    };

    const handleDelete = async () => {
        if (!deleteConfirm) return;
        setDeleting(true);
        try {
            await apiRequest(`/company/documents/${deleteConfirm.doc_id}`, { method: 'DELETE' });
            toast.success('Documento eliminato');
            setDeleteConfirm(null);
            fetchDocs();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setDeleting(false);
        }
    };

    const resetUploadForm = () => {
        setUploadFile(null);
        setUploadTitle('');
        setUploadCategory('manuali');
        setUploadTags('');
    };

    const filteredDocs = docs;
    const countByCategory = (key) => {
        if (key === 'all') return docs.length;
        return docs.filter(d => d.category === key).length;
    };

    return (
        <DashboardLayout>
            <div className="space-y-5" data-testid="quality-system-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                        <h1 className="font-sans text-xl font-bold text-[#1E293B]">Documentazione Aziendale</h1>
                        <p className="text-sm text-slate-500 mt-0.5">Archivio manuali, procedure, certificazioni e normative</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                            <Input
                                data-testid="search-docs"
                                placeholder="Cerca documenti..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="pl-8 h-9 w-56 text-sm"
                            />
                        </div>
                        <Button
                            data-testid="btn-upload-doc"
                            onClick={() => setShowUpload(true)}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC] h-9 text-xs"
                        >
                            <Upload className="h-3.5 w-3.5 mr-1.5" /> Carica Documento
                        </Button>
                    </div>
                </div>

                {/* Category Pills */}
                <div className="flex flex-wrap gap-1.5" data-testid="category-tabs">
                    {CATEGORIES.map(cat => {
                        const Icon = cat.icon;
                        const isActive = activeCategory === cat.key;
                        const count = countByCategory(cat.key);
                        return (
                            <button
                                key={cat.key}
                                data-testid={`tab-${cat.key}`}
                                onClick={() => setActiveCategory(cat.key)}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                                    isActive
                                        ? 'bg-[#0055FF] text-white border-[#0055FF]'
                                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                                }`}
                            >
                                <Icon className="h-3 w-3" />
                                {cat.label}
                                {count > 0 && (
                                    <span className={`ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] leading-none ${
                                        isActive ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'
                                    }`}>
                                        {count}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>

                {/* Content */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-6 w-6 animate-spin text-[#0055FF]" />
                    </div>
                ) : filteredDocs.length === 0 ? (
                    <EmptyState category={activeCategory} onUpload={() => setShowUpload(true)} />
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3" data-testid="docs-grid">
                        {filteredDocs.map(doc => (
                            <DocumentCard
                                key={doc.doc_id}
                                doc={doc}
                                onDownload={() => handleDownload(doc)}
                                onDelete={() => setDeleteConfirm(doc)}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Upload Dialog */}
            <Dialog open={showUpload} onOpenChange={(v) => { if (!v) resetUploadForm(); setShowUpload(v); }}>
                <DialogContent className="max-w-md" data-testid="upload-dialog">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Upload className="h-5 w-5 text-[#0055FF]" /> Carica Documento
                        </DialogTitle>
                        <DialogDescription className="text-xs text-slate-500">
                            Seleziona un file e compila i dettagli per aggiungerlo all'archivio.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 mt-2">
                        {/* File Drop */}
                        <div
                            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                                uploadFile ? 'border-[#0055FF] bg-blue-50/50' : 'border-slate-200 hover:border-slate-300'
                            }`}
                            onClick={() => document.getElementById('file-input-company-doc')?.click()}
                            data-testid="drop-zone"
                        >
                            <input
                                id="file-input-company-doc"
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
                                    <span className="text-sm font-medium text-[#1E293B] truncate max-w-[250px]">{uploadFile.name}</span>
                                    <button onClick={e => { e.stopPropagation(); setUploadFile(null); }} className="text-slate-400 hover:text-red-500">
                                        <X className="h-4 w-4" />
                                    </button>
                                </div>
                            ) : (
                                <div>
                                    <Plus className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                                    <p className="text-sm text-slate-500">Clicca per selezionare un file</p>
                                    <p className="text-[10px] text-slate-400 mt-1">PDF, DOC, XLS, DWG, immagini (max 50 MB)</p>
                                </div>
                            )}
                        </div>

                        <div>
                            <Label className="text-xs">Titolo *</Label>
                            <Input
                                data-testid="input-upload-title"
                                value={uploadTitle}
                                onChange={e => setUploadTitle(e.target.value)}
                                placeholder="es. Manuale Qualita EN 1090-1"
                                className="h-9 text-sm"
                            />
                        </div>

                        <div>
                            <Label className="text-xs">Categoria</Label>
                            <Select value={uploadCategory} onValueChange={setUploadCategory}>
                                <SelectTrigger data-testid="select-upload-category" className="h-9 text-sm">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="manuali">Manuali Qualita</SelectItem>
                                    <SelectItem value="procedure">Procedure</SelectItem>
                                    <SelectItem value="certificazioni">Certificazioni</SelectItem>
                                    <SelectItem value="template">Template</SelectItem>
                                    <SelectItem value="normative">Normative</SelectItem>
                                    <SelectItem value="altro">Altro</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label className="text-xs">Tag (separati da virgola)</Label>
                            <Input
                                data-testid="input-upload-tags"
                                value={uploadTags}
                                onChange={e => setUploadTags(e.target.value)}
                                placeholder="es. EN 1090, ISO 9001, saldatura"
                                className="h-9 text-sm"
                            />
                        </div>
                    </div>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => { resetUploadForm(); setShowUpload(false); }} className="text-xs h-9">
                            Annulla
                        </Button>
                        <Button
                            data-testid="btn-confirm-upload"
                            onClick={handleUpload}
                            disabled={uploading || !uploadFile || !uploadTitle.trim()}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs h-9"
                        >
                            {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Upload className="h-3.5 w-3.5 mr-1.5" />}
                            {uploading ? 'Caricamento...' : 'Carica'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirm Dialog */}
            <Dialog open={!!deleteConfirm} onOpenChange={v => { if (!v) setDeleteConfirm(null); }}>
                <DialogContent className="max-w-sm" data-testid="delete-dialog">
                    <DialogHeader>
                        <DialogTitle className="text-red-600">Elimina Documento</DialogTitle>
                        <DialogDescription className="sr-only">Conferma eliminazione documento</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-slate-600 mt-2">
                        Sei sicuro di voler eliminare <strong>{deleteConfirm?.title}</strong>? L'azione non e reversibile.
                    </p>
                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setDeleteConfirm(null)} className="text-xs h-9">Annulla</Button>
                        <Button
                            data-testid="btn-confirm-delete"
                            onClick={handleDelete}
                            disabled={deleting}
                            className="bg-red-600 text-white hover:bg-red-500 text-xs h-9"
                        >
                            {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Trash2 className="h-3.5 w-3.5 mr-1.5" />}
                            Elimina
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}

/* ── Document Card ── */
function DocumentCard({ doc, onDownload, onDelete }) {
    const fileInfo = FILE_ICONS[doc.content_type] || { color: 'text-slate-500', label: doc.filename?.split('.').pop()?.toUpperCase() || 'FILE' };
    const catColor = CATEGORY_COLORS[doc.category] || CATEGORY_COLORS.altro;
    const catLabel = CATEGORIES.find(c => c.key === doc.category)?.label || doc.category;

    return (
        <Card
            className="border-gray-200 hover:border-slate-300 hover:shadow-sm transition-all group"
            data-testid={`doc-card-${doc.doc_id}`}
        >
            <CardContent className="p-4">
                <div className="flex items-start gap-3">
                    {/* File icon */}
                    <div className={`flex-shrink-0 w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center ${fileInfo.color}`}>
                        <FileText className="h-5 w-5" />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-[#1E293B] truncate" title={doc.title}>
                            {doc.title}
                        </h3>
                        <div className="flex items-center gap-2 mt-1">
                            <Badge className={`text-[9px] px-1.5 py-0 border ${catColor}`}>
                                {catLabel}
                            </Badge>
                            <span className="text-[10px] text-slate-400 font-mono">{fileInfo.label}</span>
                            <span className="text-[10px] text-slate-400">{formatFileSize(doc.size_kb)}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                            <span className="text-[10px] text-slate-400">{formatDate(doc.upload_date)}</span>
                            {doc.uploaded_by && (
                                <span className="text-[10px] text-slate-400 truncate max-w-[120px]">
                                    da {doc.uploaded_by}
                                </span>
                            )}
                        </div>
                        {doc.tags?.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1.5">
                                {doc.tags.map((tag, i) => (
                                    <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            data-testid={`btn-download-${doc.doc_id}`}
                            onClick={onDownload}
                            className="p-1.5 rounded hover:bg-blue-50 text-slate-400 hover:text-[#0055FF] transition-colors"
                            title="Scarica"
                        >
                            <Download className="h-3.5 w-3.5" />
                        </button>
                        <button
                            data-testid={`btn-delete-${doc.doc_id}`}
                            onClick={onDelete}
                            className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
                            title="Elimina"
                        >
                            <Trash2 className="h-3.5 w-3.5" />
                        </button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

/* ── Empty State ── */
function EmptyState({ category, onUpload }) {
    const catInfo = CATEGORIES.find(c => c.key === category);
    const Icon = catInfo?.icon || FolderOpen;
    return (
        <div className="flex flex-col items-center justify-center py-20 text-center" data-testid="empty-state">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                <Icon className="h-7 w-7 text-slate-400" />
            </div>
            <h3 className="text-sm font-semibold text-[#1E293B] mb-1">
                {category === 'all' ? 'Nessun documento caricato' : `Nessun documento in "${catInfo?.label || category}"`}
            </h3>
            <p className="text-xs text-slate-500 mb-4 max-w-xs">
                Carica manuali, procedure, certificazioni e altri documenti aziendali per averli sempre a portata di mano.
            </p>
            <Button onClick={onUpload} className="bg-[#0055FF] text-white hover:bg-[#0044CC] h-9 text-xs">
                <Upload className="h-3.5 w-3.5 mr-1.5" /> Carica il primo documento
            </Button>
        </div>
    );
}
