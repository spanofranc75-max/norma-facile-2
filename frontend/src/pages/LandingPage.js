/**
 * Landing Page - Norma Facile 2.0
 * Main entry point with Google OAuth login.
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { FileText, MessageSquare, Database, Shield, ArrowRight, Scale } from 'lucide-react';

export default function LandingPage() {
    const { isAuthenticated, login, loading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (isAuthenticated) {
            navigate('/dashboard');
        }
    }, [isAuthenticated, navigate]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    const features = [
        {
            icon: FileText,
            title: 'Generazione Documenti',
            description: 'Crea contratti, lettere e atti legali con l\'intelligenza artificiale.',
        },
        {
            icon: MessageSquare,
            title: 'Assistente Legale',
            description: 'Chatbot specializzato per rispondere alle tue domande legali.',
        },
        {
            icon: Database,
            title: 'Archivio Sicuro',
            description: 'Salva e organizza tutti i tuoi documenti in un unico posto.',
        },
    ];

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Hero Section */}
            <div className="hero-mesh">
                <header className="container mx-auto px-6 py-6">
                    <nav className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Scale className="h-8 w-8 text-[#0055FF]" strokeWidth={1.5} />
                            <span className="font-sans text-xl font-bold text-slate-900">
                                Norma Facile
                            </span>
                        </div>
                        <Button
                            data-testid="header-login-btn"
                            onClick={login}
                            className="bg-[#0055FF] text-white hover:bg-[#0044CC]"
                        >
                            Accedi
                        </Button>
                    </nav>
                </header>

                <section className="container mx-auto px-6 py-24 text-center">
                    <div className="max-w-3xl mx-auto animate-fade-in">
                        <span className="inline-block px-4 py-1.5 mb-6 text-xs font-semibold uppercase tracking-wider text-[#0055FF] bg-blue-50 rounded-full">
                            CRM per Fabbri e Carpenterie
                        </span>
                        <h1 className="font-sans text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 mb-6">
                            Il Ferro, <span className="text-[#0055FF]">Organizzato</span>
                        </h1>
                        <p className="text-lg text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
                            Gestisci commesse, distinte materiali, certificazioni CE
                            e fatturazione in un'unica piattaforma pensata per chi lavora il metallo.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Button
                                data-testid="hero-login-btn"
                                onClick={login}
                                size="lg"
                                className="bg-[#0055FF] text-white hover:bg-[#0044CC] px-8 py-3 text-base"
                            >
                                Inizia Gratuitamente
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Button>
                            <Button
                                data-testid="hero-demo-btn"
                                variant="outline"
                                size="lg"
                                className="border-slate-300 text-slate-700 hover:bg-slate-100 px-8 py-3 text-base"
                            >
                                Guarda Demo
                            </Button>
                        </div>
                    </div>
                </section>
            </div>

            {/* Features Section */}
            <section className="py-24 bg-white">
                <div className="container mx-auto px-6">
                    <div className="text-center mb-16">
                        <h2 className="font-sans text-3xl font-bold tracking-tight text-slate-900 mb-4">
                            Tutto ciò che ti serve
                        </h2>
                        <p className="text-slate-600 max-w-xl mx-auto">
                            Strumenti avanzati per semplificare il lavoro legale quotidiano.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {features.map((feature, index) => (
                            <div
                                key={feature.title}
                                data-testid={`feature-card-${index}`}
                                className="group p-8 bg-white border border-slate-200 rounded-lg hover:shadow-md hover:border-slate-300 transition-all duration-300 animate-slide-up"
                                style={{ animationDelay: `${index * 100}ms` }}
                            >
                                <div className="w-12 h-12 mb-6 flex items-center justify-center bg-[#0055FF] text-white rounded-lg group-hover:bg-[#0044CC] transition-colors duration-300">
                                    <feature.icon className="h-6 w-6" strokeWidth={1.5} />
                                </div>
                                <h3 className="font-sans text-xl font-bold text-slate-900 mb-3">
                                    {feature.title}
                                </h3>
                                <p className="text-slate-600 leading-relaxed">
                                    {feature.description}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Section */}
            <section className="py-16 bg-slate-50 border-y border-slate-200">
                <div className="container mx-auto px-6 text-center">
                    <div className="flex items-center justify-center gap-2 mb-4">
                        <Shield className="h-5 w-5 text-slate-500" strokeWidth={1.5} />
                        <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                            Sicuro e Affidabile
                        </span>
                    </div>
                    <p className="text-lg text-slate-700">
                        Utilizzato da <span className="font-semibold text-slate-900">oltre 500 studi legali</span> in Italia
                    </p>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-12 bg-white border-t border-slate-200">
                <div className="container mx-auto px-6">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                        <div className="flex items-center gap-2">
                            <Scale className="h-6 w-6 text-slate-400" strokeWidth={1.5} />
                            <span className="font-sans text-lg text-slate-600">Norma Facile</span>
                        </div>
                        <p className="text-sm text-slate-500">
                            © 2026 Norma Facile. Tutti i diritti riservati.
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
