/**
 * Protected Route Component
 * Verifies authentication before rendering protected pages.
 * CRITICAL: Once authenticated, NEVER unmount children (prevents form data loss).
 */
import { useState, useEffect, useRef } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();
    const wasAuthenticated = useRef(false);

    // Once user is authenticated, remember it permanently for this mount
    if (user) {
        wasAuthenticated.current = true;
    }

    // If user data passed from AuthCallback, render immediately
    if (location.state?.user) {
        return children;
    }

    // Show loading ONLY on initial auth check, never after
    if (loading && !wasAuthenticated.current) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    // Redirect to login if not authenticated and never was
    if (!user && !wasAuthenticated.current) {
        return <Navigate to="/" replace />;
    }

    return children;
}
