import { useState } from 'react';
import { apiRequest } from '../lib/utils';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Database, CheckCircle2, Loader2 } from 'lucide-react';

export default function MigrationWidget() {
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const runMigration = async () => {
        setRunning(true);
        setError(null);
        setResult(null);
        try {
            const res = await apiRequest('/admin/migration/backfill-client-snapshots', { method: 'POST' });
            setResult(res);
        } catch (e) {
            setError(e.message || 'Errore durante la migrazione');
        } finally {
            setRunning(false);
        }
    };

    return (
        <Card className="border-blue-200" data-testid="migration-widget">
            <CardContent className="py-3 px-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-blue-50">
                            <Database className="h-4 w-4 text-blue-600" />
                        </div>
                        <div>
                            <p className="text-xs font-semibold text-slate-700">Migrazione Snapshot Clienti</p>
                            {result ? (
                                <p className="text-[11px] text-emerald-600">
                                    {result.total_updated} aggiornati, {result.total_skipped} gia ok, {result.total_no_client} senza cliente
                                </p>
                            ) : (
                                <p className="text-[11px] text-slate-400">Aggiunge snapshot cliente ai documenti storici</p>
                            )}
                        </div>
                    </div>
                    <Button
                        size="sm"
                        variant={result ? 'ghost' : 'default'}
                        onClick={runMigration}
                        disabled={running}
                        className={result ? 'h-7 text-xs text-emerald-600' : 'h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white'}
                        data-testid="migration-run-btn"
                    >
                        {running ? (
                            <><Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> Migrazione...</>
                        ) : result ? (
                            <><CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Completata</>
                        ) : (
                            'Esegui Migrazione'
                        )}
                    </Button>
                </div>
                {error && <p className="text-[11px] text-red-500 mt-1">{error}</p>}
                {result?.collections && (
                    <div className="mt-2 grid grid-cols-4 gap-1">
                        {Object.entries(result.collections).map(([name, data]) => (
                            <div key={name} className="text-center bg-slate-50 rounded px-2 py-1">
                                <p className="text-[10px] text-slate-400 capitalize">{name}</p>
                                <p className="text-xs font-semibold text-slate-700">{data.updated}</p>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
