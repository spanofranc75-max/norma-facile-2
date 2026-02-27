/**
 * Perizia Sinistro — Editor Page
 * Full editor: map picker, multi-image upload, damage selector, AI analysis, cost table.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    Save, ArrowLeft, FileDown, Plus, Trash2, Camera, Brain, RefreshCw,
    MapPin, ShieldAlert, Wrench, Zap, PaintBucket, X, FileText,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix leaflet default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const TIPO_DANNO_OPTIONS = [
    { value: 'strutturale', label: 'Danno Strutturale (EN 1090)', icon: ShieldAlert, color: 'text-red-600 border-red-200 bg-red-50', desc: 'Sostituzione modulo obbligatoria' },
    { value: 'estetico', label: 'Danno Estetico', icon: PaintBucket, color: 'text-amber-600 border-amber-200 bg-amber-50', desc: 'Carteggiatura e verniciatura' },
    { value: 'automatismi', label: 'Danno Automatismi (EN 12453)', icon: Zap, color: 'text-purple-600 border-purple-200 bg-purple-50', desc: 'Verifiche impianto motorizzato' },
];

const CODICE_COLORS = {
    red: 'border-red-300 bg-red-50 text-red-800 hover:bg-red-100',
    orange: 'border-orange-300 bg-orange-50 text-orange-800 hover:bg-orange-100',
    blue: 'border-blue-300 bg-blue-50 text-blue-800 hover:bg-blue-100',
    yellow: 'border-yellow-300 bg-yellow-50 text-yellow-800 hover:bg-yellow-100',
    purple: 'border-purple-300 bg-purple-50 text-purple-800 hover:bg-purple-100',
};

const CODICE_SELECTED = {
    red: 'border-red-500 bg-red-100 text-red-900 ring-2 ring-red-300',
    orange: 'border-orange-500 bg-orange-100 text-orange-900 ring-2 ring-orange-300',
    blue: 'border-blue-500 bg-blue-100 text-blue-900 ring-2 ring-blue-300',
    yellow: 'border-yellow-500 bg-yellow-100 text-yellow-900 ring-2 ring-yellow-300',
    purple: 'border-purple-500 bg-purple-100 text-purple-900 ring-2 ring-purple-300',
};

const API = process.env.REACT_APP_BACKEND_URL;

function LocationPicker({ position, onSelect }) {
    useMapEvents({
        click(e) { onSelect(e.latlng); },
    });
    return position ? <Marker position={position} /> : null;
}

export default function PeriziaEditorPage() {
    const { periziaId } = useParams();
    const navigate = useNavigate();
    const isNew = !periziaId;
    const fileInputRef = useRef(null);

    // Core state
    const [saving, setSaving] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [recalcing, setRecalcing] = useState(false);
    const [generatingLetter, setGeneratingLetter] = useState(false);
    const [periziaInfo, setPInfo] = useState({ number: null, status: 'bozza', perizia_id: null });

    // Form state
    const [clientId, setClientId] = useState('');
    const [clientSearch, setClientSearch] = useState('');
    const [clients, setClients] = useState([]);
    const [tipoDanno, setTipoDanno] = useState('strutturale');
    const [codiciDanno, setCodiciDanno] = useState([]);
    const [codiciDannoDb, setCodiciDannoDb] = useState([]);
    const [descrizione, setDescrizione] = useState('');
    const [prezzoMl, setPrezzoMl] = useState(0);
    const [coeffMagg, setCoeffMagg] = useState(20);
    const [moduli, setModuli] = useState([{ descrizione: 'Modulo 1', lunghezza_ml: 0, altezza_m: 0, note: '' }]);
    const [photos, setPhotos] = useState([]); // base64 strings
    const [aiAnalysis, setAiAnalysis] = useState('');
    const [statoDiFatto, setStatoDiFatto] = useState('');
    const [notaTecnica, setNotaTecnica] = useState('');
    const [vociCosto, setVociCosto] = useState([]);
    const [notes, setNotes] = useState('');
    const [letteraAccompagnamento, setLetteraAccompagnamento] = useState('');

    // Map state
    const [mapPos, setMapPos] = useState(null); // {lat, lng}
    const [indirizzo, setIndirizzo] = useState('');
    const [comune, setComune] = useState('');
    const [provincia, setProvincia] = useState('');
    const [mapCenter, setMapCenter] = useState([41.9028, 12.4964]); // Rome default

    // Fetch clients + codici danno
    useEffect(() => {
        apiRequest('/clients/?limit=200').then(d => setClients(d.clients || [])).catch(() => {});
        apiRequest('/perizie/codici-danno').then(d => setCodiciDannoDb(d.codici_danno || [])).catch(() => {});
    }, []);

    // Load existing perizia
    const loadPerizia = useCallback(async () => {
        if (isNew) return;
        try {
            const data = await apiRequest(`/perizie/${periziaId}`);
            setPInfo({ number: data.number, status: data.status, perizia_id: data.perizia_id });
            setClientId(data.client_id || '');
            setTipoDanno(data.tipo_danno || 'strutturale');
            setCodiciDanno(data.codici_danno || []);
            setDescrizione(data.descrizione_utente || '');
            setPrezzoMl(data.prezzo_ml_originale || 0);
            setCoeffMagg(data.coefficiente_maggiorazione ?? 20);
            setModuli(data.moduli?.length ? data.moduli : [{ descrizione: 'Modulo 1', lunghezza_ml: 0, altezza_m: 0, note: '' }]);
            setPhotos(data.foto || []);
            setAiAnalysis(data.ai_analysis || '');
            setStatoDiFatto(data.stato_di_fatto || '');
            setNotaTecnica(data.nota_tecnica || '');
            setVociCosto(data.voci_costo || []);
            setNotes(data.notes || '');
            setLetteraAccompagnamento(data.lettera_accompagnamento || '');

            const loc = data.localizzazione || {};
            if (loc.lat && loc.lng) {
                setMapPos({ lat: loc.lat, lng: loc.lng });
                setMapCenter([loc.lat, loc.lng]);
            }
            setIndirizzo(loc.indirizzo || '');
            setComune(loc.comune || '');
            setProvincia(loc.provincia || '');
        } catch (e) { toast.error('Errore caricamento perizia'); navigate('/perizie'); }
    }, [isNew, periziaId, navigate]);

    useEffect(() => { loadPerizia(); }, [loadPerizia]);

    // Map click → reverse geocode
    const handleMapClick = async (latlng) => {
        setMapPos(latlng);
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latlng.lat}&lon=${latlng.lng}&format=json&accept-language=it`);
            const data = await res.json();
            if (data.address) {
                const a = data.address;
                const road = a.road || a.pedestrian || a.footway || '';
                const number = a.house_number || '';
                setIndirizzo(`${road} ${number}`.trim() || data.display_name?.split(',')[0] || '');
                setComune(a.city || a.town || a.village || a.municipality || '');
                setProvincia(a.county || a.state || '');
            }
        } catch { /* ignore geocoding error */ }
    };

    // Address search
    const handleAddressSearch = async () => {
        if (!indirizzo) return;
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(indirizzo + ' ' + comune)}&format=json&limit=1&accept-language=it`);
            const data = await res.json();
            if (data.length > 0) {
                const pos = { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
                setMapPos(pos);
                setMapCenter([pos.lat, pos.lng]);
            } else {
                toast.error('Indirizzo non trovato');
            }
        } catch { toast.error('Errore ricerca indirizzo'); }
    };

    // Photo upload
    const handlePhotoUpload = (e) => {
        const files = Array.from(e.target.files);
        if (photos.length + files.length > 5) {
            toast.error('Massimo 5 foto');
            return;
        }
        files.forEach(file => {
            const reader = new FileReader();
            reader.onload = () => {
                setPhotos(prev => [...prev, reader.result]);
            };
            reader.readAsDataURL(file);
        });
        e.target.value = '';
    };

    const removePhoto = (idx) => setPhotos(prev => prev.filter((_, i) => i !== idx));

    // Module management
    const addModule = () => setModuli(prev => [...prev, { descrizione: `Modulo ${prev.length + 1}`, lunghezza_ml: 0, altezza_m: 0, note: '' }]);
    const removeModule = (idx) => setModuli(prev => prev.filter((_, i) => i !== idx));
    const updateModule = (idx, field, val) => setModuli(prev => prev.map((m, i) => i === idx ? { ...m, [field]: val } : m));

    // Cost item management
    const updateVoce = (idx, field, val) => {
        setVociCosto(prev => prev.map((v, i) => {
            if (i !== idx) return v;
            const updated = { ...v, [field]: val };
            if (field === 'quantita' || field === 'prezzo_unitario') {
                updated.totale = parseFloat(updated.quantita || 0) * parseFloat(updated.prezzo_unitario || 0);
                updated.totale = Math.round(updated.totale * 100) / 100;
            }
            return updated;
        }));
    };
    const addVoce = () => setVociCosto(prev => [...prev, { codice: '', descrizione: '', unita: 'corpo', quantita: 1, prezzo_unitario: 0, totale: 0 }]);
    const removeVoce = (idx) => setVociCosto(prev => prev.filter((_, i) => i !== idx));

    const totalePerizia = vociCosto.reduce((s, v) => s + (parseFloat(v.totale) || 0), 0);

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
            foto: photos,
            ai_analysis: aiAnalysis,
            stato_di_fatto: statoDiFatto,
            nota_tecnica: notaTecnica,
            voci_costo: vociCosto,
            lettera_accompagnamento: letteraAccompagnamento,
            notes,
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

    // AI Analysis
    const handleAnalyze = async () => {
        if (isNew) { toast.error('Salva prima la perizia'); return; }
        if (photos.length === 0) { toast.error('Carica almeno una foto'); return; }
        setAnalyzing(true);
        try {
            // Save photos first
            await apiRequest(`/perizie/${periziaId}`, {
                method: 'PUT',
                body: { foto: photos, descrizione_utente: descrizione, tipo_danno: tipoDanno },
            });
            const res = await apiRequest(`/perizie/${periziaId}/analyze-photos`, { method: 'POST' });
            setAiAnalysis(res.ai_analysis || '');
            setStatoDiFatto(res.stato_di_fatto || '');
            setNotaTecnica(res.nota_tecnica || '');
            toast.success('Analisi AI completata');
        } catch (e) { toast.error(e.message); }
        finally { setAnalyzing(false); }
    };

    // Recalculate costs
    const handleRecalc = async () => {
        if (isNew) { toast.error('Salva prima la perizia'); return; }
        setRecalcing(true);
        try {
            // Save current data first
            await apiRequest(`/perizie/${periziaId}`, {
                method: 'PUT',
                body: {
                    tipo_danno: tipoDanno,
                    prezzo_ml_originale: parseFloat(prezzoMl) || 0,
                    coefficiente_maggiorazione: parseFloat(coeffMagg) || 20,
                    moduli,
                    codici_danno: codiciDanno,
                },
            });
            const res = await apiRequest(`/perizie/${periziaId}/recalc`, { method: 'POST' });
            setVociCosto(res.voci_costo || []);
            toast.success(`Costi ricalcolati: ${res.total_perizia?.toFixed(2)} EUR`);
        } catch (e) { toast.error(e.message); }
        finally { setRecalcing(false); }
    };

    // Generate cover letter
    const handleGeneraLettera = async () => {
        if (isNew) { toast.error('Salva prima la perizia'); return; }
        setGeneratingLetter(true);
        try {
            // Save current data first
            await apiRequest(`/perizie/${periziaId}`, {
                method: 'PUT',
                body: {
                    stato_di_fatto: statoDiFatto,
                    nota_tecnica: notaTecnica,
                    descrizione_utente: descrizione,
                    tipo_danno: tipoDanno,
                },
            });
            const res = await apiRequest(`/perizie/${periziaId}/genera-lettera`, { method: 'POST' });
            setLetteraAccompagnamento(res.lettera_accompagnamento || '');
            toast.success('Lettera di accompagnamento generata');
        } catch (e) { toast.error(e.message); }
        finally { setGeneratingLetter(false); }
    };

    return (
        <DashboardLayout>
            <div className="space-y-4" data-testid="perizia-editor-page">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => navigate('/perizie')} className="text-slate-500"><ArrowLeft className="h-4 w-4" /></Button>
                        <div>
                            <h1 className="text-xl font-bold text-[#1E293B] flex items-center gap-2">
                                <ShieldAlert className="h-5 w-5 text-[#0055FF]" />
                                {isNew ? 'Nuova Perizia Sinistro' : `Perizia ${periziaInfo.number || ''}`}
                            </h1>
                            {!isNew && <Badge className="bg-slate-100 text-slate-600 text-[10px] mt-1">{periziaInfo.status?.toUpperCase()}</Badge>}
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {!isNew && (
                            <Button data-testid="btn-pdf" variant="outline" onClick={() => window.open(`${API}/api/perizie/${periziaId}/pdf`, '_blank')} className="h-9 text-xs border-[#0055FF] text-[#0055FF]">
                                <FileDown className="h-3.5 w-3.5 mr-1.5" /> PDF Perizia
                            </Button>
                        )}
                        <Button data-testid="btn-save" onClick={handleSave} disabled={saving} className="h-9 text-xs bg-[#0055FF] text-white hover:bg-[#0044CC]">
                            <Save className="h-3.5 w-3.5 mr-1.5" /> {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </div>
                </div>

                {/* Main Grid: 2-col layout */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Left Column (2/3) */}
                    <div className="lg:col-span-2 space-y-4">
                        {/* Tipo Danno Selector */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">Tipo di Danno</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-3">
                                    {TIPO_DANNO_OPTIONS.map(opt => {
                                        const Icon = opt.icon;
                                        const sel = tipoDanno === opt.value;
                                        return (
                                            <button
                                                key={opt.value}
                                                data-testid={`tipo-${opt.value}`}
                                                onClick={() => setTipoDanno(opt.value)}
                                                className={`p-3 rounded-lg border-2 transition-all text-left ${
                                                    sel ? `${opt.color} border-current ring-2 ring-current/20` : 'border-slate-200 hover:border-slate-300 bg-white'
                                                }`}
                                            >
                                                <Icon className={`h-5 w-5 mb-1 ${sel ? '' : 'text-slate-400'}`} />
                                                <div className="text-xs font-semibold">{opt.label}</div>
                                                <div className="text-[10px] opacity-70 mt-0.5">{opt.desc}</div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Map + Location */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <ShieldAlert className="h-4 w-4 text-red-500" /> Codici Danno Rilevati
                                </CardTitle>
                                <p className="text-[11px] text-slate-500">Seleziona i codici danno dal sopralluogo. Ogni tag genera automaticamente le voci di costo e le norme citate.</p>
                            </CardHeader>
                            <CardContent>
                                {(() => {
                                    const grouped = {};
                                    codiciDannoDb.forEach(c => {
                                        if (!grouped[c.categoria]) grouped[c.categoria] = [];
                                        grouped[c.categoria].push(c);
                                    });
                                    return Object.entries(grouped).map(([cat, codes]) => (
                                        <div key={cat} className="mb-3">
                                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">{cat}</p>
                                            <div className="flex flex-wrap gap-2">
                                                {codes.map(cd => {
                                                    const sel = codiciDanno.includes(cd.codice);
                                                    const cls = sel ? CODICE_SELECTED[cd.color] || CODICE_SELECTED.blue : CODICE_COLORS[cd.color] || CODICE_COLORS.blue;
                                                    return (
                                                        <button
                                                            key={cd.codice}
                                                            data-testid={`tag-${cd.codice}`}
                                                            onClick={() => setCodiciDanno(prev => sel ? prev.filter(c => c !== cd.codice) : [...prev, cd.codice])}
                                                            className={`px-3 py-1.5 rounded-full border text-xs font-medium transition-all cursor-pointer ${cls}`}
                                                        >
                                                            <span className="font-mono font-bold mr-1">{cd.codice}</span>
                                                            {cd.label}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    ));
                                })()}
                                {codiciDanno.length > 0 && (
                                    <div className="mt-3 p-2 bg-slate-50 rounded-lg">
                                        <p className="text-[10px] font-bold text-slate-600 mb-1">Norme attivate:</p>
                                        <div className="flex flex-wrap gap-1">
                                            {[...new Set(codiciDanno.map(c => codiciDannoDb.find(cd => cd.codice === c)?.norma).filter(Boolean))].map(n => (
                                                <Badge key={n} className="bg-[#0055FF]/10 text-[#0055FF] text-[10px]">{n}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Map + Location (original) */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <MapPin className="h-4 w-4 text-[#0055FF]" /> Localizzazione Sinistro
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="flex gap-2">
                                    <Input data-testid="input-indirizzo" value={indirizzo} onChange={e => setIndirizzo(e.target.value)} placeholder="Via / Piazza..." className="flex-1" />
                                    <Input value={comune} onChange={e => setComune(e.target.value)} placeholder="Comune" className="w-40" />
                                    <Input value={provincia} onChange={e => setProvincia(e.target.value)} placeholder="Prov." className="w-20" />
                                    <Button data-testid="btn-search-address" variant="outline" size="sm" onClick={handleAddressSearch} className="h-10">
                                        <MapPin className="h-4 w-4" />
                                    </Button>
                                </div>
                                <div className="rounded-lg overflow-hidden border border-slate-200" style={{ height: 280 }} data-testid="map-container">
                                    <MapContainer
                                        center={mapCenter}
                                        zoom={13}
                                        style={{ height: '100%', width: '100%' }}
                                        key={`${mapCenter[0]}-${mapCenter[1]}`}
                                    >
                                        <TileLayer
                                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                        />
                                        <LocationPicker position={mapPos} onSelect={handleMapClick} />
                                    </MapContainer>
                                </div>
                                {mapPos && (
                                    <p className="text-xs text-slate-400">Coordinate: {mapPos.lat.toFixed(6)}, {mapPos.lng.toFixed(6)}</p>
                                )}
                            </CardContent>
                        </Card>

                        {/* Photos */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <Camera className="h-4 w-4 text-[#0055FF]" /> Foto del Danno ({photos.length}/5)
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={handlePhotoUpload} />
                                <div className="grid grid-cols-5 gap-3">
                                    {photos.map((p, i) => (
                                        <div key={i} className="relative group">
                                            <img src={p} alt={`Foto ${i + 1}`} className="w-full h-24 object-cover rounded-lg border border-slate-200" />
                                            <button
                                                onClick={() => removePhoto(i)}
                                                className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                <X className="h-3 w-3" />
                                            </button>
                                        </div>
                                    ))}
                                    {photos.length < 5 && (
                                        <button
                                            data-testid="btn-upload-photo"
                                            onClick={() => fileInputRef.current?.click()}
                                            className="h-24 border-2 border-dashed border-slate-300 rounded-lg flex flex-col items-center justify-center text-slate-400 hover:border-[#0055FF] hover:text-[#0055FF] transition-colors"
                                        >
                                            <Camera className="h-5 w-5" />
                                            <span className="text-[10px] mt-1">Aggiungi</span>
                                        </button>
                                    )}
                                </div>
                                {photos.length > 0 && (
                                    <Button
                                        data-testid="btn-ai-analyze"
                                        onClick={handleAnalyze}
                                        disabled={analyzing}
                                        className="mt-3 w-full bg-gradient-to-r from-indigo-600 to-blue-600 text-white hover:from-indigo-700 hover:to-blue-700"
                                    >
                                        <Brain className="h-4 w-4 mr-2" />
                                        {analyzing ? 'Analisi AI in corso...' : 'Analizza Foto con AI (GPT-4o Vision)'}
                                    </Button>
                                )}
                            </CardContent>
                        </Card>

                        {/* AI Analysis Result */}
                        {aiAnalysis && (
                            <Card className="border-indigo-200 bg-indigo-50/30">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm font-semibold text-indigo-700 flex items-center gap-2">
                                        <Brain className="h-4 w-4" /> Analisi AI del Danno
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">{aiAnalysis}</pre>
                                </CardContent>
                            </Card>
                        )}

                        {/* Stato di Fatto (editable) */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">1. Descrizione Stato di Fatto</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Textarea
                                    data-testid="input-stato-fatto"
                                    value={statoDiFatto}
                                    onChange={e => setStatoDiFatto(e.target.value)}
                                    placeholder="Descrizione tecnica dello stato dei danni (generata automaticamente dall'AI o compilata manualmente)..."
                                    rows={6}
                                    className="text-sm"
                                />
                            </CardContent>
                        </Card>

                        {/* Cost Table */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-sm font-semibold text-[#1E293B]">2. Computo Metrico Estimativo</CardTitle>
                                    <div className="flex gap-2">
                                        <Button data-testid="btn-recalc" variant="outline" size="sm" onClick={handleRecalc} disabled={recalcing} className="h-7 text-xs">
                                            <RefreshCw className={`h-3 w-3 mr-1 ${recalcing ? 'animate-spin' : ''}`} /> Ricalcola
                                        </Button>
                                        <Button variant="outline" size="sm" onClick={addVoce} className="h-7 text-xs">
                                            <Plus className="h-3 w-3 mr-1" /> Voce
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="bg-[#1E293B] text-white text-xs">
                                                <th className="px-2 py-2 text-left w-16">Cod.</th>
                                                <th className="px-2 py-2 text-left">Descrizione</th>
                                                <th className="px-2 py-2 text-center w-16">U.M.</th>
                                                <th className="px-2 py-2 text-right w-16">Q.ta</th>
                                                <th className="px-2 py-2 text-right w-24">Prezzo</th>
                                                <th className="px-2 py-2 text-right w-24">Totale</th>
                                                <th className="w-10"></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {vociCosto.map((v, i) => (
                                                <tr key={i} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`voce-row-${i}`}>
                                                    <td className="px-2 py-1">
                                                        <Input value={v.codice} onChange={e => updateVoce(i, 'codice', e.target.value)} className="h-7 text-xs px-1" />
                                                    </td>
                                                    <td className="px-2 py-1">
                                                        <Textarea value={v.descrizione} onChange={e => updateVoce(i, 'descrizione', e.target.value)} className="min-h-[28px] text-xs resize-none" rows={1} />
                                                    </td>
                                                    <td className="px-2 py-1">
                                                        <Select value={v.unita} onValueChange={val => updateVoce(i, 'unita', val)}>
                                                            <SelectTrigger className="h-7 text-xs"><SelectValue /></SelectTrigger>
                                                            <SelectContent>
                                                                {['corpo', 'ore', 'ml', 'mq', 'kg', 'nr'].map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                                                            </SelectContent>
                                                        </Select>
                                                    </td>
                                                    <td className="px-2 py-1">
                                                        <Input type="number" step="0.1" value={v.quantita} onChange={e => updateVoce(i, 'quantita', parseFloat(e.target.value) || 0)} className="h-7 text-xs text-right px-1" />
                                                    </td>
                                                    <td className="px-2 py-1">
                                                        <Input type="number" step="0.01" value={v.prezzo_unitario} onChange={e => updateVoce(i, 'prezzo_unitario', parseFloat(e.target.value) || 0)} className="h-7 text-xs text-right px-1" />
                                                    </td>
                                                    <td className="px-2 py-1 text-right font-mono font-medium text-xs">{(parseFloat(v.totale) || 0).toFixed(2)}</td>
                                                    <td className="px-1">
                                                        <Button variant="ghost" size="sm" onClick={() => removeVoce(i)} className="h-7 w-7 p-0 text-red-400 hover:text-red-600">
                                                            <Trash2 className="h-3 w-3" />
                                                        </Button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                {/* Total */}
                                <div className="flex justify-end p-3 bg-slate-50 border-t">
                                    <div className="text-right">
                                        <span className="text-sm text-slate-500 mr-4">TOTALE PERIZIA:</span>
                                        <span className="text-lg font-bold text-[#0055FF] font-mono" data-testid="total-perizia">
                                            {totalePerizia.toLocaleString('it-IT', { minimumFractionDigits: 2 })} EUR
                                        </span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Nota Tecnica */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">3. Nota Tecnica per il Perito</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Textarea
                                    data-testid="input-nota-tecnica"
                                    value={notaTecnica}
                                    onChange={e => setNotaTecnica(e.target.value)}
                                    placeholder="Motivazione normativa per la sostituzione (EN 1090, EN 13241). Generata dall'AI o compilata manualmente..."
                                    rows={5}
                                    className="text-sm"
                                />
                            </CardContent>
                        </Card>

                        {/* Lettera di Accompagnamento Tecnica */}
                        <Card className="border-gray-200 border-l-4 border-l-amber-500">
                            <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                        <FileText className="h-4 w-4 text-amber-600" /> 4. Lettera di Accompagnamento Tecnica
                                    </CardTitle>
                                    {!isNew && (
                                        <Button
                                            data-testid="btn-genera-lettera"
                                            onClick={handleGeneraLettera}
                                            disabled={generatingLetter}
                                            className="h-8 text-xs bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600"
                                        >
                                            <FileText className="h-3.5 w-3.5 mr-1.5" />
                                            {generatingLetter ? 'Generazione AI...' : 'Genera Diffida Tecnica per Perito'}
                                        </Button>
                                    )}
                                </div>
                                <p className="text-[11px] text-slate-500 mt-1">
                                    Lettera formale per l'ufficio sinistri che sposta il focus dal prezzo alla responsabilita normativa (EN 1090, EN 13241, ISO 12944)
                                </p>
                            </CardHeader>
                            <CardContent>
                                <Textarea
                                    data-testid="input-lettera"
                                    value={letteraAccompagnamento}
                                    onChange={e => setLetteraAccompagnamento(e.target.value)}
                                    placeholder="Clicca 'Genera Diffida Tecnica per Perito' per generare automaticamente la lettera con i dati della perizia, oppure scrivi manualmente..."
                                    rows={letteraAccompagnamento ? 18 : 4}
                                    className="text-sm font-serif leading-relaxed"
                                />
                                {letteraAccompagnamento && (
                                    <p className="text-[10px] text-amber-600 mt-2 flex items-center gap-1">
                                        <ShieldAlert className="h-3 w-3" />
                                        La lettera sara inclusa nel PDF della perizia. Modifica liberamente prima di esportare.
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right Column (1/3) — Sidebar */}
                    <div className="space-y-4">
                        {/* Client */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">Cliente / Assicurato</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                <Input
                                    data-testid="input-client-search"
                                    placeholder="Cerca cliente..."
                                    value={clientSearch}
                                    onChange={e => setClientSearch(e.target.value)}
                                    className="h-8 text-xs"
                                />
                                <Select value={clientId || '__none__'} onValueChange={v => setClientId(v === '__none__' ? '' : v)}>
                                    <SelectTrigger data-testid="select-client" className="h-9 text-xs"><SelectValue placeholder="Seleziona cliente..." /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="__none__">-- Nessun cliente --</SelectItem>
                                        {clients.filter(c => !clientSearch || c.business_name?.toLowerCase().includes(clientSearch.toLowerCase())).map(c => (
                                            <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </CardContent>
                        </Card>

                        {/* Descrizione */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">Descrizione Sinistro</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Textarea
                                    data-testid="input-descrizione"
                                    value={descrizione}
                                    onChange={e => setDescrizione(e.target.value)}
                                    placeholder="Urto da veicolo su recinzione in acciaio zincato..."
                                    rows={4}
                                    className="text-xs"
                                />
                            </CardContent>
                        </Card>

                        {/* Pricing */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                                    <Wrench className="h-4 w-4 text-[#0055FF]" /> Prezzi di Riferimento
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div>
                                    <Label className="text-xs">Prezzo Originale (EUR/ml)</Label>
                                    <Input data-testid="input-prezzo-ml" type="number" step="0.01" value={prezzoMl} onChange={e => setPrezzoMl(e.target.value)} className="h-8 text-xs font-mono" />
                                </div>
                                <div>
                                    <Label className="text-xs">Maggiorazione Fuori Serie (%)</Label>
                                    <Input data-testid="input-coeff" type="number" step="1" value={coeffMagg} onChange={e => setCoeffMagg(e.target.value)} className="h-8 text-xs font-mono" />
                                </div>
                                <Separator />
                                <div className="text-xs text-slate-500">
                                    Prezzo maggiorato: <strong className="text-[#1E293B] font-mono">{(prezzoMl * (1 + coeffMagg / 100)).toFixed(2)} EUR/ml</strong>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Modules */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-sm font-semibold text-[#1E293B]">Moduli Danneggiati</CardTitle>
                                    <Button data-testid="btn-add-module" variant="outline" size="sm" onClick={addModule} className="h-7 text-xs">
                                        <Plus className="h-3 w-3 mr-1" /> Modulo
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {moduli.map((m, i) => (
                                    <div key={i} className="p-2 border rounded-lg bg-slate-50 space-y-2" data-testid={`module-${i}`}>
                                        <div className="flex items-center justify-between">
                                            <Input value={m.descrizione} onChange={e => updateModule(i, 'descrizione', e.target.value)} className="h-7 text-xs font-medium flex-1 mr-2" />
                                            {moduli.length > 1 && (
                                                <Button variant="ghost" size="sm" onClick={() => removeModule(i)} className="h-6 w-6 p-0 text-red-400">
                                                    <X className="h-3 w-3" />
                                                </Button>
                                            )}
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div>
                                                <Label className="text-[10px] text-slate-500">Lunghezza (ml)</Label>
                                                <Input type="number" step="0.1" value={m.lunghezza_ml} onChange={e => updateModule(i, 'lunghezza_ml', parseFloat(e.target.value) || 0)} className="h-7 text-xs font-mono" />
                                            </div>
                                            <div>
                                                <Label className="text-[10px] text-slate-500">Altezza (m)</Label>
                                                <Input type="number" step="0.1" value={m.altezza_m} onChange={e => updateModule(i, 'altezza_m', parseFloat(e.target.value) || 0)} className="h-7 text-xs font-mono" />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                <Separator />
                                <div className="text-xs text-slate-500">
                                    Totale ML: <strong className="text-[#1E293B] font-mono">{moduli.reduce((s, m) => s + (parseFloat(m.lunghezza_ml) || 0), 0).toFixed(2)} ml</strong>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Notes */}
                        <Card className="border-gray-200">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-semibold text-[#1E293B]">Note Aggiuntive</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Textarea
                                    data-testid="input-notes"
                                    value={notes}
                                    onChange={e => setNotes(e.target.value)}
                                    placeholder="Note per la perizia..."
                                    rows={3}
                                    className="text-xs"
                                />
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
