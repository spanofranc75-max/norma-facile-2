/**
 * Auth Callback Page - Handles Google OAuth redirect
 * Processes 'code' from URL query string and exchanges it for session.
 */
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../lib/utils';

export default function AuthCallback() {
    const navigate = useNavigate();
    const { setAuthUser } = useAuth();
    const hasProcessed = useRef(false);

    useEffect(() => {
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const processAuth = async () => {
            try {
                // Google OAuth sends 'code' as a query parameter
                const params = new URLSearchParams(window.location.search);
                const code = params.get('code');

                if (!code) {
                    console.error('No code found in URL');
                    navigate('/');
                    return;
                }

                // The redirect_uri must match exactly what's registered in Google Console
                const redirectUri = `${window.location.origin}/auth/callback`;

                // Exchange code for user session via backend
                const user = await apiRequest('/auth/callback', {
                    method: 'POST',
                    body: JSON.stringify({ code, redirect_uri: redirectUri }),
                });

                setAuthUser(user);
                navigate('/dashboard', { state: { user } });

            } catch (error) {
                console.error('Auth callback error:', error);
                navigate('/');
            }
        };

        processAuth();
    }, [navigate, setAuthUser]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="text-center">
                <div className="w-8 h-8 loading-spinner mx-auto mb-4" />
                <p className="text-slate-600">Autenticazione in corso...</p>
            </div>
        </div>
    );
}

