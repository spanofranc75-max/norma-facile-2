/**
 * CaseStudyPage — Public case study page for commercial use.
 * "Da preventivo a cantiere pronto" — Steel Project Design pilot case.
 * Accessible without login at /caso-studio
 */
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
    ArrowLeft, Clock, ShieldCheck, FileCheck, Eye,
    ChevronRight, BarChart3, AlertTriangle, CheckCircle2,
    Wrench, Target, TrendingUp,
} from 'lucide-react';

const METRICS = [
    { label: 'Tempo preparazione POS', before: 'Ore di copia manuale da Word', after: 'Bozza precompilata in minuti', estimate: 'Riduzione stimata 50–70%', icon: Clock },
    { label: 'Dossier documentale cliente', before: 'Ricerca manuale file e attestati', after: 'Checklist + matching + invio tracciato', estimate: 'Tempo operativo sensibilmente ridotto', icon: FileCheck },
    { label: 'Visibilita commessa', before: 'Informazioni sparse tra moduli e email', after: 'Dashboard + Registro Obblighi', estimate: 'Da frammentato a vista unica', icon: Eye },
    { label: 'Rischio omissioni', before: 'Nessun gate, nessun controllo preventivo', after: 'Evidence Gate + checklist + auto-close', estimate: 'Riduzione rischio omissioni documentali', icon: ShieldCheck },
];

