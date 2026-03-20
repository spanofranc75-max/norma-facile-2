/**
 * MontaggioPanel — Diario di Montaggio per Vista Officina.
 * 
 * 4 sezioni:
 * 1. Analisi DDT Bulloneria (AI Vision + confronto visivo)
 * 2. Serraggio Intelligente (coppia Nm auto + checklist SI/NO)
 * 3. Cantiere (fondazioni OK/NOK + foto giunti e ancoraggi)
 * 4. Firma Cliente (canvas touch per verbale fine lavori)
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// ── Sub-step navigation ──
const STEPS = [
    { id: 'sicurezza', label: 'SICUREZZA', icon: '🛡️' },
    { id: 'ddt', label: 'DDT', icon: '📋' },
    { id: 'serraggio', label: 'SERRAGGIO', icon: '🔧' },
    { id: 'varianti', label: 'VARIANTI', icon: '📝' },
    { id: 'cantiere', label: 'CANTIERE', icon: '🏗️' },
    { id: 'firma', label: 'FIRMA', icon: '✍️' },
];

export default function MontaggioPanel({ commessaId, voceId, selectedOp, normativa }) {
    const [step, setStep] = useState('sicurezza');
    const [sicurezzaDone, setSicurezzaDone] = useState(false);
    const [ddtData, setDdtData] = useState(null);
    const [savedDdts, setSavedDdts] = useState([]);
    const [montaggioId, setMontaggioId] = useState(null);
    const [serraggi, setSerraggi] = useState([]);
    const [fondazioniOk, setFondazioniOk] = useState(null);
    const [fotoGiunti, setFotoGiunti] = useState([]);
    const [fotoAncoraggi, setFotoAncoraggi] = useState([]);
    const [firmaCompleta, setFirmaCompleta] = useState(false);
    const [varianti, setVarianti] = useState([]);

    // Load existing DDTs for this commessa/voce
    useEffect(() => {
        const loadDdts = async () => {
            try {
                const res = await fetch(`${API}/api/montaggio/ddt/${commessaId}?voce_id=${voceId || ''}`);
                if (res.ok) {
                    const data = await res.json();
                    setSavedDdts(data.ddts || []);
                }
            } catch (e) { /* ignore */ }
        };
        loadDdts();
    }, [commessaId, voceId]);

    return (
        <div className="max-w-lg mx-auto" data-testid="montaggio-panel">
            {/* Step indicator */}
            <div className="flex gap-1 mb-4">
                {STEPS.map((s) => (
                    <button
                        key={s.id}
                        data-testid={`montaggio-step-${s.id}`}
                        onClick={() => setStep(s.id)}
                        className={`flex-1 py-2 rounded-xl text-center transition-all text-xs font-bold
                            ${step === s.id
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                                : 'bg-slate-800 text-slate-500 hover:bg-slate-700'}`}
                    >
                        <span className="block text-lg">{s.icon}</span>
                        {s.label}
                    </button>
                ))}
            </div>

            {/* Step content */}
            {step === 'sicurezza' && (
                <SicurezzaCantiereSection
                    commessaId={commessaId}
                    voceId={voceId}
                    selectedOp={selectedOp}
                    sicurezzaDone={sicurezzaDone}
                    setSicurezzaDone={setSicurezzaDone}
                    onNext={() => setStep('ddt')}
                />
            )}
            {step === 'ddt' && (
                <DDTSection
                    commessaId={commessaId}
                    voceId={voceId}
                    selectedOp={selectedOp}
                    ddtData={ddtData}
                    setDdtData={setDdtData}
                    savedDdts={savedDdts}
                    setSavedDdts={setSavedDdts}
                    setSerraggi={setSerraggi}
                    onNext={() => setStep('serraggio')}
                />
            )}
            {step === 'serraggio' && (
                <SerraggioSection
                    serraggi={serraggi}
                    setSerraggi={setSerraggi}
                    savedDdts={savedDdts}
                    onNext={() => setStep('varianti')}
                />
            )}
            {step === 'varianti' && (
                <VariantiSection
                    commessaId={commessaId}
                    voceId={voceId}
                    selectedOp={selectedOp}
                    varianti={varianti}
                    setVarianti={setVarianti}
                    onNext={() => setStep('cantiere')}
                />
            )}
            {step === 'cantiere' && (
                <CantiereSection
                    commessaId={commessaId}
                    voceId={voceId}
                    selectedOp={selectedOp}
                    fondazioniOk={fondazioniOk}
                    setFondazioniOk={setFondazioniOk}
                    fotoGiunti={fotoGiunti}
                    setFotoGiunti={setFotoGiunti}
                    fotoAncoraggi={fotoAncoraggi}
                    setFotoAncoraggi={setFotoAncoraggi}
                    onNext={() => setStep('firma')}
                />
            )}
            {step === 'firma' && (
                <FirmaSection
                    commessaId={commessaId}
                    voceId={voceId}
                    selectedOp={selectedOp}
                    serraggi={serraggi}
                    fondazioniOk={fondazioniOk}
                    fotoGiunti={fotoGiunti}
                    fotoAncoraggi={fotoAncoraggi}
                    montaggioId={montaggioId}
                    setMontaggioId={setMontaggioId}
                    firmaCompleta={firmaCompleta}
                    setFirmaCompleta={setFirmaCompleta}
                />
            )}
        </div>
    );
}


// ══════════════════════════════════════════════════════════════
//  SEZIONE 0: SICUREZZA CANTIERE (checklist + foto panoramica)
// ══════════════════════════════════════════════════════════════

