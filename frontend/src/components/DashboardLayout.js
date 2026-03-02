/**
 * Dashboard Layout — Accordion Sidebar Navigation
 * Groups: Dashboard, Commerciale, Produzione, Certificazioni, Acquisti, Perizie, Impostazioni
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
import {
    Sparkles, Receipt, Users, Settings, Ruler, Package, Shield,
    HardHat, Warehouse, ClipboardList, Truck, Factory, ShieldAlert,
    BarChart3, BoxIcon, FileInput, Camera, ChevronDown,
    Briefcase, Wrench, Award, ShoppingCart, FileText, LayoutGrid,
    CreditCard, TrendingUp, ClipboardCheck, Calendar, CircleDollarSign,
} from 'lucide-react';

// ── Navigation Structure ────────────────────────────────────────

const NAV_GROUPS = [
    {
        id: 'dashboard',
        label: 'Dashboard',
        icon: Sparkles,
        type: 'link',
        path: '/dashboard',
    },
    {
        id: 'ebitda',
        label: 'Analisi Finanziaria',
        icon: TrendingUp,
        type: 'link',
        path: '/ebitda',
    },
    {
        id: 'commerciale',
        label: 'Commerciale',
        icon: Briefcase,
        type: 'group',
        children: [
            { path: '/clients', label: 'Clienti', icon: Users },
            { path: '/preventivi', label: 'Preventivi', icon: ClipboardList },
            { path: '/invoices', label: 'Fatturazione', icon: Receipt },
            { path: '/ddt', label: 'DDT', icon: Truck },
        ],
    },
    {
        id: 'produzione',
        label: 'Produzione',
        icon: Wrench,
        type: 'group',
        children: [
            { path: '/planning', label: 'Planning Cantieri', icon: LayoutGrid },
            { path: '/rilievi', label: 'Rilievi', icon: Ruler },
            { path: '/distinte', label: 'Distinte', icon: Package },
            { path: '/tracciabilita', label: 'Tracciabilit\u00e0 EN 1090', icon: Shield },
            { path: '/sicurezza', label: 'Sicurezza POS', icon: HardHat },
        ],
    },
    {
        id: 'certificazioni',
        label: 'Certificazioni',
        icon: Award,
        type: 'group',
        children: [
            { path: '/quality-hub', label: 'Quality Hub', icon: LayoutGrid },
            { path: '/certificazioni', label: 'Certificazioni CE', icon: Shield },
            { path: '/core-engine', label: 'Core Engine', icon: Shield },
            { path: '/validazione-foto', label: 'Validazione Foto AI', icon: Camera },
            { path: '/report-cam', label: 'Sostenibilita & CO2', icon: Award },
            { path: '/sistema-qualita', label: 'Sistema Qualita', icon: FileText },
            { path: '/strumenti', label: 'Apparecchiature', icon: Wrench },
            { path: '/saldatori', label: 'Saldatori', icon: Users },
            { path: '/audit', label: 'Audit & NC', icon: ClipboardCheck },
        ],
    },
    {
        id: 'acquisti',
        label: 'Acquisti & Magazzino',
        icon: ShoppingCart,
        type: 'group',
        children: [
            { path: '/fatture-ricevute', label: 'Fatture Ricevute', icon: FileInput },
            { path: '/controllo-costi', label: 'Controllo Costi', icon: CircleDollarSign },
            { path: '/scadenziario', label: 'Scadenziario', icon: Calendar },
            { path: '/fornitori', label: 'Fornitori', icon: Factory },
            { path: '/catalogo', label: 'Catalogo Profili', icon: Warehouse },
            { path: '/articoli', label: 'Catalogo Articoli', icon: BoxIcon },
            { path: '/archivio-certificati', label: 'Archivio Certificati', icon: FileInput },
        ],
    },
    {
        id: 'perizie',
        label: 'Perizie',
        icon: ShieldAlert,
        type: 'group',
        children: [
            { path: '/perizie', label: 'Perizie Sinistro', icon: ShieldAlert },
            { path: '/archivio-sinistri', label: 'Archivio Sinistri', icon: BarChart3 },
        ],
    },
    {
        id: 'impostazioni',
        label: 'Impostazioni',
        icon: Settings,
        type: 'group',
        children: [
            { path: '/settings', label: 'Dati Azienda', icon: Settings },
            { path: '/impostazioni/pagamenti', label: 'Tipi Pagamento', icon: CreditCard },
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

    const activeGroupId = findActiveGroup(location.pathname);
    const [openGroups, setOpenGroups] = useState(() => {
        return activeGroupId ? new Set([activeGroupId]) : new Set();
    });

    // Fetch company logo once
    useEffect(() => {
        apiRequest('/company/settings')
            .then(data => { if (data?.logo_url) setCompanyLogo(data.logo_url); })
            .catch(() => {});
    }, []);

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

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Sidebar */}
            <aside className="fixed left-0 top-0 h-screen w-64 bg-[#1E293B] text-slate-300 border-r border-slate-700 z-50 flex flex-col">
                {/* Logo */}
                <div className="px-5 pt-5 pb-4">
                    <div className="inline-block bg-white rounded-lg p-1.5">
                        <img src="/logo-1090.jpeg" alt="1090 Norma Facile" className="h-8 w-auto" data-testid="sidebar-brand-logo" />
                    </div>
                </div>

                {/* Nav */}
                <nav className="flex-1 overflow-y-auto px-3 pb-2 sidebar-scroll">
                    <div className="space-y-0.5">
                        {NAV_GROUPS.map((group) => {
                            if (group.type === 'link') {
                                return <SingleLink key={group.id} item={group} active={activeGroupId === group.id} navigate={navigate} />;
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
            </aside>

            {/* Main Content */}
            <main className="ml-64 p-8 pb-16">{children}</main>
            <div className="ml-64"><LegalFooter /></div>
        </div>
    );
}

// ── Sub-components ──────────────────────────────────────────────

function SingleLink({ item, active, navigate }) {
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
            <span>{item.label}</span>
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
