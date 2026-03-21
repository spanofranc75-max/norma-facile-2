/**
 * VerbalePosaPage — Dichiarazione di Corretta Posa in Opera.
 * Mobile-first: ottimizzato per uso in cantiere (cellulare/tablet).
 * Carica dati commessa, materiali, lotti EN 1090.
 * Checklist tecnica, upload foto cantiere, firma touch, generazione PDF.
 */
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import {
    FileDown, Save, Loader2, Camera, X, Pen, RotateCcw,
    CheckSquare, Building2, MapPin, ClipboardList, Send, Image, Package,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/* ═══════ SIGNATURE CANVAS ═══════ */
function SignatureCanvas({ value, onChange }) {
    const canvasRef = useRef(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [hasSignature, setHasSignature] = useState(false);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        if (value && value.startsWith('data:')) {
            const img = new window.Image();
            img.onload = () => { ctx.drawImage(img, 0, 0); setHasSignature(true); };
            img.src = value;
        }
    }, []);

    const getPos = (e) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches?.[0];
        const clientX = touch ? touch.clientX : e.clientX;
        const clientY = touch ? touch.clientY : e.clientY;
        return {
            x: (clientX - rect.left) * (canvas.width / rect.width),
            y: (clientY - rect.top) * (canvas.height / rect.height),
        };
    };

    const startDraw = (e) => {
        e.preventDefault();
        setIsDrawing(true);
        const ctx = canvasRef.current.getContext('2d');
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        ctx.strokeStyle = '#1a1a1a';
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
    };

    const draw = (e) => {
        if (!isDrawing) return;
        e.preventDefault();
        const ctx = canvasRef.current.getContext('2d');
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        setHasSignature(true);
    };

    const endDraw = () => {
        if (!isDrawing) return;
        setIsDrawing(false);
        const data = canvasRef.current.toDataURL('image/png');
        onChange(data);
    };

    const clear = () => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        setHasSignature(false);
        onChange('');
    };

    return (
        <div data-testid="signature-canvas-wrapper">
            <div className="relative border-2 border-dashed border-slate-300 rounded-xl overflow-hidden bg-white">
                <canvas
                    ref={canvasRef}
                    width={600}
                    height={200}
                    className="w-full cursor-crosshair touch-none"
                    style={{ height: '160px' }}
                    onMouseDown={startDraw}
                    onMouseMove={draw}
                    onMouseUp={endDraw}
                    onMouseLeave={endDraw}
                    onTouchStart={startDraw}
                    onTouchMove={draw}
                    onTouchEnd={endDraw}
                    data-testid="signature-canvas"
                />
                {!hasSignature && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <p className="text-slate-400 text-sm flex items-center gap-2">
                            <Pen className="w-5 h-5" /> Firma qui (touch o mouse)
                        </p>
                    </div>
                )}
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={clear} className="text-xs text-slate-500 mt-1">
                <RotateCcw className="w-3 h-3 mr-1" /> Cancella firma
            </Button>
        </div>
    );
}

