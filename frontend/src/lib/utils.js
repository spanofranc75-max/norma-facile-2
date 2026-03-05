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
        let rawBody = '';
        try {
            rawBody = await response.clone().text();
            console.error(`[apiRequest] ${response.status} response body:`, rawBody);
        } catch (readErr) {
            try {
                rawBody = await response.text();
            } catch {
                console.error('[apiRequest] Failed to read response body:', readErr);
            }
        }
        if (rawBody) {
            try {
                const err = JSON.parse(rawBody);
                if (err.detail) {
                    if (typeof err.detail === 'string') {
                        detail = err.detail;
                    } else if (Array.isArray(err.detail)) {
                        const messages = err.detail.map(e => {
                            const field = (e.loc || []).filter(l => l !== 'body').join('.');
                            return field ? `${field}: ${e.msg}` : e.msg;
                        });
                        detail = messages.join('; ');
                    } else {
                        detail = JSON.stringify(err.detail);
                    }
                }
            } catch {
                detail = rawBody.substring(0, 500);
            }
        }
        throw new Error(detail);
    }
    
    // Handle 204 No Content
    if (response.status === 204) return {};
    
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
