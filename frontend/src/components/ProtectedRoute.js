/**
 * Protected Route Component
 * Verifies authentication before rendering protected pages.
 */
import { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();
    const [authChecked, setAuthChecked] = useState(false);

    useEffect(() => {
        // Once loading is complete, mark auth as checked
        if (!loading) {
            setAuthChecked(true);
        }
    }, [loading]);

    // If user data passed from AuthCallback, render immediately
    if (location.state?.user) {
        return children;
    }

    // Show loading while checking auth
    if (loading || !authChecked) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    // Redirect to login if not authenticated
    if (!user) {
        return <Navigate to="/" replace />;
    }

    return children;
}
