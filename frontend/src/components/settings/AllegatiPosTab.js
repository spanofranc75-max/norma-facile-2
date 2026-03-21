/**
 * AllegatiPosTab — Allegati Tecnici POS: Rumore, Vibrazioni, MMC.
 * Upload file + toggle "Includi sempre nel POS".
 */
import { useState, useEffect } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../ui/table';
import { toast } from 'sonner';
import { Upload, FileCheck, FileX, Trash2, Download, Loader2, Volume2, Vibrate, Weight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const DOC_ICONS = {
    rumore: Volume2,
    vibrazioni: Vibrate,
    mmc: Weight,
};

const DOC_COLORS = {
    rumore: 'bg-orange-600',
    vibrazioni: 'bg-purple-600',
    mmc: 'bg-cyan-600',
};

export default function AllegatiPosTab() {
    const [allegati, setAllegati] = useState({});
    const [caricati, setCar] = useState(0);
    const [totale, setTot] = useState(0);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(null);

    const load = async () => {
        try {
            const res = await fetch(`${API}/api/company/documents/allegati-pos`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setAllegati(data.allegati || {});
                setCar(data.caricati || 0);
                setTot(data.totale || 0);
            }
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    const handleUpload = async (docType, file) => {
        setUploading(docType);
        try {
            const fd = new FormData();
            fd.append('file', file);
            fd.append('includi_pos', allegati[docType]?.includi_pos !== false ? 'true' : 'false');
            const res = await fetch(`${API}/api/company/documents/allegati-pos/${docType}`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (res.ok) {
                toast.success(`${allegati[docType]?.label || docType} caricato`);
                load();
            } else {
                const d = await res.json().catch(() => ({}));
                toast.error(d.detail || 'Errore upload');
            }
        } catch (e) { toast.error('Errore: ' + e.message); }
        finally { setUploading(null); }
    };

    const handleToggle = async (docType, newVal) => {
        try {
            const res = await fetch(`${API}/api/company/documents/allegati-pos/${docType}`, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ includi_pos: newVal }),
            });
            if (res.ok) {
                toast.success(newVal ? 'Incluso nel POS' : 'Escluso dal POS');
                setAllegati(prev => ({
                    ...prev,
                    [docType]: { ...prev[docType], includi_pos: newVal },
                }));
            } else {
                toast.error('Errore aggiornamento');
            }
        } catch (e) { toast.error(e.message); }
    };

    const handleDelete = async (docType) => {
        if (!window.confirm(`Eliminare ${allegati[docType]?.label}?`)) return;
        try {
            const res = await fetch(`${API}/api/company/documents/allegati-pos/${docType}`, {
                method: 'DELETE', credentials: 'include',
            });
            if (res.ok) { toast.success('Allegato eliminato'); load(); }
            else toast.error('Errore eliminazione');
        } catch (e) { toast.error(e.message); }
    };

    const handleDownload = async (docType) => {
        const docId = allegati[docType]?.doc_id;
        if (!docId) return;
        try {
            const r = await fetch(`${API}/api/company/documents/${docId}/download`, { credentials: 'include' });
            if (!r.ok) { toast.error('Download non disponibile'); return; }
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = allegati[docType]?.filename || 'allegato.pdf';
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;

    const docTypes = ['rumore', 'vibrazioni', 'mmc'];

    return (
        <div className="space-y-4" data-testid="allegati-pos-tab">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                        <Volume2 className="w-5 h-5 text-orange-500" />
                        Allegati Tecnici POS
                    </h3>
                    <p className="text-sm text-slate-500 mt-0.5">
                        Valutazioni specifiche dei rischi. Attiva "Includi nel POS" per inserirli automaticamente nei pacchetti sicurezza.
                    </p>
                </div>
                <Badge data-testid="allegati-counter" className={
                    caricati === totale && totale > 0
                        ? 'bg-emerald-100 text-emerald-700 border border-emerald-200 text-sm px-3 py-1'
                        : 'bg-amber-100 text-amber-700 border border-amber-200 text-sm px-3 py-1'
                }>
                    {caricati}/{totale} caricati
                </Badge>
            </div>

            <div className="border rounded-lg overflow-hidden" data-testid="allegati-table">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-[#1E293B]">
                            <TableHead className="text-white font-semibold w-12 text-center">#</TableHead>
                            <TableHead className="text-white font-semibold">Documento</TableHead>
                            <TableHead className="text-white font-semibold text-center">Stato</TableHead>
                            <TableHead className="text-white font-semibold">File</TableHead>
                            <TableHead className="text-white font-semibold text-center">Includi nel POS</TableHead>
                            <TableHead className="text-white font-semibold text-right">Azioni</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {docTypes.map((dt, idx) => {
                            const d = allegati[dt] || {};
                            const Icon = DOC_ICONS[dt] || Volume2;
                            const color = DOC_COLORS[dt] || 'bg-slate-600';

                            return (
                                <TableRow key={dt} className={`${d.presente ? 'bg-white' : 'bg-slate-50/50'} hover:bg-slate-100/60 transition-colors`} data-testid={`allegato-row-${dt}`}>
                                    <TableCell className="text-center">
                                        <div className={`w-8 h-8 rounded-md flex items-center justify-center text-white mx-auto ${color}`}>
                                            <Icon className="w-4 h-4" />
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="font-semibold text-slate-800 text-sm">{d.label || dt}</div>
                                        <div className="text-xs text-slate-500">{d.desc || ''}</div>
                                    </TableCell>
                                    <TableCell className="text-center">
                                        {d.presente ? (
                                            <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px] gap-1">
                                                <FileCheck className="w-3 h-3" /> Caricato
                                            </Badge>
                                        ) : (
                                            <Badge className="bg-red-100 text-red-600 border border-red-200 text-[10px] gap-1">
                                                <FileX className="w-3 h-3" /> Mancante
                                            </Badge>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        {d.presente ? (
                                            <div className="text-xs">
                                                <div className="font-medium text-slate-700 truncate max-w-[180px]" title={d.filename}>{d.filename}</div>
                                                <div className="text-slate-400">{d.size_kb} KB — {d.upload_date ? new Date(d.upload_date).toLocaleDateString('it-IT') : ''}</div>
                                            </div>
                                        ) : (
                                            <span className="text-xs text-slate-400 italic">Nessun file</span>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-center">
                                        <div className="flex items-center justify-center gap-2">
                                            <Switch
                                                checked={d.includi_pos !== false}
                                                onCheckedChange={(val) => d.presente && handleToggle(dt, val)}
                                                disabled={!d.presente}
                                                data-testid={`toggle-pos-${dt}`}
                                            />
                                            <span className="text-xs text-slate-500">
                                                {d.includi_pos !== false ? 'Si' : 'No'}
                                            </span>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center justify-end gap-1">
                                            <label>
                                                <input type="file" accept=".pdf,.doc,.docx,.png,.jpg" className="hidden"
                                                    onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(dt, f); e.target.value = ''; }}
                                                    data-testid={`file-input-pos-${dt}`} />
                                                <Button variant="outline" size="sm" className="h-8 text-xs px-2 gap-1"
                                                    disabled={uploading === dt} asChild>
                                                    <span>
                                                        {uploading === dt
                                                            ? <Loader2 className="w-3 h-3 animate-spin" />
                                                            : <Upload className="w-3 h-3" />}
                                                        {d.presente ? 'Aggiorna' : 'Carica'}
                                                    </span>
                                                </Button>
                                            </label>
                                            {d.presente && (
                                                <>
                                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                                        onClick={() => handleDownload(dt)} data-testid={`download-pos-${dt}`}>
                                                        <Download className="w-3.5 h-3.5" />
                                                    </Button>
                                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                                                        onClick={() => handleDelete(dt)} data-testid={`delete-pos-${dt}`}>
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </Button>
                                                </>
                                            )}
                                        </div>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </div>

            <div className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-3">
                I documenti con "Includi nel POS" attivo verranno automaticamente inseriti nella cartella <strong>05_ALLEGATI_POS</strong> del pacchetto sicurezza di ogni commessa.
            </div>
        </div>
    );
}