export default function CaseStudyPage() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-white">
            {/* Header */}
            <header className="bg-[#0F172A] text-white">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <button onClick={() => navigate('/')} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm">
                        <ArrowLeft className="h-4 w-4" />
                        <img src="/logo-1090.png" alt="NormaFacile" className="h-7" />
                    </button>
                    <span className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Caso Studio</span>
                </div>
            </header>

            {/* Hero */}
            <section className="bg-[#0F172A] text-white pb-16 pt-10">
                <div className="max-w-4xl mx-auto px-6">
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-[11px] uppercase tracking-widest text-lime-400 font-semibold">Caso pilota</span>
                        <span className="text-[11px] text-slate-500">|</span>
                        <span className="text-[11px] text-slate-400">Stime operative interne</span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold leading-tight mb-4" data-testid="case-study-title">
                        Da preventivo a cantiere pronto:
                        <br />
                        <span className="text-lime-400">meno lavoro manuale, commessa governabile</span>
                    </h1>
                    <p className="text-base text-slate-300 max-w-2xl leading-relaxed">
                        Come un'azienda di carpenteria metallica ha trasformato il proprio flusso operativo — dal preventivo alla consegna — riducendo passaggi manuali, errori documentali e tempi morti.
                    </p>
                </div>
            </section>

            {/* Contesto */}
            <section className="py-12 border-b border-slate-100" data-testid="section-contesto">
                <div className="max-w-4xl mx-auto px-6">
                    <SectionHeader number="01" title="Contesto" icon={Target} />
                    <div className="mt-5 text-sm text-slate-700 leading-relaxed space-y-3 max-w-3xl">
                        <p>
                            Steel Project Design S.R.L.S. opera nel settore della carpenteria metallica, con commesse che spaziano dalla produzione di strutture EN 1090 ai cancelli e portoni EN 13241, fino a lavorazioni generiche non normate.
                        </p>
                        <p>
                            L'azienda gestisce mediamente commesse miste — dove una singola commessa puo contenere lavorazioni con requisiti normativi diversi. Il flusso operativo coinvolge titolare, ufficio tecnico, responsabile sicurezza e qualita.
                        </p>
                        <p>
                            Prima di 1090 Norma Facile, il processo dal preventivo al cantiere pronto era frammentato tra fogli Excel, documenti Word, email e cartelle condivise.
                        </p>
                    </div>
                </div>
            </section>

            {/* Problema Prima */}
            <section className="py-12 bg-slate-50 border-b border-slate-100" data-testid="section-problema">
                <div className="max-w-4xl mx-auto px-6">
                    <SectionHeader number="02" title="Il problema prima" icon={AlertTriangle} color="text-amber-600" />
                    <div className="mt-6 grid sm:grid-cols-2 gap-4">
                        <ProblemCard title="Commessa come puzzle">
                            Le informazioni su obblighi, documenti, scadenze e normative erano sparse tra moduli diversi. Nessuno aveva una lista unica delle cose da fare.
                        </ProblemCard>
                        <ProblemCard title="POS riscritto da zero">
                            Ogni Piano Operativo di Sicurezza partiva da un vecchio file Word, con correzioni manuali, rischi dimenticati e dati reinseriti piu volte.
                        </ProblemCard>
                        <ProblemCard title="Pacchetti documentali a mano">
                            Preparare un dossier per il cliente significava cercare file, attestati e allegati sparsi, sperando di non dimenticarne nessuno.
                        </ProblemCard>
                        <ProblemCard title="Blocchi scoperti troppo tardi">
                            Mancavano evidenze per emettere DoP o certificazioni CE, ma il problema emergeva solo a ridosso della consegna.
                        </ProblemCard>
                    </div>
                </div>
            </section>

            {/* Cosa fa NormaFacile */}
            <section className="py-12 border-b border-slate-100" data-testid="section-soluzione">
                <div className="max-w-4xl mx-auto px-6">
                    <SectionHeader number="03" title="Cosa fa 1090 Norma Facile" icon={Wrench} color="text-blue-600" />
                    <div className="mt-6 space-y-4 max-w-3xl">
                        <SolutionStep step="1" title="Dal preventivo all'istruttoria">
                            L'AI analizza il preventivo e propone un'istruttoria tecnica e normativa strutturata. Classificazione automatica EN 1090 / EN 13241, domande residue ad alto impatto, base per commessa pre-istruita.
                        </SolutionStep>
                        <SolutionStep step="2" title="Segmentazione commessa mista">
                            Le righe della commessa vengono segmentate in rami normativi distinti. Ogni ramo ha i propri requisiti, documenti ed emissioni. Nessun rischio di mischiare normative.
                        </SolutionStep>
                        <SolutionStep step="3" title="Registro Obblighi centralizzato">
                            Un unico registro raccoglie automaticamente da 8 fonti diverse tutto cio che manca, blocca o richiede attenzione. Con responsabili, scadenze e priorita.
                        </SolutionStep>
                        <SolutionStep step="4" title="POS precompilato da commessa">
                            La scheda cantiere attiva rischi, DPI e misure. Il sistema genera una bozza POS DOCX modificabile, con gate che verifica completezza prima dell'emissione.
                        </SolutionStep>
                        <SolutionStep step="5" title="Pacchetti documentali verificati">
                            Matching automatico dei documenti, verifica scadenze, preview invio e tracking completo. Il dossier esce corretto e tracciato.
                        </SolutionStep>
                        <SolutionStep step="6" title="Evidence Gate per emissioni">
                            Prima di emettere qualsiasi documento certificativo, il sistema verifica che tutte le evidenze esistano davvero. Blocco automatico se manca qualcosa.
                        </SolutionStep>
                    </div>
                </div>
            </section>

            {/* Risultati */}
            <section className="py-12 bg-[#0F172A] text-white" data-testid="section-risultati">
                <div className="max-w-4xl mx-auto px-6">
                    <SectionHeader number="04" title="Risultati ottenuti" icon={TrendingUp} color="text-lime-400" light />
                    <p className="text-xs text-slate-500 mt-2 mb-6">Stime operative interne — caso pilota</p>
                    <div className="grid sm:grid-cols-2 gap-4">
                        {METRICS.map((m, i) => (
                            <MetricCard key={i} metric={m} />
                        ))}
                    </div>
                </div>
            </section>

            {/* Cosa cambia */}
            <section className="py-12 border-b border-slate-100" data-testid="section-cambiamento">
                <div className="max-w-4xl mx-auto px-6">
                    <SectionHeader number="05" title="Cosa cambia nella gestione quotidiana" icon={CheckCircle2} color="text-emerald-600" />
                    <div className="mt-6 grid sm:grid-cols-3 gap-5">
                        <ChangeCard title="Meno reinserimento manuale" desc="I dati fluiscono dal preventivo alla commessa, dalla commessa al POS, dal POS al pacchetto documentale. Senza ricopiare." />
                        <ChangeCard title="Maggiore prontezza documentale" desc="Il dossier cliente si prepara in minuti, non in ore. Con verifica automatica di completezza e scadenze." />
                        <ChangeCard title="Commessa governabile" desc="Un unico cruscotto mostra stato, blocchi e priorita. Il titolare vede subito cosa serve per sbloccare la consegna." />
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-14 bg-slate-50" data-testid="section-cta">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <h2 className="text-xl font-bold text-slate-900 mb-2">Vuoi vedere il sistema in azione?</h2>
                    <p className="text-sm text-slate-500 mb-6">Prova l'ambiente demo con dati realistici — nessuna registrazione richiesta.</p>
                    <div className="flex justify-center gap-3">
                        <Button className="bg-[#0F172A] text-white text-sm px-6 py-2.5 h-auto" onClick={() => navigate('/')} data-testid="cta-demo">
                            Prova la Demo
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                        <Button variant="outline" className="text-sm px-6 py-2.5 h-auto border-slate-300" onClick={() => navigate('/')} data-testid="cta-home">
                            Torna alla Home
                        </Button>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-6 border-t border-slate-200">
                <div className="max-w-4xl mx-auto px-6 flex items-center justify-between text-[11px] text-slate-400">
                    <span>2026 1090 Norma Facile — Steel Project Design S.R.L.S.</span>
                    <span>Le metriche presentate sono stime operative interne derivate da un caso pilota.</span>
                </div>
            </footer>
        </div>
    );
}

