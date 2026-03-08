/**
 * Perizia Sinistro — Sopralluogo Rapido (Mobile-First Wizard)
 * Step 1: Cantiere (GPS + ID)
 * Step 2: Foto (Camera + AI)
 * Step 3: Diagnosi (Tag Bubbles)
 * Step 4: Misure (Sliders + Toggles)
 * Step 5: Riepilogo (Preview + Quick Actions)
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import {
    Save, ArrowLeft, ArrowRight, Camera, Brain, MapPin, ShieldAlert,
    Wrench, Zap, PaintBucket, X, FileText, FileDown, Send, Ruler,
    Plus, Trash2, RefreshCw, Check, Locate, ImagePlus, Focus, Info, Percent,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const API = process.env.REACT_APP_BACKEND_URL;

const STEPS = [
    { key: 'cantiere', label: 'Cantiere', icon: MapPin },
    { key: 'foto', label: 'Foto', icon: Camera },
    { key: 'diagnosi', label: 'Diagnosi', icon: ShieldAlert },
    { key: 'misure', label: 'Misure', icon: Ruler },
    { key: 'riepilogo', label: 'Riepilogo', icon: FileText },
];

const SEVERITY_GROUPS = [
    { label: 'DANNO STRUTTURALE', color: 'red', codes: ['S1-DEF', 'S2-WELD'] },
    { label: 'DANNO ANCORAGGIO', color: 'orange', codes: ['A1-ANCH', 'A2-CONC'] },
    { label: 'DANNO ESTETICO / PROTETTIVO', color: 'blue', codes: ['P1-ZINC'] },
    { label: 'DANNO SICUREZZA', color: 'yellow', codes: ['G1-GAP'] },
    { label: 'DANNO AUTOMAZIONE', color: 'purple', codes: ['M1-FORCE'] },
];

const BG = {
    red: 'bg-red-50 border-red-200 hover:bg-red-100',
    orange: 'bg-orange-50 border-orange-200 hover:bg-orange-100',
    blue: 'bg-blue-50 border-blue-200 hover:bg-blue-100',
    yellow: 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100',
    purple: 'bg-purple-50 border-purple-200 hover:bg-purple-100',
};
const BG_SEL = {
    red: 'bg-red-500 border-red-600 text-white ring-4 ring-red-200',
    orange: 'bg-orange-500 border-orange-600 text-white ring-4 ring-orange-200',
    blue: 'bg-blue-500 border-blue-600 text-white ring-4 ring-blue-200',
    yellow: 'bg-yellow-500 border-yellow-600 text-white ring-4 ring-yellow-200',
    purple: 'bg-purple-500 border-purple-600 text-white ring-4 ring-purple-200',
};
const TEXT_COL = { red: 'text-red-700', orange: 'text-orange-700', blue: 'text-blue-700', yellow: 'text-yellow-700', purple: 'text-purple-700' };

function LocationPicker({ position, onSelect }) {
    useMapEvents({ click(e) { onSelect(e.latlng); } });
    return position ? <Marker position={position} /> : null;
}

export default function PeriziaEditorPage() {
    const { periziaId } = useParams();
    const navigate = useNavigate();
    const isNew = !periziaId;
    const fileInputRef = useRef(null);
    const detailInputRef = useRef(null);

    const [step, setStep] = useState(0);
    const [saving, setSaving] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [generatingLetter, setGeneratingLetter] = useState(false);
    const [recalcing, setRecalcing] = useState(false);
    const [periziaInfo, setPInfo] = useState({ number: null, status: 'bozza', perizia_id: null });

    // Data
    const [clientId, setClientId] = useState('');
    const [clients, setClients] = useState([]);
    const [tipoDanno, setTipoDanno] = useState('strutturale');
    const [codiciDanno, setCodiciDanno] = useState([]);
    const [codiciDannoDb, setCodiciDannoDb] = useState([]);
    const [descrizione, setDescrizione] = useState('');
    const [prezzoMl, setPrezzoMl] = useState('170');
    const [coeffMagg, setCoeffMagg] = useState('20');
    const [moduli, setModuli] = useState([{ descrizione: 'Modulo 1', lunghezza_ml: 6, altezza_m: 1.5, note: '' }]);
    const [photos, setPhotos] = useState([]);
    const [aiAnalysis, setAiAnalysis] = useState('');
    const [aiSuggestions, setAiSuggestions] = useState([]);
    const [statoDiFatto, setStatoDiFatto] = useState('');
    const [notaTecnica, setNotaTecnica] = useState('');
    const [vociCosto, setVociCosto] = useState([]);
    const [letteraAccompagnamento, setLetteraAccompagnamento] = useState('');
    const [notes, setNotes] = useState('');
    const [needsSmaltimento, setNeedsSmaltimento] = useState(true);
    const [accessoDifficile, setAccessoDifficile] = useState(false);
    const [scontoCortesia, setScontoCortesia] = useState(0);
    const [openTooltip, setOpenTooltip] = useState(null);

    // Geo
    const [mapPos, setMapPos] = useState(null);
    const [indirizzo, setIndirizzo] = useState('');
    const [comune, setComune] = useState('');
    const [provincia, setProvincia] = useState('');
    const [mapCenter, setMapCenter] = useState([41.9028, 12.4964]);
    const [geoLoading, setGeoLoading] = useState(false);

    useEffect(() => {
        apiRequest('/clients/?limit=200').then(d => setClients(d.clients || [])).catch(() => {});
        apiRequest('/perizie/codici-danno').then(d => setCodiciDannoDb(d.codici_danno || [])).catch(() => {});
    }, []);

    // Load existing
    const loadPerizia = useCallback(async () => {
        if (isNew) return;
        try {
            const data = await apiRequest(`/perizie/${periziaId}`);
            setPInfo({ number: data.number, status: data.status, perizia_id: data.perizia_id });
            setClientId(data.client_id || '');
            setTipoDanno(data.tipo_danno || 'strutturale');
            setCodiciDanno(data.codici_danno || []);
            setDescrizione(data.descrizione_utente || '');
            setPrezzoMl(String(data.prezzo_ml_originale || 170));
            setCoeffMagg(String(data.coefficiente_maggiorazione ?? 20));
            setModuli(data.moduli?.length ? data.moduli : [{ descrizione: 'Modulo 1', lunghezza_ml: 6, altezza_m: 1.5, note: '' }]);
            setPhotos(data.foto || []);
            setAiAnalysis(data.ai_analysis || '');
            setStatoDiFatto(data.stato_di_fatto || '');
            setNotaTecnica(data.nota_tecnica || '');
            setVociCosto(data.voci_costo || []);
            setLetteraAccompagnamento(data.lettera_accompagnamento || '');
            setNotes(data.notes || '');
            if (data.smaltimento !== undefined) setNeedsSmaltimento(data.smaltimento);
            if (data.accesso_difficile !== undefined) setAccessoDifficile(data.accesso_difficile);
            if (data.sconto_cortesia !== undefined) setScontoCortesia(data.sconto_cortesia);
            const loc = data.localizzazione || {};
            if (loc.lat && loc.lng) {
                setMapPos({ lat: loc.lat, lng: loc.lng });
                setMapCenter([loc.lat, loc.lng]);
            }
            setIndirizzo(loc.indirizzo || '');
            setComune(loc.comune || '');
            setProvincia(loc.provincia || '');
            if (data.voci_costo?.length) setStep(4); // Jump to riepilogo if already has costs
        } catch { toast.error('Errore caricamento perizia'); navigate('/perizie'); }
    }, [isNew, periziaId, navigate]);

    useEffect(() => { loadPerizia(); }, [loadPerizia]);

    // Auto GPS
    const handleAutoGeo = () => {
        if (!navigator.geolocation) { toast.error('GPS non disponibile'); return; }
        setGeoLoading(true);
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const latlng = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                setMapPos(latlng);
                setMapCenter([latlng.lat, latlng.lng]);
                try {
                    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latlng.lat}&lon=${latlng.lng}&format=json&accept-language=it`);
                    const data = await res.json();
                    if (data.address) {
                        const a = data.address;
                        setIndirizzo(`${a.road || ''} ${a.house_number || ''}`.trim() || data.display_name?.split(',')[0] || '');
                        setComune(a.city || a.town || a.village || '');
                        setProvincia(a.county || a.state || '');
                    }
                } catch { /* ignore */ }
                setGeoLoading(false);
                toast.success('Posizione rilevata');
            },
            () => { setGeoLoading(false); toast.error('Impossibile rilevare la posizione'); },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };

    const handleMapClick = async (latlng) => {
        setMapPos(latlng);
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latlng.lat}&lon=${latlng.lng}&format=json&accept-language=it`);
            const data = await res.json();
            if (data.address) {
                const a = data.address;
                setIndirizzo(`${a.road || ''} ${a.house_number || ''}`.trim());
                setComune(a.city || a.town || a.village || '');
                setProvincia(a.county || a.state || '');
            }
        } catch { /* ignore */ }
    };

    // Photo upload
    const handlePhotoUpload = async (e) => {
        const files = Array.from(e.target.files);
        e.target.value = '';
        if (!periziaId || isNew) {
            // For new perizie, save first then upload
            toast.error('Salva la perizia prima di caricare foto');
            return;
        }
        const currentObjCount = photos.filter(p => typeof p === 'object').length;
        if (currentObjCount + files.length > 5) { toast.error('Massimo 5 foto'); return; }
        for (const file of files) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch(`${API}/api/perizie/${periziaId}/upload-foto`, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData,
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || 'Upload fallito');
                }
                const fotoEntry = await res.json();
                setPhotos(prev => [...prev, fotoEntry]);
            } catch (err) { toast.error(err.message); }
        }
    };

    const handleDeletePhoto = async (photo, idx) => {
        // Object storage photo (new format)
        if (typeof photo === 'object' && photo.foto_id) {
            try {
                await apiRequest(`/perizie/${periziaId}/foto/${photo.foto_id}`, { method: 'DELETE' });
                setPhotos(prev => prev.filter((_, i) => i !== idx));
            } catch { toast.error('Errore eliminazione foto'); }
        } else {
            // Legacy base64 — just remove from array
            setPhotos(prev => prev.filter((_, i) => i !== idx));
        }
    };

    const getPhotoSrc = (photo) => {
        // Object storage photo (new format) — use proxy
        if (typeof photo === 'object' && photo.storage_path) {
            return `${API}/api/perizie/foto-proxy/${photo.storage_path}`;
        }
        // Legacy base64 string
        if (typeof photo === 'string' && photo.startsWith('data:')) {
            return photo;
        }
        return '';
    };

    // Module management
    const addModule = () => setModuli(p => [...p, { descrizione: `Modulo ${p.length + 1}`, lunghezza_ml: 3, altezza_m: 1.5, note: '' }]);
    const removeModule = (i) => setModuli(p => p.filter((_, idx) => idx !== i));
    const updateModule = (i, f, v) => setModuli(p => p.map((m, idx) => idx === i ? { ...m, [f]: v } : m));

    const totalMl = moduli.reduce((s, m) => s + (parseFloat(m.lunghezza_ml) || 0), 0);
    const prezzoMagg = (parseFloat(prezzoMl) || 0) * (1 + (parseFloat(coeffMagg) || 0) / 100);
    const totalePerizia = vociCosto.reduce((s, v) => s + (parseFloat(v.totale) || 0), 0);

    // Toggle damage code
    const toggleCode = (code) => setCodiciDanno(prev => prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]);

    // Auto-detect tipo from codes
    useEffect(() => {
        if (codiciDanno.length === 0) return;
        const hasStruct = codiciDanno.some(c => c.startsWith('S'));
        const hasAuto = codiciDanno.some(c => c.startsWith('M'));
        if (hasStruct) setTipoDanno('strutturale');
        else if (hasAuto) setTipoDanno('automatismi');
        else setTipoDanno('estetico');
    }, [codiciDanno]);

    // Save
    const handleSave = async () => {
        setSaving(true);
        const payload = {
            client_id: clientId || null,
            localizzazione: { indirizzo, lat: mapPos?.lat || 0, lng: mapPos?.lng || 0, comune, provincia },
            tipo_danno: tipoDanno,
            descrizione_utente: descrizione,
            codici_danno: codiciDanno,
            prezzo_ml_originale: parseFloat(prezzoMl) || 0,
            coefficiente_maggiorazione: parseFloat(coeffMagg) || 20,
            moduli,
            ai_analysis: aiAnalysis, stato_di_fatto: statoDiFatto,
            nota_tecnica: notaTecnica, voci_costo: vociCosto,
            lettera_accompagnamento: letteraAccompagnamento, notes,
            smaltimento: needsSmaltimento,
            accesso_difficile: accessoDifficile,
            sconto_cortesia: scontoCortesia,
        };
        try {
            if (isNew) {
                const res = await apiRequest('/perizie/', { method: 'POST', body: payload });
                toast.success(`Perizia ${res.number} creata`);
                navigate(`/perizie/${res.perizia_id}`);
            } else {
                await apiRequest(`/perizie/${periziaId}`, { method: 'PUT', body: payload });
                toast.success('Perizia salvata');
                loadPerizia();
            }
        } catch (e) { toast.error(e.message); }
        finally { setSaving(false); }
    };

    // AI Analyze Photos
    const handleAnalyze = async () => {
        if (isNew) { await handleSave(); return; }
        if (photos.length === 0) { toast.error('Carica almeno una foto'); return; }
        setAnalyzing(true);
        try {
            // Save metadata before analysis (photos are already on object storage)
            await apiRequest(`/perizie/${periziaId}`, { method: 'PUT', body: { descrizione_utente: descrizione, tipo_danno: tipoDanno, codici_danno: codiciDanno } });
            const res = await apiRequest(`/perizie/${periziaId}/analyze-photos`, { method: 'POST' });
            setAiAnalysis(res.ai_analysis || '');
            setStatoDiFatto(res.stato_di_fatto || '');
            setNotaTecnica(res.nota_tecnica || '');
            // Parse AI suggestions for tags
            const text = (res.ai_analysis || '').toLowerCase();
            const suggestions = [];
            if (text.includes('deformaz') || text.includes('piega') || text.includes('snervamento')) suggestions.push('S1-DEF');
            if (text.includes('saldatura') || text.includes('cricca') || text.includes('rottura')) suggestions.push('S2-WELD');
            if (text.includes('tassello') || text.includes('ancor') || text.includes('piastra')) suggestions.push('A1-ANCH');
            if (text.includes('cemento') || text.includes('cordolo') || text.includes('crepa')) suggestions.push('A2-CONC');
            if (text.includes('zincat') || text.includes('ruggine') || text.includes('ossid') || text.includes('vernice')) suggestions.push('P1-ZINC');
            if (text.includes('distanz') || text.includes('cesoiam') || text.includes('schiaccia')) suggestions.push('G1-GAP');
            if (text.includes('motore') || text.includes('automazion') || text.includes('centralina')) suggestions.push('M1-FORCE');
            setAiSuggestions(suggestions.filter(s => !codiciDanno.includes(s)));
            toast.success('Analisi AI completata');
        } catch (e) { toast.error(e.message); }
        finally { setAnalyzing(false); }
    };

    // Recalculate costs
    const handleRecalc = async () => {
        if (isNew) { toast.error('Salva prima la perizia'); return; }
        setRecalcing(true);
        try {
            await apiRequest(`/perizie/${periziaId}`, { method: 'PUT', body: { tipo_danno: tipoDanno, prezzo_ml_originale: parseFloat(prezzoMl) || 0, coefficiente_maggiorazione: parseFloat(coeffMagg) || 20, moduli, codici_danno: codiciDanno, smaltimento: needsSmaltimento, accesso_difficile: accessoDifficile, sconto_cortesia: scontoCortesia } });
            const res = await apiRequest(`/perizie/${periziaId}/recalc`, { method: 'POST' });
            setVociCosto(res.voci_costo || []);
            toast.success(`Totale: ${res.total_perizia?.toFixed(2)} EUR`);
        } catch (e) { toast.error(e.message); }
        finally { setRecalcing(false); }
    };

    // Generate letter
    const handleGeneraLettera = async () => {
        if (isNew) { toast.error('Salva prima'); return; }
        setGeneratingLetter(true);
        try {
            await apiRequest(`/perizie/${periziaId}`, { method: 'PUT', body: { stato_di_fatto: statoDiFatto, nota_tecnica: notaTecnica, descrizione_utente: descrizione, tipo_danno: tipoDanno } });
            const res = await apiRequest(`/perizie/${periziaId}/genera-lettera`, { method: 'POST' });
            setLetteraAccompagnamento(res.lettera_accompagnamento || '');
            toast.success('Lettera generata');
        } catch (e) { toast.error(e.message); }
        finally { setGeneratingLetter(false); }
    };

    // Accept AI suggestion
    const acceptSuggestion = (code) => {
        setCodiciDanno(prev => [...prev, code]);
        setAiSuggestions(prev => prev.filter(s => s !== code));
        toast.success(`Tag ${code} aggiunto`);
    };

    const canNext = () => {
        if (step === 0) return !!indirizzo || !!mapPos;
        if (step === 1) return photos.length > 0;
        if (step === 2) return codiciDanno.length > 0;
        if (step === 3) return totalMl > 0;
        return true;
    };

    const goNext = async () => {
        if (step === 3 && isNew) {
            await handleSave();
            return;
        }
        if (step === 3 && !isNew) {
            await handleRecalc();
        }
        setStep(s => Math.min(s + 1, 4));
    };

    const currentStep = STEPS[step];

    return (
        <DashboardLayout>
            <div className="max-w-2xl mx-auto space-y-4" data-testid="perizia-editor-page">
                {/* Header Bar */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" onClick={() => step > 0 ? setStep(s => s - 1) : navigate('/perizie')} className="text-slate-500 h-10 w-10 p-0">
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div>
                            <h1 className="text-lg font-bold text-[#1E293B]">
                                {isNew ? 'Sopralluogo Rapido' : `Perizia ${periziaInfo.number || ''}`}
                            </h1>
                            {periziaInfo.number && <Badge className="bg-slate-100 text-slate-600 text-[10px]">{periziaInfo.status?.toUpperCase()}</Badge>}
                        </div>
                    </div>
                    <Button data-testid="btn-save" onClick={handleSave} disabled={saving} size="sm" className="bg-[#0055FF] text-white h-10 px-4">
                        <Save className="h-4 w-4 mr-1.5" /> {saving ? '...' : 'Salva'}
                    </Button>
                </div>

                {/* Step Indicator */}
                <div className="flex items-center gap-1 px-2">
                    {STEPS.map((s, i) => {
                        const Icon = s.icon;
                        const active = i === step;
                        const done = i < step;
                        return (
                            <button
                                key={s.key}
                                data-testid={`step-${s.key}`}
                                onClick={() => setStep(i)}
                                className={`flex-1 flex flex-col items-center gap-1 py-2 rounded-lg transition-all ${
                                    active ? 'bg-[#0055FF] text-white' : done ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-50 text-slate-400'
                                }`}
                            >
                                {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                                <span className="text-[10px] font-semibold">{s.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* ═══ STEP 1: CANTIERE ═══ */}
                {step === 0 && (
                    <div className="space-y-4">
                        {/* Auto GPS Box */}
                        <Card className="border-gray-200 overflow-hidden">
                            <div className="bg-[#1E293B] p-3 flex items-center justify-between">
                                <div className="text-white">
                                    <p className="text-xs font-medium opacity-70">POSIZIONE CANTIERE</p>
                                    <p className="text-sm font-bold mt-0.5" data-testid="geo-address">
                                        {indirizzo ? `${indirizzo}, ${comune} (${provincia})` : 'Posizione non rilevata'}
                                    </p>
                                    {mapPos && <p className="text-[10px] opacity-50 font-mono mt-0.5">{mapPos.lat.toFixed(5)}, {mapPos.lng.toFixed(5)}</p>}
                                </div>
                                <Button
                                    data-testid="btn-auto-gps"
                                    onClick={handleAutoGeo}
                                    disabled={geoLoading}
                                    className="bg-[#0055FF] hover:bg-[#0044CC] text-white h-12 px-4"
                                >
                                    <Locate className={`h-5 w-5 mr-2 ${geoLoading ? 'animate-spin' : ''}`} />
                                    {geoLoading ? 'Rilevo...' : 'GPS Auto'}
                                </Button>
                            </div>
                            <CardContent className="p-3 space-y-2">
                                <div className="flex gap-2">
                                    <Input data-testid="input-indirizzo" value={indirizzo} onChange={e => setIndirizzo(e.target.value)} placeholder="Via / Piazza..." className="flex-1 h-11 text-sm" />
                                    <Input value={comune} onChange={e => setComune(e.target.value)} placeholder="Comune" className="w-32 h-11 text-sm" />
                                    <Input value={provincia} onChange={e => setProvincia(e.target.value)} placeholder="Pr." className="w-16 h-11 text-sm" />
                                </div>
                                <div className="rounded-lg overflow-hidden border border-slate-200" style={{ height: 220 }} data-testid="map-container">
                                    <MapContainer center={mapCenter} zoom={14} style={{ height: '100%', width: '100%' }} key={`${mapCenter[0]}-${mapCenter[1]}`}>
                                        <TileLayer attribution='&copy; OSM' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                                        <LocationPicker position={mapPos} onSelect={handleMapClick} />
                                    </MapContainer>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Client */}
                        <Card className="border-gray-200">
                            <CardContent className="p-3">
                                <Label className="text-xs text-slate-500">Cliente / Assicurato (opzionale)</Label>
                                <Select value={clientId || '__none__'} onValueChange={v => setClientId(v === '__none__' ? '' : v)}>
                                    <SelectTrigger data-testid="select-client" className="h-11 mt-1"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                        {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </CardContent>
                        </Card>

                        {/* Description */}
                        <Card className="border-gray-200">
                            <CardContent className="p-3">
                                <Label className="text-xs text-slate-500">Descrizione rapida del sinistro</Label>
                                <Textarea data-testid="input-descrizione" value={descrizione} onChange={e => setDescrizione(e.target.value)} placeholder="Es: Urto da furgone sulla recinzione lato strada..." rows={3} className="mt-1 text-sm" />
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ═══ STEP 2: FOTO ═══ */}
                {step === 1 && (
                    <div className="space-y-4">
                        <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={handlePhotoUpload} />
                        <input ref={detailInputRef} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={handlePhotoUpload} />

                        {/* Camera Buttons */}
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                data-testid="btn-foto-panoramica"
                                onClick={() => fileInputRef.current?.click()}
                                className="p-6 rounded-2xl border-2 border-dashed border-blue-300 bg-blue-50 hover:bg-blue-100 flex flex-col items-center gap-2 transition-colors"
                            >
                                <ImagePlus className="h-10 w-10 text-blue-500" />
                                <span className="text-sm font-bold text-blue-700">Foto Panoramica</span>
                                <span className="text-[10px] text-blue-500">Per il contesto generale</span>
                            </button>
                            <button
                                data-testid="btn-foto-dettaglio"
                                onClick={() => detailInputRef.current?.click()}
                                className="p-6 rounded-2xl border-2 border-dashed border-red-300 bg-red-50 hover:bg-red-100 flex flex-col items-center gap-2 transition-colors"
                            >
                                <Focus className="h-10 w-10 text-red-500" />
                                <span className="text-sm font-bold text-red-700">Dettaglio Danno</span>
                                <span className="text-[10px] text-red-500">Macro su deformazioni</span>
                            </button>
                        </div>

                        {/* Photo Grid */}
                        {photos.length > 0 && (
                            <div className="grid grid-cols-3 gap-2">
                                {photos.map((p, i) => (
                                    <div key={i} className="relative group rounded-xl overflow-hidden">
                                        <img src={getPhotoSrc(p)} alt={`Foto ${i + 1}`} className="w-full h-28 object-cover" />
                                        <button onClick={() => handleDeletePhoto(p, i)} className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <X className="h-3.5 w-3.5" />
                                        </button>
                                        <div className="absolute bottom-0 left-0 right-0 bg-black/40 text-white text-[10px] text-center py-0.5">{i + 1}/{photos.length}</div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <p className="text-center text-xs text-slate-400">{photos.length}/5 foto caricate</p>

                        {/* AI Analysis Button */}
                        {photos.length > 0 && (
                            <Button
                                data-testid="btn-ai-analyze"
                                onClick={handleAnalyze}
                                disabled={analyzing}
                                className="w-full h-14 text-base bg-gradient-to-r from-indigo-600 to-blue-600 text-white hover:from-indigo-700 hover:to-blue-700 rounded-xl"
                            >
                                <Brain className="h-5 w-5 mr-2" />
                                {analyzing ? 'Analisi in corso...' : 'Analizza con AI (GPT-4o)'}
                            </Button>
                        )}

                        {/* AI Suggestions */}
                        {aiSuggestions.length > 0 && (
                            <Card className="border-indigo-200 bg-indigo-50/50">
                                <CardContent className="p-3">
                                    <p className="text-xs font-bold text-indigo-700 mb-2 flex items-center gap-1"><Brain className="h-3.5 w-3.5" /> Parere dell'AI — Tag suggeriti:</p>
                                    <div className="space-y-2">
                                        {aiSuggestions.map(s => {
                                            const cd = codiciDannoDb.find(c => c.codice === s);
                                            return cd ? (
                                                <div key={s} className="flex items-center justify-between bg-white rounded-lg p-2 border border-indigo-100">
                                                    <div>
                                                        <span className="font-mono font-bold text-xs text-indigo-700">{s}</span>
                                                        <span className="text-xs text-slate-600 ml-2">{cd.label}</span>
                                                    </div>
                                                    <Button size="sm" onClick={() => acceptSuggestion(s)} className="h-8 bg-indigo-600 text-white text-xs">
                                                        <Plus className="h-3 w-3 mr-1" /> Applica
                                                    </Button>
                                                </div>
                                            ) : null;
                                        })}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* AI Analysis Text */}
                        {aiAnalysis && (
                            <Card className="border-indigo-200">
                                <CardContent className="p-3">
                                    <p className="text-xs font-bold text-indigo-700 mb-1">Analisi AI del danno:</p>
                                    <pre className="text-[11px] text-slate-600 whitespace-pre-wrap font-sans leading-relaxed max-h-40 overflow-y-auto">{aiAnalysis}</pre>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                )}

                {/* ═══ STEP 3: DIAGNOSI ═══ */}
                {step === 2 && (
                    <div className="space-y-4">
                        <p className="text-sm text-slate-600 text-center">Seleziona i danni rilevati durante il sopralluogo</p>

                        {SEVERITY_GROUPS.map(group => {
                            const codes = group.codes.map(c => codiciDannoDb.find(cd => cd.codice === c)).filter(Boolean);
                            if (codes.length === 0) return null;
                            return (
                                <div key={group.label}>
                                    <p className={`text-[11px] font-bold uppercase tracking-wider mb-2 ${TEXT_COL[group.color]}`}>
                                        {group.label}
                                    </p>
                                    <div className="grid grid-cols-1 gap-2">
                                        {codes.map(cd => {
                                            const sel = codiciDanno.includes(cd.codice);
                                            return (
                                                <button
                                                    key={cd.codice}
                                                    data-testid={`tag-${cd.codice}`}
                                                    onClick={() => toggleCode(cd.codice)}
                                                    className={`p-4 rounded-xl border-2 text-left transition-all ${sel ? BG_SEL[group.color] : BG[group.color]}`}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <span className={`text-lg font-mono font-black ${sel ? '' : TEXT_COL[group.color]}`}>{cd.codice}</span>
                                                            <div>
                                                                <p className="text-sm font-bold">{cd.label}</p>
                                                                <p className={`text-[10px] ${sel ? 'opacity-80' : 'opacity-60'}`}>{cd.norma} — {cd.azione}</p>
                                                            </div>
                                                        </div>
                                                        {sel && <Check className="h-6 w-6" />}
                                                    </div>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}

                        {codiciDanno.length > 0 && (
                            <Card className="border-[#0055FF]/30 bg-[#0055FF]/5">
                                <CardContent className="p-3">
                                    <p className="text-[10px] font-bold text-[#0055FF] mb-1">NORME ATTIVATE:</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {[...new Set(codiciDanno.map(c => codiciDannoDb.find(cd => cd.codice === c)?.norma).filter(Boolean))].map(n => (
                                            <Badge key={n} className="bg-[#0055FF] text-white text-[10px] px-2 py-0.5">{n}</Badge>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                )}

                {/* ═══ STEP 4: MISURE ═══ */}
                {step === 3 && (
                    <div className="space-y-4">
                        {/* Modules */}
                        <Card className="border-gray-200">
                            <CardContent className="p-3 space-y-3">
                                <div className="flex items-center justify-between">
                                    <Label className="text-sm font-bold text-[#1E293B]">Moduli Danneggiati</Label>
                                    <Button data-testid="btn-add-module" variant="outline" size="sm" onClick={addModule} className="h-8"><Plus className="h-3.5 w-3.5 mr-1" /> Modulo</Button>
                                </div>
                                {moduli.map((m, i) => (
                                    <div key={i} className="bg-slate-50 rounded-xl p-3 space-y-2" data-testid={`module-${i}`}>
                                        <div className="flex items-center justify-between">
                                            <Input value={m.descrizione} onChange={e => updateModule(i, 'descrizione', e.target.value)} className="h-9 text-sm font-medium flex-1 mr-2" />
                                            {moduli.length > 1 && <Button variant="ghost" size="sm" onClick={() => removeModule(i)} className="h-8 w-8 p-0 text-red-400"><X className="h-4 w-4" /></Button>}
                                        </div>
                                        <div>
                                            <div className="flex items-center justify-between mb-1">
                                                <Label className="text-[10px] text-slate-500">Lunghezza: <strong className="text-[#1E293B]">{m.lunghezza_ml} ml</strong></Label>
                                            </div>
                                            <input
                                                type="range" min="0.5" max="12" step="0.5"
                                                value={m.lunghezza_ml}
                                                onChange={e => updateModule(i, 'lunghezza_ml', parseFloat(e.target.value))}
                                                className="w-full h-3 rounded-full appearance-none cursor-pointer accent-[#0055FF]"
                                                data-testid={`slider-length-${i}`}
                                            />
                                            <div className="flex justify-between text-[9px] text-slate-400 mt-0.5"><span>0.5</span><span>6</span><span>12 ml</span></div>
                                        </div>
                                        <div>
                                            <div className="flex items-center justify-between mb-1">
                                                <Label className="text-[10px] text-slate-500">Altezza: <strong className="text-[#1E293B]">{m.altezza_m} m</strong></Label>
                                            </div>
                                            <input
                                                type="range" min="0.5" max="3" step="0.1"
                                                value={m.altezza_m}
                                                onChange={e => updateModule(i, 'altezza_m', parseFloat(e.target.value))}
                                                className="w-full h-3 rounded-full appearance-none cursor-pointer accent-[#0055FF]"
                                            />
                                            <div className="flex justify-between text-[9px] text-slate-400 mt-0.5"><span>0.5</span><span>1.5</span><span>3.0 m</span></div>
                                        </div>
                                    </div>
                                ))}
                                <div className="text-center py-1">
                                    <span className="text-sm font-bold text-[#0055FF]">Totale: {totalMl.toFixed(1)} ml</span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Pricing */}
                        <Card className="border-gray-200">
                            <CardContent className="p-3 space-y-3">
                                <Label className="text-sm font-bold text-[#1E293B] flex items-center gap-2"><Wrench className="h-4 w-4 text-[#0055FF]" /> Prezzi</Label>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label className="text-[10px] text-slate-500">Prezzo originale (EUR/ml)</Label>
                                        <Input data-testid="input-prezzo-ml" type="number" value={prezzoMl} onChange={e => setPrezzoMl(e.target.value)} className="h-11 text-lg font-mono font-bold" />
                                    </div>
                                    <div>
                                        <Label className="text-[10px] text-slate-500">Maggiorazione (%)</Label>
                                        <Input data-testid="input-coeff" type="number" value={coeffMagg} onChange={e => setCoeffMagg(e.target.value)} className="h-11 text-lg font-mono font-bold" />
                                    </div>
                                </div>
                                <div className="bg-[#0055FF]/5 rounded-lg p-2 text-center">
                                    <span className="text-xs text-slate-500">Prezzo maggiorato: </span>
                                    <span className="text-base font-bold text-[#0055FF] font-mono">{prezzoMagg.toFixed(2)} EUR/ml</span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Quick Toggles */}
                        <Card className="border-gray-200">
                            <CardContent className="p-3 space-y-3">
                                <Label className="text-sm font-bold text-[#1E293B]">Opzioni Aggiuntive</Label>
                                <div className="flex items-center justify-between py-2">
                                    <div>
                                        <p className="text-sm font-medium text-[#1E293B]">Smaltimento in discarica</p>
                                        <p className="text-[10px] text-slate-500">CER 170405 — Ferro e acciaio</p>
                                    </div>
                                    <Switch data-testid="toggle-smaltimento" checked={needsSmaltimento} onCheckedChange={setNeedsSmaltimento} />
                                </div>
                                <Separator />
                                <div className="flex items-center justify-between py-2">
                                    <div>
                                        <p className="text-sm font-medium text-[#1E293B]">Accesso cantiere difficile</p>
                                        <p className="text-[10px] text-slate-500">Maggiorazione trasporto speciale</p>
                                    </div>
                                    <Switch data-testid="toggle-accesso" checked={accessoDifficile} onCheckedChange={setAccessoDifficile} />
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* ═══ STEP 5: RIEPILOGO ═══ */}
                {step === 4 && (
                    <div className="space-y-4">
                        {/* Summary Header */}
                        <Card className="border-[#0055FF]/30 bg-gradient-to-br from-[#0055FF]/5 to-transparent overflow-hidden">
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-slate-500">TOTALE PERIZIA</p>
                                        <p className="text-3xl font-black text-[#0055FF] font-mono" data-testid="total-perizia">
                                            {totalePerizia.toLocaleString('it-IT', { minimumFractionDigits: 2 })} EUR
                                        </p>
                                    </div>
                                    <div className="text-right space-y-1">
                                        <Badge className="bg-slate-100 text-slate-600 text-[10px]">{codiciDanno.length} codici danno</Badge>
                                        <p className="text-xs text-slate-400">{totalMl.toFixed(1)} ml totali</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Cost Table */}
                        <Card className="border-gray-200">
                            <CardContent className="p-0">
                                <div className="flex items-center justify-between p-3 border-b bg-slate-50">
                                    <p className="text-xs font-bold text-[#1E293B]">Computo Metrico Estimativo</p>
                                    <Button data-testid="btn-recalc" variant="outline" size="sm" onClick={handleRecalc} disabled={recalcing} className="h-7 text-xs">
                                        <RefreshCw className={`h-3 w-3 mr-1 ${recalcing ? 'animate-spin' : ''}`} /> Ricalcola
                                    </Button>
                                </div>
                                <div className="divide-y divide-slate-100">
                                    {vociCosto.map((v, i) => (
                                        <div key={i} className="p-3 hover:bg-slate-50" data-testid={`voce-row-${i}`}>
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1 min-w-0">
                                                    <span className="font-mono text-xs font-bold text-[#0055FF]">{v.codice}</span>
                                                    <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{v.descrizione}</p>
                                                </div>
                                                <div className="text-right shrink-0">
                                                    <p className="text-sm font-bold font-mono text-[#1E293B]">{parseFloat(v.totale || 0).toFixed(2)}</p>
                                                    <p className="text-[9px] text-slate-400">{v.quantita} {v.unita} x {parseFloat(v.prezzo_unitario || 0).toFixed(2)}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="p-3 bg-[#1E293B] flex items-center justify-between">
                                    <span className="text-sm font-bold text-white">TOTALE</span>
                                    <span className="text-lg font-black text-white font-mono">{totalePerizia.toLocaleString('it-IT', { minimumFractionDigits: 2 })} EUR</span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Stato di Fatto */}
                        {statoDiFatto && (
                            <Card className="border-gray-200">
                                <CardContent className="p-3">
                                    <p className="text-xs font-bold text-[#1E293B] mb-1">Stato di Fatto</p>
                                    <Textarea data-testid="input-stato-fatto" value={statoDiFatto} onChange={e => setStatoDiFatto(e.target.value)} rows={4} className="text-xs" />
                                </CardContent>
                            </Card>
                        )}

                        {/* Nota Tecnica */}
                        {notaTecnica && (
                            <Card className="border-gray-200">
                                <CardContent className="p-3">
                                    <p className="text-xs font-bold text-[#1E293B] mb-1">Nota Tecnica per il Perito</p>
                                    <Textarea data-testid="input-nota-tecnica" value={notaTecnica} onChange={e => setNotaTecnica(e.target.value)} rows={3} className="text-xs" />
                                </CardContent>
                            </Card>
                        )}

                        {/* Lettera */}
                        {letteraAccompagnamento && (
                            <Card className="border-amber-200">
                                <CardContent className="p-3">
                                    <p className="text-xs font-bold text-amber-700 mb-1">Lettera Accompagnamento Tecnica</p>
                                    <Textarea data-testid="input-lettera" value={letteraAccompagnamento} onChange={e => setLetteraAccompagnamento(e.target.value)} rows={6} className="text-xs font-serif" />
                                </CardContent>
                            </Card>
                        )}

                        <Separator />

                        {/* ═══ QUICK ACTION FOOTER ═══ */}
                        <div className="space-y-2">
                            <Button
                                data-testid="btn-genera-preventivo"
                                onClick={handleRecalc}
                                disabled={recalcing}
                                className="w-full h-14 text-base bg-[#0055FF] text-white hover:bg-[#0044CC] rounded-xl"
                            >
                                <FileText className="h-5 w-5 mr-2" />
                                {recalcing ? 'Generazione...' : 'Genera Preventivo Normato'}
                            </Button>

                            <Button
                                data-testid="btn-genera-lettera"
                                onClick={handleGeneraLettera}
                                disabled={generatingLetter}
                                variant="outline"
                                className="w-full h-14 text-base border-amber-400 text-amber-700 hover:bg-amber-50 rounded-xl"
                            >
                                <FileText className="h-5 w-5 mr-2" />
                                {generatingLetter ? 'Generazione AI...' : 'Lettera Perito (EN 1090/13241)'}
                            </Button>

                            {!isNew && (
                                <Button
                                    data-testid="btn-pdf"
                                    onClick={() => window.open(`${API}/api/perizie/${periziaId}/pdf`, '_blank')}
                                    variant="outline"
                                    className="w-full h-14 text-base border-[#0055FF] text-[#0055FF] hover:bg-blue-50 rounded-xl"
                                >
                                    <FileDown className="h-5 w-5 mr-2" /> Scarica PDF Perizia
                                </Button>
                            )}

                            {!isNew && (
                                <Button
                                    data-testid="btn-share"
                                    onClick={() => {
                                        const text = `Perizia ${periziaInfo.number} — Totale: ${totalePerizia.toFixed(2)} EUR\nPDF: ${API}/api/perizie/${periziaId}/pdf`;
                                        if (navigator.share) {
                                            navigator.share({ title: `Perizia ${periziaInfo.number}`, text });
                                        } else {
                                            navigator.clipboard.writeText(text);
                                            toast.success('Link copiato negli appunti');
                                        }
                                    }}
                                    variant="outline"
                                    className="w-full h-14 text-base border-emerald-400 text-emerald-700 hover:bg-emerald-50 rounded-xl"
                                >
                                    <Send className="h-5 w-5 mr-2" /> Invia via WhatsApp / Email
                                </Button>
                            )}
                        </div>
                    </div>
                )}

                {/* Navigation Buttons */}
                {step < 4 && (
                    <div className="flex gap-3 pt-2">
                        {step > 0 && (
                            <Button variant="outline" onClick={() => setStep(s => s - 1)} className="flex-1 h-12 rounded-xl text-sm">
                                <ArrowLeft className="h-4 w-4 mr-2" /> Indietro
                            </Button>
                        )}
                        <Button
                            data-testid="btn-next-step"
                            onClick={goNext}
                            disabled={!canNext()}
                            className={`flex-1 h-12 rounded-xl text-sm ${canNext() ? 'bg-[#0055FF] text-white hover:bg-[#0044CC]' : 'bg-slate-200 text-slate-400'}`}
                        >
                            {step === 3 ? (isNew ? 'Crea e Calcola' : 'Calcola Costi') : 'Avanti'}
                            <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