function SicurezzaCantiereSection({ commessaId, voceId, selectedOp, sicurezzaDone, setSicurezzaDone, onNext }) {
    const [checks, setChecks] = useState([
        { codice: 'area_delimitata', label: 'Area delimitata?', esito: false },
        { codice: 'dpi_indossati', label: 'DPI indossati?', esito: false },
        { codice: 'attrezzature_verificate', label: 'Attrezzature verificate?', esito: false },
    ]);
    const [fotoDocId, setFotoDocId] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [saving, setSaving] = useState(false);
    const fileRef = useRef(null);

    // Check if already completed
    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API}/api/sicurezza/cantiere/${commessaId}?voce_id=${voceId || ''}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.sicurezza && data.sicurezza.all_ok) {
                        setSicurezzaDone(true);
                    }
                }
            } catch { /* ignore */ }
        };
        load();
    }, [commessaId, voceId, setSicurezzaDone]);

    const toggleCheck = (idx) => {
        setChecks(prev => prev.map((c, i) => i === idx ? { ...c, esito: !c.esito } : c));
    };

    const handleUploadFoto = async (file) => {
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('voce_id', voceId || '');
            formData.append('operatore_id', selectedOp.op_id);
            formData.append('operatore_nome', selectedOp.nome);
            formData.append('tipo_foto', 'sicurezza_cantiere');

            const res = await fetch(`${API}/api/montaggio/foto/${commessaId}`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Upload fallito');
            const data = await res.json();
            setFotoDocId(data.doc_id);
            toast.success('Foto panoramica caricata');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUploading(false);
        }
    };

    const handleSave = async () => {
        if (!checks.every(c => c.esito)) { toast.error('Tutti i controlli devono essere confermati'); return; }
        if (!fotoDocId) { toast.error('Foto panoramica obbligatoria'); return; }
        setSaving(true);
        try {
            const res = await fetch(`${API}/api/sicurezza/cantiere`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    commessa_id: commessaId,
                    voce_id: voceId || '',
                    operatore_id: selectedOp.op_id,
                    operatore_nome: selectedOp.nome,
                    checklist: checks,
                    foto_panoramica_doc_id: fotoDocId,
                }),
            });
            if (!res.ok) throw new Error('Salvataggio fallito');
            setSicurezzaDone(true);
            toast.success('Sicurezza cantiere confermata');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    if (sicurezzaDone) {
        return (
            <div data-testid="sicurezza-done" className="text-center py-8">
                <span className="text-6xl block mb-3">🛡️</span>
                <p className="text-green-400 text-xl font-bold">Cantiere in Sicurezza</p>
                <p className="text-slate-500 text-sm mt-2">Checklist completata. Puoi procedere.</p>
                <button onClick={onNext} data-testid="btn-next-from-sicurezza"
                    className="mt-4 w-full h-14 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-lg transition-all active:scale-95">
                    Avanti: DDT →
                </button>
            </div>
        );
    }

    const allChecked = checks.every(c => c.esito);
    const canSave = allChecked && fotoDocId;

    return (
        <div data-testid="sicurezza-cantiere-section">
            <p className="text-slate-400 text-center text-base mb-4 font-medium">Sicurezza Cantiere</p>
            <p className="text-red-400 text-xs text-center mb-4 font-bold">OBBLIGATORIO — Completa prima di procedere</p>

            {/* Checklist */}
            <div className="space-y-2 mb-4">
                {checks.map((c, idx) => (
                    <button
                        key={c.codice}
                        data-testid={`sic-check-${c.codice}`}
                        onClick={() => toggleCheck(idx)}
                        className={`w-full h-14 rounded-2xl flex items-center justify-between px-5 transition-all active:scale-[0.98]
                            ${c.esito ? 'bg-green-600 text-white shadow-lg shadow-green-600/30' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border-2 border-slate-700'}`}
                    >
                        <span className="font-bold text-sm">{c.label}</span>
                        <span className="text-xl">{c.esito ? '✓ SI' : 'NO'}</span>
                    </button>
                ))}
            </div>

            {/* Mandatory panoramic photo */}
            <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUploadFoto(f); if (fileRef.current) fileRef.current.value = ''; }}
                data-testid="sic-foto-input"
            />
            <button
                data-testid="btn-foto-panoramica"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className={`w-full h-16 rounded-2xl font-bold text-lg mb-4 transition-all active:scale-95
                    ${fotoDocId ? 'bg-green-600 text-white' : uploading ? 'bg-blue-500/20 text-blue-400 animate-pulse' : 'bg-slate-800 text-slate-300 border-2 border-dashed border-slate-600 hover:border-blue-500'}`}
            >
                {uploading ? 'Caricamento...' : fotoDocId ? '📷 Foto Panoramica OK' : '📷 Foto Panoramica Cantiere (obbligatoria)'}
            </button>

            {!canSave && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-center mb-3">
                    <p className="text-red-400 text-xs font-bold">
                        {!allChecked && 'Conferma tutti i controlli sicurezza. '}
                        {!fotoDocId && 'Serve la foto panoramica del cantiere.'}
                    </p>
                </div>
            )}

            <button
                data-testid="btn-conferma-sicurezza"
                onClick={handleSave}
                disabled={!canSave || saving}
                className={`w-full h-14 rounded-2xl font-bold text-lg transition-all active:scale-95
                    ${canSave ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-600/30' : 'bg-slate-700 text-slate-500'}`}
            >
                {saving ? 'Salvataggio...' : 'Conferma Sicurezza e Prosegui'}
            </button>
        </div>
    );
}


