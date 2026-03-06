import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
    ArrowLeft, ArrowRight, Camera, Upload, Trash2, Brain, FileText,
    AlertTriangle, CheckCircle2, ShieldAlert, Loader2, X, Eye,
    MapPin, User, Image as ImageIcon, ChevronRight, Wrench, Download, UserPlus, Mail,
    Shield, Accessibility, HardHat
} from 'lucide-react';
import { ClientQuickCreateModal } from '../components/ClientQuickCreateModal';

const STEPS = [
    { id: 'cliente', label: 'Cliente & Luogo', icon: User },
    { id: 'foto', label: 'Foto Sopralluogo', icon: Camera },
    { id: 'analisi', label: 'Analisi AI', icon: Brain },
    { id: 'risultati', label: 'Risultati & Azioni', icon: FileText },
];

const FOTO_LABELS = [
    { value: 'panoramica', label: 'Vista Panoramica' },
    { value: 'dettaglio', label: 'Dettaglio Critico' },
    { value: 'motore', label: 'Motore / Automazione' },
    { value: 'guide', label: 'Guide / Binari' },
    { value: 'chiusura', label: 'Punto di Chiusura' },
    { value: 'sicurezza', label: 'Dispositivi Sicurezza' },
    { value: 'rete', label: 'Rete / Tamponamento' },
    { value: 'ancoraggio', label: 'Ancoraggio / Base' },
    { value: 'scala', label: 'Scala / Rampa' },
    { value: 'corrimano', label: 'Corrimano / Parapetto' },
    { value: 'struttura', label: 'Struttura Portante' },
    { value: 'saldatura', label: 'Saldatura / Giunzione' },
    { value: 'fondazione', label: 'Fondazione / Piastra' },
    { value: 'corrosione', label: 'Corrosione / Degrado' },
    { value: 'altro', label: 'Altro' },
];

const GRAVITA_COLORS = {
    alta: 'bg-red-100 text-red-800 border-red-200',
    media: 'bg-amber-100 text-amber-800 border-amber-200',
    bassa: 'bg-blue-100 text-blue-800 border-blue-200',
};

const TIPO_PERIZIA_OPTIONS = [
    {
        value: 'cancelli',
        label: 'Cancelli & Automazioni',
        norm: 'EN 12453 / EN 13241',
        description: 'Cancelli scorrevoli, battenti, sezionali, avvolgibili',
        icon: Shield,
        color: 'from-blue-500 to-blue-700',
        borderColor: 'border-blue-400',
        bgColor: 'bg-blue-50',
    },
    {
        value: 'barriere',
        label: 'Barriere Architettoniche',
        norm: 'D.M. 236/89',
        description: 'Scale, rampe, accessi, percorsi accessibilita',
        icon: Accessibility,
        color: 'from-emerald-500 to-teal-700',
        borderColor: 'border-emerald-400',
        bgColor: 'bg-emerald-50',
    },
    {
        value: 'strutture',
        label: 'Strutture & Carpenteria',
        norm: 'NTC 2018 / EN 1090',
        description: 'Tettoie, scale metalliche, soppalchi, pensiline',
        icon: HardHat,
        color: 'from-amber-500 to-orange-700',
        borderColor: 'border-amber-400',
        bgColor: 'bg-amber-50',
    },
];

