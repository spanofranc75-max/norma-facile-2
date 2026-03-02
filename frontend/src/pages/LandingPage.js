/**
 * Landing Page — Norma Facile 1090
 * Split Screen: Brand Experience (Dark) | Login Area (Light)
 * Palette: Navy #0F172A, Steel Grey #64748B, Lime Accent #84CC16
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import { LegalFooter } from '../components/LegalFooter';
import {
    Shield, CheckCircle2, Lock, ArrowRight,
    Wrench, FileCheck, BarChart3, Zap,
} from 'lucide-react';

export default function LandingPage() {
    const { isAuthenticated, login, loading } = useAuth();
    const navigate = useNavigate();
    const [tosAccepted, setTosAccepted] = useState(false);

    useEffect(() => {
        if (isAuthenticated) navigate('/dashboard');
    }, [isAuthenticated, navigate]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#0F172A]">
                <div className="w-10 h-10 border-2 border-lime-400 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col lg:flex-row" data-testid="landing-page">
            {/* ═══ LEFT: Brand Experience ═══ */}
            <div className="relative lg:w-[55%] min-h-[40vh] lg:min-h-screen bg-[#0F172A] overflow-hidden flex flex-col">
                {/* Technical grid pattern overlay */}
                <div className="absolute inset-0 opacity-[0.04]"
                     style={{
                         backgroundImage: `
                             linear-gradient(rgba(148,163,184,1) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(148,163,184,1) 1px, transparent 1px)
                         `,
                         backgroundSize: '60px 60px',
                     }}
                />
                {/* Radial glow */}
                <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] bg-lime-500/5 rounded-full blur-[120px]" />
                <div className="absolute bottom-0 right-0 w-[300px] h-[300px] bg-slate-500/5 rounded-full blur-[80px]" />

                {/* Content */}
                <div className="relative z-10 flex-1 flex flex-col justify-between p-8 lg:p-12 xl:p-16">
                    {/* Top: Logo */}
                    <div>
                        <div className="inline-block bg-white/95 rounded-2xl p-4 shadow-lg shadow-black/20 backdrop-blur-sm">
                            <img
                                src="/logo-1090.jpeg"
                                alt="1090 Norma Facile"
                                className="h-20 lg:h-24 w-auto"
                                data-testid="brand-logo"
                            />
                        </div>
                    </div>

                    {/* Center: Hero copy */}
                    <div className="my-8 lg:my-0">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1 mb-6 rounded-full border border-lime-500/30 bg-lime-500/10">
                            <Zap className="h-3 w-3 text-lime-400" />
                            <span className="text-[11px] font-semibold text-lime-400 uppercase tracking-wider">Carpenteria 4.0</span>
                        </div>

                        <h1 className="text-3xl sm:text-4xl lg:text-5xl xl:text-6xl font-black text-white leading-[1.1] mb-6 tracking-tight">
                            Il Gestionale per la{' '}
                            <span className="relative inline-block">
                                <span className="relative z-10">Carpenteria</span>
                                <span className="absolute bottom-1 left-0 right-0 h-3 bg-lime-500/20 -skew-x-3" />
                            </span>
                        </h1>

                        <p className="text-base lg:text-lg text-slate-400 max-w-lg leading-relaxed mb-8">
                            EN 1090 &bull; EN 13241 &bull; ISO 3834.
                            <br />
                            Tutto il ferro, organizzato in un unico Hub.
                        </p>

                        {/* Feature checklist */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
                            {[
                                { icon: Wrench, text: 'Commesse e Produzione' },
                                { icon: FileCheck, text: 'Fascicolo Tecnico CE' },
                                { icon: Shield, text: 'Qualifica Saldatori' },
                                { icon: BarChart3, text: 'Controllo Costi e Margini' },
                            ].map((f) => (
                                <div key={f.text} className="flex items-center gap-2.5 group">
                                    <div className="w-7 h-7 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center group-hover:border-lime-500/50 group-hover:bg-lime-500/10 transition-colors duration-300">
                                        <f.icon className="h-3.5 w-3.5 text-lime-400" />
                                    </div>
                                    <span className="text-sm text-slate-300 font-medium">{f.text}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Bottom: Footer */}
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-slate-600">
                            Powered by <span className="text-slate-500 font-semibold">Steel Project Design</span>
                        </p>
                        <div className="flex items-center gap-4">
                            <span className="text-[10px] text-slate-600 uppercase tracking-wider">EN 1090</span>
                            <span className="w-px h-3 bg-slate-700" />
                            <span className="text-[10px] text-slate-600 uppercase tracking-wider">EN 13241</span>
                            <span className="w-px h-3 bg-slate-700" />
                            <span className="text-[10px] text-slate-600 uppercase tracking-wider">ISO 3834</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* ═══ RIGHT: Login Area ═══ */}
            <div className="lg:w-[45%] min-h-[60vh] lg:min-h-screen bg-slate-50 flex items-center justify-center p-8 lg:p-12">
                <div className="w-full max-w-sm">
                    {/* Login card */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#0F172A] mb-5 shadow-lg shadow-slate-900/20">
                            <Lock className="h-6 w-6 text-lime-400" />
                        </div>
                        <h2 className="text-xl font-bold text-[#0F172A] mb-1">
                            Accedi al tuo Hub
                        </h2>
                        <p className="text-sm text-slate-500">
                            Gestisci commesse, certificazioni e qualità
                        </p>
                    </div>

                    {/* ToS Acceptance */}
                    <label className="flex items-start gap-2.5 cursor-pointer group mb-5" data-testid="tos-checkbox-label">
                        <Checkbox
                            checked={tosAccepted}
                            onCheckedChange={setTosAccepted}
                            className="mt-0.5 h-4 w-4 border-slate-300 data-[state=checked]:bg-[#0F172A] data-[state=checked]:border-[#0F172A]"
                            data-testid="tos-checkbox"
                        />
                        <span className="text-[11px] text-slate-500 leading-relaxed">
                            Accetto i{' '}
                            <a href="/legal/terms" target="_blank" className="text-[#0F172A] underline hover:text-blue-600 font-medium">Termini di Servizio</a>
                            {' '}e dichiaro di aver letto il{' '}
                            <a href="/legal/disclaimer" target="_blank" className="text-amber-600 underline hover:text-amber-700 font-medium">Disclaimer sulle responsabilità EN 1090</a>.
                        </span>
                    </label>

                    {/* Google Login Button */}
                    <Button
                        data-testid="hero-login-btn"
                        onClick={login}
                        disabled={!tosAccepted}
                        size="lg"
                        className={`w-full h-12 text-sm font-semibold rounded-xl shadow-lg transition-all duration-300 group ${
                            tosAccepted
                                ? 'bg-[#0F172A] text-white hover:bg-[#1E293B] shadow-slate-900/10 hover:shadow-xl hover:shadow-slate-900/20 hover:-translate-y-0.5'
                                : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                        }`}
                    >
                        <svg className="h-5 w-5 mr-2.5" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                        </svg>
                        Accedi con Google
                        <ArrowRight className="h-4 w-4 ml-2 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300" />
                    </Button>

                    {/* Separator */}
                    <div className="flex items-center gap-3 my-6">
                        <div className="flex-1 h-px bg-slate-200" />
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">oppure</span>
                        <div className="flex-1 h-px bg-slate-200" />
                    </div>

                    {/* Demo request */}
                    <Button
                        data-testid="hero-demo-btn"
                        variant="outline"
                        size="lg"
                        className="w-full h-11 border-slate-300 text-slate-600 hover:bg-white hover:border-slate-400 text-sm rounded-xl"
                    >
                        Richiedi una Demo
                    </Button>

                    {/* Trust signals */}
                    <div className="mt-8 pt-6 border-t border-slate-200">
                        <div className="flex flex-col gap-2.5">
                            {[
                                'Conforme EN 1090-1 e EN 13241',
                                'Generazione DoP e Etichette CE',
                                'Tracciabilità Materiali ISO 3834',
                            ].map((text) => (
                                <div key={text} className="flex items-center gap-2">
                                    <CheckCircle2 className="h-3.5 w-3.5 text-lime-500 shrink-0" />
                                    <span className="text-xs text-slate-500">{text}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Footer */}
                    <p className="text-center text-[10px] text-slate-400 mt-8">
                        © 2026 Norma Facile — Steel Project Design S.R.L.S.
                        <br />
                        P.IVA 02042850897
                    </p>
                    <div className="flex items-center justify-center gap-3 mt-3">
                        <a href="/legal/privacy" className="text-[10px] text-slate-400 hover:text-slate-600 underline">Privacy</a>
                        <a href="/legal/terms" className="text-[10px] text-slate-400 hover:text-slate-600 underline">Termini</a>
                        <a href="/legal/disclaimer" className="text-[10px] text-amber-500 hover:text-amber-600 underline">Disclaimer</a>
                    </div>
                </div>
            </div>
        </div>
    );
}
