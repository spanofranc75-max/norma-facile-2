/**
 * GlobalSearchBar — Searchbar with debounce + dropdown results
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Search, FileText, Users, Truck, ClipboardList, X } from 'lucide-react';

const TYPE_CONFIG = {
    commessa: { icon: ClipboardList, color: 'text-blue-600 bg-blue-50', label: 'Commessa' },
    preventivo: { icon: FileText, color: 'text-amber-600 bg-amber-50', label: 'Preventivo' },
    cliente: { icon: Users, color: 'text-emerald-600 bg-emerald-50', label: 'Cliente' },
    ddt: { icon: Truck, color: 'text-violet-600 bg-violet-50', label: 'DDT' },
};

export default function GlobalSearchBar() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [selectedIdx, setSelectedIdx] = useState(-1);
    const inputRef = useRef(null);
    const containerRef = useRef(null);
    const navigate = useNavigate();
    const debounceRef = useRef(null);

    const search = useCallback(async (q) => {
        if (q.length < 2) { setResults([]); setOpen(false); return; }
        setLoading(true);
        try {
            const data = await apiRequest(`/search/?q=${encodeURIComponent(q)}&limit=12`);
            setResults(data.results || []);
            setOpen(true);
        } catch { setResults([]); }
        finally { setLoading(false); }
    }, []);

    const handleChange = (e) => {
        const val = e.target.value;
        setQuery(val);
        setSelectedIdx(-1);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => search(val), 300);
    };

    const handleSelect = (result) => {
        setOpen(false);
        setQuery('');
        navigate(result.url);
    };

    const handleKeyDown = (e) => {
        if (!open || results.length === 0) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIdx(prev => Math.min(prev + 1, results.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIdx(prev => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter' && selectedIdx >= 0) {
            e.preventDefault();
            handleSelect(results[selectedIdx]);
        } else if (e.key === 'Escape') {
            setOpen(false);
        }
    };

    // Close dropdown on click outside
    useEffect(() => {
        const handler = (e) => {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Keyboard shortcut: Ctrl+K or Cmd+K to focus
    useEffect(() => {
        const handler = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                inputRef.current?.focus();
            }
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, []);

    return (
        <div ref={containerRef} className="relative w-full max-w-md" data-testid="global-search-container">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                    ref={inputRef}
                    data-testid="global-search-input"
                    type="text"
                    value={query}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    onFocus={() => { if (results.length > 0) setOpen(true); }}
                    placeholder="Cerca commesse, preventivi, clienti... (Ctrl+K)"
                    className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 placeholder:text-slate-400"
                />
                {query && (
                    <button
                        onClick={() => { setQuery(''); setResults([]); setOpen(false); }}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-slate-100"
                    >
                        <X className="h-3.5 w-3.5 text-slate-400" />
                    </button>
                )}
            </div>

            {open && (
                <div
                    data-testid="global-search-dropdown"
                    className="absolute top-full mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg z-[60] max-h-80 overflow-y-auto"
                >
                    {loading && <p className="px-4 py-3 text-xs text-slate-400">Ricerca in corso...</p>}
                    {!loading && results.length === 0 && (
                        <p className="px-4 py-3 text-xs text-slate-400">Nessun risultato per "{query}"</p>
                    )}
                    {results.map((r, i) => {
                        const cfg = TYPE_CONFIG[r.type] || TYPE_CONFIG.commessa;
                        const Icon = cfg.icon;
                        return (
                            <button
                                key={`${r.type}-${r.id}`}
                                data-testid={`search-result-${r.type}-${i}`}
                                onClick={() => handleSelect(r)}
                                className={`flex items-center gap-3 w-full px-4 py-2.5 text-left hover:bg-slate-50 transition-colors ${
                                    i === selectedIdx ? 'bg-blue-50' : ''
                                }`}
                            >
                                <span className={`flex items-center justify-center w-7 h-7 rounded-md ${cfg.color}`}>
                                    <Icon className="h-3.5 w-3.5" />
                                </span>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium text-slate-800 truncate">{r.label}</span>
                                        <span className="text-[10px] font-medium text-slate-400 uppercase">{cfg.label}</span>
                                    </div>
                                    {r.subtitle && (
                                        <p className="text-xs text-slate-500 truncate">{r.subtitle}</p>
                                    )}
                                </div>
                                {r.extra && r.extra !== r.subtitle && (
                                    <span className="text-[10px] text-slate-400 flex-shrink-0">{r.extra}</span>
                                )}
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
