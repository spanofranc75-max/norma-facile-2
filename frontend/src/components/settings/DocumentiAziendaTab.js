/**
 * DocumentiAziendaTab — Checklist CIMS: DURC, Visura, White List, Patente a Crediti, DVR.
 * Tabella professionale con gestione scadenze e alert < 15 giorni.
 */
import { useState, useEffect } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../ui/table';
import { toast } from 'sonner';
import { Upload, FileCheck, FileX, Trash2, Download, Shield, Loader2, AlertTriangle, Clock, CheckCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function ExpiryBadge({ data }) {
    if (!data?.presente) return null;
    if (!data.scadenza) return <span className="text-xs text-slate-400 italic">Non impostata</span>;
    if (data.is_expired) {
        return (
            <Badge className="bg-red-100 text-red-700 border border-red-200 text-[10px] gap-1">
                <AlertTriangle className="w-3 h-3" /> Scaduto
            </Badge>
        );
    }
    if (data.is_expiring) {
        return (
            <Badge className="bg-red-50 text-red-600 border border-red-200 text-[10px] gap-1 animate-pulse">
                <Clock className="w-3 h-3" /> {data.days_to_expiry}gg
            </Badge>
        );
    }
    if (data.days_to_expiry !== null && data.days_to_expiry <= 30) {
        return (
            <Badge className="bg-amber-50 text-amber-700 border border-amber-200 text-[10px] gap-1">
                <Clock className="w-3 h-3" /> {data.days_to_expiry}gg
            </Badge>
        );
    }
    return (
        <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] gap-1">
            <CheckCircle className="w-3 h-3" /> Valido
        </Badge>
    );
}

function StatusBadge({ presente }) {
    if (presente) {
        return (
            <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px] gap-1">
                <FileCheck className="w-3 h-3" /> Caricato
            </Badge>
        );
    }
    return (
        <Badge className="bg-red-100 text-red-600 border border-red-200 text-[10px] gap-1">
            <FileX className="w-3 h-3" /> Mancante
        </Badge>
    );
}

const DOC_META = {
    durc: { num: '01', color: 'bg-blue-600' },
    visura: { num: '02', color: 'bg-indigo-600' },
    white_list: { num: '03', color: 'bg-teal-600' },
    patente_crediti: { num: '04', color: 'bg-amber-600' },
    dvr: { num: '05', color: 'bg-rose-600' },
};

