import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');

    if (!code) {
      navigate('/');
      return;
    }

    const redirectUri = window.location.origin + '/auth/callback';

    apiRequest('/auth/callback', {
      method: 'POST',
      body: { code, redirect_uri: redirectUri },
    })
      .then((data) => {
        // Salva il token in localStorage
        if (data.session_token) {
          localStorage.setItem('session_token', data.session_token);
        }
        setUser(data.user);
        navigate('/dashboard');
      })
      .catch((err) => {
        console.error('Auth callback error:', err);
        navigate('/');
      });
  }, []);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <p>Accesso in corso...</p>
    </div>
  );
}
