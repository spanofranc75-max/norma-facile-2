/**
 * DiagnosticaTab — Shows raw company_settings data from the database.
 * Helps debug issues where PDF/email show wrong company data.
 */
import { useState } from 'react';
import { apiRequest } from '../../lib/utils';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { Bug, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

export default function DiagnosticaTab() {
    const [diagnostics, setDiagnostics] = useState(null);
    const [loading, setLoading] = useState(false);

    const runDiagnostics = async () => {
        setLoading(true);
        try {
            const data = await apiRequest('/company/settings/diagnostics');
            setDiagnostics(data);
        } catch (err) {
            toast.error('Errore: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-4" data-testid="diagnostica-tab">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                    <div>
                        <h3 className="font-semibold text-amber-900">Strumento diagnostico</h3>
                        <p className="text-sm text-amber-800 mt-1">
                            Questo strumento mostra i dati aziendali <strong>esattamente come sono salvati nel database</strong>.
                            Utile per capire perche i PDF o le email mostrano dati diversi da quelli inseriti.
                        </p>
                    </div>
                </div>
            </div>

            <Button
                onClick={runDiagnostics}
                disabled={loading}
                variant="outline"
                className="gap-2"
                data-testid="btn-run-diagnostics"
            >
                {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Bug className="h-4 w-4" />}
                {loading ? 'Analisi in corso...' : 'Esegui Diagnostica'}
            </Button>

            {diagnostics && (
                <div className="space-y-4">
                    {/* Warnings */}
                    {diagnostics.warnings?.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
                            <h4 className="font-semibold text-red-900 flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4" />
                                Problemi trovati
                            </h4>
                            {diagnostics.warnings.map((w, i) => (
                                <p key={i} className="text-sm text-red-800 pl-6">- {w}</p>
                            ))}
                        </div>
                    )}
                    {diagnostics.warnings?.length === 0 && (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                            <p className="text-green-800 flex items-center gap-2 font-medium">
                                <CheckCircle className="h-4 w-4" />
                                Nessun problema rilevato
                            </p>
                        </div>
                    )}

                    {/* Overview */}
                    <div className="bg-white border rounded-lg p-4 space-y-3">
                        <h4 className="font-semibold text-slate-800">Panoramica collezione</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            <span className="text-slate-500">Il tuo user_id:</span>
                            <span className="font-mono text-xs break-all">{diagnostics.current_user_id}</span>
                            <span className="text-slate-500">Totale documenti nella collezione:</span>
                            <span className="font-semibold">{diagnostics.total_company_settings_docs}</span>
                            <span className="text-slate-500">Documenti per il tuo account:</span>
                            <span className="font-semibold">{diagnostics.docs_for_current_user}</span>
                            <span className="text-slate-500">Tutti i user_id presenti:</span>
                            <span className="font-mono text-xs break-all">{diagnostics.all_user_ids_in_collection?.join(', ') || 'nessuno'}</span>
                        </div>
                    </div>

                    {/* Current user document */}
                    {diagnostics.current_user_document && (
                        <div className="bg-white border rounded-lg p-4 space-y-3">
                            <h4 className="font-semibold text-slate-800">I tuoi dati nel database</h4>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                {Object.entries(diagnostics.current_user_document).map(([k, v]) => (
                                    <div key={k} className="contents">
                                        <span className="text-slate-500">{k}:</span>
                                        <span className={`font-mono text-xs break-all ${!v ? 'text-red-400 italic' : ''}`}>
                                            {v || '(vuoto)'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* First doc warning */}
                    {diagnostics.first_doc_in_collection && diagnostics.first_doc_in_collection.user_id !== diagnostics.current_user_id && (
                        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                            <h4 className="font-semibold text-orange-900">Primo documento nella collezione (potenziale conflitto)</h4>
                            <p className="text-sm text-orange-800 mt-1">
                                user_id: <code className="bg-orange-100 px-1 rounded">{diagnostics.first_doc_in_collection.user_id}</code><br/>
                                business_name: <code className="bg-orange-100 px-1 rounded">{diagnostics.first_doc_in_collection.business_name || '(vuoto)'}</code>
                            </p>
                            <p className="text-sm text-orange-700 mt-2">
                                Questo documento non e tuo ma verrebbe restituito da query senza filtro user_id.
                            </p>
                        </div>
                    )}

                    {/* Legacy */}
                    {diagnostics.legacy_settings_collection?.exists && (
                        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                            <h4 className="font-semibold text-purple-900">Collezione legacy "settings"</h4>
                            <p className="text-sm text-purple-800">
                                ragione_sociale: <code className="bg-purple-100 px-1 rounded">{diagnostics.legacy_settings_collection.ragione_sociale || '(vuoto)'}</code>
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