export default function DocumentiAziendaTab() {
    const [docs, setDocs] = useState({});
    const [completo, setCompleto] = useState(false);
    const [caricati, setCar] = useState(0);
    const [totale, setTot] = useState(0);
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(null);
    const [scadenze, setScadenze] = useState({});

    const load = async () => {
        try {
            const res = await fetch(`${API}/api/company/documents/sicurezza-globali`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setDocs(data.documenti || {});
                setCompleto(data.completo || false);
                setCar(data.caricati || 0);
                setTot(data.totale || 0);
                setAlerts(data.scadenze_alert || []);
                const sc = {};
                for (const [k, v] of Object.entries(data.documenti || {})) {
                    sc[k] = v.scadenza || '';
                }
                setScadenze(sc);
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
            const sc = scadenze[docType];
            if (sc) fd.append('scadenza', sc);
            const res = await fetch(`${API}/api/company/documents/sicurezza-globali/${docType}`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (res.ok) {
                toast.success(`${docs[docType]?.label || docType} caricato con successo`);
                load();
            } else {
                const d = await res.json().catch(() => ({}));
                toast.error(d.detail || 'Errore upload');
            }
        } catch (e) { toast.error('Errore: ' + e.message); }
        finally { setUploading(null); }
    };

    const handleDelete = async (docType) => {
        if (!window.confirm(`Eliminare ${docs[docType]?.label}?`)) return;
        try {
            const res = await fetch(`${API}/api/company/documents/sicurezza-globali/${docType}`, {
                method: 'DELETE', credentials: 'include',
            });
            if (res.ok) { toast.success('Documento eliminato'); load(); }
            else toast.error('Errore eliminazione');
        } catch (e) { toast.error(e.message); }
    };

    const handleDownload = async (docType) => {
        const docId = docs[docType]?.doc_id;
        if (!docId) return;
        try {
            const r = await fetch(`${API}/api/company/documents/${docId}/download`, { credentials: 'include' });
            if (!r.ok) { toast.error('Download non disponibile'); return; }
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = docs[docType]?.filename || 'documento.pdf';
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { toast.error(e.message); }
    };

    if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;

    const docTypes = ['durc', 'visura', 'white_list', 'patente_crediti', 'dvr'];

    return (
        <div className="space-y-4" data-testid="documenti-azienda-tab">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-[#0055FF]" />
                        Checklist Documenti CIMS
                    </h3>
                    <p className="text-sm text-slate-500 mt-0.5">
                        Documenti obbligatori per cantiere. Automaticamente inclusi nei pacchetti sicurezza/POS.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {alerts.length > 0 && (
                        <Badge className="bg-red-100 text-red-700 border border-red-200 gap-1">
                            <AlertTriangle className="w-3 h-3" /> {alerts.length} in scadenza
                        </Badge>
                    )}
                    <Badge data-testid="docs-counter" className={
                        completo
                            ? 'bg-emerald-100 text-emerald-700 border border-emerald-200 text-sm px-3 py-1'
                            : 'bg-amber-100 text-amber-700 border border-amber-200 text-sm px-3 py-1'
                    }>
                        {completo ? 'Completo' : `${caricati}/${totale} caricati`}
                    </Badge>
                </div>
            </div>

            {/* Alert banner for expiring docs */}
            {alerts.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2" data-testid="expiry-alert-banner">
                    <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-red-700">
                        <strong>Attenzione scadenze:</strong>{' '}
                        {alerts.map((a, i) => (
                            <span key={a.doc_type}>
                                {i > 0 && ', '}
                                <strong>{a.label}</strong>
                                {a.is_expired
                                    ? ` (scaduto il ${a.scadenza})`
                                    : ` (scade tra ${a.days_to_expiry} giorni — ${a.scadenza})`
                                }
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Table */}
            <div className="border rounded-lg overflow-hidden" data-testid="docs-table">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-[#1E293B]">
                            <TableHead className="text-white font-semibold w-12 text-center">#</TableHead>
                            <TableHead className="text-white font-semibold">Documento</TableHead>
                            <TableHead className="text-white font-semibold text-center">Stato</TableHead>
                            <TableHead className="text-white font-semibold">File</TableHead>
                            <TableHead className="text-white font-semibold">Data di Scadenza</TableHead>
                            <TableHead className="text-white font-semibold text-center">Validita</TableHead>
                            <TableHead className="text-white font-semibold text-right">Azioni</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {docTypes.map(dt => {
                            const d = docs[dt] || {};
                            const meta = DOC_META[dt] || {};
                            const rowClass = d.is_expired
                                ? 'bg-red-50/60'
                                : d.is_expiring
                                    ? 'bg-amber-50/40'
                                    : d.presente
                                        ? 'bg-white'
                                        : 'bg-slate-50/50';

                            return (
                                <TableRow key={dt} className={`${rowClass} hover:bg-slate-100/60 transition-colors`} data-testid={`doc-row-${dt}`}>
                                    <TableCell className="text-center">
                                        <div className={`w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold text-white mx-auto ${meta.color}`}>
                                            {meta.num}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="font-semibold text-slate-800 text-sm">{d.label || dt}</div>
                                        <div className="text-xs text-slate-500">{d.desc || ''}</div>
                                    </TableCell>
                                    <TableCell className="text-center">
                                        <StatusBadge presente={d.presente} />
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
                                    <TableCell>
                                        <Input
                                            type="date"
                                            value={scadenze[dt] || ''}
                                            onChange={e => setScadenze(prev => ({ ...prev, [dt]: e.target.value }))}
                                            className="h-8 text-xs w-[150px]"
                                            data-testid={`scadenza-${dt}`}
                                        />
                                        {d.scadenza && <div className="text-[10px] text-slate-400 mt-0.5">Attuale: {d.scadenza}</div>}
                                    </TableCell>
                                    <TableCell className="text-center">
                                        <ExpiryBadge data={d} />
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center justify-end gap-1">
                                            <label>
                                                <input type="file" accept=".pdf,.doc,.docx,.png,.jpg" className="hidden"
                                                    onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(dt, f); e.target.value = ''; }}
                                                    data-testid={`file-input-${dt}`} />
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
                                                        onClick={() => handleDownload(dt)} data-testid={`download-${dt}`}>
                                                        <Download className="w-3.5 h-3.5" />
                                                    </Button>
                                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                                                        onClick={() => handleDelete(dt)} data-testid={`delete-${dt}`}>
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

            {/* Footer warnings */}
            {!completo && (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>Documenti mancanti. I pacchetti sicurezza/POS generati per le commesse CIMS saranno incompleti.</span>
                </div>
            )}
        </div>
    );
}
