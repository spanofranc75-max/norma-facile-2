/**
 * OfficinaPage — Vista blindata per operai.
 * 4 Ponti: Diario (Timer), Foto, Qualità (Checklist), Blocco Dati.
 * Accessibile via QR Code + PIN 4 cifre. Nessuna navigazione esterna.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import MontaggioPanel from '../components/MontaggioPanel';

const API = process.env.REACT_APP_BACKEND_URL;

const apiCall = async (path, opts = {}) => {
    const res = await fetch(`${API}/api${path}`, {
        headers: { 'Content-Type': 'application/json', ...opts.headers },
        ...opts,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Errore');
    }
    return res.json();
};

// ── Category colors ──
const CAT_COLORS = {
    EN_1090: { bg: 'bg-blue-600', light: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300', label: 'Strutturale' },
    EN_13241: { bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300', label: 'Cancello' },
    GENERICA: { bg: 'bg-slate-500', light: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-300', label: 'Generica' },
};

// ── Checklist icon map ──
const CHECKLIST_ICONS = {
    flame: '🔥', ruler: '📐', package: '📦', shield: '🛡️', move: '⚙️', check: '✓',
};

export default function OfficinaPage() {
    const { commessaId, voceId } = useParams();
    const [phase, setPhase] = useState('loading'); // loading, select-op, pin, main
    const [context, setContext] = useState(null);
    const [operatori, setOperatori] = useState([]);
    const [selectedOp, setSelectedOp] = useState(null);
    const [pin, setPin] = useState('');
    const [pinError, setPinError] = useState(false);
    const [activeTab, setActiveTab] = useState('timer'); // timer, foto, qualita

    // Timer state
    const [timerStatus, setTimerStatus] = useState('idle'); // idle, running, paused
    const [timerStart, setTimerStart] = useState(null);
    const [elapsed, setElapsed] = useState(0);
    const [pausedTotal, setPausedTotal] = useState(0);
    const [pauseStart, setPauseStart] = useState(null);
    const intervalRef = useRef(null);

    // Photo state
    const [uploading, setUploading] = useState(false);
    const [lastPhoto, setLastPhoto] = useState(null);
    const fileInputRef = useRef(null);

    // Checklist state
    const [checkItems, setCheckItems] = useState([]);
    const [checkSubmitting, setCheckSubmitting] = useState(false);
    const [checkDone, setCheckDone] = useState(false);

    // Load context and operators
    useEffect(() => {
        const load = async () => {
            try {
                const [ctx, ops] = await Promise.all([
                    apiCall(`/officina/context/${commessaId}?voce_id=${voceId || ''}`),
                    apiCall(`/officina/operatori/${commessaId}`),
                ]);
                setContext(ctx);
                setOperatori(ops.operatori || []);

                // Initialize checklist items (all undefined = not answered yet)
                if (ctx.checklist_config) {
                    setCheckItems(ctx.checklist_config.map(c => ({ ...c, esito: null })));
                }

                // Restore active timer if present
                if (ctx.timer) {
                    const t = ctx.timer;
                    setTimerStatus(t.status);
                    setTimerStart(new Date(t.started_at));
                    setPausedTotal(t.total_paused_seconds || 0);
                    if (t.status === 'paused') {
                        const pauses = t.pauses || [];
                        const lastPause = pauses[pauses.length - 1];
                        if (lastPause && !lastPause.resumed_at) {
                            setPauseStart(new Date(lastPause.paused_at));
                        }
                    }
                }

                setPhase('select-op');
            } catch (e) {
                toast.error('Errore: ' + e.message);
            }
        };
        load();
    }, [commessaId, voceId]);

    // Timer tick
    useEffect(() => {
        if (timerStatus === 'running' && timerStart) {
            intervalRef.current = setInterval(() => {
                const now = new Date();
                const totalSec = (now - timerStart) / 1000 - pausedTotal;
                setElapsed(Math.max(0, Math.floor(totalSec)));
            }, 1000);
        } else if (timerStatus === 'paused' && timerStart && pauseStart) {
            // Update elapsed but freeze it at pause point
            const now = pauseStart;
            const totalSec = (now - timerStart) / 1000 - pausedTotal;
            setElapsed(Math.max(0, Math.floor(totalSec)));
        }
        return () => clearInterval(intervalRef.current);
    }, [timerStatus, timerStart, pausedTotal, pauseStart]);

    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h > 0 ? h + ':' : ''}${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    };

    // ── PIN handling ──
    const handlePinDigit = (digit) => {
        setPinError(false);
        const newPin = pin + digit;
        setPin(newPin);
        if (newPin.length === 4) {
            verifyPin(newPin);
        }
    };
    const handlePinDelete = () => setPin(p => p.slice(0, -1));

    const verifyPin = async (pinCode) => {
        try {
            await apiCall('/officina/pin/verify', {
                method: 'POST',
                body: JSON.stringify({ pin: pinCode, operatore_id: selectedOp.op_id }),
            });
            setPhase('main');
        } catch {
            setPinError(true);
            setPin('');
        }
    };

    // ── Timer actions ──
    const handleTimer = async (action) => {
        try {
            const res = await apiCall(`/officina/timer/${commessaId}?voce_id=${voceId || ''}`, {
                method: 'POST',
                body: JSON.stringify({
                    action,
                    operatore_id: selectedOp.op_id,
                    operatore_nome: selectedOp.nome,
                }),
            });

            if (action === 'start') {
                setTimerStatus('running');
                setTimerStart(new Date());
                setPausedTotal(0);
                setPauseStart(null);
                setElapsed(0);
            } else if (action === 'pause') {
                setTimerStatus('paused');
                setPauseStart(new Date());
            } else if (action === 'resume') {
                const now = new Date();
                if (pauseStart) {
                    setPausedTotal(p => p + (now - pauseStart) / 1000);
                }
                setPauseStart(null);
                setTimerStatus('running');
            } else if (action === 'stop') {
                clearInterval(intervalRef.current);
                setTimerStatus('idle');
                setTimerStart(null);
                setElapsed(0);
                setPausedTotal(0);
                setPauseStart(null);
                toast.success(`${res.total_minutes} minuti registrati`);
            }
        } catch (e) {
            toast.error(e.message);
        }
    };

    // ── Photo upload ──
    const handlePhotoCapture = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        setLastPhoto(null);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('voce_id', voceId || '');
            formData.append('operatore_id', selectedOp.op_id);
            formData.append('operatore_nome', selectedOp.nome);

            const res = await fetch(`${API}/api/officina/foto/${commessaId}`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Upload fallito');
            const data = await res.json();
            setLastPhoto(data);
            toast.success('Foto salvata');
        } catch (e) {
            toast.error(e.message);
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    // ── Checklist submit ──
    const handleCheckToggle = (idx, esito) => {
        setCheckItems(items => items.map((item, i) => i === idx ? { ...item, esito } : item));
    };

    const handleCheckSubmit = async () => {
        const unanswered = checkItems.filter(i => i.esito === null);
        if (unanswered.length > 0) { toast.error('Rispondi a tutti i controlli'); return; }
        setCheckSubmitting(true);
        try {
            const res = await apiCall(`/officina/checklist/${commessaId}?voce_id=${voceId || ''}`, {
                method: 'POST',
                body: JSON.stringify({
                    operatore_id: selectedOp.op_id,
                    operatore_nome: selectedOp.nome,
                    items: checkItems.map(i => ({ codice: i.codice, esito: i.esito })),
                }),
            });
            setCheckDone(true);
            if (res.all_ok) {
                toast.success('Tutto OK');
            } else {
                toast.error(`${res.problemi} problema/i segnalato/i`);
            }
        } catch (e) {
            toast.error(e.message);
        } finally {
            setCheckSubmitting(false);
        }
    };

    const normativa = context?.voce?.normativa_tipo || 'GENERICA';
    const catColor = CAT_COLORS[normativa] || CAT_COLORS.GENERICA;

    // ── LOADING ──
    if (phase === 'loading') {
        return (
            <div className="min-h-screen bg-slate-900 flex items-center justify-center" data-testid="officina-loading">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto" />
                    <p className="text-slate-400 mt-4 text-lg">Caricamento...</p>
                </div>
            </div>
        );
    }

    // ── OPERATOR SELECTION ──
    if (phase === 'select-op') {
        return (
            <div className="min-h-screen bg-slate-900 flex flex-col" data-testid="officina-select-op">
                {/* Header */}
                <div className={`${catColor.bg} px-4 py-5 text-white text-center`}>
                    <p className="text-sm opacity-80">{context?.commessa?.numero}</p>
                    <h1 className="text-xl font-bold mt-1 line-clamp-2">{context?.voce?.descrizione || context?.commessa?.title}</h1>
                    <p className="text-xs mt-1 opacity-70">{catColor.label}</p>
                </div>

                <div className="flex-1 p-4">
                    <p className="text-slate-400 text-center text-lg mb-6 font-medium">Chi sei?</p>
                    <div className="space-y-3 max-w-md mx-auto">
                        {operatori.map(op => (
                            <button
                                key={op.op_id}
                                data-testid={`op-${op.op_id}`}
                                onClick={() => { setSelectedOp(op); setPhase('pin'); setPin(''); }}
                                className="w-full flex items-center gap-4 p-5 bg-slate-800 rounded-2xl border-2 border-slate-700 hover:border-blue-500 active:scale-[0.98] transition-all"
                            >
                                <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold shrink-0">
                                    {op.nome.charAt(0).toUpperCase()}
                                </div>
                                <span className="text-white text-xl font-semibold">{op.nome}</span>
                            </button>
                        ))}
                        {operatori.length === 0 && (
                            <p className="text-slate-500 text-center py-8">Nessun operatore registrato</p>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    // ── PIN ENTRY ──
    if (phase === 'pin') {
        return (
            <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4" data-testid="officina-pin">
                <div className="text-center mb-8">
                    <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-3xl font-bold mx-auto mb-3">
                        {selectedOp.nome.charAt(0).toUpperCase()}
                    </div>
                    <p className="text-white text-xl font-semibold">{selectedOp.nome}</p>
                    <p className="text-slate-400 mt-1">Inserisci il PIN</p>
                </div>

                {/* PIN dots */}
                <div className="flex gap-4 mb-8" data-testid="pin-dots">
                    {[0, 1, 2, 3].map(i => (
                        <div key={i} className={`w-5 h-5 rounded-full transition-all ${i < pin.length ? (pinError ? 'bg-red-500 scale-110' : 'bg-blue-500 scale-110') : 'bg-slate-700'}`} />
                    ))}
                </div>
                {pinError && <p className="text-red-400 text-sm mb-4 animate-pulse" data-testid="pin-error">PIN errato</p>}

                {/* Numpad */}
                <div className="grid grid-cols-3 gap-3 max-w-[280px]">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, null, 0, 'del'].map((digit, i) => {
                        if (digit === null) return <div key={i} />;
                        if (digit === 'del') return (
                            <button key={i} onClick={handlePinDelete} data-testid="pin-delete"
                                className="h-16 rounded-2xl bg-slate-800 text-slate-400 text-xl font-bold active:bg-slate-700 transition-colors flex items-center justify-center">
                                ←
                            </button>
                        );
                        return (
                            <button key={i} onClick={() => handlePinDigit(String(digit))} data-testid={`pin-${digit}`}
                                className="h-16 rounded-2xl bg-slate-800 text-white text-2xl font-bold active:bg-blue-600 transition-colors">
                                {digit}
                            </button>
                        );
                    })}
                </div>

                <button onClick={() => { setPhase('select-op'); setPin(''); setPinError(false); }}
                    className="mt-6 text-slate-500 text-sm underline" data-testid="pin-back">
                    Cambia operatore
                </button>
            </div>
        );
    }

    // ── MAIN INTERFACE (Locked) ──
    return (
        <div className="min-h-screen bg-slate-900 flex flex-col" data-testid="officina-main">
            {/* Compact header */}
            <div className={`${catColor.bg} px-4 py-3 text-white`}>
                <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                        <p className="text-[11px] opacity-70">{context?.commessa?.numero} — {catColor.label}</p>
                        <p className="font-bold text-sm truncate">{context?.voce?.descrizione || context?.commessa?.title}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-3">
                        <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold">
                            {selectedOp.nome.charAt(0)}
                        </div>
                    </div>
                </div>
            </div>

            {/* Tab bar */}
            <div className="flex bg-slate-800 border-b border-slate-700">
                {[
                    { id: 'timer', label: 'TEMPI', icon: '⏱️' },
                    { id: 'foto', label: 'FOTO', icon: '📷' },
                    { id: 'qualita', label: 'QUALITÀ', icon: '✓' },
                    { id: 'montaggio', label: 'MONTAGGIO', icon: '🔧' },
                ].map(tab => (
                    <button
                        key={tab.id}
                        data-testid={`tab-${tab.id}`}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex-1 py-3 text-center text-sm font-bold transition-colors ${activeTab === tab.id ? 'text-white bg-slate-700 border-b-2 border-blue-500' : 'text-slate-500'}`}
                    >
                        <span className="text-lg block">{tab.icon}</span>
                        <span className="text-[10px]">{tab.label}</span>
                    </button>
                ))}
            </div>

            {/* Content area */}
            <div className="flex-1 p-4">
                {activeTab === 'timer' && (
                    <TimerPanel
                        status={timerStatus}
                        elapsed={elapsed}
                        formatTime={formatTime}
                        onAction={handleTimer}
                    />
                )}
                {activeTab === 'foto' && (
                    <FotoPanel
                        uploading={uploading}
                        lastPhoto={lastPhoto}
                        fileInputRef={fileInputRef}
                        onCapture={handlePhotoCapture}
                        normativa={normativa}
                        catColor={catColor}
                    />
                )}
                {activeTab === 'qualita' && (
                    <QualitaPanel
                        items={checkItems}
                        onToggle={handleCheckToggle}
                        onSubmit={handleCheckSubmit}
                        submitting={checkSubmitting}
                        done={checkDone}
                    />
                )}
                {activeTab === 'montaggio' && (
                    <MontaggioPanel
                        commessaId={commessaId}
                        voceId={voceId}
                        selectedOp={selectedOp}
                        normativa={normativa}
                    />
                )}
            </div>
        </div>
    );
}

// ── PONTE 1: TIMER PANEL ────────────────────────────────────────

function TimerPanel({ status, elapsed, formatTime, onAction }) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[50vh]" data-testid="timer-panel">
            {/* Timer display */}
            <div className={`text-6xl sm:text-7xl font-mono font-bold mb-10 tabular-nums tracking-wider
                ${status === 'running' ? 'text-green-400' : status === 'paused' ? 'text-yellow-400 animate-pulse' : 'text-slate-500'}`}
                data-testid="timer-display"
            >
                {formatTime(elapsed)}
            </div>

            {/* Action buttons */}
            <div className="flex gap-4 w-full max-w-md">
                {status === 'idle' && (
                    <button
                        data-testid="btn-start"
                        onClick={() => onAction('start')}
                        className="flex-1 h-24 rounded-3xl bg-green-600 hover:bg-green-500 active:scale-95 text-white text-2xl font-black transition-all shadow-lg shadow-green-600/30 flex items-center justify-center gap-3"
                    >
                        <span className="text-4xl">▶</span> START
                    </button>
                )}

                {status === 'running' && (
                    <>
                        <button
                            data-testid="btn-pause"
                            onClick={() => onAction('pause')}
                            className="flex-1 h-24 rounded-3xl bg-yellow-500 hover:bg-yellow-400 active:scale-95 text-slate-900 text-2xl font-black transition-all shadow-lg shadow-yellow-500/30 flex items-center justify-center gap-3"
                        >
                            <span className="text-4xl">⏸</span> PAUSA
                        </button>
                        <button
                            data-testid="btn-stop"
                            onClick={() => onAction('stop')}
                            className="flex-1 h-24 rounded-3xl bg-red-600 hover:bg-red-500 active:scale-95 text-white text-2xl font-black transition-all shadow-lg shadow-red-600/30 flex items-center justify-center gap-3"
                        >
                            <span className="text-4xl">⏹</span> STOP
                        </button>
                    </>
                )}

                {status === 'paused' && (
                    <>
                        <button
                            data-testid="btn-resume"
                            onClick={() => onAction('resume')}
                            className="flex-1 h-24 rounded-3xl bg-green-600 hover:bg-green-500 active:scale-95 text-white text-2xl font-black transition-all shadow-lg shadow-green-600/30 flex items-center justify-center gap-3"
                        >
                            <span className="text-4xl">▶</span> RIPRENDI
                        </button>
                        <button
                            data-testid="btn-stop-paused"
                            onClick={() => onAction('stop')}
                            className="flex-1 h-24 rounded-3xl bg-red-600 hover:bg-red-500 active:scale-95 text-white text-2xl font-black transition-all shadow-lg shadow-red-600/30 flex items-center justify-center gap-3"
                        >
                            <span className="text-4xl">⏹</span> STOP
                        </button>
                    </>
                )}
            </div>

            {status !== 'idle' && (
                <p className="text-slate-600 text-xs mt-6 text-center">
                    {status === 'running' ? 'Lavoro in corso...' : 'In pausa — premi RIPRENDI o STOP'}
                </p>
            )}
        </div>
    );
}

// ── PONTE 2: FOTO PANEL ─────────────────────────────────────────

function FotoPanel({ uploading, lastPhoto, fileInputRef, onCapture, normativa, catColor }) {
    const destLabel = normativa === 'EN_1090' ? 'Certificati 3.1'
        : normativa === 'EN_13241' ? 'Fascicolo Tecnico'
        : 'Documenti';

    return (
        <div className="flex flex-col items-center justify-center min-h-[50vh]" data-testid="foto-panel">
            <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={onCapture}
                data-testid="foto-input"
            />

            <button
                data-testid="btn-foto"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className={`w-40 h-40 rounded-full ${catColor.bg} hover:opacity-90 active:scale-95 text-white flex flex-col items-center justify-center transition-all shadow-xl ${uploading ? 'opacity-50 animate-pulse' : ''}`}
            >
                <span className="text-5xl mb-2">{uploading ? '⏳' : '📷'}</span>
                <span className="text-xl font-black">{uploading ? 'INVIO...' : 'FOTO'}</span>
            </button>

            <p className="text-slate-500 text-sm mt-6 text-center">
                La foto viene salvata in: <span className={`font-bold ${catColor.text}`}>{destLabel}</span>
            </p>

            {lastPhoto && (
                <div className={`mt-4 p-3 ${catColor.light} ${catColor.border} border rounded-xl text-center`} data-testid="foto-success">
                    <p className={`font-bold text-sm ${catColor.text}`}>Foto salvata</p>
                    <p className="text-xs text-slate-500 mt-1">{lastPhoto.nome_file}</p>
                </div>
            )}
        </div>
    );
}

// ── PONTE 3: QUALITÀ PANEL ──────────────────────────────────────

function QualitaPanel({ items, onToggle, onSubmit, submitting, done }) {
    if (done) {
        const allOk = items.every(i => i.esito === true);
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh]" data-testid="qualita-done">
                <span className="text-7xl mb-4">{allOk ? '✅' : '⚠️'}</span>
                <p className="text-white text-2xl font-bold">
                    {allOk ? 'Tutto OK' : 'Problemi segnalati'}
                </p>
                <p className="text-slate-400 mt-2 text-sm">
                    {allOk ? 'Controllo qualità superato' : 'L\'admin è stato avvisato'}
                </p>
            </div>
        );
    }

    return (
        <div className="max-w-md mx-auto" data-testid="qualita-panel">
            <p className="text-slate-400 text-center text-lg mb-6 font-medium">Controllo Qualità</p>

            <div className="space-y-4">
                {items.map((item, idx) => (
                    <div key={item.codice} className="bg-slate-800 rounded-2xl p-4 border-2 border-slate-700" data-testid={`check-${item.codice}`}>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <span className="text-2xl">{CHECKLIST_ICONS[item.icona] || '🔍'}</span>
                                <span className="text-white font-bold text-lg">{item.label_admin}</span>
                            </div>
                        </div>
                        <div className="flex gap-3 mt-3">
                            <button
                                data-testid={`check-${item.codice}-ok`}
                                onClick={() => onToggle(idx, true)}
                                className={`flex-1 h-16 rounded-2xl text-3xl font-black transition-all active:scale-95
                                    ${item.esito === true ? 'bg-green-600 text-white shadow-lg shadow-green-600/30 ring-2 ring-green-400' : 'bg-slate-700 text-slate-500 hover:bg-slate-600'}`}
                            >
                                👍
                            </button>
                            <button
                                data-testid={`check-${item.codice}-nok`}
                                onClick={() => onToggle(idx, false)}
                                className={`flex-1 h-16 rounded-2xl text-3xl font-black transition-all active:scale-95
                                    ${item.esito === false ? 'bg-red-600 text-white shadow-lg shadow-red-600/30 ring-2 ring-red-400' : 'bg-slate-700 text-slate-500 hover:bg-slate-600'}`}
                            >
                                👎
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <button
                data-testid="btn-submit-checklist"
                onClick={onSubmit}
                disabled={submitting || items.some(i => i.esito === null)}
                className={`w-full h-16 mt-6 rounded-2xl text-xl font-black transition-all active:scale-95
                    ${items.some(i => i.esito === null) ? 'bg-slate-700 text-slate-500' : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-600/30'}`}
            >
                {submitting ? 'INVIO...' : 'INVIA CONTROLLO'}
            </button>
        </div>
    );
}
