/**
 * ArticleSearch - Inline autocomplete for invoice line items.
 * Searches the Catalogo Articoli and populates line fields.
 */
import { useState, useRef, useEffect } from 'react';
import { apiRequest } from '../lib/utils';
import { Input } from './ui/input';
import { Search } from 'lucide-react';

const formatCurrency = (v) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v || 0);

export default function ArticleSearch({ value, onChange, onSelect, placeholder, testId }) {
    const [query, setQuery] = useState(value || '');
    const [results, setResults] = useState([]);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const wrapperRef = useRef(null);
    const debounceRef = useRef(null);

    // Sync external value
    useEffect(() => {
        setQuery(value || '');
    }, [value]);

    // Close on outside click
    useEffect(() => {
        const handleClick = (e) => {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const searchArticles = (q) => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        if (!q || q.length < 2) {
            setResults([]);
            setOpen(false);
            return;
        }
        debounceRef.current = setTimeout(async () => {
            setLoading(true);
            try {
                const data = await apiRequest(`/articoli/search?q=${encodeURIComponent(q)}`);
                setResults(data.results || []);
                setOpen(data.results?.length > 0);
            } catch {
                setResults([]);
            } finally {
                setLoading(false);
            }
        }, 250);
    };

    const handleChange = (e) => {
        const v = e.target.value;
        setQuery(v);
        onChange?.(v);
        searchArticles(v);
    };

    const handleSelect = (article) => {
        setOpen(false);
        setQuery(article.codice || '');
        onSelect?.(article);
    };

    return (
        <div ref={wrapperRef} className="relative">
            <div className="relative">
                <Input
                    data-testid={testId}
                    value={query}
                    onChange={handleChange}
                    onFocus={() => { if (results.length > 0) setOpen(true); }}
                    placeholder={placeholder || 'Cerca articolo...'}
                    className="h-8 text-sm pr-7"
                />
                <Search className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
            </div>

            {open && (
                <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-[200px] overflow-y-auto">
                    {loading ? (
                        <div className="p-2 text-center text-xs text-slate-400">Ricerca...</div>
                    ) : results.length === 0 ? (
                        <div className="p-2 text-center text-xs text-slate-400">Nessun risultato</div>
                    ) : (
                        results.map((art) => (
                            <button
                                key={art.articolo_id}
                                type="button"
                                data-testid={`article-result-${art.articolo_id}`}
                                className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-100 last:border-0 transition-colors"
                                onClick={() => handleSelect(art)}
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="font-mono text-xs font-semibold text-[#0055FF]">{art.codice}</span>
                                        <span className="ml-2 text-sm text-slate-700 truncate">{art.descrizione}</span>
                                    </div>
                                    <span className="text-xs font-mono text-slate-500">{formatCurrency(art.prezzo_unitario)}</span>
                                </div>
                            </button>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
