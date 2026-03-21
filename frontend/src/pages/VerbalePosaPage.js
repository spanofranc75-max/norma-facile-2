/**
 * VerbaleGosaPage — Dichiarazione di Corretta Posa in Opera.
 * Carica dati commessa, materiali, lotti EN 1090.
 * Checklist tecnica, upload foto cantiere, firma touch, generazione PDF.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest, API_BASE } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import {
    FileDown, Save, Loader2, Camera, X, Trash2, Pen, RotateCcw,
    CheckSquare, Building2, MapPin, ClipboardList, Send, Image,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

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
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
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
        <div className="space-y-2" data-testid="signature-canvas-wrapper">
            <div className="relative border-2 border-dashed border-slate-300 rounded-lg overflow-hidden bg-white">
                <canvas
                    ref={canvasRef}
                    width={600}
                    height={200}
                    className="w-full cursor-crosshair touch-none"
                    style={{ height: '150px' }}
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
                        <p className="text-slate-400 text-sm flex items-center gap-1"><Pen className="w-4 h-4" /> Firma qui (mouse o touch)</p>
                    </div>
                )}
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={clear} className="text-xs text-slate-500">
                <RotateCcw className="w-3 h-3 mr-1" /> Cancella firma
            </Button>
        </div>
    );
}

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
        <div className="space-y-2" data-testid="photo-upload">
            <div
                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                    dragOver ? 'border-[#0055FF] bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                } ${photos.length >= 3 ? 'opacity-50 pointer-events-none' : ''}`}
                onClick={() => inputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                data-testid="photo-dropzone"
            >
                <input ref={inputRef} type="file" accept="image/*" multiple className="hidden"
                    onChange={e => { addFiles(e.target.files); e.target.value = ''; }} />
                <Camera className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-sm text-slate-600">Trascina foto dal cellulare o clicca per selezionare</p>
                <p className="text-xs text-slate-400">Max 3 foto — JPG, PNG</p>
            </div>
            {photos.length > 0 && (
                <div className="grid grid-cols-3 gap-2">
                    {photos.map((p, i) => (
                        <div key={i} className="relative group rounded-lg overflow-hidden border border-slate-200" data-testid={`photo-preview-${i}`}>
                            <img src={p.preview} alt={p.name} className="w-full h-28 object-cover" />
                            <button
                                onClick={() => removePhoto(i)}
                                className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <X className="w-3 h-3" />
                            </button>
                            <p className="text-[10px] text-slate-500 text-center p-1 truncate">{p.name}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

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
                toast.error('Errore caricamento dati: ' + e.message);
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
            toast.success('PDF generato!');
        } catch (e) { toast.error(e.message); }
        finally { setGenPdf(false); }
    };

    const setField = (key, val) => setForm(f => ({ ...f, [key]: val }));

    if (loading) return <DashboardLayout><div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div></DashboardLayout>;

    return (
        <DashboardLayout>
            <div className="max-w-4xl mx-auto space-y-5" data-testid="verbale-posa-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Verbale di Posa in Opera</h1>
                        <p className="text-sm text-slate-500">
                            Commessa <strong>{ctx?.commessa_number}</strong> — {ctx?.client_name}
                        </p>
                    </div>
                    <div className="flex gap-2">
                        {saved && (
                            <>
                                <Button variant="outline" onClick={handlePdf} disabled={genPdf}
                                    className="border-[#0055FF] text-[#0055FF]" data-testid="btn-pdf">
                                    {genPdf ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                                    Genera PDF
                                </Button>
                                <Button variant="outline" disabled
                                    className="border-amber-300 text-amber-600 cursor-not-allowed" data-testid="btn-send-cims">
                                    <Send className="w-4 h-4 mr-2" /> Invia a CIMS
                                </Button>
                            </>
                        )}
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF] hover:bg-[#0044CC]" data-testid="btn-save">
                            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                            Salva Verbale
                        </Button>
                    </div>
                </div>

                {/* DATI CANTIERE */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-[#0055FF]" /> Dati del Cantiere
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-2 gap-4">
                        <div>
                            <Label className="text-xs">Data di Posa *</Label>
                            <Input type="date" value={form.data_posa} onChange={e => setField('data_posa', e.target.value)}
                                className="mt-1" data-testid="input-data-posa" />
                        </div>
                        <div>
                            <Label className="text-xs">Luogo / Cantiere *</Label>
                            <Input value={form.luogo_posa} onChange={e => setField('luogo_posa', e.target.value)}
                                placeholder="es. Via Roma 1, Loiano (BO)" className="mt-1" data-testid="input-luogo" />
                        </div>
                        <div>
                            <Label className="text-xs">Responsabile Montaggio</Label>
                            <Input value={form.responsabile} onChange={e => setField('responsabile', e.target.value)}
                                placeholder="Nome e cognome" className="mt-1" data-testid="input-responsabile" />
                        </div>
                        <div>
                            <Label className="text-xs">Committente</Label>
                            <Input value={ctx?.client_name || ''} disabled className="mt-1 bg-slate-50" />
                        </div>
                        <div>
                            <Label className="text-xs">Classe di Esecuzione</Label>
                            <Input value={ctx?.execution_class || 'N/A'} disabled className="mt-1 bg-slate-50" />
                        </div>
                        <div>
                            <Label className="text-xs">Impresa Esecutrice</Label>
                            <Input value={ctx?.company_name || 'Steel Project Design'} disabled className="mt-1 bg-slate-50" />
                        </div>
                    </CardContent>
                </Card>

                {/* MATERIALI */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <ClipboardList className="w-4 h-4 text-[#0055FF]" /> Materiali dalla Commessa
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="border rounded-lg overflow-hidden" data-testid="materials-table">
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
                                        <tr><td colSpan={3} className="text-center py-4 text-slate-400 text-sm">Nessun materiale dalla commessa</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>

                {/* LOTTI EN 1090 */}
                {(ctx?.lotti?.length > 0) && (
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <MapPin className="w-4 h-4 text-[#0055FF]" /> Lotti Materiale (EN 1090)
                                <Badge className="bg-blue-100 text-blue-700 text-[10px]">{ctx.lotti.length} lotti</Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="border rounded-lg overflow-hidden" data-testid="lotti-table">
                                <table className="w-full">
                                    <thead>
                                        <tr className="bg-[#1E293B]">
                                            <th className="text-left text-white text-xs px-3 py-2">N. Colata</th>
                                            <th className="text-left text-white text-xs px-3 py-2">Dimensioni</th>
                                            <th className="text-left text-white text-xs px-3 py-2">Acciaieria</th>
                                            <th className="text-left text-white text-xs px-3 py-2">Cert. 3.1</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ctx.lotti.map((l, i) => (
                                            <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                                                <td className="px-3 py-2 text-sm font-mono">{l.heat_number}</td>
                                                <td className="px-3 py-2 text-sm">{l.dimensions}</td>
                                                <td className="px-3 py-2 text-sm">{l.acciaieria}</td>
                                                <td className="px-3 py-2 text-sm">{l.cert_31}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* CHECKLIST */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <CheckSquare className="w-4 h-4 text-[#0055FF]" /> Dichiarazioni Tecniche
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3" data-testid="checklist-section">
                        {[
                            { key: 'check_regola_arte', label: 'Il montaggio e stato eseguito a regola d\'arte' },
                            { key: 'check_conformita', label: 'Conformita alle normative vigenti (D.M. 17/01/2018 — NTC, EN 1090)' },
                            { key: 'check_materiali', label: 'I materiali utilizzati sono conformi ai certificati 3.1' },
                            { key: 'check_sicurezza', label: 'Le prescrizioni di sicurezza (D.Lgs 81/08) sono state rispettate' },
                        ].map(item => (
                            <label key={item.key} className="flex items-center gap-3 p-2 rounded hover:bg-slate-50 cursor-pointer" data-testid={item.key}>
                                <Checkbox
                                    checked={form[item.key]}
                                    onCheckedChange={v => setField(item.key, v)}
                                />
                                <span className="text-sm text-slate-700">{item.label}</span>
                            </label>
                        ))}
                    </CardContent>
                </Card>

                {/* NOTE */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">Note di Cantiere</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <textarea
                            value={form.note_cantiere}
                            onChange={e => setField('note_cantiere', e.target.value)}
                            rows={4}
                            className="w-full border rounded-lg p-3 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-[#0055FF]/20 focus:border-[#0055FF]"
                            placeholder="Annotazioni del caposquadra, anomalie riscontrate, condizioni meteo..."
                            data-testid="input-note"
                        />
                    </CardContent>
                </Card>

                {/* FOTO */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Image className="w-4 h-4 text-[#0055FF]" /> Foto del Cantiere
                            <Badge variant="outline" className="text-[10px]">Max 3</Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <PhotoUpload photos={photos} setPhotos={setPhotos} />
                    </CardContent>
                </Card>

                {/* FIRMA */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Pen className="w-4 h-4 text-[#0055FF]" /> Firma del Committente / Responsabile
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-xs text-slate-500 mb-2">Il cliente firma qui per accettare la posa in opera. Funziona con mouse o touch su tablet/cellulare.</p>
                        <SignatureCanvas value={signature} onChange={setSignature} />
                    </CardContent>
                </Card>

                {/* FOOTER ACTIONS */}
                <div className="flex justify-between items-center py-4">
                    <Button variant="outline" onClick={() => navigate(-1)}>Indietro</Button>
                    <div className="flex gap-2">
                        <Button onClick={handleSave} disabled={saving} className="bg-[#0055FF] hover:bg-[#0044CC]" data-testid="btn-save-bottom">
                            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                            Salva Verbale
                        </Button>
                        {saved && (
                            <Button variant="outline" onClick={handlePdf} disabled={genPdf}
                                className="border-[#0055FF] text-[#0055FF]" data-testid="btn-pdf-bottom">
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