/* ─── Sub-components ─── */

function SectionHeader({ number, title, icon: Icon, color = 'text-slate-800', light = false }) {
    return (
        <div className="flex items-center gap-3">
            <span className={`text-xs font-mono ${light ? 'text-slate-500' : 'text-slate-400'}`}>{number}</span>
            <Icon className={`h-5 w-5 ${color}`} strokeWidth={1.5} />
            <h2 className={`text-lg font-bold ${light ? 'text-white' : 'text-slate-900'}`}>{title}</h2>
        </div>
    );
}

function ProblemCard({ title, children }) {
    return (
        <div className="p-4 bg-white rounded-lg border border-slate-200 border-l-4 border-l-amber-400">
            <h3 className="text-sm font-bold text-slate-800 mb-1">{title}</h3>
            <p className="text-xs text-slate-600 leading-relaxed">{children}</p>
        </div>
    );
}

function SolutionStep({ step, title, children }) {
    return (
        <div className="flex gap-4">
            <div className="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs font-bold text-blue-600">{step}</span>
            </div>
            <div>
                <h3 className="text-sm font-bold text-slate-800">{title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed mt-0.5">{children}</p>
            </div>
        </div>
    );
}

function MetricCard({ metric }) {
    const Icon = metric.icon;
    return (
        <div className="p-4 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4 text-lime-400" />
                <h3 className="text-sm font-semibold text-white">{metric.label}</h3>
            </div>
            <div className="space-y-1.5">
                <div className="flex items-start gap-2">
                    <span className="text-[10px] font-bold text-red-400 mt-0.5 shrink-0">PRIMA</span>
                    <p className="text-xs text-slate-400">{metric.before}</p>
                </div>
                <div className="flex items-start gap-2">
                    <span className="text-[10px] font-bold text-lime-400 mt-0.5 shrink-0">DOPO</span>
                    <p className="text-xs text-slate-300">{metric.after}</p>
                </div>
                <p className="text-xs font-semibold text-lime-400/80 pt-1 border-t border-white/5">{metric.estimate}</p>
            </div>
        </div>
    );
}

function ChangeCard({ title, desc }) {
    return (
        <div className="text-center p-4">
            <CheckCircle2 className="h-6 w-6 text-emerald-500 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-800 mb-1">{title}</h3>
            <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
        </div>
    );
}
