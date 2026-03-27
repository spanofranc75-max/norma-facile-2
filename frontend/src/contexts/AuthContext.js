/**
 * Auth Context Provider for Norma Facile 2.0
 * 
 * Policy sessioni documentata:
 * - Max 5 sessioni contemporanee per utente (backend)
 * - Sessione rinnovata automaticamente dal backend quando si avvicina alla scadenza (< 2 giorni)
 * - Health check ogni 3 minuti quando l'utente è attivo
 * - Se 401 arriva da qualsiasi endpoint → mostra "Sessione scaduta", MAI svuotare dati componenti
 * - onAuthExpired callback collegato al layer API centralizzato (utils.js)
 * 
 * Supports both:
 *   - Direct Google OAuth (production, when REACT_APP_GOOGLE_CLIENT_ID is set)
 *   - Emergent Auth (preview environment)
 */
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { apiRequest, onAuthExpired } from '../lib/utils';

const AuthContext = createContext(null);

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;
const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_SCOPES = 'openid email profile';

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [sessionExpired, setSessionExpired] = useState(false);
    const [sessionExpiredDetail, setSessionExpiredDetail] = useState('');
    const healthCheckRef = useRef(null);

    const checkAuth = useCallback(async () => {
        const savedToken = localStorage.getItem('session_token');
        if (!savedToken) {
            setUser(null);
            setLoading(false);
            return false;
        }
        try {
            const userData = await apiRequest('/auth/me');
            setUser(userData);
            setSessionExpired(false);
            setSessionExpiredDetail('');
            return true;
        } catch (error) {
            localStorage.removeItem('session_token');
            setUser(null);
            return false;
        } finally {
            setLoading(false);
        }
    }, []);

    // Register global 401 interceptor — called from apiRequest on ANY 401
    useEffect(() => {
        onAuthExpired((detail) => {
            setSessionExpired(true);
            setSessionExpiredDetail(detail || 'Sessione scaduta');
            setUser(null);
            localStorage.removeItem('session_token');
            sessionStorage.removeItem('nf_was_authenticated');
        });
        return () => onAuthExpired(null);
    }, []);

    useEffect(() => {
        // Skip /me check if returning from OAuth callback
        if (window.location.hash?.includes('session_id=') ||
            window.location.search?.includes('code=')) {
            setLoading(false);
            return;
        }
        checkAuth();
    }, [checkAuth]);

    // Periodic session health check — every 3 minutes when user is active
    useEffect(() => {
        if (!user) {
            if (healthCheckRef.current) clearInterval(healthCheckRef.current);
            return;
        }
        healthCheckRef.current = setInterval(async () => {
            try {
                await apiRequest('/auth/me');
                // Session still valid — backend auto-renews if near expiry
            } catch {
                // onAuthExpired callback already handles the 401 → sessionExpired=true
            }
        }, 3 * 60 * 1000);
        return () => {
            if (healthCheckRef.current) clearInterval(healthCheckRef.current);
        };
    }, [user]);

    const login = () => {
        // Reset expired state before login
        setSessionExpired(false);
        setSessionExpiredDetail('');
        if (GOOGLE_CLIENT_ID) {
            // Direct Google OAuth (production)
            const redirectUri = window.location.origin + '/auth/callback';
            const params = new URLSearchParams({
                client_id: GOOGLE_CLIENT_ID,
                redirect_uri: redirectUri,
                response_type: 'code',
                scope: GOOGLE_SCOPES,
                access_type: 'offline',
                prompt: 'consent',
            });
            window.location.href = `${GOOGLE_AUTH_URL}?${params.toString()}`;
        } else {
            // Emergent Auth (preview)
            const redirectUrl = window.location.origin + '/dashboard';
            window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
        }
    };

    const logout = async () => {
        try {
            await apiRequest('/auth/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            localStorage.removeItem('session_token');
            setUser(null);
            setSessionExpired(false);
            sessionStorage.removeItem('nf_was_authenticated');
        }
    };

    const setAuthUser = (userData) => {
        if (userData?.session_token) {
            localStorage.setItem('session_token', userData.session_token);
        }
        setUser(userData);
        setLoading(false);
        setSessionExpired(false);
    };

    const value = {
        user,
        loading,
        login,
        logout,
        setAuthUser,
        checkAuth,
        isAuthenticated: !!user,
        sessionExpired,
        sessionExpiredDetail,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
