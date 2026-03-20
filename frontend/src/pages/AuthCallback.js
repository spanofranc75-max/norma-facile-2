/**
 * Auth Callback Page - Handles OAuth redirect
 * Supports both:
 *   - Google OAuth code exchange (URL query: ?code=xxx)
 *   - Emergent Auth session exchange (URL hash: #session_id=xxx)
 */
import { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../lib/utils';

export default function AuthCallback() {
    const navigate = useNavigate();
    const location = useLocation();
    const { setAuthUser } = useAuth();
    const hasProcessed = useRef(false);

    useEffect(() => {
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const processAuth = async () => {
            try {
                const hash = window.location.hash;
                const searchParams = new URLSearchParams(window.location.search);
                const code = searchParams.get('code');

                let user;

                if (code) {
                    // Google OAuth: exchange code for session
                    const redirectUri = window.location.origin + '/auth/callback';
                    user = await apiRequest('/auth/callback', {
                        method: 'POST',
                        body: JSON.stringify({ code, redirect_uri: redirectUri }),
                    });
                } else if (hash?.includes('session_id=')) {
                    // Emergent Auth: exchange session_id
                    const sessionIdMatch = hash.match(/session_id=([^&]+)/);
                    if (!sessionIdMatch) {
                        console.error('No session_id found in URL');
                        navigate('/');
                        return;
                    }
                    user = await apiRequest('/auth/session', {
                        method: 'POST',
                        body: JSON.stringify({ session_id: sessionIdMatch[1] }),
                    });
                } else {
                    console.error('No auth credentials found in URL');
                    navigate('/');
                    return;
                }

                setAuthUser(user);
                navigate('/dashboard', { state: { user } });
            } catch (error) {
                console.error('Auth callback error:', error);
                navigate('/');
            }
        };

        processAuth();
    }, [navigate, setAuthUser, location]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="text-center">
                <div className="w-8 h-8 loading-spinner mx-auto mb-4" />
                <p className="text-slate-600">Autenticazione in corso...</p>
            </div>
        </div>
    );
}
