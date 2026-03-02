/**
 * LegalFooter — Footer legale con P.IVA, link Privacy, Termini e Disclaimer.
 * Usato nella Landing Page e nel DashboardLayout.
 */
import { Link } from 'react-router-dom';

export function LegalFooter({ variant = 'light' }) {
    const isDark = variant === 'dark';
    return (
        <footer className={`py-3 px-6 text-center border-t ${isDark ? 'border-slate-700 bg-[#0F172A]' : 'border-slate-200 bg-white'}`} data-testid="legal-footer">
            <div className="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4 text-[10px]">
                <span className={isDark ? 'text-slate-500' : 'text-slate-400'}>
                    &copy; 2026 Steel Project Design S.R.L.S. &mdash; P.IVA 02042850897
                </span>
                <span className={`hidden sm:inline ${isDark ? 'text-slate-700' : 'text-slate-300'}`}>|</span>
                <div className="flex items-center gap-3">
                    <Link to="/legal/privacy" className={`hover:underline ${isDark ? 'text-slate-400 hover:text-slate-300' : 'text-slate-500 hover:text-slate-700'}`} data-testid="footer-privacy">
                        Privacy Policy
                    </Link>
                    <Link to="/legal/terms" className={`hover:underline ${isDark ? 'text-slate-400 hover:text-slate-300' : 'text-slate-500 hover:text-slate-700'}`} data-testid="footer-terms">
                        Termini di Servizio
                    </Link>
                    <Link to="/legal/disclaimer" className={`hover:underline ${isDark ? 'text-amber-500/70 hover:text-amber-400' : 'text-amber-600 hover:text-amber-700'}`} data-testid="footer-disclaimer">
                        Disclaimer EN 1090
                    </Link>
                </div>
            </div>
        </footer>
    );
}
