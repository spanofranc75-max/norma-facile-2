import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiRequest } from '../lib/utils';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const userData = await apiRequest('/auth/me');
      setUser(userData);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
    const redirectUri = window.location.origin + '/auth/callback';
    const scope = 'openid email profile';
    const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&prompt=select_account`;
    window.location.href = url;
  };

  const logout = async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch {}
    localStorage.removeItem('session_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};
