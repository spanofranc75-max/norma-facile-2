import { useState, useEffect } from 'react';
import { apiRequest } from '../../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { HardDrive, Download, Loader2, RefreshCw, UploadCloud, Trash2 } from 'lucide-react';
import { useConfirm } from '../ConfirmProvider';
import {
    AlertDialog,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '../ui/alert-dialog';

const COLLECTION_LABELS = {
    commesse: 'Commesse', preventivi: 'Preventivi', clients: 'Clienti',
    invoices: 'Fatture Emesse', ddt: 'DDT', fpc_projects: 'Progetti FPC',
    gate_certifications: 'Cert. Cancelli', welders: 'Saldatori',
    instruments: 'Strumenti', company_docs: 'Documenti', distinte: 'Distinte',
    rilievi: 'Rilievi', fatture_ricevute: 'Fatture Ricevute',
    consumable_batches: 'Consumabili', project_costs: 'Costi Progetto',
    audit_findings: 'Audit/NC', company_settings: 'Impostazioni',
    catalogo_profili: 'Catalogo Profili', articoli: 'Articoli',
};

const fmtSize = (bytes) => {
    if (!bytes) return '\u2014';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
};

const fmtDate = (d) => {
    if (!d) return '\u2014';
    try { return new Date(d).toLocaleString('it-IT', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
    catch { return d; }
};

export default function BackupTab() {
    const confirm = useConfirm();
    const [lastBackup, setLastBackup] = useState(null);
    const [stats, setStats] = useState(null);
    const [loadingStats, setLoadingStats] = useState(true);
    const [exporting, setExporting] = useState(false);
    const [restoring, setRestoring] = useState(false);
    const [restoreResult, setRestoreResult] = useState(null);
    const [pendingFile, setPendingFile] = useState(null);
    const [showModeDialog, setShowModeDialog] = useState(false);
    const [history, setHistory] = useState([]);
    const [backupProgress, setBackupProgress] = useState('');

    const API = process.env.REACT_APP_BACKEND_URL;

    useEffect(() => {
        (async () => {
            try {
                const [lastRes, statsRes, histRes] = await Promise.all([
                    apiRequest('/admin/backup/last'),
                    apiRequest('/admin/backup/stats'),
                    apiRequest('/admin/backup/history'),
                ]);
                setLastBackup(lastRes.last_backup);
                setStats(statsRes);
                setHistory(histRes?.history || []);
            } catch { /* silent */ }
            finally { setLoadingStats(false); }
        })();
    }, []);

    const handleExport = async () => {
        setExporting(true);
        setBackupProgress('Avvio backup...');
        try {
            const startRes = await apiRequest('/admin/backup/start', { method: 'POST' });
            const backupId = startRes.backup_id;
            let status = 'in_corso';
            let pollData = null;
            while (status === 'in_corso') {
                await new Promise(r => setTimeout(r, 2000));
                pollData = await apiRequest(`/admin/backup/status/${backupId}`);
                status = pollData.status;
                setBackupProgress(pollData.progress || 'In corso...');
            }
            if (status === 'errore') {
                throw new Error(pollData?.error || 'Errore durante il backup');
            }
            setBackupProgress('Download in corso...');
            const dlUrl = `${API}/api/admin/backup/download/${backupId}`;
            const res = await fetch(dlUrl, { credentials: 'include' });
            if (!res.ok) throw new Error('Download fallito');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = pollData?.filename || 'backup_normafacile.json';
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`Backup completato: ${pollData?.total_records || 0} record`);
            const [lastRes, histRes] = await Promise.all([
                apiRequest('/admin/backup/last'),
                apiRequest('/admin/backup/history'),
            ]);
            setLastBackup(lastRes.last_backup);
            setHistory(histRes?.history || []);
        } catch (e) {
            toast.error(e.message || 'Errore backup');
        }
        finally {
            setExporting(false);
            setBackupProgress('');
        }
    };

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        setPendingFile(file);
        setShowModeDialog(true);
    };

    const executeRestore = async (mode) => {
        setShowModeDialog(false);
        const file = pendingFile;
        setPendingFile(null);
        if (!file) return;

        if (mode === 'wipe') {
            const ok = await confirm(
                'ATTENZIONE CRITICA: Scegliendo "Sostituzione Totale", TUTTI i dati attuali verranno CANCELLATI prima dell\'importazione.\n\nQuesta operazione e IRREVERSIBILE.\n\nSei assolutamente sicuro?',
                'Conferma Sostituzione Totale'
            );
            if (!ok) return;
        }

        setRestoring(true);
        setRestoreResult(null);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('mode', mode);
            const res = await fetch(`${API}/api/admin/backup/restore`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            const rawText = await res.text();
            let data;
            try {
                data = JSON.parse(rawText);
            } catch {
                throw new Error(res.ok ? 'Risposta non valida dal server' : `Errore ${res.status}: ${rawText.substring(0, 200)}`);
            }
            if (!res.ok) throw new Error(data.detail || 'Errore restore');
            setRestoreResult(data);
            toast.success(data.message);
            const [lastRes, statsRes] = await Promise.all([
                apiRequest('/admin/backup/last'),
                apiRequest('/admin/backup/stats'),
            ]);
            setLastBackup(lastRes.last_backup);
            setStats(statsRes);
        } catch (err) { toast.error(err.message); }
        finally { setRestoring(false); }
    };

    const cancelRestore = () => {
        setShowModeDialog(false);
        setPendingFile(null);
    };

    return (
        <>
        <Card className="border-gray-200">
            <CardHeader className="bg-slate-800 border-b border-gray-200 rounded-t-lg">
                <CardTitle className="text-white flex items-center gap-2">
                    <HardDrive className="h-5 w-5" /> Backup & Restore Dati
                </CardTitle>
                <CardDescription className="text-slate-300">
                    Scarica una copia completa dei dati aziendali o ripristina da un backup precedente
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {/* Export Section */}
                <div className="border border-emerald-200 bg-emerald-50/30 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-sm font-bold text-emerald-800 flex items-center gap-1.5">
                                <Download className="h-4 w-4" /> Esporta Backup
                            </h3>
                            <p className="text-xs text-emerald-600 mt-0.5">
                                Scarica un file JSON con tutti i dati: commesse, clienti, preventivi, certificazioni, fatture e altro.
                            </p>
                        </div>
                    </div>

                    {lastBackup && (
                        <div className="bg-white border border-emerald-200 rounded-lg p-3">
                            <p className="text-xs text-slate-500">Ultimo backup: <strong className="text-slate-700">{fmtDate(lastBackup.date)}</strong></p>
                            <p className="text-xs text-slate-400 mt-0.5">
                                {lastBackup.total_records} record — {fmtSize(lastBackup.size_bytes)}
                            </p>
                        </div>
                    )}

                    {!loadingStats && stats && (
                        <div>
                            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Dati Attuali ({stats.total} record)</p>
                            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-1.5">
                                {Object.entries(stats.stats || {}).filter(([, v]) => v > 0).map(([k, v]) => (
                                    <div key={k} className="bg-white border rounded px-2 py-1.5 text-center">
                                        <p className="text-sm font-bold text-[#1E293B]">{v}</p>
                                        <p className="text-[9px] text-slate-400 leading-tight">{COLLECTION_LABELS[k] || k}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    {loadingStats && <p className="text-xs text-slate-400 flex items-center gap-1"><RefreshCw className="h-3 w-3 animate-spin" /> Calcolo statistiche...</p>}

                    <Button
                        onClick={handleExport}
                        disabled={exporting}
                        className="w-full bg-emerald-600 hover:bg-emerald-700 text-white h-10"
                        data-testid="btn-export-backup"
                    >
                        {exporting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                        {exporting ? (backupProgress || 'Backup in corso...') : 'Crea Backup'}
                    </Button>
                </div>

                {/* Restore Section */}
                <div className="border border-amber-200 bg-amber-50/30 rounded-lg p-4 space-y-3">
                    <div>
                        <h3 className="text-sm font-bold text-amber-800 flex items-center gap-1.5">
                            <UploadCloud className="h-4 w-4" /> Ripristina da Backup
                        </h3>
                        <p className="text-xs text-amber-600 mt-0.5">
                            Importa dati da un file di backup. Dopo aver selezionato il file, potrai scegliere la modalita di importazione.
                        </p>
                    </div>

                    <label className={`flex items-center justify-center w-full h-10 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                        restoring ? 'border-amber-300 bg-amber-100' : 'border-amber-300 hover:border-amber-400 hover:bg-amber-50'
                    }`}>
                        <input type="file" accept=".json" onChange={handleFileSelect} disabled={restoring} className="hidden" data-testid="input-restore-file" />
                        {restoring ? (
                            <span className="flex items-center gap-2 text-xs text-amber-700"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Ripristino in corso...</span>
                        ) : (
                            <span className="flex items-center gap-2 text-xs text-amber-700"><UploadCloud className="h-3.5 w-3.5" /> Seleziona file backup (.json)</span>
                        )}
                    </label>

                    {restoreResult && (
                        <div className="bg-white border border-amber-200 rounded-lg p-3 text-xs" data-testid="restore-result">
                            <p className="font-semibold text-emerald-700">{restoreResult.message}</p>
                            {restoreResult.mode === 'wipe' && restoreResult.total_deleted > 0 && (
                                <p className="text-red-600 mt-1">Record eliminati prima dell'importazione: <strong>{restoreResult.total_deleted}</strong></p>
                            )}
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1 mt-2">
                                {Object.entries(restoreResult.details || {}).filter(([, v]) => v.inserted > 0 || v.updated > 0 || v.errors > 0).map(([k, v]) => (
                                    <span key={k} className="text-slate-600">
                                        {COLLECTION_LABELS[k] || k}: {v.inserted > 0 && <strong className="text-emerald-600">+{v.inserted}</strong>}
                                        {v.updated > 0 && <span className="text-blue-600 font-semibold"> {v.inserted > 0 ? '/ ' : ''}{v.updated} agg.</span>}
                                        {v.errors > 0 && <span className="text-red-500"> ({v.errors} errori)</span>}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Auto-Backup & History */}
                <div className="border border-blue-200 bg-blue-50/30 rounded-lg p-4 space-y-3">
                    <div>
                        <h3 className="text-sm font-bold text-blue-800 flex items-center gap-1.5">
                            <RefreshCw className="h-4 w-4" /> Backup Automatico
                        </h3>
                        <p className="text-xs text-blue-600 mt-0.5">
                            Il sistema esegue un backup automatico giornaliero. Vengono conservati gli ultimi 7 backup automatici.
                        </p>
                    </div>
                    {history.length > 0 ? (
                        <div className="space-y-1.5" data-testid="backup-history">
                            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Storico Backup ({history.length})</p>
                            {history.map((h, i) => (
                                <div key={i} className="flex items-center justify-between bg-white border rounded px-3 py-2 text-xs">
                                    <div className="flex items-center gap-2">
                                        {h.auto ? (
                                            <Badge variant="outline" className="text-[9px] bg-blue-50 text-blue-600 border-blue-200">Auto</Badge>
                                        ) : (
                                            <Badge variant="outline" className="text-[9px] bg-emerald-50 text-emerald-600 border-emerald-200">Manuale</Badge>
                                        )}
                                        <span className="text-slate-700 font-medium">{fmtDate(h.date)}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-slate-500">
                                        <span>{h.total_records} record</span>
                                        <span>{fmtSize(h.size_bytes)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">Nessun backup nello storico</p>
                    )}
                </div>
            </CardContent>
        </Card>

        {/* Restore Mode Selection Dialog */}
        <AlertDialog open={showModeDialog} onOpenChange={(v) => { if (!v) cancelRestore(); }}>
            <AlertDialogContent className="max-w-lg" data-testid="restore-mode-dialog">
                <AlertDialogHeader>
                    <AlertDialogTitle>Scegli Modalita di Ripristino</AlertDialogTitle>
                    <AlertDialogDescription className="text-sm">
                        File selezionato: <strong>{pendingFile?.name}</strong>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="space-y-3 py-2">
                    <button
                        onClick={() => executeRestore('merge')}
                        className="w-full text-left border-2 border-blue-200 hover:border-blue-400 bg-blue-50/50 hover:bg-blue-50 rounded-lg p-4 transition-colors"
                        data-testid="btn-restore-merge"
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <RefreshCw className="h-4 w-4 text-blue-600" />
                            <span className="font-semibold text-blue-800 text-sm">Unisci / Aggiorna (Consigliato)</span>
                        </div>
                        <p className="text-xs text-blue-600 leading-relaxed">
                            I record esistenti vengono aggiornati, i nuovi vengono inseriti. Nessun dato viene cancellato. Ideale per sincronizzare o aggiornare i dati.
                        </p>
                    </button>
                    <button
                        onClick={() => executeRestore('wipe')}
                        className="w-full text-left border-2 border-red-200 hover:border-red-400 bg-red-50/50 hover:bg-red-50 rounded-lg p-4 transition-colors"
                        data-testid="btn-restore-wipe"
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <Trash2 className="h-4 w-4 text-red-600" />
                            <span className="font-semibold text-red-800 text-sm">Sostituzione Totale</span>
                        </div>
                        <p className="text-xs text-red-600 leading-relaxed">
                            TUTTI i dati attuali vengono CANCELLATI e sostituiti con quelli del backup. Operazione irreversibile. Usare solo per ripristino completo.
                        </p>
                    </button>
                </div>
                <AlertDialogFooter>
                    <AlertDialogCancel onClick={cancelRestore} data-testid="btn-restore-cancel">Annulla</AlertDialogCancel>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
        </>
    );
}
