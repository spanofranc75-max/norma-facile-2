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
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
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
    
    const [formData, setFormData] = useState({
        client_id: clientIdFromUrl || '',
        project_name: '',
        survey_date: new Date().toISOString().split('T')[0],
        location: '',
        notes: '',
        status: 'bozza',
        sketches: [],
        photos: [],
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

    const handlePhotoUpload = (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        files.forEach(file => {
            const reader = new FileReader();
            reader.onload = (event) => {
                setFormData(prev => ({
                    ...prev,
                    photos: [
                        ...prev.photos,
                        {
                            photo_id: `temp_${Date.now()}_${Math.random().toString(36).slice(2)}`,
                            name: file.name,
                            image_data: event.target.result,
                            caption: '',
                        }
                    ]
                }));
            };
            reader.readAsDataURL(file);
        });
    };

    const removePhoto = (photoId) => {
        setFormData(prev => ({
            ...prev,
            photos: prev.photos.filter(p => p.photo_id !== photoId)
        }));
    };

    const handleSketchSave = (sketchData) => {
        if (editingSketch?.sketch_id) {
            // Update existing
            setFormData(prev => ({
                ...prev,
                sketches: prev.sketches.map(s =>
                    s.sketch_id === editingSketch.sketch_id
                        ? { ...s, ...sketchData }
                        : s
                )
            }));
        } else {
            // Add new
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

    const removeSketch = (sketchId) => {
        setFormData(prev => ({
            ...prev,
            sketches: prev.sketches.filter(s => s.sketch_id !== sketchId)
        }));
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
                await apiRequest(`/rilievi/${rilievoId}`, {
                    method: 'PUT',
                    body: JSON.stringify(formData),
                });
                toast.success('Rilievo aggiornato');
            } else {
                const result = await apiRequest('/rilievi/', {
                    method: 'POST',
                    body: JSON.stringify(formData),
                });
                toast.success('Rilievo creato');
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
                            <Button
                                variant="outline"
                                onClick={handleDownloadPDF}
                                className="h-12 px-6"
                            >
                                <Download className="h-5 w-5 mr-2" />
                                PDF
                            </Button>
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
                                                            onClick={() => removeSketch(sketch.sketch_id)}
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
                                                    src={photo.image_data}
                                                    alt={photo.name || `Foto ${index + 1}`}
                                                    className="w-full h-48 object-cover"
                                                />
                                                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                                    <Button
                                                        variant="destructive"
                                                        size="sm"
                                                        onClick={() => removePhoto(photo.photo_id)}
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
        </DashboardLayout>
    );
}
