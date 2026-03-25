import { useRef, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { FileText, Eye, EyeOff } from 'lucide-react';

const PLACEHOLDERS = [
    { key: 'ragione_sociale', label: 'Ragione Sociale', group: 'azienda' },
    { key: 'indirizzo', label: 'Indirizzo completo', group: 'azienda' },
    { key: 'partita_iva', label: 'P.IVA', group: 'azienda' },
    { key: 'codice_fiscale', label: 'Cod. Fiscale', group: 'azienda' },
    { key: 'pec', label: 'PEC', group: 'azienda' },
    { key: 'telefono', label: 'Telefono', group: 'azienda' },
    { key: 'email_azienda', label: 'Email', group: 'azienda' },
    { key: 'pagamento', label: 'Tipo pagamento', group: 'documento' },
    { key: 'validita', label: 'Giorni validita', group: 'documento' },
    { key: 'consegna', label: 'Tempi consegna', group: 'documento' },
    { key: 'numero_documento', label: 'N. documento', group: 'documento' },
    { key: 'data_documento', label: 'Data documento', group: 'documento' },
];

function renderPreview(text, settings) {
    if (!text) return '';
    let preview = text;
    const map = {
        ragione_sociale: settings.business_name || 'Azienda S.r.l.',
        indirizzo: [settings.address, settings.cap, settings.city, settings.province ? `(${settings.province})` : ''].filter(Boolean).join(' - ') || 'Via Esempio 1 - 00000 Citta',
        partita_iva: settings.partita_iva || 'IT00000000000',
        codice_fiscale: settings.codice_fiscale || '',
        pec: settings.pec || '',
        telefono: settings.phone || '',
        email_azienda: settings.email || '',
        pagamento: 'BB 30 FM',
        validita: '30',
        consegna: '60 giorni',
        numero_documento: 'PRV-2026-0001',
        data_documento: new Date().toLocaleDateString('it-IT'),
    };
    for (const [k, v] of Object.entries(map)) {
        preview = preview.replaceAll(`{${k}}`, v || `{${k}}`);
    }
    return preview;
}

export default function CondizioniTab({ settings, updateField }) {
    const textareaRef = useRef(null);
    const [showPreview, setShowPreview] = useState(false);

    const insertPlaceholder = (key) => {
        const el = textareaRef.current;
        if (!el) return;
        const tag = `{${key}}`;
        const start = el.selectionStart ?? el.value.length;
        const end = el.selectionEnd ?? start;
        const before = el.value.substring(0, start);
        const after = el.value.substring(end);
        const newVal = before + tag + after;
        updateField('condizioni_vendita', newVal);
        setTimeout(() => {
            el.focus();
            const pos = start + tag.length;
            el.setSelectionRange(pos, pos);
        }, 0);
    };

    const azienda = PLACEHOLDERS.filter(p => p.group === 'azienda');
    const documento = PLACEHOLDERS.filter(p => p.group === 'documento');

    return (
        <Card className="border-gray-200" data-testid="card-condizioni-tab">
            <CardHeader className="bg-blue-50 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            Condizioni Generali di Vendita
                        </CardTitle>
                        <CardDescription>
                            Template stampato in calce a preventivi, fatture e DDT. Usa i segnaposti per valori dinamici.
                        </CardDescription>
                    </div>
                    <button
                        type="button"
                        data-testid="btn-toggle-preview"
                        onClick={() => setShowPreview(v => !v)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 bg-white hover:bg-gray-50 transition-colors"
                    >
                        {showPreview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        {showPreview ? 'Editor' : 'Anteprima'}
                    </button>
                </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
                {/* Placeholders legend */}
                <div className="space-y-2" data-testid="placeholders-legend">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Segnaposti disponibili — click per inserire</p>
                    <div className="space-y-1.5">
                        <div className="flex flex-wrap gap-1.5">
                            <span className="text-[10px] text-slate-400 w-16 pt-0.5">Azienda</span>
                            {azienda.map(p => (
                                <button
                                    key={p.key}
                                    type="button"
                                    data-testid={`placeholder-${p.key}`}
                                    onClick={() => insertPlaceholder(p.key)}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors cursor-pointer"
                                    title={`Inserisci {${p.key}}`}
                                >
                                    {`{${p.key}}`}
                                    <span className="text-[9px] text-blue-400 font-sans">{p.label}</span>
                                </button>
                            ))}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                            <span className="text-[10px] text-slate-400 w-16 pt-0.5">Documento</span>
                            {documento.map(p => (
                                <button
                                    key={p.key}
                                    type="button"
                                    data-testid={`placeholder-${p.key}`}
                                    onClick={() => insertPlaceholder(p.key)}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono bg-amber-50 text-amber-700 border border-amber-200 rounded hover:bg-amber-100 transition-colors cursor-pointer"
                                    title={`Inserisci {${p.key}}`}
                                >
                                    {`{${p.key}}`}
                                    <span className="text-[9px] text-amber-400 font-sans">{p.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Editor or Preview */}
                {showPreview ? (
                    <div data-testid="condizioni-preview">
                        <Label className="mb-1 block">Anteprima (con valori di esempio)</Label>
                        <div className="rounded-md border border-gray-200 bg-white p-4 text-sm whitespace-pre-wrap font-serif leading-relaxed min-h-[260px] text-gray-800">
                            {renderPreview(settings.condizioni_vendita, settings) || (
                                <span className="text-slate-400 italic">Nessun testo inserito</span>
                            )}
                        </div>
                    </div>
                ) : (
                    <div>
                        <Label htmlFor="condizioni_vendita">Testo condizioni</Label>
                        <Textarea
                            ref={textareaRef}
                            id="condizioni_vendita"
                            data-testid="input-condizioni-vendita"
                            value={settings.condizioni_vendita}
                            onChange={(e) => updateField('condizioni_vendita', e.target.value)}
                            placeholder={"Es: La {ragione_sociale}, con sede in {indirizzo}, P.IVA {partita_iva}, propone...\n\nPagamento: {pagamento}\nValidita offerta: {validita} giorni dalla data di emissione"}
                            rows={14}
                            className="font-mono text-sm"
                        />
                    </div>
                )}

                <p className="text-xs text-slate-400">
                    I segnaposti tra parentesi graffe vengono sostituiti automaticamente con i dati reali nel PDF.
                    Il testo viene stampato nella seconda pagina di ogni preventivo generato.
                </p>
            </CardContent>
        </Card>
    );
}
