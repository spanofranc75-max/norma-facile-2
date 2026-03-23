/**
 * Dashboard Layout — Accordion Sidebar Navigation
 * Groups: Dashboard, Commerciale, Produzione, Certificazioni, Acquisti, Perizie, Impostazioni
 * Responsive: hamburger menu on mobile, slide-out sidebar with backdrop
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { LegalFooter } from './LegalFooter';
import GlobalSearchBar from './GlobalSearchBar';
import DemoBanner from './DemoBanner';
import {
    Sparkles, Receipt, Users, Settings, Ruler, Package, Shield,
    HardHat, Warehouse, ClipboardList, Truck, Factory, ShieldAlert,
    BarChart3, BoxIcon, FileInput, Camera, ChevronDown,
    Briefcase, Wrench, Award, ShoppingCart, FileText, LayoutGrid,
    CreditCard, TrendingUp, ClipboardCheck, Calendar, CircleDollarSign,
    User, LogOut, Bell, Flame, Calculator, ScrollText, Menu, X, Archive, Brain, Target,
    BookOpen, FlaskConical, PenSquare,
} from 'lucide-react';

// ── Navigation Structure ────────────────────────────────────────
// roles: which roles can see this group/link. Empty = all.
const NAV_GROUPS = [
    {
        id: 'dashboard',
        label: 'Dashboard',
        icon: Sparkles,
        type: 'link',
        path: '/dashboard',
        roles: [],
    },
    {
        id: 'executive',
        label: 'Cruscotto Executive',
        icon: TrendingUp,
        type: 'link',
        path: '/executive',
        roles: ['admin'],
    },
    {
        id: 'cruscotto-cantiere',
        label: 'Dashboard Cantiere',
        icon: ClipboardCheck,
        type: 'link',
        path: '/cruscotto-cantiere',
        roles: ['admin', 'ufficio_tecnico'],
    },
    {
        id: 'ebitda',
        label: 'Analisi Finanziaria',
        icon: TrendingUp,
        type: 'link',
        path: '/ebitda',
        roles: ['admin', 'amministrazione'],
    },
    {
        id: 'notifiche',
        label: 'Notifiche',
        icon: Bell,
        type: 'link',
        path: '/notifiche',
        roles: ['admin', 'ufficio_tecnico'],
    },
    {
        id: 'commerciale',
        label: 'Commerciale',
        icon: Briefcase,
        type: 'group',
        roles: ['admin', 'ufficio_tecnico', 'amministrazione'],
        children: [
            { path: '/clients', label: 'Clienti', icon: Users },
            { path: '/preventivi', label: 'Preventivi', icon: ClipboardList },
            { path: '/preventivatore', label: 'AI Predittivo', icon: Brain },
            { path: '/kpi', label: 'Dashboard KPI', icon: Target },
            { path: '/invoices', label: 'Fatturazione', icon: Receipt, roles: ['admin', 'amministrazione'] },
            { path: '/ddt', label: 'DDT', icon: Truck },
        ],
    },
    {
        id: 'produzione',
        label: 'Produzione',
        icon: Wrench,
        type: 'group',
        roles: ['admin', 'ufficio_tecnico', 'officina'],
        children: [
            { path: '/planning', label: 'Planning Cantieri', icon: LayoutGrid },
            { path: '/distinte', label: 'Distinte', icon: Package },
            { path: '/tracciabilita', label: 'Tracciabilit\u00e0 EN 1090', icon: Shield },
            { path: '/sicurezza', label: 'Sicurezza POS', icon: HardHat },
            { path: '/pacchetti-documentali', label: 'Pacchetti Documentali', icon: FileInput },
        ],
    },
    {
        id: 'certificazioni',
        label: 'Certificazioni',
        icon: Award,
        type: 'group',
        roles: ['admin', 'ufficio_tecnico'],
        children: [
            { path: '/quality-hub', label: 'Quality Hub', icon: LayoutGrid },
            { path: '/certificazioni', label: 'Certificazioni CE', icon: Shield },
            { path: '/core-engine', label: 'Core Engine', icon: Shield },
            { path: '/validazione-foto', label: 'Validazione Foto AI', icon: Camera },
            { path: '/report-cam', label: 'Sostenibilita & CO2', icon: Award },
            { path: '/sistema-qualita', label: 'Sistema Qualita', icon: FileText },
            { path: '/strumenti', label: 'Apparecchiature', icon: Wrench },
            { path: '/wps', label: 'WPS (Procedure)', icon: Flame },
            { path: '/audit', label: 'Audit & NC', icon: ClipboardCheck },
            { path: '/attrezzature', label: 'Scadenzario Attrezzature', icon: Wrench },
            { path: '/manutenzioni', label: 'Scadenziario Manutenzioni', icon: Calendar },
            { path: '/verbali-itt', label: 'Verbali ITT', icon: Award },
            { path: '/validazione-p1', label: 'Validazione AI (P1)', icon: FlaskConical },
        ],
    },
    {
        id: 'risorse_umane',
        label: 'Risorse Umane',
        icon: Users,
        type: 'group',
        roles: ['admin', 'ufficio_tecnico'],
        children: [
            { path: '/operai', label: 'Anagrafica Operai', icon: Users },
            { path: '/operai/matrice', label: 'Matrice Scadenze', icon: Shield },
        ],
    },
    {
        id: 'acquisti',
        label: 'Acquisti & Magazzino',
        icon: ShoppingCart,
        type: 'group',
        roles: ['admin', 'amministrazione'],
        children: [
            { path: '/fatture-ricevute', label: 'Fatture Ricevute', icon: FileInput },
            { path: '/controllo-costi', label: 'Controllo Costi', icon: CircleDollarSign },
            { path: '/analisi-margini', label: 'Analisi Margini', icon: BarChart3 },
            { path: '/configurazione-finanziaria', label: 'Costo Aziendale', icon: Calculator },
            { path: '/scadenziario', label: 'Scadenziario', icon: Calendar },
            { path: '/movimenti-bancari', label: 'Movimenti Bancari', icon: CreditCard },
            { path: '/fornitori', label: 'Fornitori', icon: Factory },
            { path: '/catalogo', label: 'Catalogo Profili', icon: Warehouse },
            { path: '/articoli', label: 'Catalogo Articoli', icon: BoxIcon },
            { path: '/archivio-certificati', label: 'Archivio Certificati', icon: FileInput },
        ],
    },
    {
        id: 'perizie',
        label: 'Sopralluoghi & Perizie',
        icon: ShieldAlert,
        type: 'group',
        roles: ['admin', 'ufficio_tecnico'],
        children: [
            { path: '/sopralluoghi', label: 'Sopralluoghi AI', icon: ShieldAlert },
            { path: '/rilievi', label: 'Rilievi', icon: Ruler },
            { path: '/perizie', label: 'Perizie Sinistro', icon: ShieldAlert },
            { path: '/archivio-sinistri', label: 'Archivio Sinistri', icon: BarChart3 },
        ],
    },
    {
        id: 'contenuti',
        label: 'Contenuti',
        icon: PenSquare,
        type: 'link',
        path: '/contenuti',
        roles: ['admin'],
    },
    {
        id: 'impostazioni',
        label: 'Impostazioni',
        icon: Settings,
        type: 'group',
        roles: ['admin'],
        children: [
            { path: '/settings', label: 'Dati Azienda', icon: Settings },
            { path: '/impostazioni/pagamenti', label: 'Tipi Pagamento', icon: CreditCard },
            { path: '/manuale', label: 'Guida all\'Uso', icon: BookOpen },
            { path: '/registro-attivita', label: 'Registro Attivita', icon: ScrollText },
            { path: '/archivio-storico', label: 'Archivio Storico', icon: Archive },
        ],
    },
];

// ── Helpers ──────────────────────────────────────────────────────

function findActiveGroup(pathname) {
    for (const group of NAV_GROUPS) {
        if (group.type === 'link' && pathname.startsWith(group.path)) return group.id;
        if (group.children) {
            for (const child of group.children) {
                if (pathname === child.path || pathname.startsWith(child.path + '/')) return group.id;
            }
        }
    }
    return null;
}

function isChildActive(pathname, path) {
    if (path === '/dashboard') return pathname === '/dashboard';
    return pathname === path || pathname.startsWith(path + '/');
}

// ── Component ───────────────────────────────────────────────────

export default function DashboardLayout({ children }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [companyLogo, setCompanyLogo] = useState(null);
    const [alertCount, setAlertCount] = useState(0);
    const [smartCount, setSmartCount] = useState(0);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [notifDrawerOpen, setNotifDrawerOpen] = useState(false);
    const [notifItems, setNotifItems] = useState([]);
    const [notifLoading, setNotifLoading] = useState(false);

    const activeGroupId = findActiveGroup(location.pathname);
    const userRole = user?.role || 'admin';

    // Filter nav groups based on user role
    const filteredNav = NAV_GROUPS.filter(group => {
        if (!group.roles || group.roles.length === 0) return true;
        return group.roles.includes(userRole);
    }).map(group => {
        if (!group.children) return group;
        return {
            ...group,
            children: group.children.filter(child =>
                !child.roles || child.roles.length === 0 || child.roles.includes(userRole)
            ),
        };
    });
    const [openGroups, setOpenGroups] = useState(() => {
        return activeGroupId ? new Set([activeGroupId]) : new Set();
    });

    // Fetch company logo once
    useEffect(() => {
        apiRequest('/company/settings')
            .then(data => { if (data?.logo_url) setCompanyLogo(data.logo_url); })
            .catch(() => {});
    }, []);

    // Fetch alert count for notification badge
    useEffect(() => {
        if (['admin', 'ufficio_tecnico'].includes(userRole)) {
            apiRequest('/notifications/status')
                .then(data => { setAlertCount(data?.current_alerts?.total || 0); })
                .catch(() => {});
        }
    }, [userRole]);

    // Fetch smart notification count
    useEffect(() => {
        const fetchSmartCount = () => {
            apiRequest('/notifiche-smart/count')
                .then(data => { setSmartCount(data?.unread || 0); })
                .catch(() => {});
        };
        fetchSmartCount();
        const interval = setInterval(fetchSmartCount, 30000); // Poll every 30s
        return () => clearInterval(interval);
    }, []);

    const loadSmartNotif = async () => {
        setNotifLoading(true);
        try {
            const data = await apiRequest('/notifiche-smart?status=unread&limit=20');
            setNotifItems(data?.items || []);
        } catch { setNotifItems([]); }
        setNotifLoading(false);
    };

    const openNotifDrawer = () => {
        setNotifDrawerOpen(true);
        loadSmartNotif();
    };

    const handleMarkRead = async (notifId) => {
        await apiRequest(`/notifiche-smart/${notifId}/read`, { method: 'POST' });
        setNotifItems(prev => prev.filter(n => n.notification_id !== notifId));
        setSmartCount(prev => Math.max(0, prev - 1));
    };

    const handleMarkAllRead = async () => {
        await apiRequest('/notifiche-smart/read-all', { method: 'POST' });
        setNotifItems([]);
        setSmartCount(0);
    };

    // Keep active group open on navigation
    useEffect(() => {
        if (activeGroupId) {
            setOpenGroups(prev => {
                const next = new Set(prev);
                next.add(activeGroupId);
                return next;
            });
        }
    }, [activeGroupId]);

    // Close mobile sidebar on route change
    useEffect(() => { setMobileOpen(false); }, [location.pathname]);

    const toggleGroup = (groupId) => {
        setOpenGroups(prev => {
            const next = new Set(prev);
            if (next.has(groupId)) next.delete(groupId);
            else next.add(groupId);
            return next;
        });
    };

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const sidebarContent = (
        <>
            {/* Logo */}
            <div className="px-5 pt-5 pb-4 flex items-center justify-between">
                <img src="/logo-1090.png" alt="1090 Norma Facile" className="h-10 w-auto" data-testid="sidebar-brand-logo" />
                <button className="lg:hidden text-slate-400 hover:text-white p-1" onClick={() => setMobileOpen(false)} data-testid="close-mobile-menu">
                    <X className="h-5 w-5" />
                </button>
            </div>

            {/* Nav */}
            <nav className="flex-1 overflow-y-auto px-3 pb-2 sidebar-scroll">
                <div className="space-y-0.5">
                    {filteredNav.map((group) => {
                        if (group.type === 'link') {
                            return <SingleLink key={group.id} item={group} active={activeGroupId === group.id} navigate={navigate} badge={group.id === 'notifiche' ? alertCount : 0} />;
                        }
                        const isOpen = openGroups.has(group.id);
                        const hasActive = activeGroupId === group.id;
                        return (
                            <NavGroup
                                key={group.id}
                                group={group}
                                isOpen={isOpen}
                                hasActive={hasActive}
                                pathname={location.pathname}
                                onToggle={() => toggleGroup(group.id)}
                                navigate={navigate}
                            />
                        );
                    })}
                </div>
            </nav>

            {/* User menu */}
            <div className="p-3 border-t border-slate-700">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            data-testid="user-menu-btn"
                            className="flex items-center gap-3 w-full p-2 rounded-md hover:bg-white/10 transition-colors"
                        >
                            <Avatar className="h-8 w-8">
                                <AvatarImage src={user?.picture} alt={user?.name} />
                                <AvatarFallback className="bg-[#0055FF] text-white text-xs">
                                    {user?.name?.charAt(0) || 'U'}
                                </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 text-left min-w-0">
                                <p className="text-xs font-medium text-white truncate">{user?.name}</p>
                                <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
                                {userRole !== 'admin' && (
                                    <span className="text-[8px] bg-lime-500/20 text-lime-400 border border-lime-500/30 rounded-full px-1.5 py-0 mt-0.5 inline-block capitalize">{
                                        userRole === 'ufficio_tecnico' ? 'Uff. Tecnico' :
                                        userRole === 'officina' ? 'Officina' :
                                        userRole === 'amministrazione' ? 'Amministraz.' :
                                        userRole === 'guest' ? 'In Attesa' : userRole
                                    }</span>
                                )}
                            </div>
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel>Il mio account</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem data-testid="menu-profile" onClick={() => navigate('/settings')}>
                            <User className="mr-2 h-4 w-4" /> Profilo
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem data-testid="menu-logout" onClick={handleLogout} className="text-red-600">
                            <LogOut className="mr-2 h-4 w-4" /> Esci
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </>
    );

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Desktop Sidebar */}
            <aside className="hidden lg:flex fixed left-0 top-0 h-screen w-64 bg-[#1E293B] text-slate-300 border-r border-slate-700 z-50 flex-col">
                {sidebarContent}
            </aside>

            {/* Mobile Sidebar Overlay */}
            {mobileOpen && (
                <div className="fixed inset-0 z-50 lg:hidden" data-testid="mobile-sidebar-overlay">
                    <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
                    <aside className="absolute left-0 top-0 h-full w-72 bg-[#1E293B] text-slate-300 flex flex-col shadow-2xl animate-in slide-in-from-left duration-200">
                        {sidebarContent}
                    </aside>
                </div>
            )}

            {/* Main Content */}
            <main className="lg:ml-64 min-h-screen">
                <DemoBanner />
                {/* Top bar */}
                <div className="sticky top-0 z-40 bg-slate-50/80 backdrop-blur-sm border-b border-slate-200/60 px-4 lg:px-8 py-3 flex items-center gap-3">
                    <button className="lg:hidden text-slate-600 hover:text-slate-900 p-1.5 -ml-1" onClick={() => setMobileOpen(true)} data-testid="open-mobile-menu">
                        <Menu className="h-5 w-5" />
                    </button>
                    <div className="flex-1 flex justify-end items-center gap-2">
                        <GlobalSearchBar />
                        {/* Smart Notification Bell */}
                        <button
                            className="relative p-2 rounded-lg hover:bg-slate-200/60 transition-colors"
                            onClick={openNotifDrawer}
                            data-testid="smart-notif-bell"
                        >
                            <Bell className="h-5 w-5 text-slate-600" />
                            {(smartCount + alertCount) > 0 && (
                                <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white"
                                    data-testid="smart-notif-count">
                                    {smartCount + alertCount}
                                </span>
                            )}
                        </button>
                    </div>
                </div>
                <div className="p-4 lg:p-8 pb-16">{children}</div>
            </main>

            {/* Smart Notification Drawer */}
            {notifDrawerOpen && (
                <div className="fixed inset-0 z-50" data-testid="notif-drawer-overlay">
                    <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setNotifDrawerOpen(false)} />
                    <div className="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl animate-in slide-in-from-right duration-200 flex flex-col">
                        {/* Drawer Header */}
                        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
                            <div className="flex items-center gap-2">
                                <Bell className="h-5 w-5 text-slate-700" />
                                <h2 className="text-base font-bold text-slate-900">Notifiche</h2>
                                {smartCount > 0 && (
                                    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
                                        {smartCount}
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                {smartCount > 0 && (
                                    <button className="text-[11px] text-blue-600 hover:text-blue-800 font-medium"
                                        onClick={handleMarkAllRead} data-testid="mark-all-read">
                                        Segna tutte lette
                                    </button>
                                )}
                                <button className="p-1.5 hover:bg-slate-100 rounded-lg" onClick={() => setNotifDrawerOpen(false)}>
                                    <X className="h-4 w-4 text-slate-500" />
                                </button>
                            </div>
                        </div>
                        {/* Drawer Content */}
                        <div className="flex-1 overflow-y-auto">
                            {notifLoading ? (
                                <div className="flex justify-center py-12">
                                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
                                </div>
                            ) : notifItems.length === 0 ? (
                                <div className="py-16 text-center">
                                    <Bell className="h-8 w-8 text-slate-200 mx-auto mb-3" />
                                    <p className="text-sm text-slate-400">Nessuna notifica non letta</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-slate-100">
                                    {notifItems.map(n => (
                                        <NotifItem key={n.notification_id} notif={n}
                                            onRead={() => handleMarkRead(n.notification_id)}
                                            onNavigate={(path) => { setNotifDrawerOpen(false); handleMarkRead(n.notification_id); navigate(path); }}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                        {/* Footer link */}
                        <div className="px-5 py-3 border-t border-slate-200">
                            <button className="text-xs text-blue-600 hover:text-blue-800 font-medium w-full text-center"
                                onClick={() => { setNotifDrawerOpen(false); navigate('/notifiche'); }}
                                data-testid="goto-all-notif">
                                Vedi tutte le notifiche
                            </button>
                        </div>
                    </div>
                </div>
            )}
            <div className="lg:ml-64"><LegalFooter /></div>
        </div>
    );
}

// ── Sub-components ──────────────────────────────────────────────

function SingleLink({ item, active, navigate, badge = 0 }) {
    const Icon = item.icon;
    return (
        <a
            href={item.path}
            data-testid={`nav-${item.path.slice(1).replace(/\//g, '-')}`}
            onClick={(e) => { e.preventDefault(); navigate(item.path); }}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-150 ${
                active
                    ? 'bg-[#0055FF] text-white font-medium'
                    : 'text-slate-300 hover:text-white hover:bg-white/10'
            }`}
        >
            <Icon className="h-[18px] w-[18px] flex-shrink-0" strokeWidth={1.5} />
            <span className="flex-1">{item.label}</span>
            {badge > 0 && (
                <span className="bg-red-500 text-white text-[9px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1" data-testid="notification-badge">
                    {badge}
                </span>
            )}
        </a>
    );
}

function NavGroup({ group, isOpen, hasActive, pathname, onToggle, navigate }) {
    const Icon = group.icon;
    return (
        <div data-testid={`nav-group-${group.id}`}>
            {/* Parent toggle */}
            <button
                data-testid={`nav-toggle-${group.id}`}
                onClick={onToggle}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm transition-all duration-150 ${
                    hasActive
                        ? 'text-white font-semibold bg-white/5'
                        : 'text-slate-300 hover:text-white hover:bg-white/10'
                }`}
            >
                <Icon className="h-[18px] w-[18px] flex-shrink-0" strokeWidth={1.5} />
                <span className="flex-1 text-left">{group.label}</span>
                <ChevronDown
                    className={`h-3.5 w-3.5 text-slate-500 transition-transform duration-200 ${isOpen ? 'rotate-0' : '-rotate-90'}`}
                    strokeWidth={2}
                />
            </button>

            {/* Children — animated */}
            <div
                className={`overflow-hidden transition-all duration-200 ease-in-out ${
                    isOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                }`}
            >
                <div className="ml-3 pl-3 border-l border-slate-700/50 mt-0.5 mb-1 space-y-0.5">
                    {group.children.map((child) => {
                        const ChildIcon = child.icon;
                        const active = isChildActive(pathname, child.path);
                        return (
                            <a
                                key={child.path}
                                href={child.path}
                                data-testid={`nav-${child.path.slice(1).replace(/\//g, '-')}`}
                                onClick={(e) => { e.preventDefault(); navigate(child.path); }}
                                className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs transition-all duration-150 ${
                                    active
                                        ? 'bg-[#0055FF]/90 text-white font-medium'
                                        : 'text-slate-400 hover:text-slate-100 hover:bg-white/5'
                                }`}
                            >
                                <ChildIcon className="h-3.5 w-3.5 flex-shrink-0" strokeWidth={1.5} />
                                <span>{child.label}</span>
                            </a>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}


const NOTIF_SEVERITY = {
    critica: { bg: 'bg-red-50', border: 'border-l-red-500', icon: '!!', color: 'text-red-700' },
    alta: { bg: 'bg-amber-50', border: 'border-l-amber-500', icon: '!', color: 'text-amber-700' },
    media: { bg: 'bg-blue-50', border: 'border-l-blue-400', icon: 'i', color: 'text-blue-700' },
    bassa: { bg: 'bg-slate-50', border: 'border-l-slate-300', icon: '', color: 'text-slate-600' },
};

const NOTIF_TYPE_ICONS = {
    semaforo_peggiorato: { emoji: '', label: 'Semaforo' },
    nuovo_hard_block: { emoji: '', label: 'Blocco' },
    documento_scaduto: { emoji: '', label: 'Scadenza' },
    emissione_bloccata: { emoji: '', label: 'Emissione' },
    gate_pos_peggiorato: { emoji: '', label: 'POS' },
    pacchetto_incompleto: { emoji: '', label: 'Pacchetto' },
};

function NotifItem({ notif, onRead, onNavigate }) {
    const sev = NOTIF_SEVERITY[notif.severity] || NOTIF_SEVERITY.media;
    const typeInfo = NOTIF_TYPE_ICONS[notif.notification_type] || { emoji: '', label: '' };
    const timeAgo = formatTimeAgo(notif.updated_at || notif.created_at);

    return (
        <div className={`px-5 py-3.5 ${sev.bg} border-l-4 ${sev.border} hover:bg-white/80 transition-colors`}
            data-testid={`notif-${notif.notification_id}`}>
            <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${sev.color}`}>
                            {typeInfo.label || notif.notification_type}
                        </span>
                        <span className="text-[10px] text-slate-400">{timeAgo}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-900 leading-tight">{notif.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{notif.message}</p>
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                    {notif.linked_route && (
                        <button className="text-[10px] text-blue-600 hover:text-blue-800 font-medium"
                            onClick={() => onNavigate(notif.linked_route)} data-testid={`notif-goto-${notif.notification_id}`}>
                            Apri
                        </button>
                    )}
                    <button className="text-[10px] text-slate-400 hover:text-slate-600"
                        onClick={onRead} data-testid={`notif-read-${notif.notification_id}`}>
                        Letta
                    </button>
                </div>
            </div>
        </div>
    );
}

function formatTimeAgo(isoStr) {
    if (!isoStr) return '';
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'ora';
    if (mins < 60) return `${mins}m fa`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h fa`;
    const days = Math.floor(hours / 24);
    return `${days}g fa`;
}
