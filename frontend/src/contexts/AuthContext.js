/**
 * Auth Context Provider for Norma Facile 2.0
 * Handles user authentication state and session management.
 * Supports both:
 *   - Direct Google OAuth (production, when REACT_APP_GOOGLE_CLIENT_ID is set)
 *   - Emergent Auth (preview environment)
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';

const AuthContext = createContext(null);

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;
const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_SCOPES = 'openid email profile';

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const userData = await apiRequest('/auth/me');
            setUser(userData);
        } catch (error) {
            setUser(null);
        } finally {
            setLoading(false);
        }
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

    const login = () => {
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
            setUser(null);
        }
    };

    const setAuthUser = (userData) => {
        setUser(userData);
        setLoading(false);
    };

    const value = {
        user,
        loading,
        login,
        logout,
        setAuthUser,
        checkAuth,
        isAuthenticated: !!user,
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
