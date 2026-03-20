/**
 * ArchivioStoricoPage — Esportazione massiva per anno o cliente.
 * Genera ZIP con struttura: /{Anno}/{Cliente}/{Commessa}/
 */
import { useState, useEffect } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import {
    Archive, Download, Calendar, Users, Loader2,
    FolderDown, FileText, Clock,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ArchivioStoricoPage() {
    const [stats, setStats] = useState(null);
    const [exports, setExports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);
    const [selAnno, setSelAnno] = useState('');
    const [selClient, setSelClient] = useState('');

    useEffect(() => {
        (async () => {
            try {
                const [s, e] = await Promise.all([
                    apiRequest('/archivio/stats'),
                    apiRequest('/archivio/exports').catch(() => ({ exports: [] })),
                ]);
                setStats(s);
                setExports(e.exports || []);
            } catch { toast.error('Errore caricamento dati'); }
            finally { setLoading(false); }
        })();
    }, []);

    const handleExport = async () => {
        setExporting(true);
        try {
            const body = {};
            if (selAnno) body.anno = parseInt(selAnno);
            if (selClient) body.client_id = selClient;

            const res = await fetch(`${API}/api/archivio/export`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Export fallito');
            }

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = res.headers.get('Content-Disposition')?.split('filename="')[1]?.replace('"', '') || 'archivio.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            toast.success('Archivio scaricato!');

            // Refresh exports list
            const e = await apiRequest('/archivio/exports').catch(() => ({ exports: [] }));
            setExports(e.exports || []);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setExporting(false);
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="archivio-storico-page">
                {/* Header */}
                <div>
                    <h1 className="font-sans text-2xl font-bold text-slate-900">Archivio Storico</h1>
                    <p className="text-sm text-slate-500 mt-1">Esportazione massiva documenti per anno o cliente</p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4">
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3 text-center">
                            <FileText className="h-8 w-8 text-blue-500 mx-auto mb-1" />
                            <p className="text-2xl font-bold text-slate-800">{stats?.totale_commesse || 0}</p>
                            <p className="text-xs text-slate-500">Commesse totali</p>
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3 text-center">
                            <Calendar className="h-8 w-8 text-emerald-500 mx-auto mb-1" />
                            <p className="text-2xl font-bold text-slate-800">{stats?.anni?.length || 0}</p>
                            <p className="text-xs text-slate-500">Anni disponibili</p>
                        </CardContent>
                    </Card>
                    <Card className="border-gray-200">
                        <CardContent className="pt-4 pb-3 text-center">
                            <Users className="h-8 w-8 text-amber-500 mx-auto mb-1" />
                            <p className="text-2xl font-bold text-slate-800">{stats?.clienti?.length || 0}</p>
                            <p className="text-xs text-slate-500">Clienti</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Export controls */}
                <Card className="border-blue-200 bg-blue-50/30" data-testid="export-controls">
                    <CardHeader className="py-3">
                        <CardTitle className="text-sm flex items-center gap-2">
                            <FolderDown className="h-4 w-4 text-blue-600" /> Esporta Archivio
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <p className="text-xs text-slate-600">
                            Genera un file ZIP con struttura ordinata: Anno / Cliente / Commessa. Include documenti, foto, certificati e diari.
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="text-xs text-slate-500 block mb-1">Filtro per Anno</label>
                                <select value={selAnno} onChange={e => setSelAnno(e.target.value)}
                                    className="w-full border rounded-md px-3 py-2 text-sm bg-white" data-testid="export-anno">
                                    <option value="">Tutti gli anni</option>
                                    {(stats?.anni || []).map(a => (
                                        <option key={a} value={a}>{a}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-slate-500 block mb-1">Filtro per Cliente</label>
                                <select value={selClient} onChange={e => setSelClient(e.target.value)}
                                    className="w-full border rounded-md px-3 py-2 text-sm bg-white" data-testid="export-cliente">
                                    <option value="">Tutti i clienti</option>
                                    {(stats?.clienti || []).map(c => (
                                        <option key={c.client_id} value={c.client_id}>{c.nome}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <Button onClick={handleExport} disabled={exporting}
                            className="w-full bg-blue-600 hover:bg-blue-500" data-testid="btn-export">
                            {exporting ? (
                                <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Generazione in corso...</>
                            ) : (
                                <><Download className="h-4 w-4 mr-2" /> Scarica Archivio ZIP</>
                            )}
                        </Button>
                    </CardContent>
                </Card>

                {/* Export history */}
                {exports.length > 0 && (
                    <Card className="border-gray-200" data-testid="export-history">
                        <CardHeader className="py-3 bg-slate-50 border-b">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <Clock className="h-4 w-4 text-slate-500" /> Esportazioni precedenti
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y max-h-[200px] overflow-y-auto">
                                {exports.map(ex => (
                                    <div key={ex.export_id} className="px-4 py-2.5 flex items-center justify-between text-xs">
                                        <div>
                                            <span className="font-medium text-slate-700">
                                                {ex.anno ? `Anno ${ex.anno}` : 'Tutte le commesse'}
                                            </span>
                                            <span className="text-slate-400 ml-2">— {ex.num_commesse} commesse</span>
                                        </div>
                                        <div className="text-slate-400">
                                            {new Date(ex.created_at).toLocaleDateString('it-IT')} — {(ex.size_bytes / 1024 / 1024).toFixed(1)} MB
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </DashboardLayout>
    );
}
