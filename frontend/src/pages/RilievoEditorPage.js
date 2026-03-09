/**
 * Rilievo Editor Page - Tablet-First Design with Sketch Pad
 * For on-site measurements and photo documentation.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../components/ui/dialog';
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from '../components/ui/tabs';
import { toast } from 'sonner';
import { Switch } from '../components/ui/switch';
import {
    Save,
    ArrowLeft,
    Plus,
    Camera,
    Ruler,
    Trash2,
    Download,
    Pencil,
    Image as ImageIcon,
    X,
    Undo,
    RotateCcw,
    Check,
    HardHat,
    Link,
    Building2,
    Grid3X3,
    DoorOpen,
    Footprints,
    TrendingUp,
    Fence,
    Grip,
    SlidersHorizontal,
    ChevronDown,
    ChevronUp,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import RilievoViewer3D from '../components/RilievoViewer3D';
import CanvasDraw from 'react-canvas-draw';

// Sketch Editor Component
function SketchEditor({ sketch, onSave, onCancel }) {
    const canvasRef = useRef(null);
    const fileInputRef = useRef(null);
    const [name, setName] = useState(sketch?.name || '');
    const [backgroundImage, setBackgroundImage] = useState(sketch?.background_image || null);
    const [brushColor, setBrushColor] = useState('#B45309'); // Amber
    const [brushRadius, setBrushRadius] = useState(3);
    const [dimensions, setDimensions] = useState(sketch?.dimensions || { width: '', height: '', depth: '' });

    const handleImageUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            setBackgroundImage(event.target.result);
        };
        reader.readAsDataURL(file);
    };

    const handleSave = () => {
        const drawingData = canvasRef.current?.getSaveData() || '';
        onSave({
            sketch_id: sketch?.sketch_id,
            name: name || 'Schizzo',
            background_image: backgroundImage,
            drawing_data: drawingData,
            dimensions,
        });
    };

    const handleClear = () => {
        canvasRef.current?.clear();
    };

    const handleUndo = () => {
        canvasRef.current?.undo();
    };

    return (
        <div className="space-y-4">
            {/* Sketch Name */}
            <div>
                <Label htmlFor="sketch-name">Nome Schizzo</Label>
                <Input
                    id="sketch-name"
                    data-testid="input-sketch-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Es: Porta ingresso, Finestra cucina..."
                    className="text-lg"
                />
            </div>

            {/* Background Image Upload */}
            <div className="flex items-center gap-4">
                <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    className="h-14 px-6 text-base"
                >
                    <ImageIcon className="h-5 w-5 mr-2" />
                    {backgroundImage ? 'Cambia Sfondo' : 'Carica Foto Sfondo'}
                </Button>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                />
                {backgroundImage && (
                    <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setBackgroundImage(null)}
                        className="text-red-600"
                    >
                        <X className="h-4 w-4 mr-1" />
                        Rimuovi
                    </Button>
                )}
            </div>

            {/* Canvas Drawing Area */}
            <div className="border-2 border-slate-300 rounded-lg overflow-hidden bg-white relative">
                {backgroundImage && (
                    <img
                        src={backgroundImage}
                        alt="Background"
                        className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                        style={{ zIndex: 0 }}
                    />
                )}
                <div style={{ position: 'relative', zIndex: 1 }}>
                    <CanvasDraw
                        ref={canvasRef}
                        brushColor={brushColor}
                        brushRadius={brushRadius}
                        lazyRadius={0}
                        canvasWidth={800}
                        canvasHeight={500}
                        backgroundColor="transparent"
                        hideGrid={true}
                        saveData={sketch?.drawing_data || ''}
                        immediateLoading={true}
                        style={{ touchAction: 'none' }}
                    />
                </div>
            </div>

            {/* Drawing Tools */}
            <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-2">
                    <Label className="text-sm">Colore:</Label>
                    <div className="flex gap-1">
                        {['#B45309', '#0F172A', '#DC2626', '#16A34A', '#2563EB'].map(color => (
                            <button
                                key={color}
                                type="button"
                                onClick={() => setBrushColor(color)}
                                className={`w-8 h-8 rounded-full border-2 transition-transform ${
                                    brushColor === color ? 'border-[#0055FF] scale-110' : 'border-transparent'
                                }`}
                                style={{ backgroundColor: color }}
                            />
                        ))}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Label className="text-sm">Spessore:</Label>
                    <div className="flex gap-1">
                        {[2, 4, 6, 8].map(size => (
                            <button
                                key={size}
                                type="button"
                                onClick={() => setBrushRadius(size)}
                                className={`w-8 h-8 rounded-lg border flex items-center justify-center transition-colors ${
                                    brushRadius === size ? 'bg-[#0055FF] text-white' : 'bg-white'
                                }`}
                            >
                                <div
                                    className="rounded-full bg-current"
                                    style={{ width: size * 2, height: size * 2 }}
                                />
                            </button>
                        ))}
                    </div>
                </div>
                <div className="flex gap-2 ml-auto">
                    <Button type="button" variant="outline" onClick={handleUndo} className="h-10">
                        <Undo className="h-4 w-4 mr-1" />
                        Annulla
                    </Button>
                    <Button type="button" variant="outline" onClick={handleClear} className="h-10">
                        <RotateCcw className="h-4 w-4 mr-1" />
                        Pulisci
                    </Button>
                </div>
            </div>

            {/* Dimensions Input */}
            <div className="grid grid-cols-3 gap-4">
                <div>
                    <Label htmlFor="dim-width">Larghezza (cm)</Label>
                    <Input
                        id="dim-width"
                        type="number"
                        value={dimensions.width}
                        onChange={(e) => setDimensions(d => ({ ...d, width: e.target.value }))}
                        placeholder="L"
                        className="text-lg h-12"
                    />
                </div>
                <div>
                    <Label htmlFor="dim-height">Altezza (cm)</Label>
                    <Input
                        id="dim-height"
                        type="number"
                        value={dimensions.height}
                        onChange={(e) => setDimensions(d => ({ ...d, height: e.target.value }))}
                        placeholder="H"
                        className="text-lg h-12"
                    />
                </div>
                <div>
                    <Label htmlFor="dim-depth">Profondità (cm)</Label>
                    <Input
                        id="dim-depth"
                        type="number"
                        value={dimensions.depth}
                        onChange={(e) => setDimensions(d => ({ ...d, depth: e.target.value }))}
                        placeholder="P"
                        className="text-lg h-12"
                    />
                </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4 pt-4">
                <Button type="button" variant="outline" onClick={onCancel} className="h-12 px-6">
                    Annulla
                </Button>
                <Button
                    type="button"
                    onClick={handleSave}
                    className="h-12 px-8 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                >
                    <Check className="h-4 w-4 mr-2" />
                    Salva Schizzo
                </Button>
            </div>
        </div>
    );
}

// ── Tipologia Selector ──
const TIPOLOGIE = [
    { id: 'inferriata_fissa', label: 'Inferriata Fissa', icon: Grid3X3, color: 'from-slate-600 to-slate-800', desc: 'Grate, protezioni finestre' },
    { id: 'cancello_carrabile', label: 'Cancello Carrabile', icon: DoorOpen, color: 'from-blue-600 to-blue-800', desc: 'Ingresso veicoli, scorrevole/battente' },
    { id: 'cancello_pedonale', label: 'Cancello Pedonale', icon: Footprints, color: 'from-emerald-600 to-emerald-800', desc: 'Ingresso pedonale, serratura' },
    { id: 'scala', label: 'Scala', icon: TrendingUp, color: 'from-amber-600 to-amber-800', desc: 'Scale interne/esterne, gradini' },
    { id: 'recinzione', label: 'Recinzione', icon: Fence, color: 'from-green-700 to-green-900', desc: 'Recinzioni perimetrali, campate' },
    { id: 'ringhiera', label: 'Ringhiera', icon: Grip, color: 'from-violet-600 to-violet-800', desc: 'Ringhiere balconi, terrazze' },
];

