/**
 * Protected Route Component
 * Verifies authentication before rendering protected pages.
 */
import { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children }) {
    const { user, loading, checkAuth } = useAuth();
    const location = useLocation();
    const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);

    useEffect(() => {
        // If user data passed from AuthCallback, skip auth check
        if (location.state?.user) return;

        const verifyAuth = async () => {
            try {
                await checkAuth();
                setIsAuthenticated(true);
            } catch (error) {
                setIsAuthenticated(false);
            }
        };

        if (!user && !loading) {
            verifyAuth();
        } else if (user) {
            setIsAuthenticated(true);
        }
    }, [user, loading, checkAuth, location.state]);

    // Show loading while checking auth
    if (loading || isAuthenticated === null) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    // Redirect to login if not authenticated
    if (isAuthenticated === false && !user) {
        return <Navigate to="/" replace />;
    }

    return children;
}
