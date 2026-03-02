/**
 * TermsPage — Termini e Condizioni di Servizio.
 */
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { ArrowLeft, FileText } from 'lucide-react';

export default function TermsPage() {
    const navigate = useNavigate();
    return (
        <div className="min-h-screen bg-slate-50" data-testid="terms-page">
            <div className="max-w-3xl mx-auto px-6 py-12">
                <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="mb-6 text-xs text-slate-500">
                    <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Indietro
                </Button>

                <div className="flex items-center gap-3 mb-8">
                    <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
                        <FileText className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-[#0F172A]">Termini e Condizioni di Servizio</h1>
                        <p className="text-sm text-slate-500">Norma Facile — Steel Project Design S.R.L.S.</p>
                    </div>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-6 text-sm text-slate-700 leading-relaxed">
                    <p className="text-xs text-slate-400">Ultimo aggiornamento: 2 Marzo 2026</p>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">1. Definizioni</h2>
                        <p>&ldquo;Servizio&rdquo;: la piattaforma software &ldquo;Norma Facile&rdquo; accessibile via web, incluse tutte le funzionalit&agrave; di gestione commesse, preventivi, fatturazione, generazione documenti tecnici e certificazioni.</p>
                        <p className="mt-1">&ldquo;Fornitore&rdquo;: Steel Project Design S.R.L.S., P.IVA 02042850897.</p>
                        <p className="mt-1">&ldquo;Utente&rdquo;: la persona fisica o giuridica che accede e utilizza il Servizio.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">2. Oggetto del Contratto</h2>
                        <p>I presenti Termini regolano l&rsquo;accesso e l&rsquo;utilizzo del Servizio. L&rsquo;utilizzo del Servizio implica l&rsquo;accettazione integrale dei presenti Termini e del Disclaimer sulle responsabilit&agrave; tecniche.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">3. Account e Accesso</h2>
                        <p>L&rsquo;accesso avviene tramite autenticazione Google OAuth. L&rsquo;Utente &egrave; responsabile della sicurezza del proprio account Google e di tutte le attivit&agrave; eseguite tramite il proprio profilo.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">4. Dati e Propriet&agrave; Intellettuale</h2>
                        <p>I dati inseriti dall&rsquo;Utente (commesse, clienti, documenti) restano di propriet&agrave; esclusiva dell&rsquo;Utente. Il Fornitore si impegna a non utilizzare tali dati per finalit&agrave; diverse dall&rsquo;erogazione del Servizio.</p>
                        <p className="mt-1">Il Software, il codice sorgente, il design e il marchio &ldquo;Norma Facile&rdquo; sono di propriet&agrave; esclusiva del Fornitore.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">5. Limitazione di Responsabilit&agrave;</h2>
                        <p>Si rimanda integralmente al documento <a href="/legal/disclaimer" className="text-blue-600 underline hover:text-blue-800">Disclaimer e Avvertenze Tecniche</a> per le limitazioni di responsabilit&agrave; relative alla documentazione tecnica generata dal Software.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">6. Disponibilit&agrave; del Servizio</h2>
                        <p>Il Fornitore si impegna a garantire la massima disponibilit&agrave; del Servizio, ma non garantisce un funzionamento ininterrotto. Eventuali interruzioni per manutenzione verranno comunicate con ragionevole anticipo.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">7. Recesso e Cancellazione</h2>
                        <p>L&rsquo;Utente pu&ograve; richiedere la cancellazione del proprio account e di tutti i dati associati in qualsiasi momento, contattando il Fornitore all&rsquo;indirizzo email indicato.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-bold text-[#0F172A] mb-2">8. Foro Competente</h2>
                        <p>Per qualsiasi controversia derivante dall&rsquo;interpretazione o esecuzione dei presenti Termini, sar&agrave; competente in via esclusiva il Foro di Siracusa (SR).</p>
                    </section>

                    <div className="border-t border-slate-200 pt-6">
                        <p className="text-xs text-slate-500 font-semibold">Steel Project Design S.R.L.S. &mdash; P.IVA 02042850897</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