function TipologiaSelector({ value, onChange }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
                <SlidersHorizontal className="h-5 w-5 text-slate-500" />
                <span className="text-sm font-medium text-slate-600">Seleziona la tipologia del manufatto</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4" data-testid="tipologia-selector">
                {TIPOLOGIE.map(t => {
                    const Icon = t.icon;
                    const selected = value === t.id;
                    return (
                        <button
                            key={t.id}
                            type="button"
                            data-testid={`tipologia-${t.id}`}
                            onClick={() => onChange(t.id)}
                            className={`relative group rounded-xl p-5 text-left transition-all duration-200 border-2 min-h-[120px] ${
                                selected
                                    ? 'border-[#0055FF] bg-blue-50 shadow-md ring-2 ring-blue-200'
                                    : 'border-slate-200 bg-white hover:border-slate-400 hover:shadow-sm'
                            }`}
                        >
                            <div className={`inline-flex items-center justify-center w-12 h-12 rounded-lg bg-gradient-to-br ${t.color} mb-3`}>
                                <Icon className="h-6 w-6 text-white" />
                            </div>
                            <div className="font-semibold text-sm text-slate-900">{t.label}</div>
                            <div className="text-xs text-slate-500 mt-1 leading-relaxed">{t.desc}</div>
                            {selected && (
                                <div className="absolute top-3 right-3">
                                    <div className="w-6 h-6 rounded-full bg-[#0055FF] flex items-center justify-center">
                                        <Check className="h-4 w-4 text-white" />
                                    </div>
                                </div>
                            )}
                        </button>
                    );
                })}
            </div>
            {value && (
                <div className="flex items-center gap-2 pt-2">
                    <Badge variant="outline" className="text-sm border-blue-200 bg-blue-50 text-blue-700">
                        {TIPOLOGIE.find(t => t.id === value)?.label}
                    </Badge>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => onChange('')}
                        className="text-slate-400 hover:text-red-500 h-7 px-2"
                    >
                        <X className="h-3 w-3 mr-1" />
                        Rimuovi
                    </Button>
                </div>
            )}
        </div>
    );
}


// ── Profili standard ──
const PROFILI_MONTANTE = ['20x20','25x25','30x30','40x40','50x50','60x60'];
const PROFILI_TRAVERSO = ['20x20','25x25','30x20','30x30','40x20'];
const PROFILI_TELAIO = ['40x40','50x30','60x40','80x40'];
const PROFILI_INFISSO = ['20x20','25x25','30x20','40x20'];
const PROFILI_STRUTTURA = ['UPN80','UPN100','UPN120','HEA100','IPE100'];
const PROFILI_CORRIMANO = ['tondo_30','tondo_40','tondo_50','quadro_40x40'];
const FINITURE = ['verniciata','zincata','zincata_verniciata','corten','inox'];
const RAL_COMUNI = ['RAL 9005','RAL 9010','RAL 7016','RAL 7035','RAL 6005','RAL 3000','RAL 5010','RAL 8017'];
const APERTURE_CANCELLO = ['battente','scorrevole','libro','a_scomparsa'];
const TIPI_SCALA = ['dritta','a_L','a_U','a_chiocciola'];
const TIPI_STRUTTURA_SCALA = ['a_ginocchio','a_cosciale','a_sbalzo','autoportante'];
const TIPI_GRADINO = ['mandorlato','striato','grigliato','lamiera_piegata','legno'];
const TIPI_PANNELLO = ['piatto','dogato','lamiera','rete'];
const TIPI_ATTACCO = ['a_pavimento','laterale','a_muro'];

