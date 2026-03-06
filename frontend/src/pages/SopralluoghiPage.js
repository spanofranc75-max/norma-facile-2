import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { toast } from 'sonner';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
    Plus, Search, MapPin, Eye, Trash2, Brain, FileText,
    Calendar, ChevronRight, Loader2, ShieldAlert
} from 'lucide-react';
import { useConfirm } from '../components/ConfirmProvider';

const STATUS_MAP = {
    bozza: { label: 'Bozza', className: 'bg-gray-100 text-gray-700' },
    analizzato: { label: 'Analizzato', className: 'bg-blue-100 text-blue-700' },
    completato: { label: 'Completato', className: 'bg-green-100 text-green-700' },
};

export default function SopralluoghiPage() {
    const confirm = useConfirm();
    const navigate = useNavigate();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    const fetchData = async () => {
        try {
            const data = await apiRequest(`/sopralluoghi/?search=${search}&limit=50`);
            setItems(data.items || []);
        } catch (err) {
            toast.error(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchData(); }, [search]);

    const handleDelete = async (id) => {
        if (!(await confirm('Eliminare questo sopralluogo?'))) return;
        try {
            await apiRequest(`/sopralluoghi/${id}`, { method: 'DELETE' });
            setItems(prev => prev.filter(i => i.sopralluogo_id !== id));
            toast.success('Eliminato');
        } catch (err) {
            toast.error(err.message);
        }
    };

    return (
        <div className="max-w-5xl mx-auto">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Sopralluoghi & Perizie AI</h1>
                    <p className="text-sm text-gray-500 mt-1">Analisi intelligente per messa a norma cancelli (EN 12453)</p>
                </div>
                <Button
                    data-testid="btn-new-sopralluogo"
                    onClick={() => navigate('/sopralluoghi/new')}
                    className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                >
                    <Plus className="h-4 w-4 mr-2" /> Nuovo Sopralluogo
                </Button>
            </div>

            <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                    data-testid="search-sopralluoghi"
                    placeholder="Cerca per indirizzo, numero o descrizione..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="pl-9"
                />
            </div>

            {loading ? (
                <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-gray-400" /></div>
            ) : items.length === 0 ? (
                <Card className="text-center py-16">
                    <CardContent>
                        <ShieldAlert className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-600 mb-2">Nessun sopralluogo</h3>
                        <p className="text-sm text-gray-400 mb-4">Inizia un nuovo sopralluogo per analizzare un cancello con l'AI</p>
                        <Button onClick={() => navigate('/sopralluoghi/new')} className="bg-[#0055FF] text-white">
                            <Plus className="h-4 w-4 mr-2" /> Primo Sopralluogo
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-3">
                    {items.map(item => {
                        const statusInfo = STATUS_MAP[item.status] || STATUS_MAP.bozza;
                        const fotoCount = item.foto?.length || 0;
                        const hasAnalysis = !!item.analisi_ai;
                        const conformita = item.analisi_ai?.conformita_percentuale;

                        return (
                            <Card
                                key={item.sopralluogo_id}
                                className="hover:shadow-md transition cursor-pointer"
                                onClick={() => navigate(`/sopralluoghi/${item.sopralluogo_id}`)}
                                data-testid={`sopralluogo-card-${item.sopralluogo_id}`}
                            >
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-4">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="font-mono text-sm text-gray-500">{item.document_number}</span>
                                                <Badge className={statusInfo.className}>{statusInfo.label}</Badge>
                                                {conformita != null && (
                                                    <Badge variant="outline" className={
                                                        conformita < 40 ? 'border-red-200 text-red-700' :
                                                        conformita < 70 ? 'border-amber-200 text-amber-700' :
                                                        'border-green-200 text-green-700'
                                                    }>
                                                        {conformita}% conforme
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="font-medium text-gray-900 truncate">
                                                {item.client_name || 'Senza cliente'}
                                            </p>
                                            {item.indirizzo && (
                                                <p className="text-sm text-gray-500 flex items-center gap-1 mt-0.5">
                                                    <MapPin className="h-3 w-3" /> {item.indirizzo}{item.comune ? `, ${item.comune}` : ''}
                                                </p>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3 text-gray-400 shrink-0">
                                            <div className="text-center">
                                                <p className="text-lg font-bold text-gray-600">{fotoCount}</p>
                                                <p className="text-xs">foto</p>
                                            </div>
                                            {hasAnalysis && <Brain className="h-5 w-5 text-purple-500" />}
                                            {item.preventivo_id && <FileText className="h-5 w-5 text-green-500" />}
                                            <button
                                                onClick={e => { e.stopPropagation(); handleDelete(item.sopralluogo_id); }}
                                                className="p-1 hover:text-red-500 transition"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </button>
                                            <ChevronRight className="h-5 w-5" />
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
