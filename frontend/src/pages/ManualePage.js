/**
 * ManualePage — Guida all'Uso interattiva + download PDF.
 * Mostra capitoli navigabili, FAQ con ricerca, e pulsante genera PDF.
 */
import { useState, useEffect, useMemo } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
    BookOpen, Download, Loader2, Search, ChevronDown, ChevronRight,
    Info, Calculator, Briefcase, Shield, Users, ClipboardCheck, BarChart3,
    HelpCircle, FileText,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
    info: Info, calculator: Calculator, briefcase: Briefcase,
    shield: Shield, users: Users, clipboard: ClipboardCheck, chart: BarChart3,
};

const CAPITOLI_COMPLETI = [
    {
        id: 'intro', titolo: 'Introduzione', icona: 'info',
        contenuto: [
            'Benvenuto nel sistema gestionale per carpenteria metallica conforme alle normative EN 1090, EN 13241 e ISO 3834.',
            'Questo manuale descrive tutte le funzionalita del software, dalla gestione commerciale alla tracciabilita dei materiali.',
            { subtitle: 'A chi e rivolto', items: ['Titolari e responsabili di officina', 'Responsabili commerciali e preventivisti', 'Responsabili della qualita e sicurezza', 'Operai e capi squadra (modulo Officina)'] },
        ],
    },
    {
        id: 'preventivi', titolo: 'Gestione Preventivi', icona: 'calculator',
        contenuto: [
            { subtitle: 'Creazione Preventivo Manuale', items: ['Dalla barra laterale, clicca su Commerciale → Preventivi', 'Clicca Nuovo Preventivo', 'Compila: cliente, oggetto, normativa (EN 1090 / EN 13241), classe di esecuzione', 'Aggiungi le voci di lavoro con peso, prezzo unitario e margine', 'Clicca Salva per creare il preventivo in stato Bozza'] },
            { subtitle: 'Preventivatore Predittivo AI', items: ['Vai su Commerciale → AI Predittivo', 'Metodo 1 — Analisi Disegno: Carica un PDF o immagine del disegno tecnico', 'Metodo 2 — Stima Rapida: Inserisci peso stimato (kg) e tipologia struttura', 'Il sistema calcola ore, costi materiali e margini differenziati', 'Clicca Genera Preventivo per il documento ufficiale'] },
            { subtitle: 'Margini Differenziati', items: ['Materiali (default 25%): ricarico su acciaio, bulloneria, accessori', 'Manodopera (default 30%): ricarico su ore officina e montaggio', 'Conto Lavoro (default 20%): ricarico su zincatura, verniciatura'] },
        ],
    },
    {
        id: 'commesse', titolo: 'Gestione Commesse', icona: 'briefcase',
        contenuto: [
            { subtitle: 'Creazione Commessa', items: ['Dalla lista preventivi, clicca Accetta su un preventivo approvato', 'Il sistema crea automaticamente la commessa con tutti i dati', 'In alternativa, vai su Produzione → Commesse → Nuova Commessa'] },
            { subtitle: 'Hub Commessa', items: ['Banner Conformita: verifica automatica documenti aziendali', 'Voci di Lavoro: dettaglio lavorazioni con stato avanzamento', 'Diario di Produzione: registrazione ore e attivita', 'Pacco Documenti: generazione automatica del fascicolo sicurezza ZIP'] },
            'All\'apertura di una commessa, il sistema verifica che tutti i documenti siano validi per la durata dei lavori.',
        ],
    },
    {
        id: 'sicurezza', titolo: 'Sicurezza e Documenti', icona: 'shield',
        contenuto: [
            { subtitle: 'Documenti Aziendali', items: ['DURC — Documento Unico Regolarita Contributiva', 'Visura Camerale — Visura CCIAA aggiornata', 'White List — Iscrizione Prefettura', 'Patente a Crediti — INAIL', 'DVR — Documento Valutazione Rischi (D.Lgs 81/08)'] },
            'Per ogni documento puoi impostare la data di scadenza con il pulsante salva. Alert colorati: Verde = Valido (>30gg), Giallo = In scadenza (<30gg), Rosso = Scaduto.',
            { subtitle: 'Allegati Tecnici POS', items: ['Valutazione Rumore — D.Lgs 81/08 Titolo VIII', 'Valutazione Vibrazioni', 'Valutazione MMC — Movimentazione Manuale Carichi', 'Interruttore "Includi nel POS" per inclusione automatica nello ZIP'] },
        ],
    },
    {
        id: 'risorse_umane', titolo: 'Risorse Umane e Attestati', icona: 'users',
        contenuto: [
            { subtitle: 'Anagrafica Operai', items: ['Dati anagrafici e mansione', 'Patentini di saldatura (EN ISO 9606)', 'Attestati: Formazione Base, Primo Soccorso, Antincendio, Lavori in Quota, PLE, Carrellista, Visita Medica'] },
            { subtitle: 'Matrice Scadenze', items: ['Verde = Attestato valido', 'Giallo = In scadenza', 'Rosso = Scaduto', 'Grigio = Non presente'] },
            'Nel wizard POS (Step 4), puoi selezionare gli operai e il sistema controlla automaticamente gli attestati.',
        ],
    },
    {
        id: 'tracciabilita', titolo: 'Tracciabilita FPC (EN 1090)', icona: 'clipboard',
        contenuto: [
            { subtitle: 'Progetto FPC', items: ['Crea un progetto FPC collegato a una commessa', 'Definisci classe di esecuzione (EXC1-EXC4)', 'Registra lotti di materiale con N. Colata e certificati 3.1', 'Esegui controlli qualita (visivi, dimensionali, NDT)'] },
            { subtitle: 'Verbale di Posa in Opera', items: ['Dalla pagina FPC, clicca Genera Verbale', 'Compila: data installazione, metodo montaggio, condizioni meteo', 'I lotti EN 1090 vengono inseriti automaticamente', 'Aggiungi foto cantiere (drag-and-drop o scatto)', 'Firma cliente direttamente sullo schermo', 'Genera PDF per il documento ufficiale'] },
        ],
    },
    {
        id: 'dashboard', titolo: 'Dashboard e KPI', icona: 'chart',
        contenuto: [
            { subtitle: 'Cruscotto Officina', items: ['KPI: Fatturato, commesse attive, ore lavorate, efficienza', 'Conformita Documentale: stato documenti con previsione 30 giorni', 'Barre Avanzamento: % conformita per ogni commessa', 'Prossime Scadenze: alert documenti in scadenza'] },
            { subtitle: 'Dashboard KPI Avanzata', items: ['Andamento fatturato mensile', 'Distribuzione costi', 'Efficienza preventivi (tasso conversione)', 'Confronto stime AI vs valori reali'] },
        ],
    },
];