export default function SopralluogoWizardPage() {
    const navigate = useNavigate();
    const { sopralluogoId } = useParams();
    const isEditing = Boolean(sopralluogoId);

    const [step, setStep] = useState(0);
    const [clients, setClients] = useState([]);
    const [saving, setSaving] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [generatingPrev, setGeneratingPrev] = useState(false);
    const [generatingPdf, setGeneratingPdf] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [sopralluogo, setSopralluogo] = useState(null);
    const [photoUrls, setPhotoUrls] = useState({});
    const [showQuickClient, setShowQuickClient] = useState(false);
    const [selectedVariant, setSelectedVariant] = useState('B');
    const [sendingEmail, setSendingEmail] = useState(false);
    const [showEmailConfirm, setShowEmailConfirm] = useState(false);
    const [emailSubject, setEmailSubject] = useState('');
    const [emailBody, setEmailBody] = useState('');

    const [formData, setFormData] = useState({
        client_id: '',
        indirizzo: '',
        comune: '',
        provincia: '',
        descrizione_utente: '',
        tipo_intervento: 'messa_a_norma',
        tipo_perizia: 'cancelli',
    });

    // Load clients
    useEffect(() => {
        apiRequest('/clients/?limit=100').then(d => setClients(d.clients || [])).catch(() => {});
    }, []);

    // Load existing sopralluogo
    useEffect(() => {
        if (!sopralluogoId) return;
        apiRequest(`/sopralluoghi/${sopralluogoId}`).then(data => {
            setSopralluogo(data);
            setFormData({
                client_id: data.client_id || '',
                indirizzo: data.indirizzo || '',
                comune: data.comune || '',
                provincia: data.provincia || '',
                descrizione_utente: data.descrizione_utente || '',
                tipo_intervento: data.tipo_intervento || 'messa_a_norma',
                tipo_perizia: data.tipo_perizia || 'cancelli',
            });
            if (data.analisi_ai) setStep(3);
            else if (data.foto?.length > 0) setStep(1);
        }).catch(() => {
            toast.error('Sopralluogo non trovato');
            navigate('/sopralluoghi');
        });
    }, [sopralluogoId, navigate]);

    // Load photo blob URLs
    const loadPhotoUrl = useCallback(async (foto) => {
        if (photoUrls[foto.foto_id]) return;
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/sopralluoghi/foto/${foto.storage_path}`,
                { credentials: 'include' }
            );
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                setPhotoUrls(prev => ({ ...prev, [foto.foto_id]: url }));
            }
        } catch (e) { /* ignore */ }
    }, [photoUrls]);

    useEffect(() => {
        if (sopralluogo?.foto) {
            sopralluogo.foto.forEach(loadPhotoUrl);
        }
    }, [sopralluogo?.foto, loadPhotoUrl]);

    // Cleanup blob URLs
    useEffect(() => {
        return () => Object.values(photoUrls).forEach(URL.revokeObjectURL);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            if (!isEditing) {
                const created = await apiRequest('/sopralluoghi/', { method: 'POST', body: formData });
                setSopralluogo(created);
                toast.success('Sopralluogo creato');
                navigate(`/sopralluoghi/${created.sopralluogo_id}`, { replace: true });
            } else {
                const updated = await apiRequest(`/sopralluoghi/${sopralluogoId}`, { method: 'PUT', body: formData });
                setSopralluogo(updated);
                toast.success('Salvato');
            }
        } catch (err) {
            toast.error(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleUploadPhoto = async (e) => {
        const files = Array.from(e.target.files);
        if (!files.length) return;
        setUploading(true);
        const id = sopralluogo?.sopralluogo_id;
        try {
            for (const file of files) {
                const fd = new FormData();
                fd.append('file', file);
                fd.append('label', 'panoramica');
                const result = await fetch(
                    `${process.env.REACT_APP_BACKEND_URL}/api/sopralluoghi/${id}/upload-foto`,
                    { method: 'POST', body: fd, credentials: 'include' }
                );
                if (!result.ok) throw new Error('Upload fallito');
            }
            // Reload sopralluogo
            const updated = await apiRequest(`/sopralluoghi/${id}`);
            setSopralluogo(updated);
            toast.success(`${files.length} foto caricate`);
        } catch (err) {
            toast.error(err.message);
        } finally {
            setUploading(false);
        }
    };

    const handleDeletePhoto = async (fotoId) => {
        try {
            await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}/foto/${fotoId}`, { method: 'DELETE' });
            setSopralluogo(prev => ({ ...prev, foto: prev.foto.filter(f => f.foto_id !== fotoId) }));
            toast.success('Foto rimossa');
        } catch (err) {
            toast.error(err.message);
        }
    };

    const handleUpdateLabel = async (fotoId, newLabel) => {
        setSopralluogo(prev => ({
            ...prev,
            foto: prev.foto.map(f => f.foto_id === fotoId ? { ...f, label: newLabel } : f),
        }));
    };

    const handleAnalyze = async () => {
        setAnalyzing(true);
        try {
            const result = await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}/analizza`, { method: 'POST' });
            setSopralluogo(prev => ({ ...prev, analisi_ai: result, status: 'analizzato' }));
            toast.success('Analisi completata!');
            setStep(3);
        } catch (err) {
            toast.error(err.message, { duration: 10000 });
        } finally {
            setAnalyzing(false);
        }
    };

    const handleEditRischio = (index, field, value) => {
        setSopralluogo(prev => {
            const newAnalisi = { ...prev.analisi_ai };
            const rischi = [...newAnalisi.rischi];
            rischi[index] = { ...rischi[index], [field]: value };
            newAnalisi.rischi = rischi;
            return { ...prev, analisi_ai: newAnalisi };
        });
    };

    const handleEditMateriale = (index, field, value) => {
        setSopralluogo(prev => {
            const newAnalisi = { ...prev.analisi_ai };
            const materiali = [...newAnalisi.materiali_suggeriti];
            materiali[index] = { ...materiali[index], [field]: value };
            newAnalisi.materiali_suggeriti = materiali;
            return { ...prev, analisi_ai: newAnalisi };
        });
    };

    const handleToggleRischio = (index) => {
        setSopralluogo(prev => {
            const newAnalisi = { ...prev.analisi_ai };
            const rischi = [...newAnalisi.rischi];
            rischi[index] = { ...rischi[index], confermato: !rischi[index].confermato };
            newAnalisi.rischi = rischi;
            return { ...prev, analisi_ai: newAnalisi };
        });
    };

    const handleDownloadPdf = async () => {
        setGeneratingPdf(true);
        try {
            // Save edits before generating PDF
            await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}`, {
                method: 'PUT',
                body: { analisi_ai: sopralluogo.analisi_ai, note_tecnico: sopralluogo.note_tecnico },
            });
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/api/sopralluoghi/${sopralluogo.sopralluogo_id}/pdf`,
                { credentials: 'include' }
            );
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || 'Errore generazione PDF');
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Perizia_${sopralluogo.document_number?.replace('/', '-') || 'SOP'}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('PDF scaricato');
        } catch (err) {
            toast.error(err.message, { duration: 8000 });
        } finally {
            setGeneratingPdf(false);
        }
    };

    const handleGeneratePreventivo = async () => {
        setGeneratingPrev(true);
        try {
            // Save confirmed risks first
            await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}`, {
                method: 'PUT',
                body: { analisi_ai: sopralluogo.analisi_ai },
            });
            const result = await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}/genera-preventivo?variante=${selectedVariant}`, { method: 'POST' });
            toast.success(result.message);
            navigate(`/preventivi/${result.preventivo.preventivo_id}`);
        } catch (err) {
            toast.error(err.message, { duration: 8000 });
        } finally {
            setGeneratingPrev(false);
        }
    };

    const generateEmailTemplate = () => {
        if (!sopralluogo || !analisi) return;
        const conf = analisi.conformita_percentuale || 0;
        const docNum = sopralluogo.document_number || '';
        const indirizzo = sopralluogo.indirizzo || '';
        const clientName = clients.find(c => c.client_id === sopralluogo.client_id)?.business_name || 'Cliente';
        const createdDate = sopralluogo.created_at?.substring(0, 10)?.split('-').reverse().join('/') || '';

        // Determine urgency based on conformity
        const isUrgent = conf < 40;
        const isWarning = conf >= 40 && conf < 65;

        // Build subject
        const urgentTag = isUrgent ? 'URGENTE - ' : isWarning ? 'ATTENZIONE - ' : '';
        const subject = `${urgentTag}Esito Perizia Tecnica Cancello ${indirizzo}`;

        // Build variant prices summary
        const varianti = analisi.varianti || {};
        const priceLines = ['A', 'B', 'C'].map(k => {
            const v = varianti[k];
            if (!v) return null;
            const cost = v.costo_stimato > 0 ? `${v.costo_stimato.toLocaleString('it-IT')}\u20AC` : 'da quotare';
            return `   ${k}) ${v.titolo || 'Variante ' + k}: ${cost}`;
        }).filter(Boolean).join('\n');

        // Find critical missing devices
        const mancanti = (analisi.dispositivi_mancanti || []).slice(0, 3).join(', ').toLowerCase();

        // Determine variant page number (approximate)
        const variantPage = analisi.rischi?.length > 3 ? '7' : '6';

        let body = '';
        if (isUrgent) {
            body = `Gentile ${clientName},