// ── Helper components ──
function NumField({ label, unit, value, onChange, min, max, step, hint, testId }) {
    const hasValue = value !== undefined && value !== '' && value !== null;
    const isValid = !hasValue || ((!min || Number(value) >= min) && (!max || Number(value) <= max));
    return (
        <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</label>
            <div className={`flex items-center rounded-lg border-2 overflow-hidden transition-colors ${!isValid ? 'border-red-400' : hasValue ? 'border-emerald-300 bg-emerald-50/30' : 'border-slate-200'}`}>
                <Input type="number" data-testid={testId} min={min || 0} step={step || 1}
                    value={value ?? ''} onChange={e => onChange(e.target.value === '' ? '' : Number(e.target.value))}
                    className="h-10 touch-manipulation border-0 shadow-none focus-visible:ring-0 bg-transparent" />
                {unit && <span className="px-3 text-xs font-medium text-slate-500 bg-slate-100 border-l border-slate-200 h-10 flex items-center whitespace-nowrap">{unit}</span>}
            </div>
            {hint && <p className="text-[11px] text-slate-400 mt-0.5">{hint}</p>}
        </div>
    );
}
function SelField({ label, value, onChange, options, testId }) {
    return (
        <div className="space-y-1">
            <Label className="text-xs text-slate-600">{label}</Label>
            <Select value={value || ''} onValueChange={onChange}>
                <SelectTrigger className="h-10 touch-manipulation" data-testid={testId}><SelectValue /></SelectTrigger>
                <SelectContent>
                    {options.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                </SelectContent>
            </Select>
        </div>
    );
}
function BoolField({ label, value, onChange, testId }) {
    return (
        <div className="flex items-center justify-between py-2">
            <Label className="text-sm text-slate-700">{label}</Label>
            <Switch checked={!!value} onCheckedChange={onChange} data-testid={testId} />
        </div>
    );
}

// ── Form Misure per tipologia ──
function riepilogoMisure(tip, m) {
    if (!tip || !m) return '';
    const fmt = (v, u) => v ? `${v}${u}` : '';
    if (tip === 'inferriata_fissa') return `Inferriata ${fmt(m.luce_larghezza,'x')}${fmt(m.luce_altezza,'mm')} | montante ${m.profilo_montante || '?'} int.${fmt(m.interasse_montanti,'mm')} | ${m.numero_traversi || 0} traversi`;
    if (tip.startsWith('cancello')) return `Cancello ${fmt(m.luce_netta,'x')}${fmt(m.altezza,'mm')} | telaio ${m.profilo_telaio || '?'} | ${m.tipo_apertura || '?'} ${m.motorizzazione ? '+ motore' : ''}`;
    if (tip === 'scala') return `Scala ${m.numero_gradini || '?'} gradini | ${fmt(m.larghezza,'mm')} larg. | alzata ${fmt(m.alzata,'mm')} pedata ${fmt(m.pedata,'mm')} | ${m.profilo_struttura || '?'}`;
    if (tip === 'recinzione') return `Recinzione ${fmt(m.lunghezza_totale,'mm')} | h.${fmt(m.altezza,'mm')} | pali ${m.profilo_palo || '?'} int.${fmt(m.interasse_pali,'mm')}`;
    if (tip === 'ringhiera') return `Ringhiera ${fmt(m.lunghezza,'mm')} | h.${fmt(m.altezza,'mm')} | corrente ${m.profilo_corrente || '?'} | montante ${m.profilo_montante || '?'}`;
    return '';
}

function ContestoSection({ misure, onChange }) {
    const [aperto, setAperto] = useState(false);
    const ctx = misure?.contesto || {};
    const setCtx = (k, v) => onChange({ ...misure, contesto: { ...ctx, [k]: v } });

    return (
        <div className="mt-6 border border-slate-200 rounded-lg overflow-hidden" data-testid="contesto-section">
            <button
                type="button"
                onClick={() => setAperto(!aperto)}
                className="w-full flex items-center justify-between bg-slate-50 px-4 py-3 hover:bg-slate-100 transition-colors"
            >
                <span className="text-[13px] font-semibold text-slate-600 flex items-center gap-2">
                    <Building2 className="h-4 w-4" /> Contesto Installazione (opzionale)
                </span>
                {aperto ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
            </button>
            {aperto && (
                <div className="p-4 space-y-3" data-testid="contesto-fields">
                    <BoolField label="Mostra parete nel 3D" value={ctx.mostra_parete} onChange={v => setCtx('mostra_parete', v)} testId="ctx-mostra-parete" />
                    {ctx.mostra_parete && (
                        <div className="space-y-3 pl-2 border-l-2 border-blue-200">
                            <div className="grid grid-cols-3 gap-3">
                                <NumField label="Spessore parete" unit="mm" value={ctx.spessore_parete ?? 300} onChange={v => setCtx('spessore_parete', v)} min={150} max={600} hint="Tipico: 300mm" testId="ctx-spessore-parete" />
                                <NumField label="Altezza parete" unit="mm" value={ctx.altezza_parete ?? 2700} onChange={v => setCtx('altezza_parete', v)} min={2000} max={4000} testId="ctx-altezza-parete" />
                                <NumField label="Larghezza parete" unit="mm" value={ctx.larghezza_parete ?? 2000} onChange={v => setCtx('larghezza_parete', v)} min={1000} max={5000} testId="ctx-larghezza-parete" />
                            </div>
                            <BoolField label="Davanzale" value={ctx.davanzale} onChange={v => setCtx('davanzale', v)} testId="ctx-davanzale" />
                            {ctx.davanzale && (
                                <NumField label="Sporgenza davanzale" unit="mm" value={ctx.sporgenza_davanzale ?? 80} onChange={v => setCtx('sporgenza_davanzale', v)} min={50} max={200} testId="ctx-sporgenza-dav" />
                            )}
                            <BoolField label="Scuri / Persiane" value={ctx.scuri} onChange={v => setCtx('scuri', v)} testId="ctx-scuri" />
                            {ctx.scuri && (
                                <SelField label="Tipo scuri" value={ctx.tipo_scuri || 'battenti'} onChange={v => setCtx('tipo_scuri', v)} options={['battenti','scorrevoli']} testId="ctx-tipo-scuri" />
                            )}
                            <BoolField label="Tapparella avvolgibile" value={ctx.tapparelle} onChange={v => setCtx('tapparelle', v)} testId="ctx-tapparelle" />
                            <BoolField label="Zanzariera" value={ctx.zanzariera} onChange={v => setCtx('zanzariera', v)} testId="ctx-zanzariera" />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function FormMisure({ tipologia, misure, onChange }) {
    const m = misure || {};
    const set = (k, v) => onChange({ ...m, [k]: v });

    if (tipologia === 'inferriata_fissa') return (
        <div className="space-y-4" data-testid="form-inferriata">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Luce larghezza" unit="mm" value={m.luce_larghezza} onChange={v => set('luce_larghezza', v)} testId="m-luce-larghezza" />
                <NumField label="Luce altezza" unit="mm" value={m.luce_altezza} onChange={v => set('luce_altezza', v)} testId="m-luce-altezza" />
                <NumField label="Interasse montanti" unit="mm" value={m.interasse_montanti} onChange={v => set('interasse_montanti', v)} testId="m-interasse-montanti" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Profilo montante" value={m.profilo_montante} onChange={v => set('profilo_montante', v)} options={PROFILI_MONTANTE} testId="m-profilo-montante" />
                <SelField label="Profilo traverso" value={m.profilo_traverso} onChange={v => set('profilo_traverso', v)} options={PROFILI_TRAVERSO} testId="m-profilo-traverso" />
                <NumField label="Numero traversi" value={m.numero_traversi} onChange={v => set('numero_traversi', v)} testId="m-numero-traversi" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo ancoraggio" value={m.tipo_ancoraggio} onChange={v => set('tipo_ancoraggio', v)} options={['tasselli','muratura','saldatura','a_muro']} testId="m-tipo-ancoraggio" />
                <NumField label="Spessore muro" unit="mm" value={m.spessore_muro} onChange={v => set('spessore_muro', v)} testId="m-spessore-muro" />
            </div>
            <BoolField label="Presenza davanzale" value={m.presenza_davanzale} onChange={v => set('presenza_davanzale', v)} testId="m-davanzale" />
            {m.presenza_davanzale && (
                <NumField label="Altezza davanzale" unit="mm" value={m.altezza_davanzale} onChange={v => set('altezza_davanzale', v)} testId="m-altezza-davanzale" />
            )}
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Finitura" value={m.finitura} onChange={v => set('finitura', v)} options={FINITURE} testId="m-finitura" />
                <SelField label="Colore RAL" value={m.colore} onChange={v => set('colore', v)} options={RAL_COMUNI} testId="m-colore" />
            </div>
            <ContestoSection misure={m} onChange={onChange} />
        </div>
    );

    if (tipologia === 'cancello_carrabile') return (
        <div className="space-y-4" data-testid="form-cancello-carrabile">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Luce netta" unit="mm" value={m.luce_netta} onChange={v => set('luce_netta', v)} testId="m-luce-netta" />
                <NumField label="Altezza" unit="mm" value={m.altezza} onChange={v => set('altezza', v)} testId="m-altezza" />
                <NumField label="Numero ante" value={m.numero_ante} onChange={v => set('numero_ante', v)} testId="m-numero-ante" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo apertura" value={m.tipo_apertura} onChange={v => set('tipo_apertura', v)} options={APERTURE_CANCELLO} testId="m-tipo-apertura" />
                <SelField label="Profilo telaio" value={m.profilo_telaio} onChange={v => set('profilo_telaio', v)} options={PROFILI_TELAIO} testId="m-profilo-telaio" />
                <SelField label="Profilo infisso" value={m.profilo_infisso} onChange={v => set('profilo_infisso', v)} options={PROFILI_INFISSO} testId="m-profilo-infisso" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <NumField label="Interasse infissi" unit="mm" value={m.interasse_infissi} onChange={v => set('interasse_infissi', v)} testId="m-interasse-infissi" />
            </div>
            <BoolField label="Pendenza terreno" value={m.pendenza_terreno} onChange={v => set('pendenza_terreno', v)} testId="m-pendenza" />
            <BoolField label="Pilastri esistenti" value={m.pilastri_esistenti} onChange={v => set('pilastri_esistenti', v)} testId="m-pilastri" />
            {m.pilastri_esistenti && (
                <NumField label="Larghezza pilastro" unit="mm" value={m.larghezza_pilastro} onChange={v => set('larghezza_pilastro', v)} testId="m-larg-pilastro" />
            )}
            <BoolField label="Motorizzazione" value={m.motorizzazione} onChange={v => set('motorizzazione', v)} testId="m-motorizzazione" />
            {m.motorizzazione && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <SelField label="Tipo motore" value={m.tipo_motore} onChange={v => set('tipo_motore', v)} options={['FAAC','CAME','BFT','NICE','BENINCA']} testId="m-tipo-motore" />
                    <NumField label="Spazio motore SX" unit="mm" value={m.spazio_motore_sx} onChange={v => set('spazio_motore_sx', v)} testId="m-spazio-sx" />
                    <NumField label="Spazio motore DX" unit="mm" value={m.spazio_motore_dx} onChange={v => set('spazio_motore_dx', v)} testId="m-spazio-dx" />
                </div>
            )}
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Finitura" value={m.finitura} onChange={v => set('finitura', v)} options={FINITURE} testId="m-finitura" />
                <SelField label="Colore RAL" value={m.colore} onChange={v => set('colore', v)} options={RAL_COMUNI} testId="m-colore" />
            </div>
        </div>
    );

    if (tipologia === 'cancello_pedonale') return (
        <div className="space-y-4" data-testid="form-cancello-pedonale">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Luce netta" unit="mm" value={m.luce_netta} onChange={v => set('luce_netta', v)} testId="m-luce-netta" />
                <NumField label="Altezza" unit="mm" value={m.altezza} onChange={v => set('altezza', v)} testId="m-altezza" />
                <NumField label="Numero ante" value={m.numero_ante} onChange={v => set('numero_ante', v)} testId="m-numero-ante" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo apertura" value={m.tipo_apertura} onChange={v => set('tipo_apertura', v)} options={['battente','scorrevole']} testId="m-tipo-apertura" />
                <SelField label="Verso apertura" value={m.verso_apertura} onChange={v => set('verso_apertura', v)} options={['interno','esterno']} testId="m-verso-apertura" />
                <SelField label="Serratura" value={m.serratura} onChange={v => set('serratura', v)} options={['Yale','a_cilindro','elettroserratura','nessuna']} testId="m-serratura" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Profilo telaio" value={m.profilo_telaio} onChange={v => set('profilo_telaio', v)} options={PROFILI_TELAIO} testId="m-profilo-telaio" />
                <SelField label="Profilo infisso" value={m.profilo_infisso} onChange={v => set('profilo_infisso', v)} options={PROFILI_INFISSO} testId="m-profilo-infisso" />
                <NumField label="Interasse infissi" unit="mm" value={m.interasse_infissi} onChange={v => set('interasse_infissi', v)} testId="m-interasse-infissi" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Finitura" value={m.finitura} onChange={v => set('finitura', v)} options={FINITURE} testId="m-finitura" />
                <SelField label="Colore RAL" value={m.colore} onChange={v => set('colore', v)} options={RAL_COMUNI} testId="m-colore" />
            </div>
            <ContestoSection misure={m} onChange={onChange} />
        </div>
    );

    if (tipologia === 'scala') return (
        <div className="space-y-4" data-testid="form-scala">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo scala" value={m.tipo} onChange={v => set('tipo', v)} options={TIPI_SCALA} testId="m-tipo-scala" />
                <NumField label="Numero gradini" value={m.numero_gradini} onChange={v => set('numero_gradini', v)} testId="m-numero-gradini" />
                <NumField label="Larghezza" unit="mm" value={m.larghezza} onChange={v => set('larghezza', v)} testId="m-larghezza" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Alzata" unit="mm" value={m.alzata} onChange={v => set('alzata', v)} testId="m-alzata" />
                <NumField label="Pedata" unit="mm" value={m.pedata} onChange={v => set('pedata', v)} testId="m-pedata" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo struttura" value={m.tipo_struttura} onChange={v => set('tipo_struttura', v)} options={TIPI_STRUTTURA_SCALA} testId="m-tipo-struttura" />
                <SelField label="Profilo struttura" value={m.profilo_struttura} onChange={v => set('profilo_struttura', v)} options={PROFILI_STRUTTURA} testId="m-profilo-struttura" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo gradino" value={m.tipo_gradino} onChange={v => set('tipo_gradino', v)} options={TIPI_GRADINO} testId="m-tipo-gradino" />
                <NumField label="Spessore gradino" unit="mm" value={m.spessore_gradino} onChange={v => set('spessore_gradino', v)} testId="m-spessore-gradino" />
            </div>
            <BoolField label="Corrimano" value={m.corrimano} onChange={v => set('corrimano', v)} testId="m-corrimano" />
            {m.corrimano && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <SelField label="Lato corrimano" value={m.lato_corrimano} onChange={v => set('lato_corrimano', v)} options={['sx','dx','entrambi']} testId="m-lato-corrimano" />
                    <SelField label="Profilo corrimano" value={m.profilo_corrimano} onChange={v => set('profilo_corrimano', v)} options={PROFILI_CORRIMANO} testId="m-profilo-corrimano" />
                    <SelField label="Montanti corrimano" value={m.montanti_corrimano} onChange={v => set('montanti_corrimano', v)} options={['quadro_20x20','quadro_25x25','tondo_20']} testId="m-montanti-corrimano" />
                    <NumField label="Interasse montanti" unit="mm" value={m.interasse_montanti} onChange={v => set('interasse_montanti', v)} testId="m-interasse-montanti" />
                </div>
            )}
            <BoolField label="Attacco a muro" value={m.attacco_muro} onChange={v => set('attacco_muro', v)} testId="m-attacco-muro" />
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Finitura" value={m.finitura} onChange={v => set('finitura', v)} options={FINITURE} testId="m-finitura" />
                <SelField label="Colore RAL" value={m.colore} onChange={v => set('colore', v)} options={RAL_COMUNI} testId="m-colore" />
            </div>
        </div>
    );

    if (tipologia === 'recinzione') return (
        <div className="space-y-4" data-testid="form-recinzione">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Lunghezza totale" unit="mm" value={m.lunghezza_totale} onChange={v => set('lunghezza_totale', v)} testId="m-lunghezza-totale" />
                <NumField label="Altezza" unit="mm" value={m.altezza} onChange={v => set('altezza', v)} testId="m-altezza" />
                <NumField label="Numero campate" value={m.numero_campate} onChange={v => set('numero_campate', v)} testId="m-numero-campate" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Lunghezza campata" unit="mm" value={m.lunghezza_campata} onChange={v => set('lunghezza_campata', v)} testId="m-lung-campata" />
                <NumField label="Interasse pali" unit="mm" value={m.interasse_pali} onChange={v => set('interasse_pali', v)} testId="m-interasse-pali" />
                <SelField label="Profilo palo" value={m.profilo_palo} onChange={v => set('profilo_palo', v)} options={['40x40','50x50','60x60','80x80','tondo_48','tondo_60']} testId="m-profilo-palo" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo pannello" value={m.tipo_pannello} onChange={v => set('tipo_pannello', v)} options={TIPI_PANNELLO} testId="m-tipo-pannello" />
                <SelField label="Profilo orizzontale" value={m.profilo_orizzontale} onChange={v => set('profilo_orizzontale', v)} options={PROFILI_TRAVERSO} testId="m-profilo-orizz" />
                <NumField label="N. orizzontali" value={m.numero_orizzontali} onChange={v => set('numero_orizzontali', v)} testId="m-num-orizz" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Profilo verticale" value={m.profilo_verticale} onChange={v => set('profilo_verticale', v)} options={PROFILI_INFISSO} testId="m-profilo-vert" />
                <NumField label="Interasse verticali" unit="mm" value={m.interasse_verticali} onChange={v => set('interasse_verticali', v)} testId="m-interasse-vert" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Finitura" value={m.finitura} onChange={v => set('finitura', v)} options={FINITURE} testId="m-finitura" />
                <SelField label="Colore RAL" value={m.colore} onChange={v => set('colore', v)} options={RAL_COMUNI} testId="m-colore" />
            </div>
        </div>
    );

    if (tipologia === 'ringhiera') return (
        <div className="space-y-4" data-testid="form-ringhiera">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <NumField label="Lunghezza" unit="mm" value={m.lunghezza} onChange={v => set('lunghezza', v)} testId="m-lunghezza" />
                <NumField label="Altezza" unit="mm" value={m.altezza} onChange={v => set('altezza', v)} testId="m-altezza" />
                <SelField label="Tipo" value={m.tipo} onChange={v => set('tipo', v)} options={['diritta','curva','angolare']} testId="m-tipo" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Profilo corrente" value={m.profilo_corrente} onChange={v => set('profilo_corrente', v)} options={PROFILI_MONTANTE} testId="m-profilo-corrente" />
                <SelField label="Profilo montante" value={m.profilo_montante} onChange={v => set('profilo_montante', v)} options={PROFILI_MONTANTE} testId="m-profilo-montante" />
                <NumField label="Interasse montanti" unit="mm" value={m.interasse_montanti} onChange={v => set('interasse_montanti', v)} testId="m-interasse-montanti" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <SelField label="Tipo infisso" value={m.tipo_infisso} onChange={v => set('tipo_infisso', v)} options={['quadro_20x20','quadro_25x25','tondo_12','tondo_16']} testId="m-tipo-infisso" />
                <NumField label="Interasse infissi" unit="mm" value={m.interasse_infissi} onChange={v => set('interasse_infissi', v)} testId="m-interasse-infissi" />
                <SelField label="Corrimano" value={m.corrimano} onChange={v => set('corrimano', v)} options={PROFILI_CORRIMANO} testId="m-corrimano" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Tipo attacco" value={m.tipo_attacco} onChange={v => set('tipo_attacco', v)} options={TIPI_ATTACCO} testId="m-tipo-attacco" />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <SelField label="Finitura" value={m.finitura} onChange={v => set('finitura', v)} options={FINITURE} testId="m-finitura" />
                <SelField label="Colore RAL" value={m.colore} onChange={v => set('colore', v)} options={RAL_COMUNI} testId="m-colore" />
            </div>
        </div>
    );

    return null;
}




export default function RilievoEditorPage() {
    const navigate = useNavigate();
    const { rilievoId } = useParams();
    const [searchParams] = useSearchParams();
    const clientIdFromUrl = searchParams.get('client_id');
    const isEditing = !!rilievoId;

    const [loading, setLoading] = useState(isEditing);
    const [saving, setSaving] = useState(false);
    const [creatingPos, setCreatingPos] = useState(false);
    const [clients, setClients] = useState([]);
    const photoInputRef = useRef(null);
    const viewer3dRef = useRef(null);
    
    const [formData, setFormData] = useState({
        client_id: clientIdFromUrl || '',
        project_name: '',
        survey_date: new Date().toISOString().split('T')[0],
        location: '',
        notes: '',
        status: 'bozza',
        sketches: [],
        photos: [],
        tipologia: '',
        misure: {},
        elementi: [],
        vista_3d_config: {},
    });

    const [sketchDialogOpen, setSketchDialogOpen] = useState(false);
    const [editingSketch, setEditingSketch] = useState(null);
    const [activeTab, setActiveTab] = useState('info');

    // Fetch clients on mount
    useEffect(() => {
        const fetchClients = async () => {
            try {
                const data = await apiRequest('/clients/?limit=100');
                setClients(data.clients);
            } catch (error) {
                toast.error('Errore caricamento clienti');
            }
        };
        fetchClients();
    }, []);

    // Fetch rilievo if editing
    useEffect(() => {
        if (!isEditing) return;
        
        const fetchRilievo = async () => {
            try {
                const data = await apiRequest(`/rilievi/${rilievoId}`);
                setFormData({
                    client_id: data.client_id,
                    project_name: data.project_name,
                    survey_date: data.survey_date,
                    location: data.location || '',
                    notes: data.notes || '',
                    status: data.status,
                    sketches: data.sketches || [],
                    photos: data.photos || [],
                    tipologia: data.tipologia || '',
                    misure: data.misure || {},
                    elementi: data.elementi || [],
                    vista_3d_config: data.vista_3d_config || {},
                });
            } catch (error) {
                toast.error('Rilievo non trovato');
                navigate('/rilievi');
            } finally {
                setLoading(false);
            }
        };
        fetchRilievo();
    }, [rilievoId, isEditing, navigate]);

    const updateField = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const API = process.env.REACT_APP_BACKEND_URL;

    const handlePhotoUpload = async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;
        if (!rilievoId || !isEditing) {
            toast.error('Salva il rilievo prima di caricare foto');
            return;
        }
        for (const file of files) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('caption', '');
                const res = await fetch(`${API}/api/rilievi/${rilievoId}/upload-foto`, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData,
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || 'Upload fallito');
                }
                const photoEntry = await res.json();
                setFormData(prev => ({
                    ...prev,
                    photos: [...prev.photos, photoEntry]
                }));
            } catch (err) { toast.error(err.message); }
        }
        e.target.value = '';
    };

    const removePhoto = async (photo) => {
        // Object storage photo (new format)
        if (photo.storage_path && rilievoId) {
            try {
                await apiRequest(`/rilievi/${rilievoId}/foto/${photo.photo_id}`, { method: 'DELETE' });
                setFormData(prev => ({
                    ...prev,
                    photos: prev.photos.filter(p => p.photo_id !== photo.photo_id)
                }));
            } catch { toast.error('Errore eliminazione foto'); }
        } else {
            // Legacy base64 — just remove from local state
            setFormData(prev => ({
                ...prev,
                photos: prev.photos.filter(p => p.photo_id !== photo.photo_id)
            }));
        }
    };

    const getPhotoSrc = (photo) => {
        if (photo.storage_path) {
            return `${API}/api/rilievi/foto-proxy/${photo.storage_path}`;
        }
        if (photo.image_data) {
            return photo.image_data;
        }
        return '';
    };

    const handleSketchSave = async (sketchData) => {
        if (editingSketch?.sketch_id && !editingSketch.sketch_id.startsWith('temp_')) {
            // Update existing sketch in local state (drawing_data update)
            setFormData(prev => ({
                ...prev,
                sketches: prev.sketches.map(s =>
                    s.sketch_id === editingSketch.sketch_id
                        ? { ...s, ...sketchData }
                        : s
                )
            }));
        } else if (rilievoId && isEditing) {
            // Upload new sketch via endpoint
            try {
                const fd = new FormData();
                fd.append('name', sketchData.name || 'Schizzo');
                fd.append('drawing_data', sketchData.drawing_data || '');
                fd.append('dimensions', JSON.stringify(sketchData.dimensions || {}));
                // If background_image is a base64 data URI, convert to blob
                if (sketchData.background_image && sketchData.background_image.startsWith('data:')) {
                    const resp = await fetch(sketchData.background_image);
                    const blob = await resp.blob();
                    fd.append('background', blob, 'background.jpg');
                }
                const res = await fetch(`${API}/api/rilievi/${rilievoId}/upload-sketch`, {
                    method: 'POST',
                    credentials: 'include',
                    body: fd,
                });
                if (!res.ok) throw new Error('Upload schizzo fallito');
                const sketchEntry = await res.json();
                setFormData(prev => ({
                    ...prev,
                    sketches: [...prev.sketches, sketchEntry]
                }));
            } catch (err) { toast.error(err.message); }
        } else {
            // Fallback: add to local state (will be saved with the form)
            setFormData(prev => ({
                ...prev,
                sketches: [
                    ...prev.sketches,
                    {
                        ...sketchData,
                        sketch_id: `temp_${Date.now()}`,
                    }
                ]
            }));
        }
        setSketchDialogOpen(false);
        setEditingSketch(null);
    };

    const removeSketch = async (sketch) => {
        if (sketch.storage_path || (sketch.sketch_id && !sketch.sketch_id.startsWith('temp_') && rilievoId)) {
            try {
                await apiRequest(`/rilievi/${rilievoId}/sketch/${sketch.sketch_id}`, { method: 'DELETE' });
            } catch { /* ignore */ }
        }
        setFormData(prev => ({
            ...prev,
            sketches: prev.sketches.filter(s => s.sketch_id !== sketch.sketch_id)
        }));
    };

    const handleGeneraPos = async () => {
        if (!isEditing) {
            toast.error('Salva il rilievo prima di generare il POS');
            return;
        }
        setCreatingPos(true);
        try {
            const res = await apiRequest(`/sicurezza/from-rilievo/${rilievoId}`, { method: 'POST' });
            toast.success('POS cantiere creato!');
            navigate(`/sicurezza/${res.pos_id || ''}`);
        } catch (e) {
            toast.error(e.message || 'Errore nella creazione del POS');
        } finally {
            setCreatingPos(false);
        }
    };

    const handleSave = async () => {
        if (!formData.client_id) {
            toast.error('Seleziona un cliente');
            return;
        }
        if (!formData.project_name.trim()) {
            toast.error('Inserisci il nome del progetto');
            return;
        }

        try {
            setSaving(true);
            
            if (isEditing) {
                // Photos and sketches are managed via dedicated upload endpoints
                const { photos: _p, sketches: _s, ...metadataOnly } = formData;
                await apiRequest(`/rilievi/${rilievoId}`, {
                    method: 'PUT',
                    body: JSON.stringify(metadataOnly),
                });
                toast.success('Rilievo aggiornato');
            } else {
                // On create, send metadata only (no photos/sketches yet)
                const { photos: _p, sketches: _s, ...metadataOnly } = formData;
                const result = await apiRequest('/rilievi/', {
                    method: 'POST',
                    body: JSON.stringify(metadataOnly),
                });
                toast.success('Rilievo creato — ora puoi aggiungere foto e schizzi');
                navigate(`/rilievi/${result.rilievo_id}`);
            }
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDownloadPDF = async () => {
        if (!rilievoId) return;
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/rilievi/${rilievoId}/pdf`,
                { credentials: 'include' }
            );
            if (!response.ok) throw new Error('Errore download');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Rilievo_${formData.project_name.replace(/\s+/g, '_')}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch (error) {
            toast.error('Errore nel download del PDF');
        }
    };

    const selectedClient = clients.find(c => c.client_id === formData.client_id);

    // ── Commessa linking ──
    const [showLinkDialog, setShowLinkDialog] = useState(false);
    const [commesseList, setCommesseList] = useState([]);
    const [linkedCommessa, setLinkedCommessa] = useState(null);
    const [materialiResult, setMaterialiResult] = useState(null);
    const [calcoloLoading, setCalcoloLoading] = useState(false);

    useEffect(() => {
        if (formData.commessa_id) {
            apiRequest(`/commesse/${formData.commessa_id}`).then(c => setLinkedCommessa(c)).catch(() => {});
        }
    }, [formData.commessa_id]);

    const handleCreaCommessa = () => {
        const params = new URLSearchParams();
        params.set('title', formData.project_name || 'Rilievo');
        if (formData.client_id) params.set('client_id', formData.client_id);
        if (formData.location) params.set('cantiere', formData.location);
        if (formData.notes) params.set('notes', formData.notes);
        params.set('linked_rilievo_id', rilievoId);
        navigate(`/commesse/nuova?${params.toString()}`);
    };

    const handleOpenLinkDialog = async () => {
        try {
            const data = await apiRequest('/commesse?limit=100');
            const list = data?.items || data || [];
            setCommesseList(list.filter(c => c.client_id === formData.client_id || !formData.client_id));
        } catch { setCommesseList([]); }
        setShowLinkDialog(true);
    };

    const handleLinkCommessa = async (commessaId) => {
        try {
            await apiRequest(`/rilievi/${rilievoId}/collega-commessa`, {
                method: 'PATCH',
                body: JSON.stringify({ commessa_id: commessaId }),
            });
            setFormData(prev => ({ ...prev, commessa_id: commessaId }));
            const c = commesseList.find(x => x.commessa_id === commessaId);
            setLinkedCommessa(c);
            setShowLinkDialog(false);
            toast.success('Rilievo collegato alla commessa');
        } catch (err) { toast.error(err.message); }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 loading-spinner" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-6 max-w-5xl">
                {/* Header - Tablet Friendly */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="lg"
                            onClick={() => navigate('/rilievi')}
                            className="h-12 px-4"
                        >
                            <ArrowLeft className="h-5 w-5 mr-2" />
                            Indietro
                        </Button>
                        <div>
                            <h1 className="font-sans text-2xl font-bold text-slate-900">
                                {isEditing ? 'Modifica Rilievo' : 'Nuovo Rilievo'}
                            </h1>
                        </div>
                    </div>
                    <div className="flex gap-3">
                        {isEditing && (
                            <>
                                <Button
                                    data-testid="btn-genera-pos"
                                    variant="outline"
                                    onClick={handleGeneraPos}
                                    disabled={creatingPos}
                                    className="h-12 px-6 border-amber-500 text-amber-600 hover:bg-amber-50"
                                >
                                    <HardHat className="h-5 w-5 mr-2" />
                                    {creatingPos ? 'Creazione...' : 'Genera POS'}
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={handleDownloadPDF}
                                    className="h-12 px-6"
                                >
                                    <Download className="h-5 w-5 mr-2" />
                                    PDF
                                </Button>
                                {!formData.commessa_id ? (
                                    <>
                                        <Button
                                            data-testid="btn-crea-commessa-rilievo"
                                            variant="outline"
                                            onClick={handleCreaCommessa}
                                            className="h-12 px-4 border-emerald-500 text-emerald-600 hover:bg-emerald-50"
                                        >
                                            <Building2 className="h-5 w-5 mr-2" />
                                            Crea Commessa
                                        </Button>
                                        <Button
                                            data-testid="btn-collega-commessa-rilievo"
                                            variant="outline"
                                            onClick={handleOpenLinkDialog}
                                            className="h-12 px-4 border-blue-500 text-blue-600 hover:bg-blue-50"
                                        >
                                            <Link className="h-5 w-5 mr-2" />
                                            Collega
                                        </Button>
                                    </>
                                ) : linkedCommessa && (
                                    <Badge variant="outline" className="h-12 px-4 text-sm border-emerald-200 bg-emerald-50 text-emerald-700 flex items-center gap-2">
                                        <Building2 className="h-4 w-4" />
                                        {linkedCommessa.numero}
                                    </Badge>
                                )}
                            </>
                        )}
                        <Button
                            data-testid="btn-save-rilievo"
                            onClick={handleSave}
                            disabled={saving}
                            className="h-12 px-8 bg-[#0055FF] text-white hover:bg-[#0044CC] text-base"
                        >
                            <Save className="h-5 w-5 mr-2" />
                            {saving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                    </div>
                </div>

                {/* Tabs - Large for Tablet */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                    <TabsList className="h-14 p-1 bg-slate-100">
                        <TabsTrigger value="info" className="h-12 px-6 text-base gap-2">
                            <Pencil className="h-5 w-5" />
                            Info
                        </TabsTrigger>
                        <TabsTrigger value="misure" className="h-12 px-6 text-base gap-2" data-testid="tab-misure">
                            <SlidersHorizontal className="h-5 w-5" />
                            Misure
                            {formData.tipologia && <span className="ml-1 w-2 h-2 rounded-full bg-[#0055FF] inline-block" />}
                        </TabsTrigger>
                        <TabsTrigger value="sketches" className="h-12 px-6 text-base gap-2">
                            <Ruler className="h-5 w-5" />
                            Schizzi ({formData.sketches.length})
                        </TabsTrigger>
                        <TabsTrigger value="photos" className="h-12 px-6 text-base gap-2">
                            <Camera className="h-5 w-5" />
                            Foto ({formData.photos.length})
                        </TabsTrigger>
                    </TabsList>

                    {/* Info Tab */}
                    <TabsContent value="info">
                        <Card className="border-gray-200">
                            <CardContent className="pt-6 space-y-6">
                                <div className="grid grid-cols-2 gap-6">
                                    <div className="col-span-2">
                                        <Label htmlFor="project_name" className="text-base">
                                            Nome Progetto *
                                        </Label>
                                        <Input
                                            id="project_name"
                                            data-testid="input-project-name"
                                            value={formData.project_name}
                                            onChange={(e) => updateField('project_name', e.target.value)}
                                            placeholder="Es: Ristrutturazione appartamento Via Roma"
                                            className="h-14 text-lg"
                                        />
                                    </div>
                                    <div>
                                        <Label className="text-base">Cliente *</Label>
                                        <Select
                                            value={formData.client_id || "__none__"}
                                            onValueChange={(v) => updateField('client_id', v === "__none__" ? "" : v)}
                                        >
                                            <SelectTrigger data-testid="select-client" className="h-14 text-base">
                                                <SelectValue placeholder="Seleziona cliente..." />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="__none__">-- Seleziona cliente --</SelectItem>
                                                {clients.map(c => (
                                                    <SelectItem key={c.client_id} value={c.client_id}>
                                                        {c.business_name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        {selectedClient && (
                                            <p className="mt-2 text-sm text-slate-500">
                                                {selectedClient.address}, {selectedClient.city}
                                            </p>
                                        )}
                                    </div>
                                    <div>
                                        <Label htmlFor="survey_date" className="text-base">
                                            Data Rilievo
                                        </Label>
                                        <Input
                                            id="survey_date"
                                            type="date"
                                            data-testid="input-survey-date"
                                            value={formData.survey_date}
                                            onChange={(e) => updateField('survey_date', e.target.value)}
                                            className="h-14 text-lg"
                                        />
                                    </div>
                                    <div className="col-span-2">
                                        <Label htmlFor="location" className="text-base">
                                            Località / Indirizzo
                                        </Label>
                                        <Input
                                            id="location"
                                            data-testid="input-location"
                                            value={formData.location}
                                            onChange={(e) => updateField('location', e.target.value)}
                                            placeholder="Indirizzo del sopralluogo"
                                            className="h-14 text-lg"
                                        />
                                    </div>
                                    <div className="col-span-2">
                                        <Label htmlFor="notes" className="text-base">
                                            Note Tecniche
                                        </Label>
                                        <Textarea
                                            id="notes"
                                            data-testid="input-notes"
                                            value={formData.notes}
                                            onChange={(e) => updateField('notes', e.target.value)}
                                            placeholder="Dettagli tecnici, osservazioni, misure particolari..."
                                            rows={6}
                                            className="text-base"
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Misure Tab */}
                    <TabsContent value="misure">
                        <Card className="border-gray-200">
                            <CardContent className="pt-6">
                                <TipologiaSelector
                                    value={formData.tipologia}
                                    onChange={(tip) => {
                                        updateField('tipologia', tip);
                                        if (tip && tip !== formData.tipologia) {
                                            updateField('misure', {});
                                            updateField('elementi', []);
                                        }
                                    }}
                                />
                                {formData.tipologia && (
                                    <div className="mt-6 pt-6 border-t border-slate-200">
                                        {(() => {
                                            const tip = TIPOLOGIE.find(t => t.id === formData.tipologia);
                                            const TipIcon = tip?.icon;
                                            return (
                                                <div className="rounded-lg mb-5 p-4 border border-slate-200" style={{
                                                    background: 'linear-gradient(135deg, rgba(0,85,255,0.06), rgba(0,85,255,0.02))',
                                                    borderLeft: '4px solid #0055FF'
                                                }}>
                                                    <div className="flex items-center gap-3">
                                                        {TipIcon && <div className="w-10 h-10 rounded-lg bg-[#0055FF] flex items-center justify-center"><TipIcon className="h-5 w-5 text-white" /></div>}
                                                        <div>
                                                            <h3 className="text-base font-bold text-slate-900 m-0">{tip?.label || formData.tipologia}</h3>
                                                            <p className="text-xs text-slate-500 m-0 mt-0.5">Inserisci le misure rilevate in cantiere</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })()}
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                            <div>
                                                <FormMisure
                                                    tipologia={formData.tipologia}
                                                    misure={formData.misure}
                                                    onChange={(newMisure) => updateField('misure', newMisure)}
                                                />
                                                {riepilogoMisure(formData.tipologia, formData.misure) && (
                                                    <div className="mt-4 rounded-lg px-4 py-3 font-mono text-xs text-slate-300 bg-[#1a1a2e] leading-relaxed" data-testid="riepilogo-misure">
                                                        {riepilogoMisure(formData.tipologia, formData.misure)}
                                                    </div>
                                                )}
                                            </div>
                                            <div>
                                                <div className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">Vista 3D</div>
                                                <RilievoViewer3D ref={viewer3dRef} tipologia={formData.tipologia} misure={formData.misure} />
                                                <div className="flex items-center justify-between mt-2">
                                                    <p className="text-xs text-slate-400">Trascina per ruotare, scroll per zoom</p>
                                                    {rilievoId && (
                                                        <Button
                                                            type="button"
                                                            variant="outline"
                                                            size="sm"
                                                            data-testid="btn-screenshot-3d"
                                                            className="h-7 text-xs gap-1"
                                                            onClick={async () => {
                                                                if (!viewer3dRef.current) return;
                                                                const dataUrl = viewer3dRef.current.captureScreenshot();
                                                                if (!dataUrl) { toast.error('Screenshot non disponibile'); return; }
                                                                try {
                                                                    const resp = await fetch(dataUrl);
                                                                    const blob = await resp.blob();
                                                                    const fd = new FormData();
                                                                    fd.append('file', blob, `vista_3d_${formData.tipologia}.png`);
                                                                    fd.append('caption', `Vista 3D - ${TIPOLOGIE.find(t => t.id === formData.tipologia)?.label || formData.tipologia}`);
                                                                    const res = await fetch(`${API}/api/rilievi/${rilievoId}/upload-foto`, {
                                                                        method: 'POST', credentials: 'include', body: fd,
                                                                    });
                                                                    if (!res.ok) throw new Error('Upload fallito');
                                                                    const photo = await res.json();
                                                                    setFormData(prev => ({ ...prev, photos: [...prev.photos, photo] }));
                                                                    toast.success('Screenshot 3D salvato nelle foto');
                                                                } catch (err) {
                                                                    toast.error(err.message || 'Errore salvataggio screenshot');
                                                                }
                                                            }}
                                                        >
                                                            <Camera className="h-3 w-3" />
                                                            Cattura
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        {/* Calcola Materiali */}
                                        {rilievoId && (
                                            <div className="mt-6 pt-4 border-t border-slate-200">
                                                <div className="flex items-center justify-between mb-3">
                                                    <span className="text-sm font-semibold text-slate-700">Calcolo Materiali</span>
                                                    <Button
                                                        type="button"
                                                        size="sm"
                                                        data-testid="btn-calcola-materiali"
                                                        disabled={calcoloLoading}
                                                        onClick={async () => {
                                                            try {
                                                                setCalcoloLoading(true);
                                                                // Salva prima le misure correnti
                                                                await apiRequest(`/rilievi/${rilievoId}`, {
                                                                    method: 'PUT',
                                                                    body: JSON.stringify({ tipologia: formData.tipologia, misure: formData.misure }),
                                                                });
                                                                const res = await apiRequest(`/rilievi/${rilievoId}/calcola-materiali`, { method: 'POST' });
                                                                setMaterialiResult(res);
                                                            } catch (err) {
                                                                toast.error(err.message || 'Errore calcolo materiali');
                                                            } finally {
                                                                setCalcoloLoading(false);
                                                            }
                                                        }}
                                                    >
                                                        {calcoloLoading ? 'Calcolo...' : 'Calcola'}
                                                    </Button>
                                                </div>
                                                {materialiResult && (
                                                    <div className="space-y-3" data-testid="materiali-result">
                                                        <div className="overflow-x-auto">
                                                            <table className="w-full text-sm">
                                                                <thead>
                                                                    <tr className="border-b border-slate-200 text-left text-xs text-slate-500 uppercase">
                                                                        <th className="py-2 pr-3">Materiale</th>
                                                                        <th className="py-2 pr-3 text-right">Qty</th>
                                                                        <th className="py-2 pr-3 text-right">ml</th>
                                                                        <th className="py-2 text-right">Peso (kg)</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {materialiResult.materiali?.map((m, i) => (
                                                                        <tr key={i} className="border-b border-slate-100">
                                                                            <td className="py-2 pr-3 text-slate-700">{m.descrizione}</td>
                                                                            <td className="py-2 pr-3 text-right text-slate-600">{m.quantita}</td>
                                                                            <td className="py-2 pr-3 text-right text-slate-600">{m.ml}</td>
                                                                            <td className="py-2 text-right font-medium text-slate-800">{m.peso_kg}</td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                        <div className="flex gap-4 text-sm bg-slate-50 rounded-lg p-3">
                                                            <div><span className="text-slate-500">Peso totale:</span> <strong>{materialiResult.peso_totale_kg} kg</strong></div>
                                                            <div><span className="text-slate-500">Superficie vern.:</span> <strong>{materialiResult.superficie_verniciatura_m2} m²</strong></div>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Sketches Tab */}
                    <TabsContent value="sketches">
                        <Card className="border-gray-200">
                            <CardHeader className="flex flex-row items-center justify-between bg-blue-50 border-b border-gray-200">
                                <CardTitle className="font-sans text-xl">Schizzi e Misure</CardTitle>
                                <Button
                                    data-testid="btn-add-sketch"
                                    onClick={() => {
                                        setEditingSketch(null);
                                        setSketchDialogOpen(true);
                                    }}
                                    className="h-12 px-6 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                >
                                    <Plus className="h-5 w-5 mr-2" />
                                    Nuovo Schizzo
                                </Button>
                            </CardHeader>
                            <CardContent>
                                {formData.sketches.length === 0 ? (
                                    <div className="text-center py-16 border-2 border-dashed border-gray-200 rounded-lg">
                                        <Ruler className="h-16 w-16 mx-auto mb-4 text-slate-300" />
                                        <p className="text-lg text-slate-500 mb-4">
                                            Nessuno schizzo ancora
                                        </p>
                                        <Button
                                            onClick={() => {
                                                setEditingSketch(null);
                                                setSketchDialogOpen(true);
                                            }}
                                            className="h-14 px-8 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                        >
                                            <Plus className="h-5 w-5 mr-2" />
                                            Crea Primo Schizzo
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-2 gap-4">
                                        {formData.sketches.map((sketch, index) => (
                                            <div
                                                key={sketch.sketch_id}
                                                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                                            >
                                                <div className="flex items-start justify-between mb-3">
                                                    <div>
                                                        <h4 className="font-semibold text-slate-900">
                                                            {sketch.name || `Schizzo ${index + 1}`}
                                                        </h4>
                                                        {sketch.dimensions && (
                                                            <p className="text-sm text-slate-500">
                                                                {sketch.dimensions.width && `L: ${sketch.dimensions.width}cm`}
                                                                {sketch.dimensions.height && ` × H: ${sketch.dimensions.height}cm`}
                                                                {sketch.dimensions.depth && ` × P: ${sketch.dimensions.depth}cm`}
                                                            </p>
                                                        )}
                                                    </div>
                                                    <div className="flex gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => {
                                                                setEditingSketch(sketch);
                                                                setSketchDialogOpen(true);
                                                            }}
                                                        >
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => removeSketch(sketch)}
                                                            className="text-red-600 hover:text-red-700"
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                </div>
                                                {sketch.background_image && (
                                                    <img
                                                        src={sketch.background_image}
                                                        alt={sketch.name}
                                                        className="w-full h-32 object-cover rounded-md"
                                                    />
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Photos Tab */}
                    <TabsContent value="photos">
                        <Card className="border-gray-200">
                            <CardHeader className="flex flex-row items-center justify-between bg-blue-50 border-b border-gray-200">
                                <CardTitle className="font-sans text-xl">Foto Sopralluogo</CardTitle>
                                <Button
                                    data-testid="btn-add-photo"
                                    onClick={() => photoInputRef.current?.click()}
                                    className="h-12 px-6 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                >
                                    <Camera className="h-5 w-5 mr-2" />
                                    Scatta / Carica Foto
                                </Button>
                                <input
                                    ref={photoInputRef}
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    capture="environment"
                                    onChange={handlePhotoUpload}
                                    className="hidden"
                                />
                            </CardHeader>
                            <CardContent>
                                {formData.photos.length === 0 ? (
                                    <div className="text-center py-16 border-2 border-dashed border-gray-200 rounded-lg">
                                        <Camera className="h-16 w-16 mx-auto mb-4 text-slate-300" />
                                        <p className="text-lg text-slate-500 mb-4">
                                            Nessuna foto ancora
                                        </p>
                                        <Button
                                            onClick={() => photoInputRef.current?.click()}
                                            className="h-14 px-8 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                        >
                                            <Camera className="h-5 w-5 mr-2" />
                                            Scatta / Carica Prima Foto
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-3 gap-4">
                                        {formData.photos.map((photo, index) => (
                                            <div
                                                key={photo.photo_id}
                                                className="relative group rounded-lg overflow-hidden border border-gray-200"
                                            >
                                                <img
                                                    src={getPhotoSrc(photo)}
                                                    alt={photo.name || `Foto ${index + 1}`}
                                                    className="w-full h-48 object-cover"
                                                />
                                                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                                    <Button
                                                        variant="destructive"
                                                        size="sm"
                                                        onClick={() => removePhoto(photo)}
                                                    >
                                                        <Trash2 className="h-4 w-4 mr-1" />
                                                        Rimuovi
                                                    </Button>
                                                </div>
                                                <div className="p-2 bg-white">
                                                    <p className="text-sm text-slate-600 truncate">
                                                        {photo.name || `Foto ${index + 1}`}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>

            {/* Sketch Editor Dialog */}
            <Dialog open={sketchDialogOpen} onOpenChange={setSketchDialogOpen}>
                <DialogContent className="max-w-4xl max-h-[95vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="font-sans text-xl">
                            {editingSketch ? 'Modifica Schizzo' : 'Nuovo Schizzo'}
                        </DialogTitle>
                        <DialogDescription>
                            Disegna direttamente sulla foto per segnare le misure
                        </DialogDescription>
                    </DialogHeader>
                    <SketchEditor
                        sketch={editingSketch}
                        onSave={handleSketchSave}
                        onCancel={() => {
                            setSketchDialogOpen(false);
                            setEditingSketch(null);
                        }}
                    />
                </DialogContent>
            </Dialog>

            {/* Dialog collegamento commessa */}
            <Dialog open={showLinkDialog} onOpenChange={setShowLinkDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Collega a Commessa Esistente</DialogTitle>
                        <DialogDescription>Seleziona la commessa a cui collegare questo rilievo</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto" data-testid="commesse-link-list">
                        {commesseList.length === 0 ? (
                            <p className="text-sm text-slate-400 text-center py-4">Nessuna commessa trovata</p>
                        ) : commesseList.map(c => (
                            <button
                                key={c.commessa_id}
                                onClick={() => handleLinkCommessa(c.commessa_id)}
                                className="w-full text-left p-3 border rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                                data-testid={`link-commessa-${c.commessa_id}`}
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="font-medium text-sm">{c.numero}</span>
                                        <span className="text-slate-400 mx-2">-</span>
                                        <span className="text-sm text-slate-600">{c.title}</span>
                                    </div>
                                    <Badge variant="outline" className="text-[10px]">{c.stato || c.status}</Badge>
                                </div>
                                {c.client_name && <p className="text-xs text-slate-400 mt-1">{c.client_name}</p>}
                            </button>
                        ))}
                    </div>
                </DialogContent>
            </Dialog>
        </DashboardLayout>
    );
}
