/**
 * Validazione Foto Posa — AI validation of installation photos (GPT-4o Vision).
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { apiRequest } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
    Camera, Upload, Trash2, CheckCircle, XCircle, AlertTriangle,
    Loader2, FileCheck, Shield, Eye,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const PRODUCT_TYPES = [
    { value: 'finestra', label: 'Finestra' },
    { value: 'portafinestra', label: 'Porta-finestra' },
    { value: 'cancello', label: 'Cancello' },
    { value: 'portone', label: 'Portone industriale' },
    { value: 'recinzione', label: 'Recinzione' },
    { value: 'ringhiera', label: 'Ringhiera / Parapetto' },
    { value: 'tettoia', label: 'Tettoia / Pensilina' },
    { value: 'scala', label: 'Scala metallica' },
    { value: 'altro', label: 'Altro' },
];

const ESITO_CONFIG = {
    'CONFORME': { icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200', badge: 'bg-emerald-100 text-emerald-800' },
    'NON CONFORME': { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50 border-red-200', badge: 'bg-red-100 text-red-800' },
    'NON VERIFICABILE': { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200', badge: 'bg-amber-100 text-amber-800' },
};

export default function ValidazioneFotoPage() {
    const fileInputRef = useRef(null);
    const [norme, setNorme] = useState([]);
    const [form, setForm] = useState({
        norma_id: '',
        product_type: 'finestra',
        description: '',
        zona_climatica: 'E',
        checklist: [],
    });
    const [photos, setPhotos] = useState([]); // { file, preview, base64 }
    const [newCheckItem, setNewCheckItem] = useState('');
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState(null);

    useEffect(() => {
        apiRequest('/engine/norme').then(d => setNorme(d.norme || [])).catch(() => {});
    }, []);

    const handlePhotoUpload = (e) => {
        const files = Array.from(e.target.files);
        if (photos.length + files.length > 5) {
            toast.error('Massimo 5 foto');
            return;
        }
        files.forEach(file => {
            const reader = new FileReader();
            reader.onload = () => {
                setPhotos(prev => [...prev, {
                    file,
                    preview: URL.createObjectURL(file),
                    base64: reader.result,
                }]);
            };
            reader.readAsDataURL(file);
        });
        e.target.value = '';
    };

    const removePhoto = (idx) => {
        setPhotos(prev => prev.filter((_, i) => i !== idx));
    };

    const addCheckItem = () => {
        if (!newCheckItem.trim()) return;
        setForm(f => ({ ...f, checklist: [...f.checklist, newCheckItem.trim()] }));
        setNewCheckItem('');
    };

    const removeCheckItem = (idx) => {
        setForm(f => ({ ...f, checklist: f.checklist.filter((_, i) => i !== idx) }));
    };

    const handleAnalyze = async () => {
        if (photos.length === 0) {
            toast.error('Caricare almeno una foto');
            return;
        }
        setAnalyzing(true);
        setResult(null);
        try {
            const payload = {
                norma_id: form.norma_id || null,
                product_type: form.product_type,
                description: form.description,
                photos_base64: photos.map(p => p.base64),
                checklist: form.checklist,
                zona_climatica: form.zona_climatica,
            };
            const data = await apiRequest('/engine/validate-installation-photos', {
                method: 'POST',
                body: payload,
            });
            setResult(data);
            toast.success('Analisi completata');
        } catch (e) {
            toast.error(e.message || 'Errore analisi');
        } finally {
            setAnalyzing(false);
        }
    };

    const globalEsito = result?.esito_globale || '';
    const esitoConf = ESITO_CONFIG[globalEsito] || ESITO_CONFIG['NON VERIFICABILE'];
    const EsitoIcon = esitoConf.icon;

    return (
        <DashboardLayout>
            <div className="space-y-4 max-w-5xl" data-testid="validazione-foto-page">
                {/* Header */}
                <div>
                    <h1 className="font-sans text-2xl font-bold text-[#1E293B] flex items-center gap-2">
                        <Camera className="h-6 w-6 text-[#0055FF]" /> Validazione Foto Posa
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Carica le foto dell'installazione completata. L'AI analizzerà la conformità rispetto ai requisiti normativi.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
                    {/* Left Panel — Configuration */}
                    <div className="space-y-3">
                        <Card className="border-gray-200">
                            <CardHeader className="py-3 px-4 bg-slate-50 border-b">
                                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                    <Shield className="h-4 w-4 text-[#0055FF]" /> Configurazione
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 space-y-3">
                                <div>
                                    <Label className="text-xs">Tipo Prodotto</Label>
                                    <Select value={form.product_type} onValueChange={v => setForm(f => ({ ...f, product_type: v }))}>
                                        <SelectTrigger data-testid="select-product-type" className="h-9"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {PRODUCT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Norma di Riferimento</Label>
                                    <Select value={form.norma_id || '__none__'} onValueChange={v => setForm(f => ({ ...f, norma_id: v === '__none__' ? '' : v }))}>
                                        <SelectTrigger data-testid="select-norma" className="h-9"><SelectValue placeholder="Opzionale..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">-- Auto-detect --</SelectItem>
                                            {norme.map(n => <SelectItem key={n.norma_id} value={n.norma_id}>{n.standard_ref} - {n.title}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Zona Climatica</Label>
                                    <Select value={form.zona_climatica} onValueChange={v => setForm(f => ({ ...f, zona_climatica: v }))}>
                                        <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {['A','B','C','D','E','F'].map(z => <SelectItem key={z} value={z}>Zona {z}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Descrizione lavoro</Label>
                                    <Textarea
                                        data-testid="input-description"
                                        value={form.description}
                                        onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                        placeholder="es. Installazione finestra PVC zona bagno piano 1..."
                                        rows={3}
                                        className="text-sm"
                                    />
                                </div>
                            </CardContent>
                        </Card>

                        {/* Custom Checklist */}
                        <Card className="border-gray-200">
                            <CardHeader className="py-3 px-4 bg-slate-50 border-b">
                                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                    <FileCheck className="h-4 w-4 text-[#0055FF]" /> Checklist Personalizzata
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 space-y-2">
                                <p className="text-[10px] text-slate-400">Aggiungi punti di controllo specifici. Se vuoto, verranno usati quelli standard per il tipo prodotto.</p>
                                <div className="flex gap-1">
                                    <Input
                                        data-testid="input-checklist-item"
                                        value={newCheckItem}
                                        onChange={e => setNewCheckItem(e.target.value)}
                                        onKeyDown={e => e.key === 'Enter' && addCheckItem()}
                                        placeholder="es. 4 viti visibili alla cerniera"
                                        className="h-8 text-xs flex-1"
                                    />
                                    <Button size="sm" onClick={addCheckItem} className="h-8 text-xs bg-[#0055FF]">+</Button>
                                </div>
                                {form.checklist.length > 0 && (
                                    <ul className="space-y-1 mt-2">
                                        {form.checklist.map((item, i) => (
                                            <li key={i} className="flex items-center gap-2 text-xs bg-slate-50 px-2 py-1.5 rounded">
                                                <span className="text-[10px] font-mono text-slate-400">{i+1}.</span>
                                                <span className="flex-1">{item}</span>
                                                <button onClick={() => removeCheckItem(i)} className="text-slate-400 hover:text-red-500">
                                                    <Trash2 className="h-3 w-3" />
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right Panel — Photos & Results */}
                    <div className="space-y-4">
                        {/* Photo Upload */}
                        <Card className="border-gray-200">
                            <CardHeader className="py-3 px-4 bg-slate-50 border-b">
                                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                    <Camera className="h-4 w-4 text-[#0055FF]" /> Foto Installazione
                                    <Badge className="bg-slate-100 text-slate-600 text-[9px] ml-auto">{photos.length}/5</Badge>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4">
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    onChange={handlePhotoUpload}
                                    className="hidden"
                                />
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                                    {photos.map((p, i) => (
                                        <div key={i} className="relative group aspect-square rounded-lg overflow-hidden border border-slate-200" data-testid={`photo-${i}`}>
                                            <img src={p.preview} alt={`Foto ${i+1}`} className="w-full h-full object-cover" />
                                            <button
                                                onClick={() => removePhoto(i)}
                                                className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </button>
                                            <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[9px] px-2 py-0.5 text-center">
                                                Foto {i+1}
                                            </div>
                                        </div>
                                    ))}
                                    {photos.length < 5 && (
                                        <button
                                            data-testid="btn-upload-photo"
                                            onClick={() => fileInputRef.current?.click()}
                                            className="aspect-square rounded-lg border-2 border-dashed border-slate-300 hover:border-[#0055FF] hover:bg-blue-50 transition-colors flex flex-col items-center justify-center gap-1 text-slate-400 hover:text-[#0055FF]"
                                        >
                                            <Upload className="h-5 w-5" />
                                            <span className="text-[10px] font-medium">Aggiungi</span>
                                        </button>
                                    )}
                                </div>

                                <Separator className="my-4" />

                                <Button
                                    data-testid="btn-analyze"
                                    onClick={handleAnalyze}
                                    disabled={analyzing || photos.length === 0}
                                    className="w-full bg-[#0055FF] hover:bg-[#0044CC] text-white h-10"
                                >
                                    {analyzing ? (
                                        <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analisi AI in corso...</>
                                    ) : (
                                        <><Eye className="h-4 w-4 mr-2" /> Analizza con AI (GPT-4o Vision)</>
                                    )}
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Results */}
                        {result && (
                            <Card className={`border-2 ${esitoConf.bg}`} data-testid="validation-result">
                                <CardHeader className="py-3 px-4">
                                    <CardTitle className="flex items-center gap-2 text-lg">
                                        <EsitoIcon className={`h-6 w-6 ${esitoConf.color}`} />
                                        <span className={`font-bold ${esitoConf.color}`}>Esito: {globalEsito}</span>
                                        <div className="ml-auto flex gap-2 text-sm font-normal">
                                            <Badge className="bg-emerald-100 text-emerald-800">{result.summary?.conformi || 0} Conformi</Badge>
                                            <Badge className="bg-red-100 text-red-800">{result.summary?.non_conformi || 0} Non Conformi</Badge>
                                            <Badge className="bg-amber-100 text-amber-800">{result.summary?.non_verificabili || 0} N.V.</Badge>
                                        </div>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4 pb-4">
                                    {/* Checklist Results */}
                                    <div className="space-y-2">
                                        {(result.checklist_results || []).map((r, i) => {
                                            const rc = ESITO_CONFIG[r.esito] || ESITO_CONFIG['NON VERIFICABILE'];
                                            const RIcon = rc.icon;
                                            return (
                                                <div key={i} data-testid={`check-result-${i}`} className="flex items-start gap-3 p-2.5 bg-white rounded-lg border border-slate-100">
                                                    <RIcon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${rc.color}`} />
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-sm font-medium text-[#1E293B]">{r.item}</span>
                                                            <Badge className={`${rc.badge} text-[9px]`}>{r.esito}</Badge>
                                                        </div>
                                                        {r.note && <p className="text-xs text-slate-500 mt-0.5">{r.note}</p>}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {/* Additional Notes */}
                                    {result.notes && (
                                        <div className="mt-4 p-3 bg-white rounded-lg border border-slate-200">
                                            <p className="text-xs font-semibold text-slate-600 mb-1">Note aggiuntive del DL</p>
                                            <p className="text-sm text-slate-700">{result.notes}</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