/* ═══════ PHOTO UPLOAD (Mobile optimized) ═══════ */
function PhotoUpload({ photos, setPhotos }) {
    const inputRef = useRef(null);
    const [dragOver, setDragOver] = useState(false);

    const addFiles = (files) => {
        const newPhotos = [...photos];
        for (const file of Array.from(files)) {
            if (newPhotos.length >= 3) break;
            if (!file.type.startsWith('image/')) continue;
            newPhotos.push({ file, preview: URL.createObjectURL(file), name: file.name });
        }
        setPhotos(newPhotos);
    };

    const handleDrop = (e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); };
    const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
    const handleDragLeave = () => setDragOver(false);
    const removePhoto = (idx) => setPhotos(photos.filter((_, i) => i !== idx));

    return (
        <div data-testid="photo-upload">
            <div
                className={`border-2 border-dashed rounded-xl p-6 sm:p-8 text-center cursor-pointer transition-all ${
                    dragOver ? 'border-[#0055FF] bg-blue-50 scale-[1.01]' : 'border-slate-300 hover:border-slate-400'
                } ${photos.length >= 3 ? 'opacity-50 pointer-events-none' : ''}`}
                onClick={() => inputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                data-testid="photo-dropzone"
            >
                <input ref={inputRef} type="file" accept="image/*" capture="environment" multiple className="hidden"
                    onChange={e => { addFiles(e.target.files); e.target.value = ''; }} />
                <Camera className="w-10 h-10 text-slate-400 mx-auto mb-2" />
                <p className="text-base font-medium text-slate-700">Scatta o seleziona foto</p>
                <p className="text-xs text-slate-400 mt-1">Max 3 foto — trascina o tocca per selezionare</p>
            </div>
            {photos.length > 0 && (
                <div className="grid grid-cols-3 gap-2 mt-3">
                    {photos.map((p, i) => (
                        <div key={i} className="relative group rounded-xl overflow-hidden border-2 border-slate-200 aspect-square" data-testid={`photo-preview-${i}`}>
                            <img src={p.preview} alt={p.name} className="w-full h-full object-cover" />
                            <button
                                onClick={(e) => { e.stopPropagation(); removePhoto(i); }}
                                className="absolute top-1.5 right-1.5 bg-red-500/90 text-white rounded-full p-1 opacity-70 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
                            >
                                <X className="w-4 h-4" />
                            </button>
                            <p className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[10px] text-center py-0.5 truncate px-1">{p.name}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ═══════ MAIN PAGE ═══════ */
export default function VerbalePosaPage() {
    const { commessaId } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [genPdf, setGenPdf] = useState(false);
    const [ctx, setCtx] = useState(null);
    const [form, setForm] = useState({
        data_posa: new Date().toISOString().split('T')[0],
        luogo_posa: '',
        responsabile: '',
        note_cantiere: '',
        check_regola_arte: true,
        check_conformita: true,
        check_materiali: true,
        check_sicurezza: true,
    });
    const [signature, setSignature] = useState('');
    const [photos, setPhotos] = useState([]);
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        const load = async () => {
            try {
                const [ctxData, existing] = await Promise.all([
                    apiRequest(`/verbale-posa/context/${commessaId}`),
                    apiRequest(`/verbale-posa/${commessaId}`),
                ]);
                setCtx(ctxData);
                if (existing?.exists) {
                    setForm(f => ({
                        ...f,
                        data_posa: existing.data_posa || f.data_posa,
                        luogo_posa: existing.luogo_posa || ctxData.cantiere || '',
                        responsabile: existing.responsabile || '',
                        note_cantiere: existing.note_cantiere || '',
                        check_regola_arte: existing.checklist?.regola_arte ?? true,
                        check_conformita: existing.checklist?.conformita_normative ?? true,
                        check_materiali: existing.checklist?.materiali_conformi ?? true,
                        check_sicurezza: existing.checklist?.sicurezza_rispettata ?? true,
                    }));
                    setSignature(existing.signature_data || '');
                    setSaved(true);
                } else {
                    setForm(f => ({ ...f, luogo_posa: ctxData.cantiere || '' }));
                }
            } catch (e) {
                toast.error('Errore caricamento: ' + e.message);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [commessaId]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const fd = new FormData();
            fd.append('data_posa', form.data_posa);
            fd.append('luogo_posa', form.luogo_posa);
            fd.append('responsabile', form.responsabile);
            fd.append('note_cantiere', form.note_cantiere);
            fd.append('check_regola_arte', form.check_regola_arte.toString());
            fd.append('check_conformita', form.check_conformita.toString());
            fd.append('check_materiali', form.check_materiali.toString());
            fd.append('check_sicurezza', form.check_sicurezza.toString());
            fd.append('signature_data', signature);
            for (const p of photos) {
                if (p.file) fd.append('photos', p.file);
            }
            const res = await fetch(`${API}/api/verbale-posa/${commessaId}`, {
                method: 'POST', credentials: 'include', body: fd,
            });
            if (res.ok) {
                toast.success('Verbale salvato!');
                setSaved(true);
            } else {
                const d = await res.json().catch(() => ({}));
                toast.error(d.detail || 'Errore salvataggio');
            }
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    const handlePdf = async () => {
        setGenPdf(true);
        try {
            const res = await fetch(`${API}/api/verbale-posa/${commessaId}/pdf`, { credentials: 'include' });
            if (!res.ok) { toast.error('Errore generazione PDF'); return; }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const code = ctx?.commessa_number?.replace(/\//g, '-')?.replace(/\s/g, '_') || commessaId;
            a.download = `Verbale_Posa_${code}_${new Date().toISOString().split('T')[0].replace(/-/g, '')}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('PDF scaricato!');
        } catch (e) { toast.error(e.message); }
        finally { setGenPdf(false); }
    };

    const setField = (key, val) => setForm(f => ({ ...f, [key]: val }));

    if (loading) return <DashboardLayout><div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div></DashboardLayout>;

    const hasLotti = ctx?.lotti?.length > 0;

    return (
        <DashboardLayout>
            <div className="max-w-4xl mx-auto space-y-4 sm:space-y-5 px-1 sm:px-0" data-testid="verbale-posa-page">
                {/* ── HEADER ── */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="min-w-0">
                        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 truncate">Verbale di Posa in Opera</h1>
                        <p className="text-sm text-slate-500 truncate">
                            <span className="font-semibold text-[#0055FF]">{ctx?.commessa_number}</span> — {ctx?.client_name}
                        </p>
                    </div>
                    <div className="flex gap-2 flex-shrink-0">
                        {saved && (
                            <>
                                <Button variant="outline" onClick={handlePdf} disabled={genPdf}
                                    className="border-[#0055FF] text-[#0055FF] h-10 sm:h-9" data-testid="btn-pdf">
                                    {genPdf ? <Loader2 className="w-4 h-4 sm:mr-2 animate-spin" /> : <FileDown className="w-4 h-4 sm:mr-2" />}
                                    <span className="hidden sm:inline">Genera PDF</span>
                                </Button>
                                <Button variant="outline" disabled
                                    className="border-amber-300 text-amber-600 cursor-not-allowed h-10 sm:h-9" data-testid="btn-send-cims">
                                    <Send className="w-4 h-4 sm:mr-2" />
                                    <span className="hidden sm:inline">Invia a CIMS</span>
                                </Button>
                            </>
                        )}
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF] hover:bg-[#0044CC] h-10 sm:h-9" data-testid="btn-save">
                            {saving ? <Loader2 className="w-4 h-4 sm:mr-2 animate-spin" /> : <Save className="w-4 h-4 sm:mr-2" />}
                            <span className="hidden sm:inline">Salva</span>
                        </Button>
                    </div>
                </div>

                {/* ── DATI CANTIERE ── */}
                <Card>
                    <CardHeader className="pb-2 sm:pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-[#0055FF]" /> Dati del Cantiere
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                        <div>
                            <Label className="text-xs">Data di Posa *</Label>
                            <Input type="date" value={form.data_posa} onChange={e => setField('data_posa', e.target.value)}
                                className="mt-1 h-11 sm:h-9 text-base sm:text-sm" data-testid="input-data-posa" />
                        </div>
                        <div>
                            <Label className="text-xs">Luogo / Cantiere *</Label>
                            <Input value={form.luogo_posa} onChange={e => setField('luogo_posa', e.target.value)}
                                placeholder="es. Via Roma 1, Loiano (BO)" className="mt-1 h-11 sm:h-9 text-base sm:text-sm" data-testid="input-luogo" />
                        </div>
                        <div>
                            <Label className="text-xs">Responsabile Montaggio</Label>
                            <Input value={form.responsabile} onChange={e => setField('responsabile', e.target.value)}
                                placeholder="Nome e cognome" className="mt-1 h-11 sm:h-9 text-base sm:text-sm" data-testid="input-responsabile" />
                        </div>
                        <div>
                            <Label className="text-xs">Committente</Label>
                            <Input value={ctx?.client_name || ''} disabled className="mt-1 h-11 sm:h-9 bg-slate-50 text-base sm:text-sm" />
                        </div>
                        <div>
                            <Label className="text-xs">Classe di Esecuzione</Label>
                            <Input value={ctx?.execution_class || 'N/A'} disabled className="mt-1 h-11 sm:h-9 bg-slate-50 text-base sm:text-sm" />
                        </div>
                        <div>
                            <Label className="text-xs">Impresa Esecutrice</Label>
                            <Input value={ctx?.company_name || 'Steel Project Design'} disabled className="mt-1 h-11 sm:h-9 bg-slate-50 text-base sm:text-sm" />
                        </div>
                    </CardContent>
                </Card>

                {/* ── LOTTI EN 1090 (priorita alta) ── */}
                {hasLotti && (
                    <Card className="border-2 border-[#0055FF]/30 bg-blue-50/20">
                        <CardHeader className="pb-2 sm:pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Package className="w-5 h-5 text-[#0055FF]" />
                                <span>Lotti Materiale EN 1090</span>
                                <Badge className="bg-[#0055FF] text-white text-[10px] ml-1">{ctx.lotti.length} lotti tracciati</Badge>
                            </CardTitle>
                            <p className="text-xs text-slate-500 mt-0.5">Tracciabilita acciaio e bulloneria — Certificati 3.1 collegati</p>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2 sm:space-y-0" data-testid="lotti-table">
                                {/* Desktop table */}
                                <div className="hidden sm:block border rounded-lg overflow-hidden">
                                    <table className="w-full">
                                        <thead>
                                            <tr className="bg-[#0055FF]">
                                                <th className="text-left text-white text-xs font-semibold px-3 py-2.5">Tipo</th>
                                                <th className="text-left text-white text-xs font-semibold px-3 py-2.5">N. Colata</th>
                                                <th className="text-left text-white text-xs font-semibold px-3 py-2.5">Descrizione</th>
                                                <th className="text-left text-white text-xs font-semibold px-3 py-2.5">Acciaieria</th>
                                                <th className="text-left text-white text-xs font-semibold px-3 py-2.5">Cert. 3.1</th>
                                                <th className="text-center text-white text-xs font-semibold px-3 py-2.5">Qta</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {ctx.lotti.map((l, i) => (
                                                <tr key={i} className="border-b border-slate-100 hover:bg-blue-50/30">
                                                    <td className="px-3 py-2">
                                                        <Badge className={l.material_type === 'bulloneria' ? 'bg-amber-100 text-amber-700 text-[10px]' : 'bg-slate-100 text-slate-700 text-[10px]'}>
                                                            {l.material_type === 'bulloneria' ? 'Bulloneria' : 'Acciaio'}
                                                        </Badge>
                                                    </td>
                                                    <td className="px-3 py-2 font-mono text-sm font-semibold text-[#0055FF]">{l.heat_number}</td>
                                                    <td className="px-3 py-2 text-sm text-slate-700">{l.description}</td>
                                                    <td className="px-3 py-2 text-sm text-slate-600">{l.acciaieria}</td>
                                                    <td className="px-3 py-2 text-sm font-mono text-emerald-700 font-medium">{l.cert_31}</td>
                                                    <td className="px-3 py-2 text-sm text-center">{l.quantity}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                {/* Mobile cards */}
                                <div className="sm:hidden space-y-2">
                                    {ctx.lotti.map((l, i) => (
                                        <div key={i} className="bg-white border border-slate-200 rounded-xl p-3 space-y-1.5" data-testid={`lotto-mobile-${i}`}>
                                            <div className="flex items-center justify-between">
                                                <span className="font-mono text-sm font-bold text-[#0055FF]">{l.heat_number}</span>
                                                <Badge className={l.material_type === 'bulloneria' ? 'bg-amber-100 text-amber-700 text-[10px]' : 'bg-slate-100 text-slate-700 text-[10px]'}>
                                                    {l.material_type === 'bulloneria' ? 'Bulloneria' : 'Acciaio'}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-slate-700 font-medium">{l.description}</p>
                                            <div className="grid grid-cols-2 gap-1 text-xs text-slate-500">
                                                <div>Acciaieria: <span className="text-slate-700">{l.acciaieria}</span></div>
                                                <div>Qta: <span className="text-slate-700">{l.quantity}</span></div>
                                            </div>
                                            <div className="text-xs">
                                                Cert. 3.1: <span className="font-mono font-semibold text-emerald-700">{l.cert_31}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* ── MATERIALI COMMESSA ── */}
                <Card>
                    <CardHeader className="pb-2 sm:pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <ClipboardList className="w-4 h-4 text-[#0055FF]" /> Materiali dalla Commessa
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div data-testid="materials-table">
                            {/* Desktop */}
                            <div className="hidden sm:block border rounded-lg overflow-hidden">
                                <table className="w-full">
                                    <thead>
                                        <tr className="bg-[#1E293B]">
                                            <th className="text-left text-white text-xs px-3 py-2">Descrizione</th>
                                            <th className="text-center text-white text-xs px-3 py-2 w-20">Qta</th>
                                            <th className="text-center text-white text-xs px-3 py-2 w-16">U.M.</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(ctx?.materiali || []).length > 0 ? ctx.materiali.map((m, i) => (
                                            <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                                                <td className="px-3 py-2 text-sm text-slate-700">{(m.description || '').substring(0, 120)}</td>
                                                <td className="px-3 py-2 text-sm text-center">{m.quantity}</td>
                                                <td className="px-3 py-2 text-sm text-center">{m.unit}</td>
                                            </tr>
                                        )) : (
                                            <tr><td colSpan={3} className="text-center py-4 text-slate-400 text-sm">Nessun materiale</td></tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            {/* Mobile */}
                            <div className="sm:hidden space-y-2">
                                {(ctx?.materiali || []).map((m, i) => (
                                    <div key={i} className="bg-slate-50 rounded-lg p-3 text-sm">
                                        <p className="text-slate-700">{(m.description || '').substring(0, 120)}</p>
                                        {(m.quantity || m.unit) && <p className="text-xs text-slate-500 mt-1">Qta: {m.quantity} {m.unit}</p>}
                                    </div>
                                ))}
                                {(ctx?.materiali || []).length === 0 && (
                                    <p className="text-center py-4 text-slate-400 text-sm">Nessun materiale</p>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* ── CHECKLIST ── */}
                <Card>
                    <CardHeader className="pb-2 sm:pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <CheckSquare className="w-4 h-4 text-[#0055FF]" /> Dichiarazioni Tecniche
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-1" data-testid="checklist-section">
                        {[
                            { key: 'check_regola_arte', label: 'Montaggio eseguito a regola d\'arte' },
                            { key: 'check_conformita', label: 'Conformita normative vigenti (NTC, EN 1090)' },
                            { key: 'check_materiali', label: 'Materiali conformi ai certificati 3.1' },
                            { key: 'check_sicurezza', label: 'Prescrizioni sicurezza D.Lgs 81/08 rispettate' },
                        ].map(item => (
                            <label key={item.key}
                                className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-colors"
                                data-testid={item.key}>
                                <Checkbox
                                    checked={form[item.key]}
                                    onCheckedChange={v => setField(item.key, v)}
                                    className="h-5 w-5"
                                />
                                <span className="text-sm sm:text-sm text-slate-700">{item.label}</span>
                            </label>
                        ))}
                    </CardContent>
                </Card>

                {/* ── NOTE ── */}
                <Card>
                    <CardHeader className="pb-2 sm:pb-3">
                        <CardTitle className="text-base">Note di Cantiere</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <textarea
                            value={form.note_cantiere}
                            onChange={e => setField('note_cantiere', e.target.value)}
                            rows={4}
                            className="w-full border rounded-xl p-3 text-base sm:text-sm resize-y focus:outline-none focus:ring-2 focus:ring-[#0055FF]/20 focus:border-[#0055FF]"
                            placeholder="Annotazioni del caposquadra, anomalie, meteo..."
                            data-testid="input-note"
                        />
                    </CardContent>
                </Card>

                {/* ── FOTO ── */}
                <Card>
                    <CardHeader className="pb-2 sm:pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Image className="w-4 h-4 text-[#0055FF]" /> Foto del Cantiere
                            <Badge variant="outline" className="text-[10px]">Max 3</Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <PhotoUpload photos={photos} setPhotos={setPhotos} />
                    </CardContent>
                </Card>

                {/* ── FIRMA ── */}
                <Card>
                    <CardHeader className="pb-2 sm:pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Pen className="w-4 h-4 text-[#0055FF]" /> Firma Committente
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-xs text-slate-500 mb-2">Firma per accettazione della posa in opera (funziona con touch su cellulare/tablet).</p>
                        <SignatureCanvas value={signature} onChange={setSignature} />
                    </CardContent>
                </Card>

                {/* ── FOOTER MOBILE ── */}
                <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2 pb-6">
                    <Button variant="outline" onClick={() => navigate(-1)} className="h-12 sm:h-9">Indietro</Button>
                    <div className="flex gap-2">
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF] hover:bg-[#0044CC] flex-1 h-12 sm:h-9 text-base sm:text-sm" data-testid="btn-save-bottom">
                            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                            Salva Verbale
                        </Button>
                        {saved && (
                            <Button variant="outline" onClick={handlePdf} disabled={genPdf}
                                className="border-[#0055FF] text-[#0055FF] flex-1 h-12 sm:h-9 text-base sm:text-sm" data-testid="btn-pdf-bottom">
                                {genPdf ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                                Genera PDF
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