Le invio in allegato la perizia tecnica (${docNum}) relativa al sopralluogo effettuato il ${createdDate} presso ${indirizzo}.

Purtroppo l'impianto ha un indice di conformita di solo il ${conf}%.

Data la gravita delle carenze rilevate${mancanti ? ` (${mancanti})` : ''}, Le segnalo che si trova in una situazione di "Colpa Grave" ai sensi dell'Art. 2051 C.C.

Cosa comporta:

- Rischio Penale: In caso di infortunio, la responsabilita e diretta.
- Rischio Assicurativo: La polizza fabbricati potrebbe non coprire i danni per impianti non a norma.

A pagina ${variantPage} della perizia trovera le 3 opzioni di adeguamento:
${priceLines}

Resto a disposizione per un incontro e illustrare la soluzione piu idonea per mettere in sicurezza l'impianto.

Cordiali saluti`;
        } else if (isWarning) {
            body = `Gentile ${clientName},

Le invio in allegato la perizia tecnica (${docNum}) relativa al sopralluogo effettuato il ${createdDate} presso ${indirizzo}.

L'impianto presenta un indice di conformita del ${conf}%, con alcune carenze${mancanti ? ` (${mancanti})` : ''} che richiedono attenzione.

Le ricordo che ai sensi dell'Art. 2051 C.C., il proprietario e responsabile della sicurezza dell'impianto.

A pagina ${variantPage} della perizia trovera le 3 opzioni di intervento:
${priceLines}

Consiglio di procedere con l'adeguamento per garantire la sicurezza dell'impianto e la conformita normativa.

Resto a disposizione per qualsiasi chiarimento.

Cordiali saluti`;
        } else {
            body = `Gentile ${clientName},

Le invio in allegato la perizia tecnica (${docNum}) relativa al sopralluogo effettuato il ${createdDate} presso ${indirizzo}.

L'impianto risulta in buono stato di conformita (${conf}%).

A pagina ${variantPage} della perizia trovera eventuali suggerimenti migliorativi:
${priceLines}

Resto a disposizione per qualsiasi chiarimento.

