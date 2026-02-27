/**
 * Fascicolo Cantiere — Project Dossier / Timeline View per Cliente
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    ArrowLeft, Building2, Ruler, Package, ClipboardList, Receipt,
    Shield, FileText, ExternalLink, Calendar,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EmptyState from '../components/EmptyState';

const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

const TYPE_CONFIG = {
    rilievo: { label: 'Rilievo', icon: Ruler, color: 'bg-amber-500', border: 'border-amber-300', light: 'bg-amber-50', text: 'text-amber-700' },
    distinta: { label: 'Distinta', icon: Package, color: 'bg-blue-500', border: 'border-blue-300', light: 'bg-blue-50', text: 'text-blue-700' },
    preventivo: { label: 'Preventivo', icon: ClipboardList, color: 'bg-emerald-500', border: 'border-emerald-300', light: 'bg-emerald-50', text: 'text-emerald-700' },
    fattura: { label: 'Fattura', icon: Receipt, color: 'bg-violet-500', border: 'border-violet-300', light: 'bg-violet-50', text: 'text-violet-700' },
    certificazione: { label: 'Cert. CE', icon: Shield, color: 'bg-rose-500', border: 'border-rose-300', light: 'bg-rose-50', text: 'text-rose-700' },
};

const STATUS_COLORS = {
    bozza: 'bg-slate-100 text-slate-700',
    completato: 'bg-emerald-100 text-emerald-800',
    confermata: 'bg-blue-100 text-blue-800',
    ordinata: 'bg-amber-100 text-amber-800',
    completata: 'bg-emerald-100 text-emerald-800',
    inviato: 'bg-blue-100 text-blue-800',
    accettato: 'bg-emerald-100 text-emerald-800',
    rifiutato: 'bg-red-100 text-red-800',
    emessa: 'bg-blue-100 text-blue-800',
    pagata: 'bg-emerald-100 text-emerald-800',
    completo: 'bg-emerald-100 text-emerald-800',
};

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        return new Date(dateStr).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

export default function FascicoloCantierePage() {
    const { clientId } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetch_ = async () => {
            try {
                const res = await apiRequest(`/dashboard/fascicolo/${clientId}`);
                setData(res);
            } catch (e) {
                toast.error('Errore nel caricamento del fascicolo');
                navigate('/clients');
            } finally {
                setLoading(false);
            }
        };
        fetch_();
    }, [clientId, navigate]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0055FF]" />
                </div>
            </DashboardLayout>
        );
    }

    if (!data) return null;

    const { client, timeline, documents } = data;
    const totalDocs = Object.values(documents).reduce((a, b) => a + b, 0);

    const docTypes = [
        { key: 'rilievi', label: 'Rilievi', icon: Ruler, count: documents.rilievi, color: 'from-amber-500 to-amber-400' },
        { key: 'distinte', label: 'Distinte', icon: Package, count: documents.distinte, color: 'from-blue-500 to-blue-400' },
        { key: 'preventivi', label: 'Preventivi', icon: ClipboardList, count: documents.preventivi, color: 'from-emerald-500 to-emerald-400' },
        { key: 'fatture', label: 'Fatture', icon: Receipt, count: documents.fatture, color: 'from-violet-500 to-violet-400' },
        { key: 'certificazioni', label: 'Cert. CE', icon: Shield, count: documents.certificazioni, color: 'from-rose-500 to-rose-400' },
    ];

    return (
        <DashboardLayout>
            <div className="space-y-6" data-testid="fascicolo-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button data-testid="btn-back" variant="outline" onClick={() => navigate('/clients')} className="h-10">
                            <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                        </Button>
                        <div>
                            <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                                <Building2 className="h-6 w-6 text-[#0055FF]" />
                                {client.business_name}
                            </h1>
                            <p className="text-sm text-slate-500 mt-0.5">
                                Fascicolo Cantiere — {totalDocs} documenti
                            </p>
                        </div>
                    </div>
                </div>

                {/* Document Grid — Cards with icons */}
                <div className="grid grid-cols-5 gap-3" data-testid="doc-grid">
                    {docTypes.map(d => (
                        <Card
                            key={d.key}
                            className={`border-0 bg-gradient-to-br ${d.color} text-white shadow-md cursor-pointer hover:shadow-lg transition-shadow`}
                            data-testid={`doc-card-${d.key}`}
                        >
                            <CardContent className="pt-4 pb-3 px-4 flex flex-col items-center text-center relative overflow-hidden">
                                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center mb-2">
                                    <d.icon className="h-5 w-5" />
                                </div>
                                <p className="text-2xl font-mono font-bold">{d.count}</p>
                                <p className="text-xs text-white/80 mt-0.5">{d.label}</p>
                                <div className="absolute -right-3 -bottom-3 w-16 h-16 rounded-full bg-white/10" />
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Timeline */}
                <Card className="border-gray-200">
                    <CardHeader className="pb-3 px-6 pt-5">
                        <CardTitle className="text-base font-semibold text-[#1E293B] flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-[#0055FF]" /> Cronologia Progetto
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="px-6 pb-6">
                        {timeline.length === 0 ? (
                            <EmptyState
                                type="fascicolo"
                                title="Nessun documento"
                                description="Questo cliente non ha ancora documenti associati. Crea un rilievo o un preventivo per iniziare."
                                actionLabel="Nuovo Rilievo"
                                onAction={() => navigate(`/rilievi/new?client_id=${clientId}`)}
                            />
                        ) : (
                            <div className="relative" data-testid="timeline">
                                {/* Vertical line */}
                                <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-slate-200" />

                                <div className="space-y-1">
                                    {timeline.map((event, i) => {
                                        const cfg = TYPE_CONFIG[event.type] || TYPE_CONFIG.rilievo;
                                        const Icon = cfg.icon;
                                        const statusColor = STATUS_COLORS[event.status] || STATUS_COLORS.bozza;

                                        return (
                                            <div
                                                key={`${event.type}-${event.id}`}
                                                className="relative flex items-start gap-4 pl-12 py-3 group cursor-pointer hover:bg-slate-50 rounded-lg transition-colors -ml-2 pr-2"
                                                onClick={() => navigate(event.link)}
                                                data-testid={`timeline-event-${i}`}
                                            >
                                                {/* Dot on timeline */}
                                                <div className={`absolute left-3 top-4 w-5 h-5 rounded-full ${cfg.color} flex items-center justify-center ring-4 ring-white shadow-sm`}>
                                                    <Icon className="h-2.5 w-2.5 text-white" />
                                                </div>

                                                {/* Content */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <Badge className={`${cfg.light} ${cfg.text} text-[10px] font-semibold`}>
                                                            {cfg.label}
                                                        </Badge>
                                                        <span className="text-sm font-medium text-[#1E293B] truncate">{event.title}</span>
                                                        <Badge className={`${statusColor} text-[10px]`}>{event.status}</Badge>
                                                    </div>
                                                    <div className="flex items-center gap-3 mt-1">
                                                        <span className="text-xs text-slate-400 font-mono">{formatDate(event.date)}</span>
                                                        {event.extra && (
                                                            <span className="text-xs text-slate-500 font-mono">{event.extra}</span>
                                                        )}
                                                    </div>
                                                </div>

                                                <ExternalLink className="h-3.5 w-3.5 text-slate-300 group-hover:text-[#0055FF] transition-colors shrink-0 mt-1" />
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
