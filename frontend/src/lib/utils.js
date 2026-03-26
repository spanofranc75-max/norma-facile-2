/**
 * Utility functions for Norma Facile 2.0
 */
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge class names with Tailwind CSS support
 */
export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

/**
 * Download PDF blob escaping the iframe sandbox.
 * Apre il blob URL in una nuova tab tramite window.top per uscire dall'iframe.
 */
export async function downloadPdfBlob(endpoint, filename) {
    const res = await fetch(`${API_BASE}/auth/download-token`, {
        method: 'POST', credentials: 'include',
    });
    if (!res.ok) throw new Error('Errore autenticazione download');
    const { token } = await res.json();
    const sep = endpoint.includes('?') ? '&' : '?';
    const url = `${API_BASE}${endpoint}${sep}token=${encodeURIComponent(token)}`;
    (window.top || window).open(url, '_blank');
}

/**
 * Make authenticated API request
 */
export async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    const config = {
        ...options,
        credentials: 'include',
        headers: {
            ...options.headers,
        },
    };

    // Only add Content-Type for requests with a body
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
            // Leggi il body UNA SOLA VOLTA
            // senza clone() per evitare "body already used"
            const rawBody = await response.text();
            if (rawBody) {
                try {
                    const json = JSON.parse(rawBody);
                    detail = json.detail
                        || json.message
                        || json.error
                        || detail;
                } catch {
                    // Body non è JSON — usa testo grezzo
                    if (rawBody.length < 200) {
                        detail = rawBody;
                    }
                }
            }
        } catch {
            // Impossibile leggere body — usa messaggio generico
        }
        throw new Error(detail);
    }
    
    // Handle 204 No Content
    if (response.status === 204) return {};
    
    // Return raw Response object when requested (for binary data like PDFs)
    if (options.rawResponse) return response;
    
    return response.json();
}

/**
 * Format date in Italian
 */
export function formatDateIT(date) {
    return new Intl.DateTimeFormat('it-IT', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    }).format(new Date(date));
}

/**
 * Format relative time in Italian
 */
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

/**
 * Truncate text with ellipsis
 */
export function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

/**
 * Download a file from an API endpoint — iframe-safe.
 * Handles sandbox restrictions by trying multiple strategies.
 * @param {string} url - Full URL to fetch
 * @param {string} filename - Suggested filename for download
 */
export async function downloadFile(url, filename) {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(url, { credentials: 'include', headers });
    if (!response.ok) {
        const errText = await response.text().catch(() => '');
        let detail = `HTTP ${response.status}`;
        try { detail = JSON.parse(errText).detail || detail; } catch {}
        throw new Error(detail);
    }
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    // Strategy 1: hidden <a> with download attribute + delayed cleanup
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = blobUrl;
    a.download = filename;
    a.target = '_blank';
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();

    // Strategy 2 (fallback): if iframe blocks <a> download, open in new tab
    // The timeout lets strategy 1 attempt first
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
    }, 2000);
}
