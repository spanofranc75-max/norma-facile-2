/**
 * DisclaimerPage — Limitazione di Responsabilità e Avvertenze Tecniche EN 1090.
 */
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { ArrowLeft, AlertTriangle, Shield, FileCheck, Wrench, Scale } from 'lucide-react';

export default function DisclaimerPage() {
    const navigate = useNavigate();
    return (
        <div className="min-h-screen bg-slate-50" data-testid="disclaimer-page">
            <div className="max-w-3xl mx-auto px-6 py-12">
                <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="mb-6 text-xs text-slate-500">
                    <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Indietro
                </Button>

                <div className="flex items-center gap-3 mb-8">
                    <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
                        <AlertTriangle className="h-6 w-6 text-amber-600" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-[#0F172A]">Limitazione di Responsabilit&agrave;</h1>
                        <p className="text-sm text-slate-500">Avvertenze Tecniche — EN 1090 / EN 13241 / ISO 3834</p>
                    </div>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-8 text-sm text-slate-700 leading-relaxed">
                    <p className="text-xs text-slate-400">Ultimo aggiornamento: 2 Marzo 2026</p>

                    <section>
                        <div className="flex items-center gap-2 mb-3">
                            <Scale className="h-4 w-4 text-[#0F172A]" />
                            <h2 className="text-base font-bold text-[#0F172A]">1. Natura del Servizio</h2>
                        </div>
                        <p>
                            &ldquo;Norma Facile&rdquo; (di seguito &ldquo;il Software&rdquo;) &egrave; uno <strong>strumento software di supporto gestionale e redazionale</strong> sviluppato da Steel Project Design S.R.L.S. (di seguito &ldquo;il Fornitore&rdquo;).
                        </p>
                        <p className="mt-2">
                            Il Software <strong>NON sostituisce in alcun modo</strong> la certificazione aziendale obbligatoria rilasciata da un Organismo Notificato ai sensi del <strong>Regolamento UE 305/2011 (CPR)</strong> per la marcatura CE dei componenti strutturali in acciaio e alluminio, n&eacute; la certificazione del sistema di gestione per la qualit&agrave; ai sensi della norma <strong>ISO 9001</strong> o del sistema di controllo della produzione in fabbrica ai sensi della <strong>EN 1090-1</strong>.
                        </p>
                    </section>

                    <section>
                        <div className="flex items-center gap-2 mb-3">
                            <Wrench className="h-4 w-4 text-[#0F172A]" />
                            <h2 className="text-base font-bold text-[#0F172A]">2. Responsabilit&agrave; dell&rsquo;Utente</h2>
                        </div>
                        <p className="mb-3">
                            L&rsquo;utente (di seguito &ldquo;il Fabbricante&rdquo;) rimane <strong>l&rsquo;unico e esclusivo responsabile</strong> di:
                        </p>
                        <ul className="space-y-2 ml-4">
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                Della <strong>veridicit&agrave; dei dati inseriti</strong> nel Software (es. numeri di colata dei materiali, parametri di saldatura, risultati delle prove, dati dei certificati 3.1).
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                Del <strong>rispetto delle procedure di saldatura</strong> (WPS) qualificate ai sensi della EN ISO 15614 e della qualifica del personale di saldatura ai sensi della EN ISO 9606.
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                Della corretta attuazione del <strong>Controllo di Produzione in Fabbrica (FPC)</strong> conformemente alla EN 1090-1, Allegato B.
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                Della <strong>marcatura CE fisica</strong> apposta sul manufatto e della relativa Dichiarazione di Prestazione (DoP).
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                Della conformit&agrave; alle normative <strong>EN 13241</strong> ed <strong>EN 12453</strong> per chiusure industriali, cancelli e automazioni, incluse le prove di forza e l&rsquo;analisi dei rischi.
                            </li>
                        </ul>
                    </section>

                    <section>
                        <div className="flex items-center gap-2 mb-3">
                            <Shield className="h-4 w-4 text-[#0F172A]" />
                            <h2 className="text-base font-bold text-[#0F172A]">3. Esclusione di Garanzia</h2>
                        </div>
                        <p>
                            Steel Project Design S.R.L.S. <strong>non garantisce</strong> che la documentazione generata dal Software sia automaticamente conforme alle interpretazioni specifiche di ogni singolo Ente Notificato o Organismo di Certificazione. &Egrave; responsabilit&agrave; del <strong>Coordinatore di Saldatura (RWC)</strong> e del <strong>Responsabile Qualit&agrave;</strong> dell&rsquo;utente validare tutti i documenti prima della loro emissione ufficiale.
                        </p>
                        <p className="mt-3">
                            Il Software viene fornito &ldquo;cos&igrave; com&rsquo;&egrave;&rdquo; (<em>as is</em>), senza garanzie esplicite o implicite di completezza, accuratezza o idoneit&agrave; per uno scopo particolare. In nessun caso il Fornitore potr&agrave; essere ritenuto responsabile per danni diretti, indiretti, incidentali o consequenziali derivanti dall&rsquo;uso del Software.
                        </p>
                    </section>

                    <section>
                        <div className="flex items-center gap-2 mb-3">
                            <FileCheck className="h-4 w-4 text-[#0F172A]" />
                            <h2 className="text-base font-bold text-[#0F172A]">4. Obblighi di Verifica</h2>
                        </div>
                        <p>
                            L&rsquo;utente si impegna a <strong>verificare sempre</strong> la correttezza dei documenti generati dal Software prima di:
                        </p>
                        <ul className="space-y-1.5 ml-4 mt-2">
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                                Allegare documentazione a pratiche ufficiali o a fascicoli tecnici.
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                                Presentare documentazione in sede di audit da parte dell&rsquo;Ente Notificato.
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                                Emettere Dichiarazioni di Prestazione (DoP) o etichette CE.
                            </li>
                        </ul>
                    </section>

                    <div className="border-t border-slate-200 pt-6 mt-6">
                        <p className="text-xs text-slate-400 italic">
                            Il presente documento ha finalit&agrave; informativa e non costituisce parere legale. Si consiglia di consultare un professionista legale per una valutazione completa dei rischi e delle responsabilit&agrave;.
                        </p>
                        <p className="text-xs text-slate-500 mt-3 font-semibold">
                            Steel Project Design S.R.L.S. &mdash; P.IVA 02042850897
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
