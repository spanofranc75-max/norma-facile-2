/**
 * Protected Route Component
 * Verifies authentication before rendering protected pages.
 * CRITICAL: Once authenticated, NEVER show loading spinner or redirect.
 * Uses both ref and sessionStorage to survive component remounts (e.g., from ErrorBoundary recovery).
 */
import { useRef } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AUTH_FLAG_KEY = 'nf_was_authenticated';

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
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

    // Redirect to login only if truly unauthenticated (first visit, no prior session)
    if (!user && !wasAuthenticated.current) {
        return <Navigate to="/" replace />;
    }

    return children;
}
