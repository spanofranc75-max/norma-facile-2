/**
 * DocumentiAziendaTab — Gestione documenti aziendali globali (DURC, Visura, White List, Patente a Crediti).
 * Questi documenti sono automaticamente disponibili per ogni pacchetto sicurezza/POS.
 */
import { useState, useEffect } from 'react';
import { apiRequest } from '../../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { toast } from 'sonner';
import { Upload, FileCheck, FileX, Trash2, Calendar, Shield, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const DOC_ICONS = {
    durc: '1',
    visura: '2',
    white_list: '3',
    patente_crediti: '4',
};

function DocCard({ docType, data, onUpload, onDelete, uploading }) {
    const [scadenza, setScadenza] = useState(data?.scadenza || '');

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) onUpload(docType, file, scadenza);
    };

    return (
        <Card className={`border ${data?.presente ? 'border-emerald-700 bg-emerald-950/20' : 'border-zinc-700 bg-zinc-900'}`} data-testid={`doc-card-${docType}`}>
            <CardContent className="pt-4 space-y-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold ${data?.presente ? 'bg-emerald-900/50 text-emerald-400' : 'bg-zinc-800 text-zinc-500'}`}>
                            {DOC_ICONS[docType]}
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-zinc-200">{data?.label || docType}</h3>
                            <p className="text-xs text-zinc-500">{data?.desc || ''}</p>
                        </div>
                    </div>
                    {data?.presente ? (
                        <Badge className="bg-emerald-900/50 text-emerald-300 text-[10px]">
                            <FileCheck className="w-3 h-3 mr-1" /> Caricato
                        </Badge>
                    ) : (
                        <Badge variant="outline" className="border-amber-600 text-amber-400 text-[10px]">
                            <FileX className="w-3 h-3 mr-1" /> Mancante
                        </Badge>
                    )}
                </div>

                {data?.presente && (
                    <div className="text-xs text-zinc-400 space-y-0.5 bg-zinc-800/50 p-2 rounded">
                        <div>File: <span className="text-zinc-300">{data.filename}</span></div>
                        <div>Caricato: <span className="text-zinc-300">{data.upload_date ? new Date(data.upload_date).toLocaleDateString('it-IT') : '-'}</span></div>
                        {data.scadenza && <div>Scadenza: <span className="text-amber-300">{data.scadenza}</span></div>}
                        <div>Dimensione: <span className="text-zinc-300">{data.size_kb} KB</span></div>
                    </div>
                )}

                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 flex-1">
                        <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                        <Input
                            type="date"
                            value={scadenza}
                            onChange={e => setScadenza(e.target.value)}
                            placeholder="Scadenza"
                            className="h-8 text-xs bg-zinc-800 border-zinc-700 flex-1"
                            data-testid={`scadenza-${docType}`}
                        />
                    </div>
                </div>

                <div className="flex gap-2">
                    <label className="flex-1">
                        <input type="file" accept=".pdf,.doc,.docx,.png,.jpg" className="hidden"
                            onChange={handleFileChange} data-testid={`file-input-${docType}`} />
                        <Button variant="outline" size="sm" className="w-full text-xs border-zinc-600 hover:bg-zinc-800"
                            disabled={uploading === docType} asChild>
                            <span>
                                {uploading === docType ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Upload className="w-3 h-3 mr-1" />}
                                {data?.presente ? 'Sostituisci' : 'Carica'}
                            </span>
                        </Button>
                    </label>
                    {data?.presente && (
                        <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300 hover:bg-red-950/30"
                            onClick={() => onDelete(docType)} data-testid={`delete-${docType}`}>
                            <Trash2 className="w-3 h-3" />
                        </Button>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

export default function DocumentiAziendaTab() {
    const [docs, setDocs] = useState({});
    const [completo, setCompleto] = useState(false);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(null);

    const load = async () => {
        try {
            const res = await fetch(`${API}/api/company/documents/sicurezza-globali`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setDocs(data.documenti || {});
                setCompleto(data.completo || false);
            }
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    const handleUpload = async (docType, file, scadenza) => {
        setUploading(docType);
        try {
            const fd = new FormData();
            fd.append('file', file);
            if (scadenza) fd.append('scadenza', scadenza);
            const res = await fetch(`${API}/api/company/documents/sicurezza-globali/${docType}`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (res.ok) {
                toast.success(`${docs[docType]?.label || docType} caricato`);
                load();
            } else {
                const d = await res.json().catch(() => ({}));
                toast.error(d.detail || 'Errore upload');
            }
        } catch (e) { toast.error('Errore: ' + e.message); }
        finally { setUploading(null); }
    };

    const handleDelete = async (docType) => {
        if (!confirm(`Eliminare ${docs[docType]?.label}?`)) return;
        try {
            const res = await fetch(`${API}/api/company/documents/sicurezza-globali/${docType}`, {
                method: 'DELETE', credentials: 'include',
            });
            if (res.ok) { toast.success('Eliminato'); load(); }
            else toast.error('Errore eliminazione');
        } catch (e) { toast.error(e.message); }
    };

    if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-zinc-500" /></div>;

    const docTypes = ['durc', 'visura', 'white_list', 'patente_crediti'];

    return (
        <div className="space-y-4" data-testid="documenti-azienda-tab">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-base font-semibold text-zinc-200 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-indigo-400" />
                        Documenti Azienda — Sicurezza Globale
                    </h3>
                    <p className="text-xs text-zinc-500 mt-0.5">
                        Questi documenti sono automaticamente inclusi in ogni pacchetto sicurezza/POS e richiesta CIMS.
                    </p>
                </div>
                <Badge className={completo ? 'bg-emerald-900/50 text-emerald-300' : 'bg-amber-900/50 text-amber-300'}>
                    {completo ? 'Completo' : `${Object.values(docs).filter(d => d.presente).length}/4 caricati`}
                </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {docTypes.map(dt => (
                    <DocCard
                        key={dt}
                        docType={dt}
                        data={docs[dt]}
                        onUpload={handleUpload}
                        onDelete={handleDelete}
                        uploading={uploading}
                    />
                ))}
            </div>

            {!completo && (
                <div className="text-xs text-amber-400 bg-amber-950/30 border border-amber-800 rounded p-3">
                    Attenzione: alcuni documenti sono mancanti. I pacchetti sicurezza/POS generati saranno incompleti.
                </div>
            )}
        </div>
    );
}
