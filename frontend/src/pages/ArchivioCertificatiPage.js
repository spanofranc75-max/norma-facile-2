/**
 * ArchivioCertificatiPage — Certificati non assegnati a nessuna commessa.
 * Profili estratti da AI OCR che non matchano ordini esistenti.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { FileInput, Loader2, CheckCircle2, ArrowRight, Package, AlertTriangle } from 'lucide-react';

export default function ArchivioCertificatiPage() {
    const [archivio, setArchivio] = useState([]);
    const [loading, setLoading] = useState(true);
    const [commesse, setCommesse] = useState([]);
    const [assignDialog, setAssignDialog] = useState(null);
    const [selectedCommessa, setSelectedCommessa] = useState('');
    const [assigning, setAssigning] = useState(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [archRes, commRes] = await Promise.all([
                apiRequest('/cam/archivio-certificati'),
                apiRequest('/commesse').catch(() => ({ commesse: [] })),
            ]);
            setArchivio(archRes.archivio || []);
            setCommesse((commRes.items || commRes.commesse || commRes || []).filter(c => c.stato !== 'completata'));
        } catch (e) {
            toast.error('Errore caricamento archivio');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleAssegna = async () => {
        if (!selectedCommessa || !assignDialog) return;
        setAssigning(true);
        try {
            await apiRequest(`/cam/archivio-certificati/${encodeURIComponent(assignDialog.numero_colata)}/assegna?commessa_id=${selectedCommessa}`, { method: 'POST' });
            const comm = commesse.find(c => c.commessa_id === selectedCommessa);
            toast.success(`Profilo ${assignDialog.dimensioni} assegnato a ${comm?.numero || selectedCommessa}`);
            setAssignDialog(null);
            setSelectedCommessa('');
            fetchData();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setAssigning(false);
        }
    };

    const METODO_LABELS = {
        forno_elettrico_non_legato: 'Forno El. (non legato)',
        forno_elettrico_legato: 'Forno El. (legato)',
        ciclo_integrale: 'Ciclo Integrale',
    };

    return (
        <DashboardLayout title="Archivio Certificati">
            <div className="max-w-5xl mx-auto space-y-4" data-testid="archivio-certificati-page">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-[#1E293B] flex items-center gap-2">
                            <FileInput className="h-5 w-5 text-amber-600" />
                            Archivio Certificati Non Assegnati
                        </h1>
                        <p className="text-sm text-slate-500 mt-0.5">
                            Profili estratti da AI OCR che non corrispondono a nessun ordine di acquisto
                        </p>
                    </div>
                    <Badge className="bg-amber-100 text-amber-700">{archivio.length} profili</Badge>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-6 w-6 animate-spin text-amber-600" />
                    </div>
                ) : archivio.length === 0 ? (
                    <Card className="border-gray-200">
                        <CardContent className="py-16 text-center">
                            <CheckCircle2 className="h-10 w-10 mx-auto mb-3 text-emerald-400" />
                            <p className="text-slate-500 text-sm font-medium">Nessun certificato in archivio</p>
                            <p className="text-xs text-slate-400 mt-1">Tutti i profili analizzati sono stati assegnati a una commessa</p>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="space-y-2">
                        {archivio.map((item, i) => (
                            <Card key={item.numero_colata || i} className="border-amber-200 hover:shadow-sm transition-shadow" data-testid={`archivio-item-${i}`}>
                                <CardContent className="p-3">
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1.5">
                                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                                                <span className="text-sm font-bold text-[#1E293B]">{item.dimensioni || 'Profilo sconosciuto'}</span>
                                                <Badge className="bg-slate-100 text-slate-600 text-[9px]">{item.qualita_acciaio || '-'}</Badge>
                                            </div>
                                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                                                <div>
                                                    <span className="text-slate-400 block text-[10px]">N. Colata</span>
                                                    <span className="font-mono font-semibold text-slate-700">{item.numero_colata || '-'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-slate-400 block text-[10px]">Fornitore</span>
                                                    <span className="font-mono text-slate-700">{item.fornitore || '-'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-slate-400 block text-[10px]">Peso</span>
                                                    <span className="font-mono text-slate-700">{item.peso_kg ? `${item.peso_kg} kg` : '-'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-slate-400 block text-[10px]">Metodo</span>
                                                    <span className="font-mono text-slate-700">{METODO_LABELS[item.metodo_produttivo] || '-'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-slate-400 block text-[10px]">% Riciclato</span>
                                                    <span className="font-mono text-slate-700">{item.percentuale_riciclato != null ? `${item.percentuale_riciclato}%` : '-'}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <Button
                                            size="sm"
                                            className="ml-3 bg-amber-500 text-white hover:bg-amber-600 shrink-0"
                                            onClick={() => { setAssignDialog(item); setSelectedCommessa(''); }}
                                            data-testid={`btn-assegna-${i}`}
                                        >
                                            <ArrowRight className="h-3.5 w-3.5 mr-1" /> Assegna
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}

                {/* Assign Dialog */}
                <Dialog open={!!assignDialog} onOpenChange={(open) => { if (!open) setAssignDialog(null); }}>
                    <DialogContent className="max-w-md" data-testid="assign-dialog">
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                <Package className="h-5 w-5 text-amber-600" />
                                Assegna a Commessa
                            </DialogTitle>
                            <DialogDescription>
                                Assegna il profilo <strong>{assignDialog?.dimensioni}</strong> (colata: {assignDialog?.numero_colata}) a una commessa esistente
                            </DialogDescription>
                        </DialogHeader>
                        <div className="py-3">
                            <Select value={selectedCommessa} onValueChange={setSelectedCommessa}>
                                <SelectTrigger className="w-full h-9" data-testid="select-commessa-assegna">
                                    <SelectValue placeholder="Seleziona commessa..." />
                                </SelectTrigger>
                                <SelectContent position="popper" sideOffset={4}>
                                    {commesse.map(c => (
                                        <SelectItem key={c.commessa_id} value={c.commessa_id}>
                                            {c.numero} — {c.title || c.client_name || ''}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" size="sm" onClick={() => setAssignDialog(null)}>Annulla</Button>
                            <Button size="sm" onClick={handleAssegna} disabled={!selectedCommessa || assigning}
                                className="bg-amber-500 text-white hover:bg-amber-600" data-testid="btn-confirm-assegna">
                                {assigning ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <ArrowRight className="h-3.5 w-3.5 mr-1" />}
                                Assegna
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </DashboardLayout>
    );
}
