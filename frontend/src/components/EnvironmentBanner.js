/**
 * EnvironmentBanner — Shows current environment, host, version and DB label.
 * Always visible at the bottom of the page, color-coded by environment type.
 */
import { useState, useEffect } from 'react';
import { Monitor, Database, Globe, ChevronUp, ChevronDown } from 'lucide-react';

const ENV_COLORS = {
    production: { bg: 'bg-emerald-600', text: 'text-white', dot: 'bg-emerald-300', label: 'PRODUZIONE' },
    staging: { bg: 'bg-amber-500', text: 'text-white', dot: 'bg-amber-200', label: 'STAGING' },
    preview: { bg: 'bg-blue-600', text: 'text-white', dot: 'bg-blue-300', label: 'PREVIEW' },
    demo: { bg: 'bg-purple-600', text: 'text-white', dot: 'bg-purple-300', label: 'DEMO' },
    unknown: { bg: 'bg-slate-600', text: 'text-white', dot: 'bg-slate-300', label: 'SCONOSCIUTO' },
};

function detectEnvironment() {
    const host = window.location.hostname;
    if (host.includes('app.1090normafacile.it')) return 'production';
    if (host.includes('1090normafacile.it')) return 'production';
    if (host.includes('vercel.app')) return 'staging';
    if (host.includes('preview.emergentagent.com')) return 'preview';
    if (host.includes('emergent.host')) return 'staging';
    if (host === 'localhost' || host === '127.0.0.1') return 'demo';
    return 'unknown';
}

export default function EnvironmentBanner() {
    const [expanded, setExpanded] = useState(false);
    const [healthData, setHealthData] = useState(null);
    const env = detectEnvironment();
    const style = ENV_COLORS[env];
    const host = window.location.hostname;

    useEffect(() => {
        const url = process.env.REACT_APP_BACKEND_URL || '';
        fetch(`${url}/api/health`)
            .then(r => r.json())
            .then(data => setHealthData(data))
            .catch(() => {});
    }, []);

    return (
        <div className={`fixed bottom-0 left-0 right-0 z-50 ${style.bg} ${style.text} text-xs shadow-lg`} data-testid="environment-banner">
            <div
                className="flex items-center justify-between px-4 py-1.5 cursor-pointer select-none"
                onClick={() => setExpanded(!expanded)}
                data-testid="env-banner-toggle"
            >
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5">
                        <span className={`inline-block w-2 h-2 rounded-full ${style.dot} animate-pulse`} />
                        <span className="font-bold tracking-wide">{style.label}</span>
                    </div>
                    <span className="opacity-70 hidden sm:inline">
                        <Globe className="inline h-3 w-3 mr-1" />{host}
                    </span>
                    {healthData?.version && (
                        <span className="opacity-70 hidden sm:inline">v{healthData.version}</span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="opacity-60 hidden sm:inline">1090 Norma Facile</span>
                    {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
                </div>
            </div>
            {expanded && (
                <div className="px-4 pb-2 pt-1 border-t border-white/20 grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="flex items-center gap-1.5">
                        <Monitor className="h-3 w-3 opacity-70" />
                        <span>Ambiente: <strong>{style.label}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <Globe className="h-3 w-3 opacity-70" />
                        <span>Host: <strong>{host}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <Database className="h-3 w-3 opacity-70" />
                        <span>DB: <strong>{healthData?.environment?.db_name || '...'}</strong></span>
                    </div>
                    <div>
                        Versione: <strong>{healthData?.version || '...'}</strong>
                    </div>
                </div>
            )}
        </div>
    );
}
