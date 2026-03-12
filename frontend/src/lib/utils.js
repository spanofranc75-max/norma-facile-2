/**
 * Utility functions for Norma Facile 2.0
 */
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export async function downloadPdfBlob(endpoint, filename) {
    const res = await fetch(`${API_BASE}/auth/download-token`, {
        method: 'POST', credentials: 'include',
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Errore autenticazione download');
    const { token } = await res.json();
    const sep = endpoint.includes('?') ? '&' : '?';
    const url = `${API_BASE}${endpoint}${sep}token=${encodeURIComponent(token)}`;
    (window.top || window).open(url, '_blank');
}

function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    if (token) return { 'Authorization': `Bearer ${token}` };
    return {};
}

export async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    const config = {
        ...options,
        credentials: 'include',
        headers: {
            ...getAuthHeaders(),
            ...options.headers,
        },
    };

    if (options.body && typeof options.body === 'object') {
        config.headers['Content-Type'] = 'application/json';
        config.body = JSON.stringify(options.body);
    } else if (options.body) {
        config.headers['Content-Type'] = 'application/json';
    }
    
    let response;
    try {
        response = await fetch(url, config);
    } catch {
        throw new Error('Errore di rete: impossibile raggiungere il server');
    }
    
    if (!response.ok) {
        let detail = `Errore ${response.status}`;
        try {
            const rawBody = await response.text();
            if (rawBody) {
                try {
                    const json = JSON.parse(rawBody);
                    detail = json.detail || json.message || json.error || detail;
                } catch {
                    if (rawBody.length < 200) detail = rawBody;
                }
            }
        } catch {}
        throw new Error(detail);
    }
    
    if (response.status === 204) return {};
    return response.json();
}

export function formatDateIT(date) {
    return new Intl.DateTimeFormat('it-IT', {
        day: 'numeric', month: 'long', year: 'numeric',
    }).format(new Date(date));
}

export function formatRelativeTimeIT(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days} giorn${days === 1 ? 'o' : 'i'} fa`;
    if (hours > 0) return `${hours} or${hours === 1 ? 'a' : 'e'} fa`;
    if (minutes > 0) return `${minutes} minut${minutes === 1 ? 'o' : 'i'} fa`;
    return 'Adesso';
}

export function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

export async function downloadFile(url, filename) {
    const headers = getAuthHeaders();
    const response = await fetch(url, { credentials: 'include', headers });
    if (!response.ok) {
        const errText = await response.text().catch(() => '');
        let detail = `HTTP ${response.status}`;
        try { detail = JSON.parse(errText).detail || detail; } catch {}
        throw new Error(detail);
    }
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = blobUrl;
    a.download = filename;
    a.target = '_blank';
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
    }, 2000);
}
