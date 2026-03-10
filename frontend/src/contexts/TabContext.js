/**
 * TabContext — Multi-tab navigation manager
 * Max 4 tabs, in-memory draft persistence, no localStorage.
 */
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';

const TabContext = createContext(null);

/** Derive a short title from a path */
function titleFromPath(path) {
    const map = {
        '/dashboard': 'Dashboard',
        '/clients': 'Clienti',
        '/preventivi': 'Preventivi',
        '/invoices': 'Fatturazione',
        '/ddt': 'DDT',
        '/distinte': 'Distinte',
        '/rilievi': 'Rilievi',
        '/perizie': 'Perizie',
        '/sopralluoghi': 'Sopralluoghi',
        '/planning': 'Planning',
        '/tracciabilita': 'Tracciabilita',
        '/settings': 'Impostazioni',
        '/fatture-ricevute': 'Fatture Ricevute',
        '/controllo-costi': 'Controllo Costi',
        '/analisi-margini': 'Analisi Margini',
        '/ebitda': 'EBITDA',
        '/fornitori': 'Fornitori',
        '/catalogo': 'Catalogo',
        '/articoli': 'Articoli',
        '/certificazioni': 'Certificazioni',
        '/sicurezza': 'Sicurezza',
        '/notifiche': 'Notifiche',
        '/quality-hub': 'Quality Hub',
        '/scadenziario': 'Scadenziario',
        '/movimenti-bancari': 'Movimenti',
        '/configurazione-finanziaria': 'Costo Aziendale',
    };
    // Exact match
    if (map[path]) return map[path];
    // Prefix match (e.g. /invoices/new → Fatturazione)
    const prefix = Object.keys(map).find(k => path.startsWith(k + '/'));
    if (prefix) return map[prefix];
    // Fallback
    const seg = path.split('/').filter(Boolean).pop() || 'Pagina';
    return seg.charAt(0).toUpperCase() + seg.slice(1);
}

let _tabIdCounter = 0;
function nextTabId() {
    _tabIdCounter += 1;
    return `tab-${_tabIdCounter}`;
}

const MAX_TABS = 4;

export function TabProvider({ children }) {
    const navigate = useNavigate();
    const location = useLocation();

    // Drafts stored by path (survives tab close)
    const draftsRef = useRef({});

    const [tabs, setTabs] = useState(() => {
        const initial = {
            id: nextTabId(),
            title: titleFromPath(location.pathname),
            path: location.pathname,
            icon: null,
            isDirty: false,
        };
        return [initial];
    });
    const [activeTabId, setActiveTabId] = useState(tabs[0]?.id);

    /** Open a tab — reuse if path matches, else create new */
    const openTab = useCallback((path, title, icon) => {
        setTabs(prev => {
            const existing = prev.find(t => t.path === path);
            if (existing) {
                setActiveTabId(existing.id);
                navigate(path);
                return prev;
            }
            if (prev.length >= MAX_TABS) {
                toast.warning('Massimo 4 tab aperte. Chiudi una tab per aprirne un\'altra.');
                return prev;
            }
            const newTab = {
                id: nextTabId(),
                title: title || titleFromPath(path),
                path,
                icon: icon || null,
                isDirty: false,
            };
            setActiveTabId(newTab.id);
            navigate(path);
            return [...prev, newTab];
        });
    }, [navigate]);

    /** Close a tab */
    const closeTab = useCallback((id) => {
        setTabs(prev => {
            if (prev.length <= 1) return prev; // don't close last tab
            const idx = prev.findIndex(t => t.id === id);
            if (idx === -1) return prev;
            const tab = prev[idx];
            // Save draft before closing
            if (tab.isDirty && draftsRef.current[tab.path]) {
                // draft already stored via setTabDirty
            }
            const next = prev.filter(t => t.id !== id);
            // If closing active tab, switch to adjacent
            if (id === activeTabId) {
                const newActive = next[Math.min(idx, next.length - 1)];
                setActiveTabId(newActive.id);
                navigate(newActive.path);
            }
            return next;
        });
    }, [activeTabId, navigate]);

    /** Switch to a tab */
    const switchTab = useCallback((id) => {
        setTabs(prev => {
            const tab = prev.find(t => t.id === id);
            if (tab) {
                setActiveTabId(id);
                navigate(tab.path);
            }
            return prev;
        });
    }, [navigate]);

    /** Mark tab as dirty + store draft data */
    const setTabDirty = useCallback((id, draftData) => {
        setTabs(prev => prev.map(t => {
            if (t.id !== id) return t;
            if (draftData === null) {
                // Clear draft
                delete draftsRef.current[t.path];
                return { ...t, isDirty: false };
            }
            draftsRef.current[t.path] = draftData;
            return { ...t, isDirty: true };
        }));
    }, []);

    /** Get draft for a path */
    const getTabDraft = useCallback((path) => {
        return draftsRef.current[path] || null;
    }, []);

    /** Sync active tab path on route change (e.g. from sidebar navigate) */
    const updateActiveTabPath = useCallback((newPath) => {
        setTabs(prev => prev.map(t => {
            if (t.id !== activeTabId) return t;
            return { ...t, path: newPath, title: titleFromPath(newPath) };
        }));
    }, [activeTabId]);

    return (
        <TabContext.Provider value={{
            tabs, activeTabId,
            openTab, closeTab, switchTab,
            setTabDirty, getTabDraft,
            updateActiveTabPath,
        }}>
            {children}
        </TabContext.Provider>
    );
}

export function useTabContext() {
    const ctx = useContext(TabContext);
    if (!ctx) throw new Error('useTabContext must be used within TabProvider');
    return ctx;
}
