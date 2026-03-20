/**
 * Auth Callback Page - Handles OAuth redirect
 * Processes session_id from URL fragment and exchanges it for session.
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
        // Use useRef for processed flag to prevent race conditions under StrictMode
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const processAuth = async () => {
            try {
                // Extract session_id from URL fragment
                const hash = window.location.hash;
                const sessionIdMatch = hash.match(/session_id=([^&]+)/);
                
                if (!sessionIdMatch) {
                    console.error('No session_id found in URL');
                    navigate('/');
                    return;
                }

                const sessionId = sessionIdMatch[1];

                // Exchange session_id for user session via backend
                const user = await apiRequest('/auth/session', {
                    method: 'POST',
                    body: JSON.stringify({ session_id: sessionId }),
                });

                // Update auth context with user data
                setAuthUser(user);

                // Navigate to dashboard with user data
                navigate('/dashboard', { state: { user } });
            } catch (error) {
                console.error('Auth callback error:', error);
                console.error('Backend URL used:', process.env.REACT_APP_BACKEND_URL);
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
