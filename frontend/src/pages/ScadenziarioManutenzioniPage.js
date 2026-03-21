/**
 * ScadenziarioManutenzioniPage — Vista unificata manutenzioni strumenti + attrezzature.
 * Fili conduttori: mostra l'impatto su Riesame Tecnico e Controllo Finale.
 */
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
    RefreshCw, AlertTriangle, Shield, Clock, Wrench, CheckCircle2, Link2
} from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';

const URGENZA_CFG = {
    scaduto:     { label: 'Scaduto',      cls: 'bg-red-600 text-white',        rowCls: 'bg-red-50/70' },
    in_scadenza: { label: 'In scadenza',  cls: 'bg-amber-500 text-white',      rowCls: 'bg-amber-50/50' },
    prossimo:    { label: '< 90 gg',      cls: 'bg-sky-100 text-sky-700',      rowCls: '' },
    ok:          { label: 'Conforme',      cls: 'bg-emerald-100 text-emerald-700', rowCls: '' },
    sconosciuto: { label: '—',            cls: 'bg-slate-100 text-slate-500',  rowCls: '' },
};

const FONTE_ICON = {
    strumento:   <Wrench className="h-3.5 w-3.5 text-indigo-500" />,
    attrezzatura: <Shield className="h-3.5 w-3.5 text-amber-600" />,
    itt:         <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />,
};

function fmtDate(d) {
    if (!d) return '—';
    const p = d.slice(0, 10).split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
}

export default function ScadenziarioManutenzioniPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filtro, setFiltro] = useState('tutti'); // tutti | scaduto | in_scadenza

    const fetch_ = useCallback(async () => {
        try {
            const d = await apiRequest('/scadenziario-manutenzioni');
            setData(d);
        } catch (e) { toast.error(e.message); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetch_(); }, [fetch_]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            </DashboardLayout>
        );
    }

    const kpi = data?.kpi || {};
    const items = (data?.items || []).filter(i =>
        filtro === 'tutti' ? true :
        filtro === 'critici' ? (i.urgenza === 'scaduto' || i.urgenza === 'in_scadenza') :
        i.urgenza === filtro
    );

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="scadenziario-manutenzioni-page">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                            Scadenziario Manutenzioni
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Strumenti di misura + Attrezzature — Vista unificata
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={fetch_} className="border-slate-200 text-slate-600" data-testid="refresh-manutenzioni">
                        <RefreshCw className="h-4 w-4 mr-1.5" /> Aggiorna
                    </Button>
                </div>

                {/* Alert blocco Riesame */}
                {data?.blocchi_riesame > 0 && (
                    <Card className="border-red-300 bg-red-50" data-testid="alert-blocchi-riesame">
                        <CardContent className="p-3 flex items-center gap-3">
                            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0" />
                            <div>
                                <p className="text-sm font-semibold text-red-800">{data.alert_msg}</p>
                                <p className="text-xs text-red-600 mt-0.5">
                                    Il Riesame Tecnico non potra essere approvato finche questi elementi non vengono aggiornati.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* KPI */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {[
                        { k: 'totale', label: 'Totale', icon: Wrench, color: 'text-slate-600', bg: '', filter: 'tutti' },
                        { k: 'scaduti', label: 'Scaduti', icon: AlertTriangle, color: 'text-red-600', bg: 'border-red-200', filter: 'scaduto' },
                        { k: 'in_scadenza', label: 'In Scadenza', icon: Clock, color: 'text-amber-600', bg: 'border-amber-200', filter: 'in_scadenza' },
                        { k: 'prossimi_90gg', label: '< 90 giorni', icon: Clock, color: 'text-sky-600', bg: '', filter: 'prossimo' },
                        { k: 'conformi', label: 'Conformi', icon: CheckCircle2, color: 'text-emerald-600', bg: '', filter: 'ok' },
                    ].map(c => {
                        const Icon = c.icon;
                        const active = filtro === c.filter;
                        return (
                            <Card key={c.k}
                                className={`cursor-pointer transition-all ${c.bg || 'border-slate-200'} ${active ? 'ring-2 ring-slate-800 ring-offset-1' : 'hover:shadow-sm'}`}
                                onClick={() => setFiltro(c.filter)}
                                data-testid={`kpi-${c.k}`}
                            >
                                <CardContent className="p-3">
                                    <div className="flex items-center gap-2 mb-1">
                                        <Icon className={`h-4 w-4 ${c.color}`} />
                                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{c.label}</span>
                                    </div>
                                    <p className={`text-2xl font-bold ${c.color} font-mono`}>{kpi[c.k] ?? 0}</p>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>

                {/* Table */}
                <Card className="border-slate-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-700">
                                    <TableHead className="text-white text-[11px] font-semibold w-[40px]">Fonte</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Nome / Modello</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">S/N</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Tipo</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Ultima Manut.</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Prossima Scad.</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold w-[100px]">Stato</TableHead>
                                    <TableHead className="text-white text-[11px] font-semibold">Impatto</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {items.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-10 text-slate-400 text-sm">
                                            Nessun elemento trovato
                                        </TableCell>
                                    </TableRow>
                                ) : items.map((item, idx) => {
                                    const cfg = URGENZA_CFG[item.urgenza] || URGENZA_CFG.sconosciuto;
                                    return (
                                        <TableRow key={item.id}
                                            className={`${cfg.rowCls || (idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50')} hover:bg-blue-50/40 transition-colors`}
                                            data-testid={`manutenzione-row-${item.id}`}
                                        >
                                            <TableCell className="text-center">{FONTE_ICON[item.fonte]}</TableCell>
                                            <TableCell>
                                                <div className="text-xs font-medium text-slate-800">{item.nome}</div>
                                                {item.modello && <div className="text-[10px] text-slate-500">{item.modello}</div>}
                                            </TableCell>
                                            <TableCell className="text-xs text-slate-600 font-mono">{item.serial || '—'}</TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-slate-200 text-slate-600">
                                                    {item.tipo_dettaglio}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-xs text-slate-600">{fmtDate(item.ultima_manutenzione)}</TableCell>
                                            <TableCell className="text-xs font-medium text-slate-700">{fmtDate(item.prossima_scadenza)}</TableCell>
                                            <TableCell>
                                                <Badge className={`text-[10px] px-1.5 py-0.5 ${cfg.cls}`}>
                                                    {cfg.label}
                                                    {item.giorni_rimasti !== null && item.urgenza !== 'ok' && (
                                                        <span className="ml-1 opacity-80">
                                                            ({item.giorni_rimasti < 0 ? `${Math.abs(item.giorni_rimasti)}gg fa` : `${item.giorni_rimasti}gg`})
                                                        </span>
                                                    )}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-wrap gap-1">
                                                    {(item.impatto || []).map((imp, i) => (
                                                        <Badge key={i} variant="outline"
                                                            className={`text-[8px] px-1 py-0 ${item.urgenza === 'scaduto' ? 'border-red-300 text-red-600 bg-red-50' : 'border-slate-200 text-slate-500'}`}
                                                        >
                                                            <Link2 className="h-2.5 w-2.5 mr-0.5" />{imp.split('(')[0].trim()}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>
                    {items.length > 0 && (
                        <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-t border-slate-200" data-testid="footer-count">
                            <span className="text-xs text-slate-500">{items.length} elementi</span>
                            <span className="text-[10px] text-slate-400">
                                Filtro: {filtro === 'tutti' ? 'Tutti' : filtro === 'critici' ? 'Critici' : URGENZA_CFG[filtro]?.label || filtro}
                            </span>
                        </div>
                    )}
                </Card>
            </div>
        </DashboardLayout>
    );
}
