import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    Sparkles, ClipboardList, Receipt, Truck, Briefcase, Package,
    Shield, HardHat, Users, Settings, ShieldAlert, Ruler, BarChart3,
    Brain, Target, FileText, LayoutGrid, TrendingUp, Calendar,
} from 'lucide-react';

// Map paths to icons and labels
const PATH_META = {
    '/dashboard': { icon: Sparkles, label: 'Dashboard' },
    '/executive': { icon: TrendingUp, label: 'Cruscotto' },
    '/clients': { icon: Users, label: 'Clienti' },
    '/preventivi': { icon: ClipboardList, label: 'Preventivi' },
    '/preventivatore': { icon: Brain, label: 'AI Predittivo' },
    '/kpi': { icon: Target, label: 'KPI' },
    '/invoices': { icon: Receipt, label: 'Fatture' },
    '/ddt': { icon: Truck, label: 'DDT' },
    '/planning': { icon: LayoutGrid, label: 'Planning' },
    '/distinte': { icon: Package, label: 'Distinte' },
    '/tracciabilita': { icon: Shield, label: 'Tracciabilita' },
    '/sicurezza': { icon: HardHat, label: 'Sicurezza POS' },
    '/certificazioni': { icon: Shield, label: 'Certificazioni' },
    '/sopralluoghi': { icon: ShieldAlert, label: 'Sopralluoghi' },
    '/rilievi': { icon: Ruler, label: 'Rilievi' },
    '/perizie': { icon: ShieldAlert, label: 'Perizie' },
    '/settings': { icon: Settings, label: 'Impostazioni' },
    '/analisi-margini': { icon: BarChart3, label: 'Margini' },
    '/fatture-ricevute': { icon: FileText, label: 'Fatt. Ricevute' },
    '/scadenziario': { icon: Calendar, label: 'Scadenziario' },
};

// Editor patterns: extract doc number from path
const EDITOR_PATTERNS = [
    { pattern: /^\/preventivi\/(.+)/, base: '/preventivi', prefix: 'PRV' },
    { pattern: /^\/invoices\/(.+?)(?:\/|$)/, base: '/invoices', prefix: 'FAT' },
    { pattern: /^\/ddt\/(.+?)(?:\/|$)/, base: '/ddt', prefix: 'DDT' },
    { pattern: /^\/distinte\/(.+)/, base: '/distinte', prefix: 'DIST' },
    { pattern: /^\/sopralluoghi\/(.+)/, base: '/sopralluoghi', prefix: 'SOP' },
    { pattern: /^\/perizie\/(.+)/, base: '/perizie', prefix: 'PER' },
    { pattern: /^\/analisi-ai\/(.+)/, base: '/preventivi', prefix: 'AI' },
];

function getTabMeta(path) {
    // Check editor patterns first
    for (const ep of EDITOR_PATTERNS) {
        const m = path.match(ep.pattern);
        if (m) {
            const baseMeta = PATH_META[ep.base] || { icon: FileText, label: ep.prefix };
            const docId = m[1].substring(0, 12);
            return {
                icon: baseMeta.icon,
                label: `${baseMeta.label} · ${docId}`,
                basePath: ep.base,
            };
        }
    }
    // Direct match
    const direct = PATH_META[path];
    if (direct) return { ...direct, basePath: path };
    // Partial match
    for (const [p, meta] of Object.entries(PATH_META)) {
        if (path.startsWith(p + '/')) return { ...meta, basePath: p };
    }
    return { icon: FileText, label: path.split('/').pop() || 'Pagina', basePath: path };
}

const MAX_TABS = 8;
const TabContext = createContext(null);

export function TabProvider({ children }) {
    const [tabs, setTabs] = useState([]);
    const scrollCache = useRef({});
    const navigate = useNavigate();
    const location = useLocation();

    const openTab = useCallback((path, customLabel) => {
        // Save current scroll position before navigating
        if (location.pathname) {
            scrollCache.current[location.pathname] = window.scrollY;
        }

        setTabs(prev => {
            // Check if tab already exists
            const existing = prev.find(t => t.path === path);
            if (existing) {
                navigate(path);
                return prev;
            }

            const meta = getTabMeta(path);
            const newTab = {
                id: `tab_${Date.now()}`,
                path,
                label: customLabel || meta.label,
                icon: meta.icon,
                basePath: meta.basePath,
                timestamp: Date.now(),
            };

            let next = [...prev, newTab];
            // Enforce max tabs — remove oldest
            if (next.length > MAX_TABS) {
                next = next.slice(next.length - MAX_TABS);
            }

            navigate(path);
            return next;
        });
    }, [navigate, location.pathname]);

    const closeTab = useCallback((path) => {
        setTabs(prev => {
            const next = prev.filter(t => t.path !== path);
            // If closing active tab, navigate to the previous one
            if (location.pathname === path && next.length > 0) {
                const last = next[next.length - 1];
                navigate(last.path);
            } else if (next.length === 0) {
                navigate('/dashboard');
            }
            delete scrollCache.current[path];
            return next;
        });
    }, [navigate, location.pathname]);

    const switchTab = useCallback((path) => {
        // Save current scroll
        if (location.pathname) {
            scrollCache.current[location.pathname] = window.scrollY;
        }
        navigate(path);
        // Restore scroll for target tab
        setTimeout(() => {
            const saved = scrollCache.current[path];
            if (saved !== undefined) window.scrollTo(0, saved);
        }, 50);
    }, [navigate, location.pathname]);

    // Update tab label dynamically (e.g., when doc number loads)
    const updateTabLabel = useCallback((path, label) => {
        setTabs(prev => prev.map(t => t.path === path ? { ...t, label } : t));
    }, []);

    // Sync: ensure current path has a tab
    const ensureTab = useCallback((path, customLabel) => {
        setTabs(prev => {
            if (prev.find(t => t.path === path)) return prev;
            const meta = getTabMeta(path);
            let next = [...prev, {
                id: `tab_${Date.now()}`,
                path,
                label: customLabel || meta.label,
                icon: meta.icon,
                basePath: meta.basePath,
                timestamp: Date.now(),
            }];
            if (next.length > MAX_TABS) next = next.slice(next.length - MAX_TABS);
            return next;
        });
    }, []);

    return (
        <TabContext.Provider value={{ tabs, openTab, closeTab, switchTab, updateTabLabel, ensureTab }}>
            {children}
        </TabContext.Provider>
    );
}

export function useTabContext() {
    return useContext(TabContext);
}