// ══════════════════════════════════════════════════════════════
//  SEZIONE 1: DDT BULLONERIA (AI Vision + confronto visivo)
// ══════════════════════════════════════════════════════════════

function DDTSection({ commessaId, voceId, selectedOp, ddtData, setDdtData, savedDdts, setSavedDdts, setSerraggi, onNext }) {
    const [analyzing, setAnalyzing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [showCompare, setShowCompare] = useState(false);
    const [previewUrl, setPreviewUrl] = useState(null);
    const fileRef = useRef(null);
    const boxFileRef = useRef(null);

    const handleDDTUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Show preview
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);

        setAnalyzing(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('commessa_id', commessaId);
            formData.append('voce_id', voceId || '');

            const res = await fetch(`${API}/api/montaggio/ddt/analyze`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Analisi fallita');
            const data = await res.json();
            setDdtData(data.analysis);
            toast.success(`Trovati ${(data.analysis?.articoli || []).length} articoli`);
        } catch (e) {
            toast.error('Errore analisi DDT: ' + e.message);
        } finally {
            setAnalyzing(false);
            if (fileRef.current) fileRef.current.value = '';
        }
    };

    const handleSave = async () => {
        if (!ddtData?.articoli?.length) return;
        setSaving(true);
        try {
            const res = await fetch(`${API}/api/montaggio/ddt/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    commessa_id: commessaId,
                    voce_id: voceId || '',
                    fornitore: ddtData.fornitore || '',
                    numero_ddt: ddtData.numero_ddt || '',
                    data_ddt: ddtData.data_ddt || '',
                    lotto_generale: ddtData.lotto_generale || '',
                    bulloni: ddtData.articoli.map(a => ({
                        diametro: a.diametro || '',
                        classe: a.classe || '',
                        lotto: a.lotto || ddtData.lotto_generale || '',
                        quantita: a.quantita || '',
                        descrizione: a.descrizione || '',
                    })),
                    source: 'ai_vision',
                }),
            });
            if (!res.ok) throw new Error('Salvataggio fallito');
            const saved = await res.json();
            setSavedDdts(prev => [saved, ...prev]);

            // Auto-populate serraggi from saved DDT bulloni
            const newSerraggi = (saved.bulloni || []).map(b => ({
                diametro: b.diametro,
                classe: b.classe,
                coppia_nm: b.coppia_nm || null,
                confermato: false,
                chiave_dinamometrica: false,
            }));
            setSerraggi(prev => [...prev, ...newSerraggi]);

            toast.success('DDT salvato');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div data-testid="ddt-section">
            <p className="text-slate-400 text-center text-base mb-4 font-medium">Analisi DDT Bulloneria</p>

            <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleDDTUpload} data-testid="ddt-file-input" />

            {/* Upload button */}
            <button
                data-testid="btn-upload-ddt"
                onClick={() => fileRef.current?.click()}
                disabled={analyzing}
                className={`w-full h-20 rounded-2xl border-2 border-dashed transition-all flex items-center justify-center gap-3 text-lg font-bold
                    ${analyzing ? 'border-blue-500 bg-blue-500/10 text-blue-400 animate-pulse' : 'border-slate-600 bg-slate-800 text-slate-400 hover:border-blue-500 hover:text-blue-400 active:scale-[0.98]'}`}
            >
                {analyzing ? (
                    <><span className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" /> Analisi AI in corso...</>
                ) : (
                    <>📋 Scatta foto DDT</>
                )}
            </button>

            {/* Preview DDT photo */}
            {previewUrl && (
                <div className="mt-3 rounded-xl overflow-hidden border border-slate-700">
                    <img src={previewUrl} alt="DDT" className="w-full max-h-48 object-contain bg-slate-800" data-testid="ddt-preview" />
                </div>
            )}

            {/* AI Results */}
            {ddtData && ddtData.articoli && ddtData.articoli.length > 0 && (
                <div className="mt-4 bg-slate-800 rounded-2xl p-4 border border-slate-700" data-testid="ddt-results">
                    <div className="flex items-center justify-between mb-3">
                        <p className="text-white font-bold">Dati Estratti dal DDT</p>
                        <span className="bg-green-600 text-white text-xs px-2 py-1 rounded-full font-bold">
                            {ddtData.articoli.length} articoli
                        </span>
                    </div>

                    {ddtData.fornitore && (
                        <p className="text-slate-400 text-sm mb-2">Fornitore: <span className="text-white">{ddtData.fornitore}</span></p>
                    )}
                    {ddtData.numero_ddt && (
                        <p className="text-slate-400 text-sm mb-2">DDT N.: <span className="text-white">{ddtData.numero_ddt}</span></p>
                    )}

                    {/* Bolt table */}
                    <div className="overflow-x-auto mt-2">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-slate-400 text-xs border-b border-slate-700">
                                    <th className="text-left py-2 px-1">Diam.</th>
                                    <th className="text-left py-2 px-1">Classe</th>
                                    <th className="text-left py-2 px-1">Lotto</th>
                                    <th className="text-right py-2 px-1">Coppia</th>
                                </tr>
                            </thead>
                            <tbody>
                                {ddtData.articoli.map((art, i) => (
                                    <tr key={i} className="border-b border-slate-700/50">
                                        <td className="py-2 px-1 text-white font-bold">{art.diametro}</td>
                                        <td className="py-2 px-1 text-amber-400">{art.classe}</td>
                                        <td className="py-2 px-1 text-slate-400 text-xs">{art.lotto || '—'}</td>
                                        <td className="py-2 px-1 text-right text-green-400 font-mono">
                                            {art.coppia_nm ? `${art.coppia_nm} Nm` : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Save + Compare buttons */}
                    <div className="flex gap-2 mt-4">
                        <button
                            data-testid="btn-save-ddt"
                            onClick={handleSave}
                            disabled={saving}
                            className="flex-1 h-12 rounded-xl bg-green-600 hover:bg-green-500 text-white font-bold transition-all active:scale-95"
                        >
                            {saving ? 'Salvataggio...' : 'Salva DDT'}
                        </button>
                        <button
                            data-testid="btn-compare-ddt"
                            onClick={() => setShowCompare(!showCompare)}
                            className="h-12 px-4 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-300 font-bold transition-all"
                        >
                            📷 Confronta
                        </button>
                    </div>
                </div>
            )}

            {/* Compare mode: take photo of box for visual comparison */}
            {showCompare && (
                <div className="mt-3 bg-amber-500/10 border border-amber-500/30 rounded-xl p-4" data-testid="ddt-compare">
                    <p className="text-amber-400 text-sm font-bold mb-2">Confronto Visivo</p>
                    <p className="text-slate-400 text-xs mb-3">Scatta una foto della scatola bulloni per confrontarla con i dati DDT</p>
                    <input ref={boxFileRef} type="file" accept="image/*" capture="environment" className="hidden"
                        onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) {
                                const url = URL.createObjectURL(f);
                                setPreviewUrl(url);
                                toast.success('Foto scatola caricata — confronta visivamente con i dati sopra');
                            }
                        }}
                        data-testid="box-photo-input"
                    />
                    <button
                        onClick={() => boxFileRef.current?.click()}
                        className="w-full h-14 rounded-xl bg-amber-500 text-slate-900 font-bold active:scale-95 transition-all"
                        data-testid="btn-photo-box"
                    >
                        📷 Foto Scatola Bulloni
                    </button>
                </div>
            )}

            {/* Previously saved DDTs */}
            {savedDdts.length > 0 && (
                <div className="mt-4" data-testid="saved-ddts">
                    <p className="text-slate-500 text-xs font-bold mb-2">DDT Salvati ({savedDdts.length})</p>
                    {savedDdts.map(ddt => (
                        <div key={ddt.ddt_id} className="bg-slate-800/50 rounded-xl p-3 mb-2 border border-slate-700/50">
                            <div className="flex justify-between items-center">
                                <span className="text-white text-sm font-bold">{ddt.fornitore || 'DDT'} {ddt.numero_ddt && `#${ddt.numero_ddt}`}</span>
                                <span className="text-slate-500 text-xs">{ddt.bulloni?.length || 0} bulloni</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <button
                data-testid="btn-next-serraggio"
                onClick={onNext}
                className="w-full h-14 mt-4 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-lg transition-all active:scale-95"
            >
                Avanti: Serraggio →
            </button>
        </div>
    );
}


// ══════════════════════════════════════════════════════════════
//  SEZIONE 2: SERRAGGIO INTELLIGENTE
// ══════════════════════════════════════════════════════════════

function SerraggioSection({ serraggi, setSerraggi, savedDdts, onNext }) {
    const [taraturaAlert, setTaraturaAlert] = useState(null);

    // Auto-populate from saved DDTs if serraggi is empty
    useEffect(() => {
        if (serraggi.length === 0 && savedDdts.length > 0) {
            const items = [];
            for (const ddt of savedDdts) {
                for (const b of (ddt.bulloni || [])) {
                    items.push({
                        diametro: b.diametro,
                        classe: b.classe,
                        coppia_nm: b.coppia_nm || null,
                        confermato: false,
                        chiave_dinamometrica: false,
                    });
                }
            }
            if (items.length > 0) setSerraggi(items);
        }
    }, [savedDdts, serraggi.length, setSerraggi]);

    // Check torque wrench calibration
    useEffect(() => {
        const check = async () => {
            try {
                const res = await fetch(`${API}/api/attrezzature/check-taratura`, { credentials: 'include' });
                if (res.ok) {
                    const data = await res.json();
                    if (!data.tutte_valide) {
                        setTaraturaAlert(data);
                    }
                }
            } catch { /* non-blocking */ }
        };
        check();
    }, []);

    const toggleField = (idx, field) => {
        setSerraggi(prev => prev.map((s, i) => i === idx ? { ...s, [field]: !s[field] } : s));
    };

    const allConfirmed = serraggi.length > 0 && serraggi.every(s => s.confermato && s.chiave_dinamometrica);

    return (
        <div data-testid="serraggio-section">
            <p className="text-slate-400 text-center text-base mb-4 font-medium">Serraggio Intelligente</p>

            {/* Taratura alert */}
            {taraturaAlert && taraturaAlert.scadute?.length > 0 && (
                <div className="bg-red-500/10 border-2 border-red-500/30 rounded-2xl p-3 mb-4" data-testid="taratura-alert-serraggio">
                    <p className="text-red-400 text-sm font-bold mb-1">TARATURA SCADUTA</p>
                    {taraturaAlert.scadute.map((c, i) => (
                        <p key={i} className="text-red-300 text-xs">{c.modello} (S/N: {c.numero_serie || 'N/D'}) — scaduta da {Math.abs(c.giorni_rimasti)}gg</p>
                    ))}
                    <p className="text-red-500/60 text-xs mt-1">Avvisare l'Admin per rinnovo taratura.</p>
                </div>
            )}

            {serraggi.length === 0 ? (
                <div className="text-center py-10">
                    <span className="text-5xl block mb-3">🔧</span>
                    <p className="text-slate-500 text-sm">Nessun bullone da serrare.</p>
                    <p className="text-slate-600 text-xs mt-1">Carica prima un DDT nella sezione precedente.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {serraggi.map((s, idx) => (
                        <div key={idx} className="bg-slate-800 rounded-2xl p-4 border-2 border-slate-700" data-testid={`serraggio-${idx}`}>
                            {/* Header: diameter + class + torque */}
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <span className="text-white text-xl font-black">{s.diametro}</span>
                                    <span className="text-amber-400 text-sm font-bold ml-2">cl. {s.classe}</span>
                                </div>
                                <div className="text-right">
                                    {s.coppia_nm ? (
                                        <div className="bg-green-600/20 border border-green-600 rounded-lg px-3 py-1">
                                            <span className="text-green-400 text-lg font-black font-mono">{s.coppia_nm}</span>
                                            <span className="text-green-500 text-xs ml-1">Nm</span>
                                        </div>
                                    ) : (
                                        <span className="text-slate-500 text-xs">N/D</span>
                                    )}
                                </div>
                            </div>

                            {/* Checklist */}
                            <div className="space-y-2">
                                <button
                                    data-testid={`serraggio-${idx}-confermato`}
                                    onClick={() => toggleField(idx, 'confermato')}
                                    className={`w-full h-12 rounded-xl flex items-center justify-between px-4 transition-all active:scale-[0.98]
                                        ${s.confermato ? 'bg-green-600 text-white' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'}`}
                                >
                                    <span className="font-bold text-sm">Serraggio corretto?</span>
                                    <span className="text-xl">{s.confermato ? '✓ SI' : 'NO'}</span>
                                </button>
                                <button
                                    data-testid={`serraggio-${idx}-chiave`}
                                    onClick={() => toggleField(idx, 'chiave_dinamometrica')}
                                    className={`w-full h-12 rounded-xl flex items-center justify-between px-4 transition-all active:scale-[0.98]
                                        ${s.chiave_dinamometrica ? 'bg-green-600 text-white' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'}`}
                                >
                                    <span className="font-bold text-sm">Chiave dinamometrica usata?</span>
                                    <span className="text-xl">{s.chiave_dinamometrica ? '✓ SI' : 'NO'}</span>
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Summary */}
            {serraggi.length > 0 && (
                <div className={`mt-4 p-3 rounded-xl text-center text-sm font-bold ${allConfirmed ? 'bg-green-600/20 text-green-400 border border-green-600/30' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'}`}>
                    {allConfirmed ? 'Tutti i serraggi confermati' : `${serraggi.filter(s => s.confermato && s.chiave_dinamometrica).length}/${serraggi.length} serraggi confermati`}
                </div>
            )}

            <button
                data-testid="btn-next-cantiere"
                onClick={onNext}
                className="w-full h-14 mt-4 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-lg transition-all active:scale-95"
            >
                Avanti: Cantiere →
            </button>
        </div>
    );
}


// ══════════════════════════════════════════════════════════════
//  SEZIONE 2.5: VARIANTI (note di variante con foto obbligatoria)
// ══════════════════════════════════════════════════════════════

function VariantiSection({ commessaId, voceId, selectedOp, varianti, setVarianti, onNext }) {
    const [descrizione, setDescrizione] = useState('');
    const [uploading, setUploading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [fotoDocId, setFotoDocId] = useState(null);
    const fileRef = useRef(null);

    // Load existing varianti
    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API}/api/montaggio/varianti/${commessaId}?voce_id=${voceId || ''}`);
                if (res.ok) {
                    const data = await res.json();
                    setVarianti(data.varianti || []);
                }
            } catch { /* ignore */ }
        };
        load();
    }, [commessaId, voceId, setVarianti]);

    const handleUploadFoto = async (file) => {
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('voce_id', voceId || '');
            formData.append('operatore_id', selectedOp.op_id);
            formData.append('operatore_nome', selectedOp.nome);
            formData.append('tipo_foto', 'variante');

            const res = await fetch(`${API}/api/montaggio/foto/${commessaId}`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Upload fallito');
            const data = await res.json();
            setFotoDocId(data.doc_id);
            toast.success('Foto variante caricata');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUploading(false);
        }
    };

    const handleSave = async () => {
        if (!descrizione.trim()) { toast.error('Descrizione obbligatoria'); return; }
        if (!fotoDocId) { toast.error('Foto obbligatoria per la variante'); return; }
        setSaving(true);
        try {
            const res = await fetch(`${API}/api/montaggio/variante`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    commessa_id: commessaId,
                    voce_id: voceId || '',
                    operatore_id: selectedOp.op_id,
                    operatore_nome: selectedOp.nome,
                    descrizione: descrizione.trim(),
                    foto_doc_id: fotoDocId,
                }),
            });
            if (!res.ok) throw new Error('Salvataggio fallito');
            const saved = await res.json();
            setVarianti(prev => [saved, ...prev]);
            setDescrizione('');
            setFotoDocId(null);
            toast.success('Nota di variante salvata');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div data-testid="varianti-section">
            <p className="text-slate-400 text-center text-base mb-4 font-medium">Note di Variante</p>

            {/* New variant form */}
            <div className="bg-amber-500/10 border-2 border-amber-500/30 rounded-2xl p-4 mb-4" data-testid="variante-form">
                <p className="text-amber-400 text-sm font-bold mb-3">Nuova Variante</p>

                <textarea
                    data-testid="variante-descrizione"
                    value={descrizione}
                    onChange={e => setDescrizione(e.target.value)}
                    placeholder="Descrivi la variante rispetto al progetto originale..."
                    className="w-full h-24 bg-slate-800 border-2 border-slate-700 rounded-xl px-4 py-3 text-white text-sm placeholder-slate-600 focus:border-amber-500 focus:outline-none resize-none"
                />

                <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUploadFoto(f); if (fileRef.current) fileRef.current.value = ''; }}
                    data-testid="variante-foto-input"
                />

                <div className="flex gap-2 mt-3">
                    <button
                        data-testid="btn-foto-variante"
                        onClick={() => fileRef.current?.click()}
                        disabled={uploading}
                        className={`flex-1 h-12 rounded-xl font-bold transition-all active:scale-95
                            ${fotoDocId ? 'bg-green-600 text-white' : uploading ? 'bg-blue-500/20 text-blue-400 animate-pulse' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                    >
                        {uploading ? 'Caricamento...' : fotoDocId ? '📷 Foto OK' : '📷 Foto (obbligatoria)'}
                    </button>
                    <button
                        data-testid="btn-save-variante"
                        onClick={handleSave}
                        disabled={saving || !descrizione.trim() || !fotoDocId}
                        className={`flex-1 h-12 rounded-xl font-bold transition-all active:scale-95
                            ${descrizione.trim() && fotoDocId ? 'bg-amber-500 text-slate-900 hover:bg-amber-400' : 'bg-slate-700 text-slate-500'}`}
                    >
                        {saving ? 'Salvataggio...' : 'Salva Variante'}
                    </button>
                </div>
            </div>

            {/* Existing varianti */}
            {varianti.length > 0 && (
                <div className="space-y-2 mb-4" data-testid="varianti-list">
                    <p className="text-slate-500 text-xs font-bold">Varianti registrate ({varianti.length})</p>
                    {varianti.map(v => (
                        <div key={v.variante_id} className="bg-slate-800 rounded-xl p-3 border border-amber-500/20">
                            <div className="flex items-start gap-2">
                                <span className="text-amber-400 text-lg">📝</span>
                                <div className="min-w-0 flex-1">
                                    <p className="text-white text-sm">{v.descrizione}</p>
                                    <p className="text-slate-500 text-xs mt-1">{v.operatore_nome} — {new Date(v.created_at).toLocaleDateString('it-IT')}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {varianti.length === 0 && (
                <p className="text-slate-600 text-xs text-center mb-4">Nessuna variante. Se non ci sono modifiche, prosegui.</p>
            )}

            <button
                data-testid="btn-next-cantiere-from-varianti"
                onClick={onNext}
                className="w-full h-14 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-lg transition-all active:scale-95"
            >
                Avanti: Cantiere →
            </button>
        </div>
    );
}


// ══════════════════════════════════════════════════════════════
//  SEZIONE 3: CANTIERE (fondazioni + foto obbligatorie)
// ══════════════════════════════════════════════════════════════

function CantiereSection({ commessaId, voceId, selectedOp, fondazioniOk, setFondazioniOk, fotoGiunti, setFotoGiunti, fotoAncoraggi, setFotoAncoraggi, onNext }) {
    const [uploading, setUploading] = useState(null); // 'giunti' or 'ancoraggi'
    const giuntiRef = useRef(null);
    const ancoraggiRef = useRef(null);

    const handleUpload = async (file, tipo) => {
        setUploading(tipo);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('voce_id', voceId || '');
            formData.append('operatore_id', selectedOp.op_id);
            formData.append('operatore_nome', selectedOp.nome);
            formData.append('tipo_foto', tipo);

            const res = await fetch(`${API}/api/montaggio/foto/${commessaId}`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Upload fallito');
            const data = await res.json();

            if (tipo === 'giunti') {
                setFotoGiunti(prev => [...prev, data.doc_id]);
            } else {
                setFotoAncoraggi(prev => [...prev, data.doc_id]);
            }
            toast.success(`Foto ${tipo} salvata`);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUploading(null);
        }
    };

    const canProceed = fondazioniOk !== null && fotoGiunti.length > 0 && fotoAncoraggi.length > 0;

    return (
        <div data-testid="cantiere-section">
            <p className="text-slate-400 text-center text-base mb-4 font-medium">Controllo Cantiere</p>

            {/* Fondazioni check */}
            <div className="bg-slate-800 rounded-2xl p-4 border-2 border-slate-700 mb-4" data-testid="fondazioni-check">
                <p className="text-white font-bold text-lg mb-3">Fondazioni / Appoggi idonei?</p>
                <div className="flex gap-3">
                    <button
                        data-testid="fondazioni-ok"
                        onClick={() => setFondazioniOk(true)}
                        className={`flex-1 h-16 rounded-2xl text-3xl font-black transition-all active:scale-95
                            ${fondazioniOk === true ? 'bg-green-600 text-white shadow-lg shadow-green-600/30 ring-2 ring-green-400' : 'bg-slate-700 text-slate-500 hover:bg-slate-600'}`}
                    >
                        👍
                    </button>
                    <button
                        data-testid="fondazioni-nok"
                        onClick={() => setFondazioniOk(false)}
                        className={`flex-1 h-16 rounded-2xl text-3xl font-black transition-all active:scale-95
                            ${fondazioniOk === false ? 'bg-red-600 text-white shadow-lg shadow-red-600/30 ring-2 ring-red-400' : 'bg-slate-700 text-slate-500 hover:bg-slate-600'}`}
                    >
                        👎
                    </button>
                </div>
            </div>

            {/* Foto giunti serrati (mandatory) */}
            <div className="bg-slate-800 rounded-2xl p-4 border-2 border-slate-700 mb-4" data-testid="foto-giunti-section">
                <div className="flex items-center justify-between mb-3">
                    <p className="text-white font-bold">Foto Giunti Serrati</p>
                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${fotoGiunti.length > 0 ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
                        {fotoGiunti.length > 0 ? `${fotoGiunti.length} foto` : 'Obbligatorio'}
                    </span>
                </div>
                <input ref={giuntiRef} type="file" accept="image/*" capture="environment" className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f, 'giunti'); if (giuntiRef.current) giuntiRef.current.value = ''; }}
                    data-testid="giunti-file-input"
                />
                <button
                    data-testid="btn-foto-giunti"
                    onClick={() => giuntiRef.current?.click()}
                    disabled={uploading === 'giunti'}
                    className={`w-full h-14 rounded-xl font-bold text-lg transition-all active:scale-95
                        ${uploading === 'giunti' ? 'bg-blue-500/20 text-blue-400 animate-pulse' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}
                >
                    {uploading === 'giunti' ? 'Caricamento...' : '📷 Scatta Foto Giunti'}
                </button>
            </div>

            {/* Foto ancoraggi (mandatory) */}
            <div className="bg-slate-800 rounded-2xl p-4 border-2 border-slate-700 mb-4" data-testid="foto-ancoraggi-section">
                <div className="flex items-center justify-between mb-3">
                    <p className="text-white font-bold">Foto Ancoraggi</p>
                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${fotoAncoraggi.length > 0 ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
                        {fotoAncoraggi.length > 0 ? `${fotoAncoraggi.length} foto` : 'Obbligatorio'}
                    </span>
                </div>
                <input ref={ancoraggiRef} type="file" accept="image/*" capture="environment" className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f, 'ancoraggi'); if (ancoraggiRef.current) ancoraggiRef.current.value = ''; }}
                    data-testid="ancoraggi-file-input"
                />
                <button
                    data-testid="btn-foto-ancoraggi"
                    onClick={() => ancoraggiRef.current?.click()}
                    disabled={uploading === 'ancoraggi'}
                    className={`w-full h-14 rounded-xl font-bold text-lg transition-all active:scale-95
                        ${uploading === 'ancoraggi' ? 'bg-blue-500/20 text-blue-400 animate-pulse' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}
                >
                    {uploading === 'ancoraggi' ? 'Caricamento...' : '📷 Scatta Foto Ancoraggi'}
                </button>
            </div>

            {/* Proceed */}
            {!canProceed && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-center mb-3">
                    <p className="text-amber-400 text-xs font-bold">
                        {fondazioniOk === null && 'Indica se le fondazioni sono idonee. '}
                        {fotoGiunti.length === 0 && 'Serve almeno 1 foto dei giunti. '}
                        {fotoAncoraggi.length === 0 && 'Serve almeno 1 foto degli ancoraggi.'}
                    </p>
                </div>
            )}

            <button
                data-testid="btn-next-firma"
                onClick={onNext}
                disabled={!canProceed}
                className={`w-full h-14 rounded-2xl font-bold text-lg transition-all active:scale-95
                    ${canProceed ? 'bg-blue-600 hover:bg-blue-500 text-white' : 'bg-slate-700 text-slate-500'}`}
            >
                Avanti: Firma Cliente →
            </button>
        </div>
    );
}


// ══════════════════════════════════════════════════════════════
//  SEZIONE 4: FIRMA DIGITALE CLIENTE
// ══════════════════════════════════════════════════════════════

function FirmaSection({ commessaId, voceId, selectedOp, serraggi, fondazioniOk, fotoGiunti, fotoAncoraggi, montaggioId, setMontaggioId, firmaCompleta, setFirmaCompleta }) {
    const canvasRef = useRef(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [hasSigned, setHasSigned] = useState(false);
    const [clientName, setClientName] = useState('');
    const [saving, setSaving] = useState(false);

    // Canvas drawing
    const getPos = useCallback((e) => {
        const canvas = canvasRef.current;
        if (!canvas) return { x: 0, y: 0 };
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches?.[0];
        const clientX = touch ? touch.clientX : e.clientX;
        const clientY = touch ? touch.clientY : e.clientY;
        return {
            x: (clientX - rect.left) * (canvas.width / rect.width),
            y: (clientY - rect.top) * (canvas.height / rect.height),
        };
    }, []);

    const startDraw = useCallback((e) => {
        e.preventDefault();
        const ctx = canvasRef.current?.getContext('2d');
        if (!ctx) return;
        setIsDrawing(true);
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
    }, [getPos]);

    const draw = useCallback((e) => {
        e.preventDefault();
        if (!isDrawing) return;
        const ctx = canvasRef.current?.getContext('2d');
        if (!ctx) return;
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        setHasSigned(true);
    }, [isDrawing, getPos]);

    const endDraw = useCallback((e) => {
        e.preventDefault();
        setIsDrawing(false);
    }, []);

    // Setup canvas
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.strokeStyle = '#1a3a6b';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
    }, []);

    const clearCanvas = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        setHasSigned(false);
    };

    const handleSaveAll = async () => {
        if (!hasSigned || !clientName.trim()) {
            toast.error('Inserisci il nome e la firma del cliente');
            return;
        }
        setSaving(true);
        try {
            // Step 1: Save diario montaggio
            let mtgId = montaggioId;
            if (!mtgId) {
                const res = await fetch(`${API}/api/montaggio/diario`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        commessa_id: commessaId,
                        voce_id: voceId || '',
                        operatore_id: selectedOp.op_id,
                        operatore_nome: selectedOp.nome,
                        serraggi: serraggi,
                        fondazioni_ok: fondazioniOk,
                        foto_giunti_doc_ids: fotoGiunti,
                        foto_ancoraggi_doc_ids: fotoAncoraggi,
                    }),
                });
                if (!res.ok) throw new Error('Errore salvataggio diario');
                const diario = await res.json();
                mtgId = diario.montaggio_id;
                setMontaggioId(mtgId);
            }

            // Step 2: Save client signature
            const canvas = canvasRef.current;
            const firmaB64 = canvas.toDataURL('image/png');

            const firmaRes = await fetch(`${API}/api/montaggio/firma`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    commessa_id: commessaId,
                    voce_id: voceId || '',
                    montaggio_id: mtgId,
                    firma_base64: firmaB64,
                    firma_nome: clientName.trim(),
                }),
            });
            if (!firmaRes.ok) throw new Error('Errore salvataggio firma');

            setFirmaCompleta(true);
            toast.success('Montaggio completato con firma cliente!');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    if (firmaCompleta) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[40vh]" data-testid="firma-done">
                <span className="text-7xl mb-4">✅</span>
                <p className="text-white text-2xl font-bold">Montaggio Completato</p>
                <p className="text-slate-400 mt-2 text-sm text-center">
                    Diario di montaggio salvato con firma cliente.
                    <br />Il documento sara' incluso nel Pacco Documenti.
                </p>
            </div>
        );
    }

    return (
        <div data-testid="firma-section">
            <p className="text-slate-400 text-center text-base mb-4 font-medium">Firma Cliente — Verbale Fine Lavori</p>

            {/* Riepilogo */}
            <div className="bg-slate-800 rounded-xl p-3 mb-4 border border-slate-700">
                <p className="text-slate-500 text-xs font-bold mb-2">Riepilogo Montaggio</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="text-slate-400">Serraggi: <span className="text-white font-bold">{serraggi.filter(s => s.confermato).length}/{serraggi.length}</span></div>
                    <div className="text-slate-400">Fondazioni: <span className={fondazioniOk ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{fondazioniOk ? 'OK' : fondazioniOk === false ? 'NOK' : '—'}</span></div>
                    <div className="text-slate-400">Foto giunti: <span className="text-white font-bold">{fotoGiunti.length}</span></div>
                    <div className="text-slate-400">Foto ancoraggi: <span className="text-white font-bold">{fotoAncoraggi.length}</span></div>
                </div>
            </div>

            {/* Client name */}
            <div className="mb-4">
                <label className="text-slate-400 text-sm font-bold block mb-1">Nome del Cliente</label>
                <input
                    data-testid="firma-nome-cliente"
                    type="text"
                    value={clientName}
                    onChange={e => setClientName(e.target.value)}
                    placeholder="Es. Mario Rossi"
                    className="w-full h-12 bg-slate-800 border-2 border-slate-700 rounded-xl px-4 text-white font-bold placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                />
            </div>

            {/* Signature canvas */}
            <div className="mb-4">
                <div className="flex items-center justify-between mb-1">
                    <label className="text-slate-400 text-sm font-bold">Firma del Cliente</label>
                    <button onClick={clearCanvas} className="text-xs text-slate-500 underline" data-testid="btn-clear-firma">Cancella</button>
                </div>
                <div className="bg-white rounded-xl border-2 border-slate-600 overflow-hidden">
                    <canvas
                        ref={canvasRef}
                        width={600}
                        height={200}
                        data-testid="firma-canvas"
                        className="w-full touch-none cursor-crosshair"
                        style={{ height: '150px' }}
                        onMouseDown={startDraw}
                        onMouseMove={draw}
                        onMouseUp={endDraw}
                        onMouseLeave={endDraw}
                        onTouchStart={startDraw}
                        onTouchMove={draw}
                        onTouchEnd={endDraw}
                    />
                </div>
                {!hasSigned && <p className="text-slate-600 text-xs mt-1 text-center">Firmare qui sopra con il dito o lo stilo</p>}
            </div>

            {/* Save button */}
            <button
                data-testid="btn-save-montaggio"
                onClick={handleSaveAll}
                disabled={saving || !hasSigned || !clientName.trim()}
                className={`w-full h-16 rounded-2xl text-xl font-black transition-all active:scale-95
                    ${saving ? 'bg-blue-500/20 text-blue-400 animate-pulse' :
                        hasSigned && clientName.trim() ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-600/30' :
                        'bg-slate-700 text-slate-500'}`}
            >
                {saving ? 'Salvataggio in corso...' : 'CONFERMA MONTAGGIO'}
            </button>
        </div>
    );
}