const FAQ_LIST = [
    { q: 'La data di scadenza non si salva. Cosa faccio?', a: 'Dopo aver inserito la data, clicca l\'icona del dischetto (salva) accanto al campo. La data si salva solo premendo il pulsante. Verifica che il documento sia stato prima caricato.' },
    { q: 'Come carico un nuovo patentino per un operaio?', a: 'Vai su Risorse Umane, seleziona l\'operaio, clicca Aggiungi Qualifica. Scegli il tipo, compila date e salva.' },
    { q: 'Il preventivo AI mostra tutto a zero?', a: 'Usa la Stima Rapida Manuale: inserisci peso (kg) e tipologia nello Step 1. Oppure carica un disegno tecnico chiaro.' },
    { q: 'Come includo gli allegati nel pacchetto sicurezza?', a: 'In Impostazioni → Documenti → Allegati Tecnici POS. Carica i file e attiva "Includi nel POS".' },
    { q: 'Il banner rosso dice "Conformita insufficiente"?', a: 'Clicca "Correggi documenti" per andare alle Impostazioni. Carica i documenti mancanti e imposta le scadenze.' },
    { q: 'Come genero il Verbale di Posa?', a: 'Apri la commessa → FPC/Tracciabilita → Genera Verbale. Compila dati, foto e firma su tablet.' },
    { q: 'Posso personalizzare il logo?', a: 'Si. Impostazioni → Logo → carica il logo. Apparira su tutti i PDF generati.' },
    { q: 'Come scarico il fascicolo aziendale?', a: 'Dashboard → widget Conformita → pulsante "Fascicolo". Scarica lo ZIP con tutti i documenti.' },
];

