/**
 * Protected Route Component
 * Verifies authentication before rendering protected pages.
 * CRITICAL: Once authenticated, NEVER show loading spinner or redirect silently.
 * Uses both ref and sessionStorage to survive component remounts (e.g., from ErrorBoundary recovery).
 */
import { useRef } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AUTH_FLAG_KEY = 'nf_was_authenticated';

export default function ProtectedRoute({ children }) {
    const { user, loading, login, sessionExpired } = useAuth();
    const location = useLocation();
    const wasAuthenticated = useRef(sessionStorage.getItem(AUTH_FLAG_KEY) === '1');

    // Once user is authenticated, remember it permanently (survives remounts via sessionStorage)
    if (user) {
        wasAuthenticated.current = true;
        try { sessionStorage.setItem(AUTH_FLAG_KEY, '1'); } catch {}
    }

    // If user data passed from AuthCallback, render immediately
    if (location.state?.user) {
        return children;
    }

    // Show loading ONLY on the very first auth check of the entire browser session
    if (loading && !wasAuthenticated.current) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    // Session expired while user was active — show clear message
    if (sessionExpired || (!user && wasAuthenticated.current)) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="text-center space-y-4 p-8 max-w-sm">
                    <div className="w-12 h-12 mx-auto bg-amber-100 rounded-full flex items-center justify-center">
                        <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h2 className="text-lg font-semibold text-slate-800">Sessione scaduta</h2>
                    <p className="text-sm text-slate-500">La tua sessione è scaduta. Effettua di nuovo l'accesso per continuare.</p>
                    <button
                        onClick={() => {
                            sessionStorage.removeItem(AUTH_FLAG_KEY);
                            login();
                        }}
                        className="px-6 py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-medium hover:bg-[#0044CC] transition-colors"
                        data-testid="btn-relogin"
                    >
                        Accedi di nuovo
                    </button>
                </div>
            </div>
        );
    }

    // Redirect to login only if truly unauthenticated (first visit, no prior session)
    if (!user && !wasAuthenticated.current) {
        return <Navigate to="/" replace />;
    }

    return children;
}
