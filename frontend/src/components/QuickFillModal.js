/**
 * QuickFillModal — Seleziona un Preventivo o DDT per auto-popolare le righe fattura.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { toast } from 'sonner';
import { Search, FileText, Truck, ArrowRight, Check } from 'lucide-react';

const fmtEur = (v) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

export function QuickFillModal({ open, onOpenChange, onSelect }) {
    const [sources, setSources] = useState([]);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState('');

    const fetchSources = useCallback(async () => {
        setLoading(true);
        try {
            let url = '/invoices/quick-fill/sources?';
            if (search) url += `q=${encodeURIComponent(search)}&`;
            if (filter) url += `doc_type=${filter}&`;
            const data = await apiRequest(url);
            setSources(data.sources || []);
        } catch (e) {
            toast.error('Errore caricamento documenti');
        } finally {
            setLoading(false);
        }
    }, [search, filter]);

    useEffect(() => {
        if (open) fetchSources();
    }, [open, fetchSources]);

    const handleSelect = (source) => {
        onSelect(source);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle className="text-lg font-bold text-[#1E293B]">
                        Importa da Preventivo / DDT
                    </DialogTitle>
                    <DialogDescription className="text-sm text-slate-500">
                        Seleziona un documento per auto-popolare le righe della fattura
                    </DialogDescription>
                </DialogHeader>

                <div className="flex items-center gap-2 mt-2">
                    <div className="flex gap-1">
                        {[
                            { value: '', label: 'Tutti' },
                            { value: 'preventivo', label: 'Preventivi' },
                            { value: 'ddt', label: 'DDT' },
                        ].map(f => (
                            <button
                                key={f.value}
                                data-testid={`qf-filter-${f.value || 'all'}`}
                                onClick={() => setFilter(f.value)}
                                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${filter === f.value ? 'bg-[#0055FF] text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                            >{f.label}</button>
                        ))}
                    </div>
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                        <Input
                            data-testid="qf-search"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Cerca per numero, cliente..."
                            className="pl-9 h-8 text-sm"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-auto mt-3 border rounded-lg">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                        </div>
                    ) : sources.length === 0 ? (
                        <div className="text-center py-12 text-slate-400 text-sm">
                            Nessun documento trovato
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-50">
                                    <TableHead className="text-[10px] font-semibold">Tipo</TableHead>
                                    <TableHead className="text-[10px] font-semibold">Numero</TableHead>
                                    <TableHead className="text-[10px] font-semibold">Cliente</TableHead>
                                    <TableHead className="text-[10px] font-semibold">Oggetto</TableHead>
                                    <TableHead className="text-[10px] font-semibold text-right">Totale</TableHead>
                                    <TableHead className="text-[10px] font-semibold">Stato</TableHead>
                                    <TableHead className="text-[10px] font-semibold">Data</TableHead>
                                    <TableHead className="w-[60px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {sources.map(src => {
                                    const isPrev = src.source_type === 'preventivo';
                                    const isConverted = !!src.converted_to;
                                    return (
                                        <TableRow
                                            key={`${src.source_type}-${src.source_id}`}
                                            data-testid={`qf-row-${src.source_id}`}
                                            className={`hover:bg-blue-50 cursor-pointer ${isConverted ? 'opacity-50' : ''}`}
                                            onClick={() => !isConverted && handleSelect(src)}
                                        >
                                            <TableCell>
                                                <Badge className={`text-[9px] ${isPrev ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                                                    {isPrev ? <><FileText className="h-3 w-3 mr-1 inline" />PRV</> : <><Truck className="h-3 w-3 mr-1 inline" />DDT</>}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="font-mono text-xs font-semibold text-[#0055FF]">{src.number}</TableCell>
                                            <TableCell className="text-xs">{src.client_name || '-'}</TableCell>
                                            <TableCell className="text-xs text-slate-500 max-w-[150px] truncate">{src.subject || '-'}</TableCell>
                                            <TableCell className="text-right font-mono text-xs font-semibold">{fmtEur(src.total)}</TableCell>
                                            <TableCell>
                                                <Badge className={`text-[9px] ${isConverted ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                                                    {isConverted ? <><Check className="h-3 w-3 mr-0.5 inline" />Conv.</> : src.status}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-[10px] text-slate-400">{src.date}</TableCell>
                                            <TableCell>
                                                {!isConverted && (
                                                    <Button variant="ghost" size="sm" className="h-7 text-[#0055FF]">
                                                        <ArrowRight className="h-3 w-3" />
                                                    </Button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
