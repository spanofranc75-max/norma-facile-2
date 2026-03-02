/**
 * PrivacyPage — Informativa sulla Privacy (GDPR).
 */
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { ArrowLeft, Eye } from 'lucide-react';

export default function PrivacyPage() {
    const navigate = useNavigate();
    return (
        <div className="min-h-screen bg-slate-50" data-testid="privacy-page">
            <div className="max-w-3xl mx-auto px-6 py-12">
                <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="mb-6 text-xs text-slate-500">
                    <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Indietro
                </Button>

                <div className="flex items-center gap-3 mb-8">
                    <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
                        <Eye className="h-6 w-6 text-emerald-600" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-[#0F172A]">Informativa sulla Privacy</h1>
                        <p className="text-sm text-slate-500">Ai sensi del Regolamento UE 2016/679 (GDPR)</p>
                    </div>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-6 text-sm text-slate-700 leading-relaxed">
                    <p className="text-xs text-slate-400">Ultimo aggiornamento: 2 Marzo 2026</p>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">1. Titolare del Trattamento</h2>
                        <p>Il Titolare del trattamento dei dati personali &egrave;:</p>
                        <div className="mt-2 bg-slate-50 rounded-lg p-3 text-xs">
                            <p className="font-semibold">Steel Project Design S.R.L.S.</p>
                            <p>P.IVA: 02042850897</p>
                            <p>Email: privacy@steelprojectdesign.it</p>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">2. Dati Raccolti</h2>
                        <p>Il Servizio raccoglie le seguenti categorie di dati:</p>
                        <ul className="mt-2 space-y-1 ml-4">
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                                <strong>Dati di identificazione:</strong> nome, cognome, indirizzo email (tramite Google OAuth).
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                                <strong>Dati aziendali:</strong> ragione sociale, P.IVA, indirizzo sede legale, dati bancari (inseriti volontariamente dall&rsquo;Utente).
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                                <strong>Dati operativi:</strong> commesse, preventivi, fatture, documenti tecnici, certificazioni (inseriti dall&rsquo;Utente nell&rsquo;ambito dell&rsquo;utilizzo del Servizio).
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                                <strong>Dati tecnici:</strong> log di accesso, indirizzo IP, tipo di browser (raccolti automaticamente).
                            </li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">3. Finalit&agrave; del Trattamento</h2>
                        <p>I dati sono trattati per le seguenti finalit&agrave;:</p>
                        <ul className="mt-2 space-y-1 ml-4">
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" /> Erogazione del Servizio e gestione dell&rsquo;account utente.</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" /> Generazione di documenti tecnici (DoP, Etichette CE, FPC).</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" /> Comunicazioni relative al Servizio (aggiornamenti, manutenzione).</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" /> Adempimento di obblighi di legge.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">4. Base Giuridica</h2>
                        <p>Il trattamento &egrave; fondato su: (a) esecuzione del contratto di servizio; (b) consenso dell&rsquo;interessato; (c) legittimo interesse del Titolare; (d) adempimento di obblighi legali.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">5. Conservazione dei Dati</h2>
                        <p>I dati personali sono conservati per la durata del rapporto contrattuale e per i 10 anni successivi alla cessazione dello stesso, in conformit&agrave; agli obblighi fiscali e normativi vigenti.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">6. Diritti dell&rsquo;Interessato</h2>
                        <p>Ai sensi degli artt. 15-22 del GDPR, l&rsquo;Utente ha diritto di:</p>
                        <ul className="mt-2 space-y-1 ml-4">
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" /> Accedere ai propri dati personali.</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" /> Richiedere la rettifica o la cancellazione dei dati.</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" /> Richiedere la limitazione del trattamento.</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" /> Esercitare il diritto alla portabilit&agrave; dei dati (funzione Backup).</li>
                            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" /> Proporre reclamo al Garante per la Protezione dei Dati Personali.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">7. Cookie</h2>
                        <p>Il Servizio utilizza cookie tecnici strettamente necessari per il funzionamento (sessione di autenticazione). Non vengono utilizzati cookie di profilazione o di terze parti a fini pubblicitari.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">8. Trasferimento Dati</h2>
                        <p>I dati sono conservati su server situati nell&rsquo;Unione Europea. In caso di utilizzo di servizi di terze parti (es. Google per l&rsquo;autenticazione), si applicano le rispettive informative sulla privacy.</p>
                    </section>

                    <div className="border-t border-slate-200 pt-6">
                        <p className="text-xs text-slate-400 italic">Per esercitare i propri diritti, contattare: privacy@steelprojectdesign.it</p>
                        <p className="text-xs text-slate-500 mt-2 font-semibold">Steel Project Design S.R.L.S. &mdash; P.IVA 02042850897</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
