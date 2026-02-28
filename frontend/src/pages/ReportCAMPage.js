/**
 * ReportCAMPage — Bilancio di Sostenibilità Ambientale Multi-Commessa
 * Mostra KPI aggregati, CO2 risparmiata, e breakdown per commessa/fornitore.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import {
    Leaf, Download, Factory, Loader2, CheckCircle2, AlertTriangle,
    TreePine, Weight, Recycle, Building2, TrendingDown,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const fmtKg = (v) => (v || 0).toLocaleString('it-IT', { maximumFractionDigits: 1 });
const fmtT = (v) => ((v || 0) / 1000).toLocaleString('it-IT', { maximumFractionDigits: 2 });
const fmtPerc = (v) => (v || 0).toLocaleString('it-IT', { maximumFractionDigits: 1 });

const METODO_LABELS = {
    forno_elettrico_non_legato: 'Forno El. (non legato)',
    forno_elettrico_legato: 'Forno El. (legato)',
    ciclo_integrale: 'Ciclo Integrale',
    sconosciuto: 'Non specificato',
};

export default function ReportCAMPage() {
    const currentYear = new Date().getFullYear();
    const [anno, setAnno] = useState(String(currentYear));
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchReport = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiRequest(`/cam/report-aziendale?anno=${anno}`);
            setReport(data);
        } catch (e) {
            toast.error('Errore caricamento report');
        } finally {
            setLoading(false);
        }
    }, [anno]);

    useEffect(() => { fetchReport(); }, [fetchReport]);

    const handleDownloadPdf = async () => {
        try {
            const res = await fetch(`${API}/api/cam/report-aziendale/pdf?anno=${anno}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            });
            if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Errore'); }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Bilancio_Sostenibilita_CAM_${anno}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Report PDF generato');
        } catch (e) { toast.error(e.message); }
    };

    const years = [];
    for (let y = currentYear; y >= currentYear - 5; y--) years.push(String(y));

    return (
        <DashboardLayout title="Report CAM">
            <div className="max-w-5xl mx-auto space-y-5" data-testid="report-cam-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-[#1E293B] flex items-center gap-2">
                            <Leaf className="h-5 w-5 text-emerald-600" />
                            Bilancio di Sostenibilità Ambientale
                        </h1>
                        <p className="text-sm text-slate-500 mt-0.5">DM 23 giugno 2022 n. 256 — Criteri Ambientali Minimi</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Select value={anno} onValueChange={setAnno}>
                            <SelectTrigger className="w-28 h-9" data-testid="select-anno"><SelectValue /></SelectTrigger>
                            <SelectContent position="popper" sideOffset={4}>
                                {years.map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        <Button onClick={handleDownloadPdf} disabled={!report || report.totale_lotti === 0}
                            className="bg-emerald-600 text-white hover:bg-emerald-700" data-testid="btn-download-report-pdf">
                            <Download className="h-4 w-4 mr-1.5" /> Report PDF
                        </Button>
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
                    </div>
                ) : !report || report.totale_lotti === 0 ? (
                    <Card className="border-gray-200">
                        <CardContent className="py-16 text-center">
                            <Leaf className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                            <p className="text-slate-500 text-sm">Nessun dato CAM per il {anno}</p>
                            <p className="text-xs text-slate-400 mt-1">Aggiungi lotti materiale alle commesse dalla sezione CAM</p>
                        </CardContent>
                    </Card>
                ) : (
                    <>
                        {/* KPI Cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="cam-kpi-grid">
                            <KpiCard icon={Weight} label="Acciaio Totale" value={`${fmtT(report.peso_totale_kg)} t`} sublabel={`${fmtKg(report.peso_totale_kg)} kg`} color="slate" />
                            <KpiCard icon={Recycle} label="Acciaio Riciclato" value={`${fmtT(report.peso_riciclato_kg)} t`} sublabel={`${fmtPerc(report.percentuale_riciclato_media)}% del totale`} color="emerald" />
                            <KpiCard icon={Building2} label="Commesse Conformi" value={`${report.commesse_conformi}/${report.commesse_totali}`} sublabel={`${report.totale_lotti} lotti totali`} color="blue" />
                            <KpiCard icon={TreePine} label="CO2 Risparmiata" value={`${(report.co2?.co2_risparmiata_t || 0).toLocaleString('it-IT', { maximumFractionDigits: 2 })} t`} sublabel={`-${fmtPerc(report.co2?.riduzione_percentuale)}% emissioni`} color="green" />
                        </div>

                        {/* CO2 Hero Card */}
                        <Card className="border-emerald-300 bg-gradient-to-br from-emerald-50 to-green-50" data-testid="co2-hero">
                            <CardContent className="py-6 text-center">
                                <TreePine className="h-8 w-8 mx-auto mb-2 text-emerald-600" />
                                <p className="text-xs text-emerald-700 font-semibold uppercase tracking-wider">Impatto Ambientale Positivo</p>
                                <p className="text-4xl font-black text-emerald-800 mt-1">
                                    {(report.co2?.co2_risparmiata_kg || 0).toLocaleString('it-IT', { maximumFractionDigits: 0 })} kg
                                </p>
                                <p className="text-sm text-emerald-600 font-medium">di CO2 equivalente risparmiata</p>
                                <div className="flex items-center justify-center gap-4 mt-3 text-xs text-slate-500">
                                    <span>Emissioni effettive: <strong>{(report.co2?.co2_effettiva_t || 0).toLocaleString('it-IT', { maximumFractionDigits: 2 })} tCO2e</strong></span>
                                    <span className="text-emerald-600 font-medium flex items-center gap-1">
                                        <TrendingDown className="h-3 w-3" />
                                        -{fmtPerc(report.co2?.riduzione_percentuale)}% vs acciaio primario
                                    </span>
                                </div>
                                <p className="text-[10px] text-slate-400 mt-2">Fonte: World Steel Association, 2023 — EAF: 0,67 tCO2/t | BOF: 2,33 tCO2/t</p>
                            </CardContent>
                        </Card>

                        {/* Commesse Table */}
                        <Card className="border-gray-200" data-testid="cam-commesse-table">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <Building2 className="h-3.5 w-3.5" /> Dettaglio per Commessa ({report.commesse?.length || 0})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="text-xs">Commessa</TableHead>
                                            <TableHead className="text-xs">Cliente</TableHead>
                                            <TableHead className="text-xs text-right">Peso (kg)</TableHead>
                                            <TableHead className="text-xs text-right">Riciclato (kg)</TableHead>
                                            <TableHead className="text-xs text-center">% Ric.</TableHead>
                                            <TableHead className="text-xs text-center">Stato</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(report.commesse || []).map((c, i) => (
                                            <TableRow key={i} data-testid={`comm-row-${i}`}>
                                                <TableCell className="text-sm">
                                                    <div>
                                                        <span className="font-mono text-xs text-slate-500">{c.numero}</span>
                                                        {c.titolo && <p className="text-xs text-slate-700 font-medium truncate max-w-[180px]">{c.titolo}</p>}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-xs text-slate-600">{c.cliente || '-'}</TableCell>
                                                <TableCell className="text-right text-xs font-mono">{fmtKg(c.peso_kg)}</TableCell>
                                                <TableCell className="text-right text-xs font-mono text-emerald-700">{fmtKg(c.peso_riciclato_kg)}</TableCell>
                                                <TableCell className="text-center">
                                                    <span className={`text-xs font-bold ${c.percentuale_riciclato >= 60 ? 'text-emerald-700' : 'text-red-600'}`}>
                                                        {fmtPerc(c.percentuale_riciclato)}%
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {c.conforme ? (
                                                        <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">
                                                            <CheckCircle2 className="h-3 w-3 mr-0.5" /> Conforme
                                                        </Badge>
                                                    ) : (
                                                        <Badge className="bg-red-100 text-red-700 text-[9px]">
                                                            <AlertTriangle className="h-3 w-3 mr-0.5" /> Non conf.
                                                        </Badge>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* Fornitori Table */}
                        <Card className="border-gray-200" data-testid="cam-fornitori-table">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg">
                                <CardTitle className="text-xs font-semibold text-white flex items-center gap-2">
                                    <Factory className="h-3.5 w-3.5" /> Breakdown per Fornitore ({report.fornitori?.length || 0})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="text-xs">Fornitore / Acciaieria</TableHead>
                                            <TableHead className="text-xs text-right">Peso (kg)</TableHead>
                                            <TableHead className="text-xs text-right">Riciclato (kg)</TableHead>
                                            <TableHead className="text-xs text-center">% Ric.</TableHead>
                                            <TableHead className="text-xs text-center">Lotti</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {(report.fornitori || []).map((f, i) => (
                                            <TableRow key={i}>
                                                <TableCell className="text-sm font-medium">{f.fornitore}</TableCell>
                                                <TableCell className="text-right text-xs font-mono">{fmtKg(f.peso_kg)}</TableCell>
                                                <TableCell className="text-right text-xs font-mono text-emerald-700">{fmtKg(f.peso_riciclato_kg)}</TableCell>
                                                <TableCell className="text-center text-xs font-bold text-blue-700">{fmtPerc(f.percentuale_riciclato)}%</TableCell>
                                                <TableCell className="text-center text-xs">{f.lotti}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* Metodi Produttivi */}
                        {Object.keys(report.metodi_produttivi || {}).length > 0 && (
                            <Card className="border-gray-200" data-testid="cam-metodi-table">
                                <CardHeader className="py-2 px-4">
                                    <CardTitle className="text-xs font-semibold text-slate-500 flex items-center gap-2">
                                        <Recycle className="h-3.5 w-3.5" /> Metodi Produttivi
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4 pb-3">
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                                        {Object.entries(report.metodi_produttivi).map(([metodo, data]) => (
                                            <div key={metodo} className="p-2 bg-slate-50 rounded border text-center">
                                                <p className="text-[10px] text-slate-500">{METODO_LABELS[metodo] || metodo}</p>
                                                <p className="text-sm font-bold text-[#1E293B]">{fmtKg(data.peso_kg)} kg</p>
                                                <p className="text-[10px] text-slate-400">{data.lotti} lotti</p>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </>
                )}
            </div>
        </DashboardLayout>
    );
}

function KpiCard({ icon: Icon, label, value, sublabel, color }) {
    const colorMap = {
        slate: 'text-[#1E293B] bg-slate-50 border-slate-200',
        emerald: 'text-emerald-700 bg-emerald-50 border-emerald-200',
        blue: 'text-[#0055FF] bg-blue-50 border-blue-200',
        green: 'text-green-700 bg-green-50 border-green-200',
    };
    const cls = colorMap[color] || colorMap.slate;

    return (
        <Card className={`border ${cls.split(' ').filter(c => c.startsWith('border')).join(' ')}`}>
            <CardContent className={`p-3 ${cls.split(' ').filter(c => c.startsWith('bg')).join(' ')}`}>
                <div className="flex items-center gap-2 mb-1">
                    <Icon className={`h-4 w-4 ${cls.split(' ').filter(c => c.startsWith('text')).join(' ')}`} />
                    <span className="text-[10px] text-slate-500 uppercase tracking-wide">{label}</span>
                </div>
                <p className={`text-lg font-bold ${cls.split(' ').filter(c => c.startsWith('text')).join(' ')}`}>{value}</p>
                {sublabel && <p className="text-[10px] text-slate-400 mt-0.5">{sublabel}</p>}
            </CardContent>
        </Card>
    );
}