export default function ManualePage() {
    const [downloading, setDownloading] = useState(false);
    const [openChapter, setOpenChapter] = useState('intro');
    const [searchFaq, setSearchFaq] = useState('');

    const filteredFaq = useMemo(() => {
        if (!searchFaq.trim()) return FAQ_LIST;
        const s = searchFaq.toLowerCase();
        return FAQ_LIST.filter(f => f.q.toLowerCase().includes(s) || f.a.toLowerCase().includes(s));
    }, [searchFaq]);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const res = await fetch(`${API}/api/manuale/genera-pdf`, { credentials: 'include' });
            if (!res.ok) {
                const d = await res.json().catch(() => ({}));
                toast.error(d.detail || 'Errore generazione PDF');
                return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Manuale_Utente_${new Date().toISOString().split('T')[0]}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Manuale PDF generato e scaricato');
        } catch (e) { toast.error(e.message); }
        finally { setDownloading(false); }
    };

    const renderContent = (items) => items.map((item, i) => {
        if (typeof item === 'string') return <p key={i} className="text-sm text-slate-600 leading-relaxed mb-3">{item}</p>;
        if (item.subtitle) {
            return (
                <div key={i} className="mb-4">
                    <h4 className="text-sm font-bold text-[#0055FF] mb-1.5">{item.subtitle}</h4>
                    <ul className="space-y-1 ml-4">
                        {item.items.map((li, j) => (
                            <li key={j} className="text-sm text-slate-600 flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#0055FF] mt-2 shrink-0" />
                                {li}
                            </li>
                        ))}
                    </ul>
                </div>
            );
        }
        return null;
    });

    return (
        <DashboardLayout>
            <div className="max-w-5xl space-y-6" data-testid="manuale-page">
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="font-sans text-3xl font-bold text-slate-900 flex items-center gap-3">
                            <BookOpen className="h-8 w-8 text-[#0055FF]" />
                            Guida all'Uso
                        </h1>
                        <p className="text-slate-500 mt-1">Documentazione completa del sistema gestionale — v2.0</p>
                    </div>
                    <Button onClick={handleDownload} disabled={downloading}
                        className="bg-[#1E293B] hover:bg-[#334155] text-white h-11 px-6 gap-2" data-testid="btn-download-manuale">
                        {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        Scarica Manuale PDF
                    </Button>
                </div>

                {/* Chapters */}
                <div className="space-y-2" data-testid="chapters-list">
                    {CAPITOLI_COMPLETI.map((ch, idx) => {
                        const Icon = ICON_MAP[ch.icona] || Info;
                        const isOpen = openChapter === ch.id;
                        return (
                            <Card key={ch.id} className={`border transition-colors ${isOpen ? 'border-[#0055FF]/30 bg-white' : 'border-gray-200 bg-slate-50/50'}`}>
                                <button className="w-full flex items-center gap-3 px-5 py-3.5 text-left"
                                    onClick={() => setOpenChapter(isOpen ? null : ch.id)}
                                    data-testid={`chapter-${ch.id}`}>
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${isOpen ? 'bg-[#0055FF] text-white' : 'bg-slate-200 text-slate-500'}`}>
                                        <Icon className="h-4 w-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <span className="text-[10px] text-[#0055FF] font-semibold uppercase tracking-wider">Capitolo {idx + 1}</span>
                                        <h3 className="text-sm font-semibold text-slate-800">{ch.titolo}</h3>
                                    </div>
                                    {isOpen ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                                </button>
                                {isOpen && (
                                    <CardContent className="px-5 pb-5 pt-0 border-t border-slate-100">
                                        <div className="pt-4">{renderContent(ch.contenuto)}</div>
                                    </CardContent>
                                )}
                            </Card>
                        );
                    })}
                </div>

                {/* FAQ */}
                <Card className="border-amber-200" data-testid="faq-section">
                    <CardHeader className="bg-amber-50 border-b border-amber-200 py-3 px-5">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-semibold text-amber-800 flex items-center gap-2">
                                <HelpCircle className="h-4 w-4" />
                                Guida alla Risoluzione Problemi
                            </CardTitle>
                            <Badge className="bg-amber-100 text-amber-700 border border-amber-200 text-[10px]">{FAQ_LIST.length} FAQ</Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="px-4 py-3 border-b border-amber-100">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                                <Input placeholder="Cerca nelle FAQ..."
                                    value={searchFaq} onChange={e => setSearchFaq(e.target.value)}
                                    className="pl-9 h-8 text-sm" data-testid="faq-search" />
                            </div>
                        </div>
                        <div className="divide-y divide-slate-100 max-h-[400px] overflow-y-auto">
                            {filteredFaq.map((faq, i) => (
                                <div key={i} className="px-5 py-3 hover:bg-slate-50/50 transition-colors" data-testid={`faq-${i}`}>
                                    <p className="text-sm font-semibold text-slate-700 flex items-start gap-2">
                                        <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">{i + 1}</span>
                                        {faq.q}
                                    </p>
                                    <p className="text-sm text-slate-500 mt-1 ml-7">{faq.a}</p>
                                </div>
                            ))}
                            {filteredFaq.length === 0 && (
                                <div className="text-center py-8 text-slate-400 text-sm">Nessuna FAQ trovata</div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Footer */}
                <div className="text-center text-xs text-slate-400 py-4">
                    Il PDF include copertina con logo aziendale, indice, tutti i capitoli, tabella FAQ e QR Code per il portale clienti.
                </div>
            </div>
        </DashboardLayout>
    );
}