Cordiali saluti`;
        }

        setEmailSubject(subject);
        setEmailBody(body);
        setShowEmailConfirm(true);
    };

    const handleSendEmail = async () => {
        setSendingEmail(true);
        try {
            await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}`, {
                method: 'PUT',
                body: { analisi_ai: sopralluogo.analisi_ai, note_tecnico: sopralluogo.note_tecnico },
            });
            const result = await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}/invia-email`, {
                method: 'POST',
                body: { subject: emailSubject, body: emailBody },
            });
            toast.success(result.message || 'Perizia inviata via email!');
            setShowEmailConfirm(false);
        } catch (err) {
            toast.error(err.message || 'Errore invio email');
        } finally {
            setSendingEmail(false);
        }
    };

    const analisi = sopralluogo?.analisi_ai;
    const foto = sopralluogo?.foto || [];
    const canProceedToFoto = sopralluogo?.sopralluogo_id;
    const canAnalyze = foto.length > 0;
    const canGenerate = analisi?.rischi?.length > 0;

    return (
        <div className="max-w-4xl mx-auto pb-24">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <Button variant="ghost" size="sm" onClick={() => navigate('/sopralluoghi')} data-testid="btn-back">
                    <ArrowLeft className="h-4 w-4 mr-1" /> Indietro
                </Button>
                <h1 className="text-xl font-bold text-gray-900">
                    {isEditing ? `Sopralluogo ${sopralluogo?.document_number || ''}` : 'Nuovo Sopralluogo'}
                </h1>
                {sopralluogo?.status && (
                    <Badge variant="outline" className={
                        sopralluogo.status === 'completato' ? 'bg-green-50 text-green-700' :
                        sopralluogo.status === 'analizzato' ? 'bg-blue-50 text-blue-700' :
                        'bg-gray-50 text-gray-700'
                    }>{sopralluogo.status}</Badge>
                )}
            </div>

            {/* Step Indicator */}
            <div className="flex items-center gap-1 mb-8 overflow-x-auto pb-2" data-testid="step-indicator">
                {STEPS.map((s, i) => {
                    const Icon = s.icon;
                    const isActive = i === step;
                    const isDone = i < step;
                    return (
                        <button
                            key={s.id}
                            onClick={() => {
                                if (i <= 1 || (i === 2 && canProceedToFoto) || (i === 3 && analisi)) setStep(i);
                            }}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap
                                ${isActive ? 'bg-[#0055FF] text-white shadow-md' : isDone ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}
                        >
                            <Icon className="h-4 w-4" />
                            <span className="hidden sm:inline">{s.label}</span>
                            {isDone && <CheckCircle2 className="h-3.5 w-3.5" />}
                        </button>
                    );
                })}
            </div>

            {/* STEP 0: Cliente & Luogo */}
            {step === 0 && (
                <Card>
                    <CardHeader className="bg-blue-50 border-b">
                        <CardTitle className="text-lg flex items-center gap-2"><User className="h-5 w-5" /> Dati Sopralluogo</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                        <div>
                            <Label>Cliente</Label>
                            <div className="flex gap-2">
                                <div className="flex-1">
                                    <Select value={formData.client_id || '__none__'} onValueChange={v => setFormData(p => ({ ...p, client_id: v === '__none__' ? '' : v }))}>
                                        <SelectTrigger data-testid="select-client"><SelectValue placeholder="Seleziona cliente..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">-- Nessun cliente --</SelectItem>
                                            {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => setShowQuickClient(true)}
                                    className="border-blue-300 text-blue-600 hover:bg-blue-50 shrink-0"
                                    data-testid="btn-quick-create-client"
                                >
                                    <UserPlus className="h-4 w-4 mr-1" /> Nuovo
                                </Button>
                            </div>
                            <ClientQuickCreateModal
                                open={showQuickClient}
                                onOpenChange={setShowQuickClient}
                                onCreated={(newClient) => {
                                    setClients(prev => [...prev, newClient].sort((a, b) => a.business_name.localeCompare(b.business_name)));
                                    setFormData(p => ({ ...p, client_id: newClient.client_id }));
                                }}
                            />
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="sm:col-span-2">
                                <Label>Indirizzo Sopralluogo</Label>
                                <Input data-testid="input-indirizzo" value={formData.indirizzo} onChange={e => setFormData(p => ({ ...p, indirizzo: e.target.value }))} placeholder="Via Roma 1" />
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <Label>Comune</Label>
                                    <Input value={formData.comune} onChange={e => setFormData(p => ({ ...p, comune: e.target.value }))} placeholder="Bologna" />
                                </div>
                                <div>
                                    <Label>Prov.</Label>
                                    <Input value={formData.provincia} onChange={e => setFormData(p => ({ ...p, provincia: e.target.value }))} placeholder="BO" maxLength={2} />
                                </div>
                            </div>
                        </div>
                        {/* Tipo Perizia Card Grid */}
                        <div>
                            <Label className="mb-2 block">Tipologia Perizia</Label>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="tipo-perizia-grid">
                                {TIPO_PERIZIA_OPTIONS.map(opt => {
                                    const Icon = opt.icon;
                                    const isSelected = formData.tipo_perizia === opt.value;
                                    return (
                                        <button
                                            key={opt.value}
                                            type="button"
                                            onClick={() => setFormData(p => ({ ...p, tipo_perizia: opt.value }))}
                                            data-testid={`tipo-perizia-${opt.value}`}
                                            className={`relative text-left rounded-xl border-2 p-4 transition-all ${
                                                isSelected
                                                    ? `${opt.borderColor} ${opt.bgColor} shadow-md ring-2 ring-offset-1 ring-blue-200`
                                                    : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                                            }`}
                                        >
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-2 bg-gradient-to-br ${opt.color} text-white`}>
                                                <Icon className="h-5 w-5" />
                                            </div>
                                            <div className="font-semibold text-sm text-gray-900">{opt.label}</div>
                                            <div className="text-[11px] font-mono text-gray-500 mt-0.5">{opt.norm}</div>
                                            <div className="text-xs text-gray-400 mt-1">{opt.description}</div>
                                            {isSelected && (
                                                <div className="absolute top-2 right-2">
                                                    <CheckCircle2 className="h-5 w-5 text-blue-600" />
                                                </div>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                        <div>
                            <Label>Tipo Intervento</Label>
                            <Select value={formData.tipo_intervento} onValueChange={v => setFormData(p => ({ ...p, tipo_intervento: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="messa_a_norma">Messa a Norma (EN 12453)</SelectItem>
                                    <SelectItem value="manutenzione">Manutenzione Ordinaria</SelectItem>
                                    <SelectItem value="nuova_installazione">Nuova Installazione</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label>Descrizione / Note dal Sopralluogo</Label>
                            <Textarea
                                data-testid="input-descrizione"
                                value={formData.descrizione_utente}
                                onChange={e => setFormData(p => ({ ...p, descrizione_utente: e.target.value }))}
                                placeholder={
                                    formData.tipo_perizia === 'barriere'
                                        ? "Es: Scala condominiale senza corrimano, ingresso con gradino alto..."
                                        : formData.tipo_perizia === 'strutture'
                                        ? "Es: Tettoia in ferro con segni di corrosione, soppalco con bulloni allentati..."
                                        : "Es: Cancello scorrevole vecchio, cliente lamenta rumori anomali..."
                                }
                                rows={3}
                            />
                        </div>
                        <div className="flex justify-end pt-2">
                            <Button
                                data-testid="btn-save-step1"
                                onClick={async () => { await handleSave(); setStep(1); }}
                                disabled={saving}
                                className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                            >
                                {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                Salva e Continua <ArrowRight className="h-4 w-4 ml-2" />
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* STEP 1: Foto */}
            {step === 1 && (
                <div className="space-y-4">
                    <Card>
                        <CardHeader className="bg-blue-50 border-b">
                            <CardTitle className="text-lg flex items-center gap-2"><Camera className="h-5 w-5" /> Foto Sopralluogo</CardTitle>
                        </CardHeader>
                        <CardContent className="p-6">
                            <p className="text-sm text-gray-600 mb-4">
                                {formData.tipo_perizia === 'barriere'
                                    ? "Scatta o carica foto dell'accesso: scala, rampa, corrimano, porta, pavimentazione, spazi di manovra."
                                    : formData.tipo_perizia === 'strutture'
                                    ? "Scatta o carica foto della struttura: saldature, bulloneria, controventi, piastre di base, corrosione, panoramica."
                                    : "Scatta o carica foto del cancello: motore, guide, punto di chiusura, dispositivi di sicurezza, panoramica."
                                }
                            </p>
                            <div className="flex gap-3 flex-wrap">
                                <label className="cursor-pointer">
                                    <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={handleUploadPhoto} className="hidden" data-testid="file-upload" />
                                    <div className="flex items-center gap-2 px-4 py-2 border-2 border-dashed border-blue-300 rounded-lg text-blue-600 hover:bg-blue-50 transition">
                                        {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                                        Carica Foto
                                    </div>
                                </label>
                                <label className="cursor-pointer sm:hidden">
                                    <input type="file" accept="image/*" capture="environment" onChange={handleUploadPhoto} className="hidden" />
                                    <div className="flex items-center gap-2 px-4 py-2 border-2 border-dashed border-green-300 rounded-lg text-green-600 hover:bg-green-50 transition">
                                        <Camera className="h-4 w-4" /> Scatta Foto
                                    </div>
                                </label>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Photo Grid */}
                    {foto.length > 0 && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                            {foto.map((f) => (
                                <Card key={f.foto_id} className="overflow-hidden">
                                    <div className="relative aspect-square bg-gray-100">
                                        {photoUrls[f.foto_id] ? (
                                            <img src={photoUrls[f.foto_id]} alt={f.label} className="w-full h-full object-cover" />
                                        ) : (
                                            <div className="flex items-center justify-center h-full">
                                                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                                            </div>
                                        )}
                                        <button
                                            onClick={() => handleDeletePhoto(f.foto_id)}
                                            className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 shadow"
                                            data-testid={`btn-delete-foto-${f.foto_id}`}
                                        >
                                            <X className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                    <div className="p-2">
                                        <Select value={f.label || 'panoramica'} onValueChange={v => handleUpdateLabel(f.foto_id, v)}>
                                            <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                {FOTO_LABELS.map(l => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    )}

                    <div className="flex justify-between pt-2">
                        <Button variant="outline" onClick={() => setStep(0)}><ArrowLeft className="h-4 w-4 mr-1" /> Indietro</Button>
                        <Button
                            data-testid="btn-go-analyze"
                            onClick={() => setStep(2)}
                            disabled={!canAnalyze}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            Vai all'Analisi <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                    </div>
                </div>
            )}

            {/* STEP 2: Analisi AI */}
            {step === 2 && (
                <Card>
                    <CardHeader className="bg-gradient-to-r from-purple-50 to-blue-50 border-b">
                        <CardTitle className="text-lg flex items-center gap-2"><Brain className="h-5 w-5 text-purple-600" /> Analisi Intelligente</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 text-center space-y-6">
                        <div className="max-w-md mx-auto">
                            <div className="flex justify-center gap-2 mb-4">
                                {foto.slice(0, 4).map(f => (
                                    <div key={f.foto_id} className="w-16 h-16 rounded-lg bg-gray-100 overflow-hidden">
                                        {photoUrls[f.foto_id] && <img src={photoUrls[f.foto_id]} alt="" className="w-full h-full object-cover" />}
                                    </div>
                                ))}
                                {foto.length > 4 && <div className="w-16 h-16 rounded-lg bg-gray-200 flex items-center justify-center text-gray-500 text-sm">+{foto.length - 4}</div>}
                            </div>
                            <p className="text-gray-600 mb-2">
                                <strong>{foto.length} foto</strong> pronte per l'analisi
                            </p>
                            <p className="text-sm text-gray-500 mb-6">
                                {formData.tipo_perizia === 'barriere'
                                    ? "L'AI analizzerà le foto per identificare barriere architettoniche e non conformità secondo il D.M. 236/89."
                                    : formData.tipo_perizia === 'strutture'
                                    ? "L'AI analizzerà le foto per identificare criticità strutturali e non conformità secondo le NTC 2018 / EN 1090."
                                    : "L'AI analizzerà le foto per identificare rischi di sicurezza, dispositivi mancanti e interventi necessari secondo la normativa EN 12453."
                                }
                            </p>
                            {analyzing ? (
                                <div className="py-8">
                                    <Loader2 className="h-12 w-12 animate-spin text-purple-500 mx-auto mb-4" />
                                    <p className="text-lg font-medium text-purple-700">Analisi in corso...</p>
                                    <p className="text-sm text-gray-500 mt-1">GPT-4o sta esaminando le foto</p>
                                </div>
                            ) : (
                                <Button
                                    data-testid="btn-analyze"
                                    onClick={handleAnalyze}
                                    size="lg"
                                    className="bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700 shadow-lg px-8"
                                >
                                    <Brain className="h-5 w-5 mr-2" /> Analizza con AI
                                </Button>
                            )}
                        </div>
                        <div className="flex justify-start pt-4">
                            <Button variant="outline" onClick={() => setStep(1)}><ArrowLeft className="h-4 w-4 mr-1" /> Torna alle Foto</Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* STEP 3: Risultati */}
            {step === 3 && analisi && (
                <div className="space-y-4">
                    {/* Summary Card */}
                    <Card className="border-l-4 border-l-blue-500">
                        <CardContent className="p-4">
                            <div className="flex flex-wrap items-center gap-4">
                                <div>
                                    <p className="text-sm text-gray-500">Tipo Chiusura</p>
                                    <p className="font-semibold capitalize">{analisi.tipo_chiusura?.replace('_', ' ')}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500">Conformità</p>
                                    <p className={`text-2xl font-bold ${analisi.conformita_percentuale < 40 ? 'text-red-600' : analisi.conformita_percentuale < 70 ? 'text-amber-600' : 'text-green-600'}`}>
                                        {analisi.conformita_percentuale}%
                                    </p>
                                </div>
                                <div className="flex-1">
                                    <p className="text-sm text-gray-500">Descrizione</p>
                                    <p className="text-sm">{analisi.descrizione_generale}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Risks */}
                    <Card>
                        <CardHeader className="bg-red-50 border-b pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <ShieldAlert className="h-5 w-5 text-red-600" />
                                Criticità Riscontrate ({analisi.rischi?.length || 0})
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0 divide-y">
                            {(analisi.rischi || []).map((r, i) => (
                                <div
                                    key={i}
                                    className={`p-4 flex gap-3 transition ${r.confermato !== false ? '' : 'opacity-40'}`}
                                    data-testid={`rischio-${i}`}
                                >
                                    <button onClick={() => handleToggleRischio(i)} className="mt-1 shrink-0">
                                        {r.confermato !== false ? (
                                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                                        ) : (
                                            <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
                                        )}
                                    </button>
                                    <div className="flex-1 min-w-0 space-y-2">
                                        <div className="flex items-start gap-2 flex-wrap">
                                            <Badge className={GRAVITA_COLORS[r.gravita] || GRAVITA_COLORS.media}>{r.gravita?.toUpperCase()}</Badge>
                                            <span className="text-xs text-gray-500 font-mono">{r.norma_riferimento}</span>
                                        </div>
                                        <p className="font-semibold text-sm text-gray-900">{r.zona}</p>
                                        <div>
                                            <label className="text-xs text-gray-400 uppercase tracking-wide">Problema</label>
                                            <Textarea
                                                value={r.problema || ''}
                                                onChange={e => handleEditRischio(i, 'problema', e.target.value)}
                                                rows={2}
                                                className="mt-0.5 text-sm bg-gray-50 border-gray-200 focus:bg-white"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-green-600 uppercase tracking-wide flex items-center gap-1"><Wrench className="h-3 w-3" /> Soluzione</label>
                                            <Textarea
                                                value={r.soluzione || ''}
                                                onChange={e => handleEditRischio(i, 'soluzione', e.target.value)}
                                                rows={2}
                                                className="mt-0.5 text-sm bg-green-50 border-green-200 focus:bg-white"
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    {/* Dispositivi */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-green-700 flex items-center gap-1"><CheckCircle2 className="h-4 w-4" /> Dispositivi Presenti</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <ul className="space-y-1">
                                    {(analisi.dispositivi_presenti || []).map((d, i) => (
                                        <li key={i} className="text-sm flex items-center gap-2"><CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />{d}</li>
                                    ))}
                                    {!analisi.dispositivi_presenti?.length && <li className="text-sm text-gray-400">Nessuno rilevato</li>}
                                </ul>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-red-700 flex items-center gap-1"><AlertTriangle className="h-4 w-4" /> Dispositivi Mancanti</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <ul className="space-y-1">
                                    {(analisi.dispositivi_mancanti || []).map((d, i) => (
                                        <li key={i} className="text-sm flex items-center gap-2"><AlertTriangle className="h-3 w-3 text-red-500 shrink-0" />{d}</li>
                                    ))}
                                    {!analisi.dispositivi_mancanti?.length && <li className="text-sm text-gray-400">Nessuno</li>}
                                </ul>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Materials */}
                    {analisi.materiali_suggeriti?.length > 0 && (
                        <Card>
                            <CardHeader className="bg-amber-50 border-b pb-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Wrench className="h-5 w-5 text-amber-600" />
                                    Materiali Suggeriti ({analisi.materiali_suggeriti.length})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <table className="w-full text-sm">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="text-left p-3">Materiale</th>
                                            <th className="text-center p-3">Q.tà</th>
                                            <th className="text-center p-3">Priorità</th>
                                            <th className="text-right p-3">Prezzo</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y">
                                        {analisi.materiali_suggeriti.map((m, i) => (
                                            <tr key={i}>
                                                <td className="p-3">
                                                    <Input
                                                        value={m.descrizione_catalogo || m.descrizione || ''}
                                                        onChange={e => handleEditMateriale(i, 'descrizione_catalogo', e.target.value)}
                                                        className="text-sm h-8 bg-gray-50 focus:bg-white"
                                                    />
                                                    <p className="text-xs text-gray-400 mt-0.5">keyword: {m.keyword}</p>
                                                </td>
                                                <td className="text-center p-3">
                                                    <Input
                                                        type="number"
                                                        value={m.quantita}
                                                        onChange={e => handleEditMateriale(i, 'quantita', parseInt(e.target.value) || 1)}
                                                        className="text-sm h-8 w-16 text-center mx-auto"
                                                        min={1}
                                                    />
                                                </td>
                                                <td className="text-center p-3">
                                                    <Badge variant="outline" className={m.priorita === 'obbligatorio' ? 'border-red-200 text-red-700' : 'border-gray-200'}>{m.priorita}</Badge>
                                                </td>
                                                <td className="text-right p-3">
                                                    <Input
                                                        type="number"
                                                        value={m.prezzo || 0}
                                                        onChange={e => handleEditMateriale(i, 'prezzo', parseFloat(e.target.value) || 0)}
                                                        className="text-sm h-8 w-24 text-right ml-auto font-mono"
                                                        step={0.01}
                                                    />
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </CardContent>
                        </Card>
                    )}

                    {/* Varianti di Intervento (A/B/C) — Editabili */}
                    {analisi.varianti && Object.keys(analisi.varianti).length > 0 && (
                        <Card data-testid="varianti-section">
                            <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b pb-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    <FileText className="h-5 w-5 text-blue-600" />
                                    Proposte di Intervento
                                    <span className="text-xs font-normal text-gray-400 ml-auto">Modifica prezzi e voci prima di inviare</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 space-y-3">
                                {['A', 'B', 'C'].map(key => {
                                    const v = analisi.varianti[key];
                                    if (!v) return null;
                                    const isSelected = selectedVariant === key;
                                    const colors = {
                                        A: { border: 'border-amber-300', bg: 'bg-amber-50' },
                                        B: { border: 'border-blue-400', bg: 'bg-blue-50' },
                                        C: { border: 'border-purple-300', bg: 'bg-purple-50' },
                                    }[key];
                                    const updateVariant = (field, value) => {
                                        setSopralluogo(prev => ({
                                            ...prev,
                                            analisi_ai: {
                                                ...prev.analisi_ai,
                                                varianti: {
                                                    ...prev.analisi_ai.varianti,
                                                    [key]: { ...prev.analisi_ai.varianti[key], [field]: value }
                                                }
                                            }
                                        }));
                                    };
                                    const addIntervento = () => {
                                        const newItem = prompt('Aggiungi voce intervento:');
                                        if (newItem?.trim()) {
                                            updateVariant('interventi', [...(v.interventi || []), newItem.trim()]);
                                        }
                                    };
                                    const removeIntervento = (idx) => {
                                        updateVariant('interventi', (v.interventi || []).filter((_, i) => i !== idx));
                                    };
                                    return (
                                        <div
                                            key={key}
                                            data-testid={`variant-${key}`}
                                            className={`border-2 rounded-xl overflow-hidden transition-all ${
                                                isSelected ? `${colors.border} ${colors.bg} shadow-md ring-2 ring-offset-1 ring-blue-200` : 'border-gray-200'
                                            }`}
                                        >
                                            <button
                                                onClick={() => setSelectedVariant(key)}
                                                className="w-full text-left p-4"
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div className="flex items-center gap-3">
                                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg font-black ${
                                                            isSelected ? 'bg-[#0B1F3A] text-white' : 'bg-gray-200 text-gray-600'
                                                        }`}>{key}</div>
                                                        <div>
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-bold text-sm text-gray-900">{v.titolo || `Variante ${key}`}</span>
                                                                {key === 'B' && <Badge className="bg-blue-600 text-white text-[10px] px-1.5 py-0">Consigliato</Badge>}
                                                            </div>
                                                            <p className="text-xs text-gray-500 mt-0.5">{v.descrizione}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </button>
                                            {isSelected && (
                                                <div className="px-4 pb-4 space-y-3 border-t pt-3">
                                                    {/* Prezzo editabile */}
                                                    <div className="flex items-center gap-3">
                                                        <Label className="text-xs font-semibold text-gray-600 w-24">Prezzo (IVA escl.)</Label>
                                                        <div className="relative flex-1 max-w-[180px]">
                                                            <Input
                                                                type="number"
                                                                value={v.costo_stimato || ''}
                                                                onChange={e => updateVariant('costo_stimato', parseFloat(e.target.value) || 0)}
                                                                className="pr-8 text-right font-bold"
                                                                data-testid={`variant-${key}-price`}
                                                            />
                                                            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">&euro;</span>
                                                        </div>
                                                    </div>
                                                    {/* Lista interventi editabile */}
                                                    <div>
                                                        <div className="flex items-center justify-between mb-1.5">
                                                            <Label className="text-xs font-semibold text-gray-600">Interventi inclusi</Label>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={addIntervento}
                                                                className="h-6 text-xs text-blue-600"
                                                                data-testid={`variant-${key}-add-item`}
                                                            >+ Aggiungi voce</Button>
                                                        </div>
                                                        <ul className="space-y-1">
                                                            {(v.interventi || []).map((item, i) => (
                                                                <li key={i} className="flex items-center gap-1.5 text-xs text-gray-600 group">
                                                                    <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />
                                                                    <span className="flex-1">{item}</span>
                                                                    <button
                                                                        onClick={() => removeIntervento(i)}
                                                                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600"
                                                                    ><X className="h-3 w-3" /></button>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                    {/* Stima Manodopera */}
                                                    {v.stima_manodopera && (
                                                        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-dashed">
                                                            <Label className="text-xs font-semibold text-gray-500 w-24">Manodopera</Label>
                                                            <span className="text-xs text-gray-600">{v.stima_manodopera}</span>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                                <p className="text-xs text-gray-400 text-center pt-1">
                                    Seleziona e personalizza la variante. Il cliente vedra i prezzi indicati.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Rischi Residui */}
                    {analisi.rischi_residui?.length > 0 && (
                        <Card className="border-amber-200 bg-amber-50/50" data-testid="rischi-residui-section">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-amber-800 flex items-center gap-1">
                                    <AlertTriangle className="h-4 w-4" /> Rischi Residui (post-adeguamento)
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-xs text-gray-500 mb-2">Rischi minimi che permangono anche dopo l'intervento completo:</p>
                                <ul className="space-y-1.5">
                                    {analisi.rischi_residui.map((r, i) => (
                                        <li key={i} className="flex items-start gap-2 text-xs text-amber-900">
                                            <AlertTriangle className="h-3 w-3 text-amber-500 mt-0.5 shrink-0" />
                                            {r}
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>
                        </Card>
                    )}

                    {/* Testo Sintetico Fattura */}
                    {analisi.testo_sintetico_fattura && (
                        <Card data-testid="testo-sintetico-section">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-indigo-700 flex items-center gap-1"><FileText className="h-4 w-4" /> Testo per Preventivo/Fattura</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Textarea
                                    value={analisi.testo_sintetico_fattura || ''}
                                    onChange={e => setSopralluogo(prev => ({
                                        ...prev,
                                        analisi_ai: { ...prev.analisi_ai, testo_sintetico_fattura: e.target.value }
                                    }))}
                                    rows={2}
                                    className="text-sm bg-indigo-50 border-indigo-200 focus:bg-white"
                                    data-testid="input-testo-sintetico"
                                />
                                <p className="text-xs text-gray-400 mt-1">Questo testo viene usato come voce sintetica nel preventivo generato.</p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Notes */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm text-blue-800 flex items-center gap-1"><FileText className="h-4 w-4" /> Note</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <div>
                                <label className="text-xs text-gray-400 uppercase tracking-wide">Note AI (editabili)</label>
                                <Textarea
                                    value={analisi.note_tecniche || ''}
                                    onChange={e => setSopralluogo(prev => ({
                                        ...prev,
                                        analisi_ai: { ...prev.analisi_ai, note_tecniche: e.target.value }
                                    }))}
                                    rows={2}
                                    className="mt-0.5 text-sm bg-blue-50 border-blue-200"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-gray-400 uppercase tracking-wide">Note Tecnico (tue osservazioni)</label>
                                <Textarea
                                    data-testid="input-note-tecnico"
                                    value={sopralluogo.note_tecnico || ''}
                                    onChange={e => setSopralluogo(prev => ({ ...prev, note_tecnico: e.target.value }))}
                                    rows={2}
                                    placeholder="Aggiungi le tue osservazioni personali..."
                                    className="mt-0.5 text-sm"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-3 justify-between pt-2">
                        <Button variant="outline" onClick={() => setStep(2)}>
                            <Brain className="h-4 w-4 mr-1" /> Ri-Analizza
                        </Button>
                        <div className="flex gap-3 flex-wrap">
                            <Button
                                variant="outline"
                                onClick={async () => {
                                    try {
                                        await apiRequest(`/sopralluoghi/${sopralluogo.sopralluogo_id}`, {
                                            method: 'PUT',
                                            body: { analisi_ai: sopralluogo.analisi_ai, note_tecnico: sopralluogo.note_tecnico },
                                        });
                                        toast.success('Modifiche salvate');
                                    } catch (err) { toast.error(err.message); }
                                }}
                                data-testid="btn-save-edits"
                            >
                                <CheckCircle2 className="h-4 w-4 mr-1" /> Salva Modifiche
                            </Button>
                            <Button
                                data-testid="btn-download-pdf"
                                onClick={handleDownloadPdf}
                                disabled={generatingPdf}
                                variant="outline"
                                className="border-blue-300 text-blue-700 hover:bg-blue-50"
                            >
                                {generatingPdf ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                                Scarica PDF Perizia
                            </Button>
                            <Button
                                data-testid="btn-send-email"
                                onClick={generateEmailTemplate}
                                variant="outline"
                                className="border-orange-300 text-orange-700 hover:bg-orange-50"
                            >
                                <Mail className="h-4 w-4 mr-2" />
                                Invia via Email
                            </Button>
                            <Button
                                data-testid="btn-generate-preventivo"
                                onClick={handleGeneratePreventivo}
                                disabled={generatingPrev || !canGenerate}
                                className="bg-green-600 text-white hover:bg-green-700"
                            >
                                {generatingPrev ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileText className="h-4 w-4 mr-2" />}
                                Preventivo (Var. {selectedVariant})
                            </Button>
                        </div>
                    </div>

                    {/* Email Preview & Send Panel */}
                    {showEmailConfirm && (
                        <Card className="border-2 border-orange-400 shadow-lg" data-testid="email-confirm-dialog">
                            <CardHeader className="bg-gradient-to-r from-orange-50 to-amber-50 border-b pb-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Mail className="h-5 w-5 text-orange-600" />
                                    Anteprima Email — Perizia {sopralluogo.document_number}
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setShowEmailConfirm(false)}
                                        className="ml-auto h-7 w-7 p-0"
                                    ><X className="h-4 w-4" /></Button>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 space-y-4">
                                {/* Subject */}
                                <div>
                                    <Label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Oggetto</Label>
                                    <Input
                                        value={emailSubject}
                                        onChange={e => setEmailSubject(e.target.value)}
                                        className="mt-1 font-semibold"
                                        data-testid="email-subject-input"
                                    />
                                </div>
                                {/* Body */}
                                <div>
                                    <Label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Corpo del Messaggio</Label>
                                    <Textarea
                                        value={emailBody}
                                        onChange={e => setEmailBody(e.target.value)}
                                        rows={16}
                                        className="mt-1 text-sm font-mono leading-relaxed"
                                        data-testid="email-body-input"
                                    />
                                </div>
                                <p className="text-xs text-gray-400">
                                    Il PDF della perizia verra allegato automaticamente. Modifica il testo come preferisci prima dell'invio.
                                </p>
                                {/* Actions */}
                                <div className="flex items-center gap-3 pt-2 border-t">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleDownloadPdf}
                                        disabled={generatingPdf}
                                        className="border-blue-300 text-blue-700"
                                        data-testid="email-preview-download-pdf"
                                    >
                                        {generatingPdf ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Download className="h-4 w-4 mr-1" />}
                                        Scarica PDF (Anteprima)
                                    </Button>
                                    <div className="flex-1" />
                                    <Button variant="outline" size="sm" onClick={() => setShowEmailConfirm(false)}>
                                        Annulla
                                    </Button>
                                    <Button
                                        onClick={handleSendEmail}
                                        disabled={sendingEmail || !emailSubject.trim() || !emailBody.trim()}
                                        className="bg-orange-600 text-white hover:bg-orange-700"
                                        size="sm"
                                        data-testid="btn-confirm-send-email"
                                    >
                                        {sendingEmail ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Mail className="h-4 w-4 mr-2" />}
                                        Invia Email con PDF Allegato
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            )}
        </div>
    );
}
