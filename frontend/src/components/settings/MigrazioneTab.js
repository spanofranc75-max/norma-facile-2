import { useState, useEffect } from 'react';
import { apiRequest } from '../../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Upload } from 'lucide-react';
import { toast } from 'sonner';

function StatBox({ label, value }) {
    return (
        <div className="text-center bg-white rounded-md p-2 border border-emerald-100">
            <p className="text-lg font-bold text-[#1E293B]">{value}</p>
            <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        </div>
    );
}

export default function MigrazioneTab() {
    const [stato, setStato] = useState(null);
    const [loading, setLoading] = useState(false);
    const [migrating, setMigrating] = useState(false);
    const [result, setResult] = useState(null);

    useEffect(() => {
        fetchStato();
    }, []);

    const fetchStato = async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/migrazione/stato');
            setStato(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleMigrazione = async () => {
        setMigrating(true);
        setResult(null);
        try {
            const data = await apiRequest('/migrazione/importa', { method: 'POST' });
            setResult(data);
            toast.success(data.message);
            fetchStato();
        } catch (e) {
            setResult({ message: e.message || 'Errore durante la migrazione' });
            toast.error('Errore durante la migrazione');
        } finally {
            setMigrating(false);
        }
    };

    const totale = stato ? (stato.anagrafica + stato.preventivi + stato.fatture_vendita + stato.fatture_acquisto) : 0;

    return (
        <Card className="border-gray-200">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Upload className="h-5 w-5 text-[#0055FF]" />
                    Importa da Vecchia App
                </CardTitle>
                <CardDescription>
                    Importa preventivi, fatture e anagrafica dalla vecchia versione di Norma Facile. L'importazione salta automaticamente i duplicati.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                {stato && totale > 0 && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4" data-testid="migration-status">
                        <p className="text-sm font-semibold text-emerald-800 mb-2">Dati importati:</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            <StatBox label="Anagrafica" value={stato.anagrafica} />
                            <StatBox label="Preventivi" value={stato.preventivi} />
                            <StatBox label="Fatture Vendita" value={stato.fatture_vendita} />
                            <StatBox label="Fatture Acquisto" value={stato.fatture_acquisto} />
                        </div>
                    </div>
                )}

                {stato && totale === 0 && !loading && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                        <p className="text-sm text-amber-800">Nessun dato importato. Clicca il bottone per avviare la migrazione dalla vecchia app.</p>
                    </div>
                )}

                <div className="flex items-center gap-3">
                    <Button
                        onClick={handleMigrazione}
                        disabled={migrating}
                        className="bg-[#0055FF] hover:bg-[#0044CC]"
                        data-testid="btn-importa-vecchia-app"
                    >
                        <Upload className={`h-4 w-4 mr-2 ${migrating ? 'animate-bounce' : ''}`} />
                        {migrating ? 'Importazione in corso...' : 'Importa da Vecchia App'}
                    </Button>
                    {totale > 0 && (
                        <p className="text-xs text-gray-500">Puoi rieseguire senza rischi: i duplicati vengono saltati.</p>
                    )}
                </div>

                {result && (
                    <div className={`rounded-lg p-4 text-sm ${result.results ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border border-red-200'}`} data-testid="migration-result">
                        <p className="font-medium mb-1">{result.message}</p>
                        {result.results && (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                                <span className="text-blue-700">Anagrafica: <strong>{result.results.anagrafica}</strong></span>
                                <span className="text-blue-700">Preventivi: <strong>{result.results.preventivi}</strong></span>
                                <span className="text-blue-700">Fatt. Vendita: <strong>{result.results.fatture_vendita}</strong></span>
                                <span className="text-blue-700">Fatt. Acquisto: <strong>{result.results.fatture_acquisto}</strong></span>
                            </div>
                        )}
                        {result.results?.errors?.length > 0 && (
                            <div className="mt-2 text-red-600 text-xs">
                                {result.results.errors.map((e, i) => <p key={i}>{e}</p>)}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
