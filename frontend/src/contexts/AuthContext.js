/**
 * Auth Context Provider for Norma Facile 2.0
 * Handles user authentication state and session management.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';

const AuthContext = createContext(null);

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

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
        // If returning from Google OAuth callback, skip the /me check.
        if (window.location.search?.includes('code=')) {
            setLoading(false);
            return;
        }
        checkAuth();
    }, [checkAuth]);

    const login = () => {
        const redirectUri = `${window.location.origin}/auth/callback`;
        const params = new URLSearchParams({
            client_id: GOOGLE_CLIENT_ID,
            redirect_uri: redirectUri,
            response_type: 'code',
            scope: 'openid email profile',
            access_type: 'offline',
            prompt: 'select_account',
        });
        window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
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
